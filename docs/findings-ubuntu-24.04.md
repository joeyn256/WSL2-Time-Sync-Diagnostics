# Ubuntu 24.04 Findings

This page summarizes the historical Ubuntu 24.04 timing investigation under WSL2.

The original private measurement logs are not included in this repository. The values below are bounded summaries from preserved experiment outputs.

## Summary

The investigated environment showed recurring large realtime corrections and a changing clock-rate pattern.

A temporary `systemd-timesyncd` intervention produced a suggestive but formally **INCONCLUSIVE** A–B–A causal result, and a later D4R2 run demonstrated the more durable operational lesson:

> **Stopping the service did not mean the kernel clock had already settled.**

## What was actually done

In the examined interventions, `systemd-timesyncd` was temporarily **stopped** and later **started** again.

The unit remained enabled. The examined records do not establish a persistent `disable`, `mask`, or configuration edit.

This distinction matters because:

```text
inactive service
≠
disabled service
≠
settled clock
```

## C1 A–B–A result

C1 used a frozen 0.500-second event threshold.

- A0, service active: four qualifying events of roughly +0.588 to +0.628 seconds.
- B, service stopped: no qualifying events under the frozen detector.
- A1, service active again: two journal-matched events of roughly +0.424 and +0.449 seconds, both below the frozen threshold.

Because A1 did not meet the predeclared qualifying-event requirement, the formal causal result was **INCONCLUSIVE**.

This is stronger evidence than a simple anecdote, but weaker than proof that `systemd-timesyncd` was the sole cause.

## D4R2: fixed waiting was not enough

D4R2 stopped the service, confirmed it inactive, and waited about 60 seconds measured by Windows QPC before opening a 120-second timing window.

PRE still showed:

```text
tick = 10833
freq = 2157314
historical baseline calculation ≈ +83,332.918 ppm
```

The four 30-second MONOTONIC/QPC windows were:

| Window | Rate enclosure |
|---|---:|
| 0–30 s | **+26,665.299 to +26,724.999 ppm** |
| 30–60 s | −27.234 to +30.394 ppm |
| 60–90 s | −32.612 to +25.100 ppm |
| 90–120 s | −27.169 to +32.177 ppm |

The full 120-second MONOTONIC/QPC enclosure was **+6,661.607 to +6,676.217 ppm**.

By contrast, RAW/QPC remained within the historical screen, with a full-run enclosure of **−6.323 to +8.190 ppm**.

POST later showed:

```text
tick = 10000
freq = -27187
historical baseline calculation ≈ -0.415 ppm
```

That early-failure/later-recovery shape is consistent with a residual kernel correction continuing after the service stop.

## What the evidence supports

The historical evidence supports these bounded statements:

- significant timing pathology occurred in the investigated Ubuntu 24.04 WSL2 environment;
- the recorded behavior differed across the active/stopped/restored phases;
- C1 did not satisfy its predeclared causal-success rule and remained **INCONCLUSIVE**;
- D4R2 showed that a successful service stop plus a 60-second host-measured wait did not establish a settled clock;
- MONOTONIC/QPC showed a severe early anomaly while RAW/QPC did not show the same failure;
- later D4R2 windows approached nominal behavior.

## What it does not support

The evidence does **not** support these stronger claims:

- "`systemd-timesyncd` is proven to be the sole root cause";
- "Ubuntu 24.04 is broken under WSL2";
- "disabling `systemd-timesyncd` is the demonstrated fix";
- "an inactive service means the clock is settled";
- "every WSL2 machine will reproduce the same behavior";
- "Ubuntu 26.04 is better because this 24.04 experiment failed."

## Practical advice

If an existing Ubuntu 24.04 environment is working, do not change it solely because of this case study.

For timing-sensitive work:

1. record the Windows, WSL, kernel, distro, and Python versions;
2. inspect time-service and clocksource state;
3. run a bounded timing observation;
4. preserve early adverse windows rather than relying only on a long-run average;
5. treat service state and clock-settling evidence as separate questions.

See the detailed [`systemd-timesyncd` investigation](timesyncd-investigation.md).

A later, directly measured screen of the *enabled* state on a different host, with committed raw evidence, is recorded in [Same-host screens, 2026-09-24](same-host-screens-2026-09-24.md).
