@echo off
setlocal EnableExtensions

set /p HORA=Hora diaria para sincronizar Blackboard [18:30]: 
if "%HORA%"=="" set "HORA=18:30"

set "SCRIPT=%~dp0Control-Semanal.bat"
set "ACTION=cmd.exe /d /c ""%SCRIPT%" --no-open""

schtasks.exe /Create /TN "UTEC Blackboard Sync Diaria" /TR "%ACTION%" /SC DAILY /ST %HORA% /IT /RL LIMITED /F
if errorlevel 1 (
  echo No se pudo crear la tarea diaria de Blackboard.
  exit /b 1
)

echo Sincronizacion diaria de Blackboard creada para las %HORA%.
echo Requiere Chrome abierto con Blackboard autenticado.
exit /b 0
