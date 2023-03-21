

Welcome to the JockBot
======================

The aim of the ``JockBot`` is to allow a user to easily implement and edit electronic trading strategies. All of the websocket and data storage and organization structure is handled, and so the user just needs to build a strategy class that has signal generating functions. There are multiple included strategies for both IPO and Live trading phases. The creator of this repo advises that users test on risk-free events before trading in cash markets. Use at your own risk.

Docs
====

`Jockbot Documentation <https://nysugfx.github.io/jockmkt_trading_bot/index.html>`_

Getting Started
===============

1. Clone this repo to your machine (**Ensure you have Python >= 3.10**)

2. Navigate to the folder and run the following commands in your terminal:

- ``pip install -r requirements.txt``

3. Set your environment variables, using either the terminal or your IDE. You can set these in the config, if necessary.

- Necessary environment vars:
    - **api_key** - your jockmkt api key
    - **secret_key** - your jockmkt secret key
    - **log_path** - where you want to store logs, defaults to './'
    - **log_level** - logging level, corresponding with python logging package levels. Defaults to 10 (``logging.DEBUG``)

- Setting Env Vars
    - bash:
        - ``export var_name=value``
    - python:
        - ``os.environ['var_name'] = value``
- You can set these in the ``StrategyConfig``, if necessary.

4. Open ``main.py``, and trade! (

.. code-block:: python

    # Import your strategy
    from jockbot.strategies.ipo.random_strategy import RandomStrategy, RandomConfig
    ...

    if __name__ == '__main__':
        # initialize your strategy config
        config = random_strategy.RandomConfig()
        # set event id
        config.event_id = 'evt_xxx'
        # adjust your config parameters. See StrategyConfig docs for info
        # e.g.
        config.order_size = 1
        trade_strategy(RandomStrategy(config))

- Setting your ``StrategyConfig``
    - **event_id**: the event id for the event in which you want to trade
    - **order_size**: optional, the number of shares per order. Some included strategies will allow you to
    - **array_len**: length of numpy array storing historical websocket data. Useful if you are using moving averages, etc.
    - **always_update**: whether you want to update array when there is no new information
    - **message_consumers**: number of async message consumers you want. Defaults to 12, more may be necessary for large events.
    - **phase**: a list containing one or both of 'live', 'ipo'
    - **log_level**: logging levels in accordance with python `logging <https://docs.python.org/3/howto/logging.html#logging-levels>`_ package.
    - **log_path**: where the user wants to store logs in /log folder. Defaults to current directory
    - **max_spend**: maximum dollar amount the user wants to invest in this event
    - **max_position**: maximum shares of a player the user wants to own. The jockbot will never buy more than this number of any one player.
    - **print_to_console**: whether or not to print log messages to console.

5. Observe performance
    - Monitor your strategy!
    - `Profit and Loss <localhost:8080/pnl>`_ (http://localhost:8080/pnl)
    - `Holdings <localhost:8080/holdings>`_ (http://localhost:8080/holdings)


EXAMPLES
========

**trading an ipo event**

.. code-block:: python

    from strategies.ipo.heat_check import HeatCheck, HeatCheckConfig, HeatCheckStrategies

    ...

    if __name == '__main__':
        strategy_config = HeatCheckConfig()
        strategy_config.strategy_id = HeatCheckStrategies.short_hot
        strategy_config.phase = ['ipo']
        strategy_config.dollar_size = 50  # buy $50 worth of shares
        strategy_config.event_id = 'evt_xxx'
        strategy_config.risk = 0.1  # a little risk
        strategy_config.window = 5  # set the window for the rolling average to 5 games.
        trade_strategy(strategy=HeatCheck(strategy_config))


**trade a live event**

.. code-block:: python

    from strategies.live.dump_late import DumpLate, DumpLateConfig

    ...

    if __name__ == "__main__":

        # # set your keys here or in your system environment variables
        # os.environ['secret_key'] = 'enter_your_secret_key_here'
        # os.environ['api_key'] = 'enter_your_api_key_here'

        # initialize and customize your strategy config
        my_strat_config = DumpLateConfig()
        my_strat_config.log_level = logging.DEBUG
        my_strat_config.order_size = 1
        my_strat_config.event_id = 'evt_64017ed1f5b9a22156cdcc997428ff3a'
        my_strat_config.web_popup = True

        trade_strategy(strategy=DumpLate(my_strat_config))

**trading multiple events**

.. code-block:: python


    from strategies.ipo.random_strategy import RandomStrategy, RandomConfig
    from strategies.live.short_early import ShortEarly, ShortEarlyConfig

    ...

    if __name__ == "__main__":

        # # set your keys here or in your system environment variables
        # os.environ['secret_key'] = 'enter_your_secret_key_here'
        # os.environ['api_key'] = 'enter_your_api_key_here'

        # initialize and customize your strategy config
        my_strat_config1 = RandomConfig()
        my_strat_config1.log_level = logging.INFO  # USING ENUM from logging package is recommended here.
        my_strat_config1.order_size = 1
        my_strat_config1.event_id = 'evt_63fd8a52480aa200d14b34c2eb6a1006'

        # initialize and customize your strategy config
        my_strat_config2 = ShortEarlyConfig()
        my_strat_config2.log_level = logging.DEBUG
        my_strat_config2.order_size = 10
        my_strat_config2.event_id = 'evt_63fd8a52122b3c666fc4ea461fb6c839'


        jockbot.trade_multiple_strategies(strategy_list=[
            RandomStrategy(my_strat_config1),
            ShortEarly(my_strat_config2),
            ])
