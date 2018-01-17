
== Usage ==

1. Profile the application

```
sudo perf record \
    -e sched:sched_stat_runtime \
    -e sched:sched_wakeup \
    -e sched:sched_switch \
    -C 0
```

The `-C 0` switch enables profiling of CPU #0. You can use `-p <pid>` to profile the whole process, but note that
on machines with many cores this may add an unacceptable overhead and distort the measurement by affecting the system under test.

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
