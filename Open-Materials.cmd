@echo off
cd /d "%~dp0"
for /f "delims=" %%b in ('git branch --show-current') do set "materialsBranch=%%b"
if not "%materialsBranch%"=="main" (
    echo Run this demo entry from the main checkout.
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0others\scripts\Start-A1.ps1" -Target Web -NoOpen
if errorlevel 1 (
    pause
    exit /b 1
)
if /I "%~1"=="-NoOpen" exit /b 0
start "" "http://127.0.0.1:5173/#/content/materials"
