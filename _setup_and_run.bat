@echo off
REM Internal worker: creates a private .venv on first run, installs all
REM dependencies into it, then launches the app from that venv.
REM You don't run this directly - double-click "Start Income Tracker" instead.
cd /d "%~dp0"
set "FIRSTRUN="

if exist ".venv\Scripts\pythonw.exe" goto ensuredeps

set "FIRSTRUN=1"
echo.
echo   Setting up the Income Tracker for the first time...
echo   This runs once and takes about a minute. Please leave
echo   this window open - it will close itself when ready.
echo.

set "PYBOOT="
py -3.13 -c "" >nul 2>&1 && set "PYBOOT=py -3.13"
if not defined PYBOOT py -c "" >nul 2>&1 && set "PYBOOT=py"
if not defined PYBOOT python -c "" >nul 2>&1 && set "PYBOOT=python"
if not defined PYBOOT goto nopython

echo   Creating a private Python environment...
%PYBOOT% -m venv ".venv"
if errorlevel 1 goto failed

:ensuredeps
if exist ".venv\.deps-ok" goto run
echo   Downloading dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements.txt
if errorlevel 1 goto failed
echo ok> ".venv\.deps-ok"

:run
if defined FIRSTRUN echo   All set - starting it now...
start "" ".venv\Scripts\pythonw.exe" "app.py"
if defined FIRSTRUN ping -n 2 127.0.0.1 >nul
exit /b 0

:nopython
echo.
echo   Couldn't find Python. Install Python 3.13 from
echo   https://www.python.org/downloads/ and tick
echo   "Add Python to PATH" during setup, then double-click
echo   "Start Income Tracker" again.
echo.
pause
exit /b 1

:failed
echo.
echo   Setup hit a problem (see the messages above). The most
echo   common cause is no internet connection for the one-time
echo   download. Check your connection and try again.
echo.
pause
exit /b 1
