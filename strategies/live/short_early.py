import logging
import sys
from typing import Union
from jockmkt_sdk.client import Client
sys.path.append('../..')
from jockbot.strategy_base import StrategyConfig, Strategy
from jockmkt_sdk.objects import Tradeable
import numpy as np
from jockbot.signals import Signal
from jockbot.bot import JockBot

class ShortEarlyConfig(StrategyConfig):
    """
    Required config settings for :class:`ShortEarly`

    :cvar order_size: the number of shares per order
    :type order_size: Optional, default: 1, int[1, inf].
    :cvar dollar_size: if not None, the $ amount worth of shares the user wishes to buy. e.g.: if price = 5 and dollar_size = 50, the bot will place an order for 10 shares.
    :type dollar_size: optional, default: None, float(0, inf]
    :cvar price_risk: A risk parameter. Lower number = lower risk. e.g.: If you choose -1 price risk, the bot will short at 1.1x the current estimated price. (lower risk). If you choose 0.5, the bot will short the player at 0.95% of its estimated price (higher risk)
    :type price_risk: Required, default: 0.5, float[-1, 1]
    :cvar double_down: If you want the bot to short the player more than once. It will only short again if the player scores more fantasy points.
    :type double_down: Optional, default: False
    :cvar max_amount_completed: How much (%) of an event must be completed before the bot stops shorting players. This strategy is designed to short players who have scored a lot of fantasy points early in an event, and so it is only going to be profitable if this number is lower.
    :type max_amount_completed: Required, default: 0.35, float(0, 1]
    :cvar min_pct_gain: The strategy bids for players whose current estimated price is a certain percentage above their IPO. This parameter is the % the estimated price is above IPO that the player must be before the bot will consider placing an order.
    :type min_pct_gain: Required, default: 0.75, float(0, inf)
    :cvar min_ipo_price: Ignore players who have IPO'd for below a certain price. The higher this number, the fewer players the strategy will buy. This weeds out players who were cheap and way outperform their projections.
    :type min_ipo_price: Required, default: 5, float(1, 25)
    """

    order_size = 1  # Number of shares you want to buy
    dollar_size = None
    price_risk = 0.5  # Risk parameter (between -1 and 1)
    # If you choose -1 price risk, you will short sell place orders at 110% of the estimated price
    # If you choose 0.5, you will short sell down to 95% of the estimated price
    double_down = False  # If True, the strategy will continue to short a player if they score more fantasy points
    # if False, it will short the player once and hold the position.
    max_amount_completed = 0.09  # Maximum amount of the entire event completed, ideally < 0.25
    min_pct_gain = 25  # How high above a player's IPO price their estimated price must be in order to short them
    min_ipo_price = 25  # Pool of potential shorts limited to players who IPO above this parameter
    # if price_risk > 1 or price_risk < -1:
        # raise ValueError


class ShortEarly(Strategy):
    """
    How it works:

    Once an event has started, we are looking for players who far outperform their projections early on. These players are
    likely to fall back down to earth at some point before the event ends.
    For example, in an NFL Sunday slate, if Saquon Barkley gets a 50 yard touchdown in the first 2 minutes of his 1pm game,
    he will be projected for many more points than anyone else. Because of this, his price will be very inflated.
    We should short him! This strategy is also applicable to NBA, and other sports, where a player scores a large chunk of
    points early on in the event.

    """
    def __init__(self, config: StrategyConfig | ShortEarlyConfig):
        super().__init__(config)
        self.config: StrategyConfig = config
        self.players = {}
        self.games = {}
        self.amount_completed = 0
        self.max_amount_completed = config.max_amount_completed
        self.min_pct_gain = config.min_pct_gain
        # self.order_size_min = self.config.order_size_min
        # self.order_size_max = self.config.order_size_max
        self.order_size = config.order_size
        self.dollar_size = config.dollar_size
        self.price_risk = config.price_risk
        # self.size_risk = self.config.size_risk
        self.double_down = config.double_down
        self.min_ipo_price = config.min_ipo_price
        self.recent_signals = {}
        self.open_positions = {}
        self.open_orders = {}

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
                'bid': player['bid'][-1] or 1,
                'diff_est': player['estimated'][-1] - player['estimated'][-2],
                'ipo': player['tradeable'].ipo,
                'diff_ipo': player['estimated'][-1] - player['tradeable'].ipo
            }

            self.players[tradeable_id] = p_dict

    def update_player_dict(self, tradeable_id: str, player_dict: dict[str, Union[Tradeable, np.ndarray]],
                           amount_completed):
        """
        Update our stored player dictionary with new information

        :param tradeable_id: tradeable id
        :param player_dict: jockbot player dictionary
        :param amount_completed: percent of the game completed, may be useful for other strategies
        :return: Signal
        """
        new_player_dict = {
            'tradeable_id': tradeable_id,
            'bid': player_dict['bid'][-1],
            'fpts_scored': player_dict['fpts_scored'][-1],
            'est': player_dict['estimated'][-1],
            'diff_est': player_dict['estimated'][-1] - player_dict['estimated'][-2],
            'ipo': player_dict['tradeable'].ipo,
            'diff_ipo': player_dict['estimated'][-1] - player_dict['tradeable'].ipo,
            'game_completed': amount_completed
        }
        self.players[tradeable_id] = new_player_dict
        return self.signal_generator(new_player_dict)

    def signal_generator(self, player_dict):
        """
        if the difference between the ipo price and estimated is greater than 100%, and the ipo price was greater than
        5, and the event is less than 20% complete, place an order.

        In the future:
            we can change the difference based on ipo price

        our price and size are calculated using risk params

        :param player_dict: OUR STRATEGY PLAYER DICT
        :return:
        """
        if player_dict['diff_ipo'] / player_dict['ipo'] > self.min_pct_gain and player_dict['ipo'] > self.min_ipo_price \
                and self.amount_completed <= self.max_amount_completed:
            if not self.pass_recent_signals(player_dict):
                self.recent_signals[player_dict['tradeable_id']] = player_dict['fpts_scored']
                price = self.get_price(player_dict)
                orders = [
                    {'tradeable_id': player_dict['tradeable_id'],
                     'price': price,
                     'quantity': self.get_size(price),
                     'side': 'sell'}
                ]
                return Signal(orders, [])

    def pass_recent_signals(self, player_dict):
        """
        We'll need to filter the signals. I think the bot will want to place orders over and over again. we will do it based off of fpts_scored
        :param player_dict: OUR STRATEGY SPECIFIC PLAYER DICT
        :return: False if we should not pass this signal
        """
        last_sig = self.recent_signals.get(player_dict['tradeable_id'], 0)
        current_sig = self.players[player_dict['tradeable_id']]['fpts_scored']
        if self.double_down:
            if current_sig > last_sig:
                return False
        else:
            if not last_sig and player_dict['tradeable_id'] not in self.open_positions:
                return False
        return True

    def get_size(self, price):
        """
        :return:
        """
        # return round((self.order_size_max - self.order_size_min) * self.size_risk + self.order_size_min)
        if self.dollar_size is not None:
            return self.dollar_size // price
        return self.order_size

    def get_price(self, player_dict):
        """
        :param player_dict: OUR STRATEGY PLAYER DICT
        :return:
        """
        price = player_dict['est']  # Get estimated price
        risk = self.price_risk / 10  # Divide risk by 10
        price = price * (1 - risk)  # Calculate price, which is price multiplied by 1 - risk
        return price

    def on_start(self, jockbot):
        self.parse_player_dict(jockbot.player_dict)
        self.parse_open_positions(jockbot.fetch_holdings())
        self.parse_open_orders(jockbot.fetch_orders())

    def on_data(self, tradeable_id: str, jockbot) -> Signal:
        """
        :param tradeable_id:
        :param jockbot:
        :param event_live:
        :return:
        """
        self.amount_completed = jockbot.event_info.amt_completed
        event_live = jockbot.event_live
        if event_live:
            single_player_dict = jockbot.player_dict[tradeable_id]
            amount_completed = jockbot.games[single_player_dict['tradeable'].game_id].amount_completed or 0
            signal = self.update_player_dict(tradeable_id, single_player_dict, amount_completed)
            # signal = self.signal_generator(single_player_dict)

            return signal
        else:
            logging.debug('Event not yet live.')

    def parse_open_positions(self, holdings):
        self.open_positions = holdings

    def parse_open_orders(self, orders):
        self.open_orders = orders

    def on_stop(self, jockbot: JockBot):
        client: Client = jockbot.fetch_client()
        open_orders = client.get_orders(active=True, event_id=jockbot.strategy.config.event_id)
        if len(open_orders) == 100:
            for i in range(1, 5):
                open_orders.extend(client.get_orders(start=i, active=True, event_id=jockbot.strategy.config.event_id))
        return Signal(orders=[], cancels=[order.order_id for order in open_orders])
