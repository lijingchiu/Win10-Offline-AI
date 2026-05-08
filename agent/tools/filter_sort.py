"""篩選與排序工具 (5 個函式)"""
import operator as op_module
import pandas as pd
from ._base import tool
from .cleaning import _ws_to_df, _df_to_ws

_OPS = {
    "=": op_module.eq, "==": op_module.eq,
    "!=": op_module.ne, "<>": op_module.ne,
    ">": op_module.gt, ">=": op_module.ge,
    "<": op_module.lt, "<=": op_module.le,
}


@tool(
    name_zh="條件篩選",
    desc_zh="依條件篩選列，保留或刪除符合條件的列",
    desc_en="filter rows by condition keep delete where greater less equal contains",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":    {"type": "string", "description": "工作表名稱"},
            "column":   {"type": "string", "description": "篩選依據的欄位"},
            "operator": {"type": "string", "description": "運算子：=、!=、>、<、>=、<=、contains、not_contains、startswith、endswith、is_empty、is_not_empty"},
            "value":    {"type": "string", "description": "比較值（is_empty/is_not_empty 不需要）"},
            "keep":     {"type": "boolean","default": True, "description": "true=保留符合的列，false=刪除符合的列"},
        },
        "required": ["column", "operator"],
    },
    confirm=True,
    modifies=True,
)
def filter_rows_by_condition(wb, *, sheet: str = "", column: str, operator: str, value: str = "", keep: bool = True) -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    if column not in df.columns:
        return {"error": f"欄位「{column}」不存在，可用: {list(df.columns)}"}

    col = df[column]
    if operator in _OPS:
        try:
            num_val = float(value)
            mask = col.apply(lambda x: _OPS[operator](_to_num(x), num_val) if _to_num(x) is not None else False)
        except (ValueError, TypeError):
            mask = col.apply(lambda x: _OPS[operator](str(x), str(value)))
    elif operator == "contains":
        mask = col.astype(str).str.contains(str(value), na=False)
    elif operator == "not_contains":
        mask = ~col.astype(str).str.contains(str(value), na=False)
    elif operator == "startswith":
        mask = col.astype(str).str.startswith(str(value), na=False)
    elif operator == "endswith":
        mask = col.astype(str).str.endswith(str(value), na=False)
    elif operator == "is_empty":
        mask = col.isna() | (col.astype(str).str.strip() == "")
    elif operator == "is_not_empty":
        mask = ~(col.isna() | (col.astype(str).str.strip() == ""))
    else:
        return {"error": f"不支援的運算子：{operator}"}

    if not keep:
        mask = ~mask
    before = len(df)
    df = df[mask].reset_index(drop=True)
    removed = before - len(df)
    _df_to_ws(ws, df)
    return {"message": f"篩選後剩餘 {len(df)} 列（刪除 {removed} 列）", "remaining": len(df), "removed": removed}


def _to_num(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


@tool(
    name_zh="多欄排序",
    desc_zh="依一個或多個欄位排序工作表",
    desc_en="sort multiple columns ascending descending order",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":   {"type": "string", "description": "工作表名稱"},
            "sort_by": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "column":    {"type": "string"},
                        "ascending": {"type": "boolean", "default": True},
                    },
                },
                "description": "排序條件清單，如 [{\"column\":\"部門\",\"ascending\":true},{\"column\":\"薪資\",\"ascending\":false}]",
            },
        },
        "required": ["sort_by"],
    },
    confirm=False,
    modifies=True,
)
def multi_column_sort(wb, *, sheet: str = "", sort_by: list) -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    cols = [s.get("column") or s.get("col", "") for s in sort_by]
    asc  = [bool(s.get("ascending", True)) for s in sort_by]
    bad = [c for c in cols if c not in df.columns]
    if bad:
        return {"error": f"欄位不存在: {bad}，可用: {list(df.columns)}"}
    df.sort_values(by=cols, ascending=asc, inplace=True)
    df.reset_index(drop=True, inplace=True)
    _df_to_ws(ws, df)
    desc = "、".join(f"{c}({'升冪' if a else '降冪'})" for c, a in zip(cols, asc))
    return {"message": f"已依 {desc} 排序", "sort_keys": cols}


@tool(
    name_zh="取 Top N 列",
    desc_zh="依指定欄位取值最大或最小的前 N 列",
    desc_en="top n rows largest smallest max min ranking",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":   {"type": "string",  "description": "工作表名稱"},
            "column":  {"type": "string",  "description": "排序依據欄位"},
            "n":       {"type": "integer", "default": 10, "description": "取幾列"},
            "largest": {"type": "boolean", "default": True, "description": "true=最大，false=最小"},
        },
        "required": ["column"],
    },
    confirm=True,
    modifies=True,
)
def top_n_rows(wb, *, sheet: str = "", column: str, n: int = 10, largest: bool = True) -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    if column not in df.columns:
        return {"error": f"欄位「{column}」不存在，可用: {list(df.columns)}"}
    try:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    except Exception:
        pass
    before = len(df)
    df = df.nlargest(n, column) if largest else df.nsmallest(n, column)
    df.reset_index(drop=True, inplace=True)
    _df_to_ws(ws, df)
    direction = "最大" if largest else "最小"
    return {"message": f"已保留「{column}」欄 {direction} 的 {len(df)} 列（原本 {before} 列）", "kept": len(df)}


@tool(
    name_zh="區間篩選",
    desc_zh="依數值區間篩選列，保留在最小值到最大值之間的列",
    desc_en="filter by range between min max value numeric",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":     {"type": "string", "description": "工作表名稱"},
            "column":    {"type": "string", "description": "篩選依據的數值欄位"},
            "min_value": {"type": "number", "description": "最小值（含），留空則不設下限"},
            "max_value": {"type": "number", "description": "最大值（含），留空則不設上限"},
        },
        "required": ["column"],
    },
    confirm=True,
    modifies=True,
)
def filter_by_range(wb, *, sheet: str = "", column: str, min_value=None, max_value=None) -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    if column not in df.columns:
        return {"error": f"欄位「{column}」不存在，可用: {list(df.columns)}"}
    df[column] = pd.to_numeric(df[column], errors="coerce")
    mask = pd.Series([True] * len(df))
    if min_value is not None:
        mask &= df[column] >= float(min_value)
    if max_value is not None:
        mask &= df[column] <= float(max_value)
    before = len(df)
    df = df[mask].reset_index(drop=True)
    _df_to_ws(ws, df)
    range_desc = f"{min_value if min_value is not None else '-∞'} ~ {max_value if max_value is not None else '+∞'}"
    return {"message": f"「{column}」區間 {range_desc} 篩選後剩 {len(df)} 列（刪除 {before-len(df)} 列）", "remaining": len(df)}


@tool(
    name_zh="清單篩選",
    desc_zh="保留欄位值在指定清單中的列",
    desc_en="filter by list values keep rows in list whitelist",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":   {"type": "string", "description": "工作表名稱"},
            "column":  {"type": "string", "description": "篩選依據欄位"},
            "values":  {"type": "array",  "items": {"type": "string"}, "description": "允許保留的值清單"},
            "exclude": {"type": "boolean","default": False, "description": "true=排除清單中的值"},
        },
        "required": ["column", "values"],
    },
    confirm=True,
    modifies=True,
)
def filter_by_list(wb, *, sheet: str = "", column: str, values: list, exclude: bool = False) -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    if column not in df.columns:
        return {"error": f"欄位「{column}」不存在，可用: {list(df.columns)}"}
    str_vals = [str(v) for v in values]
    mask = df[column].astype(str).isin(str_vals)
    if exclude:
        mask = ~mask
    before = len(df)
    df = df[mask].reset_index(drop=True)
    _df_to_ws(ws, df)
    action = "排除" if exclude else "保留"
    return {"message": f"{action}清單值後剩 {len(df)} 列（刪除 {before-len(df)} 列）", "remaining": len(df)}
