@echo off
setlocal
cd /d "%~dp0"

set "BO1_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%BO1_PYTHON%" (
    echo Environnement Python absent. Lancez installer.bat une fois.
    pause
    exit /b 1
)

echo BO1 - VERSION FINALE
"%BO1_PYTHON%" "%~dp0launcher.py"

if errorlevel 1 (
    echo.
    echo Demarrage impossible. Le detail est dans logs\server.log.
)
pause
endlocal
