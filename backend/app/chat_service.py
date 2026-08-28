"""对话引擎（AI 核心）。

流程：意图识别 → 分支处理
- order：查业务系统（订单表），直接回答订单状态
- transfer：转人工，生成工单
- consult：RAG 检索 → 置信度判断 → 够高则 LLM 生成（带来源），过低则诚实承认不知道并转人工

维护多轮上下文：生成时把最近几轮对话一并喂给 LLM。
"""
import re

from sqlalchemy.orm import Session

from . import config, llm, rag, intent
from . import ticket_service
from .models import Conversation, Message, User, Order

_ANSWER_SYSTEM = (
    "你是「云作 Cloudwork」云协作 SaaS 平台的 AI 客服。请严格基于下方【知识库片段】回答用户问题。\n"
    "要求：\n"
    "1. 只能使用知识库片段中的信息回答，禁止编造片段中没有的内容；\n"
    "2. 回答时在关键结论后用【来源：文档名 · 段落号】标注出处（如【来源：产品套餐 · Q1】）；\n"
    "3. 如果知识库片段不足以回答，直接说「这个问题我暂时无法从知识库中找到确切答案」，不要硬编；\n"
    "4. 语气友好、简洁、条理清晰。"
)

_ORDER_SYSTEM = "你是客服系统。下面是根据业务系统查询到的用户订单信息，请用简洁友好的中文告知用户。"


def _recent_history(db: Session, conversation_id: int, n: int = 6) -> list[dict]:
    msgs = (db.query(Message).filter(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc()).limit(n).all())
    return [{"role": m.role, "content": m.content} for m in reversed(msgs)]


def _format_sources(chunks: list[dict]) -> list[dict]:
    return [{
        "doc_title": c["doc_title"],
        "source_ref": c["source_ref"],
        "score": c["score"],
        "text": c["text"][:200],
    } for c in chunks]


def _lookup_order(db: Session, user_id: int, message: str) -> list[Order]:
    orders = db.query(Order).filter(Order.user_id == user_id).all()
    if not orders:
        return []
    # 尝试从消息里提取订单号
    nos = re.findall(r"[A-Za-z0-9]{6,20}", message)
    if nos:
        for n in nos:
            for o in orders:
                if n.lower() in o.order_no.lower():
                    return [o]
    return orders


_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _prev_assistant_intent(db: Session, conversation_id: int) -> str | None:
    """最近一条 assistant 消息的意图，用于多轮上下文判断。"""
    m = (db.query(Message)
         .filter(Message.conversation_id == conversation_id, Message.role == "assistant")
         .order_by(Message.id.desc()).first())
    return m.intent if m else None


def _parse_order_select(message: str) -> int | None:
    """从指代短句里解析「选第几笔订单」（从 1 开始），解析不出返回 None。

    例：「第一个吧」→ 1；「第二笔」→ 2；「就第一个」→ 1。
    """
    m = re.search(r"第\s*([一二三四五六七八九十\d]+)\s*[个笔单张]?", message)
    if not m:
        return None
    tok = m.group(1)
    if tok.isdigit():
        return int(tok)
    return _CN_NUM.get(tok)


# 对上一条订单问询的肯定/接续回应词（如「好的」「嗯」「可以」）
_ORDER_ACK = {"好的", "好", "好呀", "好呢", "好哦", "好嘞", "好滴", "嗯", "嗯嗯",
              "是", "是的", "对", "对的", "可以", "行", "ok", "okay"}


def _is_order_ack(message: str) -> bool:
    """判断是否为对上一条订单问询的纯肯定/接续回应。

    例：「好的」→ True；「好的，第一个吧」→ 先由 _parse_order_select 处理；「好的，我想退款」→ False。
    只匹配纯肯定词，避免把带新诉求的话误判为接续。
    """
    core = message.strip().strip("。！!？?~～ .,，").lower()
    core = core.rstrip("吧呢啊呀哦哈滴啦了")
    return core in _ORDER_ACK


def _order_reply(db: Session, user_id: int, message: str, select: int | None = None) -> str:
    orders = _lookup_order(db, user_id, message)
    if not orders:
        return "在业务系统中没有查询到您名下的订单记录，如需进一步核实，可以转接人工客服帮您查。"
    # 多轮续问：用户只回了「好的」这类肯定词、未指明哪一笔 → 简单确认并回归正常接待
    if select is None and _is_order_ack(message):
        return "好的，如还有其他订单问题或任何需要帮助的地方，请随时告诉我。"
    # 多轮续问：用户明确选了第几笔（如「第一个吧」），只回那一笔
    if select is not None:
        orders = [orders[select - 1]] if 1 <= select <= len(orders) else orders[:1]
    lines = []
    for o in orders[:5]:
        lines.append(f"订单 {o.order_no}｜{o.product}｜金额 ￥{o.amount:.2f}｜状态：{o.status}")
    info = "\n".join(lines)
    try:
        reply = llm.chat([
            {"role": "system", "content": _ORDER_SYSTEM},
            {"role": "user", "content": f"用户问题：{message}\n\n订单信息：\n{info}"},
        ], temperature=0.2, max_tokens=400)
        return reply
    except Exception:
        return "您名下的订单如下：\n" + info


def handle_chat(db: Session, user_id: int, message: str,
                conversation_id: int | None = None) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        user = User(id=user_id, name=f"访客{user_id}", role="customer")
        db.add(user)
        db.commit()

    conv = None
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv is None:
        conv = Conversation(user_id=user_id, status="active")
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 存用户消息
    db.add(Message(conversation_id=conv.id, role="user", content=message))
    db.commit()

    # 1) 意图识别
    it = intent.detect_intent(message)

    # 1.5) 多轮上下文：上一轮 AI 在列订单、本轮是指代选择（「第一个吧」）或肯定接续（「好的」）
    #      → 续走订单分支，避免把「好的」当成新问题走 RAG 导致低置信转人工。
    #      仅当本轮不含明确转人工信号（投诉/人工等）时才覆盖，避免误吞「我要投诉」。
    select = _parse_order_select(message)
    if it != "order" and (select is not None or _is_order_ack(message)) \
            and _prev_assistant_intent(db, conv.id) == "order" \
            and not any(kw in message for kw in config.INTENT_KEYWORDS["transfer"]):
        it = "order"

    # 2) 分支处理
    if it == "order":
        reply = _order_reply(db, user_id, message, select=select)
        am = Message(conversation_id=conv.id, role="assistant", content=reply,
                     intent="order", confidence=1.0, sources=[])
        db.add(am)
        db.flush()
        db.commit()
        return {
            "conversation_id": conv.id, "message_id": am.id, "reply": reply, "intent": "order",
            "confidence": 1.0, "low_confidence": False, "transferred": False,
            "ticket_id": None, "sources": [],
        }

    if it == "transfer":
        ticket = ticket_service.create_ticket(db, conv, user, message, reason="意图识别为转人工")
        conv.status = "transferred"
        db.commit()
        reply = ("已为您转接人工客服。我们已生成工单 #{tid}，客服会尽快处理您的问题，请稍候。"
                 .format(tid=ticket.id))
        am = Message(conversation_id=conv.id, role="assistant", content=reply,
                     intent="transfer", confidence=0.0, sources=[])
        db.add(am)
        db.flush()
        db.commit()
        return {
            "conversation_id": conv.id, "message_id": am.id, "reply": reply, "intent": "transfer",
            "confidence": 0.0, "low_confidence": True, "transferred": True,
            "ticket_id": ticket.id, "sources": [],
        }

    # 3) consult：RAG 检索
    chunks = rag.retrieve(db, message)
    if not chunks:
        top_score = 0.0
    else:
        top_score = chunks[0]["score"]

    # 4) 防幻觉：Top-1 低于阈值 → 老实承认不知道并转人工
    if top_score < config.RAG_MIN_SCORE:
        conv.status = "transferred"
        ticket = ticket_service.create_ticket(db, conv, user, message, reason="置信度不足")
        db.commit()
        reply = ("抱歉，这个问题我暂时无法从知识库中找到确切答案，为避免误导您，"
                 "我已为您转接人工客服（工单 #{tid}）。".format(tid=ticket.id))
        am = Message(conversation_id=conv.id, role="assistant", content=reply,
                     intent="consult", confidence=top_score,
                     low_confidence=True, sources=_format_sources(chunks))
        db.add(am)
        db.flush()
        db.commit()
        return {
            "conversation_id": conv.id, "message_id": am.id, "reply": reply, "intent": "consult",
            "confidence": top_score, "low_confidence": True, "transferred": True,
            "ticket_id": ticket.id, "sources": _format_sources(chunks),
        }

    # 5) 高置信：LLM 生成（带来源 + 多轮上下文）
    kb_text = "\n\n".join(
        f"[来源：{c['doc_title']} · {c['source_ref']}]\n{c['text']}" for c in chunks)
    history = _recent_history(db, conv.id, n=6)
    msgs = [{"role": "system", "content": _ANSWER_SYSTEM},
            {"role": "user", "content": f"【知识库片段】\n{kb_text}\n\n"
                                        f"【对话历史】\n{history or '（无）'}\n\n"
                                        f"【用户问题】\n{message}"}]
    try:
        reply = llm.chat(msgs, temperature=config.LLM_TEMPERATURE, max_tokens=800)
    except Exception as e:
        reply = f"（AI 生成失败：{e}）请稍后重试或转人工。"

    conv.ai_resolved = True
    am = Message(conversation_id=conv.id, role="assistant", content=reply,
                 intent="consult", confidence=top_score,
                 low_confidence=False, sources=_format_sources(chunks))
    db.add(am)
    db.flush()
    db.commit()
    return {
        "conversation_id": conv.id, "message_id": am.id, "reply": reply, "intent": "consult",
        "confidence": top_score, "low_confidence": False, "transferred": False,
        "ticket_id": None, "sources": _format_sources(chunks),
    }
