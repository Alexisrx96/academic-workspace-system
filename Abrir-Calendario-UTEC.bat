@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..") do set "TARGET=%%~fI"

if not exist "%TARGET%\Control Académico\UTEC-Fechas.ics" (
  echo Aun no existe el calendario. Ejecuta primero Control-Semanal.bat.
  exit /b 1
)
start "Calendario UTEC" "%TARGET%\Control Académico\UTEC-Fechas.ics"
exit /b 0
