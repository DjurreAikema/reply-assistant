#!/usr/bin/env bash
# Mac and Linux equivalent of start.bat. Ctrl+C stops both.
set -e
cd "$(dirname "$0")"

(cd backend && . .venv/bin/activate && python run.py) &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT

cd frontend && npm start
