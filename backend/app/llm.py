"""LLM 客户端（DeepSeek，OpenAI 兼容接口）。所有 AI 能力（生成/意图/聚类标签/摘要/建议回复）都走这里，真连 LLM，禁止 mock。"""
import json

import httpx

from . import config


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }


def chat(messages: list[dict], temperature: float | None = None,
         max_tokens: int = 1024, json_mode: bool = False) -> str:
    """调用 LLM，返回文本内容。json_mode=True 时要求模型只输出 JSON。"""
    if not config.LLM_API_KEY:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法调用 LLM")
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "temperature": config.LLM_TEMPERATURE if temperature is None else temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    r = httpx.post(
        f"{config.LLM_BASE_URL}/chat/completions",
        headers=_headers(), json=payload, timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


def chat_json(messages: list[dict], temperature: float | None = None,
              max_tokens: int = 1024) -> dict:
    """调用 LLM 并解析 JSON，失败时返回空 dict（上层有兜底）。"""
    raw = chat(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)
    try:
        # 剥离可能的 ```json ... ``` 包裹
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw[raw.find("{"):]
        return json.loads(raw)
    except Exception:
        # 尝试截取第一个 { 到最后一个 }
        try:
            return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        except Exception:
            return {}
