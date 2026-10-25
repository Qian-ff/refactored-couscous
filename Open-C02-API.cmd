@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0others\scripts\Start-C02.ps1"
if errorlevel 1 pause
