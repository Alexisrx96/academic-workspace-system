@echo off
setlocal EnableExtensions

set "PROJECT=%~dp0"
set "SYNC_ARGS="
:parse_args
if "%~1"=="" goto args_ready
if /I "%~1"=="--no-open" set "NO_OPEN=1"
if /I "%~1"=="--force-sync" set "SYNC_ARGS=%SYNC_ARGS% --force-sync"
shift
goto parse_args
:args_ready
for %%I in ("%PROJECT%..") do set "TARGET=%%~fI"

pushd "%PROJECT%"
if errorlevel 1 goto :error

echo [1/2] Sincronizando Blackboard de forma diferencial...
set "SYNC_ATTEMPTED=1"
uv run --extra browser --extra ocr academic-workspace --target "%TARGET%" %SYNC_ARGS%
if errorlevel 1 goto :error
set "SYNC_DONE=1"

echo [2/2] Actualizando control semanal, calendario y recordatorios...
uv run python scripts\study_control.py --target "%TARGET%" --days 7 --sync-status verified
if errorlevel 1 goto :error

if not defined NO_OPEN start "Control academico UTEC" "%TARGET%\Control Académico\Estado semanal.md"
popd
exit /b 0

:error
if defined SYNC_ATTEMPTED if not defined SYNC_DONE uv run python scripts\study_control.py --target "%TARGET%" --days 7 --sync-status unavailable
echo.
echo No se pudo completar el control. Verifica que Chrome siga abierto y que Blackboard conserve la sesion iniciada.
popd
exit /b 1
