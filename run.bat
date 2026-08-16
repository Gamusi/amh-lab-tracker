@echo off
title AMH Lab Tracker Server
echo ============================================================
echo   Starting AMH Lab Tracker Server...
echo   Ahmadiyya Muslim Hospital, Mbale, Uganda
echo ============================================================

cd /d "%~dp0"
set PYTHONPATH=%~dp0

:: Self-Healing: Check if port 8756 is in use, and automatically terminate the ghost process
echo Checking for ghost processes on port 8756...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8756 ^| findstr LISTENING') do (
    echo Port 8756 is occupied by process PID %%a.
    echo Terminating ghost process to free up port...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 0 (
        echo Process %%a terminated successfully.
    ) else (
        echo Failed to terminate process %%a.
    )
)

echo.
echo Checking database and applying seed data...
python -m backend.app.seed

echo.
echo Launching client browser...
start "" python -c "import time, webbrowser; time.sleep(2); webbrowser.open('http://127.0.0.1:8756/')"

echo.
echo Server starting. Press Ctrl+C inside this window to stop the server.
python backend\run_server.py

echo.
echo Server has stopped.
pause
