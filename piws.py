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
                    self.ob_event.bids.append((data['costPerShareYes'], data['quantity']))
                    return self.ob_event
                elif data['tradeType'] == 0:  # May be wrong
                    self.ob_event.asks.append((data['costPerShareYes'], data['quantity']))
                    return self.ob_event
            elif 'p' in data and data['p'].startswith('contractOrderBook'):
                # structure of data['p'] = 'contractOrderBook/\d+'
                self.ob_event.contract_id = data['p'][data['p'].index('/')+1:]

            return self.ob_event 

# For two string, just dump as json
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
                self.event.contract_id = data['ContractId']
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

class SharesTradedEvent:
    trade_type = '' # bought / sold
    status = '' # open / close?
    quantity = 0
    price = 0
    timestamp = 0

# Maybe create a simple request object for tracking request counts (although I'm not sure its necessary) 
# Create a basic socket with hooks that are called on a message

# Is this going to be a convenient object for the bot?
# I'll probably need to utilize some sort of arb state machine, that is modified by the call backs
# I provide. Just pass in the objects methods
# Also this is only for the trading websocket for now
# Need a way to also communicate with the sockets, so that we can send various commands.
# Either make separate objects for these sockets, or simply add methods to this socket
# Probably better to keep things simple, as though we're dealing with one event stream
class PredictItWebSocket():
    #def __init__(self, token, ws_token):
    def __init__(self):
        self.market_stats_callback = None
        self.contract_stats_callback = None
        self.orderbook_change_callback = None
        self.ws = None
        self.queue = None
        self.queue_callback = None
        #self.token = token
        #self.ws_token = ws_token

    def set_market_stats_callback(self, callback):
        self.market_stats_callback = callback

    def set_contract_stats_callback(self, callback):
        self.contract_stats_callback = callback

    def set_orderbook_change_callback(self, callback):
        self.orderbook_change_callback = callback

    def subscribe_contract_orderbook(self, contract_id):
        pass

    def unsubscribe_contract_orderbook(self, contract_id):
        pass

    # Ideally can interact with the event loop, and send subscribe messages
    async def send(self, msg):
        pass

    async def recv(self):
        pass

    async def connect_status_feed(self):
        p = pi.PredictItAPI(0).create(*load_auth())
        #p.authenticate('auth.txt')
        ws_token = p.negotiate_ws()['ConnectionToken']
        print(ws_token)

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
                #print(data)
                await self.queue.put(self._parse_status_feed(data))
                #print(f'status: {data}')

    def _parse_shares_traded_event(self, msg):
        event = SharesTradedEvent()
        event.quantity = msg[1]['Quantity']
        event.trade_type = TRADE_TYPE_BUY if msg[1]['TradeType'] == TRADE_TYPE_BUY else TRADE_TYPE_SELL
        event.price = msg[1]['PricePerShare']
        event.timestamp = msg[1]['TimeStamp']

    # parse raw status feed data and return as status feed event
    # Might accidentally miss an important message since it's a list
    def _parse_status_feed(self, msg):
        if 'M' in msg:
            for event in msg['M']:
                if event['A'][0] == ContractOwnershipUpdateEvent.event_message:
                    return json.loads(str(event['A'][1]).replace('\'', '"'), cls=ContractOwnershipUpdateEvent.ContractOwnershipUpdateEventDecoder)
        return msg
        '''
        msg = json.loads(msg)
        print(f'status: {msg}')
        if 'M' in msg:
            for update in msg['M']:
                if 'A' in update and 'notification_shares_traded' in update['A']:
                    print('SHARES TRADED')
                    return self._parse_shares_traded_event(update['A'])
        return msg
        '''

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
        print(url)

        #self.ws = await websockets.connect(url)
        async with websockets.connect(url) as ws:
            await ws.recv()
            await ws.send(json.dumps({"t":"d","d":{"r":1,"a":"s","b":{"c":{"sdk.js.4-9-1":1}}}}))
            await ws.send(json.dumps({"t":"d","d":{"r":2,"a":"q","b":{"p":"/marketStats","q":{"sp":str(time.time()),"i":"TimeStamp"},"t":1,"h":""}}}))
            # Have to subscribe to contract stats first?
            await ws.send(json.dumps({"t":"d","d":{"r":3,"a":"q","b":{"p":"/contractStats","q":{"sp":str(time.time()),"i":"TimeStamp"},"t":2,"h":""}}}))
            await ws.send(subscribe_contract_orderbook_msg('16688', 4))
            
            while True:
                data = await ws.recv()
                #print(data)
                await self.queue.put(self._route_trade_data(data))
                #print(f'trade: {data}')
                #self._route_trade_data(data)

    def set_queue_callback(self, callback):
        self.queue_callback = callback

    async def _run_queue(self):
        while True:
            data = await self.queue.get()
            if self.queue_callback:
                # async?
                await self.queue_callback(data)

    # Begin running the event loop
    async def _start(self):

        await asyncio.gather(self.connect_trade_feed(), self.connect_status_feed())

    async def start(self):
        self.queue = asyncio.Queue()
        await asyncio.gather(self.connect_trade_feed(), self.connect_status_feed(), self._run_queue())
        #asyncio.run(self._start())
        #asyncio.run(self.connect_trade_feed())

    def _route_status_data(self, data):
        pass

    @staticmethod
    def _convert_orderbook(orderbook):
        bids = []
        asks = []
        
        print(orderbook)
        if orderbook['noOrders'] != 0:
            bids = list(map(lambda no: (int(no[1]['costPerShareYes']*100), no[1]['quantity']), 
                orderbook['noOrders'].items()))

        if orderbook['yesOrders'] != 0:
            asks = list(map(lambda no: (int(no[1]['costPerShareYes']*100), no[1]['quantity']), 
                orderbook['yesOrders'].items()))

        '''
        return { 
            'bid': ,
            'ask': list(map(lambda no: (int(no[1]['costPerShareYes']*100), no[1]['quantity']), 
                orderbook['yesOrders'].items())) 
        }
        '''

        return {
            'bid': bids,
            'ask': asks
        }

    # Need to understand which methods should be async
    def _route_trade_data(self, data):
        #print(data)
        data = json.loads(data)
        if data == {}: return {}
        if 'p' in data['d']['b']:
            msg = data['d']['b']['p']
            if msg.startswith('contractOrderBook'):
                # Make sure to fix up the orderbook in the actual decoder
                event = json.loads(str(data).replace("'", '"') , cls=OrderbookEvent.OrderbookEventDecoder)
                return event
                '''
                ob = OrderbookEvent()
                trades = PredictItWebSocket._convert_orderbook(data['d']['b']['d'])
                ob.bids = trades['bid']
                ob.asks = trades['ask']
                '''
                #print(PredictItWebSocket._convert_orderbook(data['d']['b']['d']))
                #self.orderbook_change_callback(PredictItWebSocket._convert_orderbook(data['d']['b']['d']))
                #return ob
        return data

    def stop():
        pass

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

async def connect(token, ws_token):
    # Not headers, params!
    # Pass in headers yourself via requests
    params = {
        'transport': 'webSockets',
        'clientProtocol': 1.5,
        'bearer': token,
        'connectionToken': ws_token,
        'connectionData': '[{"name":"markethub"}]',
        'tid': 9
    }

    headers = {
        #'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36'
    }

    '''
    r = requests.get('https://www.predictit.org/signalr/connect', params=params, headers=headers)
    print(r.url)
    print(r.status_code)
    '''
    # This websocket tracks our account holdings on the contracts in various markets
    # Basically tracks our holdings data -- not too interesting, but still useful
    # Some of it is just basic info
    req = requests.Request('GET', 'https://www.predictit.org/signalr/connect', params=params).prepare()
    url = 'wss://' + req.url[8:]
    print(url)
    async with websockets.connect(url, extra_headers = headers) as ws:
        while True:
            data = await ws.recv()
            print(f'data: {data}')

# Eventually will need to catch the error with firebase version
async def trading_connect():
    params = {
        'v': 5,
        'ns': 'predictit-f497e'
    }

    headers = {
        'Host': 's-usc1c-nss-204.firebaseio.com'
    }

    req = requests.Request('GET', 'https://s-usc1c-nss-204.firebaseio.com/.ws', params=params).prepare()
    url = 'wss://' + req.url[8:]
    print(url)
    async with websockets.connect(url, extra_headers=headers) as ws:
        data = await ws.recv()
        print(f'data: {data}')
        await ws.send(json.dumps({"t":"d","d":{"r":1,"a":"s","b":{"c":{"sdk.js.4-9-1":1}}}}))
        await ws.send(json.dumps({"t":"d","d":{"r":2,"a":"q","b":{"p":"/marketStats","q":{"sp":str(time.time()),"i":"TimeStamp"},"t":1,"h":""}}}))
        # Have to subscribe to contract stats first?
        await ws.send(json.dumps({"t":"d","d":{"r":3,"a":"q","b":{"p":"/contractStats","q":{"sp":str(time.time()),"i":"TimeStamp"},"t":2,"h":""}}}))
        await ws.send(subscribe_contract_orderbook_msg('16578', 4))

        while True:
            data = json.loads(await ws.recv())
            msg = data['d']['b']
            #print(msg)

            # Here's where you handle the arb
            #if 'p' in msg and msg['p'].startswith('/contractOrderBook'):
            #    print(msg['p'])
            #print(f'data: {data}')


def load_auth():
    with open('auth.txt', 'r') as f:
        return f.read().split()

#logger = logging.getLogger('websockets')
#logger.setLevel(logging.INFO)
#logger.addHandler(logging.StreamHandler())

def main():
    username, password = load_auth()
    p = pi.PredictItAPI.create(username, password)
    detail = p.get_profile_detail()
    negotiation = p.negotiate_ws()
    ws_token = negotiation['ConnectionToken']
    #print(ws_token)

    #asyncio.get_event_loop().run_until_complete(connect(p.token, ws_token))
    #asyncio.get_event_loop().run_until_complete(trading_connect())

    #w = PredictItWebSocket(p.token, ws_token)

    # 16684
    w = PredictItWebSocket()
    '''
    w.set_orderbook_change_callback(lambda p: print(p))
    asyncio.get_event_loop().run_until_complete(w.start())
    '''
    asyncio.run(w.start())

if __name__ == '__main__':
    main()
