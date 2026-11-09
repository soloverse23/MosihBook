@echo off
setlocal
chcp 65001 >nul
set "APP=%LOCALAPPDATA%\MosiBooks"
set "URL=http://127.0.0.1:8765"
if /i "%~1"=="serve" goto serve

curl.exe -s -o nul --max-time 2 %URL%/api/auth/status
if not errorlevel 1 goto ready

start "MosiBooks - closing this window stops the app" /min "%~f0" serve
echo Starting MosiBooks...
for /l %%i in (1,1,90) do (
  curl.exe -s -o nul --max-time 1 %URL%/api/auth/status
  if not errorlevel 1 goto ready
  ping -n 2 127.0.0.1 >nul
)
echo.
echo MosiBooks did not start. Details are in: %APP%\server.log
echo.
pause
exit /b 1

:ready
start "" "%URL%"
exit /b 0

:serve
if exist "%APP%\credentials.bat" (call "%APP%\credentials.bat") else if exist "%~dp0credentials.bat" call "%~dp0credentials.bat"
set "MOSIBOOKS_APP_DIR=%APP%"
set "PYTHONUTF8=1"
if not exist "%USERPROFILE%\MosiBooks" mkdir "%USERPROFILE%\MosiBooks"
cd /d "%USERPROFILE%\MosiBooks"
"%APP%\venv\Scripts\python.exe" -m bookforge.cli serve --no-open > "%APP%\server.log" 2>&1
exit
