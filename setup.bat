@echo off
title AMH Lab Tracker - 1-Click Setup
setlocal enabledelayedexpansion

echo ============================================================
echo   AMH Lab Tracker - Offline Setup
echo   Ahmadiyya Muslim Hospital, Mbale, Uganda
echo ============================================================
echo.

cd /d "%~dp0"

:: 1. Verify Python is installed and accessible on PATH
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found on your system PATH!
    echo.
    echo Please install Python (3.11+ recommended):
    echo   1. Run the Python installer (e.g., python-3.11.x-amd64.exe).
    echo   2. IMPORTANT: Check the box "Add Python to PATH" during installation.
    echo   3. After installing Python, run setup.bat again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Detected Python: %PY_VER%
echo.

:: 2. Install dependencies offline from local wheels
echo [1/3] Installing application dependencies offline...
if exist "offline_packages\wheels" (
    python -m pip install --no-index --find-links="offline_packages\wheels" -r requirements.txt
) else if exist "usb_drive\wheels" (
    python -m pip install --no-index --find-links="usb_drive\wheels" -r requirements.txt
) else if exist "wheels" (
    python -m pip install --no-index --find-links="wheels" -r requirements.txt
) else (
    echo [WARNING] Local wheels directory not found. Attempting standard install...
    python -m pip install -r requirements.txt
)

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install Python dependencies.
    echo Please verify that the wheels in 'offline_packages/wheels' match your Python version (%PY_VER%).
    echo.
    pause
    exit /b 1
)

echo [OK] Dependencies installed successfully.
echo.

:: 3. Run install.py (Database initialization + Desktop shortcut)
echo [2/3] Initializing database and creating shortcuts...
python install.py
if errorlevel 1 (
    echo.
    echo [ERROR] Setup script encountered an issue during database initialization.
    pause
    exit /b 1
)

echo.
echo [3/3] Setup Completed Successfully!
echo ============================================================
echo.
set /p START_NOW="Do you want to launch AMH Lab Tracker now? (Y/N): "
if /i "%START_NOW%"=="Y" (
    echo Launching AMH Lab Tracker...
    call run.bat
)

