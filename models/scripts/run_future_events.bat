@echo off
setlocal EnableExtensions

set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%"

if "%~1"=="" (
    echo Usage: models\scripts\run_future_events.bat ^<train-result^|train-btts^|train-goals^|evaluate-result^|evaluate-btts^|evaluate-goals^|predict-pair^|predict-batch^> [arguments]
    echo.
    echo Examples:
    echo   run_future_events.bat predict-batch --league-id 1 --write-db --select-finals
    echo   run_future_events.bat predict-pair --home 10 --away 20 --as-of 2026-07-23 --match-id 123 --write-db
    exit /b 2
)

set "ACTION=%~1"
shift /1

rem CMD nie aktualizuje %%* po shift — zbieramy reszte argumentow recznie
set "REST="
:collect_args
if "%~1"=="" goto dispatch
set "REST=%REST% %1"
shift /1
goto collect_args

:dispatch
if /I "%ACTION%"=="train-result" (
    python models\scripts\model_runner.py train --config models\configs\training\football_result_v2.json%REST%
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="train-btts" (
    python models\scripts\model_runner.py train --config models\configs\training\football_btts_v2.json%REST%
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="train-goals" (
    python models\scripts\model_runner.py train --config models\configs\training\football_goals_poisson_v1.json%REST%
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="evaluate-result" (
    python models\scripts\model_runner.py evaluate --config models\configs\training\football_result_v2.json%REST%
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="evaluate-btts" (
    python models\scripts\model_runner.py evaluate --config models\configs\training\football_btts_v2.json%REST%
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="evaluate-goals" (
    python models\scripts\model_runner.py evaluate --config models\configs\training\football_goals_poisson_v1.json%REST%
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="predict-pair" goto predict
if /I "%ACTION%"=="predict-batch" goto predict

echo Unknown action: %ACTION%
exit /b 2

:predict
python models\scripts\model_runner.py %ACTION% ^
    --result-config models\configs\prediction\football_result_v2.json ^
    --btts-config models\configs\prediction\football_btts_v2.json ^
    --goals-config models\configs\prediction\football_goals_poisson_v1.json%REST%
exit /b %ERRORLEVEL%
