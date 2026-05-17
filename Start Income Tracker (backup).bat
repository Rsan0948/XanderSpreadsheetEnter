@echo off
title Income Tracker
cd /d "%~dp0"
echo Starting the Income Tracker... your browser will open shortly.
echo (You can minimize this window. Closing it stops the tracker.)
python app.py
if errorlevel 1 py app.py
pause
