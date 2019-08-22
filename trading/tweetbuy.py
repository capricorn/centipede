# Given a bracket that we suspect a price move on, buy Yes in the opposing category, and No on the other
# category

import asyncio
import time
import datetime

import tweetstream as ts
import predictit as pi

'''
I think the only necessary component is:
    - A tweet checker that dispatches trades when a tweet occurs
'''
p = pi.PredictItAPI('5787').create(load_auth())
short_contract = '16903'
long_contract = '' # just start with long contract -- need to double check No works

def callback(tweet, count):
    global p
    global short_contract

    ob = p.get_contract_orderbook(short_contract)
    print(f'Fetching orderbook for contract: {short_contract}')
    yes_orders = list(map(lambda k: (k['pricePerShare'], k['quantity']), ob['yesOrders']))

    print(yes_orders)
    price, quantity = yes_orders[0]
    print(price)
    print(quantity)
    # Next, buy $50 worth of No -- be careful!
    # Determine what price level you need to buy at by examining quantity necessary.

    allowance = 20
    for yes in yes_orders:
        price, quantity = yes
        if allowance / price <= quantity:
            print(f'Buying contracts {int(allowance / price)}@{price}')
            print(p.buy(short_contract, int(price*100), int(allowance / price)))
            break
        else:
            print(f'Buying contracts {quantity} @ {price}')
            allowance = allowance - quantity*price
            print(f'Still need to buy: {allowance}')
            print(p.buy(short_contract, int(price*100), quantity))
            print('Remaining allowance: {allowance}')
        time.sleep(1)

    #p.buy_no(short_contract, )

'''
t = datetime.datetime.strptime('Aug 15 2019 12:00', '%b %d %Y %H:%M')
ts = ts.TweetStream(t)
ts.set_callback(callback)
ts.run()
'''

#callback(None)
#p.buy_no('16805', 59, 1)

'''
ws = piws.PredictItWebSocket()
ws.set_queue_callback(callback)
ws.set_contract_stats_filter(lambda c: not (c == '16805' or c == '16808'))
asyncio.get_event_loop().run_until_complete(ws.start())
'''

# Need to place two orders:
# A no order on the contract we are shorting
# and a yes order on the contract we're long on
