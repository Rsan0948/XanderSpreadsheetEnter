@echo off
title Income Tracker - One-time setup
echo.
echo   Setting up the Income Tracker...
echo   (this only needs to be done once)
echo.

python -m pip install --user flask
if errorlevel 1 (
  echo Trying the "py" launcher instead...
  py -m pip install --user flask
)

echo.
if errorlevel 1 (
  echo   Hmm, that didn't work. Make sure Python is installed
  echo   from https://www.python.org/downloads/ ^(check
  echo   "Add Python to PATH" during install^), then run this again.
) else (
  echo   All set!  From now on just double-click
  echo   "Start Income Tracker" to open it.
)
echo.
pause
