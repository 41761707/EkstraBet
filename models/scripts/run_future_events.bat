@echo off
setlocal

set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%"

if "%~1"=="" (
    echo Usage: models\scripts\run_future_events.bat ^<train-result^|train-btts^|train-goals^|evaluate-result^|evaluate-btts^|evaluate-goals^|predict-pair^|predict-batch^> [arguments]
    exit /b 2
)

set "ACTION=%~1"
shift

if /I "%ACTION%"=="train-result" (
    python models\scripts\model_runner.py train --config models\configs\training\football_result_v2.json %*
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="train-btts" (
    python models\scripts\model_runner.py train --config models\configs\training\football_btts_v2.json %*
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="train-goals" (
    python models\scripts\model_runner.py train --config models\configs\training\football_goals_poisson_v1.json %*
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="evaluate-result" (
    python models\scripts\model_runner.py evaluate --config models\configs\training\football_result_v2.json %*
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="evaluate-btts" (
    python models\scripts\model_runner.py evaluate --config models\configs\training\football_btts_v2.json %*
    exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="evaluate-goals" (
    python models\scripts\model_runner.py evaluate --config models\configs\training\football_goals_poisson_v1.json %*
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
    --goals-config models\configs\prediction\football_goals_poisson_v1.json %*
exit /b %ERRORLEVEL%
