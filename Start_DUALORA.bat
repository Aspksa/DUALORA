@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 dualora.py
) else (
  python dualora.py
)
if errorlevel 1 pause
