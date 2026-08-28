"""Pydantic 请求/响应模型。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---- 知识库 ----
class DocCreate(BaseModel):
    title: str
    category: str = "FAQ"
    content: str
    note: str = ""


class DocUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    note: str = ""


# ---- 对话 ----
class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    user_id: int = 1
    message: str


class SourceRef(BaseModel):
    doc_title: str
    source_ref: str
    score: float
    text: str


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: Optional[int] = None
    reply: str
    intent: str
    confidence: float
    low_confidence: bool
    transferred: bool
    ticket_id: Optional[int] = None
    sources: list[SourceRef] = []


# ---- 反馈 ----
class FeedbackRequest(BaseModel):
    message_id: int
    conversation_id: Optional[int] = None
    kind: str  # up / down


# ---- 工单 ----
class TicketAssign(BaseModel):
    assignee_id: int


class TicketStatus(BaseModel):
    status: str  # pending/processing/resolved/closed


class TicketSatisfaction(BaseModel):
    satisfaction: int  # 1-5


class TicketResolution(BaseModel):
    resolution: str = ""  # 人工客服处理意见/回复


# ---- 看板 ----
class DashboardRequest(BaseModel):
    start: Optional[str] = None  # YYYY-MM-DD
    end: Optional[str] = None
