# TS3AudioBot + 录音 Web 界面启动脚本 (Windows PowerShell)
# 用法：在 Bot 工作目录下运行 .\start.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# ── 启动录音 Web 服务器（后台进程）──────────────
$webServerScript = Join-Path $scriptDir "recordings_server.py"
if (Test-Path $webServerScript) {
    Write-Host "[start] 启动录音 Web 服务器..." -ForegroundColor Cyan
    $webJob = Start-Process -FilePath "python" `
        -ArgumentList $webServerScript `
        -PassThru -NoNewWindow
    Write-Host "[start] 录音 Web 服务器 PID: $($webJob.Id)" -ForegroundColor Cyan
} else {
    Write-Host "[start] 未找到 recordings_server.py，跳过 Web 服务器" -ForegroundColor Yellow
}

# ── 启动 TS3AudioBot ─────────────────────────────
Write-Host "[start] 启动 TS3AudioBot..." -ForegroundColor Green
try {
    dotnet TS3AudioBot.dll
} finally {
    # Bot 退出后一并停止 Web 服务器
    if ($webJob -and !$webJob.HasExited) {
        Write-Host "`n[start] 正在停止录音 Web 服务器..." -ForegroundColor Cyan
        Stop-Process -Id $webJob.Id -Force -ErrorAction SilentlyContinue
    }
}
