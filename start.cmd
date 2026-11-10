@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First run: open PowerShell in this folder and run .\start.ps1 -Setup
    pause
    exit /b 1
)
echo Estoque Local: http://127.0.0.1:8765
echo Keep this window open while using the app. Press Ctrl+C to stop.
".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
