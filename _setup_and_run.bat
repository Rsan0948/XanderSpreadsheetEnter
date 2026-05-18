@echo off
REM Internal worker: stops any leftover instance, then (on first run)
REM creates a private .venv, installs all dependencies into it, and
REM launches the app from that venv.
REM You don't run this directly - double-click "Start Income Tracker".
REM Progress is recorded in setup.log so the first run is easy to confirm.
cd /d "%~dp0"
set "FIRSTRUN="
set "LOG=%~dp0setup.log"

call :logline "Launcher started."

REM ---------------------------------------------------------------
REM Clean slate: kill anything left over from a previous run BEFORE
REM we touch anything else, so we always start from a fresh state.
REM ---------------------------------------------------------------
call :logline "Cleaning up any previous instance..."
set "KILLED="

REM 1) Kill whatever is holding our port (the old running server).
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /r /c:"127\.0\.0\.1:5000 " 2^>nul') do (
  taskkill /F /PID %%P >nul 2>&1
  if not errorlevel 1 set "KILLED=1"
)

REM 2) Kill any python/pythonw whose EXE is THIS folder's venv
REM    (scoped to this folder so unrelated Python apps are untouched).
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=('%~dp0.venv\Scripts\').ToLower(); Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and ($_.ExecutablePath.ToLower() -eq ($d+'pythonw.exe') -or $_.ExecutablePath.ToLower() -eq ($d+'python.exe')) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; '1' }" 2>nul | findstr "1" >nul 2>&1 && set "KILLED=1"

if defined KILLED (
  call :logline "Stopped a previous instance - waiting for the port to free up."
  ping -n 2 127.0.0.1 >nul
) else (
  call :logline "Nothing was running - clean start."
)

REM ---------------------------------------------------------------
REM Normal setup / launch
REM ---------------------------------------------------------------
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
