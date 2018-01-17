
1. Profile the application

```
sudo perf record \
    -e sched:sched_stat_runtime \
    -e sched:sched_wakeup \
    -e sched:sched_switch \
    -p `pgrep scylla`
```

For flame graphs, you need to also collect backtraces by adding `--call-graph dwarf` to the command line arguments.

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
./sched-list.py --proc perf_fast --state sleeping < perf.log | sort -r -k4 | head
[000] perf_fast_forwa:2088 5632.127121: duration=0.009826 [s] SLEEPING  
[000] perf_fast_forwa:2088 5631.824382: duration=0.009821 [s] SLEEPING  
[000] perf_fast_forwa:2088 5632.439547: duration=0.009800 [s] SLEEPING  
[000] perf_fast_forwa:2088 5632.399226: duration=0.009795 [s] SLEEPING  
[000] perf_fast_forwa:2088 5632.157513: duration=0.009785 [s] SLEEPING  
[000] perf_fast_forwa:2088 5632.086809: duration=0.009674 [s] SLEEPING  
[000] perf_fast_forwa:2088 5632.358935: duration=0.009621 [s] SLEEPING  
[000] perf_fast_forwa:2088 5631.260176: duration=0.009484 [s] SLEEPING  
[000] perf_fast_forwa:2088 5630.756756: duration=0.009301 [s] SLEEPING  
[000] perf_fast_forwa:2088 5631.421351: duration=0.009291 [s] SLEEPING  
```
