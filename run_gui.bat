@echo off
chcp 65001 > nul
title MdPersia Desktop GUI
cd /d "%~dp0"

echo ====================================================
echo  MdPersia - Desktop Application
echo ====================================================
echo Launching GUI...

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m mdpersia --gui
) else (
    python -m mdpersia --gui
)

if %errorlevel% neq 0 (
    echo.
    echo An error occurred while launching MdPersia GUI.
    pause
)
