@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run run_windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import sys; print(sys.version); import streamlit, pydantic, openai, requests, bs4, pypdf; print('All imports OK'); print('Streamlit', streamlit.__version__)"
".venv\Scripts\python.exe" -m compileall app.py src
pause
