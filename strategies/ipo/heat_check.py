import sys

import numpy as np
import pandas as pd

sys.path.append('../..')
from jockbot.strategy_base import StrategyConfig, Strategy
from jockbot.bot import JockBotException
from jockbot.signals import Signal
from typing import Dict
from enum import Enum

class HeatCheckStrategies(Enum):
    """
    Enum with each possible strategy for heat_check

    :cvar short_hot: strategy that shorts the players who have regularly been outperforming their projections, looking for mean reversion
    :cvar short_cold: strategy that shorts the players who have regularly been underperforming projections
    :cvar long_hot: long players who are outplaying their projection
    :cvar long_cold: long players who have been underperforming, looking for a mean reversion
    :cvar short_hot_long_cold: short players who have outperformed projection, and long players who are underperforming
    :cvar long_hot_short_cold: long players who have outperformed projection, and short players who are underperforming
    :cvar long_breakout: long players who have been performing closely to their projection
    :cvar short_breakout: short players who have been performing closely to their projection
    """
    short_hot = 1
    short_cold = 2
    long_hot = 3
    long_cold = 4
    short_hot_long_cold = 5
    long_hot_short_cold = 6
    long_breakout = 7
    short_breakout = 8
    """
    Thoughts:
        We can short or long hot players
        We can short or long cold players
        We can do both
        We can trade players who are performing very closely to their projections assuming they are ready for a breakout?

    """


class HeatCheckConfig(StrategyConfig):
    """
    :cvar order_size: the amount of shares to buy for each order. Default: 10
    :type order_size: int, optional
    :cvar dollar_size: dollar amount to spend on each player (i.e. buy 10 shares at $5 for a total of $50, and 20 shares @ 2.5)
    :type dollar_size: int, optional
    :cvar strategy: which HeatCheck strategy to use, see :class:`HeatCheckStrategies`
    :cvar pct_field: how many of the players in the field we should buy, as a float 0 < x < 1. If 100 players available
                    and pct_field = 0.25, it will choose the optimal 25 players based on your strategy
    :type pct_field: float, required
    :cvar window: the lookback window for the rolling average calc, default: 10
    :type window: float, required
    :cvar risk: buy at est price * (1 + risk), higher risk = higher price willing to pay
    :type risk: float, required
    """
    order_size: int = 10
    dollar_size: int | None = None
    strategy: HeatCheckStrategies | int = 2
    pct_field: float = 0.25  # BUY THIS PCT OF THE FIELD
    window: int = 10
    risk = 0  # buy at est price * (1 + risk), higher risk = higher price willing to pay


class HeatCheck(Strategy):
    def __init__(self, config: StrategyConfig | HeatCheckConfig):
        super().__init__(config)
        self.client = None
        self.event_id = None
        self.config = config
        self.window = config.window
        self.order_size = config.order_size
        self.dollar_size = config.dollar_size
        self.risk = config.risk
        self.strategy_id = config.strategy
        self.pct_field = config.pct_field
        if self.pct_field > 1:
            raise JockBotException('1', 'pct_field should be less than 1.', '')
        self.strategy = self.get_strategy()
        self.event = None
        self.tradeables: Dict[Dict[str, float]] = {}
        self.jb_p_dict = None
        self.ent_id_to_tdbl_id_dict = {}
        self.df: pd.DataFrame | None = None
        self.n_to_buy: int | None = None
        self.orders: list = []

    def on_start(self, jockbot):
        self.client = jockbot.fetch_client()
        self.jb_p_dict = jockbot.player_dict
        self.tradeables = self.build_gamelog_dict(jockbot.strategy.config.event_id)
        self.n_to_buy = round(len(self.tradeables) * self.pct_field)
        self.df = self.build_df()
        self.orders = self.strategy()

    def ipo_trade(self, jockbot) -> Signal:
        return Signal(self.orders, [])

    def calc_order_size(self, price):
        if self.dollar_size is not None:
            return self.dollar_size // price
        else:
            return self.order_size

    def build_gamelog_dict(self, event_id):
        dict_gamelogs = {}
        self.event = self.client.get_event(event_id)
        tradeables = self.event.tradeables
        for player in tradeables:
            dict_player = self.get_player_fpts(self.client.get_game_logs(entity_id=player.entity_id))
            dict_player['tradeable_id'] = player.tradeable_id
            dict_player['tradeable'] = player
            dict_player['est_price'] = player.estimated
            dict_player['proj'] = player.fpts_proj_pregame
            dict_gamelogs[player.entity_id] = dict_player
        return dict_gamelogs

    def get_player_fpts(self, player_gamelogs):
        logs = {
            'projected': [],
            'actual': []
        }
        for log in reversed(player_gamelogs):
            print(log)
            if log.game.status == 'final':
                proj_stats = self.calc_fpts(log.projected_stats)
                if proj_stats:
                    logs['projected'].append(proj_stats)
                    logs['actual'].append(self.calc_fpts(log.actual_stats) or 0)
        logs['projected'] = np.array(logs['projected'])
        logs['actual'] = np.array(logs['actual'])
        return logs

    @staticmethod
    def calc_fpts(stats):
        if len(stats) > 1:
            if stats['league'] == 'nba':
                return round(
                    2 * (stats['blocks'] + stats['steals']) + stats['points'] + 1.5 * stats['assists'] + 1.25 * stats[
                        'rebounds'] + (stats['points'] // 10) * 1.5 - 0.5 * (
                                stats['field_goals_att'] + stats['turnovers'] - stats['field_goals_made']), 2)
            elif stats['league'] == 'nfl':
                return round(stats['passing_yards'] * 0.04 + (stats['passing_yards'] // 100) * 1.5 + 4 * stats[
                    'passing_touchdowns'] - 3 * (stats['passing_interceptions'] + stats['lost_fumbles']) + 0.1 * (
                                         stats['rushing_yards'] + stats['receiving_yards']) + 6 * (
                                         stats['rushing_touchdowns'] + stats['receiving_touchdowns'] + stats[
                                            'kick_return_touchdowns'] + stats['punt_return_touchdowns'] + stats[
                                             'interception_return_touchdowns'] + stats['misc_touchdowns']) + 2 * (
                             stats['two_pt_conversions']) + stats['receiving_receptions'] + (
                                         stats['receiving_yards'] // 100) * 3 + (stats['rushing_yards'] // 100) * 3, 2)
            elif stats['league'] == 'mlb':
                raise JockBotException('000', 'League not available', f'{stats["league"]} is not available for this strategy')
            else:
                raise JockBotException('000', 'League not available', f'{stats["league"]} is not available for this strategy')
        else:
            return

    def get_strategy(self):
        strategy_dict = {
            1: self.short_hot,
            2: self.short_cold,
            3: self.long_hot,
            4: self.long_cold,
            5: self.short_hot_long_cold,
            6: self.long_hot_short_cold,
            7: self.long_breakout,
            8: self.short_breakout
        }
        return strategy_dict[self.strategy_id]

    def build_order(self, tradeable_id, side):
        return {
            'tradeable_id': tradeable_id,
            'price': self.get_price(tradeable_id, side),
            'quantity': self.order_size,
            'side': side
        }

    def get_price(self, tradeable_id, side):
        est = self.jb_p_dict[tradeable_id]['estimated'][-1]
        return est * (1 + self.risk) if side == 'buy' else est * (1 - self.risk)

    def long_hot(self):
        self.df = self.df.sort_values('rolling_dev', ascending=False)
        buys = self.df.tradeable_id.values[:self.n_to_buy]
        orders = [self.build_order(i, 'buy') for i in buys]
        return orders

    def short_hot(self):
        self.df = self.df.sort_values('rolling_dev', ascending=True)
        sells = self.df.tradeable_id.values[:self.n_to_buy]
        orders = [self.build_order(i, 'sell') for i in sells]
        return orders

    def long_cold(self):
        self.df = self.df.sort_values('rolling_dev', ascending=True)
        buys = self.df.tradeable_id.values[:self.n_to_buy]
        orders = [self.build_order(i, 'buys') for i in buys]
        return orders

    def short_cold(self):
        self.df = self.df.sort_values('rolling_dev', ascending=False)
        sells = self.df.tradeable_id.values[:self.n_to_buy]
        orders = [self.build_order(i, 'sell') for i in sells]
        return orders

    def short_hot_long_cold(self):
        self.df = self.df.sort_values('rolling_dev', ascending=False)
        buys_per_side = self.n_to_buy // 2
        buys = self.df.tradeable_id.values[-buys_per_side:]
        sells = self.df.tradeable_id.values[:buys_per_side]
        orders = [self.build_order(i, 'sell') for i in sells]
        orders.extend([self.build_order(i, 'buy') for i in buys])
        return orders

    def long_hot_short_cold(self):
        self.df = self.df.sort_values('rolling_dev', ascending=False)
        buys_per_side = self.n_to_buy // 2
        sells = self.df.tradeable_id.values[-buys_per_side:]
        buys = self.df.tradeable_id.values[:buys_per_side]
        orders = [self.build_order(i, 'sell') for i in sells]
        orders.extend([self.build_order(i, 'buy') for i in buys])
        return orders

    def long_breakout(self):
        self.df = self.df.sort_values('rolling_dev', ascending=False)
        midpoint = len(self.df // 2)
        buys = self.df.tradeable_id.values[midpoint - self.n_to_buy // 2: midpoint + self.n_to_buy // 2]
        orders = [self.build_order(i, 'buy') for i in buys]
        return orders

    def short_breakout(self):
        self.df = self.df.sort_values('rolling_dev', ascending=False)
        midpoint = len(self.df // 2)
        sells = self.df.tradeable_id.values[midpoint - self.n_to_buy // 2: midpoint + self.n_to_buy // 2]
        orders = [self.build_order(i, 'sell') for i in sells]
        return orders

    def build_df(self):
        df_skel = []
        for tdbl, player in self.tradeables.items():
            print(player)
            df_skel.append(self.row_generator(player))
        return pd.DataFrame(df_skel)

    def row_generator(self, player_dict):
        print(player_dict)
        proj = player_dict['proj']
        season_avg = np.mean(player_dict['actual'])
        mean_act = np.mean(player_dict['actual'][-self.window:])
        return {
            'tradeable_id': player_dict['tradeable_id'],
            'season_avg': season_avg,
            'season_var': np.var(player_dict['actual'], ddof=1),
            'rolling_mean': mean_act,
            'rolling_dev': (proj - mean_act)/proj,
            'proj': proj,
        }




