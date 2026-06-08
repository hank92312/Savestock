@echo off
title Savestock Launcher
set "ROOT=%~dp0"

echo ============================================
echo    Savestock - one click launcher
echo ============================================
echo.

REM --- 1. Backend API (port 8000) ---
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul && goto :api_ok
echo [1/3] Starting API on port 8000 ...
start "Savestock API" /min /d "%ROOT%backend" "%ROOT%.venv\Scripts\python.exe" -m uvicorn main:app --port 8000
goto :api_done
:api_ok
echo [1/3] API already running (8000), skip
:api_done

REM --- 2. Web build check (build if missing) ---
if exist "%ROOT%frontend\build\web\index.html" goto :build_ok
echo [2/3] No web build found, building now (about 30-60s) ...
pushd "%ROOT%frontend"
call flutter build web
popd
goto :build_done
:build_ok
echo [2/3] Web build exists
:build_done

REM --- 3. Web server (port 5000) ---
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul && goto :web_ok
echo [3/3] Starting web server on port 5000 ...
start "Savestock Web" /min /d "%ROOT%frontend\build\web" "%ROOT%.venv\Scripts\python.exe" -m http.server 5000
goto :web_done
:web_ok
echo [3/3] Web server already running (5000), skip
:web_done

REM --- Open browser after services are up ---
timeout /t 3 /nobreak >nul
start "" http://localhost:5000

echo.
echo  Done. Browser opened at  http://localhost:5000
echo    - Backend API : http://localhost:8000
echo    - To STOP: close the two minimized windows
echo               "Savestock API" and "Savestock Web"
echo.
echo  Tip: to refresh prices, press the Update button on the home page.
echo       To re-fetch all default stocks: .venv\Scripts\python.exe etl\fetch_data.py
echo.
pause
