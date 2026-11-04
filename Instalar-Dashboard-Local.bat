@echo off
setlocal EnableExtensions

set "SCRIPT=%~dp0Control-Pasivo-Academico.bat"
set "ACTION=cmd.exe /d /c ""%SCRIPT%" --no-open""

schtasks.exe /Create /TN "UTEC Dashboard Local" /TR "%ACTION%" /SC MINUTE /MO 60 /IT /RL LIMITED /F
if errorlevel 1 (
  echo No se pudo crear la tarea programada del dashboard local.
  exit /b 1
)

echo Dashboard local programado cada 60 minutos.
exit /b 0
