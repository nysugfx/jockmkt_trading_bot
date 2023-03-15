import logging
import time
import sys
from typing import Union
from jockmkt_sdk.client import Client

sys.path.append('../..')
from jockbot.strategy_base import StrategyConfig, Strategy
from jockmkt_sdk.objects import Order, Tradeable
import numpy as np
from jockbot.signals import Signal
from typing import Type
from jockbot.bot import JockBot


class HBConfig(StrategyConfig):
    """
    class variables:
        - order_size: Optional, default: 1, int[1, inf].
                      the number of shares per order
    """

    order_size = 1  # Number of shares you want to buy


class HBStrategy(Strategy):
    def __init__(self, config: StrategyConfig | HBConfig):
        super().__init__(config)
        self.league = None
        self.config: StrategyConfig = config
        self.order_size = config.order_size
        self.event = None
        self.players = {}
        self.recents = {}

    def parse_player_dict(self, jockbot_player_dict):
        """
        Build a dictionary stored within our class with information like:
        Best bid
        difference between current estimate and previous estimated price
        ipo price
        difference between the estimated price and ipo (which we use to figure out whether we should short)

        :param jockbot_player_dict: the jockbot dictionary for the player we've received an update for
        :return:
        """
        for tradeable_id, player in jockbot_player_dict.items():
            p_dict = {
                'tradeable_id': tradeable_id,
                'scored_fpts': player['fpts_scored'][-1],
                'old_fpts': player['fpts_scored'][-2],
                'bid': player['bid'][-1] or 1,
                'ask': player['ask'][-1] or 25,
                'est': player['estimated']
            }

            self.recents[tradeable_id] = player['ask'][-1]

            self.players[tradeable_id] = p_dict

    def update_player_dict(self, tradeable_id: str, player_dict: dict[str, Union[Tradeable, np.ndarray]]):
        """
        Update our stored player dictionary with new information

        :param tradeable_id: tradeable id
        :param player_dict: jockbot player dictionary
        :param amount_completed: percent of the game completed, may be useful for other strategies
        :return: Signal
        """
        est = player_dict['estimated'][-1]
        bid = player_dict['bid'][-1]
        ask = player_dict['ask'][-1]
        fpts = player_dict['fpts_scored']
        old_fpts = fpts[-2]
        new_fpts = fpts[-1]
        if self.league != 'simulated_horse_racing':
            status = player_dict['tradeable'].entity.injury_status
        else:
            status = None
        p_dict = {
            'tradeable_id': tradeable_id,
            'scored_fpts': new_fpts,
            'old_fpts': old_fpts,
            'bid': bid or 1,
            'ask': ask or 25,
            'est': est
        }
        signal = self.signal_generator(bid, ask, est, tradeable_id, new_fpts, status)
        self.players[tradeable_id] = p_dict
        return signal

    def signal_generator(self, bid, ask, est, tradeable_id, fpts, status=None):
        """
        Our signal:
            if the est price has gone up x% or down x% and the bid or ask has not moved, buy that shit bitch.
        """
        # if self.league == 'simulated_horse_racing':
        #     mult = 0.8
        # else:
        #     mult = 1.03
        if ask * .9 < est and status is None and fpts > 0:
            # if self.recents[tradeable_id] != ask:
                order = [
                    {'tradeable_id': tradeable_id,
                     'price': ask + 0.02,
                     'quantity': self.order_size,
                     'side': 'buy'}
                     # 'price': bid - 0.02,
                     # 'quantity': self.order_size,
                     # 'side': 'sell'}
                ]
                self.recents[tradeable_id] = ask
                return Signal(order, [])
        # elif bid * .90 > est and bid > 5 and status is None and fpts > 0:
        #     if self.recents[tradeable_id] != ask:
        #         order = [
        #             {'tradeable_id': tradeable_id,
        #              'price': ask+0.02,
        #              'quantity': self.order_size,
        #              'side': 'sell'}
        #         ]
        #         self.recents[tradeable_id] = ask
        #         return Signal(order, [])

    # def pass_recent_signals(self, player_dict):
    #     """
    #     We'll need to filter the signals. I think the bot will want to place orders over and over again. we will do it based off of fpts_scored
    #     :param player_dict: OUR STRATEGY SPECIFIC PLAYER DICT
    #     :return: False if we should not pass this signal
    #     """
    #     last_sig = self.recent_signals.get(player_dict['tradeable_id'], 0)
    #     current_sig = self.players[player_dict['tradeable_id']]['fpts_scored']
    #     if self.double_down:
    #         if current_sig > last_sig:
    #             return False
    #     else:
    #         if not last_sig and player_dict['tradeable_id'] not in self.open_positions:
    #             return False
    #     return True

    def on_start(self, jockbot):
        self.parse_player_dict(jockbot.player_dict)
        self.league = jockbot.event_info.league

    def on_data(self, tradeable_id: str, jockbot) -> Signal:
        """
        NOTE: Need to make sure that we are not trading on the same data more than once. If we get multiple updates for the same player within a few seconds, we can expect to get the same signal over and over again.
        :param tradeable_id:
        :param jockbot:
        :param event_live:
        :return:
        """
        event_live = jockbot.event_live
        if event_live:
            single_player_dict = jockbot.player_dict[tradeable_id]
            signal = self.update_player_dict(tradeable_id, single_player_dict)

            return signal
        else:
            logging.debug('Event not yet live.')

    def on_order(self, order: Order, my_orders: dict[str, Order]) -> Signal:
        if order.status == 'accepted':
            return Signal([], [order.order_id])

    def on_stop(self, jockbot: JockBot):
        client: Client = jockbot.fetch_client()
        open_orders = client.get_orders(active=True, event_id=jockbot.event_id)
        if len(open_orders) == 100:
            for i in range(1, 5):
                open_orders.extend(client.get_orders(start=i, active=True, event_id=jockbot.event_id))
        return Signal(orders=[], cancels=[order.order_id for order in open_orders])
