:: run_predictions.bat
python .\main.py goals predict 1 alpha_0_0_goals_ppb --model_load_name alpha_0_0_goals_ppb --prediction_config .\prediction_configs\prediction_daily.json --prediction_automate
python .\main.py btts predict 1 alpha_0_0_btts --model_load_name alpha_0_0_btts --prediction_config .\prediction_configs\prediction_daily.json --prediction_automate
python .\main.py winner predict 1 alpha_0_0_result --model_load_name alpha_0_0_result --prediction_config .\prediction_configs\prediction_daily.json --prediction_automate
