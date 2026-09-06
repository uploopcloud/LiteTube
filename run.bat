@echo off
setlocal EnableExtensions
title LiteTube - Local Music Player
cd /d "%~dp0"

echo.
echo ==========================================
echo              LiteTube
echo        Local Audio-Only Player
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found.
    echo Install Python 3.10 or newer and add it to PATH.
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo ERROR: LiteTube requires Python 3.10 or newer.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create the virtual environment.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" server.py
pause
exit /b 0

:fail
echo ERROR: Dependency installation failed.
pause
exit /b 1
