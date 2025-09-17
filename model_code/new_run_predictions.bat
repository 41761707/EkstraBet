:: new_run_predictions.bat
python main.py --mode predict --model_config .\model_btts_dev\alpha_0_0_btts_config_redefined.json --prediction_config .\prediction_configs\prediction_sample.json --prediction_automate
python main.py --mode predict --model_config .\model_goals_dev\alpha_0_0_goals_ppb_config_redefined.json --prediction_config .\prediction_configs\prediction_sample.json --prediction_automate
python main.py --mode predict --model_config .\model_goals_dev\new_goals_6_classes_enchanced_config_redefined.json --prediction_config .\prediction_configs\prediction_sample.json --prediction_automate
python main.py --mode predict --model_config .\model_winner_dev\alpha_0_0_result_config_redefined.json --prediction_config .\prediction_configs\prediction_sample.json --prediction_automate
