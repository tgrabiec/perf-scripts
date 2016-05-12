#!/usr/bin/env python
import sys
import events

min_duration = 0.000010
# min_duration = 0.0004

for elem in events.get_sched_timeline(sys.stdin):
    flags = ''
    if elem.state == events.TimelineElement.WOKEN:
        delta = elem.wakeup_vruntime_delta
        if delta:
            delta_str = '%f [s]' % delta
            if delta < min_duration:
                flags += '!'
        else:
            delta_str = '?'
        print("%-20s %f: duration=%f [s] %-10s vruntime_delta=%-13s %5s" % (elem.proc, elem.start, elem.duration, elem.state, delta_str, flags))
    else:
        print("%-20s %f: duration=%f [s] %-10s" % (elem.proc, elem.start, elem.duration, elem.state))
