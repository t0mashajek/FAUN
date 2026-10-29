@echo off
rem Builds FAUN.exe from FAUN.py (double-click, or run in a command prompt).
cd /d "%~dp0"

py -c "import tkinter" 2>nul
if errorlevel 1 (
  echo This Python has no tkinter. Install Python from python.org with the "tcl/tk" option ticked.
  pause
  exit /b 1
)

py -m venv .buildenv
call .buildenv\Scripts\activate.bat
pip install --quiet --upgrade pip pyinstaller tkinterdnd2

set ICON=
set ADDDATA=
if exist FAUN.ico set ICON=--icon FAUN.ico
if exist FAUN.ico set ADDDATA=--add-data "FAUN.ico;."

pyinstaller --noconfirm --clean --onefile --windowed --name FAUN --collect-all tkinterdnd2 %ADDDATA% %ICON% FAUN.py

echo.
echo Done: %cd%\dist\FAUN.exe
pause
