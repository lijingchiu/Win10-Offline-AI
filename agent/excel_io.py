"""
Excel workbook I/O: xlwings (live) → openpyxl (file) fallback.
All tools receive an openpyxl Workbook; xlwings path reloads after save.
"""
import shutil
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl import Workbook


def open_workbook(path: str, prefer_live: bool = True) -> tuple[Workbook, str]:
    """
    Return (openpyxl_wb, mode).  mode is "xlwings" or "openpyxl".
    xlwings mode is used only when the exact file is already open in Excel.
    """
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"找不到檔案：{resolved}")

    if prefer_live:
        try:
            import xlwings as xw
            for app in xw.apps:
                for book in app.books:
                    try:
                        if Path(book.fullname).resolve() == resolved:
                            # File is open in Excel — save a temp copy to read with openpyxl
                            book.save()
                            wb = openpyxl.load_workbook(str(resolved))
                            return wb, "xlwings"
                    except Exception:
                        continue
        except ImportError:
            pass
        except Exception:
            pass

    wb = openpyxl.load_workbook(str(resolved))
    return wb, "openpyxl"


def save_workbook(wb: Workbook, path: str, mode: str) -> None:
    """Save workbook. If xlwings mode, reload the saved file in Excel."""
    wb.save(str(path))
    if mode == "xlwings":
        try:
            import xlwings as xw
            resolved = Path(path).resolve()
            for app in xw.apps:
                for book in app.books:
                    try:
                        if Path(book.fullname).resolve() == resolved:
                            book.close()
                            xw.Book(str(resolved))
                            return
                    except Exception:
                        continue
        except Exception:
            pass


def backup_workbook(path: str, tool_name: str, backups_dir: str) -> str:
    """
    Copy workbook to backups_dir/<YYYY-MM-DD>/<stem>_<HHMMSS>_before_<tool>.xlsx.
    Returns the backup path string.
    """
    src = Path(path)
    now = datetime.now()
    date_dir = Path(backups_dir) / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    ts = now.strftime("%H%M%S")
    dst = date_dir / f"{src.stem}_{ts}_before_{tool_name}{src.suffix}"
    shutil.copy2(src, dst)
    return str(dst)


def get_wb_info(wb: Workbook, filename: str) -> dict:
    """Return a dict describing the workbook (for prompt injection)."""
    info: dict = {"filename": filename, "sheet_names": wb.sheetnames}
    if not wb.sheetnames:
        return info
    ws = wb[wb.sheetnames[0]]
    headers = []
    for cell in next(ws.iter_rows(max_row=1), []):
        if cell.value is not None:
            headers.append(str(cell.value))
    info["active_sheet"] = wb.sheetnames[0]
    info["columns"]      = headers
    info["row_count"]    = max(0, (ws.max_row or 1) - 1)
    return info
