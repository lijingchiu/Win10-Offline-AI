"""
Ollama /api/chat wrapper with JSON-mode and json_repair fallback.
"""
import json
import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DEFAULT_MODEL = "qwen2.5:7b"
TIMEOUT = 120


def chat(
    messages: list[dict],
    model: str | None = None,
    num_ctx: int = 2048,
    fmt: str = "json",
) -> dict:
    """
    Call Ollama and return the parsed JSON response dict.
    Raises RuntimeError on network error or unparseable response.
    """
    payload: dict = {
        "model":   model or DEFAULT_MODEL,
        "messages": messages,
        "stream":  False,
        "options": {"num_ctx": num_ctx},
    }
    if fmt == "json":
        payload["format"] = "json"

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Ollama 連線失敗: {e}")

    content: str = resp.json().get("message", {}).get("content", "")

    # First attempt: direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Second attempt: json_repair
    try:
        from json_repair import repair_json
        repaired = repair_json(content)
        return json.loads(repaired)
    except Exception:
        pass

    raise RuntimeError(f"無法解析 LLM 回應為 JSON: {content[:200]}")


def list_models() -> list[str]:
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []
