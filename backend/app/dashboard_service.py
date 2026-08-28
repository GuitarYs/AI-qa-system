"""数据分析看板。所有数字都从真实对话/工单/反馈表中统计，不预置假数据。"""
from datetime import datetime, timedelta, date

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from . import clustering
from .models import Conversation, Message, Ticket, Feedback, User


def _parse_range(start: str | None, end: str | None) -> tuple[datetime, datetime]:
    today = date.today()
    if end:
        end_d = datetime.strptime(end, "%Y-%m-%d").date()
    else:
        end_d = today
    if start:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
    else:
        start_d = end_d
    start_dt = datetime.combine(start_d, datetime.min.time())
    end_dt = datetime.combine(end_d, datetime.max.time())
    return start_dt, end_dt


def _day_series(start_dt: datetime, end_dt: datetime) -> list[str]:
    days = []
    d = start_dt.date()
    while d <= end_dt.date():
        days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def get_dashboard(db: Session, start: str | None = None, end: str | None = None) -> dict:
    start_dt, end_dt = _parse_range(start, end)

    # ---- 会话 & 趋势 ----
    convs = (db.query(Conversation)
             .filter(Conversation.created_at >= start_dt, Conversation.created_at <= end_dt)
             .all())
    total_convs = len(convs)
    transferred = sum(1 for c in convs if c.status == "transferred")
    ai_resolved = sum(1 for c in convs if c.status != "transferred" and c.ai_resolved)
    ai_rate = round((total_convs - transferred) / total_convs * 100, 1) if total_convs else 0.0

    # 按天趋势（柱状图/趋势线用）
    day_counts = {d: 0 for d in _day_series(start_dt, end_dt)}
    for c in convs:
        key = c.created_at.date().isoformat()
        if key in day_counts:
            day_counts[key] += 1

    # ---- 平均响应时长 ----
    msgs = (db.query(Message)
            .filter(Message.created_at >= start_dt, Message.created_at <= end_dt)
            .order_by(Message.conversation_id, Message.id).all())
    resp_seconds = []
    prev = None
    for m in msgs:
        if m.role == "assistant" and prev is not None and prev.conversation_id == m.conversation_id and prev.role == "user":
            resp_seconds.append((m.created_at - prev.created_at).total_seconds())
        prev = m
    avg_resp = round(sum(resp_seconds) / len(resp_seconds), 1) if resp_seconds else 0.0

    # ---- 满意度 ----
    fbs = (db.query(Feedback)
           .filter(Feedback.created_at >= start_dt, Feedback.created_at <= end_dt).all())
    up = sum(1 for f in fbs if f.kind == "up")
    down = sum(1 for f in fbs if f.kind == "down")
    tickets_in_range = (db.query(Ticket)
                        .filter(Ticket.created_at >= start_dt, Ticket.created_at <= end_dt).all())
    sats = [t.satisfaction for t in tickets_in_range if t.satisfaction]
    avg_sat = round(sum(sats) / len(sats), 1) if sats else 0.0

    # 点赞/点踩按天序列（柱状图用）
    fb_up_day = {d: 0 for d in day_counts}
    fb_down_day = {d: 0 for d in day_counts}
    for f in fbs:
        key = f.created_at.date().isoformat()
        if key in fb_up_day:
            if f.kind == "up":
                fb_up_day[key] += 1
            else:
                fb_down_day[key] += 1
    feedback_trend = [{"date": d, "up": fb_up_day[d], "down": fb_down_day[d]} for d in day_counts]

    # 工单满意度按天序列（趋势线用）
    sat_day = {}
    for t in tickets_in_range:
        if t.satisfaction:
            key = t.created_at.date().isoformat()
            sat_day.setdefault(key, []).append(t.satisfaction)
    satisfaction_trend = []
    for d in day_counts:
        scores = sat_day.get(d, [])
        satisfaction_trend.append({
            "date": d,
            "score": round(sum(scores) / len(scores), 1) if scores else None,
            "count": len(scores),
        })

    # ---- 热门问题 Top10（AI 聚类）----
    user_qs = [m.content for m in msgs if m.role == "user"]
    hot_topics = clustering.cluster_and_label(user_qs, max_k=10)

    # ---- 知识库缺口分析：转人工/低置信的问题聚类 ----
    gap_qs = []
    for m in msgs:
        if m.role == "user" and (m.low_confidence or m.intent == "transfer"):
            gap_qs.append(m.content)
    for t in tickets_in_range:
        gap_qs.append(t.summary or t.title)
    gap_clusters = clustering.cluster_and_label(gap_qs, max_k=8)
    gap_total = sum(g["count"] for g in gap_clusters)
    gap_analysis = []
    for g in gap_clusters:
        pct = round(g["count"] / gap_total * 100, 1) if gap_total else 0.0
        gap_analysis.append({
            "label": g["label"],
            "count": g["count"],
            "pct": pct,
            "suggestion": f"「{g['label']}」类问题 {g['count']} 条转人工（占 {pct}%），建议补充/完善 {g['label']} 相关知识",
            "examples": g["examples"],
        })

    # ---- 工单状态分布 ----
    ticket_status = {}
    for t in tickets_in_range:
        ticket_status[t.status] = ticket_status.get(t.status, 0) + 1

    return {
        "range": {"start": start_dt.date().isoformat(), "end": end_dt.date().isoformat()},
        "total_conversations": total_convs,
        "ai_resolution_rate": ai_rate,
        "ai_resolved_count": ai_resolved,
        "transferred_count": transferred,
        "avg_response_seconds": avg_resp,
        "feedback": {"up": up, "down": down, "total": up + down},
        "feedback_trend": feedback_trend,
        "ticket_avg_satisfaction": avg_sat,
        "satisfaction_trend": satisfaction_trend,
        "trend": [{"date": d, "count": day_counts[d]} for d in day_counts],
        "hot_topics": hot_topics,
        "gap_analysis": gap_analysis,
        "ticket_status": ticket_status,
        "ticket_total": len(tickets_in_range),
    }
