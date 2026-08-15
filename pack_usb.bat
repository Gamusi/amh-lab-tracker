@echo off
title Pack AMH Lab Tracker for Offline USB Deployment
echo ============================================================
echo   Preparing Offline USB Bundle for Target Workstation...
echo   Ahmadiyya Muslim Hospital, Mbale, Uganda
echo ============================================================

mkdir wheels 2>nul
echo Downloading dependency wheel packages for offline installation...
pip download -r requirements.txt -d wheels

echo.
echo ============================================================
echo   USB PACKAGING COMPLETE!
echo.
echo   STEPS TO DEPLOY ON TARGET PC (NO INTERNET / NO PYTHON):
echo   1. Copy the entire 'amh-lab-tracker' folder to your USB drive.
echo   2. Download Python installer (python-3.11.9-amd64.exe) to your USB drive.
echo   3. On Target PC:
echo      a. Run python-3.11.9-amd64.exe (CHECK "Add Python to PATH").
echo      b. Open CMD, navigate to USB drive, and run:
echo         pip install --no-index --find-links=wheels -r requirements.txt
echo         python install.py
echo      c. Double-click the 'AMH Lab Tracker' shortcut on Desktop!
echo ============================================================
pause
