@echo off
REM Lokalny wrapper Windows dla FOOTBALL_PLAYED_BETTER_NOXG_V1
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.."

if "%~1"=="" (
  echo Usage: run_football_played_better_noxg.bat train^|evaluate^|assess-match^|assess-batch [extra args...]
  echo Examples:
  echo   run_football_played_better_noxg.bat train
  echo   run_football_played_better_noxg.bat assess-match --match-id 12345 --write-db
  echo   run_football_played_better_noxg.bat assess-batch --season-id 12 --write-db
  exit /b 1
)

set "COMMAND=%~1"
set "EXTRA_ARGS="
shift /1

:collect_args
if "%~1"=="" goto dispatch
set "EXTRA_ARGS=!EXTRA_ARGS! %1"
shift /1
goto collect_args

:dispatch
if /I "%COMMAND%"=="train" (
  python models\scripts\model_runner.py train --config models\configs\training\football_played_better_noxg_v1.json!EXTRA_ARGS!
  exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="evaluate" (
  python models\scripts\model_runner.py evaluate --config models\configs\training\football_played_better_noxg_v1.json!EXTRA_ARGS!
  exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="assess-match" (
  python models\scripts\model_runner.py assess-match --config models\configs\prediction\football_played_better_noxg_v1.json!EXTRA_ARGS!
  exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="assess-batch" (
  python models\scripts\model_runner.py assess-batch --config models\configs\prediction\football_played_better_noxg_v1.json!EXTRA_ARGS!
  exit /b %ERRORLEVEL%
)

echo Unknown command: %COMMAND%
exit /b 1
