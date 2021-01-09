import datetime
from math import floor
from time import sleep
from itertools import combinations
#from itertools import reduce
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from scipy.stats import pearsonr

#PRICE_FILE = 'aug26_clean.csv'
# contract_id, timestamp, price
PRICE_FILE = '28aug_prices_clean.csv'
#TWEETS_FILE = 'aug22_tweets.txt'
#TWEETS_FILE = 'new_tweets.txt'

# count, timestamp (ISO)
TWEETS_FILE = 'aug28_tweets.csv'

'''
CONTRACT_NAMES = {
    '16998': '109 or fewer',
    '16993': '110 - 119',
    '16996': '120 - 129',
    '16997': '130 - 139',
    '16995': '140 - 149',
    '16994': '150 - 159',
    '16992': '160 or more'
}
'''
CONTRACT_NAMES = {
    '17130': '139 or fewer',
    '17127': '140 - 149',
    '17126': '150 - 159',
    '17128': '160 - 169',
    '17125': '170 - 179',
    '17129': '180 - 189',
    '17124': '190 or more'
}

# Hunting for a correlation between tweet times and price changes
def read_prices():
    with open(PRICE_FILE, 'r') as f:
        data = f.read()
        data = data.split('\n')
        data.pop()  # remove ['']
        data = list(map(lambda k: k.split(','), data))
        data = list(map(lambda k: (k[0], float(k[1]), int(float(k[2])*100)), data))
        return data

# Return the count for analysis
def read_tweet_timestamps():
    with open(TWEETS_FILE, 'r') as f:
        data = f.read()
        data = data.split('\n')
        data.pop()
        #data = data[:-30]
        # Twitter outputs in UTC, 5 hours off our local time zone,
        # and one of our price timestamps seems to be in UTC, and the other in CST
        #return list(map(lambda t: datetime.datetime.strptime(t.split(',')[1], '%Y-%m-%d %H:%M:%S').timestamp() - 60*60*5, data))
        for d in data:
            print(d.split(',')[1])
        return list(map(lambda t: (t.split(',')[0], datetime.datetime.strptime(t.split(',')[1], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp()), data))

# Need prices & timestamp pairs to plot
'''
prices = list(filter(lambda k: k[0] == '16992', read_prices()))
price_data = list(map(lambda k: float(k[2]), prices))
price_ts_data = list(map(lambda k: float(k[1]), prices))
'''

#for ts in price_ts_data:
#    print(datetime.datetime.fromtimestamp(ts))

#plt.plot(price_ts_data, price_data)

'''
prices = list(filter(lambda k: k[0] == '16807', read_prices()))
price_data = list(map(lambda k: float(k[2]), prices))
price_ts_data = list(map(lambda k: float(k[1]), prices))
'''

'''
plt.plot(price_ts_data, price_data, color='g')
'''

'''
ts = read_tweet_timestamps()
counts = list(map(lambda t: t[0], ts))
counts.reverse()
ts = list(zip(counts, map(lambda t: t[1], ts)))
ts.reverse()
#for count, timestamp in ts:
#    plt.axvline(x=timestamp, color='r')

#expiration = datetime.datetime.strptime('Aug 28 2019 16:00', '%b %d %Y %H:%M').astimezone(datetime.timezone.utc)
start_ts = datetime.datetime.strptime('Aug 21 2019 12:00', '%b %d %Y %H:%M').timestamp()
expiration_ts = datetime.datetime.strptime('Aug 28 2019 12:00', '%b %d %Y %H:%M').timestamp()
tweet_ts = list(map(lambda t: t[1] - start_ts, ts))
tweet_ts.reverse()

#print(ts)
#print(price_ts_data)
def plot_3v():
    x = []
    y = []
    z = []
    for contract, price_ts, price in prices:
        #print(price_ts)
        #print(list(zip(ts, ts[1:]))[0][0][1])
        #tweet_ts = list(filter(lambda t: t[0][0][1] < price_ts < t[0][1][1], zip(ts, ts[1:])))
        for t1, t2 in zip(ts, ts[1:]):
            if t1[1] < float(price_ts) < t2[1]:
                x.append(float(price_ts) - start_ts)
                y.append(int(t1[0]))
                z.append(int(float(price)*100))
                break
    return (x,y,z)
'''

'''
x,y,z = plot_3v()
print(x,y,z)

fig = plt.figure()
ax = Axes3D(fig)
#ax.plot_trisurf(x, y, z)
ax.bar3d(x,y,z, np.ones(len(x)), np.ones(len(x)), np.ones(len(x)))
plt.show()
'''
'''
First, normalize all timestamps by subtracting by the unix time of the start date
This will then end at 7*24*60*60 seconds.
Convert all tweets to unix time in the same window.
x range: [0, 7*24*60*60]
y range: [0, tweet_count]
z range: [1, 99]
For each price change, locate the tweet count that falls within it, and likewise the price at that time
'''

def get_contract_data(contract, prices):
    return list(filter(lambda p: p[0] == contract, prices))

# Plot contracts as tte / price with vertical tweet times (labelled with tweet count)
def plot_contracts(xs=[], show_tweets=False):
    start_ts = datetime.datetime.strptime('Aug 21 2019 16:00', '%b %d %Y %H:%M').timestamp()
    #contracts = ['16996', '16993', '16998', '16994', '16992', '16997', '16995']
    contracts = ['17130', '17127', '17126', '17128', '17125', '17129', '17124']
    prices = read_prices()
    tweets = read_tweet_timestamps()

    print(tweets)

    plots = []
    plot_names = []
    for contract in contracts:
        contract_data = get_contract_data(contract, prices)
        #tte = list(map(lambda k: int(k[1] - start_ts), contract_data))
        p = list(map(lambda k: k[2], contract_data))
        ts = list(map(lambda k: k[1], contract_data))
        #print(ts)
        #print(tte)
        #print(contract_data)
        plot, = plt.plot(ts, p)
        plots.append(plot)
        plot_names.append(CONTRACT_NAMES[contract])
    plt.legend(plots, plot_names)

    if show_tweets:
        for count, timestamp in tweets:
            print(f'tweet ts: {timestamp}')
            plt.axvline(x=timestamp, color='r')
            #plt.text(timestamp-start_ts+1, 0, count)

    '''
    # Place a green line for the end of each day
    for i in range(0, 7*24*60*60, 24*60*60):
        plt.axvline(x=i, color='g')
    '''

    for x in xs:
        plt.axvline(x=x, color='c')

    #plt.show()

# tweets = (count, ts)
def find_closest_tweet(ts, tweets):
    # Does tweets need reversed?
    res = list(filter(lambda p: p[0][1] < ts < p[1][1], zip(tweets, tweets[1:])))
    if res == []: return res
    return res[0][0]

def get_tweet_pace(tweet, start_ts):
    tweet_count, tweet_ts = tweet
    tweet_count = int(tweet_count)
    # Next, find the total time that has elapsed (end_time - current_time),
    # and find the average tweet rate. Next, multiply this by 7 for the week's running projection. 
    time_elapsed = tweet_ts - start_ts
    avg_tweet_rate = tweet_count / (time_elapsed / 60 / 60 / 24)
    pace = avg_tweet_rate * 7

    return pace

def plot_price_and_pace():
    '''
    - For each price point, find the current pace by:
        - Locating the closest tweet count at the time
        - Calculating pace via tte of price
        - Then, plot (pace, price) (what format?)
    Curious how the market moves based off this info
    '''

    # Probably in utc by default
    # Maybe adjust by +4, since UTC = est-4
    start_ts = datetime.datetime.strptime('Aug 28 2019 16:00', '%b %d %Y %H:%M').astimezone(datetime.timezone.utc).timestamp()

    end_ts = datetime.datetime.strptime('Sep 04 2019 16:00', '%b %d %Y %H:%M').astimezone(datetime.timezone.utc).timestamp()
    #contracts = ['16996', '16993', '16998', '16994', '16992', '16997', '16995']
    prices = read_prices()
    tweets = read_tweet_timestamps()
    # Fix tweets, since our data is backwards -- should really correct the collector
    #tweets = list(zip(range(len(tweets), 0, -1), map(lambda k: k[1], tweets)))
    #tweets.reverse()

    '''
    for tweet in tweets:
        tweet_count, tweet_ts = tweet
        # Next, find the total time that has elapsed (end_time - current_time),
        # and find the average tweet rate. Next, multiply this by 7 for the week's running projection. 
        time_elapsed = tweet_ts - start_ts
        avg_tweet_rate = tweet_count / (time_elapsed / 60 / 60 / 24)
        pace = avg_tweet_rate * 7

        print(f'count: {tweet_count} avg: {avg_tweet_rate} pace: {pace}')

    return
    '''
    contracts = ['17130', '17127', '17126', '17128', '17125', '17129', '17124']
    #contracts = ['16992']
    for contract in contracts:
        x_points = []
        y_points = []
        contract_prices = list(filter(lambda k: k[0] == contract, prices))
        for data in contract_prices:
            contract_id, ts, price = data
            tweet = find_closest_tweet(ts, tweets)
            if tweet == []: continue

            tweet_count, tweet_ts = tweet
            # Next, find the total time that has elapsed (end_time - current_time),
            # and find the average tweet rate. Next, multiply this by 7 for the week's running projection. 
            time_elapsed = tweet_ts - start_ts
            avg_tweet_rate = int(tweet_count) / (time_elapsed / 60 / 60 / 24)
            pace = avg_tweet_rate * 7

            x_points.append(pace)
            y_points.append(price)

        plt.plot(x_points, y_points)

    plt.show()
    #for contract in contracts:
    #    pass

# Need another figure for placing pace timestamps on the graph
# How about plot contracts, and then signal the timestamps where large pace changes occurred (~20 or more)
def pace_strat():
    '''
    Basic idea:
    - Go through each price point. If there is a significant jump in pace, then buy that bracket.
    See if it's profitable. Adjustments to the strat can be made as necessary.
    '''
    # Python immediately formats according to local time I guess (CST).
    # Need a better timezone independent solution
    # Or switch to the replace code?
    #start_ts = datetime.datetime.strptime('Aug 28 2019 11:00', '%b %d %Y %H:%M').astimezone(datetime.timezone.utc).timestamp()
    start_ts = datetime.datetime.strptime('Aug 28 2019 16:00', '%b %d %Y %H:%M').replace(tzinfo=datetime.timezone.utc).timestamp()
    print(f'start ts: {start_ts}')
    #end_ts = datetime.datetime.strptime('Sep 04 2019 11:00', '%b %d %Y %H:%M').astimezone(datetime.timezone.utc).timestamp()
    end_ts = datetime.datetime.strptime('Sep 04 2019 16:00', '%b %d %Y %H:%M').replace(tzinfo=datetime.timezone.utc).timestamp()
    tweets = read_tweet_timestamps()
    # Correct tweets
    #tweets = list(zip(range(len(tweets), 0, -1), map(lambda k: k[1], tweets)))
    #tweets.reverse()

    tweet_ts = list(map(lambda k: k[1], tweets))

    # First, just output diffs in pace
    # How can we mark the favorite pace at each tweet?
    # Maybe two different plots?
    diffs = []
    for t1, t2 in zip(tweets, tweets[1:]):
        p1 = get_tweet_pace(t1, start_ts)
        p2 = get_tweet_pace(t2, start_ts)
        #print(f'new pace: {p2} -- diff: {p2 - p1}')
        #diffs.append(get_tweet_pace(t2, start_ts) - get_tweet_pace(t1, start_ts))
        if abs(p2 - p1) >= 10:
            print(p2 - p1, p2)
            diffs.append(t2[1])

    for i in range(int(start_ts), int(end_ts)+1, 60*60*24):
        plt.axvline(x=i, color='r')

    paces_y = []
    ts_x = []
    for tweet in tweets:
        ts_x.append(tweet[1])
        paces_y.append(get_tweet_pace(tweet, start_ts))
    print(paces_y)
    #diffs.extend(tweet_ts)
    print(diffs)
    plt.subplot(211, title='price data')
    plt.xlabel('timestamp')
    plt.ylabel('price (cents)')
    times = []
    times.extend(tweet_ts)
    plot_contracts(xs=times)
    plt.subplot(212, title='pace (tweets)')
    plt.xlabel('timestamp')
    plt.ylabel('pace')
    plt.plot(ts_x, paces_y)
    # Show pace at each tweet ts
    #plot_contracts(xs=tweet_ts)
    plt.show()
    #print(f'max delta: {max(diffs)}')



# Pad c1 to be the same length as c2
def pad_prices(c1, c2):
    '''
    Look at the size difference between c1 and c2.
    '''
    pad_per_price = floor(len(c2) / len(c1))
    #print(f'ppp: {pad_per_price}')
    # Just place an extra left over until everything is gone.
    leftovers = len(c2) % len(c1)
    #print(f'leftover: {leftovers}')

    new_c1 = []
    # Next, extend each item in c1 by pad_per_price, with an optional leftover
    for price in c1:
        new_c1.extend([price]*pad_per_price)
        if leftovers > 0:
            new_c1.append(price)
            leftovers -= 1

    return new_c1


# Create individual figures for each contract, place tweets over them all the same.
def plot_individual_contracts(contracts):
    prices = read_prices()
    tweets = read_tweet_timestamps()

    plot_count = 1
    for contract in contracts:
        contract_prices = list(filter(lambda c: c[0] == contract, prices))
        price_data = list(map(lambda c: c[2], contract_prices))
        timestamps = list(map(lambda c: c[1], contract_prices))

        plt.subplot(len(contracts) * 100 + 10 + plot_count)
        plt.title(CONTRACT_NAMES[contract])
        plt.plot(timestamps, price_data)
        plot_count += 1

        for tweet in tweets:
            count, ts = tweet
            plt.axvline(x=ts, color='r')

    plt.show()

def cluster_tweets(tweets):
    '''
    Start with an empty list
    '''
    clusters = []
    current = []
    for tweet in tweets:
        if current == []:
            current.append(tweet)
            continue
        _, last_ts = current[-1]
        _, ts = tweet

        if ts - last_ts < 30 * 60:
            current.append(tweet)
        else:
            clusters.append(current)
            current = []
            current.append(tweet)

    return clusters

# Check the correlation between contracts
# 160 or more, 109 or fewer
# 16992, 16998
def contract_correlation(c1_id, c2_id):
    prices = read_prices()

    c1 = list(filter(lambda c: c[0] == c1_id, prices))
    c2 = list(filter(lambda c: c[0] == c2_id, prices))



    c1_prices = list(map(lambda c: int(float(c[2]) * 100), c1))
    c2_prices = list(map(lambda c: int(float(c[2]) * 100), c2))

    #print(c1_prices)

    if len(c1) < len(c2):
        c1_prices = pad_prices(c1_prices, c2_prices)
    elif len(c2) < len(c1):
        c2_prices = pad_prices(c2_prices, c1_prices)

    return pearsonr(c1_prices[-100:], c2_prices[-100:])[0]

def find_pair_correlations():
    # Run this on all adjacent contracts? (Or perhaps different baskets?)
    #print(contract_correlation('16998', '16992'))
    #market_contracts = ['16998', '16993', '16996', '16997', '16995', '16994', '16992']
    market_contracts = ['17130', '17127', '17126', '17128', '17125', '17129', '17124']
    #for c1, c2 in zip(market_contracts, market_contracts[1:]):
    #    print(f'correlation {contract_correlation(c1, c2): .2f} [{CONTRACT_NAMES[c1]}] [{CONTRACT_NAMES[c2]}]')

    # Correlation of all possible pairings
    for c1, c2 in combinations(market_contracts, 2):
        print(f'correlation {contract_correlation(c1, c2): .2f} [{CONTRACT_NAMES[c1]}] [{CONTRACT_NAMES[c2]}]')




def attempt_trades():
    # Start via negative correlation between '109 or fewer' and '160 or more'
    # We will have to do realtime calculations, and go from there (since we don't know the correlation
    # in the future.
    prices = read_prices()

    c1 = list(filter(lambda c: c[0] == '16998', prices))
    c2 = list(filter(lambda c: c[0] == '16992', prices))


    c1_prices = list(map(lambda c: c[2], c1))
    c2_prices = list(map(lambda c: c[2], c2))

    if len(c1) < len(c2):
        c1_prices = pad_prices(c1_prices, c2_prices)
    elif len(c2) < len(c1):
        c2_prices = pad_prices(c2_prices, c1_prices)

    c1_past_data = []
    c2_past_data = []
    step = 1
    for c1_price, c2_price in zip(c1_prices, c2_prices):
        print(f'c1: {c1_price} c2: {c2_price}')
        if c1_past_data == [] or c2_past_data == []:
            c1_past_data.append(c1_price)
            c2_past_data.append(c2_price)
            step+=1
            continue


        # Cut up test set for all points where corr remains >= -.8
        # Then, divide this in half, a test set and run set.
        # See how it performs.
        # Other question is, can we estimate what the price increase will be?
        # Can the correlation ratio be used to estimate this?
        
        corr = pearsonr(c1_past_data, c2_past_data)[0]
        if corr <= -.80:
            #if c2_price > c2_past_data[-1]:
            #    print('short c1')
            if c1_price < c1_past_data[-1]:
                print('buy c2')
        #print(f'{step:4d} corr: {pearsonr(c1_past_data, c2_past_data)[0]: .2f}')
        c1_past_data.append(c1_price)
        c2_past_data.append(c2_price)
        step+=1

    # So say we start making trades at a correlation >= .8
    # What would happen is if we see a movement in price of one asset, 
    # then we expect the opposite.


#find_pair_correlations()
#attempt_trades()
#plot_price_and_pace()
#pace_strat()

def get_contract_prices(contract_id):
    return list(filter(lambda c: c[0] == contract_id, read_prices()))

def analyze_tweet_cluster_profit(contracts):
    '''
    Basic idea is to look at what maximum gains would've been had we bought at the start
    of a cluster, and then sold sometime in between the start of another cluster.

    Need to get price data between start of 1st group and 2nd group
    '''
    tweets = read_tweet_timestamps()
    clusters = cluster_tweets(tweets)
    for contract in contracts:
        prices = get_contract_prices(contract)

        def get_prices_between_groups(group1, group2):
            _, start_ts = group1[0]
            _, end_ts = group2[0]   # Group 1 to start of group 2
            return list(map(lambda p: p[2], filter(lambda p: start_ts < p[1] < end_ts, prices)))


        '''
        for group1, group2 in zip(clusters, cluster[1:]):
            _, start_ts = group1[0]
            _, end_ts = group2[-1]
            between_prices = list(filter(lambda p: p[1] 
        '''

        # See what the average profit is in the window after a group
        for group in clusters:
            _, start_ts = group[0]
            _,_, closest_price = list(filter(lambda p: p[0][1] <= start_ts <= p[1][1], zip(prices, prices[1:])))[0][0]
            next_prices = list(map(lambda p: p[2], list(filter(lambda p: p[1] > start_ts, prices))[:20]))
            avg = np.average(next_prices)
            print(f'{CONTRACT_NAMES[contract]} profit (20 window): ' +\
                    f'A:({np.average(next_prices) - closest_price:.2f}) M:({max(next_prices) - closest_price})')
        print('')

        continue

        volatility = []
        #for group in clusters:
        for group1, group2 in zip(clusters, clusters[1:]):
            _, start_ts = group1[0]
            _,_, closest_price = list(filter(lambda p: p[0][1] <= start_ts <= p[1][1], zip(prices, prices[1:])))[0][0]

            inbetween_prices = get_prices_between_groups(group1, group2)
            volatility.append(np.var(inbetween_prices))
            print(f'[{CONTRACT_NAMES[contract]}]\n' +\
                    f'    max profit: {max(inbetween_prices) - closest_price}\n' +\
                    f'    max loss: {min(inbetween_prices) - closest_price}\n' +\
                    f'    volatility: {np.var(inbetween_prices):.2f}')

        print(f'    avg volatility: {np.average(volatility):.2f}')

def plot_tweet_clusters():
    tweets = read_tweet_timestamps()
    clusters = cluster_tweets(tweets)
    plot_contracts()
    for group in clusters:
        # Start is red
        # End is blue
        # If cluster contains only 1 item, green line
        _, start_ts = group[0]
        _, end_ts = group[-1]
        if start_ts == end_ts:
            plt.axvline(x=start_ts, color='g')
        else:
            plt.axvline(x=start_ts, color='b')
            plt.axvline(x=end_ts, color='r')

    print(clusters)
    plt.show()
pace_strat()
#plot_price_and_pace()
#plot_tweet_clusters()
#analyze_tweet_cluster_profit(['17130', '17127', '17126', '17128', '17125', '17129', '17124'])
#find_pair_correlations()
#plot_contracts(show_tweets=True)
#plot_individual_contracts(['17130', '17127', '17126', '17128', '17125', '17129', '17124'])
#plt.show()

#print(ts)
#print(prices)
