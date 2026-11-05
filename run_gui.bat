@echo off
chcp 65001 > nul
title MdPersia Desktop GUI
cd /d "%~dp0"

echo ====================================================
echo  MdPersia - Desktop Application
echo ====================================================
echo Launching GUI...

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

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
