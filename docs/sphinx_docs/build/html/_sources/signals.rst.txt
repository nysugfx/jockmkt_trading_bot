.. _signals:

Signals
=======

.. code-block:: py

    def on_data(tradeable_id, jockbot):

        orders = [{'tradeable_id': tradeable_id,
                   'price': 10.00,
                   'quantity': 3,
                   'side': 'buy'},
                  {'tradeable_id': tradeable_id,
                   'price': 12.00,
                   'quantity': 3,
                   'side': 'sell'}]

        order_ids = list(jockbot.my_orders.keys())

        cancels = order_ids

        signal = Signal(orders, cancels)

        return signal


.. py:currentmodule:: signals

.. autoclass:: Signal