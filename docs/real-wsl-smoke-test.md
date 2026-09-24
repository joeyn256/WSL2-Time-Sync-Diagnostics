# Real WSL2 Smoke Test — Ubuntu 26.04

This page records the first real-machine smoke test of the public CLI after publication.

It is a **software smoke test**, not a scientific timing qualification and not a controlled Ubuntu-version comparison.

## Tested repository revision

```text
07397a9b471f2f66c5d1fd443f8243294fa4c780
```

The repository revision was verified before the CLI was run.

## Environment

```text
WSL detected:  True
Ubuntu:        Ubuntu 26.04.1 LTS
Python:        3.14.4
Kernel:        6.18.33.2-microsoft-standard-WSL2
Clocksource:   tsc
```

The repository was cloned into the Linux filesystem under the user's home directory rather than run from `/mnt/c`.

## Probe

The smoke test ran:

```text
wsl-time-sync diagnose
wsl-time-sync probe --duration 30 --cadence 1
wsl-time-sync analyze
```

The probe returned:

```text
sample_count                       = 31
first_index                        = 0
last_index                         = 30
monotonic_vs_raw_ppm               = -2.737266971197805
realtime_backward_events           = 0
large_realtime_minus_raw_changes   = 0
```

## Interpretation

The public CLI completed the expected diagnose → probe → analyze path successfully on a real Ubuntu 26.04 WSL2 instance.

The 30-second guest-side observation did not detect:

- a realtime backward event;
- a realtime-minus-RAW change larger than the CLI's 500 ms event threshold.

The reported `CLOCK_MONOTONIC` versus `CLOCK_MONOTONIC_RAW` full-run rate was approximately `-2.74 ppm`.

This short smoke test should **not** be interpreted as:

- host-referenced timing accuracy;
- a replacement for the historical 300-second observation;
- a controlled Ubuntu 24.04 versus 26.04 comparison;
- proof of long-duration stability;
- proof that Ubuntu 26.04 or a particular time service universally fixes WSL timing.

## Evidence hashes

The three generated JSON files were retained privately. Their SHA-256 identities were:

```text
diagnose.json  f6017bf3d61600745bee997f2ece7906baef30f8c41e4d14defa5fb7922ef6f8
probe.json     edc0fbee6987e58adfcae56514bd652f896c7b256ae2d92cabe0d2e11507d1f7
analysis.json  5afa1927bcc2f5733bb4779897276668c764eb9af2d114817761d5af5ca7fe16
```

The raw files are not published because environment diagnostics can contain machine-specific identifiers.

## Result

```text
REAL_WSL2_CLI_SMOKE_TEST = PASS
```
