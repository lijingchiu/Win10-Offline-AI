# Win10 離線 AI — 一鍵安裝包

> 完全離線的本地 AI 助手，只需 `git clone` 即可取得所有檔案，不依賴任何 CDN 或外部下載。

---

## 安裝方式（公司網路只開放 GitHub 時）

### 1. Clone 此 Repo

```bash
git clone https://github.com/lijingchiu/Win10-Offline-AI.git
```

> **注意**：Repo 約 11.5 GB，首次 clone 需要較長時間，請耐心等候。
> 建議使用有線網路連接，或在下班後讓 clone 在背景執行。

### 2. 執行安裝

進入下載好的資料夾，**右鍵** `install.bat` → **以系統管理員身分執行**

安裝程式會自動完成：

| 步驟 | 說明 |
|------|------|
| ① 環境檢查 | 確認管理員權限與磁碟空間 |
| ② 安裝 Ollama | 組合 23 個分段 → 安裝 OllamaSetup.exe |
| ③ 啟動服務 | 啟動 Ollama LLM 服務 |
| ④ Python 3.12 | 解壓 Python 可攜版至 C:\WinLLM\python |
| ⑤ 安裝套件 | 從本機 wheel 離線安裝所有 Python 依賴 |
| ⑥ 匯入模型 | 組合 GGUF 分段 → ollama create |
| ⑦ 部署介面 | 複製 Web UI + 建立桌面捷徑 |

### 3. 啟動使用

雙擊桌面 **「Win10 离线 AI」** 捷徑，瀏覽器自動開啟 `http://localhost:8765`

---

## Repo 內容說明

```
Win10-Offline-AI/
├── install.bat              ← 雙擊此檔案開始安裝
├── install.ps1              ← PowerShell 安裝腳本
├── frontend/
│   └── index.html           ← Web UI（Chat + 文件上傳）
├── server/
│   └── server.py            ← 文件解析服務（PDF/Excel/Word/PPT）
├── setup/
│   ├── ollama/              ← OllamaSetup.exe（23 × 90MB 分段）
│   ├── python/              ← Python 3.12 可攜版（39MB）
│   ├── wheels/              ← pip wheel 套件（完全離線安裝）
│   └── models/
│       ├── qwen3/           ← Qwen3-8B Q4_K_M（54 × 90MB 分段）
│       └── llama31/         ← Llama3.1-8B Q4_K_M（53 × 90MB 分段）
└── README.md
```

---

## 功能

| 模式 | 功能 |
|------|------|
| 💬 一般對話 | 與 AI 自由交流 |
| 📄 文件問答 | 上傳文件後針對內容提問 |
| 📝 文件摘要 | 自動生成結構化摘要 |
| 📊 資料提取 | 提取表格、數字、關鍵資訊 |
| 🌐 翻譯助手 | 中英文互譯 |
| 🔍 審閱校對 | 文件審閱與改善建議 |

**支援格式**：PDF · Excel (.xlsx) · Word (.docx) · PowerPoint (.pptx) · TXT · CSV

---

## AI 模型

| 模型 | 參數 | 大小 | 說明 |
|------|------|------|------|
| **Qwen3-8B Q4_K_M** | 8B | 4.7 GB | 推薦首選，繁體中文最佳 |
| **Llama 3.1 8B Instruct Q4_K_M** | 8B | 4.6 GB | 通用對話，英文能力優秀 |

---

## 系統需求

- Windows 10 x64（64 位元）
- RAM：16 GB 以上推薦（最低 8 GB）
- 磁碟：C 槽至少 15 GB 可用空間
- 不需要獨立顯示卡（CPU 推理，每秒約 2-8 tokens）

---

## 常見問題

**Q：clone 很慢怎麼辦？**
→ 正常，Repo 共 11.5 GB。若進度停滯超過 10 分鐘，可中斷後重新執行 `git clone`（Git 支援斷點續傳）。

**Q：安裝後介面顯示「無法連線 Ollama」**
→ 確認已執行 `C:\WinLLM\start.bat`，並等候 5 秒後重新整理瀏覽器。

**Q：回應速度慢**
→ 無 GPU 下 8B 模型每秒 2-8 tokens 為正常速度。

**Q：需要更新或重新安裝**
→ 執行 `git pull` 取得最新版本，再重新執行 `install.bat`。
