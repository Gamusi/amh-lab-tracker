#!/usr/bin/env bash
echo "============================================================"
echo "  Starting AMH Lab Tracker Server..."
echo "  Ahmadiyya Muslim Hospital, Mbale, Uganda"
echo "============================================================"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR"

# Self-Healing: Check if port 8756 is in use, and automatically terminate the ghost process
echo "Checking for ghost processes on port 8756..."
PORT_PID=$(lsof -t -i:8756 2>/dev/null)
if [ -n "$PORT_PID" ]; then
    echo "Port 8756 is occupied by process PID $PORT_PID."
    echo "Terminating ghost process to free up port..."
    kill -9 $PORT_PID 2>/dev/null
    echo "Process $PORT_PID terminated."
fi

# Initialize DB & seed
python3 -m backend.app.seed

# Open web browser after 2s delay
(sleep 2 && python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8756/')") &
BROWSER_PID=$!

# Trap Ctrl+C (SIGINT) and exit (SIGTERM) to clean up background tasks
cleanup() {
    echo ""
    echo "Shutting down background processes..."
    # Kill browser launch timer if it's still running
    if kill -0 $BROWSER_PID 2>/dev/null; then
        kill $BROWSER_PID 2>/dev/null
    fi
    echo "System shutdown complete."
    exit 0
}
trap cleanup SIGINT SIGTERM

# Run FastAPI Uvicorn server in foreground so live logs are visible in shell
python3 backend/run_server.py
