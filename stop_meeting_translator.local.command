#!/bin/bash
# -*- coding: utf-8 -*-
# ============================================================================
# 會議翻譯 App — 舊 Mac 停止腳本
# Port 8502 版（對應 run_meeting_translator.local.command）
# ============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PID_FILE="$SCRIPT_DIR/.streamlit_app.pid"
PORT="${STREAMLIT_PORT:-8502}"

stop_pid() {
    local pid="$1"

    if ! kill -0 "$pid" 2>/dev/null; then
        return 1
    fi

    echo "正在停止 Meeting Translator（PID $pid）..."
    kill "$pid" 2>/dev/null || true

    local i
    for i in $(seq 1 20); do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        sleep 0.25
    done

    echo "程式未正常結束，強制終止..."
    kill -9 "$pid" 2>/dev/null || true
    return 0
}

STOPPED=0

# 優先用 PID file 停止
if [ -f "$PID_FILE" ]; then
    PID="$(cat "$PID_FILE" 2>/dev/null)"
    if [ -n "${PID:-}" ] && stop_pid "$PID"; then
        STOPPED=1
    fi
    rm -f "$PID_FILE"
fi

# Port fallback
if command -v lsof > /dev/null 2>&1; then
    PORT_PIDS="$(lsof -ti tcp:"$PORT" 2>/dev/null || true)"
    if [ -n "$PORT_PIDS" ]; then
        for pid in $PORT_PIDS; do
            stop_pid "$pid" && STOPPED=1
        done
    fi
fi

if [ "$STOPPED" -eq 1 ]; then
    echo "✅ Meeting Translator 已停止。"
else
    echo "未偵測到 Port $PORT 上有執行中的 Meeting Translator。"
fi
