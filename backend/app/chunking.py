"""知识库分块。

种子知识库是标准 FAQ 格式（Q1：… / Q2：…），每条 Q&A 天然是语义完整的一块，
按 Q 切分能保证「来源引用」精确到某一条（如「产品套餐 Q3」）。
对于非 FAQ 格式的文档，回退到按标题/段落切分。
"""
import re

# 匹配「Q1：」「Q12：」等（全角/半角冒号都兼容）
_Q_RE = re.compile(r"^Q\s*(\d+)\s*[：:]", re.MULTILINE)
_HEADING_RE = re.compile(r"^(#{1,6}\s+.*|.*·.*)$", re.MULTILINE)


def _split_faq(content: str) -> list[tuple[str, str, str]]:
    """把 FAQ 文本切成 (q_no, section, text) 列表。text 含问题+答案。"""
    matches = list(_Q_RE.finditer(content))
    if not matches:
        return []

    # 记录每个 Q 之前的最近章节标题
    headings = list(_HEADING_RE.finditer(content))

    def section_before(pos: int) -> str:
        sec = ""
        for h in headings:
            if h.start() < pos:
                sec = h.group(1).strip().lstrip("#").strip()
            else:
                break
        return sec

    blocks = []
    for i, m in enumerate(matches):
        q_no = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        text = content[start:end].strip()
        sec = section_before(start)
        blocks.append((q_no, sec, text))
    return blocks


def chunk_markdown(content: str) -> list[dict]:
    """返回 [{'text', 'source_ref'}]。source_ref 为段号（如「Q3」「段1」），文档名由上层单独标注。"""
    result = []
    faq_blocks = _split_faq(content)
    if faq_blocks:
        for q_no, sec, text in faq_blocks:
            if sec and sec not in text[:20]:
                text = f"[{sec}]\n{text}"
            result.append({"text": text, "source_ref": f"Q{q_no}"})
        return result

    # 回退：按标题/段落切分
    parts = re.split(r"\n(?=#{1,6}\s)", content)
    idx = 0
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) > 800:  # 超长段落按长度硬切
            for i in range(0, len(p), 800):
                idx += 1
                result.append({"text": p[i:i + 800], "source_ref": f"段{idx}"})
        else:
            idx += 1
            result.append({"text": p, "source_ref": f"段{idx}"})
    return result
