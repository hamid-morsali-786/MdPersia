@echo off
chcp 65001 > nul
title MdPersia Desktop GUI
cd /d "%~dp0"

echo ====================================================
echo  MdPersia - Desktop Application
echo ====================================================
echo Launching GUI...

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
if exist "%~dp0.venv\Lib\site-packages\playwright\driver\node.exe" (
    set "PATH=%~dp0.venv\Lib\site-packages\playwright\driver;%PATH%"
)
if "%~1"=="" (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr /R /C:":1420 .*LISTENING"') do (
        taskkill /F /PID %%a /T >nul 2>&1
    )
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m mdpersia --gui %*
    goto :check_err
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m mdpersia --gui %*
    goto :check_err
)

python -m mdpersia --gui %*

:check_err
if %errorlevel% neq 0 (
    echo.
    echo An error occurred while launching MdPersia GUI.
    pause
)
