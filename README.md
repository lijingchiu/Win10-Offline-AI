# Win10 離線 AI — 一鍵安裝包

> 完全離線運行的本地 AI 助手，支援文件分析（PDF / Excel / Word / PPT），無需網路，資料不外傳。

---

## 安裝步驟

### 1. 下載安裝包

前往 **[Releases](../../releases/latest)** 頁面，下載 `WinLLM_Setup.exe`。

> 公司環境只開放 GitHub 網域同樣可以下載，因為 Release 檔案由 GitHub 伺服器提供。

### 2. 執行安裝

- 右鍵 `WinLLM_Setup.exe` → **「以系統管理員身分執行」**
- 精靈會自動完成所有步驟

### 3. 安裝模型

安裝精靈完成後，AI 模型會透過以下方式之一安裝：

| 方式 | 說明 |
|------|------|
| GitHub Releases 自動下載 | 若管理員已將 GGUF 上傳至 Releases，自動下載 |
| 網路直接拉取 | 若公司網路允許，自動執行 `ollama pull` |
| 離線手動匯入 | 將 GGUF 放至 `C:\WinLLM\models\` 後執行 `import_model.bat` |

**→ 詳見 [模型安裝說明](models/README.md)**

### 4. 啟動使用

雙擊桌面的 **「Win10 离线 AI」** 捷徑，瀏覽器自動開啟介面。

---

## 功能介紹

| 功能 | 說明 |
|------|------|
| 💬 一般對話 | 與 AI 自由對話 |
| 📄 文件問答 | 上傳文件後針對內容提問 |
| 📝 文件摘要 | 自動生成結構化摘要 |
| 📊 資料提取 | 從文件提取表格、數據 |
| 🌐 翻譯助手 | 中英文互譯 |
| 🔍 審閱校對 | 文件審閱與改善建議 |

### 支援的文件格式

- PDF（含掃描件文字層）
- Excel（.xlsx / .xls）
- Word（.docx）
- PowerPoint（.pptx）
- 純文字（.txt / .csv / .md）

---

## 架構說明

```
C:\WinLLM\                   ← 安裝目錄
├── frontend/                ← 網頁介面（HTML + JS）
│   └── index.html
├── python/                  ← Python 3.12 可攜版
├── models/                  ← GGUF 模型暫存區
├── server.py                ← 本地文件處理服務 (port 8765)
├── start.bat                ← 啟動腳本
├── stop.bat                 ← 停止腳本
└── scripts/
    └── import_model.bat     ← 手動匯入模型

Ollama 服務 → port 11434     ← LLM 推理引擎
文件服務   → port 8765      ← 提供前端 + 文件解析 API
```

---

## 離線安裝完整流程（公司網路限制時）

```
家用電腦（可上網）                   公司電腦（只能 GitHub）
─────────────────────                ─────────────────────────
1. 下載 WinLLM_Setup.exe            2. 執行 WinLLM_Setup.exe
   (from GitHub Releases)              (以管理員身分)
3. 執行 download_models_home.ps1    4. 複製 .gguf 檔案至
   下載 GGUF 模型至 USB                C:\WinLLM\models\
                          ──USB──→  5. 執行 import_model.bat
                                    6. 雙擊桌面捷徑啟動！
```

---

## 常見問題

**Q: 介面顯示「無法連線至 Ollama」**
→ 確認已執行 `start.bat`，等待約 5 秒後重新整理瀏覽器。

**Q: 沒有可用模型**
→ 參考 [模型安裝說明](models/README.md)，手動匯入 GGUF 檔案。

**Q: 文件上傳後無反應**
→ 確認 `start.bat` 已啟動文件服務（Python 服務 port 8765）。

**Q: 回應速度慢**
→ 8B 模型在無 GPU 電腦上每秒約 2-8 個 token，屬正常現象。可改用 4B 模型加速。

---

## 技術棧

- **LLM 引擎**: [Ollama](https://github.com/ollama/ollama)
- **推薦模型**: Qwen3-8B / Llama-3.1-8B（量化版 Q4_K_M）
- **Python 可攜版**: [python-build-standalone](https://github.com/indygreg/python-build-standalone)
- **文件解析**: PyMuPDF / python-docx / openpyxl / python-pptx
- **前端**: 純 HTML + JavaScript（無框架依賴）
- **安裝程式**: Python + PyInstaller（GitHub Actions 自動建置）
