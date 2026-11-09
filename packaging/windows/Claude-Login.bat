@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
"%LOCALAPPDATA%\MosiBooks\venv\Scripts\python.exe" -m bookforge.cli claude-login
pause
