# Investigating `systemd-timesyncd` Under WSL2

This page documents the strongest historical lesson from the Ubuntu 24.04 investigation: **successfully stopping a time service did not mean the kernel clock was already settled or ready for a benchmark**.

The original private measurement logs are not published here. The numerical results below are a bounded reconstruction from the preserved experiment outputs.

## Exact intervention: stopped, not disabled

In the examined C1 and D4R2 interventions, the service transition was:

```text
systemctl stop systemd-timesyncd.service
...
systemctl start systemd-timesyncd.service
```

The unit remained **enabled** while stopped. The preserved state sequence for D4R2 was:

```text
active/running/enabled
→ inactive/dead/enabled
→ active/running/enabled
```

No persistent `disable`, `mask`, service-file edit, or `timedatectl set-ntp` action is established by the examined interventions.

These historical commands are evidence about what the experiment did, not a recommendation to change a reader's system.

## C1: suggestive intervention, formally inconclusive

C1 used an A–B–A design with a frozen event threshold of at least 0.500 seconds.

The preserved result was:

| Phase | Service state | Recorded result under the frozen detector |
|---|---|---|
| A0 | active | Four qualifying events, about +0.588 to +0.628 s |
| B | stopped | No qualifying events under the frozen detector |
| A1 | active again | Two journal-matched events, about +0.424 and +0.449 s, both below the 0.500 s threshold |

Because A1 did not meet the predeclared requirement for qualifying events, the formal causal result remained **INCONCLUSIVE**.

The experiment therefore supports the narrower statement that the observed pattern changed during the temporary stop. It does **not** prove that `systemd-timesyncd` was the sole writer or sole root cause.

## D4R2: the stop worked, but the clock was still correcting

D4R2 asked a different operational question: after a confirmed stop, was a fixed 60-second wait enough before opening the benchmark window?

It was not.

The wait was measured using Windows QueryPerformanceCounter (QPC). PRE sampling occurred about 60 seconds after the confirmed service stop, and the measurement window opened about 60.06 QPC seconds after that stop.

At that point the service was inactive, but the kernel still reported a large correction state.

| Recorded point or interval | Observation | Bounded interpretation |
|---|---|---|
| After stop | inactive/dead, MainPID 0, UnitFileState enabled | Runtime stop established; persistent disable was not performed |
| PRE after the 60-second hold | `tick=10833`, `freq=2157314`; historical baseline calculation about **+83,332.918 ppm** | Large correction state still present |
| First 30 s | MONOTONIC/QPC **+26,665.299 to +26,724.999 ppm** | Early elapsed-time rate far outside the study's ±1000 ppm screen |
| 30–60 s | MONOTONIC/QPC **−27.234 to +30.394 ppm** | Within the historical screen |
| 60–90 s | MONOTONIC/QPC **−32.612 to +25.100 ppm** | Within the historical screen |
| 90–120 s | MONOTONIC/QPC **−27.169 to +32.177 ppm** | Within the historical screen |
| Full 120 s | MONOTONIC/QPC **+6,661.607 to +6,676.217 ppm** | Full run remained outside the historical screen |
| RAW/QPC | Full interval **−6.323 to +8.190 ppm**; required intervals stayed within the screen | Differential evidence localized the anomaly to disciplined-vs-raw clock behavior; it did not identify the writer |
| POST | `tick=10000`, `freq=-27187`; historical baseline calculation about **−0.415 ppm** | Near-nominal static baseline at the later snapshot |
| Restoration | service started and confirmed active/running/enabled | Original service state restored |

The historical static baseline calculation was:

```text
A_BASE_PPM = 100 × (tick_usec − 10000) + freq / 65536
```

That calculation is specific to the historical environment's nominal-tick assumption. A static snapshot is supporting evidence; it is not the same thing as a measured rate over an entire window.

## The important sequence

D4R2 demonstrated this distinction:

```text
service successfully stopped
        ≠
kernel correction already finished
        ≠
clock already settled
        ≠
benchmark ready
```

The early anomaly and later return toward nominal behavior are consistent with a residual kernel slew continuing after the service transition. The experiment did not trace the initiating adjustment syscall and did not prove that every other possible clock writer was absent.

That rate shape does not explain who set or later reset `tick`: it is not a phase-offset field that simply decays. The [upstream review](upstream-time-sync-status.md#connection-to-this-projects-d4r2-evidence) separates persistent kernel discipline from writer attribution and documents Canonical's current default-controller guidance.

## An instrumentation lesson

One earlier D3 attempt also exposed a narrower measurement hazard: in that experiment, querying `timedatectl show-timesync` could activate the stopped service through its query path.

That does **not** mean every `timedatectl` or `systemctl` read mutates service state. It means a supposedly observational command must itself be checked when designing a sensitive intervention.

## A useful mechanism hypothesis, not a proven root cause

The historical evidence is consistent with more than one clock-discipline component interacting with the same guest kernel clock.

That is a useful mechanism hypothesis because:

- the active/stopped phases showed different recorded behavior;
- the PRE and POST kernel correction states differed substantially;
- MONOTONIC/QPC showed the early anomaly while RAW/QPC remained near nominal.

But the investigation did not authenticate a complete write trace identifying the sole clock writer. The formal causal conclusion therefore remains **INCONCLUSIVE**.

## Better experimental design

For timing-sensitive work, prefer:

```text
capture baseline
→ make one bounded intervention
→ observe measured clock state
→ open the benchmark only if the chosen observation criterion is satisfied
→ restore and verify original state
```

over:

```text
stop service
→ sleep N seconds
→ assume settled
→ benchmark
```

The v0.2 `settle-check` command provides a finite read-only observation of an explicitly configured example band. It does not provide a universal settling predicate or certify benchmark readiness.

## What this investigation supports

Supported:

- the service was temporarily **stopped and later started**, not persistently disabled, in the examined interventions;
- the unit remained enabled during the D4R2 stop;
- C1's A–B–A result was suggestive but formally **INCONCLUSIVE** under its frozen 0.500-second threshold;
- D4R2 still showed a substantial kernel correction state after a 60-second QPC-measured wait;
- D4R2's first 30-second MONOTONIC/QPC interval was about +26.7k ppm while RAW/QPC remained within the historical screen;
- later D4R2 windows moved back near nominal;
- service state alone did not establish benchmark readiness.

Not supported:

- `systemd-timesyncd` was the sole root cause;
- stopping or disabling it is a universal WSL repair;
- a non-nominal `tick` identifies the writer by itself;
- every Ubuntu 24.04 WSL2 environment reproduces the same behavior;
- this experiment establishes a Ubuntu 24.04 versus 26.04 ranking.

## Practical lesson

The memorable result is not simply that `systemd-timesyncd` was involved.

It is that **the daemon could be successfully stopped while the kernel was still correcting time strongly enough to invalidate the next benchmark window**.
