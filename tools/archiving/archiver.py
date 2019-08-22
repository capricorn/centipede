import asyncio

import piws
import predictit as pi

fifo = []
orderbook_delta = {}



# Should return the average trade price and quantity.
# If it's a sale, the quantity will be negative
# Average trade price is necessary since the purchase may span several
# price levels
class Orderbook():
    # Maybe a named tuple would be better in this case
    '''
    class Order():
        def __init__(self, price, quantity):
            self.price = price
            self.quantity = quantity
    '''

    def __init__(self, bids, asks):
        self.buy_orders = { str(p) : q for p,q in bids }
        self.sell_orders = { str(p) : q for p,q in asks }

class OrderbookDelta():
    def __init__(self, ob):
        self.prev_book = ob
        self.curr_book = ob

    def update(self, book):
        self.prev_book = self.curr_book
        self.curr_book = book

    def get_changes(self):
        changes = []
        for level in self.prev_book.buy_orders:
            if level not in self.curr_book.buy_orders:
                changes.append((level, self.prev_book.buy_orders[level]))
            elif level in self.curr_book.buy_orders and self.prev_book.buy_orders[level] != self.curr_book.buy_orders[level]:
                changes.append((level, self.prev_book.buy_orders[level] - self.curr_book.buy_orders[level]))

        for level in self.prev_book.sell_orders:
            if level not in self.curr_book.sell_orders:
                changes.append((level, self.prev_book.sell_orders[level]))
            elif level in self.curr_book.sell_orders and self.prev_book.sell_orders[level] != self.curr_book.sell_orders[level]:
                changes.append((level, self.prev_book.sell_orders[level] - self.curr_book.sell_orders[level]))
        return changes

def find_order_quantity(delta):
    changes = delta.get_changes()
    if changes == []:
        return 'No change'
    prices = list(map(lambda k: float(k[0]), changes))
    quantity = sum(map(lambda k: int(k[1]), changes))

    return (sum(prices) / len(prices), quantity)
     

# Instead, utilize market stats
async def callback(event):
    global fifo
    global orderbook_delta
    # Making an assumption that orderbook events will at least arrive in order
    # To do this, we need the previous orderbook, and current orderbook
    '''
    if type(event) == piws.ContractStatsEvent:
        print(f'{event.contract_id}, {event.timestamp}, {event.last_trade_price}')
        fifo.append(event)
    elif type(event) == piws.OrderbookEvent:
        if fifo != []:
            stats = fifo.pop(0)
            if event.contract_id in orderbook_delta:
                orderbook_delta[event.contract_id].update(Orderbook(event.bids, event.asks))
                print(f'Change: {find_order_quantity(orderbook_delta[event.contract_id])}')
            else:
                orderbook_delta[event.contract_id] = OrderbookDelta(Orderbook(event.bids, event.asks))
    '''
    if type(event) == piws.OrderbookEvent:
        print(f'{event.contract_id}: Orderbook event')
    # Implement market status event here

if __name__ == '__main__':
    p = pi.PredictItAPI('5782')
    p.authenticate('../../auth.txt')
    contracts = p.get_market_contract_ids()
    print(contracts)
    #for c in contracts:
    #    orderbook_delta[c] = {}
    ws = piws.PredictItWebSocket()
    ws.contracts = contracts
    ws.set_queue_callback(callback)
    ws.set_contract_stats_filter(lambda contract: contract not in contracts)
    asyncio.run(ws.start())
