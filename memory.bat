@echo off
cd /d "%~dp0"
python -m cli %*
if errorlevel 1 pause
