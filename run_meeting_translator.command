#!/bin/zsh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

PID_FILE="$SCRIPT_DIR/.streamlit_app.pid"
PORT="${STREAMLIT_PORT:-8501}"
HOST="${STREAMLIT_HOST:-127.0.0.1}"
APP_URL="http://localhost:$PORT"

if [ -f "$HOME/.zprofile" ]; then
  source "$HOME/.zprofile"
fi

echo "======================================"
echo "  Meeting Translator"
echo "======================================"
echo ""

# ============================================================================
# 函數定義
# ============================================================================

find_python() {
  local candidates=()

  if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    candidates+=("$SCRIPT_DIR/.venv/bin/python")
  fi
  if command -v python3 >/dev/null 2>&1; then
    candidates+=("$(command -v python3)")
  fi
  if command -v python >/dev/null 2>&1; then
    candidates+=("$(command -v python)")
  fi

  for candidate in "${candidates[@]}"; do
    if "$candidate" -c "import streamlit" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done

  return 1
}

is_port_ready() {
  local python_bin="$1"
  "$python_bin" - "$HOST" "$PORT" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    sys.exit(0 if sock.connect_ex((host, port)) == 0 else 1)
PY
}

open_browser_when_ready() {
  local python_bin="$1"

  for _ in {1..60}; do
    if is_port_ready "$python_bin"; then
      if [ "${AUTO_OPEN_BROWSER:-1}" != "0" ]; then
        open "$APP_URL"
      fi
      return 0
    fi
    sleep 0.5
  done

  echo "Browser auto-open skipped because the app was not ready in time."
}

prepare_build_env() {
  if command -v brew >/dev/null 2>&1 && brew list portaudio >/dev/null 2>&1; then
    PORTAUDIO_PREFIX=$(brew --prefix portaudio)
    export CFLAGS="-I${PORTAUDIO_PREFIX}/include ${CFLAGS:-}"
    export LDFLAGS="-L${PORTAUDIO_PREFIX}/lib ${LDFLAGS:-}"
    export PKG_CONFIG_PATH="${PORTAUDIO_PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
  fi
}

# ============================================================================
# 尋找 Python
# ============================================================================

PYTHON_BIN="$(find_python)" || {
  echo ""
  echo "Could not find a Python environment with Streamlit installed."
  echo ""
  echo "Install dependencies first:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  echo ""
  echo "Press any key to close..."
  read -k 1
  exit 1
}

if [ "$PYTHON_BIN" = "$SCRIPT_DIR/.venv/bin/python" ]; then
  echo "Using virtual environment: $SCRIPT_DIR/.venv"
else
  echo "Using python: $PYTHON_BIN"
fi

# ============================================================================
# 首次啟動：建立虛擬環境
# ============================================================================

if [ ! -d ".venv" ]; then
  echo ""
  echo "【首次啟動】正在建立虛擬環境..."
  echo ""

  # 檢查 portaudio
  if command -v brew >/dev/null 2>&1 && ! brew list portaudio >/dev/null 2>&1; then
    echo "正在安裝 portaudio（sounddevice 需要）..."
    brew install portaudio
  fi

  # 建立虛擬環境
  python3 -m venv .venv

  # 準備編譯環境
  prepare_build_env

  # 升級 pip 和建置工具
  echo "正在升級 pip 和建置工具..."
  .venv/bin/pip install --upgrade setuptools wheel
  .venv/bin/pip install --upgrade pip

  # 安裝依賴
  echo "正在安裝依賴套件（約需 1-2 分鐘）..."
  if ! .venv/bin/pip install -r requirements.txt; then
    echo ""
    echo "❌ 依賴安裝失敗"
    echo "Press any key to close..."
    read -k 1
    exit 1
  fi

  echo ""
  echo "✅ 虛擬環境建立完成！"
  echo ""

  # 重新找 python（現在 .venv 存在了）
  PYTHON_BIN="$(find_python)" || { echo "Cannot find Python after venv setup."; exit 1; }
fi

# ============================================================================
# 檢查套件更新
# ============================================================================

if [ -f "requirements.txt" ] && [ -f ".venv/pyvenv.cfg" ]; then
  if [ "requirements.txt" -nt ".venv/pyvenv.cfg" ]; then
    echo "偵測到套件更新，正在同步..."
    prepare_build_env
    .venv/bin/pip install -r requirements.txt
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
# 已在執行時直接開啟瀏覽器，不重複啟動
# ============================================================================

if [ -f "$PID_FILE" ]; then
  EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null)"
  if [ -n "${EXISTING_PID:-}" ] && kill -0 "$EXISTING_PID" >/dev/null 2>&1; then
    echo "Meeting Translator is already running with PID $EXISTING_PID"
    echo "URL: $APP_URL"
    if [ "${AUTO_OPEN_BROWSER:-1}" != "0" ]; then
      open "$APP_URL"
    fi
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if is_port_ready "$PYTHON_BIN"; then
  echo "Port $PORT is already serving an app."
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
echo "  🎙️ Meeting Translator 啟動中..."
echo "  URL: $APP_URL"
echo "  瀏覽器將自動開啟"
echo "  Terminal 視窗保持開啟即可"
echo "  停止請雙擊 stop_meeting_translator.command"
echo "======================================"
echo ""

echo "$$" > "$PID_FILE"

if [ "${AUTO_OPEN_BROWSER:-1}" != "0" ]; then
  open_browser_when_ready "$PYTHON_BIN" &
fi

exec "$PYTHON_BIN" -m streamlit run "$SCRIPT_DIR/app.py" \
  --server.headless true \
  --server.port "$PORT" \
  --server.address "$HOST"
