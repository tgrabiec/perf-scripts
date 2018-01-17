#!/usr/bin/env python3
import sys
import events
import math
import argparse
import filters
import bisect
from collections import defaultdict

parser = argparse.ArgumentParser(description='Print histogram of scheduling delay')
parser.add_argument('--max', '-m', type=float, default=1.0)
parser.add_argument('--proc', '-p', required=True)
parser.add_argument('-C', '--cpu', type=int)
args = parser.parse_args()

max_value = args.max

if args.cpu:
    cpu_filter = lambda elem: elem.cpu == args.cpu
else:
    cpu_filter = lambda elem: True

def filter(elem):
    return elem.proc.startswith(args.proc) and cpu_filter(elem)

buckets = []
causes = [] # list of map(proc -> float)
thresholds = []
th = 0
while True:
    th = max(0.000001, th * 1.33)
    thresholds.append(th)
    buckets.append(0)
    causes.append(defaultdict(lambda: 0.0))
    if th >= max_value:
        break
thresholds.append(9999999999.0) # +inf
buckets.append(0)
causes.append(defaultdict(lambda: 0.0))

running_per_cpu = defaultdict(lambda: defaultdict(lambda: 0.0))
runnable_on_cpu = defaultdict(lambda: None)
processed = 0
for elem in events.get_sched_timeline(sys.stdin, generate_runnable=True):
    processed += 1
    if processed % (8*1024) == 0:
        print('.', end='')
        sys.stdout.flush()
    if filter(elem):
        if elem.state == events.TimelineElement.IS_RUNNABLE:
            runnable_on_cpu[elem.cpu] = elem.start
        elif elem.state.is_running:
            running_per_cpu[elem.cpu].clear()
            runnable_on_cpu[elem.cpu] = None
        elif elem.state.is_delayed:
            i = bisect.bisect_left(thresholds, elem.duration)
            buckets[i] += elem.duration
            c = causes[i]
            total_duration = 0
            for proc, duration in running_per_cpu[elem.cpu].items():
                c[proc] += duration
                total_duration += duration
            if total_duration != elem.duration:
                print('ERROR: %f: %f != %f' % (elem.start, total_duration, elem.duration))

    elif elem.state.is_running:
        start = runnable_on_cpu[elem.cpu]
        if start:
            running_per_cpu[elem.cpu][elem.proc] += elem.start + elem.duration - max(elem.start, start)

max_count = max(buckets)
width = 40.0
if max_count:
    scale = width / max(buckets)
else:
    scale = 1

print("%21s %12s" % ('duration [s]', 'sum'))
print("%21s %12s" % ('------------', '-----------'))

for i, total_delay in enumerate(buckets):
    count_pattern = '%12f'
    print(("%20.9f: " + count_pattern + " %s") % (thresholds[i], total_delay, '#' * int(math.ceil(scale * total_delay))))
    if causes[i]:
        print('\n'.join(('%.2f%%: %s' % (duration * 100.0 / total_delay, proc) for proc, duration  in sorted(causes[i].items(), key=lambda e: -e[1]))))

print("total: %10f" % (sum(buckets)))
