@echo off
chcp 65001 >nul
title Win10 离线 AI

:: ── 啟動 Ollama 服務 ────────────────────────────────────────────────────────
echo [1/3] 啟動 Ollama LLM 服務...
set OLLAMA_ORIGINS=*
set OLLAMA_HOST=127.0.0.1:11434

:: Find ollama.exe
set OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe
if not exist "%OLLAMA_EXE%" set OLLAMA_EXE=C:\Program Files\Ollama\ollama.exe
if not exist "%OLLAMA_EXE%" (
    for /f "delims=" %%i in ('where ollama 2^>nul') do set OLLAMA_EXE=%%i
)

if not exist "%OLLAMA_EXE%" (
    echo [ERROR] 找不到 ollama.exe，請確認 Ollama 已安裝。
    echo 下載地址: https://github.com/ollama/ollama/releases
    pause
    exit /b 1
)

tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if errorlevel 1 (
    start "" /B "%OLLAMA_EXE%" serve
    timeout /t 4 /nobreak >nul
    echo     Ollama 服務已啟動
) else (
    echo     Ollama 服務已在運行中
)

:: ── 啟動文件處理服務 ──────────────────────────────────────────────────────────
echo [2/3] 啟動文件處理服務...
set PYTHON_EXE=C:\WinLLM\python\python.exe
set SERVER_PY=C:\WinLLM\server.py

if not exist "%PYTHON_EXE%" (
    echo [WARN] 找不到可攜式 Python，嘗試系統 Python...
    set PYTHON_EXE=python
)

tasklist /FI "WINDOWTITLE eq WinLLM-Server*" 2>nul | find "python" >nul
if errorlevel 1 (
    if exist "%SERVER_PY%" (
        start "WinLLM-Server" /B "%PYTHON_EXE%" "%SERVER_PY%"
        timeout /t 2 /nobreak >nul
        echo     文件處理服務已啟動 (port 8765)
    ) else (
        echo [WARN] 找不到 server.py，跳過文件服務
    )
) else (
    echo     文件處理服務已在運行中
)

:: ── 開啟瀏覽器 ────────────────────────────────────────────────────────────────
echo [3/3] 開啟 AI 介面...
timeout /t 1 /nobreak >nul
start "" "http://localhost:8765"

echo.
echo ========================================
echo  Win10 离线 AI 已啟動！
echo  瀏覽器應已自動開啟
echo  介面地址: http://localhost:8765
echo ========================================
echo.
echo 按任意鍵關閉此視窗（不影響 AI 服務運行）
pause >nul
