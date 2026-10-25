@echo off
rem Menu to restart, rebuild or stop varuna's containers. Double-click or run from a terminal.
cd /d "%~dp0"
python scripts\manage.py
if "%~1"=="" pause
