from jockmkt_sdk.client import Client

def pnl_calc(client: Client, event_id: str, pages=3, order_count=False):
    entries = dict((i.event_id, i) for i in client.get_entries())
    print(entries)
    entry = entries[event_id]
    event = client.get_event(event_id)
    pnl_w_fees = entry.profit
    total_fees = 0
    if order_count:
        orders, order_count = client.get_orders(event_id=event_id)
        pages = order_count // 100 + 1
    for i in range(pages):
        total_fees += sum([i.fee_paid for i in client.get_orders(event_id=event_id, start=i)])

    return {
        'event_id': event_id,
        'event_name': event.name,
        'leaderboard_position': entry.leaderboard_pos,
        'pnl_w_fees': round(pnl_w_fees, 2),
        'fees_paid': round(total_fees, 2),
        'net_profit': round(pnl_w_fees - total_fees, 2)
    }


