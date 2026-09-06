@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build LiteTube Windows App

echo ==========================================
echo        LiteTube Windows App Builder
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python was not found on PATH.
  echo Install Python 3.10+ and enable Add Python to PATH.
  pause
  exit /b 1
)

python --version
if errorlevel 1 goto :fail

if not exist "server.py" goto :missing
if not exist "static" goto :missing
if not exist "LiteTube.ico" goto :missing

if not exist ".venv\Scripts\python.exe" (
  echo Creating build environment...
  python -m venv .venv
  if errorlevel 1 goto :fail
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "LiteTube.exe" del /q "LiteTube.exe"

echo.
echo Building LiteTube.exe...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name LiteTube --icon "LiteTube.ico" --add-data "static;static" --add-data "update_config.json;." --add-data "VERSION.txt;." server.py
if errorlevel 1 goto :fail

if not exist "dist\LiteTube.exe" goto :fail
copy /Y "dist\LiteTube.exe" "LiteTube.exe" >nul
if errorlevel 1 goto :fail

echo.
echo ==========================================
echo BUILD COMPLETE
echo ==========================================
echo.
echo %CD%\LiteTube.exe
echo.
echo User playlists are stored in browser local storage and are
echo not removed by replacing LiteTube.exe with a newer build.
echo.
pause
exit /b 0

:missing
echo ERROR: Required LiteTube files are missing.
pause
exit /b 1

:fail
echo.
echo BUILD FAILED.
pause
exit /b 1
