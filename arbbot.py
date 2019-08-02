import threading
import time
import asyncio
from random import randint

import predictit as pi
import piws

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
        self.position = (0, 0)

    async def _handle_wait_for_arb(self, orderbook):
        async with self.state_lock:
            self.state = ArbBot.STATE_WAIT_FOR_ARB

        best_ask = orderbook.asks[0][0]
        best_bid = orderbook.bids[0][0]
        print(f'best ask: {best_ask}, best bid: {best_bid}')
        if best_ask - best_bid >= 3:
            print(f'hit arb opportunity: a:{best_ask}, b: {best_bid}')
            vol = 15
            self.buy_position = (best_bid+1, vol)
            self.sell_position = (best_ask-1, vol)
            await self.buy_shares((best_bid+1, vol))
            
    async def _handle_waiting_for_purchase(self, buy_trade, sell_trade):
        pass

    # I think a queueing system may be necessary to maintain order and make sure things
    # happen in a timely manner
    async def handle_orderbook_change(self, orderbook_event):
        # Example of checking state
        if self.state == ArbBot.STATE_WAIT_FOR_ARB:
            print('Waiting for arb')
            await self._handle_wait_for_arb(orderbook_event)
            # Make a purchase if arb exists
        elif self.state == ArbBot.STATE_WAITING_FOR_PURCHASE:
            print('waiting for purchase')
        elif self.state == ArbBot.STATE_WAITING_FOR_SALE:
            print('waiting for sale')

    # Log in orderbook
    async def buy_shares(self, buy_order):
        '''Purchase shares on predictit according to buy_order,
        and list at strike_price.
        '''
        async with self.state_lock:
            self.state = ArbBot.STATE_WAITING_FOR_PURCHASE

        print(f'submitted order: {buy_order}')
        # Ideally, this would be async
        resp = self.p.buy(self.contract_id, *buy_order)

    async def sell_shares(self, sell_order):
        async with self.state_lock:
            self.state = ArbBot.STATE_WAITING_FOR_SALE

        print('Selling shares!')
        resp = self.p.sell(self.contract_id, *sell_order)

    async def handle_contract_update(self, update):
        async with self.state_lock:
            if self.state == ArbBot.STATE_WAITING_FOR_PURCHASE and self.contract_id == update.contract_id:
                if update.open_buy_orders == 0:
                    print('Finally bought shares!')
                    self.sell_shares(self.sell_position)
                else:
                    print(f'Still waiting on: {update.open_buy_orders}')
            elif self.state == ArbBot.STATE_WAITING_FOR_SALE and self.contract_id == update.contract_id:
                if update.open_sell_orders == 0:
                    print('Finally sold shares!')
                    self.state = ArbBot.STATE_WAIT_FOR_ARB
                else:
                    print(f'Still waiting for {update.open_sell_orders} to sell.')

    async def handle_event(self, event):
        if type(event) == piws.OrderbookEvent:
            print('Orderbook event!')
            await self.handle_orderbook_change(event)
        elif type(event) == piws.ContractOwnershipUpdateEvent:
            print('Ownership update!')
            await self.handle_contract_update(event)

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
    bot = ArbBot('16684')
    ws.set_queue_callback(bot.handle_event)
    #ws.set_queue_callback(queue_cb)
    asyncio.run(ws.start())
    
if __name__ == '__main__':
    main()
