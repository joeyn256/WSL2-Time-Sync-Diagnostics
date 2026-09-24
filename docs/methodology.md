# Methodology

This project is designed around a simple rule:

> **State exactly what was measured, what reference was used, and what the result does not prove.**

That matters especially for timekeeping, where two clocks can agree with each other while both differ from an independent reference.

## Evidence categories

The guide separates evidence into four broad categories.

### 1. Historical test evidence

Examples:

- preserved historical timing analyses;
- synthetic boundary and failure-shape fixtures;
- static source findings;
- focused continuity or uncertainty tests.

These are useful for claims about the exact code and test cases that produced them.

They are not automatically live-host qualification.

### 2. Guest-side observation

A guest-side test compares clocks or state visible inside Linux.

The accepted Ubuntu 26.04 300-second screen is an example.

Guest-side observations can reveal important anomalies, especially relative behavior between Linux clocks.

But they do not automatically establish absolute accuracy against Windows or an external reference.

### 3. Host-referenced observation

A host-referenced test compares guest time behavior with a Windows-side elapsed-time reference such as QueryPerformanceCounter (QPC).

This provides a reference outside guest clock discipline, but does not by itself establish an independent physical clock source or accuracy against UTC. QPC can be based on the processor's timestamp counter (TSC) and is not synchronized to an external time reference. See [Microsoft's QPC documentation](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps).

This can answer questions that a guest-only comparison cannot.

The historical Ubuntu 24.04 D4R2 experiment used a host reference.

### 4. Live qualification

A live qualification demonstrates a complete operational property in the actual environment being claimed.

Examples could include:

- a successful host-provider lifecycle;
- runtime containment;
- toolchain behavior;
- cleanup/restoration.

Static tests, mocked interfaces, and hashes can support a qualification, but they do not substitute for a live property that was never observed.

## Why reference clocks matter

A comparison between two guest clocks answers:

```text
How did these two guest clocks behave relative to each other?
```

A guest-versus-host comparison can answer:

```text
How did the guest clock behave relative to the Windows-side elapsed-time reference?
```

Those are related but not identical questions.

This is why the Ubuntu 26.04 guest-side screen is treated as a promising baseline rather than a full replacement for the historical host-referenced measurement.

## PPM

Timing-rate differences are often expressed in parts per million (ppm).

Conceptually:

```text
ppm = relative rate error × 1,000,000
```

A large positive or negative ppm value indicates that one measured clock interval is advancing at a different rate from the reference interval.

In this repository, always read a ppm number together with:

- the two clocks being compared;
- the measurement window;
- the method used to calculate the value.

Do not compare ppm values from different clock/reference pairs as though they were automatically equivalent.

## Fixed windows

The experiments used fixed windows so that an early transient could not be hidden inside one long average.

A 300-second run can look acceptable on average while containing a serious 30-second anomaly.

Windowed analysis makes that visible.

The v0.2 analyzer reports each configured window as well as the full-run result. A later within-band window does not erase an earlier outside-band window. Thresholds and window lengths are observation settings, not universal definitions of clock health.

## Why `CLOCK_MONOTONIC_RAW` is useful

`CLOCK_MONOTONIC_RAW` provides a useful comparison point for Linux clock behavior because it exposes a raw monotonic clock that is not subject to the same frequency adjustments as the regular monotonic clock.

The key methodological point is not that RAW is "the correct clock" for every application.

It is that comparing adjusted and raw monotonic clocks can reveal when clock discipline is affecting the measured rate.

## Bracketed guest acquisition

The v0.2 probe uses a versioned schema and this acquisition order:

```text
MONOTONIC_RAW before
REALTIME
MONOTONIC
BOOTTIME, when available
MONOTONIC_RAW after
```

The bracket width records the elapsed RAW time surrounding the intervening reads. Clock reads are sequential, not simultaneous. An unavailable clock stays explicitly unavailable; it is not replaced by another reference or a zero timestamp.

For start sample `a` and end sample `b`, let `before` and `after` denote their RAW bounds. The elapsed reference interval is:

```text
L = before_b - after_a
U = after_b - before_a
```

For positive measured clock delta `D` and valid `0 < L <= U`, the guest-relative rate enclosure in ppm is:

```text
[1,000,000 * (D / U - 1), 1,000,000 * (D / L - 1)]
```

The pure arithmetic also orders the candidate bounds correctly for signed deltas. A nonpositive MONOTONIC delta is invalid measurement geometry, rather than a usable elapsed-time rate. Missing values, reversed brackets, and a nonpositive reference lower bound do not yield a precise rate.

These bounds represent acquisition uncertainty under the observed clock ordering. They are not statistical confidence intervals and do not include every source of clock error. RAW can share underlying behavior with other guest clocks. Bracketing does not create a Windows-host or UTC reference.

## Three-way interval classification

For a configured symmetric band `[-B, +B]`, classify the entire rate enclosure:

| Result | Meaning |
|---|---|
| `WITHIN` | Both bounds lie inside the inclusive band. |
| `OUTSIDE` | The entire interval is below `-B` or above `+B`. |
| `INDETERMINATE` | The interval overlaps a boundary, or required evidence/geometry is unavailable or incomplete. |

An interval touching a boundary from the outside remains indeterminate; an interval entirely inside the band including its boundary is within. Classification uses the enclosure, never its midpoint. Exact arithmetic preserves boundary decisions; rendered decimal values are for reading the result.

Signed REALTIME changes are reported with their own enclosure against RAW elapsed time. For REALTIME delta `R`, the change interval is `[R - U, R - L]`. Positive and negative events remain distinguishable. A backward REALTIME read is recorded separately. Neither an event nor an interval rate identifies the component that changed the clock.

## Window coverage and legacy inputs

Fixed boundaries are anchored to the first usable RAW-before sample. Each boundary selects the first sample at or after it; adjoining windows share that endpoint. Reports preserve the nominal boundaries, actual sampled span, and endpoint displacement, so scheduling delays are visible. The measured rate applies to the actual endpoint span. Coverage also carries requested cadence/duration and capture completion when supplied. The recorded scheduling clock differs from RAW, so a small RAW-duration shortfall is reported without treating it as a missing scheduled sample when explicit capture-completion metadata is available. Without that metadata, a requested-duration shortfall conservatively leaves coverage incomplete.

A final short window with a distinct endpoint is retained as partial and indeterminate. A boundary-closing overshoot sample is not duplicated as an additional zero-span tail. Missing or duplicate samples, invalid order, and unavailable endpoints cannot be converted into a clean full-coverage result. Fixed-window analysis can expose an early anomaly, but finite sampling can still miss events between reads or hide a transient that cancels within a window.

The analyzer still accepts v0.1 probe inputs. Their single RAW reads do not retroactively become brackets. Legacy endpoint ppm remains descriptive, with unbounded acquisition uncertainty and an indeterminate uncertainty-aware classification. A legacy result and a bracketed result must not be silently treated as the same measurement method.

## Kernel-state and finite settling observations

The v0.2 kernel reader requests `adjtimex(modes=0)`. It validates the supported Linux x86-64 LP64 structure layout before calling the interface and returns structured unavailability on unsupported layouts or read errors. The result preserves raw kernel fields, including `tick`, scaled `freq`, status, and error estimates; units depend on the field and, for applicable fields, `STA_NANO`.

A snapshot is supporting state evidence. It does not establish that every pending correction is absent, identify the writer of an earlier correction, or measure a clock's rate over a window. In particular, `tick == 10000` and a small `freq / 65536` are historical example values, not a portable readiness rule.

The `settle-check` command observes repeated `adjtimex` snapshots for a finite requested duration. Its default policy, explicitly named `historical_example_tick10000_freq100ppm`, requires `tick == 10000` and `abs(freq / 65536) < 100`; these values and the required consecutive count are configurable. The frequency boundary is strict. Any observed tick/frequency anomaly remains visible even after later nominal readings. Missing readings, an incomplete scheduled capture, or too few consecutive readings prevent a within-band result.

Its vocabulary is `WITHIN_CONFIGURED_BAND`, `ANOMALY_OBSERVED`, or `INDETERMINATE`. A within-band outcome describes only the sampled kernel fields under that policy. The command does not measure bracketed clock rates; use `probe` and `analyze` for those. It does not certify a future workload, uninterrupted stability, host agreement, or absolute accuracy. See the [v0.2 CLI and schema reference](v0.2-guest-core.md).

## Method-aware comparison

Comparison carries schema, clock pair/reference, acquisition and analysis methods, window geometry, coverage, and configured thresholds. It distinguishes `COMPARABLE`, `DIFFERENT_METHOD`, and `INSUFFICIENT_CONTEXT`. Only compatible, sufficiently described results support a numerical comparison under that method.

The optional `continuity_label` is caller-supplied acquisition context, not a guest or host boot identifier. The probe emits `null`. If supplied labels differ, comparison conservatively reports different methods; a label on only one side leaves insufficient context. Equal labels do not prove continuous observation, the same boot, or unchanged host state.

## The fixed-wait lesson

A fixed delay after a time-service intervention was not enough to establish readiness in the historical 24.04 experiment.

The kernel could continue applying a previously commanded correction after the service state changed.

The examined interventions used `stop` then `start`; the unit remained enabled. C1's formal causal result remained **INCONCLUSIVE**. D4R2 still showed a large kernel correction state after a successful stop and approximately 60 seconds measured by Windows QPC. These observations support the bounded distinction between service state and measured clock state; they do not establish a universal cause or a universal waiting time. See the [timesyncd investigation](timesyncd-investigation.md).

Therefore this project prefers:

```text
intervention
→ measured state check
→ benchmark
```

over:

```text
intervention
→ sleep N seconds
→ assume settled
→ benchmark
```

## Repository location during Linux-side testing

When running the CLI from Ubuntu, prefer cloning the repository into the Linux filesystem (for example, under `$HOME`) instead of running it from `/mnt/c`. Microsoft recommends this layout for better filesystem performance when using Linux command-line tools.

Reference: https://learn.microsoft.com/windows/wsl/filesystems#file-storage-and-performance-across-file-systems

## Read-only first

The public diagnostic workflow should begin read-only.

Before changing a time service, collect:

- Windows version;
- WSL version;
- distro and kernel;
- boot ID;
- time-service state;
- active clocksource;
- visible Hyper-V/PTP devices;
- relevant process state;
- bounded clock observations.

Mutation should be an advanced experiment, not the first diagnostic step.

## One change at a time

If a mutating experiment is necessary, avoid changing multiple clock-related components at once unless the experiment explicitly studies their combination.

Multiple simultaneous changes make causal interpretation harder.

## Restoration

A mutating experiment should capture the original state before the change and verify restoration afterward.

A failed benchmark is still useful evidence.

A machine left in an unknown configuration is not.

## No automatic retry to erase failure

A first failure can be the most informative result.

The methodology avoids treating an automatic rerun as though the first result never happened.

If a run is invalid or incomplete, say why.

If it is a valid failure, preserve it.

## Reproducibility

A useful timing record should include enough context to reproduce or interpret it later:

- Windows version/build;
- WSL version;
- Ubuntu release;
- kernel version;
- Python version;
- boot ID;
- clocksource;
- visible time services;
- relevant PTP/Hyper-V state;
- sample cadence;
- measurement duration;
- clocks compared;
- calculation method;
- raw or sealed evidence where appropriate.

Public regression fixtures are parameterized synthetic traces, including an early slew followed by normal-looking windows, periodic sawtooth changes, signed steps, missing/duplicate samples, threshold straddles, and common-mode guest behavior. They test analysis behavior and uncertainty handling. They are not copies of private historical evidence, new live reproductions of C1/D4R2, or evidence about how frequently an anomaly occurs.

## Interpretation hierarchy

Use the narrowest conclusion supported by the evidence.

For example:

```text
Observed:
No D4R2-scale MONOTONIC-vs-RAW slew during this 300-second guest screen.

Not automatically established:
Ubuntu 26.04 universally fixes WSL2 timing.
```

Likewise:

```text
Observed:
In C1, four qualifying events occurred in the initial active phase, none were counted in the stopped phase under the frozen detector, and two real but sub-threshold events appeared after restart.

Not automatically established:
timesyncd was the sole root cause. The formal C1 causal result remained INCONCLUSIVE.
```

## Bottom line

The methodology is intentionally conservative about claims, not about learning.

A failed run, a clean screen, an inconclusive causal experiment, and an unavailable qualification can all be useful results when their scope is stated accurately.
