@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0others\scripts\Start-A1.ps1" -Target Web
if errorlevel 1 (
    pause
    exit /b 1
)
