@echo off
rem Builds FAUN.exe from FAUN.py (double-click, or run in a command prompt).
cd /d "%~dp0"

py -c "import tkinter" 2>nul
if errorlevel 1 (
  echo Python with tkinter was not found ^(the "py" launcher is missing or this Python has no tcl/tk^).
  echo Install Python from python.org with "tcl/tk and IDLE" ticked, then open a NEW command window.
  pause
  exit /b 1
)

if exist .buildenv rmdir /s /q .buildenv
py -m venv .buildenv
if errorlevel 1 goto fail
call .buildenv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet pyinstaller tkinterdnd2
if errorlevel 1 goto fail

set ICON=
set ADDDATA=
if exist FAUN.ico set ICON=--icon FAUN.ico
if exist FAUN.ico set ADDDATA=--add-data "FAUN.ico;."

python -m PyInstaller --noconfirm --clean --onefile --windowed --name FAUN --collect-all tkinterdnd2 %ADDDATA% %ICON% FAUN.py
if errorlevel 1 goto fail

echo.
echo Done: %cd%\dist\FAUN.exe
pause
exit /b 0

:fail
echo.
echo The build failed - see the messages above.
pause
exit /b 1
