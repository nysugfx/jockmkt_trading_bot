import sys
sys.path.append('../..')
from jockbot.strategy_base import StrategyConfig, Strategy
from jockmkt_sdk.objects import Tradeable
from jockmkt_sdk.exception import JockAPIException
from jockbot.signals import Signal
from typing import Union, Dict, Type

"""
Not currently functional as there is not allowed to be a buy and sell order on the same dude at the same time.
"""

class ShortTopLongBottomConfig(StrategyConfig):
    """
    Config with extra required variables to run :class:`ShortTopLongBottom` strategy

    :cvar max_buy_price: buy all players below this price. Default 1.5
    :type max_buy_price: float, required
    :cvar min_sell_price: sell all players above this price
    :type min_sell_price: float, required
    :cvar order_size: number of shares to buy (alternatively, the user can set dollar_size)
    :type order_size: int, optional
    :cvar dollar_size: dollar amount to spend on each order (i.e. if $20, buy 18 shares of a player at $1.50)
    """
    max_buy_price: float = 1.5
    min_sell_price: float = 16.00
    order_size: int = 5
    dollar_size: float | None = None

class ShortTopLongBottom(Strategy):
    def __init__(self, config: StrategyConfig | ShortTopLongBottomConfig):
        # raise JockAPIException('This strategy is not yet functional.')
        super().__init__(config)
        self.config = config
        self.quantity = config.order_size
        self.dollar_size = config.dollar_size
        self.buy_price = config.max_buy_price
        self.sell_price = config.min_sell_price
        self.tradeables = {}

    @staticmethod
    def build_player_dict(tradeable: Tradeable) -> Dict[str, float]:
        return {
            'tradeable_id': tradeable.tradeable_id,
            'estimated': tradeable.estimated,
            'last': tradeable.last or 1
        }

    def on_start(self, jockbot):
        for key, value in jockbot.player_dict.items():
            self.tradeables[key] = self.build_player_dict(value['tradeable'])

    def get_ipo_orders(self):
        orders = []
        buy_sell_tuples = [
            (self.sell_price, 'sell'),
            (self.buy_price, 'buy')
        ]

        for key, value in self.tradeables.items():
            for price, side in buy_sell_tuples:
                if side == 'buy' and value['last'] < self.buy_price:
                    orders.append(
                        {
                            'tradeable_id': value['tradeable_id'],
                            'quantity': self.quantity,
                            'limit_price': price,
                            'side': side
                        }
                    )
                elif side == 'sell' and value['last'] > self.sell_price:
                    orders.append(
                        {
                            'tradeable_id': value['tradeable_id'],
                            'quantity': self.quantity,
                            'limit_price': price,
                            'side': side
                        }
                    )
        return Signal(orders, [])

    def ipo_trade(self, jockbot) -> Signal:
        return self.get_ipo_orders()

