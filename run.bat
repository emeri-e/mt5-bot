@echo off
echo Activating virtual environment
call .venv\Scripts\activate

echo Checking Python launcher...
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo Running main.py using %PYTHON_CMD%...
%PYTHON_CMD% main.py

echo Done
pause
