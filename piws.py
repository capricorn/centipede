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

# This is actually a trade event, not a status event 
class OrderbookEvent():
    def __init__(self):
        self.bids = []
        self.asks = []
        self.contract_id = 0

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
            elif 'p' in data and data['p'].startswith('contractOrderBook'):
                # structure of data['p'] = 'contractOrderBook/\d+'
                self.ob_event.contract_id = data['p'][data['p'].index('/')+1:]

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

    def subscribe_contract_orderbook(self, contract_id):
        pass

    def unsubscribe_contract_orderbook(self, contract_id):
        pass

    def subscribe_markets_status(self):
        pass

    def subscribe_contracts_status(self):
        pass

    async def connect_status_feed(self):
        p = pi.PredictItAPI(0).create(*load_auth())
        ws_token = p.negotiate_ws()['ConnectionToken']

        params = {
            'transport': 'webSockets',
            'clientProtocol': 1.5,
            'bearer': p.token,
            'connectionToken': ws_token,
            'connectionData': '[{"name":"markethub"}]',
            'tid': 9
        }

        req = requests.Request('GET', 'https://www.predictit.org/signalr/connect', params=params).prepare()
        url = 'wss://' + req.url[8:]
        async with websockets.connect(url) as ws:
            while True:
                data = await ws.recv()
                data = json.loads(data)
                await self.queue.put(self._parse_status_feed(data))

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

    async def connect_trade_feed(self):
        params = {
            'v': 5,
            'ns': 'predictit-f497e'
        }

        headers = {
            'Host': 's-usc1c-nss-203.firebaseio.com'
        }

        req = requests.Request('GET', 'https://s-usc1c-nss-203.firebaseio.com/.ws', params=params).prepare()
        url = 'wss://' + req.url[8:]

        async with websockets.connect(url) as ws:
            await ws.recv()
            await ws.send(json.dumps({"t":"d","d":{"r":1,"a":"s","b":{"c":{"sdk.js.4-9-1":1}}}}))
            await ws.send(json.dumps({"t":"d","d":{"r":2,"a":"q","b":{"p":"/marketStats","q":{"sp":str(time.time()),"i":"TimeStamp"},"t":1,"h":""}}}))
            # Have to subscribe to contract stats first?
            await ws.send(json.dumps({"t":"d","d":{"r":3,"a":"q","b":{"p":"/contractStats","q":{"sp":str(time.time()),"i":"TimeStamp"},"t":2,"h":""}}}))
            await ws.send(subscribe_contract_orderbook_msg('16684', 4))
            
            while True:
                data = await ws.recv()
                await self.queue.put(self._route_trade_data(data))

    def set_queue_callback(self, callback):
        self.queue_callback = callback

    async def _run_queue(self):
        while True:
            data = await self.queue.get()
            if self.queue_callback:
                await self.queue_callback(data)

    async def start(self):
        self.queue = asyncio.Queue()
        self.feeds = asyncio.gather(self.connect_trade_feed(), self.connect_status_feed(), self._run_queue())
        await self.feeds

    def _route_trade_data(self, data):
        data = json.loads(data)
        if data == {}: return {}
        if 'p' in data['d']['b']:
            msg = data['d']['b']['p']
            if msg.startswith('contractOrderBook'):
                event = json.loads(str(data).replace("'", '"') , cls=OrderbookEvent.OrderbookEventDecoder)
                return event
        return data

    def stop(self):
        self.feeds.cancel()

def subscribe_market_stats_msg(req_cnt):
    pass

def subscribe_contract_stats_msg(req_cnt):
    pass

def subscribe_contract_orderbook_msg(contract_id, req_cnt):
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

def load_auth():
    with open('auth.txt', 'r') as f:
        return f.read().split()
