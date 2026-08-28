"""chromadb 向量库封装（持久化）。用 cosine 空间，向量+文本一起落盘，重启不丢。

向量 id 直接用分块主键 id 的字符串（str(Chunk.id)），检索后按 id 反查 DB 分块，
上层再用 active 字段过滤旧版本内容。为与 DB 保持一致，文档更新/删除时会同步删除
对应向量（delete()），不再靠「多取候选再过滤」这种内存态兜底。
"""
import threading

import chromadb
import numpy as np

from . import config

_client = None
_lock = threading.Lock()


def _get_client() -> chromadb.Client:
    """懒加载 PersistentClient（线程安全）。"""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return _client


def _get_collection():
    """取（或建）向量集合，cosine 空间。"""
    return _get_client().get_or_create_collection(
        name="kb_chunks",
        metadata={"hnsw:space": "cosine"},
    )


def reset():
    """清空向量库（重建索引时调用）。"""
    global _client
    try:
        _get_client().delete_collection("kb_chunks")
    except Exception:
        pass
    _client = None


def add_vectors(vectors: np.ndarray, ids: list[str],
                documents: list[str] | None = None,
                metadatas: list[dict] | None = None) -> list[str]:
    """把向量（连同文本/元数据）写入向量库。ids 为字符串 id 列表（str(Chunk.id)）。"""
    col = _get_collection()
    if not len(ids):
        return []
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    col.upsert(
        ids=list(ids),
        embeddings=vectors.astype("float32").tolist(),
        documents=list(documents) if documents is not None else None,
        metadatas=list(metadatas) if metadatas is not None else None,
    )
    return list(ids)


def delete(ids: list[str]):
    """按 id 删除向量（文档更新/删除时同步删除旧版本向量）。"""
    if not ids:
        return
    _get_collection().delete(ids=list(ids))


def search(query_vec: np.ndarray, top_k: int) -> tuple[list[str], list[float]]:
    """返回 (ids, scores)。ids 为字符串 id；scores 为余弦相似度（= 1 - cosine distance）。"""
    col = _get_collection()
    if col.count() == 0:
        return [], []
    q = np.asarray(query_vec, dtype="float32").reshape(1, -1).tolist()
    r = col.query(query_embeddings=q, n_results=min(top_k, col.count()))
    ids = r.get("ids", [[]])[0] if r.get("ids") else []
    distances = r.get("distances", [[]])[0] if r.get("distances") else []
    scores = [1.0 - float(d) for d in distances]
    return ids, scores


def size() -> int:
    return _get_collection().count()
