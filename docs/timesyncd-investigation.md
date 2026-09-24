# Investigating `systemd-timesyncd` Under WSL2

This page explains the most important timing lesson from the Ubuntu 24.04 investigation: why changing a time service and immediately benchmarking can produce a misleading result.

This public draft summarizes historical findings; it does not include the original measurement logs or a validated readiness-test implementation.

## The observed pattern

In the investigated Ubuntu 24.04 environment, the broad pattern was:

```text
timesyncd active
    ↓
recurring large realtime corrections observed

timesyncd stopped
    ↓
recurring correction pattern suppressed
```

That is strong evidence of association.

It is **not** sufficient evidence to say:

```text
timesyncd = sole root cause
```

WSL2 timing involves multiple layers, including Windows/Hyper-V, the WSL kernel, guest timekeeping, PTP (Precision Time Protocol) mechanisms, and user-space time services. The controlled causal result remains **inconclusive**.

## Why the first stop-and-test approach was misleading

A time service can request or trigger a clock adjustment that the kernel continues applying after the service state changes.

So this sequence is unsafe as a scientific assumption:

```text
stop service
wait fixed amount of time
assume clock is stable
run benchmark
```

In the historical investigation, a 60-second wait measured by Windows QueryPerformanceCounter (QPC), the host's elapsed-time counter, did not establish timing readiness.

The early anomaly and its later reduction were consistent with a residual slew: a gradual clock correction still in progress after the service stopped. This is an interpretation of the reported pattern, not proof of the component that initiated it.

## Service state vs clock state

These are different questions:

### Service state

Examples:

Run these read-only checks in an already-open Ubuntu shell with systemd:

```sh
systemctl is-active systemd-timesyncd
systemctl is-enabled systemd-timesyncd
```

These report whether the unit is running and its enablement state. Preserve the exact output: inactive, disabled, and not found describe different states. An enabled unit need not be running.

### Clock state

This asks whether the kernel clock is currently behaving as expected for the measurement you care about.

A stopped service does not automatically answer that question.

For timing-sensitive work, the clock-state question is usually more important. Name the clocks and reference used in that check. Linux `CLOCK_MONOTONIC` is still subject to frequency adjustments; its name alone does not guarantee a stable rate. See the [clock caveats](../README.md#proposed-diagnostic-workflow).

## Better experimental design

A stronger design has three phases.

### 1. Capture the baseline

Before changing anything, record:

- Windows version;
- WSL version;
- distro and kernel;
- boot ID;
- active clocksource;
- visible time services;
- PTP/Hyper-V devices;
- relevant process state.

Keep the original measurements privately. Before publishing a separate copy, remove usernames, hostnames, personal paths, literal boot/machine identifiers, and sensitive process arguments; document redactions that affect interpretation.

### 2. Make the intervention explicit

If you intentionally stop a service:

- record the exact pre-state;
- record the intervention time;
- do not change multiple time components at once unless the experiment requires it;
- have a restoration plan before making the change.

### 3. Check readiness before starting the benchmark

Instead of:

```text
sleep 60
```

prefer:

```text
observe
→ evaluate settling criterion
→ only benchmark if criterion passes
```

Choose the clock comparison, window length, tolerance, and maximum waiting time before the experiment. Start the benchmark only if the measured criterion is met. If it is not met or cannot be evaluated, retain the observation and report that readiness was not established.

This guide does not supply a validated settling threshold. A readiness check supports the chosen measurement under the observed conditions; it cannot guarantee stability throughout a later workload.

## Why not simply disable `systemd-timesyncd` permanently?

Because the investigation did not prove that this service alone explains every timing path.

A permanent change also creates new questions:

- what now disciplines the clock;
- what WSL/Hyper-V behavior remains;
- whether another daemon is active;
- whether the system behaves differently across boots;
- whether the application depends on wall-clock correction.

The public guide therefore treats service mutation as an advanced experiment, not a default fix.

## Restoration matters

Any mutating timing experiment should:

1. capture the original service state;
2. make one bounded change;
3. record the resulting observation;
4. restore the original state;
5. verify restoration.

A failed benchmark should not leave the machine in an unknown time-service configuration.

## What the investigation supports

Supported:

- `systemd-timesyncd` state had a strong experimental association with the observed recurring correction pattern;
- stopping it suppressed that recurring pattern in the investigated environment;
- the residual anomaly was consistent with a kernel slew continuing after the service was stopped;
- the fixed wait was insufficient to establish readiness in the historical experiment.

Not supported:

- `systemd-timesyncd` was the sole root cause;
- disabling it is a universal WSL fix;
- `chronyd` is universally superior;
- service status alone proves timing readiness.

## A useful diagnostic mindset

When debugging time behavior, separate these layers:

```text
visible component
    ≠
component adjusting the clock
    ≠
cause of the observed error
    ≠
best remediation
```

That separation prevents a common debugging mistake: finding one correlated component and promoting it directly to root cause.

## Practical lesson

After changing a time service, use measured readiness criteria before benchmarking. Service status and elapsed waiting time alone do not establish timing readiness.
