@echo off
setlocal
set "python=%~dp0runtime\python.exe"
if not exist "%python%" set "python=%~dp0.venv\Scripts\python.exe"
if not exist "%python%" (
  echo Python environment missing. Install Python 3.12 and run Setup.cmd first.
  exit /b 1
)
"%python%" "%~dp0cli.py" %*
set "result=%errorlevel%"
if "%~1"=="" pause
exit /b %result%
