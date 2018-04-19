import matplotlib
import matplotlib.pyplot as pyplot
import json

with open('slew.json') as f:
    data = json.load(f)

fig, ax1 = pyplot.subplots()
ax1.plot(data['time'], data['era'], label='era')
#ax1.plot(data['time'], data['edec'], label='rpv')
ax1.legend(loc=0)
#pyplot.title('p = 0.7, i = 0, d = 0')
ax2 = ax1.twinx()
ax2.plot(data['time'], data['rv'], '-g', label='rv')
ax2.legend(loc=0)
pyplot.show()