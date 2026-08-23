@echo off
title AMH Lab Tracker - System Setup
setlocal enabledelayedexpansion

cd /d "%~dp0"
set "LOG_FILE=%~dp0setup_debug.log"

echo ============================================================ > "%LOG_FILE%"
echo   AMH Lab Tracker - Setup Debug Log >> "%LOG_FILE%"
echo   Date/Time: %DATE% %TIME% >> "%LOG_FILE%"
echo   Directory: %~dp0 >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

echo ============================================================
echo   AMH Lab Tracker - Offline System Setup
echo   Ahmadiyya Muslim Hospital, Mbale, Uganda
echo ============================================================
echo.
echo Setup log will be saved to: setup_debug.log
echo.

:: -------------------------------------------------------------
:: Step 1: Detect Python executable
:: -------------------------------------------------------------
echo [1/4] Detecting Python installation...
set "PY_CMD="

:: Check direct python on PATH
python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :PYTHON_FOUND
)

:: Check py launcher on PATH
py --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py"
    goto :PYTHON_FOUND
)

:: Search LocalAppData user installations
for %%V in (Python314 Python313 Python312 Python311 Python310 Python39) do (
    if exist "%LOCALAPPDATA%\Programs\Python\%%V\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\%%V\python.exe"
        goto :PYTHON_FOUND
    )
)

:: Search Program Files installations
for %%V in (Python314 Python313 Python312 Python311 Python310 Python39) do (
    if exist "C:\Program Files\Python\%%V\python.exe" (
        set "PY_CMD=C:\Program Files\Python\%%V\python.exe"
        goto :PYTHON_FOUND
    )
    if exist "C:\Program Files\Python%%V\python.exe" (
        set "PY_CMD=C:\Program Files\Python%%V\python.exe"
        goto :PYTHON_FOUND
    )
    if exist "C:\Python%%V\python.exe" (
        set "PY_CMD=C:\Python%%V\python.exe"
        goto :PYTHON_FOUND
    )
)

:PYTHON_NOT_FOUND
echo.
echo [ERROR] Python was NOT detected on this computer!
echo [ERROR] Python was NOT detected on this computer! >> "%LOG_FILE%"
echo.
echo Please complete the following step:
echo   1. Run your Python installer (e.g. python-3.11.x-amd64.exe).
echo   2. CRITICAL: Check the box "Add Python to PATH" on the first screen.
echo   3. After installing Python, double-click setup.bat again.
echo.
echo For more help, see INSTRUCTIONS.txt or setup_debug.log
echo.
pause
exit /b 1

:PYTHON_FOUND
echo Python executable found: %PY_CMD% >> "%LOG_FILE%"
for /f "tokens=*" %%v in ('"%PY_CMD%" --version 2^>^&1') do set "PY_VER=%%v"
echo [OK] Detected Python: !PY_VER! (Path: %PY_CMD%)
echo Detected Python: !PY_VER! >> "%LOG_FILE%"
echo.

:: -------------------------------------------------------------
:: Step 2: Install offline wheels
:: -------------------------------------------------------------
echo [2/4] Installing dependencies offline from local packages...
set "WHEELS_DIR=%~dp0offline_packages\wheels"

if not exist "%WHEELS_DIR%" (
    if exist "%~dp0wheels" set "WHEELS_DIR=%~dp0wheels"
)

echo Wheels directory: %WHEELS_DIR% >> "%LOG_FILE%"

if exist "%WHEELS_DIR%" (
    echo Installing from local wheels directory: %WHEELS_DIR%
    "%PY_CMD%" -m pip install --no-index --find-links="%WHEELS_DIR%" -r requirements.txt >> "%LOG_FILE%" 2>&1
) else (
    echo [WARNING] Offline wheels folder not found. Attempting standard install...
    "%PY_CMD%" -m pip install -r requirements.txt >> "%LOG_FILE%" 2>&1
)

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install Python dependencies!
    echo [ERROR] Failed to install Python dependencies! >> "%LOG_FILE%"
    echo.
    echo Possible causes:
    echo   1. The wheels in offline_packages\wheels do not match your Python version.
    echo   2. Pip encountered an installation permission issue.
    echo.
    echo Check setup_debug.log for the full error details.
    echo.
    pause
    exit /b 1
)

echo [OK] Dependencies installed successfully.
echo.

:: -------------------------------------------------------------
:: Step 3: Run Database & Shortcut Setup (install.py)
:: -------------------------------------------------------------
echo [3/4] Initializing database and creating Desktop shortcuts...
"%PY_CMD%" install.py >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] Database setup or shortcut creation encountered an error!
    echo [ERROR] install.py returned errorcode %ERRORLEVEL% >> "%LOG_FILE%"
    echo.
    echo Check setup_debug.log for details.
    echo.
    pause
    exit /b 1
)

echo [OK] Database seeded and Desktop shortcut created.
echo.

:: -------------------------------------------------------------
:: Step 4: Completion
:: -------------------------------------------------------------
echo [4/4] Setup Completed Successfully!
echo Setup completed successfully at %TIME% >> "%LOG_FILE%"
echo ============================================================
echo.
echo First-Time Account Setup:
echo   Open the app, click "Register", and create your account.
echo   The FIRST account created automatically becomes the Super Administrator.
echo.
echo You can start the app at any time using the Desktop shortcut
echo or by double-clicking run.bat in this folder.
echo.

set /p START_NOW="Do you want to launch AMH Lab Tracker now? (Y/N): "
if /i "%START_NOW%"=="Y" (
    echo Starting AMH Lab Tracker...
    call "%~dp0run.bat"
) else (
    echo.
    echo Setup finished. Press any key to close this window.
    pause >nul
)
