@echo off
schtasks.exe /Delete /TN "UTEC Pomodoro" /F
if errorlevel 1 exit /b 1
echo Pomodoro desinstalado.
exit /b 0
