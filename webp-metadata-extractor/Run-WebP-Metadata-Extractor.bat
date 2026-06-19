@echo off
setlocal
cd /d "%~dp0"

set "PYTHONW="
set "PYTHON="

if exist "%LocalAppData%\Programs\Python\Python310\pythonw.exe" (
    set "PYTHONW=%LocalAppData%\Programs\Python\Python310\pythonw.exe"
    set "PYTHON=%LocalAppData%\Programs\Python\Python310\python.exe"
)

if not defined PYTHONW (
    for /f "delims=" %%P in ('where pythonw 2^>nul') do (
        if not defined PYTHONW set "PYTHONW=%%P"
    )
)

if not defined PYTHON (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PYTHON set "PYTHON=%%P"
    )
)

if defined PYTHONW (
    start "" "%PYTHONW%" "%~dp0app.py"
    exit /b 0
)

if defined PYTHON (
    start "" "%PYTHON%" "%~dp0app.py"
    exit /b 0
)

echo Python was not found.
echo Install Python 3 from https://www.python.org/downloads/
echo Make sure "Add Python to PATH" is checked during installation.
pause
exit /b 1