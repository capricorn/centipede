'''
A bot to locate and invest in negative risk opportunities across PredictIt markets
'''

import time

import predictit as pi
import requests

fee = .1

def get_best_bids(p, yes=True):
    contracts = p.get_market_contract_ids()
    bids = []

    for contract_id in contracts:
        ob = p.get_contract_orderbook(contract_id)
        bids.append(ob[('yesOrders' if yes else 'noOrders')][0]['pricePerShare'])

    return bids

def get_all_markets():
    data = requests.get('https://www.predictit.org/api/marketdata/all/').json()
    return data

'''
api = pi.PredictItAPI('5724')
api.authenticate('auth.txt')

best_bids = get_best_bids(api, yes=False)
profit = sum(list(map(lambda b: (1-b) * (1 - fee), best_bids)))
loss = max(best_bids)

min_profit = profit - max(best_bids)
max_profit = profit - min(best_bids)

print(f'min p/l per share: {min_profit:.2f}')
print(f'max p/l per share: {max_profit:.2f}')
#print(f'100 shares investment: {100 * sum(best_bids)}')
#print(f'100 shares in each position is a profit range of [{100*min_profit:.2f}, {100*max_profit:.2f}]')
'''

token = ''
with open('auth.txt', 'r') as f:
    username, password = f.read().split()
    token = pi.PredictItAPI.get_auth_token(username, password)

for market in get_all_markets()['markets']:
    print(market['id'], market['shortName'])
    p = pi.PredictItAPI(str(market['id']), token)
    try:
        best_bids = get_best_bids(p, yes=False)
    except (IndexError, KeyError): 
        time.sleep(5)
        continue

    profit = sum(list(map(lambda b: (1-b) * (1 - fee), best_bids)))
    loss = max(best_bids)

    min_profit = profit - max(best_bids)
    max_profit = profit - min(best_bids)

    print(f'min p/l per share: {min_profit:.2f}')
    print(f'max p/l per share: {max_profit:.2f}')
    print('')

    time.sleep(5) 
