@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Whistle's Python environment was not found.
  echo See README.md for setup instructions.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "whistle_gui.py"
