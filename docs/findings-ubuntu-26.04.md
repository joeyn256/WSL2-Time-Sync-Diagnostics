# Ubuntu 26.04 Findings

This page summarizes the reported Ubuntu 26.04 default-state observation under WSL2. The public draft set contains a narrative summary, not the original measurement logs.

The result is encouraging, but deliberately narrow.

## Summary

During the reported 300-second guest-side Ubuntu 26.04 observation, all ten fixed 30-second `CLOCK_MONOTONIC` versus `CLOCK_MONOTONIC_RAW` windows stayed within the predeclared ±1000 ppm engineering band.

The reported window enclosures were all close to zero. The most negative lower bound was approximately `-1.191303 ppm`, and the full-run `MONOTONIC`/`RAW` enclosure was approximately `-0.504500 .. -0.463656 ppm`.

The [historical Ubuntu 24.04 failure (D4R2)](findings-ubuntu-24.04.md) used Windows-side QueryPerformanceCounter (QPC) as its elapsed-time reference and is not a direct apples-to-apples numerical comparison. However, in that failure `CLOCK_MONOTONIC`/QPC showed a very large early anomaly while `CLOCK_MONOTONIC_RAW`/QPC passed. That pattern supports a narrower guest-side inference: a D4R2-scale slew affecting `CLOCK_MONOTONIC` relative to `CLOCK_MONOTONIC_RAW` was not present during this 26.04 screen.

This is a promising screen. It does **not** establish a controlled head-to-head benchmark, absolute timing accuracy against Windows, or a universal fix.

## Observed environment

The historical summary reports the following environment; it does not establish defaults for every Ubuntu 26.04 installation:

- Ubuntu `26.04.1 LTS`;
- WSL `2.7.13.0`;
- Linux kernel `6.18.33.2-microsoft-standard-WSL2`;
- Python `3.14.4`;
- `chronyd` active/enabled;
- `chronyd` invoked with `-x`;
- `systemd-timesyncd` described as "inactive / not found"; the summary does not distinguish an inactive unit from a missing unit;
- Hyper-V PTP (Precision Time Protocol) visibility through `/dev/ptp0`;
- `/dev/ptp_hyperv` associated with the Hyper-V PTP device;
- `hyperv` reported as the PTP clock name;
- `tsc` as the active clocksource;
- the kernel command line included `hv_utils.timesync_implicit=1`.

The `-x` option disables `chronyd`'s control of the system clock. An active daemon with this option does not show that it was adjusting the clock. See the [chronyd manual](https://chrony-project.org/doc/4.9/chronyd.html).

The remaining configuration details show visible mechanisms. They do not establish which component was adjusting the clock or caused the observed behavior.

## What the 300-second screen supports

The narrow supported conclusion is:

> **No D4R2-scale slew affecting `CLOCK_MONOTONIC` relative to `CLOCK_MONOTONIC_RAW` was present during this 300-second Ubuntu 26.04 guest-side screen.**

This conclusion is deliberately narrower than a host-referenced qualification. Agreement between guest clocks does not exclude an error shared by them, and the screen does not establish accuracy relative to Windows or an external time reference.

## What it did not establish

The observation did not establish:

- a full host-referenced timing qualification;
- a controlled Ubuntu 24.04 versus Ubuntu 26.04 ranking;
- that Ubuntu 26.04 universally fixes WSL timing;
- that `chronyd` explains the reported result;
- that Hyper-V PTP was adjusting the system clock;
- that Python 3.14 is inherently better for this workload;
- that every long-running timing-sensitive application is safe on 26.04.

Complete live host/runtime qualification was not established in the summarized evidence.

That unavailable qualification should stay unavailable rather than being inferred from this promising guest-side screen.

## Why this result is still useful

A narrow observation can still be useful if its limits are clear.

The reported screen provides a limited example of guest clock-rate behavior without a large observed anomaly.

That makes Ubuntu 26.04 worth testing for new projects, especially when the dependency stack is already compatible with Python 3.14.

It does not justify migrating a stable 24.04 environment without testing your own workload.

## Practical advice

For a new WSL2 project:

1. start with the Ubuntu version that best matches your package/runtime needs;
2. capture the default time-service and clock configuration before changing anything;
3. run a short read-only timing probe;
4. test dependency installation in a clean virtual environment;
5. run your actual application/test suite;
6. only then decide whether the environment is suitable.

For a timing-sensitive workload, one clean 300-second run should be treated as a useful screen, not a guarantee.

## Practical lesson

Treat the reported 26.04 result as a **promising guest-side screen**. Test your own dependencies and timing requirements before committing to a long workload.

A second 300 s screen on another host on 2026-09-24, with committed raw evidence, agreed with this one (full run −0.535 to −0.511 ppm); see [Same-host screens, 2026-09-24](same-host-screens-2026-09-24.md).

See the [read-only diagnostic core and clock caveats](../README.md#the-read-only-diagnostic-core).
