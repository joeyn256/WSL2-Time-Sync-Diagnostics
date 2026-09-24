# Methodology

This project is designed around a simple rule:

> **State exactly what was measured, what reference was used, and what the result does not prove.**

That matters especially for timekeeping, where two clocks can agree with each other while both differ from an independent reference.

## Evidence categories

The guide separates evidence into four broad categories.

### 1. Historical test evidence

Examples:

- comparator vectors;
- boot-classification vectors;
- modeled mode-harness cases;
- static source findings.

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

## Why `CLOCK_MONOTONIC_RAW` is useful

`CLOCK_MONOTONIC_RAW` provides a useful comparison point for Linux clock behavior because it exposes a raw monotonic clock that is not subject to the same frequency adjustments as the regular monotonic clock.

The key methodological point is not that RAW is "the correct clock" for every application.

It is that comparing adjusted and raw monotonic clocks can reveal when clock discipline is affecting the measured rate.

## The fixed-wait lesson

A fixed delay after a time-service intervention was not enough to establish readiness in the historical 24.04 experiment.

The kernel could continue applying a previously commanded correction after the service state changed.

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
Stopping timesyncd suppressed the recurring correction pattern in this environment.

Not automatically established:
timesyncd was the sole root cause.
```

## Bottom line

The methodology is intentionally conservative about claims, not about learning.

A failed run, a clean screen, an inconclusive causal experiment, and an unavailable qualification can all be useful results when their scope is stated accurately.
