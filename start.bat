@echo off
@REM Switch to the current script running directory
cd /d %~dp0

if not defined PYTHON (set PYTHON=python)
if defined GIT (set "GIT_PYTHON_GIT_EXECUTABLE=%GIT%")
if not defined VENV_DIR (set "VENV_DIR=%~dp0%.venv")

set ERROR_REPORTING=FALSE

mkdir tmp 2>NUL

%PYTHON% -c "" >tmp/stdout.txt 2>tmp/stderr.txt
if %ERRORLEVEL% == 0 goto :check_pip
echo Couldn't launch python
goto :show_stdout_stderr


@REM #ANCHOR - check_pip
:check_pip
%PYTHON% -mpip --help >tmp/stdout.txt 2>tmp/stderr.txt
if %ERRORLEVEL% == 0 goto :start_venv
if "%PIP_INSTALLER_LOCATION%" == "" goto :show_stdout_stderr
%PYTHON% "%PIP_INSTALLER_LOCATION%" >tmp/stdout.txt 2>tmp/stderr.txt
if %ERRORLEVEL% == 0 goto :start_venv
echo Couldn't install pip
goto :show_stdout_stderr


@REM #ANCHOR - start_venv
:start_venv
if ["%VENV_DIR%"] == ["-"] goto :skip_venv
if ["%SKIP_VENV%"] == ["1"] goto :skip_venv
dir "%VENV_DIR%\Scripts\Python.exe" >tmp/stdout.txt 2>tmp/stderr.txt
if %ERRORLEVEL% == 0 goto :activate_venv
for /f "delims=" %%i in ('CALL %PYTHON% -c "import sys; print(sys.executable)"') do set PYTHON_FULLNAME="%%i"
echo Creating venv in directory %VENV_DIR% using python %PYTHON_FULLNAME%
%PYTHON_FULLNAME% -m venv "%VENV_DIR%" >tmp/stdout.txt 2>tmp/stderr.txt
if %ERRORLEVEL% == 0 goto :upgrade_pip
echo Unable to create venv in directory "%VENV_DIR%"
goto :show_stdout_stderr


@REM #ANCHOR - upgrade_pip
:upgrade_pip
"%VENV_DIR%\Scripts\Python.exe" -m pip install --upgrade pip >tmp/stdout.txt 2>tmp/stderr.txt
if %ERRORLEVEL% == 0 goto :activate_venv
echo Warning: Failed to upgrade PIP version


@REM #ANCHOR - activate_venv
:activate_venv
set PYTHON="%VENV_DIR%\Scripts\Python.exe"
call "%VENV_DIR%\Scripts\activate.bat"
echo venv %PYTHON%


@REM #ANCHOR - skip_venv
:skip_venv
goto :install_requirements


@REM #ANCHOR - install_requirements
:install_requirements
if EXIST tmp/requirements goto :launch
"%VENV_DIR%\Scripts\Python.exe" -m pip install -r requirements.txt >tmp/stdout.txt 2>tmp/stderr.txt
if %ERRORLEVEL% == 0 echo "success" >tmp/requirements
if %ERRORLEVEL% == 0 goto :launch
echo Unable to pip install requirements
goto :show_stdout_stderr


@REM #ANCHOR - launch
:launch
%PYTHON% wallhavenDownload.py %*
pause
exit /b


@REM #ANCHOR - show_stdout_stderr
:show_stdout_stderr
echo.
echo exit code: %errorlevel%
for /f %%i in ("tmp\stdout.txt") do set size=%%~zi
if %size% equ 0 goto :show_stderr
echo.
echo stdout:
type tmp\stdout.txt


@REM #ANCHOR - show_stderr
:show_stderr
for /f %%i in ("tmp\stderr.txt") do set size=%%~zi
if %size% equ 0 goto :show_stderr
echo.
echo stderr:
type tmp\stderr.txt


@REM #ANCHOR - endofscript
:endofscript
echo.
echo Launch unsuccessful. Exiting.
pause
