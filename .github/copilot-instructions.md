# Copilot Instructions for Ekstrabet

## Project Overview
- Ekstrabet consists of two main components:
  - `web_code/`: Streamlit web application for user interaction, navigation, and visualization.
  - `model_code/`: Python modules for data preparation, rating calculation, model training, prediction, and testing.
- All data is loaded from a database using custom queries via `db_module`.

## Architecture & Data Flow
- The web app (`Home.py`) provides navigation and UI, dynamically generating links for each league using database data.
- The model pipeline (`main.py` in `model_code/`) orchestrates:
  - Data extraction and preparation (`dataprep_module`)
  - Rating calculation (`ratings_module`)
  - Model training and prediction (`model_module`, `prediction_module`)
  - Configuration management (`config_manager`)
  - Testing (`test_module`)
- Data flows from database → data prep → rating calculation → model training/prediction → results/testing.

## Developer Workflows
- To run the web app: `streamlit run Home.py` from `web_code/`.
- To run model training/prediction/testing:
  - `python main.py <model_type> <mode> <load_weights> <model_name>` from `model_code/`.
    - Example: `python main.py winner train 1 alpha_0_0_result`
    - Modes: `train`, `predict`, `test`
- Configuration is managed via command-line arguments and `ConfigManager`.
- All database connections must be closed after use.

## Project-Specific Patterns
- Calculator functions for rating attributes are mapped in `get_calculator_func` (see `main.py`).
- Model configuration and rating types are handled via nested dictionaries and passed through the pipeline.
- All UI and documentation is in Polish; maintain language consistency.
- Custom HTML/CSS is injected in Streamlit with `unsafe_allow_html=True`.

## Integration Points
- All database operations use `db_module`.
- Model weights and configs are saved/loaded from `model_{model_type}_dev/` directories.
- External data sources referenced for attribution: `flashscore.pl`, `opta.com`, `NHL API`, `dailyfaceoff.com`.

## Conventions
- Use Pandas for all SQL query results and data manipulation.
- Page files in `pages/` should follow the naming pattern `{LeagueName}.py` and be referenced in `Home.py`.
- Model pipeline modules should be imported and used as in `main.py`.

## Example: Model Training Workflow
1. Prepare configuration and database.
2. Run: `python main.py winner train 0 alpha_0_0_result`
3. The pipeline will extract data, calculate ratings, train the model, and save results/configs.

## Example: Adding a New League
1. Add a new league to the database (`leagues` table).
2. Create a new file in `pages/` named after the league (e.g., `pages/Serie A.py`).
3. The new league will automatically appear in the navigation if `active=1` in the database.

---
For questions or unclear conventions, review `Home.py`, `main.py`, and the database schema, or ask the project author (see contact info in the UI).
