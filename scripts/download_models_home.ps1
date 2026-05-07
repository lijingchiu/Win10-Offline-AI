<#
.SYNOPSIS
    在家用電腦（可上網）下載 GGUF 模型，以便帶到公司離線使用。
.DESCRIPTION
    此腳本在可上網的電腦執行，下載 GGUF 模型後存放到指定資料夾。
    將資料夾複製到 USB 或公司電腦後，使用 import_model.bat 匯入。
.EXAMPLE
    .\download_models_home.ps1 -OutputDir D:\AI_Models
#>

param(
    [string]$OutputDir = "$env:USERPROFILE\Desktop\AI_Models"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

Write-Host @"
╔══════════════════════════════════════════════════════╗
║    Win10 离线 AI — 在家下載模型工具                  ║
║    下載完成後複製到公司電腦並執行 import_model.bat   ║
╚══════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Write-Host "`n輸出資料夾：$OutputDir`n" -ForegroundColor Green

$models = @(
    @{
        Name    = "Qwen3-8B (Q4_K_M, ~5.2GB) — 推薦，最智慧"
        HFRepo  = "Qwen/Qwen3-8B-GGUF"
        File    = "Qwen3-8B-Q4_K_M.gguf"
        OllamaTag = "qwen3:8b"
    },
    @{
        Name    = "Llama-3.1-8B-Instruct (Q4_K_M, ~4.7GB) — 通用對話"
        HFRepo  = "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"
        File    = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
        OllamaTag = "llama3.1:8b"
    },
    @{
        Name    = "Qwen3-4B (Q4_K_M, ~2.6GB) — 較小體積，性能優秀"
        HFRepo  = "Qwen/Qwen3-4B-GGUF"
        File    = "Qwen3-4B-Q4_K_M.gguf"
        OllamaTag = "qwen3:4b"
    }
)

Write-Host "可下載的模型：`n"
for ($i = 0; $i -lt $models.Count; $i++) {
    Write-Host "  [$($i+1)] $($models[$i].Name)"
}
Write-Host "  [0] 全部下載`n"

$choice = Read-Host "請選擇要下載的模型 (輸入數字)"

$toDownload = if ($choice -eq "0") { $models }
              elseif ($choice -match "^[1-9]$" -and [int]$choice -le $models.Count) { @($models[[int]$choice - 1]) }
              else { Write-Host "無效選擇" -ForegroundColor Red; exit 1 }

foreach ($model in $toDownload) {
    $destFile = Join-Path $OutputDir $model.File
    if (Test-Path $destFile) {
        $size = [math]::Round((Get-Item $destFile).Length / 1GB, 2)
        Write-Host "`n✓ 已存在：$($model.File) ($size GB)，跳過" -ForegroundColor Green
        continue
    }

    $url = "https://huggingface.co/$($model.HFRepo)/resolve/main/$($model.File)"
    Write-Host "`n⬇  下載：$($model.Name)" -ForegroundColor Yellow
    Write-Host "   來源：$url"
    Write-Host "   目標：$destFile`n"

    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("User-Agent", "WinLLM-Downloader/1.0")
        $wc.DownloadProgressChanged += {
            param($s, $e)
            Write-Progress -Activity "下載 $($model.File)" `
                -Status "$($e.ProgressPercentage)% ($([math]::Round($e.BytesReceived/1MB))MB)" `
                -PercentComplete $e.ProgressPercentage
        }
        $wc.DownloadFileAsync([Uri]$url, $destFile)
        while ($wc.IsBusy) { Start-Sleep -Milliseconds 500 }
        Write-Progress -Activity "下載 $($model.File)" -Completed
        Write-Host "✅ 下載完成：$($model.File)" -ForegroundColor Green
    } catch {
        Write-Host "❌ 下載失敗：$($_.Exception.Message)" -ForegroundColor Red
    }
}

# Write import instructions
$readme = Join-Path $OutputDir "使用說明.txt"
@"
== AI 模型使用說明 ==

1. 將此資料夾複製到公司電腦的 C:\WinLLM\models\ 目錄下
2. 在公司電腦執行：C:\WinLLM\scripts\import_model.bat
3. 依照提示輸入 GGUF 檔案路徑和模型標籤

模型標籤對應：
$(foreach ($m in $models) { "  $($m.File) → $($m.OllamaTag)`n" })

4. 匯入完成後，雙擊桌面「Win10 离线 AI」啟動
"@ | Set-Content $readme -Encoding UTF8

Write-Host "`n下載完成！使用說明已存至：$readme" -ForegroundColor Cyan
Write-Host "請將整個資料夾複製到公司電腦的 C:\WinLLM\models\ 後執行 import_model.bat`n"
Pause
