"""FAISS 向量库封装（内存态）。用 IndexFlatIP（内积）+ 归一化向量实现余弦相似度检索。

索引内行号与 Chunk.index_id 一一对应。为规避 Windows 下 FAISS 写盘对非 ASCII 路径的
兼容问题，索引不落盘，改为「启动时从 DB 分块重建」；文档更新时旧分块在 DB 中标记
active=False，检索多取候选再由上层按 active 过滤，即可正确实现版本更新后旧内容不再被召回。
"""
import threading

import faiss
import numpy as np

from . import config

_index = None
_lock = threading.Lock()


def _get_index() -> faiss.IndexFlatIP:
    global _index
    if _index is None:
        with _lock:
            if _index is None:
                _index = faiss.IndexFlatIP(config.EMBED_DIM)
    return _index


def reset():
    """清空索引（重建时调用）。"""
    global _index
    with _lock:
        _index = faiss.IndexFlatIP(config.EMBED_DIM)


def add_vectors(vectors: np.ndarray) -> list[int]:
    """把向量加入索引，返回每个向量在索引中的行号（即 Chunk.index_id）。"""
    idx = _get_index()
    start = idx.ntotal
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    idx.add(vectors.astype("float32"))
    return list(range(start, start + len(vectors)))


def search(query_vec: np.ndarray, top_k: int) -> tuple[list[int], list[float]]:
    """返回 (index_ids, scores)。scores 为余弦相似度（归一化后内积，[-1,1]）。"""
    idx = _get_index()
    if idx.ntotal == 0:
        return [], []
    q = np.asarray(query_vec, dtype="float32").reshape(1, -1)
    scores, ids = idx.search(q, min(top_k, idx.ntotal))
    return ids[0].tolist(), scores[0].tolist()


def size() -> int:
    return _get_index().ntotal
