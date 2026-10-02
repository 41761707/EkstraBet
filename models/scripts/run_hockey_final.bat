@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

set "MATCH_IDS="
:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--match-ids" goto read_match_ids
echo Unknown argument: %~1
echo Usage: models\scripts\run_hockey_final.bat --match-ids id[,id...]
exit /b 2

:read_match_ids
shift
if "%~1"=="" (
    echo Missing value for --match-ids
    exit /b 2
)
set "MATCH_IDS=%~1"
shift
goto parse_args

:args_done
if "%MATCH_IDS%"=="" (
    echo Usage: models\scripts\run_hockey_final.bat --match-ids id[,id...]
    exit /b 2
)

python models\scripts\model_runner.py predict-hockey --league-id 45 --stage final --match-ids %MATCH_IDS% --write-db --select-finals
if errorlevel 1 exit /b %ERRORLEVEL%

python models\scripts\model_runner.py predict-hockey-props --league-id 45 --stage final --match-ids %MATCH_IDS% --write-db
if errorlevel 1 exit /b %ERRORLEVEL%

python models\scripts\model_runner.py refresh-statistics --write-db
exit /b %ERRORLEVEL%
