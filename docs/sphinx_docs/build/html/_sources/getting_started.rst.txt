===============
Getting Started
===============

First...
========
- Step 1:
    - Fork/Clone this GitHub repository to your local machine
    - **Make sure you have Python >= 3.10**

- Step 2:
    - ``pip install -r requirements.txt``
- Step 3:
    - Set the following environment variables (this can be done via terminal or in your IDE):
        - **api_key**
        - **secret_key**
        - **log_path** (defaults to ./)
        - **log_level** (defaults to 10 (debug), 20=info, 30=warning, 40=error, 50=critical) (recommended: 20)
    - Setting env vars with terminal:
        - If using bash:
            - ``export var_name=value``
        - In python:
            - ``os.environ[var_name] = value``
    - You can also just set these values directly in the ``StrategyConfig``, but it is recommended to use env vars to store api keys safely.
- Step 4 (TRADE!):

    - open ``main.py``

.. code-block:: py

    if __name__ == '__main__':
        config = StrategyConfig()
        config.event_id = 'evt_xxx'
        #  adjust other parameters as you would like. See details below.
        strat = Strategy(config)
        trade_strategy(strat)

.. note::

    Replace the strategy import above with one of the prebuilt strategies, or your own!

See :ref:`strategies`: for more information on strategies (custom and prebuilt)

See :ref:`config`: for more information on setting up your config.

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

- Step 5:
    - Monitor your strategy!
    - `Profit and Loss <localhost:8080/pnl>`_
    - `Holdings <localhost:8080/holdings>`_

