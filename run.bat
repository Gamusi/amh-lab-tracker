@echo off
title AMH Lab Tracker Server
echo ============================================================
echo   Starting AMH Lab Tracker Server...
echo   Ahmadiyya Muslim Hospital, Mbale, Uganda
echo ============================================================

cd /d "%~dp0"
set PYTHONPATH=%~dp0

python -m backend.app.seed

start "" python -c "import time, webbrowser; time.sleep(2); webbrowser.open('http://127.0.0.1:8756/')"

python backend\run_server.py

pause
