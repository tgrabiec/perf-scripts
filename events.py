def get_prev_proc(columns):
    proc = columns[5]
    if 'comm' in proc:
        return proc.split('=')[1] + ':' + columns[6].split('=')[1]
    return proc

def get_next_proc(columns):
    old_proc = columns[5]
    if 'comm' in old_proc:
        return columns[10].split('=')[1] + ':' + columns[11].split('=')[1]
    return columns[9]

def processes(lines):
    history = {}
    for line in lines:
        columns = line.split()
        name = columns[0]
        pid = columns[1]
        process = name + ":" + pid
        cpu = columns[2]
        if process not in history:
            history[process] = ()
            yield process

def on_cpu_duration(lines):
    history = {}
    for line in lines:
        columns = line.split()
        name = columns[0]
        pid = columns[1]
        process = name + ":" + pid
        cpu = columns[2]
        time = float(columns[3].rstrip(':'))
        event = columns[4].rstrip(':')
        if event == 'sched:sched_switch':
            old_proc=get_prev_proc(columns)
            new_proc=get_next_proc(columns)
            if old_proc in history:
                old_time = history[old_proc]
                duration = time - old_time
                yield old_proc, old_time, duration
                del history[old_proc]
            history[new_proc] = time

class Event:
    def __init__(self, name):
        self.name = name

class SchedStatRuntimeEvent(Event):
    def __init__(self, proc, runtime, vruntime):
        Event.__init__(self, "sched:sched_stat_runtime")
        self.proc = proc
        self.runtime = runtime
        self.vruntime = vruntime

def parse_proc_name(columns):
    try:
        if 'comm' in columns[0]:
            proc = columns[0].split('=')[1]
            columns.pop(0)
            while not 'pid' in columns[0]:
                proc += columns[0]
                columns.pop(0)
            proc += ':' + columns[0].split('=')[1]
            columns.pop(0)
        else:
            proc = columns[0]
            columns.pop(0)
    except:
        print(columns)
        raise
    return proc

def parse_sched_stat_runtime(columns):
    proc = parse_proc_name(columns)
    runtime = float(columns[0].split('=')[1])
    vruntime = float(columns[2].split('=')[1])
    return SchedStatRuntimeEvent(proc, runtime, vruntime)

class SchedWakeupEvent(Event):
    def __init__(self, proc, cpu):
        Event.__init__(self, "sched:sched_wakeup")
        self.cpu = cpu
        self.proc = proc

def parse_sched_wakeup(columns):
    proc = parse_proc_name(columns)
    if '=' in columns[2]:
        cpu = int(columns[2].split('=')[1])
    else:
        cpu = int(columns[2].split(':')[1])
    return SchedWakeupEvent(proc, cpu)

class SchedSwitchEvent(Event):
    def __init__(self, old_proc, old_state, new_proc):
        Event.__init__(self, "sched:sched_switch")
        self.new_proc = new_proc
        self.old_state = old_state
        self.old_proc = old_proc

def parse_sched_switch(columns):
    old_proc = parse_proc_name(columns)
    if '=' in columns[1]:
        old_state = columns[1].split('=')[1]
    else:
        old_state = columns[1]
    columns = columns[3:]
    new_proc = parse_proc_name(columns)
    return SchedSwitchEvent(old_proc, old_state, new_proc)

state_by_name = {}

class TimelineElement:
    class State:
        def __init__(self, text, is_sleep=False, is_delayed=False, is_running=False):
            state_by_name[text] = self
            self.is_sleep = is_sleep
            self.is_delayed = is_delayed
            self.is_running = is_running
            self.text = text
        def __str__(self):
            return self.text
        def __repr__(self):
            return self.text
        def is_sleep(self):
            return self.is_sleep
        def is_delayed(self):
            return self.is_delayed
        def is_running(self):
            return self.is_running

    WOKEN = State("WOKEN", is_delayed=True)
    PREEMPTED = State("PREEMPTED", is_delayed=True)
    SLEEPING = State("SLEEPING", is_sleep=True)
    SLEEPING_UNINTERRUPTIBLY = State("SLEEPING_UNINTERRUPTIBLY", is_sleep=True)
    RUNNING = State("RUNNING", is_running=True)
    IS_RUNNABLE = State("IS_RUNNABLE")

    def __init__(self, cpu, proc, start, duration, state, wakeup_vruntime_delta=None, vruntime=None, start_stack=None, end_stack=None):
        self.cpu = cpu
        self.proc = proc
        self.start = start
        self.duration = duration
        self.state = state
        self.wakeup_vruntime_delta = wakeup_vruntime_delta
        self.vruntime = vruntime
        self.start_stack = start_stack
        self.end_stack = end_stack

class Trace:
    def __init__(self, time, curr, cpu, event, stack):
        self.event = event
        self.cpu = cpu
        self.curr = curr
        self.time = time
        self.stack = stack

#  sudo perf record \
#    -e sched:sched_stat_runtime \
#    -e sched:sched_wakeup \
#    -e sched:sched_switch
def get_traces(lines):
    i = iter(lines)
    line = i.next()
    while True:
        if line.startswith('#') or line.startswith('\n'):
            line = i.next()
            continue
        columns = line.split()
        name_and_pid = []
        while not columns[0].startswith('['):
            name_and_pid.append(columns[0])
            columns.pop(0)
        name = ' '.join(name_and_pid[:-1])
        pid = name_and_pid[-1]
        curr = name + ":" + pid
        cpu = int(columns[0].lstrip('[').rstrip(']'))
        columns.pop(0)
        time = float(columns[0].rstrip(':'))
        columns.pop(0)
        event_name = columns[0].rstrip(':')
        columns.pop(0)
        event = None
        if event_name == 'sched:sched_stat_runtime':
            event = parse_sched_stat_runtime(columns)
        elif event_name == 'sched:sched_wakeup':
            event = parse_sched_wakeup(columns)
        elif event_name == 'sched:sched_switch':
            event = parse_sched_switch(columns)

        # Parse stacktrace
        line = i.next()
        stack = []
        while line.startswith('\t'):
            stack.append(line.strip('\t\n ').split()[1])
            line = i.next()

        if event:
            yield Trace(time, curr, cpu, event, stack)

def get_vruntime_history(traces):
    def nano_to_sec(nanos):
        return float(nanos) / 1e9
    for trace in traces:
        ev = trace.event
        if ev.name == 'sched:sched_stat_runtime':
            yield ev.proc, trace.time - nano_to_sec(ev.runtime), nano_to_sec(ev.vruntime - ev.runtime), trace.time, nano_to_sec(ev.vruntime)

def get_sched_timeline(lines, generate_runnable=False):
    wakeup_history = {}
    switched_out = {}
    switched_in = {}
    vruntimes = {}
    for trace in get_traces(lines):
        time = trace.time
        curr = trace.curr
        ev = trace.event
        cpu = trace.cpu
        if ev.name == 'sched:sched_stat_runtime':
            vruntimes[ev.proc] = ev.vruntime
        elif ev.name == 'sched:sched_wakeup':
            # Don't generate wakeup blocks for preempted processes
            if not ev.proc in switched_out or not 'R' in switched_out[ev.proc][1]:
                delta = None
                if ev.cpu == cpu and curr in vruntimes and ev.proc in vruntimes:
                    delta = float(vruntimes[curr] - vruntimes[ev.proc]) / 1e9
                wakeup_history[ev.proc] = (time, delta)
                if generate_runnable:
                    yield TimelineElement(ev.cpu, ev.proc, time, 0, TimelineElement.IS_RUNNABLE)
        elif ev.name == 'sched:sched_switch':
            old_proc = ev.old_proc
            new_proc = ev.new_proc
            switched_out[old_proc] = (time, ev.old_state, trace.stack)
            switched_in[new_proc] = time
            if old_proc in wakeup_history:
                del wakeup_history[old_proc]
            if old_proc in switched_in:
                switched_in_at = switched_in[old_proc]
                yield TimelineElement(cpu, old_proc, switched_in_at, time - switched_in_at, TimelineElement.RUNNING)
                del switched_in[old_proc]
            if generate_runnable and 'R' in ev.old_state:
                yield TimelineElement(cpu, ev.old_proc, time, 0, TimelineElement.IS_RUNNABLE)
            if new_proc in switched_out:
                switched_out_at, proc_state, switchout_stack = switched_out[new_proc]
                del switched_out[new_proc]
                if 'R' in proc_state:
                    state = TimelineElement.PREEMPTED
                elif 'D' in proc_state:
                    state = TimelineElement.SLEEPING_UNINTERRUPTIBLY
                elif proc_state == 'S':
                    state = TimelineElement.SLEEPING
                else:
                    raise RuntimeError("Unknown state: " + proc_state)
                if new_proc in wakeup_history:
                    wakeup_time, delta = wakeup_history[new_proc]
                    del wakeup_history[new_proc]
                    yield TimelineElement(cpu, new_proc, switched_out_at, wakeup_time - switched_out_at, state, start_stack=switchout_stack, end_stack=trace.stack)
                    yield TimelineElement(cpu, new_proc, wakeup_time, time - wakeup_time, TimelineElement.WOKEN, delta, start_stack=switchout_stack)
                else:
                    yield TimelineElement(cpu, new_proc, switched_out_at, time - switched_out_at, state, start_stack=switchout_stack, end_stack=trace.stack)
            elif new_proc in wakeup_history:
                wakeup_time, delta = wakeup_history[new_proc]
                del wakeup_history[new_proc]
                yield TimelineElement(cpu, new_proc, wakeup_time, time - wakeup_time, TimelineElement.WOKEN, delta)

def get_min_time(lines):
    for line in lines:
        columns = line.split()
        return float(columns[3].rstrip(':'))
