import threading
import time
import asyncio
import logging
import sys
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
        # our current market position, price and quantity
        self.position = (0,0)
        self.strike_price = 0
        # tracks the shares we own, and the price we paid for them
        self.portfolio = (0,0)
        self.trade_id = 0

    def _handle_wait_for_arb(self, orderbook):
        #async with self.state_lock:
        self.state = ArbBot.STATE_WAIT_FOR_ARB

        best_ask = orderbook.asks[0][0]
        best_bid = orderbook.bids[0][0]
        logging.info(f'best ask: {best_ask}, best bid: {best_bid}')
        if best_ask - best_bid >= 3:
            logging.info(f'Hit arb opportunity: a: {best_ask}, b: {best_bid}')
            vol = 15
            self.position = (best_bid+1, vol)
            #self.sell_position = (best_ask-1, vol)
            self.strike_price = best_ask-1
            resp = self.buy_shares((best_bid+1, vol))
            self.trade_id = resp['offer']['offerId']

    # Adjust the sale, either to a different price level, or by liquidating our position
    def _handle_cancel_sale(self, orderbook_event):
        #self.state = ArbBot.STATE_CANCEL_SALE

        best_ask_price, best_ask_quantity = orderbook_event.asks[0]
        best_bid_price, best_bid_quantity = orderbook_event.bids[0]
        logging.info(f'Cancelling and adjusting sale: {(self.strike_price, self.position[1])}')
        # Need to make sure that the trade_id is set correctly after selling
        logging.info(f'Cancelled: {self.p.cancel(self.trade_id)}')
        if best_ask_quantity <= 25:
            self.position = ((best_ask_price, self.position[1]))
            logging.info(f'Sold at new position: {self.position}')
        else:
            # Liquidate
            # Need to split among all price levels in the future. For now, list at best buy price
            self.position = (best_bid_price, self.position[1])
            logging.info(f'Liquidated shares at position: {self.position}')

        self.sell_shares(self.position)
        self.state = ArbBot.STATE_WAITING_FOR_SALE
            
    # Needs knowledge of our current position (and contract portfolio)
    # Uncertain whether a state is necessary for this; we either cancel
    # immediately, and hence our position is reset, or we cancel and sell
    # our purchased shares, which results in a WAITING_FOR_SALE state 
    def _handle_cancel_purchase(self, orderbook_event):
        #async with self.state_lock: 
        self.state = ArbBot.STATE_CANCEL_PURCHASE

        # Cancel our outstanding order, and then liquidate any purchased shares
        logging.info(f'Cancelling offer: {self.trade_id}')
        logging.info(f'Order cancelled: {self.p.cancel(self.trade_id)}')
        self.position = (0,0)

        # List our remaining shares at the best ask price
        price, quantity = self.portfolio 
        if quantity > 0:
            sale = (orderbook_event.asks[0][0], quantity)
            logging.info(f'Selling remaining portfolio: {sale}')
            self.sell_shares(sale)
        else:
            self.state = ArbBot.STATE_WAIT_FOR_ARB

    # Handle the orderbook while waiting for a purchase to occur
    # May want to check if our buy order is even open still
    def _handle_waiting_for_purchase(self, orderbook_event):
        #async with self.state_lock:
        self.state = ArbBot.STATE_WAITING_FOR_PURCHASE
        # We have open buy orders; possibly some have succeeded, but not all.
        # If the arb opportunity still exists, then everything is ok. We'll just hold
        # the position. Otherwise, it's time to change our position or begin liquidating.
        bids = orderbook_event.bids
        bid_prices = list(map(lambda k: k[0], bids))
        best_ask, best_ask_quantity = orderbook_event.asks[0]
        best_bid, best_bid_quantity = orderbook_event.bids[0]
        offer, quantity = self.position

        # Two different measures I suppose of bid distance
        # One is the price difference, and the other is the level difference
        #bid_distance = best_bid - offer
        offer_idx = bid_prices.index(offer)   # If it isn't 0, we're not on top of the book

        # Need to make an adjustment if:

        # Maybe look into cumulative volume above us in orderbook, rather than just the
        # best one.
        #if bid_distance > 0 and best_bid_quantity > 50:
        if offer_idx > 0 and sum(bid_prices[:offer_idx]) > 75:
            logging.info('Cancelling position')
            # Does liquidate our position, which has a potential for loss
            self._handle_cancel_purchase(orderbook_event)

    # I think a queueing system may be necessary to maintain order and make sure things
    # happen in a timely manner
    def handle_orderbook_change(self, orderbook_event):
        if self.state == ArbBot.STATE_WAIT_FOR_ARB:
            logging.info('Waiting for arb')
            self._handle_wait_for_arb(orderbook_event)
        elif self.state == ArbBot.STATE_WAITING_FOR_PURCHASE:
            logging.info('Waiting for purchase')
            self._handle_waiting_for_purchase(orderbook_event)
        elif self.state == ArbBot.STATE_WAITING_FOR_SALE:
            # Adjust position if necessary
            logging.info('Waiting for sale')
            self._handle_waiting_for_sale(orderbook_event)

    # Liquidate asset or change price, depending on position ahead of us 
    def _handle_waiting_for_sale(self, orderbook_event):
        self.state = ArbBot.STATE_WAITING_FOR_SALE
        logging.info('Waiting for sale')
        best_ask_price, best_ask_quantity = orderbook_event.asks[0]
        dist = self.strike_price - best_ask_price

        if dist > 0:
            quantity = sum(map(lambda k: k[1], orderbook_event.asks[:dist]))
            if quantity > 150:
                logging.info('Modifying sell order')
                self._handle_cancel_sale(orderbook_event)

    # Log in orderbook
    def buy_shares(self, buy_order):
        '''Purchase shares on predictit according to buy_order,
        and list at strike_price.
        '''
        #async with self.state_lock:
        self.state = ArbBot.STATE_WAITING_FOR_PURCHASE

        logging.info(f'Submitted order: {buy_order}')
        # Ideally, this would be async
        return self.p.buy(self.contract_id, *buy_order)

    def sell_shares(self, sell_order):
        #async with self.state_lock:
        self.state = ArbBot.STATE_WAITING_FOR_SALE

        logging.info('Selling shares')
        resp = self.p.sell(self.contract_id, *sell_order)
        return resp

    def handle_contract_update(self, update):
        if self.state == ArbBot.STATE_WAITING_FOR_PURCHASE and self.contract_id == update.contract_id:
            if update.open_buy_orders == 0:
                # Update portfolio here
                logging.info('Finished buying shares')
                self.trade_id = self.sell_shares((self.strike_price, self.portfolio[1]))['offer']['offerId']
            else:
                self.portfolio = ((self.position[0] - update.open_buy_orders), self.position[1])
                logging.info(f'Still waiting on: {update.open_buy_orders}')
        elif self.state == ArbBot.STATE_WAITING_FOR_SALE and self.contract_id == update.contract_id:
            if update.open_sell_orders == 0:
                # Update portfolio here
                logging.info('Finished selling shares')
                self.portfolio = (0,0)
                self.position = (0,0)
                self.state = ArbBot.STATE_WAIT_FOR_ARB
            else:
                self.portfolio = (update.open_sell_orders, self.portfolio[1])
                logging.info(f'Still waiting for {update.open_sell_orders} to sell.')

    async def handle_event(self, event):
        if type(event) == piws.OrderbookEvent:
            logging.info('Orderbook event!')
            self.handle_orderbook_change(event)
        elif type(event) == piws.ContractOwnershipUpdateEvent:
            logging.info('Ownership update event!')
            self.handle_contract_update(event)
        await asyncio.sleep(.05)

def load_auth():
    with open('auth.txt', 'r') as f:
        return f.read().split()

async def queue_cb(data):
    if type(data) == piws.ContractOwnershipUpdateEvent:
        print(data.contract_id)

    elif type(data) == piws.OrderbookEvent:
        print(data)

def main():
    contract_id = ''
    if len(sys.argv) != 2:
        print('Argument required: contract_id')
        return
    contract_id = sys.argv[1]
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    logging.info('Starting up..')
    ws = piws.PredictItWebSocket()
    ws.init_contract(contract_id)
    bot = ArbBot(contract_id)
    ws.set_queue_callback(bot.handle_event)
    #ws.set_queue_callback(queue_cb)
    try:
        asyncio.run(ws.start())
    except KeyboardInterrupt:
        print('')
        logging.info('Bye.')
        ws.stop()
    
if __name__ == '__main__':
    main()
