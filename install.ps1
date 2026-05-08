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
$LLAMA_TAG   = 'llama3.1:8b'

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
  ║        Win10 離線 AI — 一鍵安裝                         ║
  ║   Ollama + Qwen3-8B + Llama3.1-8B + Web UI             ║
  ║   完全離線，資料不外傳                                   ║
  ╚══════════════════════════════════════════════════════════╝
'@ -ForegroundColor Cyan

# ─── Pre-flight checks ────────────────────────────────────────────────────────
Head "步驟 1 / 7：環境檢查"

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
Head "步驟 2 / 7：安裝 Ollama"

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
Head "步驟 3 / 7：啟動 Ollama 服務"

$env:OLLAMA_ORIGINS = '*'
$running = WaitOllama -MaxSec 3
if (-not $running) {
    Info "啟動 Ollama serve..."
    Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden
    if (-not (WaitOllama -MaxSec 20)) { Warn "Ollama 啟動超時，繼續安裝（可能稍後才就緒）" }
}
OK "Ollama 服務就緒 (localhost:11434)"

# ─── Step 4: Python portable ─────────────────────────────────────────────────
Head "步驟 4 / 7：Python 3.12 可攜版"

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
Head "步驟 5 / 7：安裝 Python 套件（離線）"

$wheelCount = (Get-ChildItem "$WHEELS_DIR\*.whl" -ErrorAction SilentlyContinue).Count
if ($wheelCount -eq 0) {
    Warn "找不到 wheel 檔案，跳過（若後續文件解析失敗，請檢查 $WHEELS_DIR）"
} else {
    Info "安裝 $wheelCount 個本機 wheel 套件..."
    $result = & $pythonExe -m pip install --quiet --no-index --find-links $WHEELS_DIR `
        flask flask-cors pymupdf python-docx openpyxl python-pptx requests 2>&1
    if ($LASTEXITCODE -ne 0) {
        Warn "部分套件安裝警告（可能已安裝或有衝突）"
        Log "pip warning: $result"
    } else {
        OK "所有套件安裝完成"
    }
}

# ─── Step 6: Import AI Models ─────────────────────────────────────────────────
Head "步驟 6 / 7：匯入 AI 模型"

$models = @(
    @{ Tag="qwen3:8b";    Dir="qwen3";   Label="Qwen3 8B Q4_K_M";       GGUF="Qwen3-8B-Q4_K_M.gguf" },
    @{ Tag="llama3.1:8b"; Dir="llama31"; Label="Llama 3.1 8B Q4_K_M";   GGUF="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" }
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

# ─── Step 7: Deploy UI + shortcuts ───────────────────────────────────────────
Head "步驟 7 / 7：部署介面與捷徑"

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
    OK "文件服務已複製"
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

# Desktop shortcuts
$desk = [Environment]::GetFolderPath('Desktop')
ShortcutCreate "$INSTALL\start.bat" "$desk\Win10 离线 AI.lnk"
OK "桌面捷徑已建立"

# ─── Done ─────────────────────────────────────────────────────────────────────
Write-Host "`n"
Write-Host '  ╔══════════════════════════════════════════════════╗' -ForegroundColor Green
Write-Host '  ║   ✅  安裝完成！                                 ║' -ForegroundColor Green
Write-Host '  ║                                                  ║' -ForegroundColor Green
Write-Host '  ║   雙擊桌面「Win10 离线 AI」捷徑啟動             ║' -ForegroundColor Green
Write-Host '  ║   或執行  C:\WinLLM\start.bat                   ║' -ForegroundColor Green
Write-Host '  ╚══════════════════════════════════════════════════╝' -ForegroundColor Green

Log "=== 安裝完成 ==="
Write-Host ""
Read-Host "按 Enter 立即啟動 AI 介面"
Start-Process "$INSTALL\start.bat"
