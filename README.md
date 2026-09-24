# WSL2 Timing & Ubuntu Environment Guide

A practical guide based on reported historical observations for choosing and validating an Ubuntu/Python environment for timing-sensitive work under WSL2.

## What this project is

This project grew out of a real debugging problem: long-running, time-sensitive work under WSL2 produced timing behavior that was serious enough to invalidate a benchmark and consume a large amount of engineering time.

The goal here is not to declare one Ubuntu release universally "good" and another "bad." It is to document what was observed, what the evidence actually supports, and what you should check before trusting a long-running or timing-sensitive workload.

The two main questions are:

- Should a new WSL2 project use Ubuntu 24.04 or Ubuntu 26.04?
- Should a Python project stay on Python 3.12 or move to Python 3.14?

The answer depends on your workload, dependency compatibility, and how sensitive you are to timing behavior.

This repository contains narrative summaries and a small read-only diagnostic CLI, but not the original historical measurement logs. The findings below describe historical observations; they do not validate a reader's current machine.

Read more: [Ubuntu 24.04 findings](docs/findings-ubuntu-24.04.md), [Ubuntu 26.04 findings](docs/findings-ubuntu-26.04.md), and [the time-service investigation](docs/timesyncd-investigation.md).

---

## Short version

### If you are starting a new project

Ubuntu 26.04 is a reasonable candidate, especially if your dependencies support Python 3.14, but this project does **not** claim that 26.04 universally fixes WSL timing.

The reported 300-second Ubuntu 26.04 guest-side screen showed no large anomaly in its measured clock-rate comparison. That is encouraging, but it did not establish accuracy against the Windows host or prove that every relevant clock was stable.

### If you need Python 3.12 or older package compatibility

Ubuntu 24.04 remains a reasonable environment, but timing-sensitive workloads should validate their time behavior before committing to a long run.

The historical 24.04 investigation observed recurring large realtime corrections. In its A–B–A intervention, the active phase had four qualifying events, the stopped phase had none under the frozen detector, and the restored active phase had two real but sub-threshold events. The formal causal result therefore remained **inconclusive**.

### If you already have a working 24.04 environment

Do not migrate simply because of this repository.

Instead:

1. inspect your WSL and distro configuration;
2. run a bounded read-only timing probe;
3. look for abnormal clock-rate behavior, including signs of a slew (a gradual clock correction);
4. verify your actual Python/package requirements;
5. migrate only if the evidence and compatibility tradeoff justify it.

---

## The most important timing lesson

A fixed wait after changing a time service is **not** a reliable readiness test.

One historical experiment confirmed `systemd-timesyncd` stopped while the unit remained enabled, then waited about 60 seconds measured by Windows QueryPerformanceCounter (QPC). PRE still showed a large kernel correction state (`tick=10833`, historical baseline calculation about +83,332.918 ppm), and the first 30-second MONOTONIC/QPC window was +26,665.299 to +26,724.999 ppm. Later windows returned near nominal. The stop succeeded; the fixed wait still had not established readiness.

That means:

> **service state is not the same thing as clock-settled state.**

For timing-sensitive work, use finite observations with explicit bands and retain anomalies. A within-band observation does not certify benchmark readiness.

---

## What the Ubuntu 24.04 investigation supports

The historical Ubuntu 24.04 evidence supports these bounded conclusions:

- recurring large realtime correction events were observed in the investigated environment;
- the examined intervention **stopped** `systemd-timesyncd` and later started it again; the unit remained enabled;
- C1 changed materially across the active/stopped/restored phases but did not satisfy its frozen causal-success rule;
- D4R2 still showed a large kernel correction state after a 60-second QPC-measured wait following the confirmed stop;
- the first D4R2 30-second MONOTONIC/QPC window was +26,665.299 to +26,724.999 ppm while RAW/QPC stayed within the historical screen;
- later D4R2 windows returned near nominal, consistent with a residual correction decaying after the service transition.

What it **does not** support:

- `systemd-timesyncd` is proven to be the sole root cause;
- every Ubuntu 24.04 WSL2 installation has the same behavior;
- disabling `systemd-timesyncd` is a permanent fix;
- a benchmark is safe merely because the service is inactive.

The controlled causal result remains **inconclusive**.

---

## What the Ubuntu 26.04 observation supports

The reported 300-second Ubuntu 26.04 default-state screen was promising.

All ten fixed 30-second `CLOCK_MONOTONIC` versus `CLOCK_MONOTONIC_RAW` windows stayed within the predeclared ±1000 ppm engineering band. The most negative reported window bound was about `-1.19 ppm`, and the full-run enclosure was about `-0.50 .. -0.46 ppm`.

Here, D4R2 is the label for the historical failed Ubuntu 24.04 timing run. The 26.04 screen supports one useful, narrow conclusion:

> **No D4R2-scale slew affecting `CLOCK_MONOTONIC` relative to `CLOCK_MONOTONIC_RAW` was present during this 300-second guest-side observation.**

Why that comparison is meaningful: in the historical D4R2 failure, `CLOCK_MONOTONIC` versus Windows QPC showed a very large early rate anomaly while `CLOCK_MONOTONIC_RAW` versus QPC passed. A slew on that historical scale would therefore have produced a large `MONOTONIC`-versus-`RAW` separation.

This is still a **guest-side** screen. It does not establish absolute accuracy against Windows or an external reference, and errors shared by the guest clocks could remain invisible.

It is **not** a controlled head-to-head ranking between Ubuntu 24.04 and 26.04, and it is not proof that Ubuntu 26.04 or `chronyd` universally fixes WSL2 timing.

The reported 26.04 environment included:

- Ubuntu 26.04.1 LTS;
- WSL 2.7.13.0;
- Linux kernel `6.18.33.2-microsoft-standard-WSL2`;
- Python 3.14.4;
- `chronyd` active/enabled with `-x`;
- `systemd-timesyncd` described as "inactive / not found"; the summary does not distinguish those service states;
- Hyper-V PTP (Precision Time Protocol) visible through `/dev/ptp0`;
- `tsc` as the active clocksource.

These describe that historical environment, not every installation's defaults. The `-x` option disables `chronyd`'s control of the system clock, so an active daemon in this mode does not demonstrate that it was adjusting the clock. See the [chronyd manual](https://chrony-project.org/doc/4.9/chronyd.html).

The configuration alone does not identify which component was adjusting the clock or explain the observed difference. The [26.04 findings](docs/findings-ubuntu-26.04.md) retain the reported numerical summary and its interpretation limits.

---

## Python 3.12 vs Python 3.14

Do not choose the interpreter version from release number alone.

Python 3.14 can be attractive for a new project, but the practical question is whether **your dependency set** supports it.

For a new environment:

- list your direct dependencies;
- test installation in a clean virtual environment;
- distinguish wheels from source builds;
- run your actual test suite;
- check native/compiled dependencies carefully;
- record exact package and interpreter versions.

If your project depends on packages that are mature on Python 3.12 but not yet proven in your Python 3.14 environment, staying on 3.12 can be the lower-risk engineering decision.

This repository does not make a categorical "Python 3.14 is better than Python 3.12" claim.

---

## Guest-side v0.2 workflow

The CLI is standard-library-only at runtime. Commands observe guest clocks and kernel state without privileges, clock writes, service changes, or a Windows companion.

- `diagnose` records Linux/WSL guest metadata, service inventory and an `adjtimex(modes=0)` snapshot. Unsupported ABI/layouts return structured unavailability.
- `probe` writes schema v2: RAW before, REALTIME, MONOTONIC, optional BOOTTIME, RAW after. It preserves integer timestamps, bracket widths and explicit null/error fields. RAW is a guest reference, not Windows QPC.
- `analyze` accepts v0.1 and v0.2 probe inputs. It reports fixed windows, uncertainty intervals, signed realtime events, and `WITHIN`, `OUTSIDE`, or `INDETERMINATE`. Early adverse windows remain visible when the full-run average improves. Legacy sequential samples have unknown acquisition uncertainty and cannot establish `WITHIN`.
- `settle-check` makes a finite series of read-only kernel-state observations. Its explicitly named historical example policy checks `tick == 10000` and `abs(freq/65536) < 100 ppm`; these are configurable example settings. It reports `WITHIN_CONFIGURED_BAND`, `ANOMALY_OBSERVED`, or `INDETERMINATE`, with no universal readiness verdict.
- `compare` checks schema, acquisition/reference, analysis settings, coverage and any supplied continuity label. It emits numeric differences only for `COMPARABLE` reports; other results are `DIFFERENT_METHOD` or `INSUFFICIENT_CONTEXT`.
- `python-check` reports the current interpreter and whether named distributions are installed. It does not install packages or evaluate their behavior.

The default analysis examples are 10-second windows, a ±100 ppm rate band and a 500,000,000 ns realtime-minus-RAW change band. Declare suitable settings for your question; these defaults are not definitions of clock health.

See the [CLI and schema reference](docs/v0.2-guest-core.md), [methodology](docs/methodology.md), and [limitations](docs/limitations.md). Synthetic fixtures recreate historical failure *shapes* parametrically; no private raw measurements are distributed.

Keep original measurements privately. Before sharing output, remove usernames, hostnames, personal paths, literal boot/machine identifiers, and sensitive process arguments from a separate copy; document redactions that affect interpretation.

---

## Historical engineering work and remaining limits

A later administrator-run engineering branch produced additional component tests and failure findings, but a reuse audit found that several previously quoted counts belonged mainly to **firewall/preflight machinery rather than timing validation**.

Those counts are therefore not used as evidence for the clock conclusions in this guide.

The v0.2 guest core implements bracketed sampling, fixed-window interval analysis, read-only kernel-state observation, and parametric synthetic failure fixtures. A Windows QPC companion remains outside this release. No historical controller, administrator flow, or governance apparatus has been transplanted.

Complete live host/runtime qualification from the old administrator-run branch remains unavailable and is not inferred from component-test counts or file hashes.

---

## What not to do

Avoid these shortcuts:

- "Ubuntu 26.04 looked good once, therefore it fixes the problem."
- "`systemd-timesyncd` was involved, therefore it was the sole cause."
- "The service is stopped, therefore the kernel clock is settled."
- "The hashes match, therefore the runtime behavior is qualified."
- "Python 3.14 is newer, therefore every project should use it."
- "A mocked provider test proves real Windows firewall-provider behavior."

Each of these collapses a narrower observation into a broader claim than the evidence supports.

---

## Practical recommendation

For most users:

### New project with modern dependencies
Try Ubuntu 26.04 and Python 3.14 in an isolated environment. Validate your dependency stack and run a short read-only timing probe before committing to a long timing-sensitive workload.

### Dependency-sensitive project
Use the interpreter and Ubuntu release your dependencies actually support. Python 3.12 on Ubuntu 24.04 can still be the more conservative choice.

### Existing timing-sensitive WSL2 project
Do not change the system first. Capture the current state, run a bounded diagnostic, and determine whether you have a real timing problem before changing services or migrating distributions.

---

## Evidence boundaries

This repository distinguishes between:

- **historical test evidence**;
- **guest-side observations**;
- **host-referenced qualification**;
- **live runtime qualification**;
- **causal claims**.

A result in one category is not automatically evidence for another.

Current high-level status:

| Topic | Status |
|---|---|
| Ubuntu 24.04 historical timing failure | Observed |
| `systemd-timesyncd` intervention | Active/stopped/restored phases differed; formal C1 causal result remained inconclusive |
| Controlled causal proof | Inconclusive |
| Ubuntu 26.04 guest-side default observation | Promising 300-second screen; no D4R2-scale MONOTONIC-vs-RAW slew observed |
| Ubuntu 24.04 vs 26.04 timing ranking | Not established |
| Full host/runtime qualification | Unavailable |
| v0.2 guest-core software checks | 193 tests passed on Python 3.12.3 and 3.14.4; installed CLI smoke passed on both WSL environments |
| Historical administrator-branch runtime qualification | Not established by these guest-core software tests |
| Python 3.14 universally preferable to 3.12 | Not claimed |

---

## Where to keep the repository in WSL

If you are working primarily from the Linux command line, keep the repository in the Linux filesystem, for example:

```bash
~/Projects/wsl2-time-sync-guide
```

rather than under a mounted Windows path such as:

```text
/mnt/c/Users/<you>/...
```

Microsoft recommends storing files in the WSL filesystem for the best performance when working from Linux, and storing files in the Windows filesystem when working primarily from Windows tools.

See Microsoft's guidance: https://learn.microsoft.com/windows/wsl/filesystems#file-storage-and-performance-across-file-systems

---

## Try the read-only CLI

The repository includes a small standard-library-only diagnostic CLI.

Install it in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Capture read-only environment metadata:

```bash
wsl-time-sync diagnose --output diagnose.json
```

Run a short guest-side timing probe:

```bash
wsl-time-sync probe --duration 30 --cadence 1 --output probe.json
```

Analyze that probe offline:

```bash
wsl-time-sync analyze probe.json --window 10 --rate-band-ppm 100 --event-threshold-ns 500000000 --output analysis.json
```

Observe the finite historical example kernel-state policy:

```bash
wsl-time-sync settle-check --duration 30 --cadence 1 --required-consecutive 3 --output settle.json
```

Compare two analysis reports descriptively:

```bash
wsl-time-sync compare run-a.analysis.json run-b.analysis.json
```

Check the current interpreter and optionally inspect whether distributions named
in a requirements file are installed:

```bash
wsl-time-sync python-check --requirements requirements.txt
```

The default CLI does **not** stop time services, modify firewall state, change
WSL configuration, install packages, or replace system Python.

See [Methodology](docs/methodology.md) and [Limitations](docs/limitations.md)
before interpreting timing results.

---

## Further reading

- [Dated upstream time-sync status, defaults, and upgrade caveats](docs/upstream-time-sync-status.md)
- [Ubuntu 24.04 findings](docs/findings-ubuntu-24.04.md)
- [Ubuntu 26.04 findings](docs/findings-ubuntu-26.04.md)
- [`systemd-timesyncd` investigation](docs/timesyncd-investigation.md)
- [Python 3.12 vs Python 3.14](docs/python-3.12-vs-3.14.md)
- [v0.2 CLI and schema reference](docs/v0.2-guest-core.md)
- [Methodology](docs/methodology.md)
- [Limitations](docs/limitations.md)
- [Real Ubuntu 26.04 WSL2 CLI smoke test](docs/real-wsl-smoke-test.md)

---

## Project philosophy

This project values a useful, honest result over a perfect-looking one.

A failed experiment can be valuable.
An inconclusive causal test can be valuable.
A promising observation can be valuable.
An unavailable qualification can be valuable.

The important thing is to keep those categories separate.

That is the main lesson behind this guide.
