import threading
import time
import asyncio
from random import randint

import predictit as pi
import piws

# In a sense we really don't want our arbbot to be asynchronous in terms of operating
# in its state. Although the advantage is that we could cancel tasks

# Manage state via various method calls that are passed to websocket
# (and activate if in a given state)
# Maybe a state lock?
# Do we want this to work only for individual contracts, or entire markets?
# Needs to hold its current position as state too
class ArbBot():
    STATE_WAIT_FOR_ARB = 0,
    STATE_WAITING_FOR_PURCHASE = 1,
    STATE_STOP_LOSS = 2,
    STATE_WAITING_FOR_SALE = 3,
    STATE_CANCEL_SALE = 4,
    STATE_CANCEL_PURCHASE = 5

    def __init__(self, contract_id):
        self.state = ArbBot.STATE_WAIT_FOR_ARB
        self.state_lock = asyncio.Lock()
        self.p = pi.PredictItAPI(0).create(*load_auth())
        self.contract_id = contract_id

    '''
    @staticmethod
    def boolean _has_arb(orderbook):
        return False
    '''

    async def _handle_wait_for_arb(self, orderbook):
        async with self.state_lock:
            self.state = ArbBot.STATE_WAIT_FOR_ARB
        # If there's an arb opportunity, change the state to waiting for purchase,
        # and call _handle_wait_for_purchase()

        # Test with a simple 1 q trade, make sure to not purchase when we already have a position
        best_ask = orderbook.asks[0][0]
        best_bid = orderbook.bids[0][0]
        print(f'best ask: {best_ask}, best bid: {best_bid}')
        if best_ask - best_bid >= 3:
            print(f'hit arb opportunity: a:{best_ask}, b: {best_bid}')
            #self.state = ArbBot.STATE_WAITING_FOR_PURCHASE
            #print(f'bought: ({best_bid}, 1)')
            await self.buy_shares((best_bid+1, 1))
            '''
            async with self.state_lock:
                self.state = STATE_WAITING_FOR_PURCHASE
                await self._handle_waiting_for_purchase(orderbook['buy'][0]+1, orderbook['ask'][0]-1)
            '''

    async def _handle_waiting_for_purchase(self, buy_trade, sell_trade):
        pass

    # I think a queueing system may be necessary to maintain order and make sure things
    # happen in a timely manner
    async def handle_orderbook_change(self, orderbook_event):
        # Example of checking state
        if self.state == ArbBot.STATE_WAIT_FOR_ARB:
            await self._handle_wait_for_arb(orderbook_event)
            # Make a purchase if arb exists
        elif self.state == ArbBot.STATE_WAITING_FOR_PURCHASE:
            print('waiting for purchase')
            # Dump purchase if arb opportunity is gone, otherwise do nothing
            '''
            elif self.state == ArbBot.STATE_STOP_LOSS:
                pass
                # Trying to sell an unprofitable order, adjust if necessary
            elif self.state == ArbBot.STATE_WAITING_FOR_SALE:
                pass
                # Switch to a stop loss state if necessary; otherwise do nothing 
            '''

    # Log in orderbook
    async def buy_shares(self, buy_order):
        '''Purchase shares on predictit according to buy_order,
        and list at strike_price.
        '''
        async with self.state_lock:
            self.state = ArbBot.STATE_WAITING_FOR_PURCHASE

        print(f'bought: {buy_order}')
        # Ideally, this would be async
        resp = self.p.buy(self.contract_id, *buy_order)

    async def handle_event(self, event):
        print(event)
        if type(event) == piws.OrderbookEvent:
            print('Orderbook event!')
            await self.handle_orderbook_change(event)

def get_bids(orderbook):
    return list(map(lambda k: (k['pricePerShare'], k['quantity']), orderbook['yesOrders']))

def get_asks(orderbook):
    return list(map(lambda k: (k['costPerShareYes'], k['quantity']), orderbook['noOrders']))

def handle_arb(api, contract_id, arb):
    print(arb)

#def find_arb(api, contract_id, market):
def find_arb(ob):
    #ob = api.get_contract_orderbook(contract_id)
    #print(ob)

    best_ask_price, best_ask_vol = ob['ask'][0]
    best_bid_price, best_bid_vol = ob['bid'][0]

    if best_ask_price - best_bid_price >= 3:
        print(f'b: ({best_bid_vol:3d}@{best_bid_price:2d}c) a: ({best_ask_vol:3d}@{best_ask_price:2d}c)')

    '''
    bids = get_bids(ob)
    asks = get_asks(ob)

    if bids == [] or asks == []:
        return

    bid = bids[0]
    ask = asks[0]
    if int(bid[0] * 100) - int(ask[0] * 100) >= 3:
        #print(f'[{market.contracts[contract_id]["name"]}] b: {bid[0]} a: {ask[0]}')
        print(f'[b: {bid[0]} a: {ask[0]}')
        #handle_arb(api, contract_id, (bid, ask))
    '''

async def run_queue(q):
    while True:
        data = await q.get()

def load_auth():
    with open('auth.txt', 'r') as f:
        return f.read().split()

async def queue_cb(data):
    if type(data) == piws.ContractOwnershipUpdateEvent:
        print(data.contract_id)

    elif type(data) == piws.OrderbookEvent:
        print(data)

def main():
    ws = piws.PredictItWebSocket()
    #ws.set_orderbook_change_callback(find_arb)
    #ws.start()
    #asyncio.run(ws.connect_status_feed())
    #async def start():
    #    await asyncio.gather(run_queue(q), ws.feed())

    #q = ws.queue 
    bot = ArbBot('16606')
    ws.set_queue_callback(bot.handle_event)
    #ws.set_queue_callback(queue_cb)
    asyncio.run(ws.start())
    
    '''
    api = pi.PredictItAPI('5715')
    api.authenticate('auth.txt')
    market = pi.Market(api.get_market())

    print(api.get_contract_portfolio('16575'))
    '''
    #resp = api.sell('16575', 40, 1)
    #print(resp)
    '''
    try:
        while True:
            print('Checking for arb opportunities')
            thread_pool = [ threading.Thread(target=find_arb, args=(api, contract_id, market)) for contract_id in 
                api.get_market_contract_ids() ]
            [ t.start() for t in thread_pool ]
            [ t.join() for t in thread_pool ]
            time.sleep(15 + (randint(0,1)*-1)*randint(0,3))
    except KeyboardInterrupt:
        pass
    '''

if __name__ == '__main__':
    main()
