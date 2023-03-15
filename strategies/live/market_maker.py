import sys
sys.path.append('../..')
from jockbot.strategy_base import StrategyConfig, Strategy
from jockmkt_sdk.objects import Order, Tradeable
from jockbot.signals import Signal


PRICE = 'price'
PCT = 'percent'

class MarketMakerConfig(StrategyConfig):
    """
    Config requirements for the MarketMaker strategy

    :cvar spread_type: whether the spread should be based on $ price or percent on either side of the mid price. either 'percent' or 'price'
    :type spread_type: str, required
    :cvar left_tail: $ or percent away from the mid-price you would like the bot to place its bid
    :type left_tail: float, required
    :cvar right_tail: $ or percent away from the mid-price you would like the bot to place its ask
    :type right_tail: float, required
    :cvar player_name: name of the player you want to make a market for. must match player's name in jock api
    :type player_name: str, optional
    :cvar tradeable_id: the player's tradeable id. can be accessed via the webpage or api. preferred over 'player_name' var. e.g. 'tdbl_64017ed1ce12bb263121f5a207c04f13'
    :type tradeable_id: str, optional
    :cvar left_tail: number of shares to place orders on at the bid
    :type left_tail: int, required
    :cvar right_tail: number of shares to place orders on at the ask
    :type right_tail: int, required

    """
    spread_type: str = PRICE
    left_tail: float = 0.5
    right_tail: float = 0.75
    player_name: str | None = None
    tradeable_id: str | None = None
    left_size: int = 1
    right_size: int = 1


class MarketMaker(Strategy):
    """

    Make a market on a single player. Not functional until allowed to place bids and asks at the same time.

    """
    def __init__(self, config: StrategyConfig | MarketMakerConfig):
        super().__init__(config)
        self.config = config
        self.player_name = config.player_name
        self.tradeable_id = config.tradeable_id
        self.spread_type = config.spread_type
        self.player = None
        self.spread = (config.left_tail, config.right_tail)
        self.bid_size = config.left_size
        self.ask_size = config.right_size
        self.open_orders = []

    def get_tradeable(self, jockbot_player_dict):
        if self.tradeable_id is not None:
            return jockbot_player_dict[self.tradeable_id]['tradeable']
        if self.player_name is None:
            return list(jockbot_player_dict.values())[0]['tradeable']
        else:
            name = self.player_name.lower()
            for k, p in jockbot_player_dict.items():
                if name == p['name'].lower():
                    return p['tradeable']

    def on_start(self, jockbot):
        self.player = self.get_tradeable(jockbot.player_dict)
        self.tradeable_id = self.player.tradeable_id

    def on_data(self, tradeable_id: str, jockbot) -> Signal:
        event_live = jockbot.event_live
        signal = None
        if event_live:
            if tradeable_id == self.tradeable_id:
                signal = self.get_signal(jockbot.player_dict[tradeable_id])
        return signal

    def on_order(self, order: Order, my_orders: dict[str, Order]) -> Signal:
        for order_id, order in my_orders:
            self.open_orders.append(order) if order.status == 'active' and order.tradeable_id == self.tradeable_id else\
                None

    def get_pct_spread(self, est):
        return est * (1 - self.spread[0]), est * (1 + self.spread[1])

    def get_price_spread(self, est):
        return est - self.spread[0], est + self.spread[1]

    def get_signal(self, player_dict):
        est = player_dict['est'][-1]
        bid_price, ask_price = self.get_price_spread(est) if self.spread_type == 'price' else self.get_pct_spread(est)
        orders = [
            {'tradeable_id': self.tradeable_id,
             'price': bid_price,
             'quantity': self.bid_size,
             'size': 'buy'},
            {'tradeable_id': self.tradeable_id,
             'price': ask_price,
             'quantity': self.ask_size,
             'size': 'sell'}
        ]
        cancels = [order.order_id for order in self.open_orders]

        return Signal(orders, cancels)





