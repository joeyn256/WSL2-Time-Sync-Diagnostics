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

The historical 24.04 investigation observed recurring large realtime corrections and found a strong experimental association with `systemd-timesyncd` state. That does **not** prove `systemd-timesyncd` was the sole root cause.

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

One historical experiment stopped the relevant service and then waited 60 seconds measured by Windows QueryPerformanceCounter (QPC), the host's elapsed-time counter. The run still failed its timing criteria. Its early anomaly and later reduction were consistent with a residual kernel slew after the service had stopped; the fixed wait had not established readiness.

That means:

> **service state is not the same thing as clock-settled state.**

For timing-sensitive work, prefer a measured readiness check over "wait N seconds and hope the clock has settled."

---

## What the Ubuntu 24.04 investigation supports

The historical Ubuntu 24.04 evidence supports these bounded conclusions:

- recurring large realtime correction events were observed in the investigated environment;
- those events showed a strong association with `systemd-timesyncd` state;
- stopping the service suppressed the recurring correction pattern that had been observed;
- an already-commanded kernel slew could persist after the service was stopped;
- therefore an immediate benchmark, or even a simple fixed-delay benchmark, can still capture a transient inherited from the earlier correction.

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

## Proposed diagnostic workflow

The repository includes a small first implementation of these commands. Timing diagnostics inspect the current state without changing time services. A package-installation check is separate: it should use an isolated environment and will write files there.

```text
wsl-time-sync diagnose
wsl-time-sync probe
wsl-time-sync analyze
wsl-time-sync compare
wsl-time-sync python-check
```

### `diagnose`

Capture:

- Windows version;
- WSL version;
- distro/release;
- kernel;
- Python version;
- systemd version;
- active clocksource;
- visible time services;
- Hyper-V/PTP visibility;
- boot ID;
- relevant process state.

Keep original measurements privately. Before sharing output, remove usernames, hostnames, personal paths, literal boot/machine identifiers, and sensitive process arguments from a separate copy; document redactions that affect interpretation.

For a small check you can run now in an already-open Ubuntu shell with systemd, use:

```sh
cat /etc/os-release
uname -r
python3 --version
systemctl is-active systemd-timesyncd.service
systemctl is-enabled systemd-timesyncd.service
```

Record the output, including unavailable commands or units. These are inventory checks, not timing tests or proof of clock stability. The [time-service investigation](docs/timesyncd-investigation.md) explains the distinction.

### `probe`

Run a bounded timing observation without changing services.

A good probe should:

- identify the measured clocks and reference explicitly;
- retain exact timestamps;
- capture enough metadata to interpret the run later;
- avoid automatic retries that erase the first failure;
- define the observation duration, comparison windows, and tolerances before running;
- clearly distinguish incomplete from passed.

On Linux, `CLOCK_MONOTONIC` avoids wall-clock jumps but remains subject to frequency adjustments. `CLOCK_MONOTONIC_RAW` avoids those software adjustments; it is still not an independent Windows-host reference. Choose clocks for the question being tested, rather than treating "monotonic" as proof of an unaffected timebase. See the [Linux clock documentation](https://man7.org/linux/man-pages/man3/clock_gettime.3.html).

### `analyze`

Analyze a saved run offline, preserving its original samples.

### `compare`

Compare two recorded runs without modifying either. Check that their clock references, calculations, window lengths, and conditions are comparable before interpreting numerical differences.

### `python-check`

Evaluate interpreter and package compatibility in an isolated virtual environment without replacing the system Python. Installation tests can download packages and write files; they are not read-only diagnostics.

---

## Historical component tests and remaining limits

A later Windows-host investigation reported useful component-test evidence:

- comparator test vectors: `156/156`;
- boot-classification test vectors: `40/40`;
- modeled mode-harness cases: `22/22`;
- two PowerShell variable-name collisions, including one that made part of a preliminary check ineffective.

These are historical component/model results. They do not establish real host-provider behavior or complete live host/runtime qualification.

The summarized evidence does **not** establish successful host setup and verification, production qualification, private Python/.NET provisioning, a fresh successful corrected preflight, current boot continuity, current host restoration, or the separate build/test qualification.

Those outcomes remain unavailable or not completed, as applicable. They are not inferred from historical test counts or file hashes.

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
| `systemd-timesyncd` association | Strong association, not sole-cause proof |
| Controlled causal proof | Inconclusive |
| Ubuntu 26.04 guest-side default observation | Promising 300-second screen; no D4R2-scale MONOTONIC-vs-RAW slew observed |
| Ubuntu 24.04 vs 26.04 timing ranking | Not established |
| Comparator historical vectors | 156/156 |
| Boot-classifier historical vectors | 40/40 |
| Mode-harness historical cases | 22/22 |
| Full host/runtime qualification | Unavailable |
| Separate build/test qualification | Not completed |
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
wsl-time-sync analyze probe.json --output analysis.json
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

- [Ubuntu 24.04 findings](docs/findings-ubuntu-24.04.md)
- [Ubuntu 26.04 findings](docs/findings-ubuntu-26.04.md)
- [`systemd-timesyncd` investigation](docs/timesyncd-investigation.md)
- [Python 3.12 vs Python 3.14](docs/python-3.12-vs-3.14.md)
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
