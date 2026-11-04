@echo off
setlocal EnableExtensions

set /p HORA=Hora diaria para el recordatorio [18:30]: 
if "%HORA%"=="" set "HORA=18:30"

set "SCRIPT=%~dp0Control-Semanal.bat"
set "ACTION=cmd.exe /d /c ""%SCRIPT%"""

schtasks.exe /Create /TN "UTEC Control Academico" /TR "%ACTION%" /SC DAILY /ST %HORA% /IT /RL LIMITED /F
if errorlevel 1 (
  echo No se pudo crear la tarea programada.
  exit /b 1
)

echo Recordatorio diario creado para las %HORA%.
echo Se ejecutara solo con tu sesion de Windows iniciada y necesitara Chrome con Blackboard autenticado.
exit /b 0
