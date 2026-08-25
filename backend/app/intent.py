"""意图识别：规则（关键词）优先兜底，LLM 分类兜在上面。

返回三类之一：
- consult：咨询类，由 AI 基于知识库作答
- transfer：投诉/复杂问题，转人工
- order：查订单，调业务系统
"""
from . import config, llm

_SYSTEM = (
    "你是客服系统的意图分类器。把用户消息归为以下三类之一：\n"
    "1. consult（咨询）：可以靠产品知识/帮助文档回答的问题，例如套餐价格、发票流程、功能对比、"
    "故障排查、账号安全等。\n"
    "2. transfer（转人工）：投诉、强烈不满、要求退款/赔偿/人工介入、情绪激动、或知识库无法覆盖"
    "的复杂问题。\n"
    "3. order（查订单）：询问自己订单的状态、发货、物流进度。\n"
    '只输出一个 JSON：{"intent": "consult|transfer|order"}'
)


def detect_intent(message: str) -> str:
    text = message.strip()
    # 1) 规则兜底：明确的转人工 / 查订单关键词
    for kw in config.INTENT_KEYWORDS["transfer"]:
        if kw in text:
            return "transfer"
    for kw in config.INTENT_KEYWORDS["order"]:
        if kw in text:
            return "order"

    # 2) LLM 分类兜上面（失败则默认 consult）
    try:
        result = llm.chat_json([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ], temperature=0.0, max_tokens=50)
        intent = str(result.get("intent", "consult")).strip().lower()
        if intent in ("consult", "transfer", "order"):
            return intent
    except Exception:
        pass
    return "consult"
