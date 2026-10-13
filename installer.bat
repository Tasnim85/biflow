@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Installez Python 3.11 ou plus depuis python.org puis relancez installer.bat.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m ensurepip --upgrade
if errorlevel 1 (
    set "BO1_BASE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
        "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip --python ".venv\Scripts\python.exe" install -r requirements.txt
        goto installed
    )
    echo Impossible de preparer pip. Voir README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
:installed
if errorlevel 1 (
    echo Installation echouee. Verifiez la connexion Internet.
    pause
    exit /b 1
)
echo Installation terminee. Double-cliquez run_demo.bat.
pause
endlocal
