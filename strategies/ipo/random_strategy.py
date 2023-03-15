import sys

import numpy as np

sys.path.append('../..')
from jockbot.strategy_base import StrategyConfig, Strategy
from jockmkt_sdk.objects import Tradeable
from jockbot.bot import JockBotException
from jockbot.signals import Signal
from typing import Union, Type, Dict, List


class RandomConfig(StrategyConfig):
    """
    Config for the random strategy

    :cvar pct_field_to_buy: percent of the available field to buy
    :type pct_field_to_buy: float, required
    :cvar order_size: number of shares to place each order
    :type order_size: int, required
    :cvar dollar_size: dollar amount to spend on each order
    :type dollar_size: float, optional
    :cvar risk: how high above or below the price you want to bid. (-1, 1). Default: 0
    :type risk: float, optional
    :cvar sides: one of: 'buy', 'sell', or ['buy', 'sell']
    :type sides: list or str
    """
    pct_field_to_buy: float = .5
    order_size: int = 1
    dollar_size: float = None
    risk: float = 0
    sides: list[str] | str = 'buy'
    pass

class RandomStrategy(Strategy):
    def __init__(self, config: RandomConfig | StrategyConfig):
        super().__init__(config)
        self.config = config
        self.pct_field = config.pct_field_to_buy
        self.order_size = config.order_size
        self.dollar_size = config.dollar_size
        self.risk = config.risk
        self.side = config.sides
        self.tradeables: List[Dict[str, float]] = []

    @staticmethod
    def build_player_dict(tradeable: Tradeable) -> Dict[str, float]:
        return {
            'tradeable_id': tradeable.tradeable_id,
            'estimated': tradeable.estimated,
            'last': tradeable.last or 1
        }

    def on_start(self, jockbot):
        for tradeable_id, tradeable_dict in jockbot.player_dict.items():
            self.tradeables.append(self.build_player_dict(tradeable_dict['tradeable']))

    def get_ipo_orders(self):
        orders = []
        n_buys = int(len(self.tradeables) * self.pct_field)
        idxs = np.random.uniform(0, len(self.tradeables) + 1, size=n_buys)
        for idx in idxs:
            if type(self.side) == list:
                side = np.random.choice(self.side)
            elif self.side == 'buy' or self.side == 'sell':
                side = self.side
            else:
                raise JockBotException(None, 'Invalid Input',
                                       'Please make sure that your RandomConfig has side set to one of: '
                                       '"buy", "sell", or ["buy", "sell"]')
            player = self.tradeables[idx]
            price = self.get_price(player['estimated'], side)
            if (side == 'buy' and player['last'] < price) or side == 'sell':
                orders.append(
                    {
                        'tradeable_id': player['tradeable_id'],
                        'quantity': self.get_qty(price),
                        'limit_price': price,
                        'side': side
                    }
                )
        return Signal(orders, [])

    def get_qty(self, price):
        if self.order_size is not None:
            return self.order_size
        else:
            return self.dollar_size // price

    def get_price(self, est, side):
        risk = self.risk / 10
        if side == 'buy':
            return est * (1 + risk)
        else:
            return est * (1 - risk)

    def ipo_trade(self, jockbot) -> Signal:
        return self.get_ipo_orders()

