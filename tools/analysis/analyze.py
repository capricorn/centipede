import json
import time
import datetime
import itertools
from statistics import mean
from statistics import mode
from statistics import stdev

from scipy import stats
import pytz
import matplotlib.pyplot as plt

''' TODO

- Figure out how to convert times to ET so you can figure out when 12pm ET hits.
- Look into utilizing geolocation (if available) to adjust the time when a tweet is made 
- May also want to split according to work hours
- Need to have a method that automatically dumps shares as risk increases
'''

def read_archive():
    with open('archive.json', 'r') as f:
        return json.loads(f.read())

def plot_tweets_by_hours(data):
    dates = map(lambda k: time.strptime(k['created_at'], '%a %b %d %H:%M:%S %z %Y'), data)
    dates = map(lambda k: datetime.datetime(*k[:6], tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')), dates)

    hours = { i : 0 for i in range(0, 24) }

    for ts in dates:
        hours[ts.hour] += 1

    avg_hours = list(map(lambda k: k / len(hours), hours.values()))

    print(hours)
    print(avg_hours)
    plt.bar(hours.keys(), hours.values())
    plt.ylabel('tweet count')
    plt.xlabel('hour')
    plt.suptitle('Trump tweet count by hour')
    plt.show()

# This needs to start counting from noon of the start until now.
# Also should handle cross-month dates (work on this later)
def past_week(data):
    start_day = 24
    start_month = 5

    dates = map(lambda k: time.strptime(k['created_at'], '%a %b %d %H:%M:%S %z %Y'), data)
    #dates = map(lambda k: datetime.datetime(*k[:6]).astimezone(pytz.timezone('US/Eastern')), dates)
    #return list(filter(lambda k: 17 <= k.tm_mday <= 22 and k.tm_mon == 5, dates))
    # Create a filter that filters out any dates on the start date that are before noon
    #return list(filter(lambda k: 17 <= k.tm_mday <= 22 and k.tm_mon == 5, dates))
    dates = filter(lambda k: start_day <= k.tm_mday <= (start_day + 7) and k.tm_mon == start_month, dates)
    dates = filter(lambda k: not (k.tm_mday == start_day and k.tm_mon == start_month and k.tm_hour < 12), dates)
    return list(dates)
                
def avg_mornings(data):
    dates = map(lambda k: time.strptime(k['created_at'], '%a %b %d %H:%M:%S %z %Y'), data)
    return (len(list(filter(lambda k: 0 <= k.tm_hour <= 12, dates))) / len(list(data))) * 100

# Need to utilize a partial function for filter
def group(lst, pred):
    groupings = []

    while lst != []:
        lst = lst.pop(0)
        group = list(filter(pred, lst))
        lst = list(filter(lambda k: k not in group, lst))

        groupings.append(group)

    return groupings

def tweets_per_day(data):
    dates = list(map(lambda k: time.strptime(k['created_at'], '%a %b %d %H:%M:%S %z %Y'), data))
    groupings = []
    # begin on start date
    # need an interator so we can remove entries?
    while dates != []:
        date = dates.pop(0)
        same_days = list(filter(lambda d: date.tm_mday == d.tm_mday and date.tm_mon == d.tm_mon and date.tm_year == d.tm_year, dates))
        dates = list(filter(lambda d: d not in same_days, dates))

        groupings.append(same_days)

    return groupings
    '''
    for group in groupings:
        print(f'{group}\n')
    '''


    '''
    for day in iterator:
        filter(lambda d: d.day == day.day and d.month == day.month and d.year == day.year, dates)
    '''


data = read_archive()
print(len(data))
start = datetime.datetime.strptime(data[-1:][0]['created_at'], '%a %b %d %H:%M:%S %z %Y').astimezone(pytz.timezone('US/Eastern'))
end = datetime.datetime.strptime(data[0]['created_at'], '%a %b %d %H:%M:%S %z %Y').astimezone(pytz.timezone('US/Eastern'))
'''
print(*start_time)
start = datetime.datetime(*start_time[:6], tzinfo=pytz.utc).astimezone('US/Eastern')
end = datetime.datetime(*end_time[:6], tzinfo=pytz.utc).astimezone('US/Eastern')
'''

days = (end - start).days
print(f'Days: {days}')
print(f'tweets/day: {len(data) / days}')

#print(avg_mornings(data))
print(f'Percentage tweets 0 - 12: {avg_mornings(data)}')

groups = tweets_per_day(data)
groups = list(map(lambda g: len(g), groups))
#plt.bar([i for i in range(len(groups))], groups)

print(groups)
print(f'mean: {mean(groups):.2f}')
print(f'var: +-{stdev(groups):.2f}')
#print(sorted(groups))
groups.sort()
#print(stats.relfreq(groups))
#print(list(itertools.groupby(groups)))

bins = itertools.groupby(groups)
size = len(list(itertools.groupby(groups)))
print(f'buckets: {size}')
#for b in bins:
#    print(list(b[1]))
#rfreq = list(map(lambda k: len(list(k[1]))/len(list(bins)), bins))
#print(len(list(bins)))
#print(bins.size())
rfreq = list(map(lambda k: len(list(k[1])) / len(groups), bins))
keys = list(map(lambda k: k[0], itertools.groupby(groups)))
print(f'keys: {keys}')
#print(f'Different tweets/day sizes: {len(list(itertools.groupby(groups)))}')
# maybe you should try sampling from this distribution, play around with simulations 
print(f'freqs: {rfreq}')
print(f'{sum(rfreq)}')
print(f'sfreqs: {list(itertools.accumulate(rfreq))}')
#for k, g in itertools.groupby(groups):
#    print(f'k: {k} -> {list(g)}')

# where is the cdf closest to 50%?
plt.bar(keys, rfreq)
plt.show()

'''
print(len(past_week(data)))
week = { i : 0 for i in range(17, 23) }
for w in past_week(data):
    week[w.tm_mday] += 1

plt.bar(week.keys(), week.values())
plt.show()
'''
#plot_tweets_by_hours(data)
