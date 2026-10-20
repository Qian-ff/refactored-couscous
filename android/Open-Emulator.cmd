@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\others\scripts\Start-A1.ps1" -Target Android
if errorlevel 1 (
    pause
    exit /b 1
)
