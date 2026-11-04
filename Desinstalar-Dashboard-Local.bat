@echo off
schtasks.exe /Delete /TN "UTEC Dashboard Local" /F
if errorlevel 1 exit /b 1
echo Tarea del dashboard local eliminada.
exit /b 0
