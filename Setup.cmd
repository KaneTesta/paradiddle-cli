@echo off
setlocal
pushd "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Run Start.cmd to search for a song.
popd
exit /b 0
:failed
echo Setup failed. Install Python 3.12 with the Windows Python launcher, then retry.
popd
exit /b 1
