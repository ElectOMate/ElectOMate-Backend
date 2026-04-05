#!/bin/bash
# Start Video Production Agent — Backend (5322) + Frontend (5321)
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Video Production Agent ==="
echo "  Backend:  http://localhost:5322"
echo "  Frontend: http://localhost:5321"
echo ""

# Load .env
if [ -f "$DIR/.env" ]; then
  export $(grep -v '^#' "$DIR/.env" | xargs)
elif [ -f "$DIR/../.env" ]; then
  export $(grep -v '^#' "$DIR/../.env" | xargs)
fi

# Setup Python venv if needed
if [ ! -d "$DIR/.venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$DIR/.venv"
  source "$DIR/.venv/bin/activate"
  pip install -r "$DIR/requirements.txt"
else
  source "$DIR/.venv/bin/activate"
fi

# Install frontend deps if needed
if [ ! -d "$DIR/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  cd "$DIR/frontend" && npm install && cd "$DIR"
fi

# Start backend
echo "Starting backend on :5322..."
cd "$DIR" && python -m uvicorn backend.main:app --host 0.0.0.0 --port 5322 --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on :5321..."
cd "$DIR/frontend" && npm run dev &
FRONTEND_PID=$!

echo ""
echo "Both servers running. Press Ctrl+C to stop."

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
