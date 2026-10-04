@echo off
set DOWNLOAD_DIR=%CD%\downloads
set PORT=8000
set ARIA2_PORT=6800

if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%"

echo [INFO] Starting Aria2c RPC daemon...
start "" aria2c --enable-rpc --rpc-listen-all=true --rpc-listen-port=%ARIA2_PORT% --max-connection-per-server=16 --split=16 --min-split-size=1M --continue=true --dir="%DOWNLOAD_DIR%" --rpc-allow-origin-all=true

echo [INFO] Starting Web Server on http://localhost:%PORT%
python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload
pause
