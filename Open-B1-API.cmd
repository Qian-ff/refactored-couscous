@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0others\scripts\Start-B1Api.ps1"
if errorlevel 1 pause
