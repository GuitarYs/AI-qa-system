"""ORM 模型。关系库：用户/会话/消息/工单/知识库/版本/分块/反馈/订单。"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from .db import Base


def now():
    return datetime.now()


class User(Base):
    """用户 / 坐席（role: customer / agent）。"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    email = Column(String(128), unique=True)
    role = Column(String(16), default="customer")  # customer / agent
    created_at = Column(DateTime, default=now)

    conversations = relationship("Conversation", back_populates="user")


class Document(Base):
    """知识库文档（FAQ / 政策 / 手册）。"""
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    title = Column(String(256), nullable=False)
    category = Column(String(64), default="FAQ")  # FAQ / 政策 / 手册
    content = Column(Text, nullable=False)        # Markdown 全文（最新版本）
    current_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    versions = relationship("DocumentVersion", back_populates="document",
                            cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="document",
                          cascade="all, delete-orphan")


class DocumentVersion(Base):
    """知识库版本：每次更新追加一条，实现历史追溯。"""
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    note = Column(String(256), default="")
    created_at = Column(DateTime, default=now)

    document = relationship("Document", back_populates="versions")


class Chunk(Base):
    """文档分块。向量存在 FAISS（按 index_id 对应），文本与元数据存这里。"""
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    source_ref = Column(String(256), default="")  # 如「产品套餐 Q3」
    index_id = Column(Integer, nullable=False)    # FAISS 中的行号（0-based）
    active = Column(Boolean, default=True)        # 旧版本分块标记为 False
    created_at = Column(DateTime, default=now)

    document = relationship("Document", back_populates="chunks")


class Conversation(Base):
    """一次对话会话。status: active / transferred / closed。"""
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(16), default="active")
    ai_resolved = Column(Boolean, default=False)  # 是否由 AI 直接解决（未转人工）
    created_at = Column(DateTime, default=now)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan")
    ticket = relationship("Ticket", back_populates="conversation", uselist=False)


class Message(Base):
    """对话消息。sources 为来源引用（JSON 数组）。"""
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(16), nullable=False)      # user / assistant
    content = Column(Text, nullable=False)
    intent = Column(String(32), default="")
    confidence = Column(Float, default=0.0)
    sources = Column(JSON, default=list)           # [{doc_title, source_ref, score, text}]
    low_confidence = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

    conversation = relationship("Conversation", back_populates="messages")


class Ticket(Base):
    """工单。status: pending(待处理)/processing(处理中)/resolved(已解决)/closed(已关闭)。"""
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(256), default="")
    summary = Column(Text, default="")             # AI 生成的问题摘要
    priority = Column(String(16), default="medium")  # low/medium/high
    status = Column(String(16), default="pending")
    category = Column(String(64), default="")      # AI 聚类得到的类别（缺口分析用）
    satisfaction = Column(Integer, nullable=True)  # 1-5，解决后满意度
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    conversation = relationship("Conversation", back_populates="ticket")
    user = relationship("User", foreign_keys=[user_id])
    assignee = relationship("User", foreign_keys=[assignee_id])


class Feedback(Base):
    """对 AI 回答的点赞/点踩。"""
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    kind = Column(String(8), nullable=False)        # up / down
    created_at = Column(DateTime, default=now)


class Order(Base):
    """业务系统订单表（查订单意图调用的「业务系统」）。"""
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_no = Column(String(64), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    product = Column(String(128), default="")
    amount = Column(Float, default=0.0)
    status = Column(String(32), default="待发货")   # 待付款/待发货/已发货/已完成/已退款
    created_at = Column(DateTime, default=now)
