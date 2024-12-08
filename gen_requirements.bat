@ECHO OFF
setlocal EnableDelayedExpansion

set "VENV_DIR=%~dp0%.venv"
set "PYTHON=%VENV_DIR%\Scripts\Python.exe"
call "%VENV_DIR%\Scripts\activate.bat"
echo Using venv: !PYTHON!
"%PYTHON%" -c "import sys; print(sys.version)"

for /f "delims=" %%i in ('pip list --local --exclude pip --exclude setuptools --exclude wheel --not-required --format=freeze') do (
    echo %%i
	echo %%i| findstr /v "pre_commit pytest types-" >> temp_requirements.txt
)
move /y temp_requirements.txt requirements.txt

endlocal
exit /b
