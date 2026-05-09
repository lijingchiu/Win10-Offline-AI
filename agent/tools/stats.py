"""計算統計工具 (6 個函式)"""
import pandas as pd
from ._base import tool
from .cleaning import _ws_to_df, _df_to_ws


def _num_cols(df: pd.DataFrame, columns: list | None) -> list:
    if columns:
        return columns
    return list(df.select_dtypes(include="number").columns)


@tool(
    name_zh="基本統計（總和/平均/計數）",
    desc_zh="計算指定數值欄位的總和、平均值、計數",
    desc_en="sum average count total mean statistics numeric column",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":   {"type": "string", "description": "工作表名稱"},
            "columns": {"type": "array",  "items": {"type": "string"}, "description": "要計算的欄位，留空則全部數值欄"},
        },
        "required": [],
    },
    confirm=False,
    modifies=False,
)
def column_sum_avg_count(wb, *, sheet: str = "", columns: list = None) -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    for c in (columns or list(df.columns)):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    target = _num_cols(df, columns)
    if not target:
        return {"error": "找不到數值欄位，請指定欄位名稱"}
    bad = [c for c in target if c not in df.columns]
    if bad:
        return {"error": f"欄位不存在: {bad}"}
    lines = []
    for col in target:
        s = df[col].dropna()
        lines.append(f"{col}：總和={s.sum():,.2f}，平均={s.mean():,.2f}，計數={len(s)}")
    return {"message": "\n".join(lines)}


@tool(
    name_zh="中位數與標準差",
    desc_zh="計算數值欄位的中位數、標準差、最大值、最小值",
    desc_en="median standard deviation max min statistics",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":   {"type": "string", "description": "工作表名稱"},
            "columns": {"type": "array",  "items": {"type": "string"}, "description": "要計算的欄位"},
        },
        "required": [],
    },
    confirm=False,
    modifies=False,
)
def column_median_std(wb, *, sheet: str = "", columns: list = None) -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    for c in (columns or list(df.columns)):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    target = _num_cols(df, columns)
    if not target:
        return {"error": "找不到數值欄位"}
    bad = [c for c in target if c not in df.columns]
    if bad:
        return {"error": f"欄位不存在: {bad}"}
    lines = []
    for col in target:
        s = df[col].dropna()
        lines.append(f"{col}：中位數={s.median():,.2f}，標準差={s.std():,.2f}，最大={s.max():,.2f}，最小={s.min():,.2f}")
    return {"message": "\n".join(lines)}


@tool(
    name_zh="群組統計",
    desc_zh="依指定欄位分組，對數值欄位做加總、平均、計數等統計，結果存入新工作表",
    desc_en="group by aggregate sum mean count statistics pivot groupby",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":        {"type": "string", "description": "工作表名稱"},
            "group_column": {"type": "string", "description": "分組依據的欄位"},
            "agg_column":   {"type": "string", "description": "要統計的數值欄位"},
            "agg_func":     {"type": "string", "enum": ["sum","mean","count","max","min","median","std"], "default": "sum", "description": "統計方式"},
            "new_sheet":    {"type": "string", "default": "群組統計", "description": "結果寫入的工作表名稱"},
        },
        "required": ["group_column", "agg_column"],
    },
    confirm=False,
    modifies=True,
)
def group_by_stats(wb, *, sheet: str = "", group_column: str, agg_column: str, agg_func: str = "sum", new_sheet: str = "群組統計") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    for col in [group_column, agg_column]:
        if col not in df.columns:
            return {"error": f"欄位「{col}」不存在，可用: {list(df.columns)}"}
    df[agg_column] = pd.to_numeric(df[agg_column], errors="coerce")
    result = df.groupby(group_column)[agg_column].agg(agg_func).reset_index()
    result.columns = [group_column, f"{agg_column}_{agg_func}"]
    if new_sheet in wb.sheetnames:
        del wb[new_sheet]
    out_ws = wb.create_sheet(new_sheet)
    out_ws.append(list(result.columns))
    for row in result.itertuples(index=False, name=None):
        out_ws.append(list(row))
    preview = result.head(5).to_string(index=False)
    return {"message": f"已依「{group_column}」群組統計「{agg_column}」({agg_func})，結果在工作表「{new_sheet}」\n前5筆預覽：\n{preview}", "new_sheet": new_sheet, "groups": len(result)}


@tool(
    name_zh="條件加總（SUMIF）",
    desc_zh="當條件欄位的值等於指定條件時，加總另一個數值欄位（相當於 SUMIF）",
    desc_en="sumif conditional sum sumifs criteria condition",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":            {"type": "string", "description": "工作表名稱"},
            "sum_column":       {"type": "string", "description": "要加總的數值欄位"},
            "condition_column": {"type": "string", "description": "條件判斷欄位"},
            "condition_value":  {"type": "string", "description": "條件值"},
        },
        "required": ["sum_column", "condition_column", "condition_value"],
    },
    confirm=False,
    modifies=False,
)
def conditional_sum(wb, *, sheet: str = "", sum_column: str, condition_column: str, condition_value: str) -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    for col in [sum_column, condition_column]:
        if col not in df.columns:
            return {"error": f"欄位「{col}」不存在，可用: {list(df.columns)}"}
    df[sum_column] = pd.to_numeric(df[sum_column], errors="coerce")
    mask = df[condition_column].astype(str) == str(condition_value)
    total = df.loc[mask, sum_column].sum()
    count = mask.sum()
    return {"message": f"當「{condition_column}」= '{condition_value}' 時，「{sum_column}」加總 = {total:,.2f}（共 {count} 筆）", "sum": float(total), "count": int(count)}


@tool(
    name_zh="值計數",
    desc_zh="統計欄位中每個唯一值出現的次數，相當於 Excel COUNTIF",
    desc_en="value counts unique count frequency distribution countif",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":     {"type": "string", "description": "工作表名稱"},
            "column":    {"type": "string", "description": "要統計的欄位"},
            "top_n":     {"type": "integer","default": 20, "description": "只顯示前 N 個最多的值"},
            "new_sheet": {"type": "string", "default": "", "description": "將結果寫入新工作表（留空則只顯示）"},
        },
        "required": ["column"],
    },
    confirm=False,
    modifies=False,
)
def value_counts(wb, *, sheet: str = "", column: str, top_n: int = 20, new_sheet: str = "") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    if column not in df.columns:
        return {"error": f"欄位「{column}」不存在，可用: {list(df.columns)}"}
    vc = df[column].value_counts().head(top_n)
    lines = [f"{v}: {c} 次" for v, c in vc.items()]
    if new_sheet:
        if new_sheet in wb.sheetnames:
            del wb[new_sheet]
        out_ws = wb.create_sheet(new_sheet)
        out_ws.append([column, "次數"])
        for v, c in vc.items():
            out_ws.append([v, int(c)])
    return {"message": f"「{column}」前 {len(vc)} 個值：\n" + "\n".join(lines), "unique_count": int(df[column].nunique())}


@tool(
    name_zh="工作表概況",
    desc_zh="顯示工作表的基本資訊：列數、欄數、欄位名稱、各欄非空值數量",
    desc_en="describe sheet overview info summary columns rows non null",
    params_schema={
        "type": "object",
        "properties": {
            "sheet": {"type": "string", "description": "工作表名稱，留空用第一張"},
        },
        "required": [],
    },
    confirm=False,
    modifies=False,
)
def describe_sheet(wb, *, sheet: str = "") -> dict:
    ws, df, _ = _ws_to_df(wb, sheet)
    name = sheet or wb.sheetnames[0]
    lines = [
        f"工作表：{name}",
        f"資料列數：{len(df)}，欄數：{len(df.columns)}",
        "欄位清單（非空值數）：",
    ]
    for col in df.columns:
        non_null = df[col].notna().sum()
        dtype_hint = "數值" if pd.api.types.is_numeric_dtype(df[col]) else "文字"
        lines.append(f"  {col}：{non_null}/{len(df)} 非空（{dtype_hint}）")
    return {"message": "\n".join(lines), "rows": len(df), "columns": list(df.columns)}
