#!/usr/bin/env python
import sys
import events
import math
import argparse
import filters

parser = argparse.ArgumentParser(description='Print histogram of events')
parser.add_argument('--max', '-m', type=float, default=1.0)
parser.add_argument('--sum', action='store_true')
filters.add_args(parser)
args = parser.parse_args()

max_value = args.max
filter = filters.get_filter(args)

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
                if args.sum:
                    buckets[i] += elem.duration
                else:
                    buckets[i] += 1
                break


max_count = max(buckets)
if max_count:
    scale = 40.0 / max(buckets)
else:
    scale = 1

print("%21s %12s" % ('duration [s]', ('count', 'sum')[args.sum]))
print("%21s %12s" % ('------------', '-----------'))

for i, count in enumerate(buckets):
    count_pattern = ('%12d', '%12f')[args.sum]
    print(("%20.9f: " + count_pattern + " %s") % (thresholds[i], count, '#' * int(math.ceil(scale * count))))

print("total: %10f" % (sum(buckets)))
