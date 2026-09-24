# Upstream WSL time synchronization status

Upstream status checked **2026-09-24 (UTC)**.

The sources support a real default-controller conflict class, but do not establish
the sole cause of this project's historical Ubuntu 24.04 failure. This page
separates vendor facts, current issue status, project observations, and mechanism
inference. It does not report a new timing experiment.

## Historical Microsoft sleep/resume bug

Microsoft's [WSL 2.1.1 release](https://github.com/microsoft/WSL/releases/tag/2.1.1),
published **2024-01-22** and marked as a prerelease, enabled the implicit
`ICTIMESYNCFLAG_SYNC` patch, identified #10006 as solved, and updated the kernel
to **5.15.146.1-2**. A [maintainer closed #10006](https://github.com/microsoft/WSL/issues/10006#issuecomment-1904745877)
that day with a 2.1.1 resolution notice. It is accurate to say Microsoft
considered that tracked problem resolved, not that all WSL timing defects ended.

Peter Martincic's Microsoft-authored
[WSL kernel patch](https://github.com/microsoft/WSL2-Linux-Kernel/commit/ef0917a0635d92d4f4fb29d8a3efdf53d38f25e6)
explains that a Hyper-V host bug can omit the explicit SYNC flag after modern
suspend. The [upstream Linux equivalent](https://github.com/torvalds/linux/commit/adf47524b56a791734ae24da8412c6579e2fab4f)
was accepted later; its date should not be confused with the WSL shipment.

In the [current WSL kernel implementation](https://github.com/microsoft/WSL2-Linux-Kernel/blob/14794180686c2fb6307fbe359c359bec765249f3/drivers/hv/hv_util.c#L293-L412),
SAMPLE normally supplies host-time information rather than a forced system-clock
set. With `timesync_implicit` enabled, guest time **at least five seconds behind**
the adjusted host time also triggers the SYNC work path; the implicit condition
does not separately test the SAMPLE bit. Explicit SYNC triggers that path
regardless of the implicit setting. The worker sets guest time-of-day after
successful host-time retrieval (with a separate 600-second sample freshness
limit). This is not continuous frequency locking, a symmetric five-second error
bound, or a guarantee about `CLOCK_MONOTONIC` rate. The module boolean itself
defaults to false; [WSL supplies `hv_utils.timesync_implicit=1`](https://github.com/microsoft/WSL/blob/2.7.14/src/windows/service/exe/WslCoreVm.cpp#L1575-L1576).

## Later Microsoft reports and releases

These reports must not be treated as one proven defect or equated with #10006.
Community descriptions identify symptoms, not Microsoft-confirmed root causes.

| Report | Status at review | What the public record establishes |
|---|---|---|
| [#12583: MONOTONIC frequency inaccurate](https://github.com/microsoft/WSL/issues/12583) | Open | No Microsoft root-cause acknowledgement, linked WSL fix, milestone, or ETA found. |
| [#40745: reported periodic VM pauses](https://github.com/microsoft/WSL/issues/40745) | Open | No Microsoft root-cause acknowledgement, linked fix, milestone, or ETA found; no maintainer-established link to #12583. |
| [#13867: Ubuntu 24.04 clock drift](https://github.com/microsoft/WSL/issues/13867#issuecomment-3664953521) | Closed 2025-12-17 | Bot closure after seven days without author activity; not a technical resolution. |
| [#12765: cannot turn off implicit sync](https://github.com/microsoft/WSL/issues/12765#issuecomment-5526014916) | Closed 2026-09-03 | Bot closure after a year of inactivity; a maintainer asked about the use case, but no fix was identified. A community success report was subsequently retracted. |

The latest stable release at review was
[WSL 2.7.14 (2026-09-11)](https://github.com/microsoft/WSL/releases/tag/2.7.14);
[2.9.12 (2026-09-14)](https://github.com/microsoft/WSL/releases/tag/2.9.12)
was a prerelease. Reviewing recent release notes and kernel history found no fix
explicitly tied to the MONOTONIC/default-controller reports above. There **was**
a separate [June 2026 x86 timer-MSR correction](https://github.com/microsoft/WSL2-Linux-Kernel/commit/73049104541866f41d5497d7a4cb23541812dc39)
for an out-of-tree patch affecting guests without TSC. The kernel update in
[WSL 2.7.9](https://github.com/microsoft/WSL/releases/tag/2.7.9)
was described as repairing boot regressions under KVM/older AMD chipsets and was
carried into subsequent stable releases. It would be inaccurate to claim that
recent WSL releases contain no timing-related fixes at all.

## Canonical's Ubuntu 24.04 guidance

Canonical's official [time synchronization page](https://ubuntu.com/wsl/docs/latest/explanation/time-sync/)
identifies potential disagreement between Hyper-V and guest NTP discipline. It
says Ubuntu 24.04 and earlier enable `systemd-timesyncd.service` by default and
recommends disabling it when Windows/Hyper-V synchronization is desired. The
page was introduced through [PR #1627](https://github.com/canonical/ubuntu-pro-for-wsl/pull/1627),
merged **2026-04-16**, with [versioned source](https://github.com/canonical/ubuntu-pro-for-wsl/blob/f9153f24fb42f2b2939414869a033effd39c3d3b/docs/explanation/time-sync.md).

Its example uses `systemctl disable systemd-timesyncd.service`. As the
[systemctl manual specifies](https://github.com/systemd/systemd/blob/v255/man/systemctl.xml#L881-L900),
`disable` alone does not stop an already-running service; `--now` or a separate
stop is required for that. Neither operation proves that the kernel clock has
settled. This is conditional upstream configuration guidance, not a demonstrated
repair for every historical failure.

Canonical's description of #12765 as open is now stale: its administrative
closure does not demonstrate that the override works. Also, disabling implicit
SYNC would not disable explicit host SYNC in the kernel code above.

## What changed in 25.10 and 26.04

Ubuntu selected chrony as its default time daemon starting with **25.10**.
The [26.04 release notes](https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/#chrony)
confirm the change for new installations. Daemon selection and whether its
service can run under WSL are separate changes: the
[25.10 unit](https://git.launchpad.net/ubuntu/+source/chrony/tree/debian/chrony.service?id=de4c18188d37067dcabe2a70671da18ef8ca0866)
excluded containers; [Launchpad #2122337](https://bugs.launchpad.net/ubuntu/+source/chrony/+bug/2122337)
and chrony **4.8-2ubuntu1** added a WSL exception in 26.04.

The 26.04 behavior is a combination of Ubuntu packaging and chrony's `-x` option:

- The [service unit](https://git.launchpad.net/ubuntu/+source/chrony/tree/debian/chrony.service?id=9b06cb69e13d04eb1cfe69bffc3b78b0628c5487) invokes a startup wrapper.
- The [default configuration](https://git.launchpad.net/ubuntu/+source/chrony/tree/debian/chrony.default?id=9b06cb69e13d04eb1cfe69bffc3b78b0628c5487) sets `SYNC_IN_CONTAINER="no"`.
- The [wrapper](https://git.launchpad.net/ubuntu/+source/chrony/tree/debian/chronyd-starter.sh?id=9b06cb69e13d04eb1cfe69bffc3b78b0628c5487) checks container detection and `CAP_SYS_TIME`; absent an opt-in, either container detection (including WSL) or missing capability makes it add `-x`.
- [chronyd's manual](https://chrony-project.org/doc/4.8/chronyd.html) defines `-x` as disabling system-clock control while retaining clock-offset/frequency tracking.

Thus chrony is not inherently incapable of controlling a WSL clock. Setting
`SYNC_IN_CONTAINER="yes"` and restarting bypasses the wrapper's automatic `-x`
fallback; it does not grant a missing capability or remove an explicitly supplied
`-x`. Opting into clock control can reintroduce competing discipline.

**Architecture inference:** in a fresh, unmodified 26.04 WSL installation with
these defaults, Hyper-V implicit sync remains enabled and chrony does not write
the system clock. That removes this particular default guest-NTP competitor.
It does not rule out other writers, host errors, pauses, clocksource problems,
or custom configuration. The project's [26.04 screen](findings-ubuntu-26.04.md)
and separate [CLI smoke test](real-wsl-smoke-test.md) remain bounded observations,
not proof of a universal timing fix.

## Fresh installation is not an in-place upgrade

An upgraded system can retain `systemd-timesyncd`. The
[26.04 release notes](https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/#chrony)
give these explicit migration commands for existing systems after upgrading:

```sh
apt-mark auto systemd-timesyncd
apt install chrony
```

These are administrative package changes, not actions performed by this project's
diagnostic CLI. A 24.04-to-26.04 upgrade alone does not establish a daemon
migration, remove retained configuration, or prove that a clock conflict ended.

## Ubuntu 24.04 backport or roadmap

**No public commitment/roadmap was found as of 2026-09-24** to change Ubuntu
24.04's WSL time-sync default, automatically disable timesyncd, migrate Noble to
chrony, or backport the complete 26.04 behavior.

This bounded search covered Ubuntu WSL and Ubuntu Pro for WSL issues/PRs,
Canonical's documentation and release notes, Launchpad chrony records and Noble
package history, Ubuntu release/development mailing-list searches, and Microsoft
WSL issues, releases, and kernel changes. The
[published migration plan](https://lists.ubuntu.com/archives/ubuntu-release/2025-May/006423.html)
targets 25.10 onward. There was [discussion of a future automatic upgrade path](https://bugs.launchpad.net/ubuntu/+bug/2111342/comments/15),
but the release-upgrader task is deferred with no milestone; that is not a
commitment to change Noble's WSL default. #2122337 is a 26.04 WSL service fix.
No matching Noble SRU commitment was located; this was not an exhaustive audit
of every pending SRU. The result does not mean Canonical or Microsoft will never
fix 24.04.

## Connection to this project's D4R2 evidence

The [public historical account](timesyncd-investigation.md) reports a confirmed
timesyncd stop followed by about 60 Windows-QPC seconds of waiting. PRE still
had `tick=10833`, `freq=2157314` (historical calculation **+83,332.918 ppm**).
The first 30-second MONOTONIC/QPC enclosure was **+26,665.299 to +26,724.999 ppm**;
later windows approached nominal. POST had `tick=10000`, `freq=-27187`
(approximately **-0.415 ppm**). These are preserved project observations,
not independently reproduced measurements in this review.

Primary code provides a sound reason that stopping a daemon need not undo kernel
discipline: [systemd v255 timesyncd](https://github.com/systemd/systemd/blob/v255/src/timesync/timesyncd-manager.c#L243-L316)
uses `clock_adjtime()` with `ADJ_OFFSET`/`STA_PLL` for small offsets and
`ADJ_SETOFFSET` for large ones. This is relevant upstream-family code, not an
authentication of D4R2's exact installed binary. The
[Linux adjtimex API](https://man7.org/linux/man-pages/man2/adjtimex.2.html)
sets kernel state, rather than a correction scoped to the caller's lifetime.
The [kernel implementation](https://github.com/microsoft/WSL2-Linux-Kernel/blob/a07f9ea8a99139913acbcc1c160b132cb2a49c81/kernel/time/ntp.c)
retains frequency/tick state; even `ntp_clear()` does not reset `time_freq` or
`tick_usec` to their nominal values.

There is an important limit: that timesyncd adjustment function does not set
`ADJ_TICK`, and `tick` is not a phase offset that simply decays. Persistence
therefore does **not** identify who set `tick=10833` or explain its later reset
to `10000`. A writer/kernel-event trace would be needed to resolve that history.

Canonical independently documents that simultaneous Hyper-V and guest-NTP
discipline can conflict. D4R2 is consistent with that architecture and establishes
that the confirmed stop did not immediately yield nominal kernel state or a
nominal first measurement window. It does not prove timesyncd was the sole writer
or initiating cause, or that the whole recovery was an autonomous timesyncd slew.
The controlled C1 result remains inconclusive.

> Service stopped does not mean correction finished, clock settled, or benchmark ready.
