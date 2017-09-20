#!/usr/bin/env python
import sys
import events
import filters
import argparse

parser = argparse.ArgumentParser(description='List scheduling history')
parser.add_argument('--wakeup-granularity', type=float, default=0.000010)
filters.add_all_filters(parser)
args = parser.parse_args()

filter = filters.get_filter(args)
wakeup_granularity = args.wakeup_granularity

for elem in events.get_sched_timeline(sys.stdin, generate_runnable=True):
    if not filter(elem):
        continue
    flags = ''
    if elem.state == events.TimelineElement.WOKEN:
        delta = elem.wakeup_vruntime_delta
        if delta:
            delta_str = '%f [s]' % delta
            if delta < wakeup_granularity:
                flags += '!'
        else:
            delta_str = '?'
        print("[%03d] %-20s %f: duration=%f [s] %-10s vruntime_delta=%-13s %5s" % (elem.cpu, elem.proc, elem.start, elem.duration, elem.state, delta_str, flags))
    else:
        print("[%03d] %-20s %f: duration=%f [s] %-10s" % (elem.cpu, elem.proc, elem.start, elem.duration, elem.state))
