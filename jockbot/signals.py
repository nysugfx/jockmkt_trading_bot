# order_signal_example = {
#     'order': [
#         {'tradeable_id': 'tdbl_xxx',
#          'price': 10.00,
#          'quantity': 3,
#          'side': 'buy'}
#     ],
#     'cancel': [
#         'ord_xxx',
#         'ord_xxx'
#     ],
# }
#
# cancel_signal_example = {
#     'signal': SIGNALS.CANCEL,
#
# }

class Signal:
    """
    Signal that gets sent to the jockbot

    :param orders: a list of orders that looks as follows:

    .. code-block:: python

            [{'tradeable_id': 'tdbl_xxx',
             'price': 10.00,
             'quantity': 3,
             'side': 'buy'}, ...]

    :param cancel: list of order_id cancels: ``['ord_xx1', 'ord_xx2']``

    """
    def __init__(self, orders, cancels, **kwargs):
        self.order = []
        self.cancel = []

        if orders:
            if type(orders) == dict:
                self.order.append(OrderSignal(orders))

            elif type(orders) == list:
                for order in orders:
                    self.order.append(OrderSignal(order))

        if cancels:
            for cancel in cancels:
                self.cancel.append(CancelSignal(cancel))

class OrderSignal:
    def __init__(self, order):
        self.order_type = order.get('order_type')
        self.tradeable_id = order.get('tradeable_id')
        self.limit_price = order.get('price')
        self.quantity = order.get('quantity')
        self.side = order.get('side')
        self.trigger = order.get('trigger')

class CancelSignal:
    def __init__(self, order_id):
        self.order_id = order_id

class StopLossSignal:
    pass

class TakeProfitSignal:
    pass

