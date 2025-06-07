@echo off
echo Checking Python launcher...
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo Setting up virtual environment...
%PYTHON_CMD% -m venv .venv

echo Activating virtual environment
call .venv\Scripts\activate

echo Installing dependencies
pip install -r requirements.txt

echo Setup complete. You only have to run this setup once. Just run main.py subsequently.
echo Running main.py...
%PYTHON_CMD% main.py

echo Done
pause
