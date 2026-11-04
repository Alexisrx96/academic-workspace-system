@echo off
setlocal EnableExtensions

set "PROJECT=%~dp0"
for %%I in ("%PROJECT%..") do set "TARGET=%%~fI"

call "%PROJECT%Actualizar-Dashboard-Local.bat" --no-open
if errorlevel 1 exit /b 1

pushd "%PROJECT%"
uv run python scripts\academic_alerts.py --target "%TARGET%" --notify
if errorlevel 1 echo No se pudo mostrar una notificacion; el dashboard local ya fue actualizado.
popd
exit /b 0
