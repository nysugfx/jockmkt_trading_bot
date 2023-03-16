.. _trading_examples:

Trading Examples
================

You can try trading single events or multiple events, or trade multiple strategies in a single event. The JockBot includes functionality for all of these.

You should run this from ``main.py``

**Examples**

- trading an ipo event

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


- trade a live event

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

- trading multiple events

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