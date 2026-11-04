@echo off
schtasks.exe /Delete /TN "UTEC Control Academico" /F
if errorlevel 1 exit /b 1
echo Recordatorio diario eliminado.
exit /b 0
