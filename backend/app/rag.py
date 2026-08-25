"""RAG 检索：query 向量化 → FAISS 召回 → 按 active 分块过滤 → 返回带来源的候选。"""
from sqlalchemy.orm import Session

from . import config, embeddings, vector_store
from .models import Chunk, Document


def retrieve(db: Session, query: str, top_k: int | None = None):
    """返回 [{'chunk_id', 'doc_id', 'doc_title', 'source_ref', 'text', 'score'}]。

    先取 top_k*3 的候选再在 Python 侧过滤掉已失效（旧版本）分块，
    最后取 top_k 个，保证版本更新后旧内容不会混入结果。
    """
    top_k = top_k or config.RAG_TOP_K
    q_vec = embeddings.embed_query(query)
    candidate_k = max(top_k * 3 + 5, 20)
    ids, scores = vector_store.search(q_vec, candidate_k)
    if not ids:
        return []

    # 一次查出所有候选分块及其所属文档
    chunks = db.query(Chunk).filter(Chunk.index_id.in_(ids)).all()
    chunk_by_idx = {c.index_id: c for c in chunks}
    doc_ids = {c.document_id for c in chunks}
    docs = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}

    results = []
    for idx, score in zip(ids, scores):
        c = chunk_by_idx.get(idx)
        if c is None or not c.active:
            continue  # 旧版本分块，跳过
        doc = docs.get(c.document_id)
        if doc is None:
            continue
        results.append({
            "chunk_id": c.id,
            "doc_id": doc.id,
            "doc_title": doc.title,
            "source_ref": c.source_ref,
            "text": c.text,
            "score": round(float(score), 4),
        })
        if len(results) >= top_k:
            break
    return results
