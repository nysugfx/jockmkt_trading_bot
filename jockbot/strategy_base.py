import os
import logging
import typing
from typing import Type
from jockbot.signals import Signal
from jockmkt_sdk.objects import Order, PublicOrder, Event, Game, Trade
from jockbot.bot_typing import JockBot


class StrategyConfig:
    """
    Base strategy config class

    :ivar event_id: the event ID for the event the user wishes to trade in
    :type event_id: str, required
    :ivar order_size: number of shares per order. some strategies allow you to set the $ amount too. see that strategy's config. Default: 1
    :type order_size: int, required
    :ivar api_key: your api token
    :type api_key: str, required
    :ivar secret_key: your secret key
    :type secret_key: str, required
    :ivar max_spend: the max $ amount you want to spend. Default: 1000
    :type max_spend: float, required
    :ivar max_position: the maximum number of shares you would like to own at a time
    :type max_position: int, optional
    :ivar phase: a list of phases, must contain at least one of 'ipo' or 'live' depending on your strategy, or both.
    :type phase: list, required
    :type array_len:  int
    :ivar array_len:  how much historical data the user would like saved. An array of length 1000 will hold the last 1000 updates, for example, to projected fantasy points (or other statistics/metrics) default: 300
    :ivar print_to_console: should logging messages be printed to console
    :type print_to_console: bool
    :ivar log_path: where the user wishes logs to be stored. The default will create a log folder wherever the bot is being run from. default: './'
    :type log_path: str,
    :type log_level: int, optional
    :ivar log_level: logging.DEBUG, logging.INFO, logging.ERROR, etc. Default: logging.DEBUG or 10
    :ivar log_path: the path you'd like to build your logs folder. Default './'
    :type log_path: :class:`os.PathLike` or str
    :ivar always_update: If false, numpy arrays for each player will only update when there is a change in that data point (i.e. only when a player scores fantasy points, or their estimated price changes). If true, numpy arrays update regardless of whether there is a change in fpts, price, or stat. Default: False
    :type always_update:  bool, optional
    :ivar prefill: if True, numpy arrays will be filled with the initial statistic, price or metric. If False, fills numpy arrays with zeros, and the last index of the array will have initial stat, price or metric. Default: True
    :type prefill: bool, optional
    :ivar message_consumers: number of websocket message consumers. The more players there are in the event, the more you should increase this number. Max recommended is 12.
    :type message_consumers: int, default: 4
    :ivar port: the port for web interface, default: 8080. Can be set via env vars
    :type port: int
    :ivar host_name: host name, defaults to 127.0.0.1 (localhost)
    :type host_name: str
    :ivar web_popup: open up a webpage with information about holdings and pnl. Default: True
    :type web_popup: bool

    """
    def __init__(self):
        self.port = int(os.getenv('PORT', '8080'))
        self.host_name = os.getenv('HOSTNAME', '127.0.0.1')
        self.secret_key = os.getenv('secret_key')
        self.api_key = os.getenv('api_key')
        self.event_id = None
        self.log_level = int(os.getenv('log_level', logging.DEBUG))
        self.log_path = os.getenv('log_path', './')
        if self.secret_key is None or self.api_key is None:
            print('*** keys not found in environment variables ***')

        self.array_len: int = 300
        self.always_update: bool = False
        self.phase: list = ['live']
        self.prefill: bool = False
        self.message_consumers: int = 4
        self.max_spend: float = 1000
        self.max_position: int = 10
        self.print_to_console: bool = True
        self.strategy_id: str | None = None
        self.order_size: int = 1
        self.risk: float = 0.0
        self.web_popup: bool = True


class Strategy:
    """
    all strategy funcs must return a Signal object, to which you pass in an order (or list of orders)
    and/or a list of order_ids to cancel

    for example:

    .. code-block:: python

        def on_data(tradeable_id, player_dict)
            orders = [{'tradeable_id': tradeable_id,
                     'price': 2.00
                     'quantity': 1
                     'side': 'buy'},
                     {'tradeable_id': tradeable_id,
                     'price': None
                     'quantity': 1
                     'side': 'sell'}]
            cancels = [
                'ord_xxx1',
                'ord_xxx2',
                'ord_xxx3'
            ]

            return Signal(orders, cancels)

    """

    def __init__(self, config: Type[StrategyConfig] | StrategyConfig):
        self.config: StrategyConfig = config

    def on_start(self, jockbot: JockBot):
        """
        functions to be called upon initialization of the websockets within the JockBot.

        The JockBot will pass itself through as an argument. See the JockBot documentation for available instance vars.

        :param jockbot: :class:`bot.JockBot`

        :return: :class:`signals.Signal`

        """

        pass

    def ipo_trade(self, jockbot: JockBot) -> Signal:
        """
        function passes through the jockbot and should return a list of signals that will be traded during IPO

        :param jockbot: :class:`bot.JockBot` object.

        :return: :class:`signals.Signal`

        """

        pass

    def on_stop(self, jockbot: JockBot) -> Signal:
        """
        functions that are called whenever the jockbot stops, such as a profit calculation.

        :param jockbot: :class:`bot.JockBot` object

        :return: :class:`signals.Signal`

        """
        pass

    def on_data(self, tradeable_id: str,
                jockbot: JockBot) -> Signal:  # player_dict: dict[str, Tradeable, np.ndarray], event_live: bool):
        """
        The JockBot passes the following information to this function every time there is a tradeable update.

        :param tradeable_id: Tradeable ID that has been updated
        :param jockbot: the :class:`bot.JockBot` and all of its contained information.

        The entire player dictionary for the event can be accessed, keyed by tradeable_id, structured as follows:

        .. code-block:: python

            jockbot.player_dict[tradeable_id] = {
                'last_updated': timestamp,
                'tradeable': Tradeable object (see Jockmkt SDK docs for more)
                'count_ticks': int, the number of times this tradeable has been updated,
                'timestamp': np.ndarray[timestamp],
                'pregame_projection': pregame fpts projected, float
                'fpts_projected': np.ndarray[float] array of live fpts projected
                'fpts_scored': np.ndarray[float] of fpts scored
                'estimated': np.ndarray[float] of estimated prices
                'bid': np.ndarray[float] of bids
                'ask': np.ndarray[float] of asks
                'last': np.ndarray[float] of last traded price
                'high': np.ndarray[float] of high traded price
                'low': np.ndarray[low] of low traded price
                'stats': {
                'stat1': np.ndarray[float or int] of a stat
                the stats dict differs between sport, but contains all numerical stats for each player
                }
            }

        :return: :class:`signals.Signal`

        """

        pass

    def on_tick(self, order: PublicOrder, public_orders: list) -> Signal:
        """
        The JockBot Passes information to this func every time a public order is placed.

        :param order: :class:`jockmkt_sdk.objects.PublicOrder` object, the order that was placed. See jockmkt sdk docs for more.
        :param public_orders: list[:class:`jockmkt_sdk.objects.PublicOrder`] objects that have been placed in the event.

        :return: :class:`signals.Signal`

        """

        pass

    def on_order(self, order: Order, my_orders: dict[str, Order]) -> Signal:
        """
        The JockBot passes the following information tot his function every time a user's orders are updated.

        :param order: :class:`jockmkt_sdk.objects.Object` object, the order that was created or updated
        :param my_orders: a dictionary keyed by order_id containing orders that are active for this event

        :return: :class:`signals.Signal`

        """

        pass

    def on_event(self, event_info: Event) -> Signal:
        """
        JockBot calls this function every time the event is updated

        :param event_info: :class:`jockmkt_sdk.objects.Event` object, see jockmkt sdk docs for info

        :return: :class:`signals.Signal`

        """

        pass

    def on_play(self, game: Game, games: dict[str, Game]) -> Signal:
        """
        JockBot calls this function every time there is a Game update, if the user is subscribed to 'games'

        :param game: :class:`jockmkt_sdk.objects.Game` that was updated, see jockmkt sdk docs for info
        :param games: list[:class:`jockmkt_sdk.objects.Game`]

        :return: :class:`signals.Signal`

        """

        pass

    def on_trade(self, trade: Trade, public_trades: list) -> Signal:
        """
        Passes the trade and the list of all public trades to your strategy when there is a trade websocket message

        :param trade: :class:`jockmkt_sdk.objects.Trade`
        :param public_trades: list[:class:`jockmkt_sdk.objects.Trade`]

        :return: :class:`signals.Signal`

        """

        pass

