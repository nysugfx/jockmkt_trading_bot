import logging
import time
from http.server import HTTPServer
from jockmkt_sdk.client import Client
from jockmkt_sdk.exception import JockAPIException
from jockbot.bot import JockBotException
from jockbot.server import Server
from jockbot.bot import BotThreadRunner, EnvOrderCt
from jockbot.strategy_base import Strategy
import asyncio
from threading import Thread
from sys import exit, version_info
from functools import partial
from typing import List
import webbrowser
import pyfiglet

from strategies.live.dump_late import DumpLateConfig, DumpLate
from strategies.ipo.heat_check import HeatCheckConfig, HeatCheck, HeatCheckStrategies
from strategies.live.harv_beat import HBStrategy, HBConfig


def trade_strategy(strategy: Strategy, counter=EnvOrderCt()):
    """
    Trade a single strategy

    :param strategy: An initialized strategy

    """
    handler = partial(Server, Client(strategy.config.secret_key, strategy.config.api_key), strategy.config.event_id)
    major_version, minor_version = version_info[0], version_info[1]
    if major_version != 3 or minor_version < 10:
        raise OSError('Please ensure that you have python >= 3.10')
    httpd = HTTPServer((strategy.config.host_name, int(strategy.config.port)), handler)
    print(time.asctime(), f'Server UP - {strategy.config.host_name}:{strategy.config.port}')

    if strategy.config.web_popup:
        print('Available server endpoints: \n'
              f'{strategy.config.host_name}:{strategy.config.port}/pnl - information about event PNL\n'
              f'{strategy.config.host_name}:{strategy.config.port}/holdings - information about holdings')
        webbrowser.open_new_tab(f'{strategy.config.host_name}:{strategy.config.port}/pnl')
        webbrowser.open_new_tab(f'{strategy.config.host_name}:{strategy.config.port}/holdings')

    tr = None
    new_thread = None
    try:
        tr = BotThreadRunner(strategy, counter)
        # CATCH EXCEPTIONS THAT MAY OCCUR WHEN INITIALIZING THE JOCKBOT OR THE THREADRUNNER.
        # We need to catch these exceptions, so we can close our server.
    except JockBotException as jbe:
        httpd.server_close()
        print(f'\n{jbe} \n')
        exit(1)

    except JockAPIException as jae:
        httpd.server_close()
        print(f'\n{jae} \n')
        exit(1)

    except Exception as e:
        httpd.server_close()
        print(f'\nUknown exception: {e}\n')
        exit(1)

    try:
        if tr:
            new_thread = Thread(target=tr.run_bot)
            new_thread.start()
            httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.shutdown()
    asyncio.run(tr.shut_down())

    httpd.server_close()
    if new_thread:
        if new_thread.is_alive():
            new_thread.join()
            print("bots closed")
    print(time.asctime(), f'Server DOWN - {strategy.config.host_name}:{strategy.config.port}')
    exit(0)


def trade_multiple_strategies(strategy_list: List[Strategy]):
    """
    Run multiple strategies on a single or multiple different events

    :param strategy_list: A list of initialized strategies

    """
    last_port_number = 0
    threads = {}
    counter = EnvOrderCt()
    try:
        for i, strategy in enumerate(strategy_list, 1):
            print('last_port_number', last_port_number, 'strategy.config.port', strategy.config.port)
            if last_port_number == int(strategy.config.port):
                strategy.config.port = int(strategy.config.port) + 1
                print('changed to', strategy.config.port)
            strategy.config.strategy_id = i
            t = Thread(target=trade_strategy, args=[strategy, counter])
            t.start()
            threads[f'tr{i}'] = t
            last_port_number = strategy.config.port
    except KeyboardInterrupt:
        pass

    for key, thread in threads.items():
        if thread.is_alive():
            thread.join()


if __name__ == "__main__":
    print(pyfiglet.figlet_format(text='JockBot', font='univers'))
    # # set your keys here or in your system environment variables
    # os.environ['secret_key'] = 'enter_your_secret_key_here'
    # os.environ['api_key'] = 'enter_your_api_key_here'

    # initialize and customize your strategy config
    my_strat_config1 = HBConfig()
    # my_strat_config1.strategy = 1
    my_strat_config1.log_level = logging.DEBUG
    my_strat_config1.order_size = 1
    my_strat_config1.event_id = 'evt_640ff14380a6b6c64d2fa277ea804b76'
    my_strat_config1.web_popup = True

    cf2 = HBConfig()
    cf2.order_size = 1
    cf2.event_id = 'evt_640ff14380a6b6c64d2fa277ea804b76'

    trade_multiple_strategies([HBStrategy(my_strat_config1), HBStrategy(cf2)])
