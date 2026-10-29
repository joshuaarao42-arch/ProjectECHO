@echo off
REM Launch Project ECHO on Windows. Creates a virtual environment on first run.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Setting up Project ECHO for the first time...
    py -3 -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)
".venv\Scripts\pythonw.exe" main.py
exit /b 0
:error
echo Setup failed. Make sure Python 3.10 or newer is installed (python.org) and "py" is on your PATH.
pause
exit /b 1
