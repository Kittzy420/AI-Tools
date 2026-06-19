@echo off
setlocal
cd /d "%~dp0"

title WebP Metadata Extractor (Debug)

if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    "%LocalAppData%\Programs\Python\Python310\python.exe" app.py
    goto :done
)

py -3 app.py 2>&1
if %errorlevel%==0 goto :done

python app.py 2>&1

:done
echo.
echo Exit code: %errorlevel%
pause