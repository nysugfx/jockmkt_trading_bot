from jockmkt_sdk.client import Client
from jockmkt_sdk.objects import Game, Entry, Event, Position, Order, Tradeable, PublicOrder, Trade, Balance
import numpy as np
import asyncio
from logging import Logger
from datetime import datetime
from time import time

class JockBot:
    def __init__(self, client: Client, strategy, counter):
        self.fees = 0.02
        self.client: Client = client
        self.strategy = strategy
        self.counter = counter
        self.logger: Logger = Logger
        # self.console_logger = self.init_console_logger()
        self.event_live: bool = False
        self.tasks: list = []
        self.entries: list = []
        self.trade_in_ipo: bool = True if 'ipo' in self.strategy.config.phase else False
        self.trade_in_live: bool = True if 'live' in self.strategy.config.phase else False
        self.ipo_trading_complete = False
        self.event_info: Event = Event
        self.event_status: str = ''
        self._array_len: int = strategy.config.array_len

        self._relevant_stats: list = []
        self.player_dict: dict[str, dict[str, str | Tradeable | np.ndarray, dict[str, np.ndarray]]] | dict = {}
        self.public_orders: list[PublicOrder] = []
        self.public_trades: list[Trade] = []

        self.games: dict[str, Game] = {}
        self.teams: dict[str, list[str]] = {}

        self.loop: asyncio.BaseEventLoop | None = None
        self.q: asyncio.Queue | None = None
        self.msgs: list = []

        self.currency: str = ''
        self.balance: float | None = None
        self.entry: Entry | None = None
        self.signals: list = []  #
        self.holdings: dict[str, Position] = {}
        self.my_orders: dict[str, Order] = {}

        self.first_order_last_minute_ts: float = time()
        self.next_min: float = time() + (60 - datetime.now().second)
        self.order_queue: list = []
        self.target_holdings: dict = {}
        self.max_position: int = strategy.config.max_position
        self.spent: float = 0

    def fetch_bal(self):
        """
        fetch the current balance
        :return: float, current available balance
        """
        return self.balance

    def fetch_client(self):
        """
        fetch the active client, for use in a Strategy class
        :return: jockmkt_sdk.client.Client
        """
        return self.client

    def fetch_orders(self):
        """
        Fetch current active orders, keyed by order id.
        i.e.
        self.my_orders = {
            'ord_xxx': jockmkt_sdk.Order
        }
        :return: dict[str, jockmkt_sdk.objects.Order]
        """
        return self.my_orders

    def fetch_holdings(self):
        """
        Fetch active holdings, which are stored in a dictionary as follows:
        self.holdings = {
                'tdbl_xxx': jockmkt_sdk.objects.Position,
                'tdbl_xxx': jockmkt_sdk.objects.Position
            }
        :return: dict[str, jockmkt_sdk.objects.Position]
        """
        return self.holdings

    def fetch_queue(self):
        """
        Returns an asyncio Queue to which messages are being pushed
        :return: asyncio.Queue
        """
        return self.q

    def fetch_entry(self):
        """
        Get the most recent entry update. It does not call the api, simply returns the last "entry" websocket message
        :return: jockmkt_sdk.objects.Entry
        """
        return self.entry

    def fetch_player_dict(self):
        """
        Fetch a dictionary with all player informaiton, structured as follows (all arrays' most recent update is in the
                                                                               last index, or -1):
        player_dict[tradeable_id] = {'last_updated': time(),
                                     'tradeable': jockmkt_sdk.objects.Tradeable,
                                     'name': str,
                                     'count_ticks': int,
                                     'timestamp': numpy array of timestamps for each update,
                                     'pregame_projection': float,
                                     'fpts_projected': numpy array updated with projections,
                                     'fpts_scored': numpy array updated with scored fpts,
                                     'estimated': numpy array updated with estimated prices,
                                     'bid': numpy array updated with bids,
                                     'ask': numpy array updated with asks,
                                     'last': numpy array updated with last traded price,
                                     'high': numpy array updated with high price,
                                     'low': numpy array updated with low price,
                                     'stats': dict(stat, array of stats)}

        :return:
        """
        return self.player_dict

    def fetch_games(self):
        """
        Fetch a dictionary of games in the event
        :return: dict[str, jockmkt_sdk.object.Game
        """
        return self.games

    def fetch_teams(self):
        return self.teams

