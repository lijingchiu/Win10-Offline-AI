@echo off
chcp 65001 >nul
:: Win10 離線 AI — 安裝啟動器
:: 此檔案自動以管理員身分重新啟動 PowerShell 安裝腳本

:: Check if running as admin
net session >nul 2>&1
if errorlevel 1 (
    echo 需要管理員權限，重新以管理員身分執行...
    powershell -Command "Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0install.ps1\"' -Verb RunAs"
    exit /b
)

:: Already admin — run directly
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
