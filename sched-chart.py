#!/usr/bin/env python
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import events
import filters
from collections import defaultdict
from matplotlib.colors import ColorConverter

parser = argparse.ArgumentParser(description='Print histogram of events')
filters.add_args(parser)
args = parser.parse_args()
filter = filters.get_filter(args)

# x_range = (1029553.184, 1029553.190)
#x_range = (1029333.805010, 1029333.825010)
x_range = None


fig, ax = plt.subplots()

palette = {
    events.TimelineElement.RUNNING: 'green',
    events.TimelineElement.SLEEPING: 'white',
    events.TimelineElement.SLEEPING_UNINTERRUPTIBLY: 'lightblue',
    events.TimelineElement.PREEMPTED: 'lightgrey',
    events.TimelineElement.WOKEN: 'red',
}

rgb_palette = dict((k, ColorConverter().to_rgb(c)) for k, c in palette.iteritems())

class ProcHistory:
    def __init__(self, y):
        self.y = y
        self.bars = list()
        self.colors = list()

class Rows:
    def __init__(self, height):
        self.height = height
        self.yticks = []
        self.yticklabels = []
        self.y = height + 5

    def new_row(self, label):
        self.yticks.append(self.y + self.height/2)
        self.yticklabels.append(label)
        result = self.y
        self.y += self.height
        return result

    def annotate(self, ax):
        ax.set_yticks(self.yticks)
        ax.set_yticklabels(self.yticklabels)

history_by_proc = {}
rows = Rows(height=10)

lines = list(sys.stdin)
min_time = None

for elem in events.get_sched_timeline(lines):
    if not filter(elem):
        continue
    if not min_time:
        min_time = elem.start
    if not elem.proc in history_by_proc:
        hist = ProcHistory(rows.new_row(elem.proc))
        history_by_proc[elem.proc] = hist
    else:
        hist = history_by_proc[elem.proc]

    h = rows.height * 0.75
    color = rgb_palette[elem.state]
    hist.bars.append((elem.start, elem.duration))
    hist.colors.append(color)

for proc, hist in history_by_proc.iteritems():
    ax.broken_barh(hist.bars, (hist.y, rows.height - 1), facecolors=hist.colors, edgecolor='face')

if x_range:
    ax.set_xlim(x_range[0], x_range[1])
else:
    ax.set_xlim(min_time, min_time + 0.05)
ax.set_xlabel('time [s]')
rows.annotate(ax)

ax.grid(True)
ax.annotate('on-cpu', (61, 25),
            xytext=(0.8, 0.9), textcoords='axes fraction',
            arrowprops=dict(facecolor='black', shrink=0.05),
            fontsize=16,
            horizontalalignment='right', verticalalignment='top')

patches = []
labels = []
for state, color in palette.iteritems():
    label = str(state).lower()
    patches.append(mpatches.Patch(color=color, label=label))
    labels.append(label)
plt.legend(patches, labels, 'upper right')

plt.show()
