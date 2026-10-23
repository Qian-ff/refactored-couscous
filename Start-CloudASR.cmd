@echo off
cd /d "%~dp0"
python others\scripts\cloud_asr.py start
if errorlevel 1 pause
