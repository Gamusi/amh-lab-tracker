@echo off
title Pack M-LIS Release ZIP
cd /d "%~dp0"
echo ============================================================
echo   Building M-LIS Standalone Release ZIP...
echo   Laboratory Information System
echo ============================================================
echo.

python pack_release.py
pause
