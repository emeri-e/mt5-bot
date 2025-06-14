@echo off
echo Updating MT5 Bot from GitHub...


REM Check if .git directory exists
if not exist .git (
    echo This directory is not a Git repository.
    echo Cloning fresh copy from GitHub...
    git clone https://github.com/emeri-e/mt5-bot.git temp_clone

    echo Moving files...
    xcopy /E /H /Y temp_clone\* .
    rmdir /S /Q temp_clone
) else (
    echo Pulling latest changes...
    git pull origin main
)

echo Update complete.
pause
