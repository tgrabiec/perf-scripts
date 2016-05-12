#!/usr/bin/env python
import sys
import events
import math
import argparse


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--state', '-s', type=str, choices=["woken", "preempted", "sleeping", "sleeping_uninterruptibly", "running", "delayed"], required=True)
parser.add_argument('--max', '-m', type=float, default=1.0)
parser.add_argument('--product', '-p', action='store_true')
parser.add_argument('--proc', default='scylla')
args = parser.parse_args()


max_value = args.max

if args.state == 'sleeping':
    state_filter = lambda elem: elem.state.is_sleep
elif args.state == 'delayed':
    state_filter = lambda elem: elem.state.is_delayed
else:
    state = events.state_by_name[args.state.upper()]
    state_filter = lambda elem: elem.state == state

filter = lambda elem: state_filter(elem) and args.proc in elem.proc

buckets = []
thresholds = []
th = 0
while True:
    th = max(0.000001, th * 1.33)
    thresholds.append(th)
    buckets.append(0)
    if th >= max_value:
        break
thresholds.append(9999999999.0) # +inf
buckets.append(0)

for elem in events.get_sched_timeline(sys.stdin):
    if filter(elem):
        for i, th in enumerate(thresholds):
            if elem.duration < th:
                if args.product:
                    buckets[i] += elem.duration
                else:
                    buckets[i] += 1
                break


max_count = max(buckets)
if max_count:
    scale = 40.0 / max(buckets)
else:
    scale = 1

print("%21s %12s" % ('duration [s]', ('count', 'sum')[args.product]))
print("%21s %12s" % ('------------', '-----------'))

for i, count in enumerate(buckets):
    count_pattern = ('%12d', '%12f')[args.product]
    print(("%20.9f: " + count_pattern + " %s") % (thresholds[i], count, '#' * int(math.ceil(scale * count))))

print("total: %10f" % (sum(buckets)))
