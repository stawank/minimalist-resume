#!/usr/bin/env bash
set -euo pipefail

# Stop the resume chatbot backend on the Pi.
# Usage: ./stop_all.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
PID_FILE="$BACKEND_DIR/uvicorn.pid"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping backend (PID $PID)..."
    kill "$PID" || true
  else
    echo "No running process found for PID $PID."
  fi
  rm -f "$PID_FILE"
else
  echo "PID file not found, trying to stop any uvicorn app:app process..."
  pkill -f "uvicorn app:app" 2>/dev/null || true
fi

echo "Done."

