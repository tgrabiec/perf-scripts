import argparse
import events

def add_state_filter(parser, required=False):
    parser.add_argument('--state', type=str, choices=["woken", "preempted", "sleeping", "sleeping_uninterruptibly", "running", "delayed"], required=required)

def add_process_filter(parser, required=False):
    parser.add_argument('--proc', required=required)

def add_cpu_filter(parser, required=False):
    parser.add_argument('-C', '--cpu', type=int, required=required)

def add_all_filters(parser):
    add_state_filter(parser)
    add_process_filter(parser)
    add_cpu_filter(parser)

def get_filter(args):
    filters = []

    if not hasattr(args, 'state') or not args.state:
        filters.append(lambda elem: True)
    elif args.state == 'sleeping':
        filters.append(lambda elem: elem.state.is_sleep)
    elif args.state == 'delayed':
        filters.append(lambda elem: elem.state.is_delayed)
    else:
        state = events.state_by_name[args.state.upper()]
        filters.append(lambda elem: elem.state == state)

    if hasattr(args, 'proc') and args.proc:
        filters.append(lambda elem: args.proc in elem.proc)

    if hasattr(args, 'cpu') and args.cpu:
        filters.append(lambda elem: elem.cpu == args.cpu)

    return lambda elem: all(f(elem) for f in filters)
