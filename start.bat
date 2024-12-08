:: ================
:: File: \start.bat
:: Project: wallpaper
:: Version: 0.10.7
:: File Created: Saturday, 2024-11-23 13:54:47
:: Author: vanton
:: -----
:: Last Modified: Sunday, 2024-12-08 15:13:45
:: Modified By: vanton
:: -----
:: Copyright  2024
:: License: MIT License
:: ================


@ECHO OFF
setlocal EnableDelayedExpansion

:: #ANCHOR - Initialize variables
if not defined SCHEDULER set "SCHEDULER=0"
if not defined PYTHON set "PYTHON=python"
if defined GIT set "GIT_PYTHON_GIT_EXECUTABLE=%GIT%"
if not defined VENV_DIR set "VENV_DIR=%~dp0%.venv"
set "ERROR_REPORTING=FALSE"
set "TEMP_DIR=%~dp0tmp"

:: #ANCHOR - Create temp directory if it doesn't exist
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: #ANCHOR - Check Python installation
%PYTHON% -c "" >"%TEMP_DIR%\stdout.txt" 2>"%TEMP_DIR%\stderr.txt"
if errorlevel 1 (
    echo Error: Python is not available
    goto :error_handler
)



:: #ANCHOR - Check/Install pip
%PYTHON% -m pip --help >"%TEMP_DIR%\stdout.txt" 2>"%TEMP_DIR%\stderr.txt"
if errorlevel 1 (
    if not "%PIP_INSTALLER_LOCATION%"=="" (
        %PYTHON% "%PIP_INSTALLER_LOCATION%" >"%TEMP_DIR%\stdout.txt" 2>"%TEMP_DIR%\stderr.txt"
        if errorlevel 1 (
            echo Error: Failed to install pip
            goto :error_handler
        )
    ) else (
        echo Error: pip is not available
        goto :error_handler
    )
)

:: #ANCHOR - Virtual Environment Setup
if not "%VENV_DIR%"=="-" if not "%SKIP_VENV%"=="1" (
    if not exist "%VENV_DIR%\Scripts\Python.exe" (
        for /f "delims=" %%i in ('"%PYTHON%" -c "import sys; print(sys.executable)"') do set "PYTHON_FULLNAME=%%i"
        echo Creating venv in directory %VENV_DIR% using python !PYTHON_FULLNAME!
        "!PYTHON_FULLNAME!" -m venv "%VENV_DIR%" >"%TEMP_DIR%\stdout.txt" 2>"%TEMP_DIR%\stderr.txt"
        if errorlevel 1 (
            echo Error: Failed to create virtual environment
            goto :error_handler
        )

        :: Upgrade pip in venv
        "%VENV_DIR%\Scripts\Python.exe" -m pip install --upgrade pip >"%TEMP_DIR%\stdout.txt" 2>"%TEMP_DIR%\stderr.txt"
        if errorlevel 1 echo Warning: Failed to upgrade PIP version
    )

    set "PYTHON=%VENV_DIR%\Scripts\Python.exe"
    call "%VENV_DIR%\Scripts\activate.bat"
    echo Using venv: !PYTHON!
    "%PYTHON%" -c "import sys; print(sys.version)"
)

:: #ANCHOR - Install Requirements
if not exist "requirements.txt" (
    echo Error: requirements.txt not found
    goto :error_handler
)
if not exist "%TEMP_DIR%\requirements" (
    "%PYTHON%" -m pip install -r requirements.txt >"%TEMP_DIR%\stdout.txt" 2>"%TEMP_DIR%\stderr.txt"
    if errorlevel 1 (
        echo Error: Failed to install requirements
        goto :error_handler
    )
    echo "success" >"%TEMP_DIR%\requirements"
)

:: #ANCHOR - Launch main application
%PYTHON% wallhavenDownload.py %*
if not %SCHEDULER%==1 pause
goto :cleanup

:: #ANCHOR - *function: error_handler
:error_handler
echo.
echo Exit code: %errorlevel%
if exist "%TEMP_DIR%\stdout.txt" for %%i in ("%TEMP_DIR%\stdout.txt") do if not %%~zi==0 (
    echo.
    echo stdout:
    type "%TEMP_DIR%\stdout.txt"
)
if exist "%TEMP_DIR%\stderr.txt" for %%i in ("%TEMP_DIR%\stderr.txt") do if not %%~zi==0 (
    echo.
    echo stderr:
    type "%TEMP_DIR%\stderr.txt"
)
echo.
echo Launch unsuccessful. Exiting.
if not %SCHEDULER%==1 pause

:: #ANCHOR - *function: cleanup
:cleanup
if exist "%TEMP_DIR%\stdout.txt" del "%TEMP_DIR%\stdout.txt"
if exist "%TEMP_DIR%\stderr.txt" del "%TEMP_DIR%\stderr.txt"
endlocal
exit /b
