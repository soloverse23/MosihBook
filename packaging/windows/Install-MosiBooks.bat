@echo off
setlocal
chcp 65001 >nul
title MosiBooks Setup

rem Run by double-click for a first install or a repair, or by the app itself with "update"
rem (then it waits for the app to stop, installs in place and starts the app again).
set "MODE=install"
if /i "%~1"=="update" set "MODE=update"

set "SRC=%~dp0payload"
if not exist "%SRC%\uv.exe" (
  echo.
  echo Please extract the ZIP file first: right-click it, choose "Extract All",
  echo then open the extracted folder and double-click Install-MosiBooks.bat again.
  echo.
  pause
  exit /b 1
)

set "URL=http://127.0.0.1:8765/api/auth/status"
set "APP=%LOCALAPPDATA%\MosiBooks"
set "UV=%APP%\payload\uv.exe"
set "PY=%APP%\venv\Scripts\python.exe"
set "UV_CACHE_DIR=%APP%\cache"
set "UV_PYTHON_INSTALL_DIR=%APP%\python"
set "UV_LINK_MODE=copy"
set "UV_NO_CONFIG=1"
set "LAUNCHER=%APP%\payload\MosiBooks.bat"

if "%MODE%"=="update" goto waitstop
curl.exe -s -o nul --max-time 2 %URL%
if not errorlevel 1 (
  echo.
  echo MosiBooks is running. Close its window in the taskbar, then run this again.
  echo.
  pause
  exit /b 1
)
goto begin

:waitstop
echo Waiting for MosiBooks to close...
set /a TRIES=0
:waitloop
curl.exe -s -o nul --max-time 1 %URL%
if errorlevel 1 goto stopped
set /a TRIES+=1
if %TRIES% geq 60 goto fail
ping -n 2 127.0.0.1 >nul
goto waitloop
:stopped
rem let the old app window finish and release its files
ping -n 3 127.0.0.1 >nul

:begin
echo.
if "%MODE%"=="update" (
  echo Updating MosiBooks. Please keep this window open, it closes by itself.
) else (
  echo Installing MosiBooks. The first install downloads about 300 MB
  echo and can take several minutes. Please keep this window open.
)
echo.

echo [1/4] Copying files...
if not exist "%APP%" mkdir "%APP%"
rem the login lives outside payload so updates, which carry none, keep it
if exist "%SRC%\credentials.bat" copy /y "%SRC%\credentials.bat" "%APP%\credentials.bat" >nul
if not exist "%APP%\credentials.bat" if exist "%APP%\payload\credentials.bat" copy /y "%APP%\payload\credentials.bat" "%APP%\credentials.bat" >nul
if exist "%APP%\payload" rd /s /q "%APP%\payload"
robocopy "%SRC%" "%APP%\payload" /E /XF credentials.bat /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto fail

echo [2/4] Installing Python...
if "%MODE%"=="update" if exist "%PY%" goto deps
"%UV%" venv --clear --managed-python --python 3.12 "%APP%\venv"
if errorlevel 1 goto fail

:deps
echo [3/4] Installing MosiBooks and Claude...
"%UV%" pip install --python "%PY%" -r "%APP%\payload\requirements.lock"
if errorlevel 1 goto fail
"%UV%" pip install --python "%PY%" --no-deps --reinstall-package bookforge "%APP%\payload\app"
if errorlevel 1 goto fail

echo [4/4] Creating the desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'MosiBooks.lnk')); $s.TargetPath=$env:LAUNCHER; $s.WorkingDirectory=(Split-Path $env:LAUNCHER); $s.WindowStyle=7; $s.Save()"
if errorlevel 1 echo Could not create the shortcut. You can start MosiBooks from: %LAUNCHER%

echo.
if "%MODE%"=="update" (
  echo Done. Starting MosiBooks again...
  start "MosiBooks - closing this window stops the app" /min "%LAUNCHER%" serve
  exit
)
echo Done. Opening MosiBooks...
call "%LAUNCHER%"
exit /b 0

:fail
echo.
if "%MODE%"=="update" (
  echo The update did not finish. Check the internet connection, then open MosiBooks
  echo from the desktop icon: it will offer the update again.
  if exist "%LAUNCHER%" start "MosiBooks - closing this window stops the app" /min "%LAUNCHER%" serve
) else (
  echo Setup failed. Check the internet connection and run this file again.
)
echo If it fails again, send a photo of this window to the person who gave you MosiBooks.
echo.
pause
exit /b 1
