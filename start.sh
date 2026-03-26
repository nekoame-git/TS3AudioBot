#!/usr/bin/env bash
# TS3AudioBot + 录音 Web 界面启动脚本 (Linux/macOS)
# 用法：bash start.sh  （在 Bot 工作目录下运行）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 启动录音 Web 服务器（后台）────────────────────
if [ -f "recordings_server.py" ]; then
    echo "[start] 启动录音 Web 服务器..."
    python3 recordings_server.py &
    WEB_PID=$!
    echo "[start] 录音 Web 服务器 PID: $WEB_PID"
else
    echo "[start] 未找到 recordings_server.py，跳过 Web 服务器"
    WEB_PID=""
fi

# ── 启动 TS3AudioBot ──────────────────────────────
echo "[start] 启动 TS3AudioBot..."
dotnet TS3AudioBot.dll

# ── Bot 退出后停止 Web 服务器 ─────────────────────
if [ -n "$WEB_PID" ]; then
    echo "[start] 正在停止录音 Web 服务器 (PID $WEB_PID)..."
    kill "$WEB_PID" 2>/dev/null
fi
