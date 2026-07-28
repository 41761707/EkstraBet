@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

python models\scripts\model_runner.py refresh-statistics %*
exit /b %ERRORLEVEL%
