import time
import json
import asyncio
import threading
import sys
import itertools
from math import floor
from random import randint

import requests

# Need to check delta between last orderbook and current one to see if an update is necessary
# Might also just use 304 if-modified, if that's possible; or hash the last response

class Market():
    def __init__(self, market):
        self.name = market['name']
        self.contracts = {}

        for contract in market['contracts']:
            self.contracts[str(contract['id'])] = {
                'name': contract['shortName']
            }

# Look into utilizing refresh token
# Shouldn't require a market to create it
# Phase out
class PredictItAPI():
    TRADE_TYPE_BUY = 1
    TRADE_TYPE_SELL = 3

    def __init__(self, market_id, token=''):
        self.token = token
        self.market_id = market_id
        self.lock = threading.Lock()

    # Eventually replace the constructor with this
    # And maybe have the auth method just take a username and password
    @staticmethod
    def create(username, password):
        p = PredictItAPI(0)
        p.token = PredictItAPI.get_auth_token(username, password)
        return p

    @staticmethod
    def get_auth_token(username, password):
        data = {
            'email': username,
            'password': password,
            'grant_type': 'password',
            'rememberMe': 'false'
        }
        resp = requests.get('https://www.predictit.org/api/Account/token', data=data)
        return resp.json()['access_token']

    # Obtain a websocket connection token, necessary for later connections
    def negotiate_ws(self):
        params = {
            'clientProtocol': 1.5,
            'bearer': self.token,
            'connectionData': json.dumps([{
                'name': 'markethub'
            }]),
            '_': floor(time.time())
        }

        resp = requests.get('https://www.predictit.org/signalr/negotiate', params=params)
        return resp.json()

    def _trade(self, contract_id, price, vol, trade_type):
        data = {
            'quantity': vol,
            'pricePerShare': price, # Should be in cents, not dollars
            'contractId': contract_id,
            'tradeType': trade_type
        }

        headers = {
            'Authorization': f'Bearer {self.token}'
        }

        return requests.post('https://www.predictit.org/api/Trade/SubmitTrade', 
                data=data, headers=headers).json()

    def sell(self, contract_id, price, vol):
        return self._trade(contract_id, price, vol, PredictItAPI.TRADE_TYPE_SELL)

    def buy(self, contract_id, price, vol):
        return self._trade(contract_id, price, vol, PredictItAPI.TRADE_TYPE_BUY)

    def get_profile_detail(self):
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        resp = requests.get('https://www.predictit.org/api/Profile/Detail', headers=headers)
        return resp.json()

    def authenticate(self, auth_file):
        with open(auth_file, 'r') as f:
            user, passwd = tuple(f.read().split())
            
            self.token = PredictItAPI.get_auth_token(user, passwd)

    def get_market(self):
        resp = requests.get(f'https://www.predictit.org/api/marketdata/markets/{self.market_id}')
        return json.loads(resp.text)

    def get_market_contract_ids(self):
        return list(map(lambda c: str(c['id']), self.get_market()['contracts']))

    def get_contract_orderbook(self, contract_id):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36',
            'Host': 'www.predictit.org',
            'Authorization': f'Bearer {self.token}'
        }

        resp = requests.get(f'https://www.predictit.org/api/Trade/{contract_id}/OrderBook', headers=headers)
        return json.loads(resp.text)

    def load_db(self):
        with self.lock:
            try:
                with open(f'{self.market_id}.json', 'r') as f:
                    data = f.read()

                    if data == '':
                        return {}
                    else:
                        return json.loads(data)
            except FileNotFoundError:
                return {}

    def log_orderbook(self, contract_id, orderbook, ts):
        # open contract orderbook, locate contract, append orders.
        bids = []
        asks = []

        for bid in orderbook['yesOrders']:
            bids.append((bid['pricePerShare'], bid['quantity']))

        for ask in orderbook['noOrders']:
            asks.append((ask['pricePerShare'], ask['quantity']))

        db = self.load_db()
        if db == {} or contract_id not in db:
            db[contract_id] = {}

        db[contract_id][ts] = {
            'ask': [],
            'bid': []
        }

        '''
        last_ob_time = list(db[contract_id].keys())[-1:][0]
        if db[contract_id][last_ob_time] == db[contract_id][ts]:
            return
        '''

        db[contract_id][ts]['ask'].extend(asks)
        db[contract_id][ts]['bid'].extend(bids)

        with self.lock:
            with open(f'{self.market_id}.json', 'w') as f:
                f.write(json.dumps(db))

#async def get_ob(api, contract_id):
def get_ob(api, contract_id):
    # Does this method need to be async since it's called in an async method?
    print(f'Start time: {time.time()}')
    return api.get_contract_orderbook(contract_id)

# So I think because api.get_contract_orderbook is not async, that the async method
# must wait on the method to return 
# Testing in this way shows similar performance to the async code (actually, better)
#for contract_id in api.get_market_contract_ids():
#    get_ob(api, contract_id)


# Compare performance of this vs multithreading
'''
async def main():
    tasks = [ asyncio.create_task(get_ob(api, contract_id)) for contract_id in api.get_market_contract_ids() ]
    for task in tasks:
        await task

asyncio.run(main())
'''

def write_ob(contract_id):
    #print(f'Start time: {time.time()}')
    start_time = str(floor(time.time()))
    api.log_orderbook(contract_id, api.get_contract_orderbook(contract_id), start_time)
    print(f'Logged {contract_id}')

def get_bids(orderbook):
    return list(map(lambda k: (k['pricePerShare'], k['quantity']), orderbook['yesOrders']))

def get_asks(orderbook):
    return list(map(lambda k: (k['costPerShareYes'], k['quantity']), orderbook['noOrders']))

# Preferably also let us know when to cancel or adjust the order
# Maybe output it if the quantity is extremely small

# Need to check the contract orderbook, and our current portfolio
def strat(contract_id):
    pass

def find_arb(api, contract_id, market):
    ob = api.get_contract_orderbook(contract_id)
    #print(ob)
    bids = get_bids(ob)
    asks = get_asks(ob)

    if bids == [] or asks == []:
        return

    bid = bids[0]
    ask = asks[0]
    #print(f'[{contract_id}] b: {get_bids(ob)} a: {get_asks(ob)}')
    if int(bid[0] * 100) - int(ask[0] * 100) >= 3:
        print(f'[{market.contracts[contract_id]["name"]}] b: {bid[0]} a: {ask[0]}')
    #else:
    #    print(f'[{contract_id}] greatest diff: {bid[0] * 100 - ask[0] * 100}')

    #print(ob['bid'])
    #print(ob['ask'])

# Find the profitability of each configuration
def calculate_configs(configs):
    '''
    In each config, we need to first evaluate the winnings on each Y, along with
    that Y's loss if we're wrong.
    If that Y is wrong, then of course some other N is also wrong. For greatest losses,
    assume max{N} is wrong. All the other No's will then be winning strategies.
    '''
    for config in configs:
        for contract in config:
            price, type_ = contract

def main():
    api = PredictItAPI('5715')
    api.authenticate('auth.txt')
    market = Market(api.get_market())
    '''

    # look at profitable subsets
    prices = []
    for contract_id in api.get_market_contract_ids():
        ob = api.get_contract_orderbook(contract_id)
        # (Y, N)
        no_price = 1.0
        yes_price = 1.0
        if ob['noOrders'] != []:
            no_price = ob['noOrders'][0]['pricePerShare']
        if ob['yesOrders'] != []:
            yes_price = ob['yesOrders'][0]['pricePerShare']

        prices.append([(yes_price, 'Y'), (no_price, 'N')])

    configs = list(itertools.product(*prices))
    print(configs)
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

if __name__ == '__main__':
    main()

'''
db = api.load_db()
ids = api.get_market_contract_ids()
contract_id = ids[0]
api.log_orderbook(contract_id, api.get_contract_orderbook(contract_id), str(floor(time.time())))
'''

# Use a thread for every contract
# Dispatch each thread at the same time -- use async?
'''
ids = api.get_market_contract_ids()
contract_id = ids[0]
#log_orderbook('5715', contract_id, api.get_contract_orderbook(contract_id), str(floor(time.time())))
db = load_db('5715')
a = db['16575']['1564107076']['ask']
b = db['16575']['1564107104']['ask']
print(a)
print('')
print(b)
print(a == b)
'''

# Write code to calculate opportunities on no where you make money
