#!/usr/bin/env python
import sys
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import events
from collections import defaultdict
from matplotlib import collections  as mc
import matplotlib.cm as cmx
import matplotlib.colors as colors

#x_range = (1029553.184, 1029553.190)
x_range = (1322034.361148993, 1322034.3851439261)
#x_range = None

fig, ax = plt.subplots()

segments_by_proc = defaultdict(list)
min_x = None
min_y = None
for proc, x1, y1, x2, y2 in events.get_vruntime_history(events.get_traces(sys.stdin)):
    if not proc.startswith('a.out'):
        continue
    print(proc, x1, y1, x2, y2)
    if x_range:
        if x2 > x_range[0] and x1 < x_range[1]:
            if not min_x:
                min_x = x1
                min_y = y1
        else:
            continue
    else:
        if not min_x:
            min_x = x1
            min_y = y1
    lines = segments_by_proc[proc]
    lines.append([(x1, y1), (x2, y2)])

colors_by_proc = {}
cmap = plt.get_cmap('jet', len(segments_by_proc))
for proc, lines in segments_by_proc.items():
    c = cmap(len(colors_by_proc))
    colors_by_proc[proc] = c
    mpl.rcParams['lines.color'] = c
    mpl.rcParams['lines.linewidth'] = 2
    ax.add_collection(mc.LineCollection(lines))
    x = []
    y = []
    for start, end in lines:
        x.append(start[0])
        y.append(start[1])
        x.append(end[0])
        y.append(end[1])
    ax.scatter(x, y, s=10, c=c, alpha=0.5)

if x_range:
    ax.set_xlim(x_range[0], x_range[1])
    ax.set_ylim(min_y, min_y + x_range[1] - x_range[0])
else:
    ax.set_xlim(min_x, min_x + 1)
    ax.set_ylim(min_y, min_y + 1)

ax.set_xlabel('time [s]')
ax.set_ylabel('vruntime [s]')

ax.grid(True)
ax.annotate('vruntime', (61, 25),
            xytext=(0.8, 0.9), textcoords='axes fraction',
            arrowprops=dict(facecolor='black', shrink=0.05),
            fontsize=16,
            horizontalalignment='right', verticalalignment='top')

patches = []
labels = []
for proc, c in colors_by_proc.iteritems():
    label = proc
    patches.append(mpatches.Patch(color=c, label=label))
    labels.append(label)
plt.legend(patches, labels, 'upper right')

plt.show()
