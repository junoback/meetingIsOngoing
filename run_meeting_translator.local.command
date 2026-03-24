#!/bin/bash
# -*- coding: utf-8 -*-
# ============================================================================
# 會議翻譯 App — 舊 Mac 本機啟動腳本
#
# 與主腳本的差異：
#   • bash（舊 macOS 沒有 zsh 預設）
#   • 自動掃描 Python 3.9 – 3.12
#   • portaudio 編譯環境（Intel Mac 需要）
#   • 使用 requirements.local.txt
#   • Port 8502（避免與其他機器衝突）
# ============================================================================

set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

REQ_FILE="requirements.local.txt"
PID_FILE="$DIR/.streamlit_app.pid"
PORT="${STREAMLIT_PORT:-8502}"
HOST="${STREAMLIT_HOST:-127.0.0.1}"
APP_URL="http://localhost:$PORT"
PYTHON_CMD=""

# ============================================================================
# 函數定義
# ============================================================================

find_compatible_python() {
    # 優先使用已建好的 venv
    if [ -x "$DIR/.venv/bin/python" ]; then
        PYTHON_CMD="$DIR/.venv/bin/python"
        return 0
    fi

    for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$candidate" > /dev/null 2>&1; then
            local version
            version=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            case "$version" in
                3.9|3.10|3.11|3.12)
                    PYTHON_CMD="$candidate"
                    return 0
                    ;;
            esac
        fi
    done
    return 1
}

prepare_build_env() {
    if command -v brew > /dev/null 2>&1 && brew list portaudio > /dev/null 2>&1; then
        local portaudio_prefix
        portaudio_prefix=$(brew --prefix portaudio)
        export CFLAGS="-I${portaudio_prefix}/include ${CFLAGS:-}"
        export LDFLAGS="-L${portaudio_prefix}/lib ${LDFLAGS:-}"
        export PKG_CONFIG_PATH="${portaudio_prefix}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
    fi
}

is_port_ready() {
    "$PYTHON_CMD" - "$HOST" "$PORT" <<'PY'
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(0.2)
    sys.exit(0 if s.connect_ex((host, port)) == 0 else 1)
PY
}

open_browser_when_ready() {
    local i
    for i in $(seq 1 60); do
        if is_port_ready; then
            if [ "${AUTO_OPEN_BROWSER:-1}" != "0" ]; then
                open "$APP_URL"
            fi
            return 0
        fi
        sleep 0.5
    done
    echo "⚠️ 瀏覽器自動開啟逾時，請手動開啟 $APP_URL"
}

stop_pid() {
    local pid="$1"
    if ! kill -0 "$pid" 2>/dev/null; then
        return 1
    fi
    kill "$pid" 2>/dev/null || true
    local i
    for i in $(seq 1 20); do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        sleep 0.25
    done
    kill -9 "$pid" 2>/dev/null || true
    return 0
}

# ============================================================================
# 開始
# ============================================================================

echo "======================================"
echo "  會議翻譯 App（舊 Mac 本機版）"
echo "======================================"
echo ""

# 尋找 Python
if ! find_compatible_python; then
    echo "❌ 錯誤：找不到相容的 Python（需要 3.9 – 3.12）"
    echo "請先執行：brew install python@3.11"
    echo ""
    read -p "按 Enter 關閉..."
    exit 1
fi

echo "使用 Python: $PYTHON_CMD"

# ============================================================================
# 首次啟動：建立虛擬環境
# ============================================================================

if [ ! -d ".venv" ]; then
    echo ""
    echo "【首次啟動】建立本機虛擬環境..."

    # 檢查 portaudio
    if command -v brew > /dev/null 2>&1 && ! brew list portaudio > /dev/null 2>&1; then
        echo "正在安裝 portaudio（sounddevice 需要）..."
        brew install portaudio
    fi

    "$PYTHON_CMD" -m venv .venv
    PYTHON_CMD="$DIR/.venv/bin/python"

    prepare_build_env
    .venv/bin/pip install --upgrade pip setuptools wheel
    if ! .venv/bin/pip install -r "$REQ_FILE"; then
        echo ""
        echo "❌ 依賴安裝失敗"
        read -p "按 Enter 關閉..."
        exit 1
    fi

    echo "✅ 虛擬環境建立完成！"
    echo ""
fi

# 確保 venv 建好後使用 venv 的 python
if [ -x "$DIR/.venv/bin/python" ]; then
    PYTHON_CMD="$DIR/.venv/bin/python"
fi

# ============================================================================
# 檢查套件更新
# ============================================================================

if [ -f "$REQ_FILE" ] && [ -f ".venv/pyvenv.cfg" ]; then
    if [ "$REQ_FILE" -nt ".venv/pyvenv.cfg" ]; then
        echo "偵測到本機依賴更新，正在同步..."
        prepare_build_env
        .venv/bin/pip install -r "$REQ_FILE"
        echo "✅ 套件已更新"
        echo ""
    fi
fi

# ============================================================================
# 建立必要目錄
# ============================================================================

mkdir -p recordings
mkdir -p transcripts

# ============================================================================
# 重複啟動偵測
# ============================================================================

if [ -f "$PID_FILE" ]; then
    EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null)"
    if [ -n "${EXISTING_PID:-}" ] && kill -0 "$EXISTING_PID" 2>/dev/null; then
        echo "Meeting Translator 已在執行中（PID $EXISTING_PID）"
        echo "URL: $APP_URL"
        if [ "${AUTO_OPEN_BROWSER:-1}" != "0" ]; then
            open "$APP_URL"
        fi
        exit 0
    fi
    rm -f "$PID_FILE"
fi

if is_port_ready; then
    echo "Port $PORT 已有程式在監聽。"
    echo "URL: $APP_URL"
    if [ "${AUTO_OPEN_BROWSER:-1}" != "0" ]; then
        open "$APP_URL"
    fi
    exit 0
fi

# ============================================================================
# 啟動 Streamlit App
# ============================================================================

echo ""
echo "======================================"
echo "  🎙️ 會議翻譯 App 本機版啟動中..."
echo "  URL: $APP_URL"
echo "  瀏覽器將自動開啟"
echo "  Terminal 視窗保持開啟即可"
echo "  停止請雙擊 stop_meeting_translator.local.command"
echo "======================================"
echo ""

echo "$$" > "$PID_FILE"

if [ "${AUTO_OPEN_BROWSER:-1}" != "0" ]; then
    open_browser_when_ready &
fi

exec .venv/bin/streamlit run app.py \
    --server.headless true \
    --server.port "$PORT" \
    --server.address "$HOST"
