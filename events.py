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

class SchedStatRuntimeEvent:
    def __init__(self, proc, runtime, vruntime):
        self.proc = proc
        self.runtime = runtime
        self.vruntime = vruntime

def parse_proc_name(columns):
    proc = None
    if 'comm' in columns[0]:
        proc = columns[0].split('=')[1] + ':' + columns[1].split('=')[1]
        columns.pop(0)
        columns.pop(0)
    else:
        proc = columns[0]
        columns.pop(0)
    return proc

def parse_sched_stat_runtime(columns):
    columns = columns[5:]
    proc = parse_proc_name(columns)
    runtime = float(columns[0].split('=')[1])
    vruntime = float(columns[2].split('=')[1])
    return SchedStatRuntimeEvent(proc, runtime, vruntime)

class SchedWakeupEvent:
    def __init__(self, proc, cpu):
        self.cpu = cpu
        self.proc = proc

def parse_sched_wakeup(columns):
    columns = columns[5:]
    proc = parse_proc_name(columns)
    if '=' in columns[2]:
        cpu = int(columns[2].split('=')[1])
    else:
        cpu = int(columns[2].split(':')[1])
    return SchedWakeupEvent(proc, cpu)

class SchedSwitchEvent:
    def __init__(self, old_proc, old_state, new_proc):
        self.new_proc = new_proc
        self.old_state = old_state
        self.old_proc = old_proc

def parse_sched_switch(columns):
    columns = columns[5:]
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
        def __init__(self, text, is_sleep=False, is_delayed=False):
            state_by_name[text] = self
            self.is_sleep = is_sleep
            self.is_delayed = is_delayed
            self.text = text
        def __str__(self):
            return self.text
        def __repr__(self):
            return self.text
        def is_sleep(self):
            return self.is_sleep
        def is_delayed(self):
            return self.is_delayed

    WOKEN = State("WOKEN", is_delayed=True)
    PREEMPTED = State("PREEMPTED", is_delayed=True)
    SLEEPING = State("SLEEPING", is_sleep=True)
    SLEEPING_UNINTERRUPTIBLY = State("SLEEPING_UNINTERRUPTIBLY", is_sleep=True)
    RUNNING = State("RUNNING")

    def __init__(self, proc, start, duration, state, wakeup_vruntime_delta=None):
        self.proc = proc
        self.start = start
        self.duration = duration
        self.state = state
        self.wakeup_vruntime_delta = wakeup_vruntime_delta

#  sudo perf record \
#    -e sched:sched_stat_runtime \
#    -e sched:sched_wakeup \
#    -e sched:sched_switch
def get_sched_timeline(lines):
    wakeup_history = {}
    switched_out = {}
    switched_in = {}
    vruntimes = {}
    for line in lines:
        columns = line.split()
        name = columns[0]
        pid = columns[1]
        curr = name + ":" + pid
        cpu = int(columns[2].lstrip('[').rstrip(']'))
        time = float(columns[3].rstrip(':'))
        event = columns[4].rstrip(':')
        if event == 'sched:sched_stat_runtime':
            ev = parse_sched_stat_runtime(columns)
            vruntimes[ev.proc] = ev.vruntime
        if event == 'sched:sched_wakeup':
            ev = parse_sched_wakeup(columns)
            delta = None
            if ev.cpu == cpu and curr in vruntimes and ev.proc in vruntimes:
                delta = float(vruntimes[curr] - vruntimes[ev.proc]) / 1e9
            wakeup_history[ev.proc] = (time, delta)
        if event == 'sched:sched_switch':
            ev = parse_sched_switch(columns)
            old_proc = ev.old_proc
            new_proc = ev.new_proc
            switched_out[old_proc] = (time, ev.old_state)
            switched_in[new_proc] = time
            if old_proc in wakeup_history:
                del wakeup_history[old_proc]
            if old_proc in switched_in:
                switched_in_at = switched_in[old_proc]
                yield TimelineElement(old_proc, switched_in_at, time - switched_in_at, TimelineElement.RUNNING)
                del switched_in[old_proc]
            if new_proc in switched_out:
                switched_out_at, proc_state = switched_out[new_proc]
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
                    yield TimelineElement(new_proc, switched_out_at, wakeup_time - switched_out_at, state)
                    yield TimelineElement(new_proc, wakeup_time, time - wakeup_time, TimelineElement.WOKEN, delta)
                else:
                    yield TimelineElement(new_proc, switched_out_at, time - switched_out_at, state)

def get_min_time(lines):
    for line in lines:
        columns = line.split()
        return float(columns[3].rstrip(':'))
