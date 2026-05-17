@echo off
REM Use this only if the .vbs launcher is blocked by IT/antivirus.
REM It does the exact same thing (venv + dependencies + launch),
REM just in a visible window.
title Income Tracker
cd /d "%~dp0"
call "_setup_and_run.bat"
