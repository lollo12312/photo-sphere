@echo off
title photo-sphere
rem Single-window start: frontend runs in background, backend in foreground.
rem Closing this window stops both services.

cd /d "%~dp0"

rem Guard: make sure backend virtual env dependencies are installed
backend\.venv\Scripts\python.exe -c "import fastapi" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] backend .venv missing or dependencies not installed.
  echo See README, section "Quick start": create .venv and run pip install -r requirements.txt
  pause
  exit /b 1
)

cd /d "%~dp0frontend"
start /b cmd /c "npm run dev"

cd /d "%~dp0backend"
.venv\Scripts\python.exe main.py
pause