class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.model_type = None
        self.model_mode = None
        self.load_weights = None
        self.model_name = None
        self.model_load_name = None
        self.leagues = [25]
        self.sport_id = 1
        self.country = []
        self.window_size = 5
        self.feature_columns = []
        self.rating_types = []
        self.match_attributes = []
        self.rating_config = {}
        
    def load_from_args(self, args):
        self.model_type = args[1] #[winner, btts, goals, exact]
        self.model_mode = args[2] #[train, predict]
        self.load_weights = args[3] #[0, 1]
        self.model_name = args[4] #[nazwa jaka ma dostac model / nazwa na podstawie ktorej dokonujemy predykcji]
        if self.model_mode == 'train' and self.load_weights == '1':
            self.model_load_name = args[5] #[nazwa modelu, z ktorego wczytujemy wagi]
        if self.model_type in ['winner', 'exact']:
            self.rating_types = ['gap', 'elo', 'czech']
        else:
            self.rating_types = ['gap', 'czech']
        self._setup_configurations()

    def _setup_configurations(self):
        # Definiowanie kolumn dla każdego typu ratingu
        self.elo_columns = ['home_team_elo', 'away_team_elo']
        self.czech_columns = ['home_team_win_pct',
                              'home_team_draw_pct',
                              'home_team_gs_avg',
                              'home_team_gc_avg',
                              'home_team_gs_std',
                              'home_team_gc_std',
                              'away_team_win_pct',
                              'away_team_draw_pct',
                              'away_team_gs_avg',
                              'away_team_gc_avg',
                              'away_team_gs_std',
                              'away_team_gc_std']
        self.gap_columns = [
            'home_home_att_power',
            'home_home_def_power',
            'away_away_att_power',
            'away_away_def_power',
            'home_goals_avg',
            'away_goals_avg'
        ]

        # Dynamiczne tworzenie feature_columns na podstawie rating_types
        self.feature_columns = []
        if 'elo' in self.rating_types:
            self.feature_columns.extend(self.elo_columns)
        if 'gap' in self.rating_types:
            self.feature_columns.extend(self.gap_columns)
        if 'czech' in self.rating_types:
            self.feature_columns.extend(self.czech_columns)

        # Konfiguracja match attributes
        self.match_attributes = [
            #{
            #    'name': 'goals_home',
            #    'calculator': lambda match: int(match['home_team_goals'])
            #},
            #        {
            #    'name': 'goals_away',
            #    'calculator': lambda match: int(match['away_team_goals'])
            #},
            #{
            #    'name': 'btts',
            #    'calculator': lambda match: 1 if match['home_team_goals'] > 0 and match['away_team_goals'] > 0 else 0
            #},
            {
                'name': 'chances_home',
                'calculator': lambda match: int(match['home_team_ck']) + int(match['home_team_sc'])
            },
            {
                'name': 'chances_away',
                'calculator': lambda match: int(match['away_team_ck']) + int(match['away_team_sc'])
            },
        ]

        # Konfiguracja ratingów
        self.rating_config = {
            'winner': {
                'rating_type': self.rating_types,
                'model_path': f'model_winner_dev/{self.model_name}.h5'
            },
            'goals': {
                'rating_type': self.rating_types,
                'model_path': f'model_goals_dev/{self.model_name}.h5'
            },
            'btts': {
                'rating_type': self.rating_types,
                'model_path': f'model_btts_dev/{self.model_name}.h5'
            },
            'exact': {
                'rating_type': self.rating_types,
                'model_path': f'model_exact_dev/{self.model_name}.h5'
            }
        }

        # Konfiguracja modelu (training_json)
        self.model_config ={
            "model_name": self.model_name,
            "model_type": self.model_type,
            "window_size": self.window_size,
            "train_accuracy": 0,
            "train_loss": 0,
            "val_accuracy": 0,
            "val_loss": 0,
            "model_path": f'model_{self.model_type}_dev/{self.model_name}.h5',
            "feature_columns": self.feature_columns,
            "ratings": {
                "elo": {
                    "enabled": 'elo' in self.rating_types,
                    "initial_rating": 1500,
                    "second_tier_coef": 0.8,
                    "columns": self.elo_columns if 'elo' in self.rating_types else []
                },
                "gap": {
                    "enabled": 'gap' in self.rating_types,
                    "columns": self.gap_columns if 'gap' in self.rating_types else [],
                    "match_attributes": [
                        {
                            "name": attr["name"],
                            "calculator" : attr["calculator"]
                        } for attr in self.match_attributes
                    ]
                },
                "czech" : {
                    "enabled" : 'czech' in self.rating_types,
                    "columns" : self.czech_columns if 'czech' in self.rating_types else [],
                }
            },
            "model": {
                "type" : "LSTM",
                "architecture": {
                    "lstm_layers": [
                        {
                            "units": [
                                256,
                                128,
                                64
                            ],
                            "activation": [
                                "tanh",
                                "tanh",
                                "tanh"
                            ],
                            "return_sequences": [
                                True,
                                True,
                                False
                            ],
                            "dropout": [
                                0.2,
                                0.2,
                                0.0
                            ],
                            "batch_normalization": [
                                True,
                                True,
                                False
                            ]
                        },
                        {
                            "units": [
                                256,
                                128,
                                64
                            ],
                            "activation": [
                                "tanh",
                                "tanh",
                                "tanh"
                            ],
                            "return_sequences": [
                                True,
                                True,
                                False
                            ],
                            "dropout": [
                                0.2,
                                0.2,
                                0.0
                            ],
                            "batch_normalization": [
                                True,
                                True,
                                False
                            ]
                        }
                    ],
                    "dense_layers": [
                        {
                            "units": 128,
                            "activation": "relu",
                            "regularization_l2": None,
                            "dropout": 0.2
                        },
                        {
                            "units": 64,
                            "activation": "relu",
                            "regularization_l2": None
                        },
                        {
                            "units": 16,
                            "activation": "linear",
                            "regularization_l2": None
                        }
                    ],
                    "output": {
                        "units": 3,
                        "activation": "softmax"
                    }
                },
                "compilation": {
                    "optimizer": {
                        "type": "Adam",
                        "learning_rate": 0.00001
                    },
                    "loss": "categorical_crossentropy",
                    "metrics": [
                        "accuracy",
                        "Precision",
                        "Recall"
                    ]
                }
            },
            "training_config": {
                "sport_id": 1,
                "leagues": [],
                "country": [],
                "load_weights": False
            }
        }