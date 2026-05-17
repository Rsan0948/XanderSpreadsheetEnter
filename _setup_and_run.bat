@echo off
REM Internal worker: creates a private .venv on first run, installs all
REM dependencies into it, then launches the app from that venv.
REM You don't run this directly - double-click "Start Income Tracker" instead.
REM Progress is recorded in setup.log so the first run is easy to confirm.
cd /d "%~dp0"
set "FIRSTRUN="
set "LOG=%~dp0setup.log"

call :logline "Launcher started."

if exist ".venv\Scripts\pythonw.exe" goto ensuredeps

set "FIRSTRUN=1"
echo.
echo   Setting up the Income Tracker for the first time...
echo   This runs once and takes about a minute. Please leave
echo   this window open - it will close itself when ready.
echo.
call :logline "First run: no .venv yet, beginning setup."

set "PYBOOT="
py -3.13 -c "" >nul 2>&1 && set "PYBOOT=py -3.13"
if not defined PYBOOT py -c "" >nul 2>&1 && set "PYBOOT=py"
if not defined PYBOOT python -c "" >nul 2>&1 && set "PYBOOT=python"
if not defined PYBOOT goto nopython
call :logline "Using Python launcher: %PYBOOT%"

echo   Creating a private Python environment...
%PYBOOT% -m venv ".venv"
if errorlevel 1 goto failed
call :logline "Virtual environment created."

:ensuredeps
if exist ".venv\.deps-ok" goto run
echo   Downloading dependencies...
call :logline "Installing dependencies from requirements.txt..."
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements.txt
if errorlevel 1 goto failed

echo   Checking everything installed correctly...
".venv\Scripts\python.exe" -c "import flask" >nul 2>&1
if errorlevel 1 (
  call :logline "SELF-CHECK FAILED: Flask did not import after install."
  goto failed
)
call :logline "Self-check passed: Flask imports correctly."
echo ok> ".venv\.deps-ok"

:run
if defined FIRSTRUN echo   All set - starting it now...
call :logline "Launching the app from the venv."
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
call :logline "ERROR: No Python interpreter found."
pause
exit /b 1

:failed
echo.
echo   Setup hit a problem (see the messages above, and setup.log
echo   in this folder). The most common cause is no internet
echo   connection for the one-time download. Check your
echo   connection and try again.
echo.
call :logline "ERROR: Setup failed - see messages above."
pause
exit /b 1

:logline
echo [%date% %time%] %~1>> "%LOG%"
exit /b 0
