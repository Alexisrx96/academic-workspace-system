@echo off
setlocal EnableExtensions
set "PROJECT=%~dp0"
for %%I in ("%PROJECT%..") do set "TARGET=%%~fI"
pushd "%PROJECT%"
uv run python scripts\pomodoro.py notify --target "%TARGET%" --backend auto
popd
exit /b 0
