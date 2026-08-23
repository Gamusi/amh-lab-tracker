@echo off
title Pack AMH Lab Tracker Release ZIP
cd /d "%~dp0"
echo ============================================================
echo   Building AMH Lab Tracker Standalone Release ZIP...
echo   Ahmadiyya Muslim Hospital, Mbale, Uganda
echo ============================================================
echo.

python pack_release.py
pause
