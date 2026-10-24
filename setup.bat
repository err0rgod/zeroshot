@echo off
title ZeroShot Voice Action Harness - Setup
cd /d "%~dp0"

echo ================================================================
echo   ZeroShot Voice Action Harness - Setup ^& Installer
echo ================================================================
echo.

:: 1. Check for Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    where py >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python was not found in your PATH!
        echo Please download and install Python 3.10+ from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
    set "PY_CMD=py"
) else (
    set "PY_CMD=python"
)

echo [OK] Python detected:
%PY_CMD% --version
echo.

:: 2. Check for uv (Astral fast package manager)
where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "USE_UV=1"
    echo [OK] uv package manager detected.
) else (
    set "USE_UV=0"
    echo [INFO] uv not detected. Will use standard python venv and pip.
)
echo.

:: 3. Setup Virtual Environment (.venv)
if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Creating Python virtual environment in .venv...
    if "%USE_UV%"=="1" (
        uv venv .venv
    ) else (
        %PY_CMD% -m venv .venv
    )
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
) else (
    echo [OK] Virtual environment (.venv) already exists.
)
echo.

:: 4. Install Dependencies
echo [SETUP] Installing project dependencies from requirements.txt...
if "%USE_UV%"=="1" (
    uv pip install -r requirements.txt
) else (
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
)

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] All dependencies installed successfully.
echo.

:: 5. Setup .env file
if not exist ".env" (
    echo [SETUP] Creating .env file template...
    echo ELEVENLABS_API_KEY=your_elevenlabs_api_key_here> .env
    echo [NOTICE] Created .env template.
    echo Please add your ElevenLabs API key in .env for speech-to-text.
) else (
    echo [OK] .env file detected.
)
echo.

echo ================================================================
echo   Setup Complete! Everything is ready.
echo ================================================================
echo.
set /p LAUNCH="Do you want to launch the Voice Harness now? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    echo.
    echo [LAUNCH] Starting main.py...
    .venv\Scripts\python main.py
) else (
    echo.
    echo To run the assistant anytime, run: run.bat or .venv\Scripts\python main.py
    pause
)
