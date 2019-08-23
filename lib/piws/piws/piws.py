import asyncio
import json
import logging
import base64
import time

import websockets
import requests
import predictit as pi

# Check these 
TRADE_TYPE_BUY = 1
TRADE_TYPE_SELL = 3

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

    # Basically, what are the trades that can occur?
    # 1. Someone buys from a seller
    # 2. Someone sells to a buyer
    # Yes, these are different
    def get_changes(self):
        changes = []
        # Here, someone sold to a buyer (that is, somebody successfully bought shares)
        for level in self.prev_book.buy_orders:
            # Here, a price level was bought out
            if level not in self.curr_book.buy_orders:
                changes.append(('bought', int(level), self.prev_book.buy_orders[level]))
            elif level in self.curr_book.buy_orders and self.prev_book.buy_orders[level] != self.curr_book.buy_orders[level]:
                changes.append(('bought', int(level), abs(self.prev_book.buy_orders[level] - self.curr_book.buy_orders[level])))

        for level in self.prev_book.sell_orders:
            if level not in self.curr_book.sell_orders:
                changes.append(('sold', int(level), self.prev_book.sell_orders[level]))
            elif level in self.curr_book.sell_orders and self.prev_book.sell_orders[level] != self.curr_book.sell_orders[level]:
                changes.append(('sold', int(level), abs(self.prev_book.sell_orders[level] - self.curr_book.sell_orders[level])))
        return changes

def find_order_quantity(delta):
    return delta.get_changes()
    changes = delta.get_changes()
    if changes == []:
        return 'No change'
    prices = list(map(lambda k: float(k[0]), changes))
    quantity = sum(map(lambda k: int(k[1]), changes))

    return (sum(prices) / len(prices), quantity)

class MarketStatsEvent():
    def __init__(self):
        self.market_id = ''
        self.status = ''
        self.timestamp = ''
        self.shares_traded = 0

    def __str__(self):
        return f'market id: {self.market_id}\n' \
               f'status: {self.status}\n' \
               f'timestamp: {self.timestamp}\n' \
               f'shares traded: {self.shares_traded}\n'

    class MarketStatsDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            self.stats_event = MarketStatsEvent()
            json.JSONDecoder.__init__(self, object_hook=self.hook, *args, **kwargs)

        def hook(self, data):
            if 'MarketId' in data:
                self.stats_event.market_id = str(data['MarketId'])
            if 'Status' in data:
                self.stats_event.status = data['Status']
            if 'TimeStamp' in data:
                self.stats_event.timestamp = data['TimeStamp']
            if 'TotalSharesTraded' in data:
                self.stats_event.shares_traded = data['TotalSharesTraded']

            return self.stats_event

class ContractStatsEvent():
    def __init__(self):
        self.best_no_price = 0
        self.best_yes_price = 0
        self.contract_id = ''
        self.date_updated = ''
        self.last_close_price = 0
        self.last_trade_price = 0
        self.timestamp = ''

    def __str__(self):
        return \
            f'best no price: {self.best_no_price}\n' \
            f'best yes price: {self.best_yes_price}\n' \
            f'contract id: {self.contract_id}\n' \
            f'date updated: {self.date_updated}\n' \
            f'last_close_price: {self.last_close_price}\n' \
            f'last_trade_price: {self.last_trade_price}\n' \
            f'timestamp: {self.timestamp}\n'

    class ContractStatsDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            self.stats_event = ContractStatsEvent()
            json.JSONDecoder.__init__(self, object_hook=self.hook, *args, **kwargs)

        def hook(self, data):
            #print(data)
            if 'BestNoPrice' in data:
                self.stats_event.best_no_price = data['BestNoPrice']
            if 'BestYesPrice' in data:
                self.stats_event.best_yes_price = data['BestYesPrice']
            if 'ContractId' in data:
                self.stats_event.contract_id = str(data['ContractId'])
            if 'DateUpdated' in data:
                self.stats_event.date_updated = data['DateUpdated']
            if 'LastClosePrice' in data:
                self.stats_event.last_close_price = data['LastClosePrice']
            if 'LastTradePrice' in data:
                self.stats_event.last_trade_price = data['LastTradePrice']
            if 'TimeStamp' in data:
                self.stats_event.timestamp = data['TimeStamp']

            return self.stats_event

# This is actually a trade event, not a status event 
class OrderbookEvent():
    def __init__(self):
        self.bids = []
        self.asks = []
        self.contract_id = 0
        self.timestamp = ''

    def __str__(self):
        return f'contract: {self.contract_id}\n' \
               f'bids: {self.bids}\n' \
               f'asks: {self.asks}'

    class OrderbookEventDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            self.ob_event = OrderbookEvent()
            json.JSONDecoder.__init__(self, object_hook=self.hook, *args, **kwargs)

        def hook(self, data):
            if 'tradeType' in data:
                if data['tradeType'] == 1:  # May be wrong
                    self.ob_event.bids.append((int(data['costPerShareYes']*100), data['quantity']))
                    return self.ob_event
                elif data['tradeType'] == 0:  # May be wrong
                    self.ob_event.asks.append((int(data['costPerShareYes']*100), data['quantity']))
                    return self.ob_event
            if 'p' in data and data['p'].startswith('contractOrderBook'):
                # structure of data['p'] = 'contractOrderBook/\d+'
                self.ob_event.contract_id = data['p'][data['p'].index('/')+1:]
            if 'timestamp' in data:
                self.ob_event.timestamp = data['timestamp']

            return self.ob_event 

class ContractOwnershipUpdateEvent():
    event_message = 'contractOwnershipUpdate_data'

    def __init__(self):
        self.contract_id      = 0
        self.trade_type       = 0
        self.quantity         = 0
        self.open_buy_orders  = 0
        self.open_sell_orders = 0
        self.average_pps      = 0
        self.timestamp        = 0

    class ContractOwnershipUpdateEventDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            self.event = ContractOwnershipUpdateEvent()
            json.JSONDecoder.__init__(self, object_hook=self.hook, *args, **kwargs)

        def hook(self, data):
            if 'ContractId' in data:
                self.event.contract_id = str(data['ContractId'])
            if 'UserPrediction' in data:
                self.event.trade_type = data['UserPrediction']
            if 'UserQuantity' in data:
                self.event.quantity = data['UserQuantity']
            if 'UserOpenOrdersBuyQuantity' in data:
                self.event.open_buy_orders = data['UserOpenOrdersBuyQuantity']
            if 'UserOpenOrdersSellQuantity' in data:
                self.event.open_sell_orders = data['UserOpenOrdersSellQuantity']
            if 'UserAveragePricePerShare' in data:
                self.event.average_pps = data['UserAveragePricePerShare']
            if 'TimeStamp' in data:
                self.event.timestamp = data['TimeStamp']

            return self.event

class PredictItWebSocket():
    def __init__(self):
        self.queue = None
        self.queue_callback = None
        self.feeds = None
        self.ws_token = ''
        self.start_time = 0
        self.p = None
        self.contract = None
        self.req_count = 1
        self.contract_filter = None
        self.market_filter = None
        self.contracts = None
        self.trade_feed_ws = None
        self.status_feed_ws = None
        self.trade_feed_init_msgs = []
        self.status_feed_init_msgs = []
        self.logger = logging.getLogger(__name__)

    def subscribe_contract_orderbook(self, contract_id):
        self.trade_feed_init_msgs.append(self._subscribe_contract_orderbook_msg(contract_id))

    def subscribe_market_status(self):
        self.trade_feed_init_msgs.append(self._subscribe_market_stats_msg())

    def subscribe_contract_status(self):
        self.trade_feed_init_msgs.append(self._subscribe_contract_stats_msg())

    async def connect(self):
        self.trade_feed_ws = await self._connect_trade_feed()
        self.status_feed_ws = await self._connect_status_feed()

    async def _connect_status_feed(self):
        params = {
            'transport': 'webSockets',
            'clientProtocol': 1.5,
            'bearer': self.p.token,
            'connectionToken': self.ws_token,
            'connectionData': '[{"name":"markethub"}]',
            'tid': 9
        }

        req = requests.Request('GET', 'https://www.predictit.org/signalr/connect', params=params).prepare()
        url = 'wss://' + req.url[8:]
        return await websockets.connect(url, ping_interval=None)

    async def run_status_feed(self):
        try:
            while True:
                data = await self.status_feed_ws.recv()
                data = json.loads(data)
                await self.queue.put(self._parse_status_feed(data))
        except websockets.ConnectionClosed:
            self.logger.warning('Lost connection to status feed.')
        except asyncio.CancelledError:
            self.logger.info('Cancelling status feed')

    def _parse_shares_traded_event(self, msg):
        event = SharesTradedEvent()
        event.quantity = msg[1]['Quantity']
        event.trade_type = TRADE_TYPE_BUY if msg[1]['TradeType'] == TRADE_TYPE_BUY else TRADE_TYPE_SELL
        event.price = msg[1]['PricePerShare']
        event.timestamp = msg[1]['TimeStamp']

    def _parse_status_feed(self, msg):
        if 'M' in msg:
            for event in msg['M']:
                if event['A'][0] == ContractOwnershipUpdateEvent.event_message:
                    return json.loads(str(event['A'][1]).replace('\'', '"'), 
                            cls=ContractOwnershipUpdateEvent.ContractOwnershipUpdateEventDecoder)
        return msg

    async def send_trade_feed_message(self, msg):
        await self.trade_feed_ws.send(msg(self.req_count))
        self.req_count += 1

    async def _init_trade_feed(self):
        await self.send_trade_feed_message(self._init_sdk_msg())

        for msg in self.trade_feed_init_msgs:
            await self.send_trade_feed_message(msg)
        
    async def _connect_trade_feed(self):
        params = {
            'v': 5,
            'ns': 'predictit-f497e'
        }

        headers = {
            'Host': 's-usc1c-nss-203.firebaseio.com'
        }

        req = requests.Request('GET', 'https://s-usc1c-nss-201.firebaseio.com/.ws', params=params).prepare()
        url = 'wss://' + req.url[8:]

        return await websockets.connect(url, ping_interval=None)

    async def run_trade_feed(self):
        await self._init_trade_feed()
        
        try:
            while True:
                data = await self.trade_feed_ws.recv()
                event = self._route_trade_data(data)
                if self.contract_filter and type(event) == ContractStatsEvent and self.contract_filter(event.contract_id):
                    continue
                if self.market_filter and type(event) == MarketStatsEvent and self.market_filter(event.market_id):
                    continue
                await self.queue.put(event)
        except websockets.ConnectionClosed:
            self.logger.warning('Lost connection to trade feed.')
        except asyncio.CancelledError:
            self.logger.info('Cancelling trade feed')

    def set_queue_callback(self, callback):
        self.queue_callback = callback

    async def ping(self):
        try:
            while True:
                self.start_time += 1
                self.logger.info(f'Sending ping: {self.start_time}')
                params = {
                    'bearer': self.p.token,
                    '_': self.start_time
                }
                resp = requests.get('https://www.predictit.org/signalr/ping', params=params)
                await asyncio.sleep(60 * 5)
        except asyncio.CancelledError:
            self.logger.info('Cancelling ping task')

    async def _run_queue(self):
        # Maybe use executor here -- turn on asyncio self.logger to check performance
        try:
            while True:
                data = await self.queue.get()
                if self.queue_callback:
                    await self.queue_callback(data)
        except asyncio.CancelledError:
            self.logger.info('Cancelling event queue')

    def _send_start_request(self):
        start = int(time.time())
        params = {
            'transport': 'webSockets',
            'clientProtocol': 1.5,
            'bearer': self.p.token,
            'connectionToken': self.ws_token,
            'connectionData': '[{"name":"markethub"}]',
            '_': start
        }

        resp = requests.get('https://www.predictit.org/signalr/start', params=params)
        return start

    # Takes a filter function of the form [ contract_id: str ] -> bool
    def set_contract_stats_filter(self, contract_filter):
        self.contract_filter = contract_filter

    async def start(self):
        self.p = pi.PredictItAPI(0).create(*load_auth())
        self.ws_token = self.p.negotiate_ws()['ConnectionToken']
        self.start_time = self._send_start_request()
        self.queue = asyncio.Queue()

        await self.connect()
        self.feeds = asyncio.gather(self.run_trade_feed(), self.run_status_feed(), 
                self._run_queue(), self.ping())
        try:
            await self.feeds
        except asyncio.CancelledError:
            self.logger.info('Cancelled all feeds')

    def _route_trade_data(self, data):
        data = json.loads(data)
        if data == {}: return {}
        if 'b' in data['d'] and 'p' in data['d']['b']:
            msg = data['d']['b']['p']
            if msg.startswith('contractOrderBook'):
                event = json.loads(str(data).replace("'", '"') , cls=OrderbookEvent.OrderbookEventDecoder)
                return event
            if msg.startswith('contractStats'):
                return json.loads(str(data).replace("'", '"'), cls=ContractStatsEvent.ContractStatsDecoder)
            if msg.startswith('marketStats'):
                return json.loads(str(data).replace("'", '"'), cls=MarketStatsEvent.MarketStatsDecoder)
        return data

    def set_market_filter(self, mfilter):
        self.market_filter = mfilter

    def stop(self):
        self.logger.info('Closing feeds')
        self.trade_feed_ws.close()
        self.status_feed_ws.close()

    def _subscribe_market_stats_msg(self):
        def f(req_cnt):
            return json.dumps({
                "t": "d",
                "d": {
                    "r": f'{req_cnt}',
                    "a": "q",
                    "b": {
                        "p": "/marketStats",
                        "q": {
                            "sp": str(time.time()),
                            "i": "TimeStamp"
                        },
                        "t": 1,
                        "h": ""
                    }
                }
            })
        return f

    def _subscribe_contract_stats_msg(self):
        def f(req_cnt):
            return json.dumps({
                "t": "d",
                "d": {
                    "r": f'{req_cnt}',
                    "a": "q",
                    "b": {
                        "p": "/contractStats",
                        "q": {
                            "sp": str(time.time()),
                            "i": "TimeStamp"
                        },
                        "t": 2,
                        "h": ""
                    }
                }
            })
        return f

    def _subscribe_contract_orderbook_msg(self, contract_id):
        def f(req_cnt):
            return json.dumps({
                't': 'd',
                'd': {
                    'r': f'{req_cnt}',
                    'a': 'q',   # changes to n when closing subscription
                    'b': {
                        'p': f'/contractOrderBook/{contract_id}',
                        'h': '' # h removed when closing subscription
                    }
                }
            })
        return f

    # Still unsure if this is even necessary to send
    def _init_sdk_msg(self):
        def f(req_cnt):
            return json.dumps({
                "t": "d",
                "d": {
                    "r": f'{req_cnt}',
                    "a": "s",
                    "b": {
                        "c": {
                            "sdk.js.4-9-1": 1
                        }
                    }
                }
            })
        return f

    def init_contract(self, contract_id):
        self.contract = contract_id

def load_auth():
    with open('auth.txt', 'r') as f:
        return f.read().split()
