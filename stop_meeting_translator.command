#!/bin/zsh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PID_FILE="$SCRIPT_DIR/.streamlit_app.pid"
PORT="${STREAMLIT_PORT:-8501}"

stop_pid() {
  local pid="$1"

  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 1
  fi

  echo "Stopping Meeting Translator (PID $pid)..."
  kill "$pid" >/dev/null 2>&1 || true

  for _ in {1..20}; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done

  echo "Process did not exit cleanly; forcing termination."
  kill -9 "$pid" >/dev/null 2>&1 || true
  return 0
}

STOPPED=0

# 優先用 PID file 停止（這是 run_meeting_translator.command 寫入的）
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null)"
  if [ -n "${PID:-}" ] && stop_pid "$PID"; then
    STOPPED=1
  fi
  rm -f "$PID_FILE"
fi

# 再用 port 掃描作為 fallback（確保清除所有佔用該 port 的進程）
if command -v lsof >/dev/null 2>&1; then
  PORT_PIDS="$(lsof -ti tcp:"$PORT" 2>/dev/null || true)"
  if [ -n "$PORT_PIDS" ]; then
    for pid in $PORT_PIDS; do
      stop_pid "$pid" && STOPPED=1
    done
  fi
fi

if [ "$STOPPED" -eq 1 ]; then
  echo "Meeting Translator stopped."
else
  echo "No running Meeting Translator was found on port $PORT."
fi
