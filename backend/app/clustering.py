"""AI 聚类：embedding + KMeans（纯 numpy 实现，无额外依赖）+ LLM 生成类别标签。

用于「热门问题 Top10」和「知识库缺口分析」，结果可解释（每类有一个人话标签）。
"""
import numpy as np

from . import embeddings, llm


def _kmeans(vectors: np.ndarray, k: int, seed: int = 0, iters: int = 100) -> np.ndarray:
    """纯 numpy KMeans，返回每个样本的簇编号。"""
    n = len(vectors)
    if n == 0:
        return np.array([], dtype=int)
    k = max(1, min(k, n))
    rng = np.random.RandomState(seed)
    centers = vectors[rng.choice(n, size=k, replace=False)].copy()
    labels = np.zeros(n, dtype=int)
    for _ in range(iters):
        # 余弦相似度归簇（向量已归一化，用内积）
        sim = vectors @ centers.T
        new_labels = sim.argmax(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for j in range(k):
            members = vectors[labels == j]
            if len(members):
                centers[j] = members.mean(axis=0)
                centers[j] /= (np.linalg.norm(centers[j]) + 1e-8)
    return labels


def _label_cluster(items: list[str]) -> str:
    """用 LLM 为一个簇起一个简短、可解释的标签。"""
    sample = items[:6]
    joined = "\n".join(f"- {s}" for s in sample)
    try:
        r = llm.chat_json([
            {"role": "system", "content": "你是数据分析助手。下面是一组语义相近的客服问题，"
             "请用一个 2-8 字的中文短语概括这类问题（如「发票开具」「退款流程」「套餐价格」）。"
             '只输出 JSON：{"label": "..."}'},
            {"role": "user", "content": joined},
        ], temperature=0.0, max_tokens=60)
        label = r.get("label", "").strip()
        if label:
            return label
    except Exception:
        pass
    return items[0][:8] if items else "其他"


def cluster_and_label(items: list[str], max_k: int = 10) -> list[dict]:
    """把问题聚类并打标签，返回 [{label, count, examples}]，按数量降序。

    max_k 为最大簇数；簇数按数据量自适应。
    """
    items = [s.strip() for s in items if s and s.strip()]
    if not items:
        return []
    vecs = embeddings.embed_texts(items)
    k = max(1, min(max_k, int(np.ceil(len(items) / 3))))
    labels = _kmeans(vecs, k)

    groups: dict[int, list[str]] = {}
    for item, lab in zip(items, labels):
        groups.setdefault(int(lab), []).append(item)

    out = []
    for lab, members in groups.items():
        label = _label_cluster(members)
        out.append({"label": label, "count": len(members), "examples": members[:3]})
    out.sort(key=lambda x: -x["count"])
    return out
