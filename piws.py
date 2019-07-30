import asyncio
import json
import logging
import base64
import time

import websockets
import requests
import predictit as pi

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
        #self.token = token
        #self.ws_token = ws_token

    def set_market_stats_callback(self, callback):
        self.market_stats_callback = callback

    def set_contract_stats_callback(eslf, callback):
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
                #print(f'status: {data}')
            pass

    async def connect_trade_feed(self):
        params = {
            'v': 5,
            'ns': 'predictit-f497e'
        }

        headers = {
            'Host': 's-usc1c-nss-204.firebaseio.com'
        }

        req = requests.Request('GET', 'https://s-usc1c-nss-204.firebaseio.com/.ws', params=params).prepare()
        url = 'wss://' + req.url[8:]

        self.ws = await websockets.connect(url)
        await self.ws.recv()
        await self.ws.send(json.dumps({"t":"d","d":{"r":1,"a":"s","b":{"c":{"sdk.js.4-9-1":1}}}}))
        await self.ws.send(json.dumps({"t":"d","d":{"r":2,"a":"q","b":{"p":"/marketStats","q":{"sp":str(time.time()),"i":"TimeStamp"},"t":1,"h":""}}}))
        # Have to subscribe to contract stats first?
        await self.ws.send(json.dumps({"t":"d","d":{"r":3,"a":"q","b":{"p":"/contractStats","q":{"sp":str(time.time()),"i":"TimeStamp"},"t":2,"h":""}}}))
        await self.ws.send(subscribe_contract_orderbook_msg('16575', 4))
        
        while True:
            data = await self.ws.recv()
            #print(f'trade: {data}')
            self._route_trade_data(data)

    # Begin running the event loop
    async def _start(self):
        await asyncio.gather(self.connect_trade_feed(), self.connect_status_feed())

    def start(self):
        asyncio.run(self._start())

    def _route_status_data(self, data):
        pass

    @staticmethod
    def _convert_orderbook(orderbook):
        return { 
            'bid': list(map(lambda no: (no[1]['costPerShareYes'], no[1]['quantity']), orderbook['noOrders'].items())),
            'ask': list(map(lambda no: (no[1]['costPerShareYes'], no[1]['quantity']), orderbook['yesOrders'].items())) 
        }

    # Need to understand which methods should be async
    def _route_trade_data(self, data):
        #print(data)
        data = json.loads(data)
        if data == {}: return
        if 'p' in data['d']['b']:
            msg = data['d']['b']['p']
            if msg.startswith('contractOrderBook') and self.orderbook_change_callback:
                #print(PredictItWebSocket._convert_orderbook(data['d']['b']['d']))
                self.orderbook_change_callback(PredictItWebSocket._convert_orderbook(data['d']['b']['d']))
        else:
            pass

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
            print(msg)

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
    w = PredictItWebSocket()
    '''
    w.set_orderbook_change_callback(lambda p: print(p))
    asyncio.get_event_loop().run_until_complete(w.start())
    '''
    asyncio.run(w.start())

if __name__ == '__main__':
    main()
