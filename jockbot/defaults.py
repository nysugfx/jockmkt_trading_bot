from enum import Enum, unique


side_dict = {
            'buy': 'ask',
            'sell': 'bid'
            }

@unique
class INSTRUMENT(Enum):
    FPTS_PROJ = 'fpts_projected'
    FPTS_SCORED = 'fpts_scored'
    ESTIMATED = 'estimated'
    BID = 'bid'
    ASK = 'ask'
    LAST = 'last'
    HIGH = 'high'
    LOW = 'low'

def stats_cases(league):
    print(league)
    league_case_dict = {
        'mlb': STATS.MLB.value,
        'nhl': STATS.NHL.value,
        'nfl': STATS.NFL.value,
        'nba': STATS.NBA.value,
        'nascar': STATS.NASCAR.value,
        'pga': STATS.PGA.value,
        'simulated_horse_racing': {}
    }
    return league_case_dict[league]


class STATS(Enum):
    MLB = ['rbi', 'hits', 'runs', 'walks', 'at_bats', 'doubles', 'singles', 'triples', 'home_runs', 'total_bases', 'games_played', 'hit_by_pitch', 'stolen_bases', 'games_started', 'sacrifice_flys', 'batting_average', 'reached_on_error', 'total_strikeouts', 'intentional_walks', 'plate_appearances', 'on_base_percentage', 'slugging_percentage', 'grounded_into_double_play', 'on_base_plus_slugging_percentage']
    NHL = ['hits', 'goals', 'saves', 'points', 'assists', 'giveaways', 'takeaways', 'plus_minus', 'time_on_ice', 'faceoff_wins', 'blocked_shots', 'goals_against', 'overtime_loss', 'shots_against', 'shots_on_goal', 'overtime_goals', 'shootout_goals', 'penalty_minutes', 'powerplay_goals', 'powerplay_saves', 'save_percentage', 'overtime_assists', 'game_winning_goal', 'powerplay_assists', 'shorthanded_goals', 'shorthanded_saves', 'shorthanded_assist', 'powerplay_goals_against', 'shorthanded_goals_against']
    NBA = ['blocks', 'points', 'steals', 'assists', 'minutes', 'rebounds', 'turnovers', 'field_goals_att', 'free_throws_att', 'field_goals_made', 'free_throws_made', 'three_points_att', 'three_points_made', 'defensive_rebounds', 'offensive_rebounds']
    NFL = ['targets', 'longest_rush', 'lost_fumbles', 'passing_yards', 'rushing_yards', 'misc_touchdowns', 'receiving_yards', 'rushing_attempts', 'longest_reception', 'yards_after_catch', 'passing_touchdowns', 'rushing_touchdowns', 'two_pt_conversions', 'receiving_receptions', 'receiving_touchdowns', 'passing_interceptions', 'kick_return_touchdowns', 'punt_return_touchdowns']
    NASCAR = ['points', 'best_lap', 'inactive', 'laps_led', 'position', 'avg_speed', 'pit_stops', 'times_led', 'avg_position', 'bonus_points', 'elapsed_time', 'fastest_laps', 'best_lap_time', 'last_lap_time', 'best_lap_speed', 'laps_completed', 'last_lap_speed', 'penalty_points', 'pit_stop_count', 'start_position', 'actual_position', 'avg_restart_speed']
    PGA = {}

