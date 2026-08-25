"""知识库管理：文档 CRUD + 分块 + 向量化入库 + 版本管理。"""
from sqlalchemy.orm import Session

from . import chunking, embeddings, vector_store
from .models import Document, DocumentVersion, Chunk


def _index_chunks(db: Session, doc: Document, content: str, version: int):
    """把文档内容分块、向量化、写入 FAISS，并在 DB 记录分块。"""
    blocks = chunking.chunk_markdown(content)
    if not blocks:
        return
    texts = [b["text"] for b in blocks]
    vecs = embeddings.embed_texts(texts)
    index_ids = vector_store.add_vectors(vecs)
    for b, idx in zip(blocks, index_ids):
        db.add(Chunk(document_id=doc.id, version=version, chunk_index=0,
                     text=b["text"], source_ref=b["source_ref"],
                     index_id=idx, active=True))
    db.commit()


def rebuild_index(db: Session):
    """从 DB 中所有 active 分块重建 FAISS 索引（启动时调用，保证索引与 DB 一致）。"""
    chunks = db.query(Chunk).filter(Chunk.active.is_(True)).order_by(Chunk.id).all()
    vector_store.reset()
    if not chunks:
        return
    texts = [c.text for c in chunks]
    vecs = embeddings.embed_texts(texts)
    index_ids = vector_store.add_vectors(vecs)
    for c, idx in zip(chunks, index_ids):
        c.index_id = idx
    db.commit()


def create_document(db: Session, title: str, category: str, content: str, note: str = "") -> Document:
    doc = Document(title=title, category=category, content=content,
                   current_version=1)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.add(DocumentVersion(document_id=doc.id, version=1, content=content, note=note))
    db.commit()
    _index_chunks(db, doc, content, version=1)
    return doc


def update_document(db: Session, doc: Document, title=None, category=None,
                    content=None, note="") -> Document:
    """更新文档：新增一个版本，旧分块标记失效，新分块入库。"""
    new_version = doc.current_version + 1
    if title is not None:
        doc.title = title
    if category is not None:
        doc.category = category
    if content is not None and content != doc.content:
        # 旧分块失效
        for c in doc.chunks:
            if c.active:
                c.active = False
        db.commit()
        doc.content = content
        doc.current_version = new_version
        db.add(DocumentVersion(document_id=doc.id, version=new_version,
                               content=content, note=note))
        db.commit()
        _index_chunks(db, doc, content, version=new_version)
    else:
        # 仅标题/分类变化，直接落库（updated_at 由 onupdate 自动刷新）
        db.commit()
    return doc


def delete_document(db: Session, doc: Document):
    for c in doc.chunks:
        c.active = False
    db.commit()
    db.delete(doc)
    db.commit()


def restore_version(db: Session, doc: Document, version: int) -> Document:
    """回滚到某个历史版本（本质是新增一个「回到 v」的版本）。"""
    v = (db.query(DocumentVersion)
         .filter(DocumentVersion.document_id == doc.id,
                 DocumentVersion.version == version).first())
    if v is None:
        raise ValueError("版本不存在")
    return update_document(db, doc, content=v.content,
                           note=f"回滚到版本 v{version}")


def doc_to_dict(doc: Document, include_versions=False) -> dict:
    d = {
        "id": doc.id,
        "title": doc.title,
        "category": doc.category,
        "content": doc.content,
        "current_version": doc.current_version,
        "chunk_count": sum(1 for c in doc.chunks if c.active),
        "created_at": doc.created_at.isoformat() if doc.created_at else "",
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else "",
    }
    if include_versions:
        d["versions"] = [{
            "version": v.version,
            "note": v.note,
            "content": v.content,
            "created_at": v.created_at.isoformat() if v.created_at else "",
        } for v in sorted(doc.versions, key=lambda x: x.version, reverse=True)]
    return d
