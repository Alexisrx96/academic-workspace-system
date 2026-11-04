@echo off
setlocal EnableExtensions

set "PROJECT=%~dp0"
for %%I in ("%PROJECT%..") do set "TARGET=%%~fI"

pushd "%PROJECT%"
if errorlevel 1 goto :error

echo Actualizando dashboard academico desde el estado local...
uv run python scripts\study_control.py --target "%TARGET%" --days 7
if errorlevel 1 goto :error
uv run python scripts\evidence_queue.py --target "%TARGET%"
if errorlevel 1 goto :error
uv run python scripts\dashboard_pane.py --target "%TARGET%"
if errorlevel 1 goto :error
uv run python scripts\generation_report.py --target "%TARGET%"
if errorlevel 1 goto :error

if /I not "%~1"=="--no-open" start "Dashboard academico UTEC" "%TARGET%\Control Académico\00 - Dashboard académico.md"
popd
exit /b 0

:error
echo.
echo No se pudo actualizar el dashboard local.
popd
exit /b 1
