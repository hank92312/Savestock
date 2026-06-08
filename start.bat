@echo off
title Savestock Launcher
set "ROOT=%~dp0"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"

echo Starting Savestock in background...

REM --- Backend API (port 8000), hidden ---
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul || powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath '%ROOT%.venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--port','8000' -WorkingDirectory '%ROOT%backend' -RedirectStandardOutput '%ROOT%logs\api.out.log' -RedirectStandardError '%ROOT%logs\api.err.log'"

REM --- Build web if missing ---
if not exist "%ROOT%frontend\build\web\index.html" ( pushd "%ROOT%frontend" & call flutter build web & popd )

REM --- Web server (port 5000), hidden ---
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul || powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath '%ROOT%.venv\Scripts\python.exe' -ArgumentList '-m','http.server','5000','--directory','%ROOT%frontend\build\web' -RedirectStandardOutput '%ROOT%logs\web.out.log' -RedirectStandardError '%ROOT%logs\web.err.log'"

REM --- Open browser ---
timeout /t 4 /nobreak >nul
start "" http://localhost:5000

echo.
echo Savestock started (running hidden in background).
echo    App : http://localhost:5000
echo    API : http://localhost:8000
echo    Logs: %ROOT%logs
echo    To STOP, double-click  stop.bat
timeout /t 3 /nobreak >nul
