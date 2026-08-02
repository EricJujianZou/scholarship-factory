@echo off
rem Double-click to open the dashboard. Starts the server if it is not already
rem running, then opens the browser once the port answers.
setlocal
title Scholarship Factory
cd /d "%~dp0"

set "URL=http://127.0.0.1:8000"

call :listening && goto open

echo Starting the dashboard...
start "scholarship-factory server" /min cmd /c "uv run sf serve"

rem Wait for the port so the browser does not land on a dead page.
rem ping, not timeout: timeout fails outright when stdin is redirected.
for /l %%i in (1,1,30) do (
  ping -n 2 127.0.0.1 >nul
  call :listening && goto open
)

echo.
echo Could not reach %URL% after 30 seconds.
echo Run "uv run sf serve" in this folder to see what went wrong.
echo.
pause
exit /b 1

:open
start "" "%URL%"
exit /b 0

:listening
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
exit /b %errorlevel%
