@echo off
chcp 65001 >nul
title 停止 Win10 离线 AI

echo 正在停止所有 AI 服務...
taskkill /F /IM ollama.exe /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq WinLLM-Server*" /T >nul 2>&1
:: Also kill any python.exe serving on 8765
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| find ":8765"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo 所有服務已停止。
timeout /t 2
