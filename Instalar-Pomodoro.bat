@echo off
setlocal EnableExtensions
set "SCRIPT=%~dp0Control-Pomodoro.bat"
set "ACTION=cmd.exe /d /c ""%SCRIPT%"""
schtasks.exe /Create /TN "UTEC Pomodoro" /TR "%ACTION%" /SC MINUTE /MO 1 /IT /RL LIMITED /F
if errorlevel 1 exit /b 1
echo Pomodoro programado cada minuto.
exit /b 0
