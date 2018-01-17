#!/usr/bin/env python
import sys
import events
import math
import argparse
import filters
from collections import defaultdict

parser = argparse.ArgumentParser(description='Prints summary which mimics \'perf sched latency\'')
filters.add_process_filter(parser)
filters.add_cpu_filter(parser)
args = parser.parse_args()

filter = filters.get_filter(args)

class StatsCollector:
    def __init__(self):
        self.runtime = 0
        self.switches = 0
        self.delays = []
        self.max_delay_time = 0
        self.max_delay = 0

    def add_delay(self, time, duration):
        self.delays.append(duration)
        if not self.max_delay_time or duration > self.max_delay:
            self.max_delay = duration
            self.max_delay_time = time

    def add_runtime(self, runtime):
        self.switches += 1
        self.runtime += runtime

    def avg_delay(self):
        if not self.delays:
            return 0
        return sum(self.delays) / len(self.delays)

    def max_delay(self):
        if not self.delays:
            return 0
        return max(self.delays)

stats_by_proc = defaultdict(StatsCollector)
for elem in events.get_sched_timeline(sys.stdin):
    if not filter(elem):
        continue
    if elem.state.is_running:
        stats_by_proc[elem.proc].add_runtime(elem.duration)
    elif elem.state.is_delayed:
        stats_by_proc[elem.proc].add_delay(elem.start, elem.duration)

print("""
 ---------------------------------------------------------------------------------------------------------------
  Task                  |   Runtime ms  | Switches | Average delay ms | Maximum delay ms | Maximum delay at     |
 ---------------------------------------------------------------------------------------------------------------""")

def millis(seconds):
    return '%.3f' % (seconds * 1000)

total_runtime = 0
total_switches = 0
for proc, stats in sorted(stats_by_proc.items(), key=lambda e: -e[1].max_delay):
    if proc.startswith('swapper'):
        continue
    total_runtime += stats.runtime
    total_switches += stats.switches
    print("  %-21s | %10s ms | %8d | avg: %8s ms | max: %8s ms | max at: %.6f s" %
          (proc, millis(stats.runtime), stats.switches, millis(stats.avg_delay()), millis(stats.max_delay), stats.max_delay_time))

print(""" -----------------------------------------------------------------------------------------
  TOTAL:                | %10s ms | %8d |
 ---------------------------------------------------
""" % (millis(total_runtime), total_switches))
