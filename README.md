
1. Profile the application

```
sudo perf record \
    -e sched:sched_stat_runtime \
    -e sched:sched_wakeup \
    -e sched:sched_switch \
    -p `pgrep scylla`
```

For flame graphs, you need to also collect backtraces by adding `--call-graph dwarf` to the command line argments.

2. Generate the log

```
sudo perf script > perf.log
```

3. Analyze

Generating flame graph for uninterruptible sleeps:
```
./sched-flame.py --state sleeping_uninterruptibly < perf.log | flamegraph.pl > flame.svg
```

Find longest sleeps:

```
./sched-list.py --state sleeping < perf.log | sort -k4 | head
[000] perf_fast_forwa:2088 5632.083301: duration=0.000050 [s] SLEEPING  
[000] perf_fast_forwa:2088 5632.642553: duration=0.000050 [s] SLEEPING  
[000] perf_fast_forwa:2088 5630.629793: duration=0.000051 [s] SLEEPING  
[000] syscall-0:2091       5631.569756: duration=0.000051 [s] SLEEPING  
[000] syscall-0:2091       5632.642284: duration=0.000051 [s] SLEEPING  
[000] syscall-0:2091       5631.532691: duration=0.000052 [s] SLEEPING_UNINTERRUPTIBLY
[000] perf_fast_forwa:2088 5630.643221: duration=0.000053 [s] SLEEPING  
[000] perf_fast_forwa:2088 5631.569045: duration=0.000053 [s] SLEEPING  
[000] syscall-0:2091       5631.528246: duration=0.000053 [s] SLEEPING  
[000] syscall-0:2091       5631.528976: duration=0.000053 [s] SLEEPING  
```
