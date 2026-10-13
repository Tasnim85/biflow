$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = Join-Path $projectRoot 'bo1_intelligent_data\.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create the Python virtual environment and install requirements first; see bo1_intelligent_data/README.md.' }
& $pythonPath -m streamlit run (Join-Path $projectRoot 'bo1_intelligent_data\app.py') --server.port 8502 --server.headless false --server.address 127.0.0.1 --browser.gatherUsageStats false
