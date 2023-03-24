from jockmkt_sdk.client import Client
from jockmkt_sdk.objects import Position, Entity
from typing import List

def filter_holding(holding: Position, event_id: str):
    return holding.event_id == event_id

def get_holdings(client: Client, event_id: str):
    """
    Still having some problem
    :param client:
    :param event_id:
    :return:
    """
    holdings = client.get_positions()
    event_holdings = []
    for holding in holdings:
        if holding.event_id == event_id:
            event_holdings.append(holding)
    return holdings

def get_current_prices(client: Client, event_id: str):
    return dict((i.tradeable_id, i) for i in client.get_event(event_id).tradeables)

def calc_profits(holding, est_price):
    """
    :param est_price:
    :param holding:
    :return:
    """
    proceeds = holding.proceeds or 0
    qty = holding.quantity_owned

    if holding.proceeds_all_time > 0 and qty >= 0:
        realized_profit = holding.proceeds_all_time - holding.cost_basis_all_time
    else:
        realized_profit = 0
    buy_fees = holding.cost_basis * .02
    sell_fees = holding.proceeds * .02
    current_value = holding.quantity_owned * est_price
    if qty > 0:
        total_cost = holding.cost_basis + buy_fees
        avg_cost = total_cost / qty
        total_profit = current_value - total_cost
        profit_per_share = total_profit / qty
    elif qty < 0:
        total_cost = proceeds + sell_fees
        avg_cost = abs(total_cost / qty)
        total_profit = - total_cost - current_value
        profit_per_share = total_profit / qty
    else:
        total_cost = 0
        avg_cost = 0
        total_profit = 0
        profit_per_share = 0

    return {'total_cost': round(total_cost, 3), 'avg_cost': round(avg_cost, 3), 'total_profit': round(total_profit, 3),
            'profit_per_share': round(profit_per_share, 3), 'realized_profit': round(realized_profit, 3), 'qty': qty,
            'current_price': est_price}


def build_holdings_dict(client: Client, event_id):
    holdings_dict = {}
    event = client.get_event(event_id)
    holdings = get_holdings(client, event_id)
    current_prices = get_current_prices(client, event_id)
    count = len(holdings)
    holdings_dict['event_id'] = event_id
    holdings_dict['event_name'] = event.name
    holdings_dict['event'] = event.__dict__
    holdings_dict['count'] = count
    new_holdings = []
    for holding in holdings:
        tdbl_id = holding.tradeable_id
        holding_dict = calc_profits(holding, current_prices[tdbl_id].estimated)
        entity: Entity = current_prices[tdbl_id].entity
        holding_dict['name'] = entity.name
        holding_dict['image'] = entity.image_url
        holding_dict['tradeable_id'] = tdbl_id
        new_holdings.append(holding_dict)
    holdings_dict['holdings'] = new_holdings
    pnl = round(sum([i['total_profit'] for i in new_holdings]), 2)
    holdings_dict['total_value'] = round(sum([i['total_cost'] for i in new_holdings]) + pnl, 2)
    holdings_dict['pnl'] = pnl
    return holdings_dict





