@ECHO OFF
setlocal EnableDelayedExpansion

:: Define constants
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "PYTHON=%VENV_DIR%\Scripts\Python.exe"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"
set "TEMP_REQUIREMENTS=%SCRIPT_DIR%temp_requirements.txt"

:: Validate virtual environment
if not exist "%PYTHON%" (
    echo Error: Python virtual environment not found at: %VENV_DIR%
    exit /b 1
)

:: Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    exit /b 1
)

:: Display Python information
echo Using Python from: !PYTHON!
"%PYTHON%" -c "import sys; print(f'Python version: {sys.version}')"

:: Clear existing temporary file if it exists
if exist "%TEMP_REQUIREMENTS%" del "%TEMP_REQUIREMENTS%"

:: Generate requirements file
echo Generating requirements.txt...
for /f "delims=" %%i in ('pip list --local --exclude pip --exclude setuptools --exclude wheel --not-required --format=freeze') do (
    echo %%i
    echo %%i| findstr /v "pre_commit pytest ruff types-" >>"%TEMP_REQUIREMENTS%"
)

:: Move temporary file to final location
move /y "%TEMP_REQUIREMENTS%" "%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo Error: Failed to create requirements.txt
    exit /b 1
)

echo Requirements file generated successfully at: %REQUIREMENTS_FILE%
endlocal
exit /b 0
