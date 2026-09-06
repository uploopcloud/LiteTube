@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build LiteTube Windows Desktop App

echo ==========================================
echo       LiteTube Windows Desktop Builder
echo ==========================================
echo.

echo Checking Python...
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found in PATH.
  echo Install Python 3.10+ and enable "Add Python to PATH".
  pause
  exit /b 1
)

if not exist "server.py" goto :missing
if not exist "desktop.py" goto :missing
if not exist "static" goto :missing
if not exist "LiteTube.ico" goto :missing

if not exist ".venv\Scripts\python.exe" (
  echo Creating build environment...
  python -m venv .venv
  if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

python -m pip install --upgrade pip
if errorlevel 1 goto :fail

python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "LiteTube.exe" del /q "LiteTube.exe"

echo.
echo Building TRUE Windows desktop application...
echo The app will use an embedded WebView2 window.
echo It will NOT open Chrome or Edge as the main UI.
echo.

pyinstaller --noconfirm --clean --onefile --windowed --name LiteTube --icon "LiteTube.ico" --collect-all webview --collect-all bottle --add-data "static;static" --add-data "update_config.json;." --add-data "VERSION.txt;." desktop.py
if errorlevel 1 goto :fail

if not exist "dist\LiteTube.exe" goto :fail
copy /Y "dist\LiteTube.exe" "LiteTube.exe" >nul
if errorlevel 1 goto :fail

echo.
echo ==========================================
echo BUILD COMPLETE
echo ==========================================
echo.
echo Your Windows app is here:
echo %CD%\LiteTube.exe
echo.
echo Double-click LiteTube.exe to launch the
echo standalone LiteTube desktop window.
echo.
echo NOTE: Microsoft Edge WebView2 Runtime is required.
echo Windows 10/11 systems commonly already have it.
echo.
pause
exit /b 0

:missing
echo ERROR: Required LiteTube files are missing.
echo Make sure this BAT is inside the LiteTube project folder.
pause
exit /b 1

:fail
echo.
echo ==========================================
echo BUILD FAILED
echo ==========================================
echo.
pause
exit /b 1
