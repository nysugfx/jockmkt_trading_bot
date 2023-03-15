import os
import unittest.mock

import pytest
import sys
sys.path.insert(1, '..')
from jockbot.controllers.pnl_calc import pnl_calc
from jockbot.controllers import holdings
from jockmkt_sdk.objects import *
from jockmkt_sdk.client import Client
from jockbot.bot import JockBot, EnvOrderCt
from jockbot.signals import OrderSignal
from unittest.mock import patch
from jockbot.strategy_base import Strategy, StrategyConfig

_test_api_key = "jm_key_xxx"
_test_secret_key = "xxx"

long_pos = Position(
    {'tradeable_id': 'tdbl_xx1',
     'event_id': 'evt_xxx',
     'bought_count': 10,
     'sold_count': 5,
     'buy_interest': 0,
     'sell_interest': 0,
     'quantity': 5,
     'cost_basis': 50,
     'proceeds': 0,
     'cost_basis_all_time': 75,
     'proceeds_all_time': 50}
)

short_pos = Position(
    {'tradeable_id': 'tdbl_xx2',
     'event_id': 'evt_xxx',
     'bought_count': 0,
     'sold_count': 5,
     'buy_interest': 0,
     'sell_interest': 0,
     'quantity': -5,
     'cost_basis': 0,
     'proceeds': 25,
     'cost_basis_all_time': 0,
     'proceeds_all_time': 50}
)

mock_my_orders = {
    'ord_xx1': Order(
        {
            'cost_basis': 125,
            'side': 'buy'
        }
    ),
    'ord_xx2': Order(
        {
            'proceeds': 50,
            'filled_quantity': 10,
            'side': 'sell'
        }
    )
}

mock_my_holdings = {
    'tdbl_xx1': long_pos,
    'tdbl_xx2': short_pos
}

mock_max_spend_order_success = Order(
    {
        'quantity': 5,
        'limit_price': 10,
    })

mock_max_spend_order_fail = Order(
    {
        'quantity': 5,
        'limit_price': 25,
    })

mock_max_spend_order_short = Order(
    {
        'quantity': 5,
        'limit_price': 10,
    })

mock_max_pos_order_long = OrderSignal(order={'tradeable_id': 'tdbl_xx1',
                                       'quantity': 4,
                                       'price': 20,
                                       'side': 'sell'})
mock_max_pos_order_short = OrderSignal(order={'tradeable_id': 'tdbl_xx2',
                                        'quantity': 6,
                                        'price': 4,
                                        'side': 'sell'})

mock_order_queue = [
        OrderSignal({
            'tradeable_id': 'tdbl_xxx',
            'price': 10.00,
            'quantity': 3,
            'side': 'buy'}),
        OrderSignal({
            'tradeable_id': 'tdbl_xxx',
            'price': 9.00,
            'quantity': 3,
            'side': 'buy'}),
        OrderSignal({
            'tradeable_id': 'tdbl_xxx',
            'price': 11.00,
            'quantity': 3,
            'side': 'buy'})
    ]

mock_open_orders = [
    Order({
        'tradeable_id': 'tdbl_xxx',
        'quantity': 3,
        'limit_price': 11})
]
class MockEntry:
    def __init__(self, event_id, event_name, profit, leaderboard_pos):
        self.event_id = event_id
        self.event_name = event_name
        self.profit = profit
        self.leaderboard_pos = leaderboard_pos



class MockEvent:
    def __init__(self, event_id, name):
        self.event_id = event_id
        self.name = name
        self.status = 'ipo'
        self.league = 'nba'
        self.tradeables = []
        self.games = []
        self.type = 'market'


class MockOrder:
    def __init__(self, order_id, fee_paid):
        self.order_id = order_id
        self.fee_paid = fee_paid
class MockClient:

    def get_account_bal(self):
        return [{'currency': 'curr_xxx', 'buying_power': 1000}]

    def get_positions(self):
        return []
    def get_entries(self, limit=100):
        return [MockEntry(1, 'Event 1', 200, 2), MockEntry(2, 'Event 2', 150, 1)]

    def create_entry(self, arg1, arg2=None):
        return 'success'

    def get_event(self, event_id):
        return MockEvent(event_id, f'Event {event_id}')

    def get_orders(self, event_id, active=False, start=0):
        if event_id == 1 and start == 0:
            return [MockOrder(1, 20), MockOrder(2, 10)]
        elif event_id == 2 and start == 0:
            return [MockOrder(3, 15)]
        else:
            return []

class JockBotTest(unittest.TestCase):
    os.environ['api_key'] = 'test_api_key'
    os.environ['secret_key'] = 'test_secret_key'
    strategy_config = StrategyConfig()
    strategy_config.event_id = 'evt_xxx'
    strategy_config.strategy_id = 1

    mock_bot: JockBot = JockBot(MockClient(), Strategy(strategy_config), EnvOrderCt())

    def test_get_spend(self):
        self.mock_bot.my_orders = mock_my_orders
        print(self.mock_bot.my_orders)

        implied_spend = 475
        self.assertEqual(implied_spend, self.mock_bot.get_total_spend())

    def test_get_max_spend(self):
        self.mock_bot.strategy.config.max_spend = 500
        self.mock_bot.spent = 400
        res1 = self.mock_bot.check_max_spend(mock_max_spend_order_success)
        res2 = self.mock_bot.check_max_spend(mock_max_spend_order_fail)
        res3 = self.mock_bot.check_max_spend(mock_max_spend_order_short)
        self.assertFalse(res1)
        self.assertTrue(res2)
        self.assertFalse(res3)

    def test_get_max_pos_size(self):
        self.mock_bot.strategy.config.max_position = 10
        self.mock_bot.holdings = mock_my_holdings
        res1 = self.mock_bot.check_max_pos_size(mock_max_pos_order_long)
        res2 = self.mock_bot.check_max_pos_size(mock_max_pos_order_short)
        print(res1, res2)
        self.assertFalse(res1)
        self.assertTrue(res2)

    def test_check_sufficient_funds(self):
        self.mock_bot.balance = 100
        print('mock', mock_max_pos_order_long.limit_price)
        res1 = self.mock_bot.check_sufficient_funds(mock_max_pos_order_long)
        res2 = self.mock_bot.check_sufficient_funds(mock_max_pos_order_short)
        self.assertTrue(res1)
        self.assertFalse(res2)

    @patch('jockbot.bot.JockBot.parse_open_orders_for_targets')
    def test_get_target_holdings(self, parse_open_orders_for_targets_mock):
        parse_open_orders_for_targets_mock.return_value = mock_open_orders
        self.mock_bot.order_queue = mock_order_queue
        res = self.mock_bot.get_target_holdings()
        expected_order = {'tdbl_xxx':
                            {'avg_price': 9.5,
                             'total': 57.0,
                             'qty': 6}
                          }

        self.assertEqual(res, expected_order)


#
# class MockClient:
#     def get_entries(self):
#         return {
#             '1': MockEntry(1, 'Event 1', 200, 2),
#             '2': MockEntry(2, 'Event 2', 150, 1)
#         }
def test_pnl_calc():
    # Create a mock client object that returns fake data

    client = MockClient()

    print(client.get_entries()[0].event_id)

    # Test the function with different inputs
    result = pnl_calc(client, 1)
    assert result == {'event_id': 1, 'event_name': 'Event 1', 'leaderboard_position': 2, 'pnl_w_fees': 200,
                      'fees_paid': 30, 'net_profit': 170}

    result = pnl_calc(client, 2, order_count=False)
    assert result == {'event_id': 2, 'event_name': 'Event 2', 'leaderboard_position': 1, 'pnl_w_fees': 150,
                      'fees_paid': 15, 'net_profit': 135}


def test_calc_profits():
    holding = Position({
        'proceeds': 100,
        'quantity': 10,
        'proceeds_all_time': 150,
        'cost_basis_all_time': 50,
        'cost_basis': 80, }
    )
    est_price = 10
    expected_output = {
        'total_cost': 81.6,
        'avg_cost': 8.16,
        'total_profit': 18.4,
        'profit_per_share': 1.84,
        'realized_profit': 100,
        'qty': 10,
        'current_price': 10
    }
    assert holdings.calc_profits(holding, est_price) == expected_output
