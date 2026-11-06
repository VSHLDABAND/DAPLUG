#!/bin/bash
set -e
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 is required. Install Python 3 from python.org or your package manager."
  read -r -p "Press Return to close..."
  exit 1
fi
if [ ! -d ".venv" ]; then
  echo "Creating the local Python environment..."
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --disable-pip-version-check -r requirements.txt
HOST="${PROPERTY_OS_HOST:-127.0.0.1}"
PORT="${PROPERTY_OS_PORT:-8000}"
echo ""
echo "Property OS is starting. Open http://127.0.0.1:${PORT} in your browser."
if [ "$HOST" = "0.0.0.0" ]; then
  echo "LAN mode is enabled. Team members can use this Mac's local IP address on the same trusted network."
fi
echo "Press Ctrl+C to stop the server. Your database remains in ./data/"
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
