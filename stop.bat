@echo off
title Savestock Stop
echo Stopping Savestock services...

REM Kill whatever listens on 8000 (API) and 5000 (Web)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo Stopped API (8000) and Web (5000).
timeout /t 2 /nobreak >nul
