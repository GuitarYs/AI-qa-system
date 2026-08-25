"""嵌入封装。调用 DashScope text-embedding-v3（OpenAI 兼容接口），返回 L2 归一化向量。

归一化后向量内积 = 余弦相似度，与 FAISS IndexFlatIP 配合使用。
"""
import httpx
import numpy as np

from . import config


def _call_embed(texts: list[str]) -> list[list[float]]:
    if not config.EMBED_API_KEY:
        raise RuntimeError("缺少 DASHSCOPE_API_KEY，无法调用嵌入服务")
    r = httpx.post(
        f"{config.EMBED_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {config.EMBED_API_KEY}",
                 "Content-Type": "application/json"},
        json={"model": config.EMBED_MODEL, "input": texts,
              "dimensions": config.EMBED_DIM, "encoding_format": "float"},
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    # 按 input 顺序返回
    data = sorted(data["data"], key=lambda x: x["index"])
    return [d["embedding"] for d in data]


def _normalize(vecs: np.ndarray) -> np.ndarray:
    vecs = np.asarray(vecs, dtype="float32")
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def embed_texts(texts: list[str]) -> np.ndarray:
    """批量编码，返回归一化后的 float32 向量。"""
    if not texts:
        return np.zeros((0, config.EMBED_DIM), dtype="float32")
    # DashScope 单次最多 ~10 条文本，这里分批稳妥
    out = []
    batch = 10
    for i in range(0, len(texts), batch):
        out.extend(_call_embed(texts[i:i + batch]))
    return _normalize(np.array(out, dtype="float32"))


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text])[0]
