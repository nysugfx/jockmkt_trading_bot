.. _custom_strategies:

Building Strategies
===================

The user must build their strategy in the footprint of the :class:`strategy_base.Strategy` class.
The following methods interact with the jockbot. The user is free to build whatever signal generating functions they wish,
but they must return a :class:`signals.Signal` via one of the following methods. See :ref:`signals`

There are methods within the JockBot that allow the user to fetch certain variables from the jockbot too.

.. py:currentmodule:: strategy_base

.. autoclass:: Strategy

.. automethod:: Strategy.on_start

.. automethod:: Strategy.ipo_trade

.. automethod:: Strategy.on_stop

.. automethod:: Strategy.on_data

.. automethod:: Strategy.on_tick

.. automethod:: Strategy.on_order

.. automethod:: Strategy.on_event

.. automethod:: Strategy.on_play

.. automethod:: Strategy.on_trade




.. py:currentmodule:: bot

**Fetch Player Dict with all player data**

.. automethod:: JockBot.fetch_player_dict

**Fetch current balance**

.. automethod:: JockBot.fetch_bal

**Fetch client for use making requests**

.. automethod:: JockBot.fetch_client

**Fetch orders**

.. automethod:: JockBot.fetch_orders

**Fetch Active Holdings**

.. automethod:: JockBot.fetch_holdings

**Fetch Async Queue**

.. automethod:: JockBot.fetch_queue

**Fetch Entry**

.. automethod:: JockBot.fetch_entry

**Fetch Games**

.. automethod:: JockBot.fetch_games

**Fetch Teams**

.. automethod:: JockBot.fetch_teams

