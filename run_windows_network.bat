@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run run_windows.bat once first.
  pause
  exit /b 1
)
echo Starting for phone access on the same Wi-Fi...
ipconfig | findstr /i "IPv4"
echo Open http://YOUR_PC_IPV4:8501 on your phone.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
if errorlevel 1 pause
