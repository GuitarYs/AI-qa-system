"""AI 聚类：embedding + KMeans（纯 numpy 实现，无额外依赖）+ LLM 生成类别标签。

用于「热门问题 Top10」和「知识库缺口分析」，结果可解释（每类有一个人话标签）。
"""
import numpy as np
from functools import lru_cache

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


def _label_clusters(groups: list[list[str]]) -> list[str]:
    """用一次 LLM 调用给所有簇批量起标签，减少串行调用次数（看板提速关键）。

    参数：groups —— 每个簇的成员问题列表（已分组）。
    返回：与 groups 等长的标签列表。
    """
    if not groups:
        return []
    # 每簇取前 6 条作为代表样本，拼成带编号的提示
    blocks = []
    for i, g in enumerate(groups, 1):
        blocks.append(f"第{i}组：\n" + "\n".join(f"- {s}" for s in g[:6]))
    joined = "\n\n".join(blocks)
    try:
        r = llm.chat_json([
            {"role": "system", "content": "你是数据分析助手。下面有若干组语义相近的客服问题，"
             "请给每组分别概括一个 2-8 字的中文短语（如「发票开具」「退款流程」「套餐价格」）。"
             '只输出 JSON：{"labels": ["标签1", "标签2", ...]}，labels 顺序必须与输入各组顺序一致。'},
            {"role": "user", "content": joined},
        ], temperature=0.0, max_tokens=300)
        labels = r.get("labels")
        if isinstance(labels, list) and len(labels) == len(groups):
            out = []
            for lab, g in zip(labels, groups):
                s = str(lab).strip()
                out.append(s if s else (g[0][:8] if g else "其他"))
            return out
    except Exception:
        pass
    # 兜底：用每组首条问题前 8 字
    return [g[0][:8] if g else "其他" for g in groups]


@lru_cache(maxsize=64)
def _cluster_cached(items: tuple[str, ...], max_k: int) -> list[dict]:
    """带缓存的聚类：相同问题集合 + max_k 直接复用结果，避免重复 embedding 和 LLM。"""
    vecs = embeddings.embed_texts(list(items))
    k = max(1, min(max_k, int(np.ceil(len(items) / 3))))
    labels = _kmeans(vecs, k)

    groups: dict[int, list[str]] = {}
    for item, lab in zip(items, labels):
        groups.setdefault(int(lab), []).append(item)
    ordered_groups = [groups[lab] for lab in sorted(groups)]

    # 一次 LLM 调用给所有簇起标签（原来是逐簇调用，很慢）
    cluster_labels = _label_clusters(ordered_groups)

    out = []
    for members, label in zip(ordered_groups, cluster_labels):
        out.append({"label": label, "count": len(members), "examples": members[:3]})
    out.sort(key=lambda x: -x["count"])
    return out


def cluster_and_label(items: list[str], max_k: int = 10) -> list[dict]:
    """把问题聚类并打标签，返回 [{label, count, examples}]，按数量降序。

    max_k 为最大簇数；簇数按数据量自适应。结果带缓存（相同输入直接复用）。
    """
    items = [s.strip() for s in items if s and s.strip()]
    if not items:
        return []
    return _cluster_cached(tuple(items), max_k)
