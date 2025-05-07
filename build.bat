@echo off
setlocal

REM Set the name of your Python script (adjust if different)
set SCRIPT_NAME=main.py

REM Optional: Define the output directory
set OUTPUT_DIR=dist

REM Create output directory if it doesn't exist
if not exist %OUTPUT_DIR% mkdir %OUTPUT_DIR%

REM Compile using Nuitka
python -m nuitka ^
  --standalone ^
  --show-progress ^
  --onefile ^
  --windows-icon-from-ico=icon.ico ^
  --output-dir=%OUTPUT_DIR% ^
  --enable-plugin=pylint-warnings ^
  --include-package=requests ^
  --include-package=yaml ^
  %SCRIPT_NAME%

echo.
echo [+] Build complete. Output located in: %OUTPUT_DIR%
pause
