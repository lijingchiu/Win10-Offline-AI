"""圖表工具 (4 個函式) — 使用 openpyxl 原生圖表"""
from openpyxl.chart import BarChart, LineChart, PieChart, ScatterChart, Reference, Series
from openpyxl.utils import get_column_letter
from ._base import tool
from .cleaning import _ws_to_df


def _find_col_idx(ws, col_name: str) -> int | None:
    """Return 1-based column index for given header name."""
    for cell in ws[1]:
        if str(cell.value) == col_name:
            return cell.column
    return None


def _build_references(ws, x_col_name: str, y_col_name: str) -> tuple:
    """Return (x_ref, y_ref, max_row) or raise ValueError."""
    x_idx = _find_col_idx(ws, x_col_name)
    y_idx = _find_col_idx(ws, y_col_name)
    if x_idx is None:
        raise ValueError(f"X 欄「{x_col_name}」不存在")
    if y_idx is None:
        raise ValueError(f"Y 欄「{y_col_name}」不存在")
    max_row = ws.max_row
    cats = Reference(ws, min_col=x_idx, min_row=2, max_row=max_row)
    data = Reference(ws, min_col=y_idx, min_row=1, max_row=max_row)
    return cats, data, max_row


def _place_chart(wb, ws, chart, chart_sheet: str | None, title: str):
    chart.title = title
    chart.style = 10
    if chart_sheet:
        if chart_sheet not in wb.sheetnames:
            wb.create_sheet(chart_sheet)
        cws = wb[chart_sheet]
        cws.add_chart(chart, "A1")
    else:
        ws.add_chart(chart, "H2")


@tool(
    name_zh="插入長條圖",
    desc_zh="依兩個欄位建立長條圖（直條或橫條），插入工作表中",
    desc_en="bar chart column chart insert x y axis",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":       {"type": "string", "description": "資料所在工作表"},
            "x_column":    {"type": "string", "description": "X 軸（類別）欄位名稱"},
            "y_column":    {"type": "string", "description": "Y 軸（數值）欄位名稱"},
            "title":       {"type": "string", "default": "", "description": "圖表標題"},
            "chart_sheet": {"type": "string", "default": "", "description": "圖表工作表名稱，留空則插入資料工作表"},
        },
        "required": ["x_column", "y_column"],
    },
    confirm=False,
    modifies=True,
)
def insert_bar_chart(wb, *, sheet: str = "", x_column: str, y_column: str, title: str = "", chart_sheet: str = "") -> dict:
    ws_name = sheet or wb.sheetnames[0]
    if ws_name not in wb.sheetnames:
        return {"error": f"工作表「{ws_name}」不存在"}
    ws = wb[ws_name]
    try:
        cats, data, _ = _build_references(ws, x_column, y_column)
    except ValueError as e:
        return {"error": str(e)}
    chart = BarChart()
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.shape = 4
    _place_chart(wb, ws, chart, chart_sheet or None, title or f"{y_column} 長條圖")
    dest = chart_sheet or ws_name
    return {"message": f"長條圖「{title or y_column}」已插入工作表「{dest}」"}


@tool(
    name_zh="插入折線圖",
    desc_zh="依兩個欄位建立折線圖，適合呈現趨勢變化",
    desc_en="line chart trend time series insert",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":       {"type": "string", "description": "資料所在工作表"},
            "x_column":    {"type": "string", "description": "X 軸欄位"},
            "y_column":    {"type": "string", "description": "Y 軸數值欄位"},
            "title":       {"type": "string", "default": ""},
            "chart_sheet": {"type": "string", "default": ""},
        },
        "required": ["x_column", "y_column"],
    },
    confirm=False,
    modifies=True,
)
def insert_line_chart(wb, *, sheet: str = "", x_column: str, y_column: str, title: str = "", chart_sheet: str = "") -> dict:
    ws_name = sheet or wb.sheetnames[0]
    if ws_name not in wb.sheetnames:
        return {"error": f"工作表「{ws_name}」不存在"}
    ws = wb[ws_name]
    try:
        cats, data, _ = _build_references(ws, x_column, y_column)
    except ValueError as e:
        return {"error": str(e)}
    chart = LineChart()
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    _place_chart(wb, ws, chart, chart_sheet or None, title or f"{y_column} 折線圖")
    dest = chart_sheet or ws_name
    return {"message": f"折線圖「{title or y_column}」已插入工作表「{dest}」"}


@tool(
    name_zh="插入圓餅圖",
    desc_zh="依標籤欄位和數值欄位建立圓餅圖",
    desc_en="pie chart donut proportion percentage insert",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":        {"type": "string", "description": "資料所在工作表"},
            "label_column": {"type": "string", "description": "標籤欄位（類別）"},
            "value_column": {"type": "string", "description": "數值欄位"},
            "title":        {"type": "string", "default": ""},
            "chart_sheet":  {"type": "string", "default": ""},
        },
        "required": ["label_column", "value_column"],
    },
    confirm=False,
    modifies=True,
)
def insert_pie_chart(wb, *, sheet: str = "", label_column: str, value_column: str, title: str = "", chart_sheet: str = "") -> dict:
    ws_name = sheet or wb.sheetnames[0]
    if ws_name not in wb.sheetnames:
        return {"error": f"工作表「{ws_name}」不存在"}
    ws = wb[ws_name]
    try:
        cats, data, _ = _build_references(ws, label_column, value_column)
    except ValueError as e:
        return {"error": str(e)}
    chart = PieChart()
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    _place_chart(wb, ws, chart, chart_sheet or None, title or f"{value_column} 圓餅圖")
    dest = chart_sheet or ws_name
    return {"message": f"圓餅圖「{title or value_column}」已插入工作表「{dest}」"}


@tool(
    name_zh="插入散佈圖",
    desc_zh="建立兩個數值欄位的散佈圖，適合探索相關性",
    desc_en="scatter chart correlation plot XY bubble",
    params_schema={
        "type": "object",
        "properties": {
            "sheet":       {"type": "string", "description": "資料所在工作表"},
            "x_column":    {"type": "string", "description": "X 軸數值欄位"},
            "y_column":    {"type": "string", "description": "Y 軸數值欄位"},
            "title":       {"type": "string", "default": ""},
            "chart_sheet": {"type": "string", "default": ""},
        },
        "required": ["x_column", "y_column"],
    },
    confirm=False,
    modifies=True,
)
def insert_scatter_chart(wb, *, sheet: str = "", x_column: str, y_column: str, title: str = "", chart_sheet: str = "") -> dict:
    ws_name = sheet or wb.sheetnames[0]
    if ws_name not in wb.sheetnames:
        return {"error": f"工作表「{ws_name}」不存在"}
    ws = wb[ws_name]
    x_idx = _find_col_idx(ws, x_column)
    y_idx = _find_col_idx(ws, y_column)
    if x_idx is None:
        return {"error": f"X 欄「{x_column}」不存在"}
    if y_idx is None:
        return {"error": f"Y 欄「{y_column}」不存在"}
    max_row = ws.max_row
    chart = ScatterChart()
    xvalues = Reference(ws, min_col=x_idx, min_row=2, max_row=max_row)
    yvalues = Reference(ws, min_col=y_idx, min_row=2, max_row=max_row)
    series = Series(yvalues, xvalues, title=y_column)
    chart.series.append(series)
    _place_chart(wb, ws, chart, chart_sheet or None, title or f"{x_column} vs {y_column}")
    dest = chart_sheet or ws_name
    return {"message": f"散佈圖「{title or f'{x_column} vs {y_column}'}」已插入工作表「{dest}」"}
