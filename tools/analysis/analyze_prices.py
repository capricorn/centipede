import matplotlib.pyplot as plt

def read_csv(filename):
    with open(filename, 'r') as f:
        return f.read().split('\n')

names = {
    '16810': '89 or fewer',
    '16807': '90 - 99',
    '16806': '100 - 109',
    '16805': '110 - 119',
    '16808': '120 - 129',
    '16809': '130 - 139',
    '16804': '140+'
}

contracts = ['16810','16807','16806','16805','16808','16809','16804']
data = read_csv('prices.txt')

plot = 1
for c in contracts:
    contract_data = list(map(lambda k: k.split(','), (filter(lambda k: k.split(',')[0] == c, data))))
    print(contract_data)
    base_time = float(contract_data[0][1])

    plt.subplot(len(contracts), 1, plot)
    plt.title(names[c])
    # Price swing after a tweet
    plt.axvline(x=(1565286680 - base_time), color='r')
    plt.plot(list(map(lambda k: float(k[1]) - base_time, contract_data)), list(map(lambda k: k[2], contract_data)))
    plot += 1

plt.show()
