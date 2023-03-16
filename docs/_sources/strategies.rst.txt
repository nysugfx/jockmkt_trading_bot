.. _strategies:
==========
Strategies
==========

.. strategies introduction_

Strategy Introduction
=====================

- The user can implement any of the included strategies, or build their own.
- ``Strategy`` classes have a ``StrategyConfig`` class. All custom strategies and strategy configs inherit their respective base classes.

Initializing a strategy and running it
======================================

.. code-block:: python

    strategy_config = StrategyConfig()
    # edit and adjust aspects of the config
    strategy_config.log_level = 10 # Debug mode
    strategy_config.event_id = 'evt_xxx'

    strategy = Strategy(strategy_config)

    jockbot.trade_strategy(strategy)


Prebuilt Strategies
===================

See :ref:`prebuilt_strategies`

- IPO:
    - :ref:`heat_check`
        - Based off of historical data, decide if you want to go long or short on a player who is performing above, below, or at their projections.
    - :ref:`random_strategy`
        - Buy N random players.
    - :ref:`short_top_long_bottom`
        - Short all of the expensive players over a certain price and long anyone below a certain price.

- LIVE:
    - :ref:`short_early`
        - Short players that score a lot of fantasy points early in an event
    - :ref:`dump_late`
        - Sell players who are likely to pay out less than their current best bid, once their game is complete.
        - Buy players who are likely to pay out more than their current ask, once their game is complete.
    - :ref:`market_maker`
        - Make a market on a single player.


Custom Strategies
=================

See :ref:`custom_strategies`



