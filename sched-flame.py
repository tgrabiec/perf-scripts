#!/usr/bin/env python
import sys
import events
import argparse
import filters

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates flame graph for given state')
    filters.add_state_filter(parser, required=True)
    filters.add_process_filter(parser)
    args = parser.parse_args()
    filter = filters.get_filter(args)
    for elem in events.get_sched_timeline(sys.stdin):
        if not filter(elem):
            continue
        prefix = elem.proc
        if elem.start_stack:
            prefix += ';' + ';'.join(reversed(elem.start_stack))
        print('%s %f' % (prefix, elem.duration))
