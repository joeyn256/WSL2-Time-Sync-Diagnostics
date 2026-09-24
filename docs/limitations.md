# Limitations

This repository is a practical engineering guide built from a bounded set of WSL2 observations.

It is not a universal benchmark of Ubuntu, Python, Windows, or WSL2.

## No controlled distro ranking

The Ubuntu 24.04 and Ubuntu 26.04 observations were collected under different methods and reference-clock structures.

The historical failed 24.04 timing run (D4R2) used Windows-side QueryPerformanceCounter (QPC) as its elapsed-time reference.

The accepted 26.04 screen was primarily guest-side.

That means this project does **not** establish a controlled timing ranking such as:

```text
Ubuntu 26.04 is X times more accurate than Ubuntu 24.04.
```

The 26.04 observation is encouraging, but it is not a matched head-to-head experiment.

## Single-environment evidence

The core observations came from one investigated Windows/WSL environment and specific software versions.

They should not be generalized to:

- every Windows build;
- every WSL release;
- every kernel;
- every machine;
- every Hyper-V configuration;
- every Ubuntu installation.

Reproduction on another system is useful new evidence, not confirmation that the original environment represented everyone.

## Causality remains limited

The Ubuntu 24.04 work found a strong association between `systemd-timesyncd` state and the recurring timing pathology.

The controlled causal result remained inconclusive.

The project does not prove:

- `systemd-timesyncd` was the sole wall-clock writer;
- Hyper-V alone caused the behavior;
- WSL alone caused the behavior;
- one daemon change explains every timing path.

## Service state does not prove clock state

A service can stop while a previously commanded kernel correction continues.

Therefore:

```text
service inactive
```

does not imply:

```text
timebase settled
```

This is a central limitation of simple stop/wait/benchmark experiments.

## Guest-side agreement is not absolute accuracy

Two guest clocks can agree closely while sharing an error relative to the host or an external reference.

The Ubuntu 26.04 screen therefore supports a bounded guest-relative conclusion.

It does not prove absolute guest-to-host accuracy.

## The 26.04 result is a screen, not a guarantee

The accepted 300-second Ubuntu 26.04 observation found no D4R2-scale `CLOCK_MONOTONIC` versus `CLOCK_MONOTONIC_RAW` slew.

That is useful evidence.

It does not establish:

- all-day or multi-day stability;
- behavior across suspend/resume;
- behavior across reboots;
- behavior on another host;
- behavior under every workload;
- a universal fix for WSL timekeeping.

## Full host/runtime qualification (TP1R5) is unavailable

A later, stricter engineering branch attempted to establish a much broader Windows-host/runtime qualification.

Complete live host/runtime qualification is not established by the summarized evidence.

The guide therefore does not claim:

- successful live host firewall-provider `CREATE/VERIFY`;
- completed production runtime qualification;
- successfully provisioned/admitted private Python and .NET toolchains;
- a fresh corrected production preflight;
- current same-boot continuity;
- current host restoration;
- success in the separate build/test qualification (LI2).

The historical comparator, boot, and modeled-mode results remain useful within their recorded scopes.

## Historical tests are finite

Passing:

- 156 comparator vectors;
- 40 boot-classification vectors;
- 22 modeled mode-harness cases;

shows behavior for those exact tests and exact bound code.

It does not prove exhaustive correctness.

It also does not turn modeled provider behavior into live Windows provider evidence.

## Python compatibility is workload-specific

This repository does not provide an ecosystem-wide package compatibility ranking for Python 3.12 versus Python 3.14.

Package support changes over time.

Your result depends on:

- your direct and transitive dependencies;
- package versions;
- `Requires-Python` constraints;
- wheel availability;
- architecture;
- native extensions;
- source-build requirements;
- your own tests.

Treat any compatibility result as dated.

## No universal migration recommendation

This project does not say that every Ubuntu 24.04 user should migrate to 26.04.

Migration has costs:

- dependency changes;
- interpreter changes;
- package availability;
- environment rebuilds;
- operational risk.

If your current environment is stable and meets your needs, validate before migrating.

## No universal daemon recommendation

The guide does not recommend permanently disabling `systemd-timesyncd` or universally preferring `chronyd`.

The observed 26.04 environment used `chronyd -x`, but that does not prove chronyd caused the clean result or that the same configuration is correct for every WSL2 machine.

## Public evidence is intentionally narrower than private investigation history

The public guide omits private evidence paths and unrelated private project details. It retains a few labels for historical runs and qualification work so their scopes remain distinguishable.

That means some claims are summarized rather than accompanied by the full original evidence chain.

The public goal is reproducible engineering guidance without exposing unrelated private material.

## What would strengthen the evidence

Useful future work could include:

- matched Ubuntu 24.04 and 26.04 measurements on the same host and method;
- repeated runs across clean boots;
- suspend/resume characterization;
- host-referenced 26.04 measurements;
- testing across multiple Windows/WSL versions;
- a dated Python dependency compatibility matrix for representative workloads.

None of that is required for the current guide to remain useful.

## Bottom line

The repository is strongest as a documented case study and diagnostic guide.

Use it to decide what to measure on **your** WSL2 environment, not as a substitute for measuring your environment.
