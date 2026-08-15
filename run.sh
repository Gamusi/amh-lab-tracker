#!/usr/bin/env bash
echo "============================================================"
echo "  Starting AMH Lab Tracker Server..."
echo "  Ahmadiyya Muslim Hospital, Mbale, Uganda"
echo "============================================================"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR"

# Initialize DB & seed
python3 -m backend.app.seed

# Open web browser after 2s delay
(sleep 2 && python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8756/')") &

# Run FastAPI Uvicorn server in foreground so live logs are visible in shell
python3 backend/run_server.py
