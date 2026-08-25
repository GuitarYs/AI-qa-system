"""工单系统：转人工自动生成工单、分配、状态流转、AI 建议回复、相似工单。"""
from sqlalchemy.orm import Session

from . import llm, embeddings, rag
from .models import Conversation, Ticket, Message, User
import numpy as np

_PRIORITY_HINT = ["投诉", "退款", "赔偿", "冻结", "盗号", "发票", "账号锁定"]


def _gen_summary(db: Session, conversation: Conversation, last_message: str) -> str:
    """用 LLM 生成问题摘要。"""
    msgs = (db.query(Message).filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at).all())
    history = "\n".join(f"{m.role}: {m.content}" for m in msgs[-8:])
    try:
        result = llm.chat_json([
            {"role": "system", "content": "你是客服工单系统。请用一句话概括用户的核心问题，"
             "包含关键事实（如涉及的产品、订单、诉求），不超过 60 字。只输出 JSON：{\"summary\": \"...\"}"},
            {"role": "user", "content": f"对话历史：\n{history}\n\n用户最新诉求：{last_message}"},
        ], temperature=0.2, max_tokens=200)
        s = result.get("summary", "").strip()
        if s:
            return s
    except Exception:
        pass
    return last_message[:80]


def _detect_priority(text: str) -> str:
    for kw in ["退款", "赔偿", "盗号", "冻结", "投诉"]:
        if kw in text:
            return "high"
    for kw in ["发票", "报销", "账号锁定"]:
        if kw in text:
            return "medium"
    return "medium"


def create_ticket(db: Session, conversation: Conversation, user: User,
                  last_message: str, reason: str = "") -> Ticket:
    """转人工时自动生成工单（含用户信息、对话历史、AI 摘要、优先级）。"""
    summary = _gen_summary(db, conversation, last_message)
    priority = _detect_priority(last_message)
    title = summary[:40] if summary else last_message[:40]
    ticket = Ticket(
        conversation_id=conversation.id,
        user_id=user.id,
        title=title,
        summary=summary,
        priority=priority,
        status="pending",
        category="",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_conversation_history(db: Session, conversation_id: int) -> list[dict]:
    msgs = (db.query(Message).filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at).all())
    return [{"role": m.role, "content": m.content} for m in msgs]


def find_similar_tickets(db: Session, ticket: Ticket, top_k: int = 3) -> list[Ticket]:
    """基于摘要向量相似度找历史相似工单（用于建议回复的参考）。"""
    others = (db.query(Ticket)
              .filter(Ticket.id != ticket.id, Ticket.summary != "")
              .order_by(Ticket.id.desc()).limit(200).all())
    if not others:
        return []
    texts = [ticket.summary] + [t.summary for t in others]
    vecs = embeddings.embed_texts(texts)
    q = vecs[0]
    scores = np.dot(vecs[1:], q)
    order = np.argsort(-scores)[:top_k]
    return [others[i] for i in order]


def suggest_reply(db: Session, ticket: Ticket) -> str:
    """客服处理工单时，AI 基于知识库 + 历史相似工单给出建议回复。"""
    # 1) 从知识库检索相关片段
    chunks = rag.retrieve(db, ticket.summary or ticket.title, top_k=3)
    kb_text = "\n\n".join(
        f"[{c['doc_title']} · {c['source_ref']}]\n{c['text']}" for c in chunks)

    # 2) 历史相似工单
    similar = find_similar_tickets(db, ticket)
    hist_text = "\n\n".join(
        f"历史工单#{t.id}（{t.status}，满意度{t.satisfaction or '-'}）：{t.summary}" for t in similar)

    prompt = (
        "你是资深客服坐席的 AI 助手。请基于下面的知识库片段和历史相似工单，"
        "为当前工单写一条专业、可发送给客户的建议回复。"
        "优先采用知识库里的准确信息，不要编造知识库没有的内容。\n\n"
        f"【当前工单】#{ticket.id} 标题：{ticket.title}\n摘要：{ticket.summary}\n\n"
        f"【知识库相关片段】\n{kb_text or '（无）'}\n\n"
        f"【历史相似工单】\n{hist_text or '（无）'}\n\n"
        "请直接输出建议回复内容。"
    )
    try:
        return llm.chat([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=600)
    except Exception as e:
        return f"（建议回复生成失败：{e}）"


def ticket_to_dict(t: Ticket) -> dict:
    return {
        "id": t.id,
        "conversation_id": t.conversation_id,
        "user_id": t.user_id,
        "user_name": t.user.name if t.user else "",
        "assignee_id": t.assignee_id,
        "assignee_name": t.assignee.name if t.assignee else "",
        "title": t.title,
        "summary": t.summary,
        "priority": t.priority,
        "status": t.status,
        "category": t.category,
        "satisfaction": t.satisfaction,
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "updated_at": t.updated_at.isoformat() if t.updated_at else "",
    }
