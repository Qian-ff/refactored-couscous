@echo off
setlocal
echo LabConnect A1
echo 1. Web
echo 2. Windows
echo 3. Android emulator
echo 4. All three
echo 0. Exit
choice /C 12340 /N /M "Choose 1/2/3/4/0: "
if errorlevel 5 exit /b 0
if errorlevel 4 (
    set "target=All"
) else if errorlevel 3 (
    set "target=Android"
) else if errorlevel 2 (
    set "target=Windows"
) else (
    set "target=Web"
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0others\scripts\Start-A1.ps1" -Target %target%
if errorlevel 1 (
    pause
    exit /b 1
)
