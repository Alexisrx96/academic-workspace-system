@echo off
schtasks.exe /Delete /TN "UTEC Blackboard Sync Diaria" /F
if errorlevel 1 exit /b 1
echo Sincronizacion diaria de Blackboard eliminada.
exit /b 0
