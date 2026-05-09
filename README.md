# Win10 離線 AI — 一鍵安裝包 (v2.0 with Excel Agent)

> 完全離線的本地 AI 助手，只需 `git clone` 即可取得所有檔案，不依賴任何 CDN 或外部下載。
> **v2.0 新增 Excel Agent：用自然語言操作 Excel 檔案。**

---

## 安裝方式（公司網路只開放 GitHub 時）

### 1. Clone 此 Repo

```bash
git clone https://github.com/lijingchiu/Win10-Offline-AI.git
```

> **注意**：Repo 約 12 GB（含 Qwen2.5-7B + Qwen3-8B 兩個模型），首次 clone 需要較長時間。
> 建議使用有線網路，或在下班後讓 clone 在背景執行。Git 支援斷點續傳。

### 2. 執行安裝

進入資料夾，**右鍵** `install.bat` → **以系統管理員身分執行**。

安裝程式會自動完成 8 個步驟：

| 步驟 | 說明 |
|---|---|
| ① 環境檢查 | 管理員權限 + 磁碟空間 |
| ② 安裝 Ollama | 組合 23 個分段 → 靜默安裝 |
| ③ 啟動服務 | 啟動 Ollama LLM 服務 |
| ④ Python 3.12 | 解壓 Python 可攜版至 `C:\WinLLM\python` |
| ⑤ 安裝套件 | 從本機 wheel 離線安裝所有依賴（含 pandas / xlwings / jieba） |
| ⑥ 匯入模型 | 組合 GGUF 分段 → ollama create |
| ⑦ 部署介面 | 複製 Web UI + Agent 模組 + 設定檔到 `C:\WinLLM\` |
| ⑧ 建立索引與捷徑 | 建立 38 個 Excel 工具的 BM25 索引 + 桌面啟動捷徑 |

### 3. 啟動使用

雙擊桌面「**Win10 离线 AI**」捷徑 → 瀏覽器自動開啟 `http://localhost:8765`。
完全在 Web UI 內使用，**不需要任何 Terminal 操作**。

---

## 兩大功能模式

### 💬 文件問答模式（PDF / Word / PPT / Excel）

上傳文件 → 自由提問。AI 讀取文件內容後回答，**不修改檔案**。

### 📊 Excel Agent 模式（v2.0 新功能）

**用自然語言指揮 AI 實際操作 Excel 檔案**，例如：

| 你說的話 | AI 執行的操作 |
|---|---|
| 「把工號重複的列刪掉」 | 刪除依工號重複的列 |
| 「依部門加總薪資」 | 群組統計後生成新工作表 |
| 「把月份和銷售額做成折線圖」 | 在工作表插入折線圖 |
| 「篩選薪資大於 50000 的列」 | 條件篩選 |
| 「找出 Sheet1 有但 Sheet2 沒有的客戶」 | 跨表差異比對 |
| 「把銷售報表匯出成 CSV」 | 匯出 + 提供下載 |

**完整工具清單（38 個）**：

| 類別 | 工具 |
|---|---|
| 🧹 資料清理（6） | 刪除重複列、去除前後空格、填補空值、統一欄位格式、分割欄位、合併欄位 |
| 🔍 篩選排序（5） | 條件篩選、多欄排序、取 Top N、區間篩選、清單篩選 |
| 📈 計算統計（6） | 基本統計（總和/平均/計數）、中位數與標準差、群組統計、條件加總（SUMIF）、值計數、工作表概況 |
| 📊 樞紐彙總（4） | 建立樞紐表、群組彙總（多欄）、交叉表、攤平樞紐表 |
| 🔗 查找比對（4） | VLOOKUP 比對合併、跨表比對、找差異列、模糊比對欄位 |
| 🎨 格式化（5） | 條件格式、調整欄寬、設定儲存格樣式、合併儲存格、凍結窗格 |
| 📉 圖表（4） | 長條圖、折線圖、圓餅圖、散佈圖 |
| 💾 匯入匯出（4） | CSV ↔ XLSX、合併多個工作表、依欄位拆分工作表 |

#### 使用流程

1. 切到「📊 Excel Agent」模式
2. 拖放 .xlsx 檔案到上傳區
3. 用對話描述你要做的操作
4. AI 顯示要執行的工具 → 危險操作會跳出**確認對話框**
5. 操作完成後可：**下載結果** / **復原（↩）** / **管理備份**

#### 操作備份（永久保留）

- 每次修改前自動建立備份於 `C:\WinLLM\backups\<日期>\`
- 側邊欄「📦 備份紀錄」可瀏覽 / 一鍵還原 / 刪除
- 副檔名格式：`原檔名_HHMMSS_before_工具名.xlsx`

#### 智慧雙模式

- **⚡ 即時同步**：當你已用 Excel 開啟該檔案時，AI 直接控制現有的 Excel 視窗
- **📁 檔案模式**：未開 Excel 時自動切換到檔案模式，操作後提供下載

---

## Repo 結構

```
Win10-Offline-AI/
├── install.bat              ← 雙擊安裝
├── install.ps1              ← PowerShell 主腳本
├── frontend/
│   └── index.html           ← Web UI（含 Excel Agent 介面）
├── server/
│   └── server.py            ← 後端服務（文件問答 + Agent SSE）
├── agent/                   ← Excel Agent 模組（v2.0 新增）
│   ├── tools/               ← 38 個工具函式（8 個 .py 檔）
│   ├── registry.py          ← BM25 工具檢索
│   ├── llm_client.py        ← Ollama JSON-mode 呼叫
│   ├── prompts.py           ← Prompt 建構
│   ├── runner.py            ← 工具執行 + 自動備份
│   ├── excel_io.py          ← xlwings ↔ openpyxl 智慧切換
│   └── build_index.py       ← 安裝期建索引
├── tests/                   ← 25 個單元測試
├── config/
│   └── settings.json        ← 模型 / Agent 設定
├── setup/
│   ├── ollama/              ← OllamaSetup.exe（23 × 90MB）
│   ├── python/              ← Python 3.12 可攜版
│   ├── wheels/              ← 所有 Python wheel（完全離線）
│   └── models/
│       ├── qwen25_7b/       ← Qwen2.5-7B-Instruct Q4_K_M（Agent 主力）
│       └── qwen3/           ← Qwen3-8B Q4_K_M（備選）
└── README.md
```

---

## AI 模型

| 模型 | 參數 | 量化 | RAM 占用 | 用途 |
|---|---|---|---|---|
| **Qwen2.5-7B-Instruct** ⭐ | 7B | Q4_K_M | ~5.5 GB | Agent 主力（中文好、tool calling 穩定）|
| Qwen3-8B | 8B | Q4_K_M | ~6 GB | 備選（純對話） |

**為何不用更大模型**：16GB RAM 環境扣除 Windows / Excel / 防毒 後僅剩 6-8GB 給 LLM，超過會狂用 swap 卡死。

---

## 系統需求

- **作業系統**：Windows 10 x64（64 位元）
- **RAM**：16 GB **強烈建議**，最低 12 GB
- **磁碟**：C 槽至少 20 GB 可用（含模型解壓縮峰值）
- **CPU**：x64，**不需要獨立顯示卡**（每秒 2-8 tokens）
- **Excel**：可選，僅「即時同步模式」需要

---

## 已知限制

1. **Excel Agent 一次只執行一個工具**：要連續多個操作（例如先篩選再加總再畫圖），請分多次描述。這是設計上的取捨——讓小模型只做「填空題」才能保持穩定。
2. **不支援 .xls 舊格式**：請先用 Excel 另存為 .xlsx
3. **檔案大小**：建議 < 5MB / < 10 萬列，超過可能因 RAM 不足卡頓
4. **VBA 巨集**：Agent **不會**處理巨集，操作後檔案中的巨集會保留但不會執行
5. **公式重算**：openpyxl 模式儲存後，使用者開檔時 Excel 才會重算公式

---

## 常見問題

**Q：clone 很慢怎麼辦？**
→ 正常，Repo 約 12 GB。若卡住超過 10 分鐘，中斷後重新 `git clone`（支援斷點續傳）。

**Q：安裝後介面顯示「無法連線 Ollama」**
→ 確認已執行 `C:\WinLLM\start.bat`，等 5 秒後重新整理瀏覽器。

**Q：Excel Agent 顯示「Agent 模組未啟用」**
→ 表示 pip 安裝有失敗，重新執行 `install.bat` 中的步驟 5（或執行 `C:\WinLLM\update.bat`）。

**Q：操作失敗想復原**
→ 在訊息下方按「↩ 復原」按鈕，或在側邊欄「📦 備份紀錄」找到對應備份按「還原」。

**Q：備份檔太多想清理**
→ 直接刪除 `C:\WinLLM\backups\` 下舊日期的整個資料夾即可，或用側邊欄逐一刪除。

**Q：要更新應用程式（不重灌模型）**
→ `git pull` 後執行 `C:\WinLLM\update.bat`。

**Q：完全停止 AI 服務**
→ 雙擊桌面「停止 AI 服務」捷徑（或 `C:\WinLLM\stop.bat`）。

---

## 開發者文件

### 執行單元測試

```bash
python -m pytest tests/unit/ -v
```

25 個測試應全部通過（不依賴 LLM 服務）。

### 增加新工具

在 `agent/tools/` 找適合分類的檔案，使用 `@tool` 裝飾器：

```python
from ._base import tool

@tool(
    name_zh="新工具中文名",
    desc_zh="中文描述（給 BM25 索引用）",
    desc_en="english keywords for BM25",
    params_schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        },
        "required": ["param1"],
    },
    confirm=True,    # 是否需要使用者確認
    modifies=True,   # 是否會修改工作簿
)
def my_new_tool(wb, *, param1: str) -> dict:
    # ... 實作 ...
    return {"message": "操作完成"}
```

新增後執行 `agent/build_index.py` 重建索引（或重新執行 `install.bat`）。
