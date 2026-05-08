"""
One-time index builder — run during install.
Validates all tool imports, builds BM25 index, and prints a summary.
Usage: python agent/build_index.py
"""
import sys
from pathlib import Path

# Ensure project root is on path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    print("[build_index] 載入工具模組…")
    try:
        from agent import registry
        registry.invalidate()
        tools = registry.all_tool_descriptors()
    except Exception as e:
        print(f"[build_index] 錯誤: {e}")
        sys.exit(1)

    if not tools:
        print("[build_index] 警告：沒有找到任何工具，請確認 agent/tools/ 目錄正常")
        sys.exit(1)

    print(f"[build_index] 已載入 {len(tools)} 個工具：")
    for t in tools:
        print(f"  {t['name']:35s} {t['name_zh']}")

    # Quick smoke test: retrieve a few queries
    test_queries = ["刪除重複", "加總統計", "建立圖表", "篩選條件", "匯出CSV"]
    print("\n[build_index] 檢索測試：")
    for q in test_queries:
        results = registry.retrieve_tools(q, k=3)
        names = [r["name"] for r in results]
        print(f"  '{q}' → {names}")

    print("\n[build_index] 完成 ✓")


if __name__ == "__main__":
    main()
