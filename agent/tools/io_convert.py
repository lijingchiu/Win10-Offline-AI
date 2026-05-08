"""匯入匯出工具 (4 個函式)"""
import csv
import io
import pandas as pd
from ._base import tool
from .cleaning import _ws_to_df, _df_to_ws
from .pivot import _write_df_to_new_sheet


@tool(
    name_zh="CSV 匯入為工作表",
    desc_zh="將 CSV 格式的文字內容匯入工作簿，建立新工作表",
    desc_en="csv import sheet upload text comma separated",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":       {"type": "string", "description": "資料所在工作表"},
            "csv_content": {"type": "string", "description": "CSV 格式的文字（含表頭）"},
            "sheet_name":  {"type": "string", "default": "CSV匯入", "description": "新工作表名稱"},
            "encoding":    {"type": "string", "default": "utf-8", "description": "編碼"},
            "delimiter":   {"type": "string", "default": ",", "description": "分隔符號"},
        },
        "required": ["csv_content"],
    },
    confirm=False,
    modifies=True,
)
def csv_to_sheet(wb, *, sheet: str = "", csv_content: str, sheet_name: str = "CSV匯入", encoding: str = "utf-8", delimiter: str = ",") -> dict:
    try:
        df = pd.read_csv(io.StringIO(csv_content), sep=delimiter)
    except Exception as e:
        return {"error": f"CSV 解析失敗: {e}"}
    _write_df_to_new_sheet(wb, df, sheet_name)
    return {"message": f"CSV 已匯入工作表「{sheet_name}」（{len(df)} 列 × {len(df.columns)} 欄）", "new_sheet": sheet_name, "rows": len(df)}


@tool(
    name_zh="工作表匯出 CSV",
    desc_zh="將指定工作表匯出為 CSV 格式，回傳 CSV 文字內容",
    desc_en="export csv download sheet convert",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":     {"type": "string", "description": "要匯出的工作表名稱"},
            "delimiter": {"type": "string", "default": ",", "description": "分隔符號"},
        },
        "required": [],
    },
    confirm=False,
    modifies=False,
)
def sheet_to_csv(wb, *, sheet: str = "", delimiter: str = ",") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    buf = io.StringIO()
    df.to_csv(buf, index=False, sep=delimiter)
    csv_text = buf.getvalue()
    sheet_name = sheet or wb.sheetnames[0]
    return {
        "message": f"工作表「{sheet_name}」已轉換為 CSV（{len(df)} 列），可由下方下載",
        "csv_content": csv_text,
        "export_type": "csv",
        "filename": f"{sheet_name}.csv",
    }


@tool(
    name_zh="合併多個工作表",
    desc_zh="將多個工作表的資料縱向合併為一個新工作表（欄位需一致）",
    desc_en="merge combine multiple sheets append stack union",
    params_schema={
        "type": "object",
        "properties": {
            "sheets":    {"type": "array",  "items": {"type": "string"}, "description": "要合併的工作表名稱清單，留空則合併全部"},
            "new_sheet": {"type": "string", "default": "合併", "description": "結果工作表名稱"},
            "add_source_column": {"type": "boolean", "default": False, "description": "是否新增「來源工作表」欄"},
        },
        "required": [],
    },
    confirm=False,
    modifies=True,
)
def merge_multiple_sheets(wb, *, sheets: list = None, new_sheet: str = "合併", add_source_column: bool = False) -> dict:
    target_sheets = sheets if sheets else wb.sheetnames
    bad = [s for s in target_sheets if s not in wb.sheetnames]
    if bad:
        return {"error": f"工作表不存在: {bad}"}
    if new_sheet in target_sheets:
        target_sheets = [s for s in target_sheets if s != new_sheet]
    dfs = []
    for s in target_sheets:
        try:
            _, df, _ = _ws_to_df(wb, s)
            if add_source_column:
                df.insert(0, "來源工作表", s)
            dfs.append(df)
        except Exception as e:
            return {"error": f"讀取「{s}」失敗: {e}"}
    if not dfs:
        return {"error": "沒有可合併的工作表"}
    merged = pd.concat(dfs, ignore_index=True)
    _write_df_to_new_sheet(wb, merged, new_sheet)
    return {"message": f"已合併 {len(target_sheets)} 個工作表為「{new_sheet}」（共 {len(merged)} 列）", "new_sheet": new_sheet, "total_rows": len(merged)}


@tool(
    name_zh="依欄位拆分工作表",
    desc_zh="依指定欄位的唯一值將工作表拆分為多個子工作表",
    desc_en="split sheet by column value partition separate sheets",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":  {"type": "string", "description": "要拆分的工作表名稱"},
            "column": {"type": "string", "description": "拆分依據欄位"},
            "prefix": {"type": "string", "default": "", "description": "新工作表名稱前綴"},
        },
        "required": ["column"],
    },
    confirm=True,
    modifies=True,
)
def split_sheet_by_column(wb, *, sheet: str = "", column: str, prefix: str = "") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    if column not in df.columns:
        return {"error": f"欄位「{column}」不存在，可用: {list(df.columns)}"}
    unique_vals = df[column].dropna().unique()
    if len(unique_vals) > 30:
        return {"error": f"「{column}」欄有 {len(unique_vals)} 個唯一值（上限 30），請先篩選或換一個欄位"}
    created = []
    for val in unique_vals:
        sub_df = df[df[column] == val].reset_index(drop=True)
        sheet_name = f"{prefix}{str(val)}"[:31]  # Excel sheet name limit
        _write_df_to_new_sheet(wb, sub_df, sheet_name)
        created.append(sheet_name)
    return {"message": f"已依「{column}」拆分為 {len(created)} 個工作表：{created[:5]}{'…' if len(created)>5 else ''}", "sheets_created": created}
