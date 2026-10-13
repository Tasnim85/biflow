@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -m streamlit run "%~dp0bo1_prototype\app.py" --server.headless false --server.address 127.0.0.1 --browser.gatherUsageStats false
if errorlevel 1 pause
