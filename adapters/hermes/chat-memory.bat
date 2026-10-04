@echo off
hermes chat -s agent-memory-os-router -t terminal,skills %*
if errorlevel 1 pause
