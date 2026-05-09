"""
Tool executor: backup → coerce params → call tool fn → return result.
"""
from pathlib import Path
from openpyxl import Workbook

from .tools._base import get_tool, validate_and_coerce
from .excel_io import backup_workbook


def execute_tool(
    tool_name: str,
    params: dict,
    wb: Workbook,
    workbook_path: str,
    mode: str,
    backups_dir: str | None = None,
) -> dict:
    """
    Execute a registered tool.

    Returns:
        {"success": True, "result": {...}, "backup_path": str|None}
        {"success": False, "error": str, "backup_path": str|None}
    """
    entry = get_tool(tool_name)
    if not entry:
        return {"success": False, "error": f"工具 '{tool_name}' 不存在", "backup_path": None}

    coerced, err = validate_and_coerce(tool_name, params)
    if err:
        return {"success": False, "error": err, "backup_path": None}

    backup_path: str | None = None
    if entry["modifies"] and backups_dir:
        try:
            backup_path = backup_workbook(workbook_path, tool_name, backups_dir)
        except Exception as e:
            return {"success": False, "error": f"備份失敗: {e}", "backup_path": None}

    try:
        result = entry["fn"](wb, **coerced)
    except Exception as e:
        return {"success": False, "error": _friendly_error(e), "backup_path": backup_path}

    if isinstance(result, dict) and "error" in result:
        return {"success": False, "error": result["error"], "backup_path": backup_path}

    return {"success": True, "result": result, "backup_path": backup_path}


def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if "KeyError" in type(exc).__name__:
        return f"欄位不存在: {msg}"
    if "ValueError" in type(exc).__name__:
        return f"數值錯誤: {msg}"
    return msg
