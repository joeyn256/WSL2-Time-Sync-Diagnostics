# Ubuntu 24.04 Findings

This page summarizes the historical Ubuntu 24.04 timing investigation under WSL2.

This public draft summarizes historical findings; the original measurement logs are not included in the draft set.

The goal is not to claim that every Ubuntu 24.04 installation behaves the same way. It is to document what happened in the investigated environment, what the experiments support, and what they do **not** prove.

## Summary

The Ubuntu 24.04 investigation observed recurring large corrections in realtime-related behavior.

The strongest practical finding was this:

> `systemd-timesyncd` state was strongly associated with the recurring timing pathology, but the evidence did not prove that `systemd-timesyncd` was the sole root cause.

The investigation also exposed a more general lesson:

> Stopping a time service does not prove that the kernel has finished an already-commanded clock correction (a gradual correction is called a slew).

That distinction matters for benchmarking.

## What was observed

Across the broader investigation:

- recurring large realtime corrections were observed while `systemd-timesyncd` was active;
- stopping `systemd-timesyncd` suppressed the recurring correction pattern that had been observed;
- an already-commanded kernel slew could remain active after the service was stopped;
- the historical summary reports restoration of the original `systemd-timesyncd` service state; that does not establish present-day service state or whole-host restoration.

This supports a **strong experimental association** between the service state and the observed timing behavior.

It does not establish exclusive causation.

WSL, Hyper-V, guest time discipline, kernel timekeeping, and service interaction remain part of the interpretation.

## The historical failed timing run

The historical Ubuntu 24.04 test run, labeled D4R2, remains a failure against its timing criteria.

It completed its full sample schedule but failed two test criteria. The failure pattern was consistent with an in-progress kernel slew during the early part of the run.

The historical summary reports approximately `+26,693 ppm` for the first failing 30-second interval. Ppm means parts per million of relative rate difference. The run compared `CLOCK_MONOTONIC` and `CLOCK_MONOTONIC_RAW` with Windows QueryPerformanceCounter (QPC), the host's elapsed-time counter. The draft set identifies a large early `MONOTONIC`/QPC anomaly and a `RAW`/QPC pass, but does not explicitly tie this quoted number to a clock pair or provide its calculation and sign convention. It should therefore not be read as a fully specified accuracy measurement or compared directly with the 26.04 statistic.

Later intervals were reported to show much smaller deviations.

The important point is not the exact number by itself. It is the transition:

1. the run began with a large timing anomaly;
2. the anomaly decreased during the observation, consistent with a residual clock correction;
3. a fixed delay before the benchmark had not established a settled state.

The failure should not be rewritten as a pass. The controlled causal result remains **inconclusive**.

## The fixed-wait problem

The experiment waited 60 seconds measured by Windows QueryPerformanceCounter (QPC), the host's elapsed-time counter, after service intervention.

That was not sufficient to establish that the kernel had settled.

This leads to the most useful operational lesson from the 24.04 work:

> **A fixed post-intervention delay is not a sufficient readiness check for a timing-sensitive benchmark.**

If a benchmark depends on a stable timebase, prefer a measured state condition over a timer such as "wait 60 seconds."

For example, a future diagnostic should look for evidence that the relevant clock relationship has stabilized rather than infer stability from service state alone.

## What the evidence does support

The evidence supports these statements:

- timing pathology occurred in the investigated Ubuntu 24.04 WSL2 environment;
- large realtime corrections were observed;
- `systemd-timesyncd` state was strongly associated with the recurring behavior;
- stopping the service suppressed the recurring correction pattern that had been observed;
- the residual anomaly was consistent with a kernel slew outlasting the service transition;
- a simple fixed-delay benchmark can therefore capture an inherited transient.

## What it does not support

The evidence does **not** support these stronger statements:

- "`systemd-timesyncd` is the sole root cause";
- "Ubuntu 24.04 is broken under WSL2";
- "disabling `systemd-timesyncd` permanently fixes the problem";
- "an inactive service means the clock is settled";
- "every machine or WSL version will reproduce the same behavior";
- "Ubuntu 26.04 is automatically better because this 24.04 run failed."

## Practical advice for Ubuntu 24.04 users

If you already have a working Ubuntu 24.04 environment, do not change it solely because of this investigation.

Instead:

1. record your Windows, WSL, kernel, distro, and Python versions;
2. inspect the active time services and clocksource;
3. run a bounded read-only timing probe;
4. look for evidence of active slew or abnormal clock-rate behavior;
5. only then decide whether deeper investigation or migration is warranted.

If you temporarily change a time service for an experiment, capture the original state first and restore it afterward.

Do not place service-stop commands in a first-run quick start.

## Practical lesson

The reported timing failure is specific to the investigated environment. Measure your own timebase before trusting a long timing-sensitive workload.

See the [diagnostic workflow and clock caveats](../README.md#proposed-diagnostic-workflow).
