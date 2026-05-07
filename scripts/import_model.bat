@echo off
chcp 65001 >nul
title 匯入 GGUF 模型至 Ollama

echo =============================================
echo   Win10 离线 AI — 手動匯入 GGUF 模型工具
echo =============================================
echo.
echo 此工具可將 .gguf 格式的模型檔案匯入 Ollama。
echo.
echo 建議模型及下載地址（需在可上網電腦下載後複製）：
echo.
echo  [1] Qwen3-8B  Q4_K_M (~5.2GB)
echo      https://huggingface.co/Qwen/Qwen3-8B-GGUF
echo.
echo  [2] Llama-3.1-8B  Q4_K_M (~4.7GB)
echo      https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF
echo.
echo  [3] Qwen3-4B  Q4_K_M (~2.6GB，較小但仍良好)
echo      https://huggingface.co/Qwen/Qwen3-4B-GGUF
echo.
echo ─────────────────────────────────────────────
echo.

set /p GGUF_PATH=請輸入 GGUF 檔案的完整路徑（或直接拖放檔案至此視窗）:
:: Remove surrounding quotes if any
set GGUF_PATH=%GGUF_PATH:"=%

if not exist "%GGUF_PATH%" (
    echo [ERROR] 找不到檔案: %GGUF_PATH%
    pause
    exit /b 1
)

echo.
set /p MODEL_TAG=請輸入模型標籤 (例如 qwen3:8b 或 llama3.1:8b):
if "%MODEL_TAG%"=="" (
    echo [ERROR] 模型標籤不能為空
    pause
    exit /b 1
)

:: Find ollama
set OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe
if not exist "%OLLAMA_EXE%" set OLLAMA_EXE=C:\Program Files\Ollama\ollama.exe
if not exist "%OLLAMA_EXE%" (
    for /f "delims=" %%i in ('where ollama 2^>nul') do set OLLAMA_EXE=%%i
)

if not exist "%OLLAMA_EXE%" (
    echo [ERROR] 找不到 ollama.exe，請先安裝 Ollama
    pause
    exit /b 1
)

:: Write Modelfile
set MODELFILE=C:\WinLLM\models\import_temp.Modelfile
if not exist "C:\WinLLM\models" mkdir "C:\WinLLM\models"
echo FROM %GGUF_PATH% > "%MODELFILE%"

echo.
echo 正在匯入模型 %MODEL_TAG%，請稍候（可能需要數分鐘）...
echo.

"%OLLAMA_EXE%" create %MODEL_TAG% -f "%MODELFILE%"

if errorlevel 1 (
    echo.
    echo [ERROR] 模型匯入失敗，請檢查 GGUF 檔案是否完整。
) else (
    echo.
    echo [SUCCESS] 模型 %MODEL_TAG% 匯入成功！
    echo 現在可以在 AI 介面中選擇此模型使用。
    del "%MODELFILE%" >nul 2>&1
)

echo.
pause
