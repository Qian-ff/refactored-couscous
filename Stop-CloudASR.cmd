@echo off
cd /d "%~dp0"
python others\scripts\cloud_asr.py stop
if errorlevel 1 pause
