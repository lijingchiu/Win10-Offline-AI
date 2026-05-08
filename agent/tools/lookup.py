"""查找比對工具 (4 個函式)"""
import difflib
import pandas as pd
from ._base import tool
from .cleaning import _ws_to_df, _df_to_ws
from .pivot import _write_df_to_new_sheet


@tool(
    name_zh="VLOOKUP 比對合併",
    desc_zh="從另一個工作表依索引欄查找並帶回指定欄位值（等同 VLOOKUP）",
    desc_en="vlookup lookup index match join merge sheets key column",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":            {"type": "string", "description": "要加入資料的工作表（目標表）"},
            "key_column":       {"type": "string", "description": "目標表的索引鍵欄位"},
            "lookup_sheet":     {"type": "string", "description": "查找資料來源的工作表"},
            "lookup_key":       {"type": "string", "description": "來源表的索引鍵欄位"},
            "lookup_value":     {"type": "string", "description": "要帶回的欄位"},
            "new_column_name":  {"type": "string", "default": "", "description": "新欄位名稱（留空用 lookup_value 名稱）"},
            "if_not_found":     {"type": "string", "default": "", "description": "找不到時填入的值"},
        },
        "required": ["key_column", "lookup_sheet", "lookup_key", "lookup_value"],
    },
    confirm=False,
    modifies=True,
)
def vlookup_equivalent(wb, *, sheet: str = "", key_column: str, lookup_sheet: str, lookup_key: str, lookup_value: str, new_column_name: str = "", if_not_found: str = "") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    if key_column not in df.columns:
        return {"error": f"目標表欄位「{key_column}」不存在，可用: {list(df.columns)}"}
    if lookup_sheet not in wb.sheetnames:
        return {"error": f"來源工作表「{lookup_sheet}」不存在，可用: {wb.sheetnames}"}
    _, ldf, _ = _ws_to_df(wb, lookup_sheet)
    if lookup_key not in ldf.columns:
        return {"error": f"來源表欄位「{lookup_key}」不存在，可用: {list(ldf.columns)}"}
    if lookup_value not in ldf.columns:
        return {"error": f"來源表欄位「{lookup_value}」不存在，可用: {list(ldf.columns)}"}
    lookup_map = dict(zip(ldf[lookup_key].astype(str), ldf[lookup_value]))
    col_name = new_column_name or lookup_value
    df[col_name] = df[key_column].astype(str).map(lookup_map).fillna(if_not_found)
    matched = df[col_name].notna().sum() if if_not_found == "" else (df[col_name] != if_not_found).sum()
    _df_to_ws(ws, df)
    return {"message": f"已帶入「{col_name}」欄，{matched}/{len(df)} 筆成功比對", "matched": int(matched), "total": len(df)}


@tool(
    name_zh="跨表比對",
    desc_zh="比較兩個工作表，依索引鍵找出相同、差異、只在一邊的列，結果存新工作表",
    desc_en="compare two sheets diff difference cross sheet match",
    params_schema={
        "type": "object",
        "properties": {
            "sheet1":     {"type": "string", "description": "第一個工作表"},
            "sheet2":     {"type": "string", "description": "第二個工作表"},
            "key_column": {"type": "string", "description": "比對用的索引鍵欄位"},
            "new_sheet":  {"type": "string", "default": "比對結果", "description": "結果工作表名稱"},
        },
        "required": ["sheet1", "sheet2", "key_column"],
    },
    confirm=False,
    modifies=True,
)
def cross_sheet_compare(wb, *, sheet1: str, sheet2: str, key_column: str, new_sheet: str = "比對結果") -> dict:
    for s in [sheet1, sheet2]:
        if s not in wb.sheetnames:
            return {"error": f"工作表「{s}」不存在，可用: {wb.sheetnames}"}
    _, df1, _ = _ws_to_df(wb, sheet1)
    _, df2, _ = _ws_to_df(wb, sheet2)
    for df, s in [(df1, sheet1), (df2, sheet2)]:
        if key_column not in df.columns:
            return {"error": f"工作表「{s}」缺少欄位「{key_column}」，可用: {list(df.columns)}"}
    keys1 = set(df1[key_column].astype(str))
    keys2 = set(df2[key_column].astype(str))
    only1 = sorted(keys1 - keys2)
    only2 = sorted(keys2 - keys1)
    common = sorted(keys1 & keys2)
    rows = (
        [{"狀態": f"只在{sheet1}", key_column: k} for k in only1] +
        [{"狀態": f"只在{sheet2}", key_column: k} for k in only2] +
        [{"狀態": "兩表都有",      key_column: k} for k in common]
    )
    result_df = pd.DataFrame(rows)
    _write_df_to_new_sheet(wb, result_df, new_sheet)
    return {
        "message": (
            f"比對完成 → 只在{sheet1}: {len(only1)} 筆，"
            f"只在{sheet2}: {len(only2)} 筆，"
            f"兩表共有: {len(common)} 筆。結果在「{new_sheet}」"
        ),
        "only_in_sheet1": len(only1),
        "only_in_sheet2": len(only2),
        "common": len(common),
        "new_sheet": new_sheet,
    }


@tool(
    name_zh="找差異列",
    desc_zh="找出在一個工作表中存在但另一個工作表中不存在的列（不修改檔案）",
    desc_en="find difference rows missing absent one sheet not other",
    params_schema={
        "type": "object",
        "properties": {
            "sheet1":     {"type": "string", "description": "第一個工作表"},
            "sheet2":     {"type": "string", "description": "第二個工作表"},
            "key_column": {"type": "string", "description": "比對用的索引鍵欄位"},
        },
        "required": ["sheet1", "sheet2", "key_column"],
    },
    confirm=False,
    modifies=False,
)
def find_diff_between_sheets(wb, *, sheet1: str, sheet2: str, key_column: str) -> dict:
    for s in [sheet1, sheet2]:
        if s not in wb.sheetnames:
            return {"error": f"工作表「{s}」不存在"}
    _, df1, _ = _ws_to_df(wb, sheet1)
    _, df2, _ = _ws_to_df(wb, sheet2)
    for df, s in [(df1, sheet1), (df2, sheet2)]:
        if key_column not in df.columns:
            return {"error": f"「{s}」缺少欄位「{key_column}」"}
    keys1 = set(df1[key_column].astype(str))
    keys2 = set(df2[key_column].astype(str))
    only1 = sorted(keys1 - keys2)
    only2 = sorted(keys2 - keys1)
    preview1 = only1[:10]
    preview2 = only2[:10]
    lines = [
        f"只在「{sheet1}」({len(only1)} 筆): {preview1}{'…' if len(only1)>10 else ''}",
        f"只在「{sheet2}」({len(only2)} 筆): {preview2}{'…' if len(only2)>10 else ''}",
    ]
    return {"message": "\n".join(lines), "only_in_sheet1": len(only1), "only_in_sheet2": len(only2)}


@tool(
    name_zh="模糊比對欄位",
    desc_zh="用模糊比對找出欄位值在候選清單中最相似的項目，並新增對應欄",
    desc_en="fuzzy match column similarity closest value standardize",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":          {"type": "string", "description": "工作表名稱"},
            "column":         {"type": "string", "description": "要比對的欄位"},
            "candidates":     {"type": "array",  "items": {"type": "string"}, "description": "候選標準值清單"},
            "threshold":      {"type": "integer","default": 60, "description": "最低相似度 0-100，低於此值填入空白"},
            "new_column_name":{"type": "string", "default": "", "description": "結果欄名稱，留空自動命名"},
        },
        "required": ["column", "candidates"],
    },
    confirm=False,
    modifies=True,
)
def fuzzy_match_column(wb, *, sheet: str = "", column: str, candidates: list, threshold: int = 60, new_column_name: str = "") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    if column not in df.columns:
        return {"error": f"欄位「{column}」不存在，可用: {list(df.columns)}"}

    def best_match(val: str) -> str:
        matches = difflib.get_close_matches(str(val), candidates, n=1, cutoff=threshold / 100)
        return matches[0] if matches else ""

    col_name = new_column_name or f"{column}_比對"
    df[col_name] = df[column].astype(str).apply(best_match)
    matched = (df[col_name] != "").sum()
    _df_to_ws(ws, df)
    return {"message": f"模糊比對完成，{matched}/{len(df)} 筆成功比對（相似度閾值 {threshold}%）", "matched": int(matched), "new_column": col_name}
