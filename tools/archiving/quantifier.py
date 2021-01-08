import asyncio
import logging

import piws
import predictit as pi

# Track trade quantities here, test it out
# Anyway we can ignore initialization code events? Maybe mark them as initialization objects?
fifo = []
delta_table = {}
#ob_delta = None

# Am I actually thinking of this correctly? It should be just consecutive events that arrive in order,
# such that our desired combination occurs..
async def callback(event):
    global fifo
    global delta_table

    if not(type(event) == piws.OrderbookEvent or type(event) == piws.MarketStatsEvent or
            type(event) == piws.ContractStatsEvent): return

    # Check every fifo to check if marketstats belong there (only belongs to 1 upate by ts)
    if type(event) == piws.MarketStatsEvent:
        print(f'{event.market_id} {type(event)} {event.timestamp}')
    else:
        print(f'{event.contract_id} {type(event)} {event.timestamp}')
    return

    if type(event) == piws.OrderbookEvent:
        if event.contract_id in delta_table:
            delta_table[event.contract_id].update(piws.Orderbook(event.bids, event.asks))
        else:
            delta_table[event.contract_id] = piws.OrderbookDelta(piws.Orderbook(event.bids, event.asks))

    if len(fifo) < 3:
        # Do we need a separate fifo for each orderbook item?
        # And just have them share marketstats?
        fifo.append(event)
    else:
        fifo.pop(0)
        fifo.append(event)
        # Should be sent together down the pipeline in a group of 3
        #print(set(map(lambda e: type(e), fifo)))
        if set(map(lambda e: type(e), fifo)) == {piws.OrderbookEvent, piws.MarketStatsEvent, piws.ContractStatsEvent}:
            ms_event = [ e for e in fifo if type(e) == piws.MarketStatsEvent][0]
            cs_event = [ e for e in fifo if type(e) == piws.ContractStatsEvent][0]

            if ms_event.timestamp == cs_event.timestamp:
                print(f'{cs_event.contract_id}: {piws.find_order_quantity(delta_table[cs_event.contract_id])}')
                #print(f'A trade ({piws.find_order_quantity(delta_table[cs_event.contract_id])}) occurred in contract: {cs_event.contract_id}')

        #print(fifo)


    '''
    if type(event) == piws.OrderbookEvent:
        print(f'Orderbook event: {event.contract_id}')
    elif type(event) == piws.MarketStatsEvent:
        print(f'Market stats event: {event.market_id}')
    elif type(event) == piws.ContractStatsEvent:
        print(f'Contract stats event: {event.contract_id}')
    '''

pairs = []
market_volume = []
pair = []
async def callback2(event):
    global market_volume
    global pairs
    global pair

    # Display orderbook deltas for all contracts in market inbetween, so you get a better idea?
    # Or just make a separate callback and run them side-by-side
    '''
    if type(event) == piws.MarketStatsEvent:
        market_volume.append(event)
        if len(market_volume) == 2:
            print(market_volume[1])
            print(market_volume[0])
            print(market_volume[1].shares_traded)
            print(market_volume[0].shares_traded)
            print(f'shares traded: {market_volume[1].shares_traded - market_volume[0].shares_traded}\n')
            market_volume.pop(0)
    '''
    if type(event) == piws.MarketStatsEvent:
        qlogger.info(f'Market update: {event.market_id}: {event.shares_traded} ({event.timestamp})')
    if type(event) == piws.ContractStatsEvent:
        qlogger.info(f'Contract stats: {event.contract_id} ({event.timestamp})')
    if type(event) == piws.OrderbookEvent:
        qlogger.info(f'Orderbook event: {event.contract_id} ({event.timestamp})')

    '''
    if type(event) == piws.ContractStatsEvent or type(event) == piws.MarketStatsEvent:
        pair.append(event)

    # Here, we need to:
    # 1. Decide if the pair is actually a pair, via timestamp
    # 2. Depending on the event, make the appropriate change
    # 3. Update pairs if it's a quality pair
    if len(pair) == 2 and type(event) == piws.ContractStatsEvent or type(event) == piws.MarketStatsEvent:
        p1, p2 = pair
        if p1.timestamp != p2.timestamp:
            pair.pop(0)
        else:
            pairs.append(pair)
            pair = []

    if type(event) == piws.OrderbookEvent:
        # This is where we need to use the orderbook diff and market diff together
        for p in pairs:
            pass
    '''

# Keep in mind we need to filter by the contract
# Start by just tracking states
contract_events = {}
states = {}
STATE_OB_EVENT = 0
STATE_CS_EVENT = 1
STATE_MS_EVENT = 2
STATE_INIT = 3
market_quantity = []
async def callback3(event):
    global market_quantity
    # Have to check every subscribed contract in this case?
    if type(event) == piws.MarketStatsEvent:
        qlogger.info('market stats event')
        market_quantity.append(event.shares_traded)
        if len(market_quantity) == 2:
            qlogger.info(market_quantity[1] - market_quantity[0])
            market_quantity.pop(0)
    if type(event) == piws.ContractStatsEvent:
        qlogger.info('contract stats event')
    if type(event) == piws.OrderbookEvent:
        qlogger.info('orderbook change event')

#logging.basicConfig(format='(%(module)s) [%(asctime)s] %(message)s')

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt='(%(module)s) [%(asctime)s] %(message)s'))

logger = logging.getLogger('piws')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

l = logging.getLogger('asyncio')
l.setLevel(logging.DEBUG)
l.addHandler(handler)

qlogger = logging.getLogger(__name__)
qlogger.setLevel(logging.DEBUG)
qlogger.addHandler(handler)

'''
markets = ['5782', '5787']
contracts = []
for market in markets:
    p = pi.PredictItAPI(market)
    contracts.extend(p.get_market_contract_ids())

print(contracts)
ws = piws.PredictItWebSocket()
ws.contracts = contracts
#ws.set_market_filter(lambda market_id: str(market_id) not in markets)
ws.set_market_filter(lambda market_id: str(market_id) != '5782')
#ws.set_contract_stats_filter(lambda contract_id: contract_id not in contracts)
ws.set_contract_stats_filter(lambda contract_id: contract_id != '16894')
ws.set_queue_callback(callback)
#for c in contracts:
#    ws.subscribe_contract_orderbook(c)
ws.subscribe_contract_orderbook('16894')
ws.subscribe_contract_status()
ws.subscribe_market_status()
'''

MARKET = '5812'
p = pi.PredictItAPI(MARKET)
contracts = p.get_market_contract_ids()

ws = piws.PredictItWebSocket()
ws.set_market_filter(lambda market_id: str(market_id) != MARKET)
ws.set_contract_stats_filter(lambda contract_id: contract_id not in contracts)
for contract in contracts:
    ws.subscribe_contract_orderbook(contract)
#ws.set_queue_callback(callback2)
ws.set_queue_callback(callback2)
ws.subscribe_contract_status()
ws.subscribe_market_status()

try:
    asyncio.run(ws.start())
except KeyboardInterrupt:
    ws.stop()
