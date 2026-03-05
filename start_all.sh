#!/usr/bin/env bash
set -euo pipefail

# Start the resume chatbot backend on the Pi.
# Usage: ./start_all.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
PID_FILE="$BACKEND_DIR/uvicorn.pid"
LOG_FILE="$BACKEND_DIR/uvicorn.log"

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "Backend directory not found at: $BACKEND_DIR"
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Python venv not found at: $VENV_DIR"
  echo "Create it with: python -m venv backend/venv && source backend/venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Backend already running with PID $(cat "$PID_FILE")"
  exit 0
fi

source "$VENV_DIR/bin/activate"
cd "$BACKEND_DIR"

echo "Starting FastAPI backend with uvicorn..."
nohup uvicorn app:app --host 127.0.0.1 --port 8000 > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Backend started with PID $(cat "$PID_FILE"). Logs: $LOG_FILE"

