import logging
import json
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import List
import numpy as np
from time import time, sleep
import asyncio
from threading import Lock
from jockmkt_sdk.client import Client
from jockmkt_sdk.exception import JockAPIException
from jockmkt_sdk.jm_sockets.sockets import JockmktSocketManager
from jockmkt_sdk.objects import Event, Order, PublicOrder, Trade, Tradeable, Entry, Position, Game, Balance
from jockbot.strategy_base import Strategy
from jockbot.defaults import stats_cases, INSTRUMENT
from jockbot.signals import Signal, OrderSignal, CancelSignal

class EnvOrderCt:
    def __init__(self):
        self._counter = 0
        self._lock = Lock()

    def increment(self):
        with self._lock:
            self._counter += 1

    def reset(self):
        with self._lock:
            self._counter = 1

    def get(self):
        with self._lock:
            return self._counter

class JockBot(object):
    """
    Class responsible for most of the functionality of the jockbot. Not all attributes will be annotated.

    :param client: Instance of :class:`jockmkt_sdk.client.Client`
    :param strategy: Instance of :class:`strategy_base.Strategy`

    :ivar fees: current fee amount to trade. 0.02 or 2% at this release
    :ivar client: stored version of client arg for access within a strategy
    :ivar event_live: bool, whether the event is open to trading
    :ivar event_info: :class:`jockmkt_sdk.objects.Event` containing info about the event in which we are trading
    :ivar event_status: str, the event's current status
    :ivar player_dict:  The entire player dictionary for the event, keyed by tradeable_id, structured as follows:

    .. code-block:: python

        player_dict = {
            'tdbl_xxx': {
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
        }

    :ivar public_orders: a list of orders placed by the public
    :ivar public_trades: a list of trades placed by the public
    :ivar games: dict keyed by game id, mapping to :class:`jockmkt_sdk.objects.Game` objects for all relevant games in the event
    :ivar teams: dict keyed by team_id, mapping to :class:`jockmkt_sdk.objects.Team` objects for all teams in event
    :ivar balance: float, available balance.
    :ivar holdings: dict mapping tradeable_id to :class:`jockmkt_sdk.objects.Tradeable` for players in event
    :ivar entry: :class:`jockmkt_sdk.objects.Entry` object
    :ivar my_orders: list of currently active orders

    """
    def __init__(self, client: Client, strategy: Strategy, counter: EnvOrderCt):
        self.fees = 0.02
        self.client: Client = client
        self.strategy: Strategy = strategy
        self.counter = counter
        self.logger = self.init_logger()
        # self.console_logger = self.init_console_logger()
        self.event_live: bool = False
        self.tasks = []
        self.entries = self._fetch_entries()
        try:
            if strategy.config.event_id not in self.entries:
                self.client.create_entry(strategy.config.event_id)
                logging.info('No entry found. Creating entry.')
            else:
                pass
        except JockAPIException as e:
            self.logger.critical(f'{e}: Could not create an entry.')
        self.trade_in_ipo = True if 'ipo' in self.strategy.config.phase else False
        self.trade_in_live = True if 'live' in self.strategy.config.phase else False
        self.ipo_trading_complete = False
        self.event_info: Event = self.client.get_event(strategy.config.event_id)
        self.event_status: str = self.event_info.status
        if self.event_status == 'live':
            self.event_live = True
        self._array_len: int = strategy.config.array_len

        self._relevant_stats: list = stats_cases(self.event_info.league)
        self.player_dict: dict[str, dict[str, str | Tradeable | np.ndarray, dict[str, np.ndarray]]] | dict = {}
        self._initialize_player_dict()
        self.public_orders: list[PublicOrder] = []
        self.public_trades: list[Trade] = []

        self.games: dict[str, Game] = dict((game.game_id, game) for game in self.event_info.games)
        self.teams: dict[str, list[str]] = self._build_teams_dict()

        self.loop: asyncio.BaseEventLoop | None = None
        self._socket: JockmktSocketManager | None = None
        self.q: asyncio.Queue | None = None
        self.msgs: list = []

        self.currency: str = self._get_currency()
        self._fetch_balances()
        self.balance: float | None = None
        self.entry: Entry | None = None
        self.signals: list = []  #
        self.holdings: dict[str, Position] = self._fetch_holdings()
        self.my_orders: dict[str, Order] = self._fetch_orders()
        self.logger.info('Jockbot successfully initialized with the following parameters: '
                         f'\nEvent ID : {strategy.config.event_id}'
                         f'\nEvent Name : {self.event_info.name}'
                         f'\nEvent status : {self.event_status}'
                         f'\nStrategy: {self.strategy.__class__}')
        if self.event_status in ['live_closed', 'cancelled', 'payouts_completed', 'prizes_paid']:
            self.logger.error('Invalid event status.')
            raise JockBotException(code='', title='Invalid Event Status', message='\nYou are trying to initialize the '
                                                                                  'JockBot on an event that is '
                                                                                  'currently in {} phase. \nTry a '
                                                                                  'different event, since you can no '
                                                                                  'longer trade in this one.'.format(
                                                                                   self.event_status))
        for curr in self.client.get_account_bal():
            self._parse_balance(Balance(curr))
        self.order_ct = 0
        self.first_order_last_minute_ts = time()
        self.next_min = time() + (60 - datetime.now().second)
        self.order_queue = []
        self.target_holdings = {}
        self.max_position = strategy.config.max_position
        self.spent = 0

    # ========== HANDLE BALANCES ========== #
    def _get_currency(self):
        """
        fetches the relevant currency for the event.
        :return:
        """
        if self.event_info.type == 'contest':
            currency = 'cur_' + self.strategy.config.event_id[-32:]
        else:
            currency = 'usd'
        self.logger.debug(f'Currency: {currency}')
        return currency

    def _parse_balance(self, balance):
        """
        Parses balance updates that come from the websocket feed, updating JockBot's balance instance variable.
        """
        if balance.currency == self.currency:
            self.balance = balance.buying_power
            self.logger.debug(f'Event balance: {self.balance}')
        else:
            return

    def _fetch_entries(self):
        self.logger.debug('Fetching entries.')
        return [i.event_id for i in self.client.get_entries(limit=50)]

    def _fetch_balances(self):
        """
        Fetch user's account balance, store the relevant currency/balance in memory
        """
        self.logger.debug('Fetching balances.')
        balances = self.client.get_account_bal()

        for cur in balances:
            self._parse_balance(Balance(cur))

    def _fetch_holdings(self):
        """
        Fetches the user's positions upon initialization. Holdings are updated via websockets in the future.

        Holdings are stored in a dictionary as follows:

        self.holdings = {
                'tdbl_xxx': jockmkt_sdk.Position,
                'tdbl_xxx': jockmkt_sdk.Position
            }

        Holdings are Position objects, documentation for which can be found within jockmkt-sdk docs.

        :return:
        """
        self.logger.debug('Fetching holdings.')
        positions = self.client.get_positions()
        return dict((position.tradeable_id, position) for position in positions if position.event_id == self.strategy.config.event_id)

    def _fetch_orders(self):
        """
        Fetches all active orders upon initialization.

        Orders are stored as follows:



        """
        self.logger.debug('Fetching orders.')
        return dict((order.order_id, order) for order in self.client.get_orders(event_id=self.strategy.config.event_id,
                                                                                active=True))

    def _initialize_player_dict(self):
        self.logger.debug('Initalizing player dictionary.')
        for player in self.event_info.tradeables:
            self.player_dict[player.tradeable_id] = {'last_updated': time(),
                                                     'tradeable': player,
                                                     'name': player.name,
                                                     'count_ticks': 0,
                                                     'timestamp': np.zeros(self._array_len),
                                                     'pregame_projection': player.fpts_proj_pregame,
                                                     'fpts_projected': np.zeros(self._array_len),
                                                     'fpts_scored': np.zeros(self._array_len),
                                                     'estimated': np.zeros(self._array_len),
                                                     'bid': np.zeros(self._array_len),
                                                     'ask': np.zeros(self._array_len),
                                                     'last': np.zeros(self._array_len),
                                                     'high': np.zeros(self._array_len),
                                                     'low': np.zeros(self._array_len),
                                                     'stats': dict(
                                                         (stat, np.zeros(self._array_len)) for stat in
                                                         self._relevant_stats)}

    def _build_teams_dict(self):
        self.logger.debug('Building teams dictionary.')
        if self.event_info.league != 'pga' and self.event_info.league != 'nascar' and \
                self.event_info.league != 'simulated_horse_racing':
            teams = {}
            for gm in self.event_info.games:
                teams[gm.home_info['team_id']] = []
                teams[gm.away_info['team_id']] = []
            for player in self.event_info.tradeables:
                teams[player.entity.team_id].append(player.entity_id)
            return teams
        else:
            return {}

    ### ========== ORDER CHECKS ========== ###

    def get_total_spend(self):
        spend = 0
        for key, val in self.my_orders.items():
            if val.side == 'buy':
                spend += val.cost_basis
            if val.side == 'sell':
                short_hold = (val.filled_quantity * 25) - val.proceeds
                spend += short_hold
        for key, val in self.holdings.items():
            qty = val.quantity_owned
            if qty > 0:
                spend += val.cost_basis
            else:
                short_hold = (- qty * 25) - val.proceeds
                spend += short_hold
        return spend

    def check_max_spend(self, order):
        if order.quantity > 0:
            if order.quantity * order.limit_price * (1 + self.fees) + self.spent > self.strategy.config.max_spend:
                self.logger.warning(f'Your max spend is {self.strategy.config.max_spend}, and this order will bring you above your max_spend.')
                return True
        elif order.quantity < 0:
            hold = order.quantity * (25 - order.limit_price)
            if hold * (1 + self.fees) + self.spent > self.strategy.config.max_spend:
                self.logger.warning(f'Your max spend is {self.strategy.config.max_spend}, and this order will bring you above your max_spend.')
                return True
        return False

    def check_max_pos_size(self, order: OrderSignal):
        if order.side == 'sell':
            quantity = -order.quantity
        else:
            quantity = order.quantity
        if order.tradeable_id in self.holdings:
            if abs(self.holdings.get(order.tradeable_id).quantity_owned + quantity) > self.max_position:
                return True
        return False

    def check_sufficient_funds(self, order: OrderSignal):
        """will need to get number of non-neg players"""
        if order.side == 'buy':
            total = order.quantity * order.limit_price * 1.02
        else:
            total = order.quantity * (25 - (order.limit_price * 1.02))
        if total > self.balance:
            self.logger.debug(f'{total} is greater than {self.balance}. Cannot place order')
            return False
        return True

    def get_target_holdings(self):
        """
        parse your holdings and orders to figure out what the current holdings are
        then parse order queue to figure out differences
        :return:"""
        target_holdings = {}
        self.logger.debug('getting target holdings from order queue')
        for order in self.order_queue:
            try:
                target_holdings[order.tradeable_id]['qty'] += order.quantity
                target_holdings[order.tradeable_id]['total'] += order.limit_price * order.quantity
                self.logger.debug(f'target holding: {target_holdings[order.tradeable_id]}')
            except KeyError:
                target_holdings[order.tradeable_id] = {
                    'qty': order.quantity,
                    'total': order.limit_price * order.quantity
                }

        for order in self.parse_open_orders_for_targets():
            if order.tradeable_id in target_holdings:
                target_holdings[order.tradeable_id]['qty'] -= order.quantity
                target_holdings[order.tradeable_id]['total'] -= order.quantity * order.limit_price

        for key, value in target_holdings.items():
            target_holdings[key]['avg_price'] = np.round(value['total'] / value['qty'], 2)
        self.order_queue = []
        self.logger.debug(target_holdings)
        return target_holdings

    def parse_open_orders_for_targets(self):
        """
        TODO: fix this when you update sdk
        :return:
        """
        order_ct = 100
        # orders, order_ct = self.client.get_orders(event_id=strategy.config.event_id, active=True, include_count=True)
        orders = self.client.get_orders(event_id=self.strategy.config.event_id, active=True)
        if order_ct > 100:
            orders.extend(self.client.get_orders(start=1, event_id=self.strategy.config.event_id, active=True))
        if order_ct > 200:
            orders.extend(self.client.get_orders(start=2, event_id=self.strategy.config.event_id, active=True))
        return orders

    def get_order_q_orders(self):
        orders = []
        for key, val in self.get_target_holdings():
            order = {
                'tradeable_id': key,
                'quantity': val['qty'],
                'price': val['avg_price'],
                'side': 'buy' if val['qty'] > 0 else 'sell'
            }
            orders.append(order)
        self.logger.debug(orders)
        return Signal(orders, [])

    def order_counter(self, order):
        now = time()
        next_min = 60 - datetime.now().second
        if now > self.next_min:
            self.logger.debug('Resetting order counter.')
            self.counter.reset()
            self.first_order_last_minute_ts = now
            self.next_min = now + next_min + 1
            holding_diffs = self.get_order_q_orders()
            if len(holding_diffs.order) > 0:
                self.logger.debug(f'{len(holding_diffs.order)} orders in the queue. Placing them now.')
                self.parse_signal(holding_diffs)
        else:
            if self.counter.get() < 11:
                self.logger.debug(f'{self.counter.get()} orders placed.')
                self.counter.increment()
            else:
                self.logger.debug(f'Order limit reached. Appending order to order queue.')
                self.order_queue.append(order)
                return False
        return True

    ### ========== SIGNAL CHECKS ========== ###
    def parse_signal(self, signal: Signal):
        self.logger.debug('Parsing signal.')
        if type(signal) != Signal:
            self.logger.critical('Convert your orders into a signal object.')
            raise TypeError('Please convert your orders into a Signal object')
        if self.event_live:
            orders: list[OrderSignal] = signal.order
            cancels: list[CancelSignal] = signal.cancel
            self.logger.debug(f'Received: {len(orders)} orders, {len(cancels)} cancels')

            for cancel in cancels:
                self.logger.info(f'cancelling order: {cancel.order_id}')
                self.client.delete_order(cancel.order_id)

            for order in orders:
                if order.limit_price is None:
                    if order.side == 'buy':
                        order.limit_price = self.player_dict[order.tradeable_id]['ask'][-1]
                    elif order.side == 'sell':
                        order.limit_price = self.player_dict[order.tradeable_id]['bid'][-1]
                        
                if self.check_max_spend(order):
                    # CHECKING FOR MAX SPEND
                    self.logger.warning('Order would place you over event max spend.')
                    continue
                if self.check_max_pos_size(order):
                    # CHECKING FOR MAX POS
                    self.logger.warning('Order would place you over event max position size.')
                    continue
                if not self.order_counter(order):
                    self.logger.warning(f'Order counter: {self.counter.get()}. Limit reached.')
                    continue
                if not self.check_sufficient_funds(order):
                    self.logger.error(f'Insufficient funds to place this order.')
                    continue
                self.logger.info(f'Placing an order on '
                                 f'{self.player_dict[order.tradeable_id]["name"]} '
                                 f'price: {order.limit_price}, '
                                 f'size: {order.quantity}, '
                                 f'side: {order.side}')
                self.client.place_order(order.tradeable_id, order.limit_price, order.quantity, order.side,
                                        'live')
                self.logger.debug('Order successfully placed.')
            self.logger.debug('Done parsing signal.')

    def _place_ipo_orders(self, signal: Signal):
        self.logger.debug('_place_ipo_orders() called')
        if type(signal) != Signal:
            raise TypeError('Please convert your orders into a Signal object')
        orders = signal.order
        for order in orders:
            self.logger.debug(f'placing {order.tradeable_id}')
            if order.limit_price is None:
                order.limit_price = self.player_dict[order.tradeable_id]['estimated'][-1]
            self.logger.info(f'Placing IPO order on: {self.player_dict[order.tradeable_id]["tradeable"].name}, '
                             f'price: {order.limit_price}, '
                             f'size: {order.quantity}, '
                             f'side: {order.side}')
            if self.check_max_spend(order):
                self.client.place_order(order.tradeable_id, order.limit_price, order.quantity, order.side, 'ipo')
            else:
                self.logger.warning(f'This order would place you over your max budget of {self.strategy.config.max_spend} for this '
                                    f'event.')
        self.logger.debug('_place_ipo_orders() completed')
        # =========== PARSE WEBSOCKET MESSAGES =========== #

    def _parse_position_msg(self, position):
        """
        Parse a position message from the websocket feed and update self.holdings
        """
        if position.event_id == self.strategy.config.event_id:
            self.holdings[position.tradeable_id] = position

    def _parse_entry_msg(self, entry):
        """
        Parse an entry update from the websocket feed and update self.entry
        :param entry:
        :return:
        """
        if entry.event_id == self.strategy.config.event_id:
            self.entry = entry

    def _update_tradeable(self, player):
        tradeable_id = player.tradeable_id
        player_dict = self.player_dict[tradeable_id]
        self.player_dict[tradeable_id]['last_updated'] = time()
        self.player_dict[tradeable_id]['tradeable'] = player
        self.player_dict[tradeable_id]['count_ticks'] += 1
        self.player_dict[tradeable_id]['timestamp'] = self._shift_array(player_dict['timestamp'], player.updated_at)
        self.player_dict[tradeable_id][INSTRUMENT.FPTS_PROJ.value] = self._shift_array(
            player_dict[INSTRUMENT.FPTS_PROJ.value],
            player.fpts_proj_live)
        self.player_dict[tradeable_id][INSTRUMENT.FPTS_SCORED.value] = self._shift_array(
            player_dict[INSTRUMENT.FPTS_SCORED.value],
            player.fpts_scored)
        self.player_dict[tradeable_id][INSTRUMENT.ESTIMATED.value] = self._shift_array(
            player_dict[INSTRUMENT.ESTIMATED.value],
            player.estimated)
        self.player_dict[tradeable_id][INSTRUMENT.BID.value] = self._shift_array(player_dict[INSTRUMENT.BID.value],
                                                                                 player.bid or 1)
        self.player_dict[tradeable_id][INSTRUMENT.ASK.value] = self._shift_array(player_dict[INSTRUMENT.ASK.value],
                                                                                 player.ask)
        self.player_dict[tradeable_id][INSTRUMENT.LAST.value] = self._shift_array(player_dict[INSTRUMENT.LAST.value],
                                                                                  player.last or player.ipo)
        self.player_dict[tradeable_id][INSTRUMENT.HIGH.value] = self._shift_array(player_dict[INSTRUMENT.HIGH.value],
                                                                                  player.high or player.ipo)
        self.player_dict[tradeable_id][INSTRUMENT.LOW.value] = self._shift_array(player_dict[INSTRUMENT.LOW.value],
                                                                                 player.low or player.ipo)
        if len(player.stats) > 0:
            for stat in self._relevant_stats:
                self.player_dict[tradeable_id]['stats'][stat] = self._shift_array(player_dict['stats'][stat],
                                                                                  player.stats[0].get(stat, 0))

    # =========== INITIALIZE AND RUN WEBSOCKETS =========== #
    def ipo_trade(self):
        """
        I want to make this portion of the jockbot more complex. I think we want to listen to websocket messages and
        make ipo trades based on price information that we receive.
        :return:
        """
        self.logger.info('Placing IPO orders.')
        self._place_ipo_orders(self.strategy.ipo_trade(self))
        self.logger.debug('IPO trading complete.')

    async def _initialize_websockets(self):
        self._socket = await self.client.ws_connect(self.loop, self.msgs, self._error_handler, self.q.put)
        self.logger.debug('Successfully initialized websockets')

    async def _error_handler(self):
        """
        Automatically reconnect if we have a ConnectionError
        :return:
        """
        self.logger.error('Attempting to reconnect')
        await self._socket.reconnect()

    async def consumer(self):
        if not self.q.empty():
            data = await self.q.get()
            if 'error' in data:
                self.logger.warning(f'JockAPIException: {data}')
            data = json.loads(data)
            signal = None
            self.logger.debug(data)

            obj = data['object']

            if obj == 'subscription':
                self.logger.info('Subscribed to: {}'.format(data['type']))
                pass

            elif obj == 'tradeable':
                tradeable = Tradeable(data[obj])
                self._update_tradeable(tradeable)
                signal = self.strategy.on_data(tradeable.tradeable_id, self)

            elif obj == 'event':
                self.event_info = Event(data[obj])
                self.event_status = data[obj]['status']
                if self.event_status == 'live':
                    self.event_live = True
                signal = self.strategy.on_event(self.event_info)

            elif obj == 'order' and data['subscription'] == 'account':
                """
                TODO: Need to take a look here and figure out if we can are properly handling orders that are filled
                """
                order = Order(data[obj])
                self.my_orders[order.order_id] = order
                signal = self.strategy.on_order(order, self.my_orders)
                self.spent = self.get_total_spend()

            elif obj == 'order' and data['subscription'] == 'event_activity':
                order = PublicOrder(data[obj])
                self.public_orders.append(order)
                signal = self.strategy.on_tick(order, self.public_orders)

            elif obj == 'trade':
                trade = Trade(data[obj])
                self.public_trades.append(trade)
                signal = self.strategy.on_trade(trade, self.public_trades)

            elif obj == 'balance':
                balance = Balance(data[obj])
                self._parse_balance(balance)

            elif obj == 'position':
                position = Position(data[obj])
                self._parse_position_msg(position)

            elif obj == 'entry':
                entry = Entry(data[obj])
                self._parse_entry_msg(entry)

            elif obj == 'game':
                game = Game(data[obj])
                self.games[game.game_id] = game
                signal = self.strategy.on_play(game, self.games)

            if signal:
                self.parse_signal(signal)
            else:
                pass
            self.q.task_done()

    def set_queue(self, queue: asyncio.Queue):
        self.logger.debug('Queue set successfully.')
        self.q = queue

    def set_event_loop(self, loop: asyncio.BaseEventLoop):
        self.logger.debug('Event loop set successfully.')
        self.loop = loop

    def ipo_trade_loop(self):
        if self.trade_in_ipo and not self.ipo_trading_complete:
            for player in self.client.get_event(self.strategy.config.event_id).tradeables:
                self._update_tradeable(player)
            self.ipo_trade()
            self.ipo_trading_complete = True

    # ========== HELPER/STATIC FUNCS ========== #
    @staticmethod
    def _shift_array(array, data):
        """
        Shift the array by one index to the left, making room for new data.

        The user can set 'always_update' to True if they want to update their arrays regardless of the new value.
        If false, the array only updates when the new data is different from the old data.
        """
        if data == array[-1]:
            return array
        else:
            return np.append(array[1:], [data])

    # ========== PUBLIC FUNCS ========== #
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
        Fetch a dictionary with all player informaiton, structured as follows (all arrays' most recent update is in the last index, or -1):

        .. code-block:: python

            player_dict =
                {tradeable_id:
                    {'last_updated': time(),
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
                    'stats': dict(stat, array of stats)}}

        :return: dict

        """

        return self.player_dict

    def fetch_games(self):
        """
        Fetch a dictionary of games in the event

        :return: dict[str, :class:`jockmkt_sdk.object.Game`]

        """
        return self.games

    def fetch_teams(self):
        """
        Fetch a dictionary of teams, keyed by team_id with a list of all players on that team

        :return: dict[team_id, list[:class:`jockmkt_sdk.objects.Entity`]]

        """
        return self.teams

    ### ======= LOGGING ======= ###
    def init_logger(self):
        logger = logging.getLogger(__name__ + str(self.strategy.config.strategy_id))
        self.init_log_folder()
        logger = self.set_logging_config(logger)
        return logger

    def init_log_folder(self):
        path = os.path.join('./', self.strategy.config.log_path, './logs')
        if not os.path.exists(path):
            os.mkdir(path)

    def set_logging_config(self, logger):
        filepath = os.path.join('./', self.strategy.config.log_path, './logs/jockbot.log')
        if not os.path.exists(filepath):
            with open(filepath, 'x') as file:
                file.close()
        logger.setLevel(self.strategy.config.log_level)
        filehandler = RotatingFileHandler(filepath, 'a', maxBytes=10000000, backupCount=6)
        filehandler.setLevel(self.strategy.config.log_level)
        formatter = logging.Formatter('%(asctime)s - '
                                      # '%(levelname)s - %(filename)s:%(funcname)s:%(lineno)s'
                                      f' - {self.strategy.config.event_id} - %(message)s')
        filehandler.setFormatter(formatter)
        logger.addHandler(filehandler)
        if self.strategy.config.print_to_console:
            console_formatter = logging.Formatter('%(asctime)s - %(message)s')
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.strategy.config.log_level)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        return logger

class BotThreadRunner(object):
    def __init__(self, strategy: Strategy, counter: EnvOrderCt):
        self.client: Client = Client(strategy.config.secret_key, strategy.config.api_key)
        self.strategy: Strategy = strategy
        self.counter: EnvOrderCt = counter
        self.bot: JockBot = JockBot(self.client, strategy, counter)
        self.event_status: str | None = self.bot.event_status
        self._msgs: list = []
        self.q: asyncio.Queue | None = None
        self.close: bool = False
        self.event_loop: asyncio.BaseEventLoop | None = None
        self.tasks: List = []
        self.socket_tasks: List = []
        self.consumer_tasks: List = []
        self.socket: JockmktSocketManager | None = None

    async def _error_handler(self):
        await self.socket.reconnect()

    async def cancel_tasks(self):
        self.tasks.extend(self.consumer_tasks)
        for task in self.tasks:
            if task.cancelled() or task.done():
                continue
            try:
                task.cancel()
                cancelled = task.cancelled()

                while not cancelled:
                    cancelled = task.cancelled()
                    done = task.done()
                    if done:
                        self.bot.logger.info(f'{task.get_coro().__name__} done.')
                        break
                    self.bot.logger.info(f'Waiting for cancellation of {task.get_coro().__name__}.')
                    await asyncio.sleep(1)
            except asyncio.exceptions.CancelledError:
                self.bot.logger.info(f'cancelled {task.get_coro().__name__}')

    async def shut_down(self):
        self.bot.logger.info('Shutting down.')
        await self.ask_exit()

    async def ask_exit(self):
        await self.cancel_tasks()
        logging.info('Successfully canceled tasks.')
        self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        while self.event_loop.is_running():
            logging.info('Waiting for loop to stop.')
            await asyncio.sleep(1)
        # self.event_loop.close()

    def cancel_consumers(self):
        for consumer in self.consumer_tasks:
            consumer.cancel()

    async def ipo_loop(self):
        self.bot.logger.info(f'Currently in: IPO, status: {self.bot.event_status}')
        await asyncio.sleep(15)
        await self.create_consumers()
        self.bot.ipo_trade_loop()
        if self.bot.event_status == 'ipo_closed':
            await asyncio.sleep(60)
            self.event_status = self.bot.client.get_event(self.strategy.config.event_id).status

    async def ipo_closed_loop(self):
        self.bot.logger('Currently in: IPO Closed')
        await asyncio.sleep(3)
        await self.create_consumers()
        evt = self.client.get_event(self.strategy.config.event_id).status
        self.event_status = evt

    async def live_loop(self):
        await asyncio.sleep(0)
        await self.create_consumers()

    def scheduled_loop(self):
        """not working"""
        self.bot.logger.debug('Sleeping until ipo open')
        ipo_start = self.client.get_event(self.strategy.config.event_id).ipo_start
        sleep_time = round((ipo_start / 1000) - time()) + 1
        self.bot.logger.debug(f'sleeping for {sleep_time}')
        while sleep_time > 1800:
            sleep(1800)
            sleep_time = round((ipo_start / 1000) - time()) + 1
        sleep(sleep_time)

    async def create_consumers(self):
        self.consumer_tasks = [asyncio.create_task(self.bot.consumer()) for _ in range(12)]
        await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
        self.cancel_consumers()

    async def bot_loop(self):
        """
        :return:
        """
        subscriptions = [
            {'endpoint': 'account'},
            {'endpoint': 'event',
             'event_id': self.strategy.config.event_id},
            # {'endpoint': 'event_activity',
            #  'event_id': self.strategy.config.event_id}
        ]
        self.socket = await self.client.ws_connect_new(self.event_loop, self._msgs, self._error_handler, subscriptions,
                                                       self.q.put)
        task = self.socket.conn
        self.tasks.append(task)
        self.bot.set_queue(self.q)
        signal = self.strategy.on_start(self.bot)
        if signal:
            self.bot.parse_signal(signal)
        self.bot.logger.info('Strategy on_start completed.')
        while not self.close:
            if not round(time(), 4) % 30:
                self.bot.logger.debug(f'Receiving...')
            if self.event_status == 'scheduled':
                if self.close:
                    return
                self.scheduled_loop()

            elif self.event_status == 'ipo':
                if self.close:
                    return
                await self.ipo_loop()
            elif self.event_status == 'ipo_closed':
                if self.close:
                    return
                await self.ipo_closed_loop()
            elif self.event_status == 'live':
                if self.close:
                    return
                await self.live_loop()
            elif self.event_status == 'live_closed':
                if self.close:
                    return
                self.bot.logger.info('Event closed. Halting trading.')
                ### ADD AN EXCEPTION HERE SO THAT WE CAN SHUT DOWN
                await self.shut_down()

            else:
                if self.close:
                    return
                self.bot.logger.error('Event is closed. Cannot start an instance of the JockBot')
                self.close = True
                await self.shut_down()

    def run_bot(self):
        self.event_loop = asyncio.new_event_loop()
        self.q = asyncio.Queue()
        self.tasks.append(asyncio.ensure_future(self.bot_loop(), loop=self.event_loop))
        self.event_loop.run_forever()

class JockBotException(Exception):
    def __init__(self, code, title, message):
        self.code = code
        self.title = title
        self.message = message

    def __repr__(self):
        return '{}: {} {}'.format(self.title, self.code, self.message)

    def __str__(self):
        return '{}: {} {}'.format(self.title, self.code, self.message)
