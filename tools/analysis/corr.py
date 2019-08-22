import asyncio
import logging
import time

import piws
from scipy.stats import pearsonr as corr

# Analyze running correlation between two contracts (latest trade price)

#c1_data = []
#c2_data = []
contracts = {
    '16810': [],
    '16807': []
}

async def callback(event):
    global contracts

    if type(event) == piws.ContractStatsEvent:
        print(f'{event.contract_id}: {event.date_updated, event.timestamp, event.last_trade_price}c')
        if len(contracts[event.contract_id]) < 10:
            contracts[event.contract_id].append(event.last_trade_price)
        else:
            contracts[event.contract_id].pop(0)
            contracts[event.contract_id].append(event.last_trade_price)
        #print(f'{event.contract_id}: {contracts[event.contract_id]}')
    
        if len(contracts['16810']) == 5 and len(contracts['16807']) == 5:
            print(f'corr: {corr(contracts["16810"], contracts["16807"])}')


#logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

ws = piws.PredictItWebSocket()
ws.set_queue_callback(callback)
ws.set_contract_stats_filter(lambda c: not (c == '16810' or c == '16807'))
asyncio.get_event_loop().run_until_complete(ws.start())
#ws.init_contract(contract_id)
# Share the same contract between both websocket connections for now?
