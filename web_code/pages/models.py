from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKeyConstraint, Index, Integer, String, text
from sqlalchemy.dialects.mysql import FLOAT, VARCHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime

class Base(DeclarativeBase):
    pass


class Bookmakers(Base):
    __tablename__ = 'bookmakers'
    __table_args__ = (
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'List of analized bookmakers'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="bookmaker's ID")
    name: Mapped[Optional[str]] = mapped_column(String(45, 'utf8mb3_polish_ci'), comment='Name of a bookmaker')

    bets: Mapped[List['Bets']] = relationship('Bets', back_populates='bookmakers')
    odds: Mapped[List['Odds']] = relationship('Odds', back_populates='bookmakers')


class Countries(Base):
    __tablename__ = 'countries'
    __table_args__ = {'comment': 'List of all countries considered in model'}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Country ID')
    name: Mapped[Optional[str]] = mapped_column(VARCHAR(45), comment='Name of a Country')
    short: Mapped[Optional[str]] = mapped_column(VARCHAR(3), comment="Country's shorter name (up to 3 letters)")
    emoji: Mapped[Optional[str]] = mapped_column(String(45, 'utf8mb4_unicode_ci'), comment="Country's flag as emoji")

    leagues: Mapped[List['Leagues']] = relationship('Leagues', back_populates='countries')


class Events(Base):
    __tablename__ = 'events'
    __table_args__ = (
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'Table of all events covered by  models'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Id of an event')
    name: Mapped[Optional[str]] = mapped_column(String(45, 'utf8mb3_polish_ci'), comment='Name of an event')

    bets: Mapped[List['Bets']] = relationship('Bets', back_populates='event')
    final_predictions: Mapped[List['FinalPredictions']] = relationship('FinalPredictions', back_populates='event')
    hockey_match_events: Mapped[List['HockeyMatchEvents']] = relationship('HockeyMatchEvents', back_populates='event')
    odds: Mapped[List['Odds']] = relationship('Odds', back_populates='events')
    predictions: Mapped[List['Predictions']] = relationship('Predictions', back_populates='event')


class Gamblers(Base):
    __tablename__ = 'gamblers'
    __table_args__ = {'comment': 'All information about gamblers'}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Gambler ID')
    gambler_name: Mapped[Optional[str]] = mapped_column(VARCHAR(30), comment="Gambler's name")
    parlays_played: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"), comment='Number of parlays played by given gambler')
    parlays_won: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"), comment='Number of parlays won by given gambler')
    balance: Mapped[Optional[float]] = mapped_column(Float, server_default=text("'0'"), comment='Current account balance for given gambler')
    active: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'1'"), comment='Is gambler active, 1 if yes, 0 if no')

    gambler_parlays: Mapped[List['GamblerParlays']] = relationship('GamblerParlays', back_populates='gambler')


class HockeyMatchRosters(Base):
    __tablename__ = 'hockey_match_rosters'
    __table_args__ = (
        Index('MATCH_ROSTERS_MATCH_idx', 'match_id'),
        {'comment': 'Rosters for given match. Each entry presents one player'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Entry ID')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Match ID')
    player_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Player ID')
    team_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Team ID')
    position: Mapped[Optional[str]] = mapped_column(VARCHAR(5), comment='Position on the field (for hockey: C - center / RW - right winger / LW - left winger / D - defensmen / G - goaltender)')
    line: Mapped[Optional[int]] = mapped_column(Integer, comment='Line assigned to player (there are typically 4 lines in hockey games)')
    number: Mapped[Optional[int]] = mapped_column(Integer, comment='Number on shirt')


class Players(Base):
    __tablename__ = 'players'
    __table_args__ = (
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': "Table containing information about player's stats"}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Player ID')
    first_name: Mapped[Optional[str]] = mapped_column(VARCHAR(45), comment="Player's first name")
    last_name: Mapped[Optional[str]] = mapped_column(VARCHAR(45), comment="Player's last name")
    common_name: Mapped[Optional[str]] = mapped_column(VARCHAR(60), comment='last_name + first letter of first name (although there are exceptions)')
    current_club: Mapped[Optional[int]] = mapped_column(Integer, comment='Team ID')
    current_country: Mapped[Optional[int]] = mapped_column(Integer, comment='Country ID')
    sports_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Sport ID')
    position: Mapped[Optional[str]] = mapped_column(VARCHAR(5), comment='Position on the field (for hockey: C - center / RW - right winger / LW - left winger / D - defensmen / G - goaltender)')
    external_id: Mapped[Optional[str]] = mapped_column(VARCHAR(20), comment='NHL API ID')
    external_flash_id: Mapped[Optional[str]] = mapped_column(VARCHAR(20), comment='Flashscore_ID')
    active: Mapped[Optional[int]] = mapped_column(Integer, comment='Is player active? (currently assigned to a club / country?)\n1 - YES / 0 - NO')

    hockey_rosters: Mapped[List['HockeyRosters']] = relationship('HockeyRosters', back_populates='player')
    transfers: Mapped[List['Transfers']] = relationship('Transfers', back_populates='player')
    hockey_match_events: Mapped[List['HockeyMatchEvents']] = relationship('HockeyMatchEvents', back_populates='player')
    hockey_match_player_stats: Mapped[List['HockeyMatchPlayerStats']] = relationship('HockeyMatchPlayerStats', back_populates='player')


class Seasons(Base):
    __tablename__ = 'seasons'
    __table_args__ = (
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'Seasons considered in project'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Season ID')
    years: Mapped[Optional[str]] = mapped_column(VARCHAR(10), comment='Years when given season takes place')

    leagues: Mapped[List['Leagues']] = relationship('Leagues', back_populates='current_season')
    matches: Mapped[List['Matches']] = relationship('Matches', back_populates='seasons')
    transfers: Mapped[List['Transfers']] = relationship('Transfers', back_populates='season')


class Sports(Base):
    __tablename__ = 'sports'
    __table_args__ = {'comment': "Sports' table"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Sport ID')
    name: Mapped[Optional[str]] = mapped_column(String(45, 'utf8mb3_polish_ci'), comment='Sport name')

    leagues: Mapped[List['Leagues']] = relationship('Leagues', back_populates='sport')
    models: Mapped[List['Models']] = relationship('Models', back_populates='sport')
    teams: Mapped[List['Teams']] = relationship('Teams', back_populates='sport')


class GamblerParlays(Base):
    __tablename__ = 'gambler_parlays'
    __table_args__ = (
        ForeignKeyConstraint(['gambler_id'], ['gamblers.id'], name='GAMBLER_FK'),
        Index('GAMBLER_FK_idx', 'gambler_id'),
        {'comment': "Gambler's parlays"}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Parlay ID')
    gambler_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Gambler ID')
    parlay_odds: Mapped[Optional[float]] = mapped_column(Float, comment="Multiplication of all given parlay's event's odds")
    stake: Mapped[Optional[float]] = mapped_column(Float, server_default=text("'1'"), comment='Money invested per parlay (in units)')
    settled: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"), comment='Is parlay settled, 0 if no, 1 if yes')
    parlay_outcome: Mapped[Optional[int]] = mapped_column(Integer, comment='Outcome of a parlay, 0 if lost, 1 if won')
    profit: Mapped[Optional[float]] = mapped_column(Float, server_default=text("'0'"), comment='Return (if below 0 then gambler lost money - name of a field can mislead)')
    creation_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment="Parlay's creation date (when the parlay was added to the DB)")

    gambler: Mapped[Optional['Gamblers']] = relationship('Gamblers', back_populates='gambler_parlays')
    events_parlays: Mapped[List['EventsParlays']] = relationship('EventsParlays', back_populates='parlay')


class Leagues(Base):
    __tablename__ = 'leagues'
    __table_args__ = (
        ForeignKeyConstraint(['country'], ['countries.id'], name='countryFK'),
        ForeignKeyConstraint(['current_season_id'], ['seasons.id'], name='league_seasonFK'),
        ForeignKeyConstraint(['sport_id'], ['sports.id'], name='sportFK'),
        Index('SEASONFK_idx', 'current_season_id'),
        Index('countryFK_idx', 'country'),
        Index('id_UNIQUE', 'id', unique=True),
        Index('sportFK_idx', 'sport_id'),
        {'comment': 'All leagues considered in model'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='League ID')
    name: Mapped[Optional[str]] = mapped_column(String(45, 'utf8mb3_polish_ci'), comment="League's name")
    country: Mapped[Optional[int]] = mapped_column(Integer, comment="Id of league's country")
    last_update: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, comment="Last time league's info (including matches and other information) was updated")
    active: Mapped[Optional[int]] = mapped_column(Integer, comment='1 if League taken into consideration, 0 if league is currently not supported')
    current_season_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Current season in given league, Seasons ID')
    tier: Mapped[Optional[int]] = mapped_column(Integer, comment="League's tier (1st or 2nd)")
    sport_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Sport ID')

    countries: Mapped[Optional['Countries']] = relationship('Countries', back_populates='leagues')
    current_season: Mapped[Optional['Seasons']] = relationship('Seasons', back_populates='leagues')
    sport: Mapped[Optional['Sports']] = relationship('Sports', back_populates='leagues')
    matches: Mapped[List['Matches']] = relationship('Matches', back_populates='leagues')


class Models(Base):
    __tablename__ = 'models'
    __table_args__ = (
        ForeignKeyConstraint(['sport_id'], ['sports.id'], name='MODELS_SPORTS'),
        Index('MODELS_SPORTS_idx', 'sport_id'),
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'list of created models'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb3_polish_ci'))
    active: Mapped[Optional[int]] = mapped_column(Integer)
    sport_id: Mapped[Optional[int]] = mapped_column(Integer)

    sport: Mapped[Optional['Sports']] = relationship('Sports', back_populates='models')


class Teams(Countries):
    __tablename__ = 'teams'
    __table_args__ = (
        ForeignKeyConstraint(['id'], ['countries.id'], name='COUNTRY_FK3'),
        ForeignKeyConstraint(['sport_id'], ['sports.id'], name='SPORT_FK3'),
        Index('CountryFK3_idx', 'country'),
        Index('SPORT_FK3_idx', 'sport_id'),
        Index('id_UNIQUE', 'id', unique=True),
        Index('name_UNIQUE', 'name', unique=True),
        {'comment': 'Table contains all teams considered in tests'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='id of a team')
    country: Mapped[Optional[int]] = mapped_column(Integer, comment="id of  team's country")
    name: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb3_polish_ci'), comment='Name of a team')
    shortcut: Mapped[Optional[str]] = mapped_column(VARCHAR(5), comment="Team's shortcut (usually no longer than 3 letters, although there could be some exceptions)")
    sport_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Sport ID')

    sport: Mapped[Optional['Sports']] = relationship('Sports', back_populates='teams')
    hockey_rosters: Mapped[List['HockeyRosters']] = relationship('HockeyRosters', back_populates='team')
    matches: Mapped[List['Matches']] = relationship('Matches', foreign_keys='[Matches.away_team]', back_populates='teams')
    matches_: Mapped[List['Matches']] = relationship('Matches', foreign_keys='[Matches.home_team]', back_populates='teams_')
    transfers: Mapped[List['Transfers']] = relationship('Transfers', foreign_keys='[Transfers.new_team_id]', back_populates='new_team')
    transfers_: Mapped[List['Transfers']] = relationship('Transfers', foreign_keys='[Transfers.old_team_id]', back_populates='old_team')
    hockey_match_player_stats: Mapped[List['HockeyMatchPlayerStats']] = relationship('HockeyMatchPlayerStats', back_populates='team')


class HockeyRosters(Base):
    __tablename__ = 'hockey_rosters'
    __table_args__ = (
        ForeignKeyConstraint(['player_id'], ['players.id'], name='PLAYER_TEAM_FK'),
        ForeignKeyConstraint(['team_id'], ['teams.id'], name='ROSTER_TEAM_FK'),
        Index('PLAYER_TEAM_FK_idx', 'player_id'),
        Index('ROSTER_TEAM_FK_idx', 'team_id'),
        {'comment': 'Projected line-ups for incoming game, one entry represents one '
                'player in line-up'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Player in lineup ID')
    team_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Team ID')
    player_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Player ID')
    number: Mapped[Optional[int]] = mapped_column(Integer, comment='Number on a shirt')
    line: Mapped[Optional[int]] = mapped_column(Integer, comment='Line assigned to player (1,2,3,4)')
    position: Mapped[Optional[str]] = mapped_column(VARCHAR(5), comment='Position on ice')
    pp: Mapped[Optional[int]] = mapped_column(Integer, comment='Is in PP? (1 - in first line [1PP], 2 - in second line [2PP], 0 - none of the above)')
    is_injured: Mapped[Optional[int]] = mapped_column(Integer, comment='Flag, 0 - no, 1 - yes')

    player: Mapped[Optional['Players']] = relationship('Players', back_populates='hockey_rosters')
    team: Mapped[Optional['Teams']] = relationship('Teams', back_populates='hockey_rosters')


class Matches(Base):
    __tablename__ = 'matches'
    __table_args__ = (
        ForeignKeyConstraint(['away_team'], ['teams.id'], name='TeamsFK2'),
        ForeignKeyConstraint(['home_team'], ['teams.id'], name='TeamsFK'),
        ForeignKeyConstraint(['league'], ['leagues.id'], name='LeagueFK2'),
        ForeignKeyConstraint(['season'], ['seasons.id'], name='SeasonFK'),
        Index('LeagueFK2_idx', 'league'),
        Index('SeasonFK_idx', 'season'),
        Index('SportFK_idx', 'sport_id'),
        Index('TeamsFK2_idx', 'away_team'),
        Index('TeamsFK_idx', 'home_team'),
        Index('id_UNIQUE', 'id', unique=True),
        Index('idx_matches_date', 'game_date'),
        Index('idx_matches_league_season', 'league', 'season'),
        {'comment': 'Table containg all matches considered in analysis'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Match's ID")
    league: Mapped[Optional[int]] = mapped_column(Integer, comment="League's ID")
    season: Mapped[Optional[int]] = mapped_column(Integer, comment="Season's ID")
    home_team: Mapped[Optional[int]] = mapped_column(Integer, comment='Id of a home team')
    away_team: Mapped[Optional[int]] = mapped_column(Integer, comment='Id of an away team')
    game_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, comment='Date of a game')
    home_team_goals: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored by home team')
    away_team_goals: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored by away team')
    home_team_xg: Mapped[Optional[float]] = mapped_column(Float, comment='XG - Expected goals')
    away_team_xg: Mapped[Optional[float]] = mapped_column(Float, comment='XG - Expected goals')
    home_team_bp: Mapped[Optional[int]] = mapped_column(Integer, comment='BP - Ball Possesion')
    away_team_bp: Mapped[Optional[int]] = mapped_column(Integer, comment='BP - Ball Possesion')
    home_team_sc: Mapped[Optional[int]] = mapped_column(Integer, comment='SC - Scoring Chances')
    away_team_sc: Mapped[Optional[int]] = mapped_column(Integer, comment='SC - Scoring Chances')
    home_team_sog: Mapped[Optional[int]] = mapped_column(Integer, comment='SOG - Shots on Goal')
    away_team_sog: Mapped[Optional[int]] = mapped_column(Integer)
    home_team_fk: Mapped[Optional[int]] = mapped_column(Integer, comment='FK - Free Kicks')
    away_team_fk: Mapped[Optional[int]] = mapped_column(Integer, comment='FK - Free Kicks')
    home_team_ck: Mapped[Optional[int]] = mapped_column(Integer, comment='CK - Corner Kicks')
    away_team_ck: Mapped[Optional[int]] = mapped_column(Integer, comment='CK - Corner Kicks')
    home_team_off: Mapped[Optional[int]] = mapped_column(Integer, comment='off - Offsides')
    away_team_off: Mapped[Optional[int]] = mapped_column(Integer, comment='off - Offsides')
    home_team_fouls: Mapped[Optional[int]] = mapped_column(Integer)
    away_team_fouls: Mapped[Optional[int]] = mapped_column(Integer)
    home_team_yc: Mapped[Optional[int]] = mapped_column(Integer)
    away_team_yc: Mapped[Optional[int]] = mapped_column(Integer, comment='YC - Yellow Cards')
    home_team_rc: Mapped[Optional[int]] = mapped_column(Integer, comment='RC - Red Cards')
    away_team_rc: Mapped[Optional[int]] = mapped_column(Integer)
    round: Mapped[Optional[int]] = mapped_column(Integer, comment='The round in which the game was played\\\\\\\\\\\\\\\\nSpecial round numbers for playoff format\\\\n900 - 1st game in 1/64\\\\n901 - 2nd game in 1/64\\\\n902 - 3rd game in 1/64\\\\n903 - 4rd game in 1/64\\\\n904 - 5th game in 1/64\\\\n905 - 6th game in 1/64\\\\n906 - 7th game in 1/64\\\\n910 - 916 - same as above for 1/32\\\\n920 - 926 - same as above for 1/16\\\\n930 - 936 - same as above for 1/8\\\\n940 - 946 - same as above for 1/4 (quarterfinal)\\\\n950 - 956 - same as above for 1/2 (semifinal)\\\\n960 - 966 - same as above for final\\\\n 100 - typical round in NHL / NBA / MLS (and other leagues where there is no clear distinction between rounds)')
    result: Mapped[Optional[str]] = mapped_column(String(1, 'utf8mb3_polish_ci'), comment='Result of a match. 1 - Home team won, X - draw, 2 - Away team won')
    sport_id: Mapped[Optional[int]] = mapped_column(Integer)

    teams: Mapped[Optional['Teams']] = relationship('Teams', foreign_keys=[away_team], back_populates='matches')
    teams_: Mapped[Optional['Teams']] = relationship('Teams', foreign_keys=[home_team], back_populates='matches_')
    leagues: Mapped[Optional['Leagues']] = relationship('Leagues', back_populates='matches')
    seasons: Mapped[Optional['Seasons']] = relationship('Seasons', back_populates='matches')
    bets: Mapped[List['Bets']] = relationship('Bets', back_populates='match')
    final_predictions: Mapped[List['FinalPredictions']] = relationship('FinalPredictions', back_populates='match')
    football_special_round_add: Mapped[List['FootballSpecialRoundAdd']] = relationship('FootballSpecialRoundAdd', back_populates='match')
    hockey_match_events: Mapped[List['HockeyMatchEvents']] = relationship('HockeyMatchEvents', back_populates='match')
    hockey_match_player_stats: Mapped[List['HockeyMatchPlayerStats']] = relationship('HockeyMatchPlayerStats', back_populates='match')
    hockey_matches_add: Mapped[List['HockeyMatchesAdd']] = relationship('HockeyMatchesAdd', back_populates='match')
    odds: Mapped[List['Odds']] = relationship('Odds', back_populates='match')
    predictions: Mapped[List['Predictions']] = relationship('Predictions', back_populates='match')


class Transfers(Base):
    __tablename__ = 'transfers'
    __table_args__ = (
        ForeignKeyConstraint(['new_team_id'], ['teams.id'], name='TRANSFER_NEW_TEAM_FK'),
        ForeignKeyConstraint(['old_team_id'], ['teams.id'], name='TRANSFER_OLD_TEAM_FK'),
        ForeignKeyConstraint(['player_id'], ['players.id'], name='TRANSFER_PLAYER_FK'),
        ForeignKeyConstraint(['season_id'], ['seasons.id'], name='TRANSFER_SEASON_FK'),
        Index('TRANSFER_NEW_TEAM_FK_idx', 'new_team_id'),
        Index('TRANSFER_OLD_TEAM_FK_idx', 'old_team_id'),
        Index('TRANSFER_PLAYER_FK_idx', 'player_id'),
        Index('TRANSFER_SEASON_FK_idx', 'season_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(Integer)
    old_team_id: Mapped[Optional[int]] = mapped_column(Integer)
    new_team_id: Mapped[Optional[int]] = mapped_column(Integer)
    season_id: Mapped[Optional[int]] = mapped_column(Integer)

    new_team: Mapped[Optional['Teams']] = relationship('Teams', foreign_keys=[new_team_id], back_populates='transfers')
    old_team: Mapped[Optional['Teams']] = relationship('Teams', foreign_keys=[old_team_id], back_populates='transfers_')
    player: Mapped[Optional['Players']] = relationship('Players', back_populates='transfers')
    season: Mapped[Optional['Seasons']] = relationship('Seasons', back_populates='transfers')


class Bets(Base):
    __tablename__ = 'bets'
    __table_args__ = (
        ForeignKeyConstraint(['bookmaker'], ['bookmakers.id'], name='BETS_BOOKMAKERS'),
        ForeignKeyConstraint(['event_id'], ['events.id'], name='BETS_EVENTS'),
        ForeignKeyConstraint(['match_id'], ['matches.id'], name='BETS_MATCHES'),
        Index('BETS_BOOKMAKERS_idx', 'bookmaker'),
        Index('BETS_EVENTS_idx', 'event_id'),
        Index('BETS_MATCHES_idx', 'match_id'),
        Index('idx_bets_outcome', 'outcome'),
        {'comment': 'All bets possible to make by computer\n'
                'New feature: Gamblers are able to add their own bets (for example '
                'BTTS & O2.5, which is not supported by system at the moment - '
                'additional column custom_bet'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Bet ID')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Match ID')
    event_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Event ID')
    odds: Mapped[Optional[float]] = mapped_column(Float, comment='Odds of current event')
    EV: Mapped[Optional[float]] = mapped_column(Float, comment='ValueBet (Expected Value)\nProbability of event * Max(Odds from bookmakers) - 1\nEV > 0 - bet worth considering, model sees an "edge" over bookmakers')
    bookmaker: Mapped[Optional[int]] = mapped_column(Integer, comment='Bookmaker that set given odds')
    outcome: Mapped[Optional[int]] = mapped_column(Integer, comment='0 if incorrect, 1 if correct')
    custom_bet: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"), comment='Bet inserted by user = 1, otherwise = 0')

    bookmakers: Mapped[Optional['Bookmakers']] = relationship('Bookmakers', back_populates='bets')
    event: Mapped[Optional['Events']] = relationship('Events', back_populates='bets')
    match: Mapped[Optional['Matches']] = relationship('Matches', back_populates='bets')
    events_parlays: Mapped[List['EventsParlays']] = relationship('EventsParlays', back_populates='bet')


class FinalPredictions(Base):
    __tablename__ = 'final_predictions'
    __table_args__ = (
        ForeignKeyConstraint(['event_id'], ['events.id'], name='FINAL_EVENTS'),
        ForeignKeyConstraint(['match_id'], ['matches.id'], name='FINAL_MATCHES'),
        Index('FINAL_EVENTS_idx', 'event_id'),
        Index('FINAL_MATCHES_idx', 'match_id'),
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'Final model predictions for each match, for each event'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Final prediction ID')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Match ID')
    event_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Event ID')
    confidence: Mapped[Optional[float]] = mapped_column(Float, comment="Prediction's confidence (0<= confidence <= 100)")
    outcome: Mapped[Optional[int]] = mapped_column(Integer, comment='0 if incorrect, 1 if correct')

    event: Mapped[Optional['Events']] = relationship('Events', back_populates='final_predictions')
    match: Mapped[Optional['Matches']] = relationship('Matches', back_populates='final_predictions')


class FootballSpecialRoundAdd(Base):
    __tablename__ = 'football_special_round_add'
    __table_args__ = (
        ForeignKeyConstraint(['match_id'], ['matches.id'], name='BALL_ADD_MATCHID'),
        Index('BALL_ADD_MATCHID_idx', 'match_id'),
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'Special rounds in football - additional data (OT specific)'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Special round data ID')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Referenced match ID')
    OT: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'1'"), comment='Flag, if OT (overtime)  happened 1 else 0')
    PEN: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"), comment='Flag, if penalties  happened 1 else 0')
    home_team_goals_after_ot: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored by home team in regular time + in overtime')
    away_team_goals_after_ot: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored by away team in regular time + in overtime')
    home_team_pen_score: Mapped[Optional[int]] = mapped_column(Integer, comment='if penalties happened, number of goals scored during penalties by home team')
    away_team_pen_score: Mapped[Optional[int]] = mapped_column(Integer, comment='if penalties happened, number of goals scored during penalties by home team')

    match: Mapped[Optional['Matches']] = relationship('Matches', back_populates='football_special_round_add')


class HockeyMatchEvents(Base):
    __tablename__ = 'hockey_match_events'
    __table_args__ = (
        ForeignKeyConstraint(['event_id'], ['events.id'], name='EVENT_HOCKEY_PK'),
        ForeignKeyConstraint(['match_id'], ['matches.id'], name='EVENT_MATCH_PK'),
        ForeignKeyConstraint(['player_id'], ['players.id'], name='EVENT_PLAYER_PK'),
        Index('EVENT_HOCKEY_PK_idx', 'event_id'),
        Index('EVENT_MATCH_PK_idx', 'match_id'),
        Index('EVENT_PLAYER_PK_idx', 'player_id'),
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'Table of events that happened during given hockey match'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Hockey game event ID')
    event_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Event ID (goal scored, assist, penalty, etc.)')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Match ID')
    team_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Team ID')
    player_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Player ID')
    period: Mapped[Optional[int]] = mapped_column(Integer, comment='Period when event happened, 1,2,3 - standard period, 4 = OT, 5 = SO')
    event_time: Mapped[Optional[str]] = mapped_column(String(9, 'utf8mb3_polish_ci'), comment='Time in period when event happened (in penalties, first round is noted as 00:00:01, second as 00:00:02, etc.)')
    pp_flag: Mapped[Optional[int]] = mapped_column(Integer, comment='(only for goals) - flag if happened in PP, 1 - yes, 0 - no')
    en_flag: Mapped[Optional[int]] = mapped_column(Integer, comment='(only for goals) - flag if goals was scored without goalie, 1 - yes, 0 - no')
    description: Mapped[Optional[str]] = mapped_column(String(100, 'utf8mb3_polish_ci'), comment='Event description')

    event: Mapped[Optional['Events']] = relationship('Events', back_populates='hockey_match_events')
    match: Mapped[Optional['Matches']] = relationship('Matches', back_populates='hockey_match_events')
    player: Mapped[Optional['Players']] = relationship('Players', back_populates='hockey_match_events')


class HockeyMatchPlayerStats(Base):
    __tablename__ = 'hockey_match_player_stats'
    __table_args__ = (
        ForeignKeyConstraint(['match_id'], ['matches.id'], name='P_S_MATCHES_PK'),
        ForeignKeyConstraint(['player_id'], ['players.id'], name='P_S_PLAYER_PK'),
        ForeignKeyConstraint(['team_id'], ['teams.id'], name='P_S_TEAM_PK'),
        Index('P_S_MATCHES_PK_idx', 'match_id'),
        Index('P_S_PLAYER_PK_idx', 'player_id'),
        Index('P_S_TEAM_PK_idx', 'team_id'),
        {'comment': 'Player stats (boxscore) in given match'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Boxscore ID')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Match ID')
    player_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Player ID')
    team_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Team ID')
    goals: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored by player')
    assists: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of assists (apples) aquired by players ')
    points: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of points (goals + assists)')
    plus_minus: Mapped[Optional[int]] = mapped_column(Integer, comment='A plus is given to a player who is on the ice when his team scores a goal, while a minus is given to players on the ice when opponents score.  The difference is the plus-minus rating')
    penalty_minutes: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of minutes spent in penalty box')
    sog: Mapped[Optional[int]] = mapped_column(Integer, comment='Shots on goal')
    blocked: Mapped[Optional[int]] = mapped_column(Integer, comment='Blocked shots')
    shots_acc: Mapped[Optional[float]] = mapped_column(Float, comment='Shots accuracy (shots on goal / all shots)')
    turnovers: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of times player lost the puck')
    steals: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of times player "stole" the puck from enemy team')
    faceoff: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of faceoffs player took part in')
    faceoff_won: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of faceoffs won')
    faceoff_acc: Mapped[Optional[float]] = mapped_column(Float, comment='accuracy of faceoffs')
    hits: Mapped[Optional[int]] = mapped_column(Integer, comment='Hits delivered by player')
    toi: Mapped[Optional[str]] = mapped_column(String(9, 'utf8mb3_polish_ci'), comment='Time on ice spent by player in given match')
    shots_against: Mapped[Optional[int]] = mapped_column(Integer, comment='[GOALIE ONLY] number of shots on goal a goalie faced in given match')
    shots_saved: Mapped[Optional[int]] = mapped_column(Integer, comment='[GOALIE ONLY] number of shots saved by goalie')
    saves_acc: Mapped[Optional[float]] = mapped_column(FLOAT, comment='[GOALIE ONLY] save accuracy')
    toi_str: Mapped[Optional[str]] = mapped_column(String(10, 'utf8mb3_polish_ci'))

    match: Mapped[Optional['Matches']] = relationship('Matches', back_populates='hockey_match_player_stats')
    player: Mapped[Optional['Players']] = relationship('Players', back_populates='hockey_match_player_stats')
    team: Mapped[Optional['Teams']] = relationship('Teams', back_populates='hockey_match_player_stats')


class HockeyMatchesAdd(Base):
    __tablename__ = 'hockey_matches_add'
    __table_args__ = (
        ForeignKeyConstraint(['match_id'], ['matches.id'], name='MATCH_HOCKEY_PK'),
        Index('MATCH_HOCKEY_PK_idx', 'match_id'),
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'Additional infromation unique to hockey game'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Additional stats ID')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Match ID')
    OT: Mapped[Optional[int]] = mapped_column(Integer, comment='Flag, if OT  happened 1 else 0')
    SO: Mapped[Optional[int]] = mapped_column(Integer, comment='Flag, if SO  happened 1 else 0')
    home_team_pp_goals: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored in PP (power play) by home team')
    away_team_pp_goals: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored in PP (power play) by away team')
    home_team_sh_goals: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored in SH (shorthand) by home team')
    away_team_sh_goals: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of goals scored in SH (shorthand) by away team')
    home_team_shots_acc: Mapped[Optional[float]] = mapped_column(Float, comment='Home team shots accuracy')
    away_team_shots_acc: Mapped[Optional[float]] = mapped_column(Float, comment='Away team shots accuracy')
    home_team_saves: Mapped[Optional[int]] = mapped_column(Integer, comment='Home team saved shots')
    away_team_saves: Mapped[Optional[int]] = mapped_column(Integer, comment='Away team saved shots')
    home_team_saves_acc: Mapped[Optional[float]] = mapped_column(Float, comment='Home team save accuracy')
    away_team_saves_acc: Mapped[Optional[float]] = mapped_column(Float, comment='Away team save accuracy')
    home_team_pp_acc: Mapped[Optional[float]] = mapped_column(Float, comment="Home team's power play accuracy (number of PP goals / number of PPs) ")
    away_team_pp_acc: Mapped[Optional[float]] = mapped_column(Float, comment="Away team's power play accuracy (number of PP goals / number of PPs) ")
    home_team_pk_acc: Mapped[Optional[float]] = mapped_column(Float, comment="Home team's penalty kill accuracy (number of goals lost in PK / number of PKs)")
    away_team_pk_acc: Mapped[Optional[float]] = mapped_column(Float, comment="Away team's penalty kill accuracy (number of goals lost in PK / number of PKs)")
    home_team_faceoffs: Mapped[Optional[int]] = mapped_column(Integer, comment='Faceoffs won by home team')
    away_team_faceoffs: Mapped[Optional[int]] = mapped_column(Integer, comment='Faceoffs won by away team')
    home_team_faceoffs_acc: Mapped[Optional[float]] = mapped_column(Float, comment="Home team's faceoff accuracy")
    away_team_faceoffs_acc: Mapped[Optional[float]] = mapped_column(Float, comment="Away team's faceoff accuracy")
    home_team_hits: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of hits made by home team')
    away_team_hits: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of hits made by away team')
    home_team_to: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of turnovers made by home team')
    away_team_to: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of turnovers made by home team')
    home_team_en: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of empty net goals (en - empty net) scored by home team')
    away_team_en: Mapped[Optional[int]] = mapped_column(Integer, comment='Number of empty net goals (en - empty net) scored by away team')
    OTwinner: Mapped[Optional[int]] = mapped_column(Integer, comment='0 - no OT happened \\n 1 - home team won after OT \\n 2 - away team won after OT \\n 3- no conclusion in OT')
    SOwinner: Mapped[Optional[int]] = mapped_column(Integer, comment='0- no SO happened \\n 1 - home team won after SO \\n 2 - away team won after SO')

    match: Mapped[Optional['Matches']] = relationship('Matches', back_populates='hockey_matches_add')


class Odds(Base):
    __tablename__ = 'odds'
    __table_args__ = (
        ForeignKeyConstraint(['bookmaker'], ['bookmakers.id'], name='BOOKMAKER_ODDS'),
        ForeignKeyConstraint(['event'], ['events.id'], name='EVENT_ODDS'),
        ForeignKeyConstraint(['match_id'], ['matches.id'], name='MATCH_ODDS'),
        Index('BOOKMAKER_ODDS_idx', 'bookmaker'),
        Index('EVENT_ODDS_idx', 'event'),
        Index('MATCH_ODDS_idx', 'match_id'),
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'Odds for given event, match and bookmaker'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Odds ID')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Match ID')
    bookmaker: Mapped[Optional[int]] = mapped_column(Integer, comment='Bookmaker ID')
    event: Mapped[Optional[int]] = mapped_column(Integer, comment='Events ID')
    odds: Mapped[Optional[float]] = mapped_column(Float, comment='odds for given event')

    bookmakers: Mapped[Optional['Bookmakers']] = relationship('Bookmakers', back_populates='odds')
    events: Mapped[Optional['Events']] = relationship('Events', back_populates='odds')
    match: Mapped[Optional['Matches']] = relationship('Matches', back_populates='odds')


class Predictions(Base):
    __tablename__ = 'predictions'
    __table_args__ = (
        ForeignKeyConstraint(['event_id'], ['events.id'], name='PRED_EVENTS'),
        ForeignKeyConstraint(['match_id'], ['matches.id'], name='PRED_MATCHES'),
        Index('PRED_EVENTS_idx', 'event_id'),
        Index('PRED_MATCHES_idx', 'match_id'),
        Index('id_UNIQUE', 'id', unique=True),
        {'comment': 'Generated predictions by model'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='Prediction ID')
    match_id: Mapped[Optional[int]] = mapped_column(Integer, comment='match ID')
    event_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Event iD')
    value: Mapped[Optional[float]] = mapped_column(Float, comment='Probability of event to happen (shown as percentage, 0 <= value <= 100)')

    event: Mapped[Optional['Events']] = relationship('Events', back_populates='predictions')
    match: Mapped[Optional['Matches']] = relationship('Matches', back_populates='predictions')


class EventsParlays(Base):
    __tablename__ = 'events_parlays'
    __table_args__ = (
        ForeignKeyConstraint(['bet_id'], ['bets.id'], name='EVENTS_P_BETS_FK'),
        ForeignKeyConstraint(['parlay_id'], ['gambler_parlays.id'], name='EVENTS_PARLAYS_FK'),
        Index('EVENTS_PARLAYS_FK_idx', 'parlay_id'),
        Index('EVENTS_P_BETS_FK_idx', 'bet_id'),
        {'comment': 'Parlay details'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Parlay's event id")
    parlay_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Parlay id')
    bet_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Bet id')

    bet: Mapped[Optional['Bets']] = relationship('Bets', back_populates='events_parlays')
    parlay: Mapped[Optional['GamblerParlays']] = relationship('GamblerParlays', back_populates='events_parlays')
