@echo off
title ZeroShot Voice Action Harness
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first to configure your system.
    echo.
    pause
    exit /b 1
)

.venv\Scripts\python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [PROCESS EXITED] Exit code: %ERRORLEVEL%
    pause
)
