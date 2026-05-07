# 模型安裝說明

## 安裝精靈（自動）

執行 `WinLLM_Setup.exe` 時，安裝精靈會自動嘗試安裝模型：

1. **GitHub Releases 下載**（優先）：若本 Repo 的 Releases 中有 GGUF 檔案，自動下載
2. **Ollama 直接拉取**（備選）：執行 `ollama pull qwen3:8b`（需能連線至 registry.ollama.ai）
3. **本機 GGUF 匯入**（離線）：若在此資料夾放置 GGUF 檔案，自動匯入

---

## 離線安裝模型（公司網路限制時）

### 方法 A：在家下載後帶入公司（推薦）

1. 在家用電腦執行：
   ```powershell
   .\scripts\download_models_home.ps1
   ```
2. 將下載的 `.gguf` 檔案複製到 USB 隨身碟
3. 在公司電腦將 GGUF 檔案放至 `C:\WinLLM\models\`
4. 雙擊 `C:\WinLLM\scripts\import_model.bat`

### 方法 B：上傳至 GitHub Releases（IT 管理員）

將 GGUF 檔案上傳至本 Repo 的 Releases（tag: `latest-build`），
安裝精靈會自動從 GitHub 下載（GitHub 網域在公司可訪問）。

---

## 推薦模型

| 模型 | 大小 | Ollama 標籤 | 說明 |
|------|------|-------------|------|
| Qwen3-8B-Q4_K_M.gguf | ~5.2 GB | `qwen3:8b` | **最推薦**，多語言，理解力最強 |
| Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf | ~4.7 GB | `llama3.1:8b` | 英文能力優秀，通用對話 |
| Qwen3-4B-Q4_K_M.gguf | ~2.6 GB | `qwen3:4b` | 空間有限時的最佳選擇 |

### GGUF 檔案下載地址

- Qwen3-8B: https://huggingface.co/Qwen/Qwen3-8B-GGUF
- Llama-3.1-8B: https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF
- Qwen3-4B: https://huggingface.co/Qwen/Qwen3-4B-GGUF

---

## 手動 Ollama 指令

```bash
# 匯入本機 GGUF 檔案
echo "FROM C:/WinLLM/models/Qwen3-8B-Q4_K_M.gguf" > Modelfile
ollama create qwen3:8b -f Modelfile

# 查看已安裝模型
ollama list

# 刪除模型
ollama rm qwen3:8b
```

---

## 此目錄放置規範

安裝精靈會自動尋找此目錄下的以下檔案名稱：

```
C:\WinLLM\models\
├── qwen3-8b-q4_k_m.gguf       ← Qwen3 8B
├── llama3.1-8b-q4_k_m.gguf    ← Llama 3.1 8B
└── qwen3-4b-q4_k_m.gguf       ← Qwen3 4B（備選）
```
