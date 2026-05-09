"""
Tool registry + @tool decorator.
All tool modules use @tool to self-register at import time.
"""
import functools
from typing import Any, Callable

_REGISTRY: dict[str, dict] = {}


def tool(
    *,
    name_zh: str,
    desc_zh: str,
    desc_en: str,
    params_schema: dict,
    confirm: bool = False,
    modifies: bool = True,
) -> Callable:
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[fn.__name__] = {
            "name":          fn.__name__,
            "name_zh":       name_zh,
            "desc_zh":       desc_zh,
            "desc_en":       desc_en,
            "params_schema": params_schema,
            "confirm":       confirm,
            "modifies":      modifies,
            "fn":            fn,
        }
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_tool(name: str) -> dict | None:
    return _REGISTRY.get(name)


def all_tools() -> list[dict]:
    return list(_REGISTRY.values())


def _coerce_params(params: dict, schema: dict) -> dict:
    """Best-effort type coercion so string-typed LLM outputs match expected types."""
    props = schema.get("properties", {})
    out = {}
    for key, value in params.items():
        if value is None or key not in props:
            out[key] = value
            continue
        expected = props[key].get("type")
        try:
            if expected == "integer" and not isinstance(value, int):
                out[key] = int(value)
            elif expected == "number" and not isinstance(value, (int, float)):
                out[key] = float(value)
            elif expected == "boolean" and not isinstance(value, bool):
                out[key] = str(value).lower() in ("true", "1", "yes")
            elif expected == "array" and isinstance(value, str):
                out[key] = [v.strip() for v in value.split(",") if v.strip()]
            else:
                out[key] = value
        except (ValueError, TypeError):
            out[key] = value
    return out


def validate_and_coerce(tool_name: str, params: dict) -> tuple[dict, str]:
    """Validate + coerce params. Returns (coerced_params, error_msg)."""
    entry = _REGISTRY.get(tool_name)
    if not entry:
        return params, f"工具 '{tool_name}' 不存在"
    schema = entry["params_schema"]
    coerced = _coerce_params(params, schema)
    required = schema.get("required", [])
    for key in required:
        if key not in coerced or coerced[key] is None:
            return coerced, f"缺少必要參數: '{key}'"
    return coerced, ""
