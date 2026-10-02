@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

python models\scripts\model_runner.py build-hockey-lineups --league-id 45 --write-db
if errorlevel 1 exit /b %ERRORLEVEL%

python models\scripts\model_runner.py predict-hockey --league-id 45 --stage initial --write-db --select-finals
if errorlevel 1 exit /b %ERRORLEVEL%

python models\scripts\model_runner.py predict-hockey-props --league-id 45 --stage initial --write-db
if errorlevel 1 exit /b %ERRORLEVEL%

python models\scripts\model_runner.py refresh-statistics --write-db
exit /b %ERRORLEVEL%
