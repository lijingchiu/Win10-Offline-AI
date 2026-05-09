"""
Prompt builder for the Excel Agent.
Keeps total token count under ~1150 by injecting only top-5 tools.
"""

_SYSTEM = """\
你是一個 Excel 操作助理。你的唯一工作是：
1. 從下方【可用工具】中選出最合適的「一個」工具
2. 從使用者描述中抽出執行該工具所需的參數

## 絕對規則
- 只輸出 JSON，不輸出任何說明文字、markdown、程式碼區塊或換行前綴
- 如果無法對應到任何工具，輸出 {"action_type":"clarify","question":"你要問使用者的問題"}
- 如果使用者的要求是純查詢（不需修改檔案），輸出 {"action_type":"done","answer":"回答內容"}
- 每次只選一個工具，不做多步規劃

## 輸出格式（execute 時）
{"action_type":"execute","tool":"函式名稱","params":{...},"explanation":"一句話說明"}
"""

_FEW_SHOT = [
    {"role": "user",      "content": '工作簿:員工資料.xlsx 工作表:["員工資料"] 欄位:["工號","姓名","部門","薪資"]\n\n使用者說: 把工號重複的列刪掉'},
    {"role": "assistant", "content": '{"action_type":"execute","tool":"remove_duplicates","params":{"sheet":"員工資料","columns":["工號"],"keep":"first"},"explanation":"依工號欄刪除重複列，保留第一筆"}'},
    {"role": "user",      "content": '工作簿:銷售.xlsx 工作表:["銷售"] 欄位:["月份","銷售額","地區"]\n\n使用者說: 依地區加總銷售額'},
    {"role": "assistant", "content": '{"action_type":"execute","tool":"group_by_stats","params":{"sheet":"銷售","group_column":"地區","agg_column":"銷售額","agg_func":"sum"},"explanation":"依地區欄群組加總銷售額"}'},
    {"role": "user",      "content": '工作簿:data.xlsx 工作表:["Sheet1"] 欄位:["A","B"]\n\n使用者說: 這個表有幾個工作表'},
    {"role": "assistant", "content": '{"action_type":"done","answer":"這個工作簿只有 1 個工作表：Sheet1"}'},
]


def _fmt_tool(t: dict) -> str:
    lines = [
        f"工具: {t['name']} | {t['name_zh']}",
        f"說明: {t['desc_zh']}",
    ]
    props = t.get("params_schema", {}).get("properties", {})
    required = t.get("params_schema", {}).get("required", [])
    for pname, pdef in props.items():
        req = "必填" if pname in required else "選填"
        default = f", 預設\"{pdef['default']}\"" if "default" in pdef else ""
        desc = pdef.get("description", "")
        lines.append(f"  - {pname} ({pdef.get('type','any')}, {req}{default}): {desc}")
    return "\n".join(lines)


def _fmt_wb_context(wb_info: dict) -> str:
    sheets = "、".join(wb_info.get("sheet_names", []))
    cols   = "、".join(wb_info.get("columns", []))
    rows   = wb_info.get("row_count", "?")
    fn     = wb_info.get("filename", "工作簿")
    active = wb_info.get("active_sheet", "")
    return (
        f"工作簿:{fn} 工作表:[{sheets}] "
        f"當前工作表:{active} 欄位:[{cols}] 資料列數:{rows}"
    )


def build_prompt(
    tools_info: list[dict],
    wb_info: dict,
    history: list[dict],
    user_msg: str,
) -> list[dict]:
    tool_block = "\n\n".join(_fmt_tool(t) for t in tools_info)
    system_with_tools = f"{_SYSTEM}\n## 可用工具（本次相關）\n\n{tool_block}"

    messages: list[dict] = [{"role": "system", "content": system_with_tools}]
    messages.extend(_FEW_SHOT)

    # Last 3 rounds of history
    for turn in history[-6:]:
        messages.append(turn)

    context = _fmt_wb_context(wb_info)
    messages.append({"role": "user", "content": f"{context}\n\n使用者說: {user_msg}"})
    return messages
