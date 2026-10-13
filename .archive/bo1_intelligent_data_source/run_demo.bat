@echo off
setlocal
cd /d "%~dp0"

set "BO1_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%BO1_PYTHON%" set "BO1_PYTHON=%~dp0bo1_intelligent_data\.venv\Scripts\python.exe"
if not exist "%BO1_PYTHON%" (
    echo Python environment not found. See bo1_intelligent_data\README.md for setup.
    pause
    exit /b 1
)

echo Starting BO1 with all four DSO. Your browser will open automatically.
echo Keep this window open while using the application.
echo Press Ctrl+C to stop the server.
"%BO1_PYTHON%" -m streamlit run "%~dp0bo1_intelligent_data\app.py" --server.port 8502 --server.headless false --server.address 127.0.0.1 --browser.gatherUsageStats false

if errorlevel 1 (
    echo.
    echo The server could not start. If the app is already running, open http://127.0.0.1:8502
    pause
)
endlocal
