@echo off
chcp 65001 > nul
title MdPersia - Push to GitHub
cd /d "%~dp0"
echo ====================================================
echo  MdPersia - Push to GitHub
echo ====================================================
echo Repository: https://github.com/hamid-morsali-786/MdPersia
echo.
git status -s
echo.
set /p commit_msg="Enter commit message (press Enter for default): "
if "%commit_msg%"=="" set commit_msg=feat: update documentation, screenshots, and repository standards
git add .
git commit -m "%commit_msg%"
echo.
echo Pushing to GitHub (origin/main)...
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Pushed successfully to GitHub!
) else (
    echo [ERROR] Push failed. Please check network or GitHub credentials.
)
pause
