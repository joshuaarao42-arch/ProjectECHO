@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call run_echo.bat
".venv\Scripts\python.exe" -m unittest discover -s tests -t . -v
pause
