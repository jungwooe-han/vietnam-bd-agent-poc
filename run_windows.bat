@echo off
setlocal
cd /d "%~dp0"
title Vietnam BD Agent POC

echo [1/4] Python environment check...
set "PY_CMD="
py -3.13 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.13"
if not defined PY_CMD py -3.12 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.12"
if not defined PY_CMD py -3.11 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.11"
if not defined PY_CMD python -c "import sys" >nul 2>&1 && set "PY_CMD=python"

if not defined PY_CMD (
  echo.
  echo Python was not found. Install Python 3.11, 3.12, or 3.13 and run this file again.
  pause
  exit /b 1
)

%PY_CMD% -c "import sys; print('Using Python:', sys.version)"
if errorlevel 1 goto :fail

echo [2/4] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :fail
)

set "VENV_PY=.venv\Scripts\python.exe"

echo [3/4] Installing required packages...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

if not exist ".env" copy ".env.example" ".env" >nul

echo [4/4] Starting app...
echo Browser address: http://localhost:8501
echo Keep this window open while using the app.
"%VENV_PY%" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo ========================================
echo App startup failed.
echo Copy the error shown above and send it back.
echo ========================================
pause
exit /b 1
