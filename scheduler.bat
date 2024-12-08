@ECHO OFF
setlocal

:: Run with Task Scheduler
set "SCHEDULER=1"
cd /d "%~dp0"
call start.bat

endlocal
exit /b
