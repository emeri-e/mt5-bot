@echo off
echo Activating virtual environment
call .venv\Scripts\activate

pyinstaller --noconfirm --onefile --hidden-import numpy --collect-submodules numpy --collect-all MetaTrader5 main.py

echo Done
pause
