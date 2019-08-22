import asyncio
from timeit import default_timer as timer
from scipy.stats import poisson

import piws

# Count the average time between trades (that is, the average rate a trade occurs)

# Actually, start with simply counting the time between orderbook events

last_time = 0
avg = 0
pos = 1

# Get the avg after adding n as the kth element
def running_avg(avg, n, k):
    if k == 1:
        return n

    return ((k-1)/k)*avg + n/k

async def count(event):
    global last_time
    global avg
    global pos

    # Don't we need to filter for our contract
    if type(event) == piws.OrderbookEvent:
        print('event')
        if last_time == 0:
            last_time = timer()
        else:
            t = timer()
            print(f'{t - last_time}')

            avg = running_avg(avg, t - last_time, pos)
            last_time = t
            pos += 1
            print(f'running avg: {avg}')
            print(f'expected occurrence within (95%): {poisson.ppf(.95, avg)}')

if __name__ == '__main__':
    ws = piws.PredictItWebSocket()
    ws.set_queue_callback(count)
    asyncio.run(ws.start())
