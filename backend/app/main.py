"""FastAPI 入口：API 路由 + 静态前端托管 + 启动播种。"""
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import config, chat_service, kb_service, ticket_service, dashboard_service
from .db import Base, engine, SessionLocal, get_db
from .models import User, Conversation, Message, Ticket, Document, DocumentVersion, Chunk
from . import schemas, vector_store

app = FastAPI(title="云作 Cloudwork · AI 全栈客服系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _migrate():
    """轻量迁移：为旧库补齐新增列（SQLite 的 ALTER TABLE ADD COLUMN）。"""
    from sqlalchemy import text
    with engine.begin() as conn:
        # tickets.resolution：人工客服处理意见（后加功能，老库补列）
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(tickets)"))]
        if "resolution" not in cols:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN resolution TEXT DEFAULT ''"))


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _migrate()
    from . import seed
    db = SessionLocal()
    try:
        seed.seed_all(db)
        # chroma 向量库已持久化，正常重启无需重建；仅当向量库与 DB 有效分块数不一致
        # （如首次迁移、向量库被删）时才从 DB 重建。网络异常时重建失败不阻塞启动。
        active_count = db.query(Chunk).filter(Chunk.active.is_(True)).count()
        if vector_store.size() != active_count:
            try:
                kb_service.rebuild_index(db)
            except Exception as e:
                print(f"[startup] 重建向量索引失败（可能网络不可用）：{e}")
    finally:
        db.close()


# ---------- 健康检查 ----------
@app.get("/api/health")
def health():
    return {"ok": True, "llm_model": config.LLM_MODEL,
            "llm_ready": bool(config.LLM_API_KEY),
            "embed_ready": bool(config.EMBED_API_KEY)}


# ---------- 对话 ----------
@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    return chat_service.handle_chat(db, req.user_id, req.message, req.conversation_id)


@app.get("/api/conversations/{conv_id}/messages")
def conversation_messages(conv_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if conv is None:
        raise HTTPException(404, "会话不存在")
    msgs = (db.query(Message).filter(Message.conversation_id == conv_id)
            .order_by(Message.id).all())
    return {
        "conversation_id": conv_id,
        "status": conv.status,
        "messages": [{
            "id": m.id, "role": m.role, "content": m.content,
            "intent": m.intent, "confidence": m.confidence,
            "low_confidence": m.low_confidence, "sources": m.sources,
            "created_at": m.created_at.isoformat() if m.created_at else "",
        } for m in msgs],
    }


@app.post("/api/feedback")
def feedback(req: schemas.FeedbackRequest, db: Session = Depends(get_db)):
    from .models import Feedback
    fb = Feedback(message_id=req.message_id,
                  conversation_id=req.conversation_id, kind=req.kind)
    db.add(fb)
    db.commit()
    return {"ok": True}


# ---------- 知识库 ----------
@app.get("/api/kb/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.id).all()
    return [kb_service.doc_to_dict(d) for d in docs]


@app.post("/api/kb/documents")
def create_document(req: schemas.DocCreate, db: Session = Depends(get_db)):
    doc = kb_service.create_document(db, req.title, req.category, req.content, req.note)
    return kb_service.doc_to_dict(doc, include_versions=True)


@app.get("/api/kb/documents/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None:
        raise HTTPException(404, "文档不存在")
    return kb_service.doc_to_dict(doc, include_versions=True)


@app.put("/api/kb/documents/{doc_id}")
def update_document(doc_id: int, req: schemas.DocUpdate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None:
        raise HTTPException(404, "文档不存在")
    doc = kb_service.update_document(db, doc, title=req.title, category=req.category,
                                     content=req.content, note=req.note)
    return kb_service.doc_to_dict(doc, include_versions=True)


@app.delete("/api/kb/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None:
        raise HTTPException(404, "文档不存在")
    kb_service.delete_document(db, doc)
    return {"ok": True}


@app.post("/api/kb/documents/{doc_id}/restore")
def restore_document(doc_id: int, version: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None:
        raise HTTPException(404, "文档不存在")
    doc = kb_service.restore_version(db, doc, version)
    return kb_service.doc_to_dict(doc, include_versions=True)


def _extract_pdf_text(raw: bytes) -> str:
    """提取 PDF 正文：把 PDF 各页文本拼成纯文本返回，供后续与 .md/.txt 一样分块入库。"""
    try:
        from pypdf import PdfReader  # 延迟导入，避免未安装 pypdf 时影响其他功能启动
        reader = PdfReader(BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as e:
        print(f"[kb] PDF 文本提取失败：{e}")
        return ""


@app.post("/api/kb/upload")
async def upload_document(file: UploadFile = File(...),
                          category: str = Form("FAQ"),
                          db: Session = Depends(get_db)):
    raw = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix == ".pdf":
        content = _extract_pdf_text(raw)
        if not content:
            raise HTTPException(400, "PDF 无法提取到文本内容（可能是扫描件或加密文档）")
    else:
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("gbk", errors="ignore")
    title = Path(file.filename).stem
    doc = kb_service.create_document(db, title, category, content, note="上传文档")
    return kb_service.doc_to_dict(doc, include_versions=True)


# ---------- 工单 ----------
@app.get("/api/tickets")
def list_tickets(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).order_by(Ticket.id.desc()).all()
    return [ticket_service.ticket_to_dict(t) for t in tickets]


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if t is None:
        raise HTTPException(404, "工单不存在")
    data = ticket_service.ticket_to_dict(t)
    data["history"] = ticket_service.get_conversation_history(db, t.conversation_id or 0)
    return data


@app.put("/api/tickets/{ticket_id}/assign")
def assign_ticket(ticket_id: int, req: schemas.TicketAssign, db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if t is None:
        raise HTTPException(404, "工单不存在")
    t.assignee_id = req.assignee_id
    if t.status == "pending":
        t.status = "processing"
    db.commit()
    return ticket_service.ticket_to_dict(t)


@app.put("/api/tickets/{ticket_id}/status")
def update_status(ticket_id: int, req: schemas.TicketStatus, db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if t is None:
        raise HTTPException(404, "工单不存在")
    t.status = req.status
    db.commit()
    return ticket_service.ticket_to_dict(t)


@app.post("/api/tickets/{ticket_id}/suggest")
def suggest(ticket_id: int, db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if t is None:
        raise HTTPException(404, "工单不存在")
    return {"suggestion": ticket_service.suggest_reply(db, t)}


@app.post("/api/tickets/{ticket_id}/satisfaction")
def set_satisfaction(ticket_id: int, req: schemas.TicketSatisfaction,
                     db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if t is None:
        raise HTTPException(404, "工单不存在")
    t.satisfaction = req.satisfaction
    t.status = "closed"
    db.commit()
    return ticket_service.ticket_to_dict(t)


@app.put("/api/tickets/{ticket_id}/resolution")
def save_resolution(ticket_id: int, req: schemas.TicketResolution,
                    db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if t is None:
        raise HTTPException(404, "工单不存在")
    t.resolution = req.resolution
    db.commit()
    return ticket_service.ticket_to_dict(t)


# ---------- 用户 ----------
@app.get("/api/users")
def list_users(db: Session = Depends(get_db)):
    return [{"id": u.id, "name": u.name, "role": u.role, "email": u.email}
            for u in db.query(User).order_by(User.id).all()]


# ---------- 看板 ----------
@app.get("/api/dashboard")
def dashboard(start: str | None = None, end: str | None = None,
              db: Session = Depends(get_db)):
    return dashboard_service.get_dashboard(db, start, end)


# ---------- 静态前端 ----------
_FRONTEND_DIST = config.BASE_DIR / "frontend" / "dist"


@app.get("/")
def index():
    if (_FRONTEND_DIST / "index.html").exists():
        return FileResponse(_FRONTEND_DIST / "index.html")
    return {"msg": "前端未构建。请运行 cd frontend && npm run build，或访问 /docs 查看 API。"}


# 兜底：SPA 其余路径 + 静态资源
if (_FRONTEND_DIST).exists():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")
