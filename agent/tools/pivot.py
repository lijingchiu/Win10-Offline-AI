"""樞紐彙總工具 (4 個函式)"""
import pandas as pd
from ._base import tool
from .cleaning import _ws_to_df, _df_to_ws


def _write_df_to_new_sheet(wb, df: pd.DataFrame, sheet_name: str) -> None:
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)
    ws.append(list(df.columns.astype(str)))
    for row in df.itertuples(index=False, name=None):
        ws.append([str(v) if not isinstance(v, (int, float, type(None))) else v for v in row])


@tool(
    name_zh="建立樞紐表",
    desc_zh="依列標籤、欄標籤和數值欄位建立樞紐表，結果存入新工作表",
    desc_en="pivot table create rows columns values aggregate",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":     {"type": "string", "description": "來源工作表名稱"},
            "rows":      {"type": "array",  "items": {"type": "string"}, "description": "作為列標籤的欄位"},
            "columns":   {"type": "array",  "items": {"type": "string"}, "description": "作為欄標籤的欄位（可留空）"},
            "values":    {"type": "string", "description": "要彙總的數值欄位"},
            "aggfunc":   {"type": "string", "enum": ["sum","mean","count","max","min"], "default": "sum", "description": "彙總函式"},
            "new_sheet": {"type": "string", "default": "樞紐表", "description": "結果工作表名稱"},
        },
        "required": ["rows", "values"],
    },
    confirm=False,
    modifies=True,
)
def create_pivot_table(wb, *, sheet: str = "", rows: list, columns: list = None, values: str, aggfunc: str = "sum", new_sheet: str = "樞紐表") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    all_cols = rows + (columns or []) + [values]
    bad = [c for c in all_cols if c not in df.columns]
    if bad:
        return {"error": f"欄位不存在: {bad}，可用: {list(df.columns)}"}
    df[values] = pd.to_numeric(df[values], errors="coerce")
    pivot = pd.pivot_table(
        df,
        index=rows,
        columns=columns if columns else None,
        values=values,
        aggfunc=aggfunc,
        fill_value=0,
    )
    pivot.reset_index(inplace=True)
    pivot.columns = [str(c) for c in pivot.columns]
    _write_df_to_new_sheet(wb, pivot, new_sheet)
    return {"message": f"樞紐表已建立於工作表「{new_sheet}」（{len(pivot)} 列）", "new_sheet": new_sheet, "rows_count": len(pivot)}


@tool(
    name_zh="群組彙總（多欄）",
    desc_zh="依分組欄位對多個數值欄做多種統計，結果存入新工作表",
    desc_en="group aggregate multiple columns sum mean count new sheet",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":        {"type": "string", "description": "來源工作表名稱"},
            "group_by":     {"type": "array",  "items": {"type": "string"}, "description": "分組欄位清單"},
            "aggregations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "column":  {"type": "string"},
                        "func":    {"type": "string", "enum": ["sum","mean","count","max","min"]},
                    },
                },
                "description": "統計設定，如 [{\"column\":\"薪資\",\"func\":\"sum\"},{\"column\":\"薪資\",\"func\":\"mean\"}]",
            },
            "new_sheet": {"type": "string", "default": "群組彙總", "description": "結果工作表名稱"},
        },
        "required": ["group_by", "aggregations"],
    },
    confirm=False,
    modifies=True,
)
def group_and_aggregate(wb, *, sheet: str = "", group_by: list, aggregations: list, new_sheet: str = "群組彙總") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    bad = [c for c in group_by if c not in df.columns]
    if bad:
        return {"error": f"分組欄位不存在: {bad}"}
    agg_dict: dict = {}
    for ag in aggregations:
        col = ag.get("column") or ag.get("col", "")
        func = ag.get("func", "sum")
        if col not in df.columns:
            return {"error": f"欄位「{col}」不存在"}
        df[col] = pd.to_numeric(df[col], errors="coerce")
        agg_dict.setdefault(col, []).append(func)
    result = df.groupby(group_by).agg(agg_dict)
    result.columns = ["_".join(c) if isinstance(c, tuple) else c for c in result.columns]
    result.reset_index(inplace=True)
    _write_df_to_new_sheet(wb, result, new_sheet)
    return {"message": f"群組彙總完成，結果在工作表「{new_sheet}」（{len(result)} 組）", "new_sheet": new_sheet}


@tool(
    name_zh="交叉表",
    desc_zh="建立兩個類別欄位的交叉統計表（類似交叉分析篩選器）",
    desc_en="cross tabulation crosstab frequency table two categorical columns",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":        {"type": "string", "description": "來源工作表名稱"},
            "row_column":   {"type": "string", "description": "列標籤欄位"},
            "col_column":   {"type": "string", "description": "欄標籤欄位"},
            "value_column": {"type": "string", "description": "數值欄位（留空則計次數）"},
            "aggfunc":      {"type": "string", "enum": ["count","sum","mean"], "default": "count"},
            "new_sheet":    {"type": "string", "default": "交叉表", "description": "結果工作表名稱"},
        },
        "required": ["row_column", "col_column"],
    },
    confirm=False,
    modifies=True,
)
def cross_tabulation(wb, *, sheet: str = "", row_column: str, col_column: str, value_column: str = "", aggfunc: str = "count", new_sheet: str = "交叉表") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    for col in [row_column, col_column]:
        if col not in df.columns:
            return {"error": f"欄位「{col}」不存在，可用: {list(df.columns)}"}
    if value_column and value_column not in df.columns:
        return {"error": f"數值欄位「{value_column}」不存在"}
    if value_column and aggfunc != "count":
        df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
        ct = pd.pivot_table(df, index=row_column, columns=col_column, values=value_column, aggfunc=aggfunc, fill_value=0)
    else:
        ct = pd.crosstab(df[row_column], df[col_column])
    ct.reset_index(inplace=True)
    ct.columns = [str(c) for c in ct.columns]
    _write_df_to_new_sheet(wb, ct, new_sheet)
    return {"message": f"交叉表已建立於「{new_sheet}」（{len(ct)} 行 × {len(ct.columns)-1} 列）", "new_sheet": new_sheet}


@tool(
    name_zh="攤平樞紐表",
    desc_zh="將含有多層標題或小計列的樞紐表轉換為平面資料表",
    desc_en="flatten pivot table remove subtotals unnest header",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":     {"type": "string", "description": "要攤平的工作表名稱"},
            "new_sheet": {"type": "string", "default": "",  "description": "結果工作表（留空則覆寫原表）"},
        },
        "required": [],
    },
    confirm=False,
    modifies=True,
)
def flatten_pivot(wb, *, sheet: str = "", new_sheet: str = "") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)
    target_sheet = new_sheet or (sheet or wb.sheetnames[0])
    if new_sheet and new_sheet not in wb.sheetnames:
        _write_df_to_new_sheet(wb, df, new_sheet)
    else:
        _df_to_ws(ws, df)
    return {"message": f"已攤平工作表「{target_sheet}」（{len(df)} 列 × {len(df.columns)} 欄）"}
