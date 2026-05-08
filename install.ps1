#Requires -Version 5.1
<#
.SYNOPSIS
    Win10 離線 AI — 一鍵安裝腳本
    從本機 git clone 資料夾安裝 Ollama + Web UI + AI 模型
.NOTES
    請以「系統管理員」身分執行此腳本，或直接雙擊 install.bat
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # speeds up file ops

# ─────────────────────────────────────────────────────────────────────────────
$REPO_DIR   = Split-Path -Parent $MyInvocation.MyCommand.Path
$INSTALL    = 'C:\WinLLM'
$PYTHON_DIR = "$INSTALL\python"
$MODELS_DIR = "$INSTALL\models"
$WHEELS_DIR = "$REPO_DIR\setup\wheels"
$SETUP_DIR  = "$REPO_DIR\setup"
$LOG_FILE   = "$INSTALL\install.log"

$OLLAMA_TAG  = 'qwen3:8b'

# ─── Colours ─────────────────────────────────────────────────────────────────
function Info  ($m) { Write-Host "  $m" -ForegroundColor Cyan }
function OK    ($m) { Write-Host "  ✓ $m" -ForegroundColor Green }
function Warn  ($m) { Write-Host "  ⚠  $m" -ForegroundColor Yellow }
function Err   ($m) { Write-Host "  ✗ $m" -ForegroundColor Red }
function Head  ($m) { Write-Host "`n══ $m ══" -ForegroundColor Magenta }
function Log   ($m) { Add-Content -Path $LOG_FILE -Value "$(Get-Date -f 'HH:mm:ss') $m" }

# ─── Helpers ─────────────────────────────────────────────────────────────────
function IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p  = [Security.Principal.WindowsPrincipal]$id
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assemble ($chunkDir, $destFile) {
    # Concatenate all chunk.* files in order into destFile
    $chunks = Get-ChildItem "$chunkDir\chunk.*" | Sort-Object Name
    if (-not $chunks) { throw "No chunks found in $chunkDir" }
    $stream = [IO.File]::OpenWrite($destFile)
    try {
        foreach ($c in $chunks) {
            $buf = [IO.File]::ReadAllBytes($c.FullName)
            $stream.Write($buf, 0, $buf.Length)
            $buf = $null
        }
    } finally { $stream.Close() }
    OK "組合完成：$(Split-Path -Leaf $destFile) ($([math]::Round((Get-Item $destFile).Length/1GB,2)) GB)"
}

function FindOllama {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        'C:\Program Files\Ollama\ollama.exe',
        (Get-Command ollama -ErrorAction SilentlyContinue)?.Source
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    return $null
}

function WaitOllama {
    param([int]$MaxSec = 30)
    for ($i = 0; $i -lt $MaxSec; $i++) {
        try {
            $r = Invoke-RestMethod 'http://localhost:11434/api/tags' -TimeoutSec 2 -ErrorAction Stop
            return $true
        } catch { Start-Sleep 1 }
    }
    return $false
}

function ShortcutCreate ($targetPath, $linkPath) {
    $wsh = New-Object -ComObject WScript.Shell
    $sc  = $wsh.CreateShortcut($linkPath)
    $sc.TargetPath = $targetPath
    $sc.Save()
}

# ─── Banner ───────────────────────────────────────────────────────────────────
Clear-Host
Write-Host @'
  ╔══════════════════════════════════════════════════════════╗
  ║        Win10 離線 AI — 一鍵安裝 v2.0                    ║
  ║   Ollama + Qwen2.5-7B + Qwen3-8B + Excel Agent + Web UI ║
  ║   完全離線，資料不外傳                                   ║
  ╚══════════════════════════════════════════════════════════╝
'@ -ForegroundColor Cyan

# ─── Pre-flight checks ────────────────────────────────────────────────────────
Head "步驟 1 / 8：環境檢查"

if (-not (IsAdmin)) {
    Err "需要管理員權限！"
    Write-Host "  請右鍵點擊 install.bat → 以系統管理員身分執行" -ForegroundColor Yellow
    Read-Host "按 Enter 離開"
    exit 1
}
OK "管理員權限確認"

$free = (Get-PSDrive C).Free
if ($free -lt 15GB) {
    Warn "C 磁碟可用空間不足 15 GB（目前 $([math]::Round($free/1GB,1)) GB）"
    $ans = Read-Host "  是否繼續？(y/N)"
    if ($ans -ne 'y') { exit 1 }
}
OK "磁碟空間：$([math]::Round($free/1GB,1)) GB 可用"

# Create install directory and log
New-Item -ItemType Directory -Force -Path $INSTALL   | Out-Null
New-Item -ItemType Directory -Force -Path $MODELS_DIR | Out-Null
Log "=== 安裝開始 ==="
OK "安裝目錄：$INSTALL"

# ─── Step 2: Install Ollama ───────────────────────────────────────────────────
Head "步驟 2 / 8：安裝 Ollama"

$ollamaExe = FindOllama
if ($ollamaExe) {
    OK "Ollama 已安裝：$ollamaExe"
} else {
    $ollamaSetup = "$INSTALL\_tmp_OllamaSetup.exe"

    if (-not (Test-Path $ollamaSetup)) {
        Info "組合 OllamaSetup.exe（共 23 段）..."
        Assemble "$SETUP_DIR\ollama" $ollamaSetup
    }

    Info "靜默安裝 Ollama..."
    $proc = Start-Process -FilePath $ollamaSetup `
                          -ArgumentList '/SILENT', '/NORESTART' `
                          -Wait -PassThru
    if ($proc.ExitCode -notin 0, 3010) {
        throw "Ollama 安裝失敗（exit $($proc.ExitCode)）"
    }
    Remove-Item $ollamaSetup -Force -ErrorAction SilentlyContinue
    OK "Ollama 安裝完成"
    $ollamaExe = FindOllama
    if (-not $ollamaExe) { throw "安裝後仍找不到 ollama.exe" }
}

# ─── Step 3: Start Ollama service ─────────────────────────────────────────────
Head "步驟 3 / 8：啟動 Ollama 服務"

$env:OLLAMA_ORIGINS = '*'
$running = WaitOllama -MaxSec 3
if (-not $running) {
    Info "啟動 Ollama serve..."
    Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden
    if (-not (WaitOllama -MaxSec 20)) { Warn "Ollama 啟動超時，繼續安裝（可能稍後才就緒）" }
}
OK "Ollama 服務就緒 (localhost:11434)"

# ─── Step 4: Python portable ─────────────────────────────────────────────────
Head "步驟 4 / 8：Python 3.12 可攜版"

$pythonExe = "$PYTHON_DIR\python.exe"
if (Test-Path $pythonExe) {
    OK "Python 已存在：$pythonExe"
} else {
    $pyArchive = "$SETUP_DIR\python\python-3.12-win64.tar.gz"
    if (-not (Test-Path $pyArchive)) { throw "找不到 $pyArchive" }
    Info "解壓縮 Python 3.12..."

    # Use tar (built into Windows 10 since 2018)
    $null = New-Item -ItemType Directory -Force "$INSTALL\_pytmp"
    tar -xzf $pyArchive -C "$INSTALL\_pytmp" 2>&1 | Out-Null
    # Find extracted dir and move
    $extracted = Get-ChildItem "$INSTALL\_pytmp" -Directory | Select-Object -First 1
    if ($extracted) {
        Move-Item $extracted.FullName $PYTHON_DIR -Force
    }
    Remove-Item "$INSTALL\_pytmp" -Recurse -Force -ErrorAction SilentlyContinue
    OK "Python 3.12 就緒：$pythonExe"
}

# ─── Step 5: Install pip wheels ───────────────────────────────────────────────
Head "步驟 5 / 8：安裝 Python 套件（離線）"

$wheelCount = (Get-ChildItem "$WHEELS_DIR\*.whl" -ErrorAction SilentlyContinue).Count
if ($wheelCount -eq 0) {
    Warn "找不到 wheel 檔案，跳過（若後續功能失效，請檢查 $WHEELS_DIR）"
} else {
    Info "安裝 $wheelCount 個本機 wheel 套件..."
    # Core document packages
    $result = & $pythonExe -m pip install --quiet --no-index --find-links $WHEELS_DIR `
        flask flask-cors pymupdf python-docx openpyxl python-pptx requests 2>&1
    if ($LASTEXITCODE -ne 0) {
        Warn "部分套件安裝警告: $result"
        Log "pip warning: $result"
    } else {
        OK "文件處理套件安裝完成"
    }
    # Agent packages (pandas, numpy, xlwings, BM25, jieba, json-repair)
    Info "安裝 Excel Agent 套件..."
    $agentPkgs = "pandas numpy python-dateutil pytz tzdata six pywin32 xlwings rank-bm25 jieba json-repair"
    $result2 = & $pythonExe -m pip install --quiet --no-index --find-links $WHEELS_DIR $agentPkgs 2>&1
    if ($LASTEXITCODE -ne 0) {
        Warn "Agent 套件安裝警告（若 Excel Agent 功能異常請檢查）: $result2"
        Log "agent pip warning: $result2"
    } else {
        OK "Excel Agent 套件安裝完成"
    }
    # pywin32 post-install (required for xlwings COM on Windows)
    $pywin32PostInstall = "$PYTHON_DIR\Scripts\pywin32_postinstall.py"
    if (Test-Path $pywin32PostInstall) {
        Info "執行 pywin32 後置安裝..."
        & $pythonExe $pywin32PostInstall -install 2>&1 | Out-Null
        OK "pywin32 後置安裝完成"
    }
}

# ─── Step 6: Import AI Models ─────────────────────────────────────────────────
Head "步驟 6 / 8：匯入 AI 模型"

$models = @(
    @{ Tag="qwen2.5:7b";  Dir="qwen25_7b"; Label="Qwen2.5-7B-Instruct Q4_K_M (Agent 主力)"; GGUF="Qwen2.5-7B-Instruct-Q4_K_M.gguf" },
    @{ Tag="qwen3:8b";    Dir="qwen3";     Label="Qwen3 8B Q4_K_M (備選)";                  GGUF="Qwen3-8B-Q4_K_M.gguf" }
)

foreach ($m in $models) {
    Info "── $($m.Label) ──"
    # Check if already imported
    $list = & $ollamaExe list 2>&1
    if ($list -match [regex]::Escape($m.Tag)) {
        OK "$($m.Tag) 已匯入，跳過"
        continue
    }

    $ggufDest = "$MODELS_DIR\$($m.GGUF)"

    if (-not (Test-Path $ggufDest) -or (Get-Item $ggufDest).Length -lt 1GB) {
        Info "組合 $($m.GGUF)（每段 90 MB）..."
        Assemble "$SETUP_DIR\models\$($m.Dir)" $ggufDest
    } else {
        OK "GGUF 已存在，直接匯入"
    }

    # Create Modelfile and import
    $mfPath = "$MODELS_DIR\$($m.Tag -replace ':','_').Modelfile"
    "FROM $ggufDest" | Set-Content $mfPath -Encoding UTF8

    Info "Ollama 匯入中（請耐心等候，約需 1-3 分鐘）..."
    $proc = Start-Process -FilePath $ollamaExe `
                          -ArgumentList "create", $m.Tag, "-f", $mfPath `
                          -Wait -PassThru -WindowStyle Hidden
    if ($proc.ExitCode -eq 0) {
        OK "$($m.Tag) 匯入完成！"
        Remove-Item $ggufDest, $mfPath -Force -ErrorAction SilentlyContinue
        Log "Model imported: $($m.Tag)"
    } else {
        Warn "$($m.Tag) 匯入失敗（exit $($proc.ExitCode)）"
        Log "Model import failed: $($m.Tag)"
    }
}

# ─── Step 7: Deploy UI + agent module ────────────────────────────────────────
Head "步驟 7 / 8：部署介面與 Agent 模組"

$agentDir = "$INSTALL\agent"

# Copy frontend
$frontendSrc = "$REPO_DIR\frontend"
$frontendDst = "$INSTALL\frontend"
if (Test-Path $frontendSrc) {
    Copy-Item $frontendSrc $frontendDst -Recurse -Force
    OK "網頁介面已複製至 $frontendDst"
}

# Copy server.py
$serverSrc = "$REPO_DIR\server\server.py"
if (Test-Path $serverSrc) {
    Copy-Item $serverSrc "$INSTALL\server.py" -Force
    OK "後端服務已複製"
}

# Copy agent/ directory
$agentSrc = "$REPO_DIR\agent"
if (Test-Path $agentSrc) {
    if (Test-Path $agentDir) { Remove-Item $agentDir -Recurse -Force }
    Copy-Item $agentSrc $agentDir -Recurse -Force
    OK "Excel Agent 模組已複製至 $agentDir"
}

# Copy config/
$configSrc = "$REPO_DIR\config"
if (Test-Path $configSrc) {
    Copy-Item $configSrc "$INSTALL\config" -Recurse -Force
    OK "設定檔已複製"
}

# Create backups and sessions directories
New-Item -ItemType Directory -Force -Path "$INSTALL\backups"  | Out-Null
New-Item -ItemType Directory -Force -Path "$INSTALL\sessions" | Out-Null
OK "備份與暫存目錄已建立"

# ─── Step 8: Build index + launchers + shortcuts ─────────────────────────────
Head "步驟 8 / 8：建立索引與啟動捷徑"

# Build BM25 tool index now that agent/ is deployed
if (Test-Path "$agentDir\build_index.py") {
    Info "建立 BM25 工具檢索索引..."
    $idxResult = & $pythonExe "$agentDir\build_index.py" 2>&1
    if ($LASTEXITCODE -eq 0) {
        OK "工具索引建立完成"
    } else {
        Warn "工具索引建立失敗（可在 start.bat 啟動後自動重建）: $idxResult"
        Log "build_index failed: $idxResult"
    }
} else {
    Warn "找不到 build_index.py（Excel Agent 將無法使用）"
    Log "build_index.py missing"
}

# Write start.bat
$startBat = @"
@echo off
chcp 65001 >nul
title Win10 离线 AI
set OLLAMA_ORIGINS=*
echo 啟動 Ollama...
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find "ollama.exe" >nul || start "" /B "$($ollamaExe.Replace('\','\\'))" serve
timeout /t 4 /nobreak >nul
echo 啟動文件服務...
start "" /B "$($pythonExe.Replace('\','\\'))" "$INSTALL\server.py"
timeout /t 2 /nobreak >nul
echo 開啟 AI 介面...
start "" "http://localhost:8765"
"@
$startBat | Set-Content "$INSTALL\start.bat" -Encoding UTF8
OK "start.bat 已建立"

# Write stop.bat
@'
@echo off
chcp 65001 >nul
taskkill /F /IM ollama.exe /T >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| find ":8765"') do taskkill /F /PID %%a >nul 2>&1
echo 所有服務已停止。
'@ | Set-Content "$INSTALL\stop.bat" -Encoding UTF8

# Write update.bat (update app files without reinstalling Ollama/models)
$updateBat = @"
@echo off
chcp 65001 >nul
echo 更新 Win10 离线 AI 應用程式檔案...
set REPO=%~dp0
xcopy /E /Y /I "%REPO%server\server.py" "$INSTALL\server.py*" >nul
xcopy /E /Y /I "%REPO%agent" "$INSTALL\agent\" >nul
xcopy /E /Y /I "%REPO%frontend" "$INSTALL\frontend\" >nul
xcopy /E /Y /I "%REPO%config" "$INSTALL\config\" >nul
"$($pythonExe.Replace('\','\\'))" "$INSTALL\agent\build_index.py"
echo 更新完成！請重新啟動服務。
pause
"@
$updateBat | Set-Content "$INSTALL\update.bat" -Encoding UTF8
OK "update.bat 已建立"

# Desktop shortcuts
$desk = [Environment]::GetFolderPath('Desktop')
ShortcutCreate "$INSTALL\start.bat" "$desk\Win10 离线 AI.lnk"
ShortcutCreate "$INSTALL\stop.bat"  "$desk\停止 AI 服務.lnk"
OK "桌面捷徑已建立"

# ─── Done ─────────────────────────────────────────────────────────────────────
Write-Host "`n"
Write-Host '  ╔════════════════════════════════════════════════════════╗' -ForegroundColor Green
Write-Host '  ║   ✅  安裝完成！                                       ║' -ForegroundColor Green
Write-Host '  ║                                                        ║' -ForegroundColor Green
Write-Host '  ║   • 雙擊桌面「Win10 离线 AI」捷徑啟動                ║' -ForegroundColor Green
Write-Host '  ║   • 包含 Excel Agent + 文件問答 + 備份管理            ║' -ForegroundColor Green
Write-Host '  ║   • 更新應用程式：執行 C:\WinLLM\update.bat          ║' -ForegroundColor Green
Write-Host '  ╚════════════════════════════════════════════════════════╝' -ForegroundColor Green

Log "=== 安裝完成 v2.0 ==="
Write-Host ""
Read-Host "按 Enter 立即啟動 AI 介面"
Start-Process "$INSTALL\start.bat"
