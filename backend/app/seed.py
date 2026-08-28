"""种子数据：7 用户（5 客户 + 2 客服）+ 4 知识库 + 订单 + 10 历史工单 + 若干历史会话。

历史工单与会话写入真实数据表，供看板按时间统计、供「相似工单/建议回复」参考，
满足「≥20 FAQ + 10 历史工单 + 5 用户」的验收要求（用户端下拉展示 5 个 customer）。
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import kb_service
from .models import User, Conversation, Message, Ticket, Order, Document
from .db import Base, engine

SEED_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent.parent / "seed_data" / "kb"

USERS = [
    {"name": "张三", "email": "zhangsan@example.com", "role": "customer"},
    {"name": "李四", "email": "lisi@example.com", "role": "customer"},
    {"name": "王五", "email": "wangwu@example.com", "role": "customer"},
    {"name": "赵六", "email": "zhaoliu@example.com", "role": "customer"},
    {"name": "孙七", "email": "sunqi@example.com", "role": "customer"},
    {"name": "客服小李", "email": "agent-li@cloudwork.com", "role": "agent"},
    {"name": "客服小陈", "email": "agent-chen@cloudwork.com", "role": "agent"},
]

ORDERS = [
    {"order_no": "CW20260715001", "user": "张三", "product": "专业版年付", "amount": 1068.0, "status": "已发货"},
    {"order_no": "CW20260801002", "user": "张三", "product": "企业版月付", "amount": 1990.0, "status": "已完成"},
    {"order_no": "CW20260805003", "user": "李四", "product": "基础版年付", "amount": 468.0, "status": "待发货"},
    {"order_no": "CW20260812004", "user": "李四", "product": "专业版月付", "amount": 267.0, "status": "已完成"},
    {"order_no": "CW20260815005", "user": "王五", "product": "专业版年付", "amount": 1068.0, "status": "待发货"},
    {"order_no": "CW20260818006", "user": "王五", "product": "基础版月付", "amount": 39.0, "status": "已完成"},
    {"order_no": "CW20260820007", "user": "赵六", "product": "企业版月付", "amount": 1990.0, "status": "已发货"},
    {"order_no": "CW20260822008", "user": "赵六", "product": "基础版年付", "amount": 468.0, "status": "已完成"},
    {"order_no": "CW20260824009", "user": "孙七", "product": "专业版月付", "amount": 267.0, "status": "待发货"},
    {"order_no": "CW20260825010", "user": "孙七", "product": "专业版年付", "amount": 1068.0, "status": "已完成"},
]

# 历史工单：每条含对话历史（用户消息 + 转人工答复）与工单元信息
# days_ago 控制时间分布；status 覆盖待处理/处理中/已解决/已关闭
TICKETS = [
    {"user": "张三", "days_ago": 6, "status": "resolved", "priority": "medium", "satisfaction": 5,
     "summary": "用户咨询增值税专用发票如何申请及所需资质材料", "category": "发票",
     "user_msg": "我们公司想开增值税专用发票，需要准备哪些材料？"},
    {"user": "李四", "days_ago": 6, "status": "resolved", "priority": "high", "satisfaction": 4,
     "summary": "用户投诉付款后订单状态一直显示未支付，担心重复扣款", "category": "支付故障",
     "user_msg": "我付款了但订单还显示未支付，会不会重复扣款？我要投诉！"},
    {"user": "王五", "days_ago": 5, "status": "closed", "priority": "medium", "satisfaction": 3,
     "summary": "用户忘记密码且重置邮件收不到，请求人工协助找回", "category": "账号安全",
     "user_msg": "我忘记密码了，重置邮件一直收不到，帮我人工处理一下。"},
    {"user": "张三", "days_ago": 5, "status": "resolved", "priority": "low", "satisfaction": 5,
     "summary": "用户咨询个人能否开企业抬头发票", "category": "发票",
     "user_msg": "我是个人用户，能开企业抬头的发票吗？"},
    {"user": "李四", "days_ago": 4, "status": "resolved", "priority": "high", "satisfaction": 4,
     "summary": "用户账号被盗出现异常登录，请求冻结并退出所有设备", "category": "账号安全",
     "user_msg": "我账号好像被盗了，有异地登录，帮我冻结账号调查一下。"},
    {"user": "王五", "days_ago": 4, "status": "closed", "priority": "medium", "satisfaction": 4,
     "summary": "用户咨询去年消费是否还能补开发票", "category": "发票",
     "user_msg": "去年的消费现在还能补开发票吗？"},
    {"user": "张三", "days_ago": 3, "status": "processing", "priority": "medium", "satisfaction": None,
     "summary": "用户反馈同事修改文件后自己看不到更新，怀疑同步异常", "category": "文件同步",
     "user_msg": "同事改了文件我这边一直看不到更新，是同步出问题了吗？"},
    {"user": "李四", "days_ago": 2, "status": "processing", "priority": "low", "satisfaction": None,
     "summary": "用户咨询文件删除后能否找回，涉及回收站与版本历史", "category": "文件同步",
     "user_msg": "我误删了一个重要文件，还能找回吗？"},
    {"user": "王五", "days_ago": 1, "status": "pending", "priority": "medium", "satisfaction": None,
     "summary": "用户咨询开通 2FA 后换手机如何解绑", "category": "账号安全",
     "user_msg": "我开了两步验证后换新手机了，怎么解绑旧手机？"},
    {"user": "张三", "days_ago": 0, "status": "pending", "priority": "high", "satisfaction": None,
     "summary": "用户投诉 AI 助手本月额度提前耗尽无法使用，要求退款", "category": "套餐计费",
     "user_msg": "这个月 AI 助手额度这么快就用完了，我要投诉并要求退款！"},
]

# 历史「AI 已解决」会话（未转人工，用于 AI 解决率）
AI_RESOLVED = [
    {"user": "张三", "days_ago": 6, "q": "三个套餐分别多少钱？有折扣吗？"},
    {"user": "李四", "days_ago": 5, "q": "怎么申请开发票？在哪里操作？"},
    {"user": "王五", "days_ago": 4, "q": "基础版和专业版最大的功能差别是什么？"},
    {"user": "张三", "days_ago": 3, "q": "忘记密码怎么办？"},
    {"user": "李四", "days_ago": 2, "q": "网页打开很卡怎么办？"},
    {"user": "王五", "days_ago": 1, "q": "移动端 App 是不是所有套餐都能用？"},
    {"user": "张三", "days_ago": 0, "q": "怎么开启双因素认证 2FA？"},
    {"user": "李四", "days_ago": 0, "q": "文件上传失败提示网络错误怎么办？"},
]


def _dt(days_ago: int, hour: int = 10) -> datetime:
    return datetime.now() - timedelta(days=days_ago) + timedelta(hours=hour - 10)


def seed_all(db: Session):
    if db.query(User).count() > 0:
        return False  # 已播种，跳过

    # 1) 用户
    user_map = {}
    for u in USERS:
        obj = User(name=u["name"], email=u["email"], role=u["role"])
        db.add(obj)
        db.flush()
        user_map[u["name"]] = obj

    # 2) 订单
    for o in ORDERS:
        db.add(Order(order_no=o["order_no"], user_id=user_map[o["user"]].id,
                     product=o["product"], amount=o["amount"], status=o["status"]))

    # 3) 知识库（分块 + 向量化入库）
    kb_files = [
        ("产品套餐", "FAQ", "kb_产品套餐.md"),
        ("发票与报销", "FAQ", "kb_发票与报销.md"),
        ("账号安全", "FAQ", "kb_账号安全.md"),
        ("常见故障", "FAQ", "kb_常见故障.md"),
    ]
    for title, cat, fname in kb_files:
        path = SEED_DIR / fname
        if path.exists():
            content = path.read_text(encoding="utf-8")
            kb_service.create_document(db, title, cat, content, note="种子知识库")

    # 4) 历史工单（含对话历史）
    agent_ids = [user_map["客服小李"].id, user_map["客服小陈"].id]
    for i, t in enumerate(TICKETS):
        u = user_map[t["user"]]
        conv = Conversation(user_id=u.id, status="transferred", ai_resolved=False)
        conv.created_at = _dt(t["days_ago"])
        db.add(conv)
        db.flush()
        m1 = Message(conversation_id=conv.id, role="user", content=t["user_msg"],
                     intent="transfer")
        m1.created_at = _dt(t["days_ago"])
        m2 = Message(conversation_id=conv.id, role="assistant",
                     content=f"已为您转接人工客服（工单将自动创建）。", intent="transfer")
        m2.created_at = _dt(t["days_ago"], hour=10) + timedelta(minutes=1)
        db.add_all([m1, m2])

        ticket = Ticket(
            conversation_id=conv.id, user_id=u.id,
            assignee_id=agent_ids[i % 2],
            title=t["summary"][:40], summary=t["summary"],
            priority=t["priority"], status=t["status"],
            category=t["category"], satisfaction=t["satisfaction"],
        )
        ticket.created_at = _dt(t["days_ago"], hour=10) + timedelta(minutes=2)
        ticket.updated_at = ticket.created_at
        db.add(ticket)

    # 5) 历史「AI 已解决」会话
    for a in AI_RESOLVED:
        u = user_map[a["user"]]
        conv = Conversation(user_id=u.id, status="active", ai_resolved=True)
        conv.created_at = _dt(a["days_ago"])
        db.add(conv)
        db.flush()
        m1 = Message(conversation_id=conv.id, role="user", content=a["q"],
                     intent="consult", confidence=0.85)
        m1.created_at = _dt(a["days_ago"])
        m2 = Message(conversation_id=conv.id, role="assistant",
                     content="（AI 基于知识库作答，此处为历史会话摘要）",
                     intent="consult", confidence=0.85)
        m2.created_at = _dt(a["days_ago"]) + timedelta(seconds=8)
        db.add_all([m1, m2])

    db.commit()
    return True


def run_seed():
    Base.metadata.create_all(bind=engine)
    from .db import SessionLocal
    db = SessionLocal()
    try:
        created = seed_all(db)
        print("种子数据已写入" if created else "已存在数据，跳过播种")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
