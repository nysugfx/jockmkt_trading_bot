import time
import sys

sys.path.append('../..')
from jockmkt_sdk.client import Client
from jockbot.strategy_base import StrategyConfig, Strategy
from jockmkt_sdk.objects import Order, Tradeable
import numpy as np
from jockbot.signals import Signal
from typing import Union, Type, Dict



class DumpLateConfig(StrategyConfig):
    """
    Config additions required for the DumpLate strategy.

    :cvar required_profit_margin: Require an estimated profit margin as a percentage before making a trade. Does not guarantee profit. Higher number will place less orders and take less risk.
    :type required_profit_margin: float, required
    :cvar order_size: Number of shares to buy in each order (min 1). I recommend playing around with this based on market liquidity.
    :type order_size: int, optional
    :cvar dollar_size: required if no order_size, the dollar amount you would like to spend on an order (rather than share amount)
                       e.g.: if price = 5 and dollar_size = 50, the bot will place an order for 10 shares. Default None
    :type dollar_size: float, optional
    :cvar cancel_orders: Fill or kill orders. Defaults to False.
    :type cancel_orders: bool, optional
    """
    required_profit_margin: float = .05
    order_size: int = 5
    dollar_size: float | None = None
    cancel_orders: bool = False


class DumpLate(Strategy):
    """
    How it works:

        if a player's game is completed, we know that they will not score any more fantasy points. Their price
        cannot go up unless other players score below their projection. If we have an opportunity to buy a player or sell a player at a profit
        compared to their projected payout, we do so.
    """

    def __init__(self, config: DumpLateConfig | StrategyConfig):
        super().__init__(config)
        self.fees: float = 0.02
        self.config: DumpLateConfig = config
        self.players: Dict[str, Dict[str, float]] = {}
        self.games: Dict[str, float] = {}
        self.amount_completed: float = 0
        self.risk: float = self.config.required_profit_margin
        self.order_size: int = self.config.order_size
        self.dollar_size: float = self.config.dollar_size
        self.cancel_order: bool = self.config.cancel_orders
        self.client: Union[Client, None] = None
        self.event_id: Union[str, None] = None
        self.payout_key: Dict[int, float] = {}
        # self.recent_signals = {}
        # self.open_positions = {}

    def parse_player_dict(self, jockbot_player_dict: Dict[str, Dict[str, Union[Tradeable, float, int, str]]]):
        """
        Build a dictionary stored within our class with information like:
        Best bid
        difference between current estimate and previous estimated price
        ipo price
        difference between the estimated price and ipo (which we use to figure out whether we should short)

        :param jockbot_player_dict: the jockbot dictionary for the player we've received an update for
        :return:
        """
        print('parsing player_dict')

        for tradeable_id, player in jockbot_player_dict.items():
            p_dict = {
                'tradeable_id': tradeable_id,
                'bid': player['bid'][-1] or 1,
                'ask': player['ask'][-1] or 25,
                'projected_payout': self.payout_key[int(player['tradeable'].rank_proj_live)],
                'game_completed': 0
            }
            self.players[tradeable_id] = p_dict
        print('done parsing player dict')

    def update_player_dict(self, tradeable_id: str,
                           player_dict: Dict[str, Union[Tradeable, np.ndarray, int, float, str]],
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
            'ask': player_dict['ask'][-1],
            'projected_payout': self.payout_key[int(player_dict['tradeable'].rank_proj_live)],
            'game_completed': amount_completed
        }
        self.players[tradeable_id] = new_player_dict
        return self.signal_generator(new_player_dict)

    def on_start(self, jockbot):
        """
        Build strategy-specific player dictionary
        Build the payout key: dict[str, float]
        :param jockbot: An instance of the Jockbot. We cannot import this name because that would make the
        import circular. See jockbot docs_sdk for available ivars.
        :return:
        """
        self.payout_key = dict((i['position'], i['amount']) for i in jockbot.event_info.payouts)
        self.parse_player_dict(jockbot.player_dict)
        self.client = jockbot.client
        self.event_id = jockbot.strategy.config.event_id

    def on_data(self, tradeable_id: str, jockbot) -> Signal:
        """
        :param tradeable_id:
        :param jockbot:
        :param event_live:
        :return:
        """
        self.amount_completed = jockbot.event_info.amt_completed

        if jockbot.event_live:
            single_player_dict = jockbot.player_dict[tradeable_id]
            amount_completed = jockbot.games[single_player_dict['tradeable'].game_id].amount_completed or 0
            signal = self.update_player_dict(tradeable_id, single_player_dict, amount_completed)

            return signal
        else:
            print('event not yet live')

    def on_order(self, order: Order, orders: Dict[str, Order]):
        """
        If the user wishes NOT to leave orders on the book, we'll cancel all of their orders
        :param order:
        :param orders:
        :return: Signal(orders_to_cancel)
        """
        if self.cancel_order:
            time.sleep(0.5)  # if we don't sleep, sometimes we get an error when trying to cancel orders.
            open_orders = self.client.get_orders(event_id=self.event_id, active=True)
            if open_orders:
                return Signal(orders=[], cancels=[order.order_id for order in open_orders])

    def get_buy_sig(self, projected_payout: float, ask: float):
        expected_buy_profit = projected_payout - (ask * (1 + self.fees))  # get profit less fees
        expected_buy_roi = expected_buy_profit / (ask * (1 + self.fees))  # get % profit
        if expected_buy_roi >= self.risk:  # compare % profit with required minimum profit
            return True

    def get_sell_sig(self, projected_payout: float, bid: float):
        expected_sell_profit = - projected_payout + bid - (bid * self.fees)  # get profit minus fees
        expected_sell_roi = expected_sell_profit / (bid * (1 + self.fees))  # get % profit
        if expected_sell_roi >= self.risk:  # compare % profit with required minimum profit
            return True

    def get_size(self, price):
        if self.dollar_size:
            return self.dollar_size // price
        else:
            return self.order_size

    def signal_generator(self, player_dict: Dict[str, Union[float, int, str]]):
        """
        if the game is complete:
        if we can expect to receive a certain percentage profit, we will either buy or sell
        :param player_dict:
        :return:
        """
        if player_dict['game_completed'] == 1:
            projected_payout = player_dict['projected_payout']  # Get the player's projected payout
            ask = player_dict['ask']  # get the player's ask price
            if self.get_buy_sig(projected_payout, ask):  # see if we have a buy signal (our expected profit from buying
                # is greater than or equal to our required minimum profit
                highest_potential_bid = projected_payout / (
                        1 + self.risk)  # the absolute highest price we are willing to pay based on required profit
                size = self.get_size(highest_potential_bid)
                signal = {
                    'tradeable_id': player_dict['tradeable_id'],
                    'price': highest_potential_bid,
                    # place an order at the highest possible bid to get as many shares as possible
                    'quantity': size,
                    'side': 'buy'
                }
                return Signal(orders=[signal], cancels=[])

            bid = player_dict['bid']  # get the player's best bid
            if self.get_sell_sig(projected_payout, bid):  # check for a profitable sell
                lowest_potential_ask = projected_payout / (1 - self.risk)  # get lowest profitable price
                size = self.get_size(lowest_potential_ask)
                signal = {
                    'tradeable_id': player_dict['tradeable_id'],
                    'price': lowest_potential_ask,  # place an order at the lowest profitable price
                    'quantity': size,
                    'side': 'sell'
                }
                return Signal(orders=[signal], cancels=[])
