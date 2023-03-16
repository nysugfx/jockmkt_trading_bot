.. _prebuilt_strategies:

Prebuilt Strategies
===================

.. _prebuilt_live_strategies:

Live Strategies
===============

.. _market_maker:

**Market Maker**
    - Makes a market on a single player, with options regarding the spread and order sizes at the bid and ask

.. py:currentmodule:: strategies.live.market_maker

.. autoclass:: MarketMakerConfig

.. _dump_late:

**Dump Late**
    - How it works:

        If a player's game is completed, we know that they will not score any more fantasy points. Their price
        cannot go up unless other players score below their projection. If we have an opportunity to buy a player or sell a player at a profit
        compared to their projected payout, we do so.

.. py:currentmodule:: strategies.live.dump_late

.. autoclass:: DumpLateConfig

.. _short_early:

**Short Early**
    - How it works:

        Once an event has started, we are looking for players who far outperform their projections early on. These players are
        likely to fall back down to earth at some point before the event ends.

        *For example*, in an NFL Sunday slate, if Saquon Barkley gets a 50 yard touchdown in the first 2 minutes of his 1pm game,
        he will be projected for many more points than anyone else. Because of this, his price will be very inflated.
        We should short him! This strategy is also applicable to NBA, and other sports, where a player scores a large chunk of
        points early on in the event.

.. py:currentmodule:: strategies.live.short_early

.. autoclass:: ShortEarlyConfig

.. _prebuilt_ipo_strategies:

IPO Strategies
==============

.. _heat_check:

**Heat Check**
    - How it works:

        There are numerous options for the heat check strategy. See :class:`strategies.ipo.heat_check.HeatCheckStrategies` for details.
        The strategy pulls historical data, calculates a moving average of the player's fantasy points, and compares
        it to their projection for this game, and generates a signal accordingly.

.. py:currentmodule:: strategies.ipo.heat_check

.. autoclass:: HeatCheckStrategies

.. autoclass:: HeatCheckConfig

.. _random_strategy:

**Random Strategy**
    - How it works:

        Buy a percentage of the field at random during the IPO phase

.. py:currentmodule:: strategies.ipo.random_strategy

.. autoclass:: RandomConfig

.. _short_top_long_bottom:

**Short Top, Long Bottom**
    - How it works:

        Short all players whose estimated price is over a certain number, and buy everyone under a certain est price.

.. py:currentmodule:: strategies.ipo.short_top_long_bottom

.. autoclass:: ShortTopLongBottomConfig


