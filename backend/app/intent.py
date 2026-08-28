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
    "故障排查、账号安全等。注意：用户遇到异常/故障、询问「怎么办」「为什么」「会不会…」时属于故障排查，"
    "归为 consult——即使句中提到「订单」（如「付款了但订单还显示未支付，怎么办」）。\n"
    "2. transfer（转人工）：投诉、强烈不满、要求退款/赔偿/人工介入、情绪激动、或知识库无法覆盖"
    "的复杂问题。\n"
    "3. order（查订单）：用户主动「查询/查看」自己订单的具体信息，典型如「查一下我的订单」「我的订单到哪了」"
    "「订单号 xxx 什么状态」。仅在用户是要查看订单时才归 order，不是所有含「订单」的话都是查订单。\n"
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
