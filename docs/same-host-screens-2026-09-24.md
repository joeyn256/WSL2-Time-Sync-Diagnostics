# Same-host screens, 2026-09-24: Ubuntu 24.04 with timesyncd active versus Ubuntu 26.04 fresh default

This page records two guest-side timing screens taken on one Windows host on the same day with the same read-only tooling, one per distro, each from a fresh WSL virtual machine. It exists because the README's comparison figure had no measured trace for "Ubuntu 24.04 with `systemd-timesyncd` enabled": the historical D4R2 value (+26,665.299 to +26,724.999 ppm) was measured *after* the service had been stopped, and nothing in this repository had measured the enabled state directly.

The raw probe and analysis JSON files, the redacted environment snapshots and the run logs are committed under [`evidence/2026-09-24-same-host-screens/`](../evidence/2026-09-24-same-host-screens/).

**Evidence tier:** PROJECT OBSERVATION, guest-side. `CLOCK_MONOTONIC` is compared with `CLOCK_MONOTONIC_RAW` inside RAW brackets. No Windows QPC or external reference was collected, so nothing here is host-referenced accuracy, and the two distros are not a controlled ranking: they are different distribution images with different daemons, observed one after the other on the same host.

## Headline results

| Situation | 300 s guest-side result | Kernel `tick` (adjtimex) |
|---|---|---|
| Ubuntu 24.04.4, `systemd-timesyncd` active and enabled | Every 30 s window OUTSIDE the ±1000 ppm screen: −55,089 to −40,892 ppm (rounded outward). Full run **−48,010.756 to −48,010.740 ppm** (about 4.8 % slow). Eight forward `CLOCK_REALTIME` jumps of +1.47 to +1.69 s, one every ≈34 s. | PRE 10000 → POST **9437** |
| Ubuntu 26.04.1, chrony started with `-x`, no timesyncd | Every 30 s window inside the screen: −0.73 to −0.27 ppm (rounded outward). Full run **−0.535 to −0.511 ppm**. No jumps. | PRE 10000 → POST 10000 |

The 24.04 result reproduced on a second fresh boot the same minute: an independent 20 s two-clock check at about 10 s of uptime read +0.1 ppm, the first 30 s probe window that followed read +433 ppm, the next one read −41,320 ppm, and `tick` had moved from 10000 to 9969.

## Environment

| Item | Value |
|---|---|
| Windows | 11 Pro, build 26200.9457 (25H2) |
| WSL | 2.7.13.0, kernel 6.18.33.2-microsoft-standard-WSL2 |
| Kernel command line | includes `hv_utils.timesync_implicit=1` (set by WSL) |
| Clocksource | `tsc`; `/dev/ptp0` and `/dev/ptp_hyperv` present |
| Ubuntu 24.04 guest | 24.04.4 LTS, systemd 255.4-1ubuntu8.17, `systemd-timesyncd` active/enabled, chrony not installed, NTP server ntp.ubuntu.com (stratum 2), poll interval 32 s |
| Ubuntu 26.04 guest | 26.04.1 LTS, `chronyd -n -F 1 -x` active/enabled, `systemd-timesyncd` not found |
| Windows host clock | **about 1.06 s behind NTP** at 16:50 UTC: `w32tm /stripchart` against time.windows.com and ntp.ubuntu.com reported +1.06 s, and an independent SNTP query reported server minus local of +1.071 s (ntp.ubuntu.com), +1.061 s (time.windows.com) and +1.063 s (time.nist.gov). The Windows Time service (W32Time) was **stopped**, start type Manual. |
| Tooling | `wsl-time-sync` at repository commit `f36795859e16097d08cd6adcd7a83280683d42b6`, package version 0.5.0, Python 3.12.3 (24.04) and 3.14.4 (26.04) |
| WSL configuration | No `.wslconfig` on the host; `/etc/wsl.conf` in both guests sets only `[boot] systemd=true` and a default user |

The host clock offset and the stopped W32Time service are environment facts recorded during the experiment. They are not typical of a managed Windows machine and they matter for the interpretation below.

## Protocol

Every step is read-only inside the guest: no service was started, stopped, enabled or disabled, no package was installed into the system, and nothing was run with elevation.

1. `wsl --shutdown` on the host, so that the WSL virtual machine and its kernel time-keeping state start fresh.
2. Start one distro only and run `screen.sh` (retained in the evidence folder as `run.log`): capture environment and service state, `wsl-time-sync diagnose` (PRE), sleep 60 s, `wsl-time-sync probe --duration 300 --cadence 1`, `wsl-time-sync diagnose` (POST), then `wsl-time-sync analyze` with 30 s windows at the historical ±1000 ppm screen and at the CLI's default ±100 ppm band.
3. `wsl --shutdown`, then repeat for the other distro.
4. For the 24.04 case only, an additional read-only pass ran on a further fresh boot (`followup.log`): timesyncd's own journal and status, the list of running services, an independent 20 s two-clock check written in plain Python, and a second 60 s probe.
5. For both distros, a further fresh boot recorded a kernel-state time series: `wsl-time-sync settle-check --duration 150 --cadence 0.2` (751 read-only `adjtimex(modes=0)` reads) with a concurrent 150 s probe.

The probe began 84 s after boot in the 24.04 run and 79 s after boot in the 26.04 run.

## Ubuntu 24.04 with timesyncd active

Probe: 301 samples, collection complete and verified, ten complete 30 s windows, zero partial windows.

| Window | MONOTONIC vs RAW rate enclosure (ppm) | ±1000 screen | REALTIME − RAW change over the window |
|---|---:|---|---:|
| 0–30 s | −55,088.612 to −55,088.449 | OUTSIDE | −1.654 s |
| 30–60 s | −54,399.438 to −54,399.233 | OUTSIDE | +18.0 ms |
| 60–90 s | −49,693.799 to −49,693.640 | OUTSIDE | +221 ms |
| 90–120 s | −52,680.920 to −52,680.778 | OUTSIDE | +122 ms |
| 120–150 s | −46,915.080 to −46,914.914 | OUTSIDE | +232 ms |
| 150–180 s | −43,802.517 to −43,802.364 | OUTSIDE | +341 ms |
| 180–210 s | −41,451.946 to −41,451.773 | OUTSIDE | +282 ms |
| 210–240 s | −40,892.385 to −40,892.225 | OUTSIDE | +314 ms |
| 240–270 s | −48,810.283 to −48,810.158 | OUTSIDE | +36 ms |
| 270–300 s | −46,349.792 to −46,349.638 | OUTSIDE | −1.392 s |
| Full 300 s | **−48,010.756 to −48,010.740** | OUTSIDE | −1.478 s |

Over the 300.06 s of RAW time, `CLOCK_MONOTONIC` and `CLOCK_BOOTTIME` advanced 285.65 s and `CLOCK_REALTIME` advanced 298.58 s.

Adjacent-sample `CLOCK_REALTIME` changes larger than the 500 ms event band, all forward:

| At sample (≈ s after window open) | REALTIME − RAW change |
|---:|---:|
| 30 → 31 | +1.643 s |
| 64 → 65 | +1.691 s |
| 98 → 99 | +1.646 s |
| 131 → 132 | +1.572 s |
| 165 → 166 | +1.620 s |
| 199 → 200 | +1.480 s |
| 233 → 234 | +1.508 s |
| 267 → 268 | +1.472 s |

The spacing is 33 to 34 s. Between jumps, `CLOCK_REALTIME` falls behind RAW at the same slow rate as `CLOCK_MONOTONIC`; a window that contains no jump (0–30 s, 270–300 s) therefore shows a net change of about −1.4 to −1.7 s, and a window that contains one jump shows a small net change.

Re-analysed with 5 s windows, the rate is never near nominal. It saturates at −83,333 ppm (exactly −1/12) during at least ten of the sixty windows (for example 5–20 s, 40–50 s, 75–85 s, 140–145 s, 215–220 s, 240–245 s and 275–280 s) and sits between −9,422 and −78,394 ppm otherwise, which is the signature of a rate that is being switched, not slewed smoothly.

Kernel state from `adjtimex(modes=0)`:

| Snapshot | Uptime | `tick` | `freq` | `freq` in ppm | `status` | Return |
|---|---:|---:|---:|---:|---:|---|
| PRE (before the 60 s settle) | ≈23 s | 10000 | 0 | 0 | 8192 (STA_NANO) | TIME_OK |
| POST (after the probe) | ≈385 s | **9437** | 2655521 | +40.52 | 8192 | TIME_OK |

`tick` 9437 corresponds to a static rate term of −5.63 %. The measured 300 s average was −4.80 %, and the 5 s structure shows that `tick` was not constant during the run.

### Second boot, same minute

WSL terminated the idle distro after the first script finished, so the follow-up pass ran on a new boot (uptime 3.6 s at its start):

- an independent two-clock check in plain Python over 20 s, at roughly 10 to 30 s of uptime: MONOTONIC vs RAW **+0.1 ppm**, REALTIME vs RAW +0.2 ppm;
- `adjtimex` at about 32 s of uptime: `tick` 10000, `freq` 0, `offset` 0;
- a 60 s probe at roughly 35 to 95 s of uptime: window 0–30 s **+433.1 to +433.3 ppm** (inside the ±1000 screen), window 30–60 s **−41,320.2 to −41,320.0 ppm** (outside); the second window also contained a REALTIME change of −16.6 ms with no large event;
- `adjtimex` at about 97 s of uptime: `tick` **9969**, `freq` 1958529 (+29.88 ppm).

So the pathology was absent in the first half-minute and had started by about 60 to 90 s of uptime, twice in a row.

### What timesyncd itself does

`timedatectl show-timesync` reported `PollIntervalUSec=32s`, `Frequency=0` and a stratum-2 server. Its journal shows only "Contacted time server" and "Initial clock synchronization" lines at each boot. In the systemd v255 source that this package is built from, `manager_adjust_clock` uses `ADJ_STATUS | ADJ_NANO | ADJ_OFFSET | ADJ_TIMECONST | ADJ_MAXERROR | ADJ_ESTERROR` for offsets below `NTP_MAX_ADJUST` = 0.4 s and `ADJ_STATUS | ADJ_NANO | ADJ_SETOFFSET | ADJ_MAXERROR | ADJ_ESTERROR` for larger offsets; `ADJ_TICK` and `ADJ_FREQUENCY` do not appear in the file. A poll every 32 s that finds the clock more than 0.4 s behind therefore produces exactly the forward jumps observed, and timesyncd cannot have written `tick`.

## Ubuntu 26.04 fresh default

Probe: 301 samples, collection complete and verified, ten complete 30 s windows, zero partial windows.

| Window | MONOTONIC vs RAW rate enclosure (ppm) | ±1000 screen | ±100 band | REALTIME − RAW change |
|---|---:|---|---|---:|
| 0–30 s | −0.570 to −0.274 | WITHIN | WITHIN | −18 to −9 µs |
| 30–60 s | −0.658 to −0.423 | WITHIN | WITHIN | −19 to −12 µs |
| 60–90 s | −0.667 to −0.491 | WITHIN | WITHIN | −20 to −15 µs |
| 90–120 s | −0.464 to −0.270 | WITHIN | WITHIN | −14 to −8 µs |
| 120–150 s | −0.646 to −0.403 | WITHIN | WITHIN | −20 to −13 µs |
| 150–180 s | −0.726 to −0.459 | WITHIN | WITHIN | −21 to −13 µs |
| 180–210 s | −0.681 to −0.461 | WITHIN | WITHIN | −20 to −13 µs |
| 210–240 s | −0.646 to −0.463 | WITHIN | WITHIN | −19 to −14 µs |
| 240–270 s | −0.569 to −0.391 | WITHIN | WITHIN | −17 to −12 µs |
| 270–300 s | −0.697 to −0.502 | WITHIN | WITHIN | −21 to −15 µs |
| Full 300 s | **−0.535 to −0.511** | WITHIN | WITHIN | −160 to −153 µs |

No backward REALTIME reads, no adjacent change above 500 ms, no cumulative window change above the band.

| Snapshot | Uptime | `tick` | `freq` | `freq` in ppm | `status` | Return | `timedatectl NTPSynchronized` |
|---|---:|---:|---:|---:|---:|---|---|
| PRE | ≈19 s | 10000 | 0 | 0 | 64 (STA_UNSYNC) | TIME_ERROR | no |
| POST | ≈380 s | 10000 | −37221 | −0.568 | 0 | TIME_OK | yes |

chrony was running with `-x`, which disables its control of the system clock, yet the kernel's synchronized flag was set and `freq` was trimmed by −0.57 ppm during the run. Some writer other than chrony therefore touched the kernel state on 26.04 as well; it was gentle and consistent with the measured −0.5 ppm rate, and it is not identified here.

This matches the earlier, separately reported 300 s screen on this distro (full run −0.5045 to −0.4637 ppm, worst window bound −1.19 ppm; see [Ubuntu 26.04 findings](findings-ubuntu-26.04.md)).

## Kernel-state time series from boot

On a further fresh boot of each distro, `wsl-time-sync settle-check --duration 150 --cadence 0.2` read `adjtimex(modes=0)` 751 times, starting about 3.5 s after boot, while a 150 s probe ran alongside it.

**Ubuntu 24.04 (timesyncd active).** `tick` was 10000 for the first 53 s and the probe read within ±0.4 ppm for its first five 10 s windows. From 53 s on, `tick` changed every 8 s:

| Elapsed since ≈3.5 s uptime | `tick` | Static rate term |
|---:|---:|---:|
| 0 s | 10000 | 0 |
| 53.0 s | 9167 | −83,330 ppm |
| 69.0 s | 9848 | −15,200 ppm |
| 77.0 s | 9992 | −800 ppm |
| 85.0 s | 9167 | −83,330 ppm |
| 100.0 s | 10000 | 0 |
| 101.0 s | 9828 | −17,200 ppm |
| 109.2 s | 10013 | +1,300 ppm |
| 117.2 s | 9167 | −83,330 ppm |
| 132.2 s | 10000 | 0 |
| 133.2 s | 9539 | −46,100 ppm |
| 141.2 s | 10094 | +9,400 ppm |
| 149.2 s | 9167 | −83,330 ppm |

`tick` was 9167 in 235 of the 751 reads and 10000 in 275; `freq` moved between −33.3 and +44.4 ppm; `status` stayed 8192 (STA_NANO) throughout. The concurrent probe read −59,326 ppm for 50–60 s, −83,333 ppm for 60–70 s and 90–100 s, and between −2,585 and −82,292 ppm otherwise, with forward REALTIME jumps of +1.55 s, +1.53 s and +1.75 s at 78, 112 and 146 s. Each jump came a few seconds after `tick` had returned to about 10000, and each was followed within about 8 s by `tick` dropping to 9167 again. The classification was ANOMALY_OBSERVED with 476 anomalous reads.

**Ubuntu 26.04 (chrony `-x`).** `tick` was 10000 in all 751 reads, `status` was 64 (STA_UNSYNC) for the first 103 reads (about 20 s) and 0 afterwards, `freq` moved between −36.9 and +4.9 ppm, and the concurrent probe stayed within −5.6 to +1.2 ppm in every 10 s window with no jumps. The classification was WITHIN_CONFIGURED_BAND.

Reading the two together: on 24.04 the pathology begins about a minute after boot, `tick` is driven in an 8 s cycle that spends half its time clamped at 9167, and timesyncd's 32 s poll jumps the clock forward each time it finds it more than 0.4 s behind. On 26.04 nothing drives `tick` and nothing jumps.

## Interpretation

**PROJECT OBSERVATION.** On this host, on this day, the Ubuntu 24.04 default (timesyncd active alongside Hyper-V implicit sync) produced a guest clock that ran about 4.8 % slow on average with REALTIME jumped forward by about 1.6 s every 34 s, starting within the first 90 s of boot, on three fresh boots in a row. The Ubuntu 26.04 default on the same host produced a guest clock within ±0.73 ppm for the whole screen with no jumps.

**VENDOR / DOCUMENTED FACT.** systemd v255's timesyncd jumps the clock with `ADJ_SETOFFSET` when it measures an offset of 0.4 s or more, polls every 32 s here, and never uses `ADJ_TICK`. Canonical documents that guest NTP and Hyper-V synchronization can disagree under WSL. WSL boots the kernel with `hv_utils.timesync_implicit=1`.

**INFERENCE.** The observations fit a two-reference conflict: the Windows host clock was about 1.06 s behind NTP; timesyncd repeatedly set the guest to NTP time; an unidentified writer then drove the guest clock back toward host time by lowering `tick`, at up to −83,333 ppm, until the next timesyncd poll found the clock behind again and jumped it forward. With no NTP client stepping the clock, 26.04 followed a single reference and stayed near nominal. The ±83,333 ppm magnitude is the same as the static `tick` term in D4R2 (10833, +1/12) with the opposite sign, which suggests the same kind of writer, not that the two episodes had the same cause.

**NOT ESTABLISHED.** Which process or driver changes `tick` (9437 and 9969 here, 10833 in D4R2): timesyncd is excluded by its source, chrony was not running, and observing the writer would need privileged tracing that this project does not perform. Whether the behaviour appears on a host whose clock agrees with NTP or whose Windows Time service is running: the obvious next experiment is to correct the host clock and repeat, but changing host time services is outside this project's read-only tooling. Whether other 24.04 installs behave the same way. Any host-referenced accuracy for either distro, and any ranking of the two distributions.

## Relationship to the historical record

D4R2 measured the 24.04 clock *after* timesyncd was stopped and found +26,665 to +26,725 ppm in the first window against Windows QPC, decaying to nominal, with `tick` 10833 before and 10000 after. This page measured the enabled state on a different machine, two years later, against the guest's own raw clock, and found the opposite sign at a comparable magnitude with `tick` 9437. Both records show large `tick` changes by an unidentified writer while the documented two-writer default was in place; neither proves that timesyncd was that writer.

## Files and provenance

All files are in [`evidence/2026-09-24-same-host-screens/`](../evidence/2026-09-24-same-host-screens/). `probe*.json`, `analysis*.json`, `settle*.json` and `tick-series-compact.json` are byte-for-byte as produced. In `diagnose*.json` the `boot_id` and `python_executable` fields were replaced with a redaction marker, and in the `.log` files the hostname, boot identifiers and local paths were replaced; the SHA-256 of each unredacted file is listed in the folder's `HASHES.md`. The scripts that produced the runs are reproduced verbatim in `PROTOCOL.md` in the same folder.

## What this page does not claim

- That every Ubuntu 24.04 installation under WSL behaves this way, or that any 26.04 installation is timing-safe.
- That `systemd-timesyncd` is the root cause: it is one of two writers whose behaviour is documented, and the other writer is not identified.
- That the D4R2 episode had the same mechanism.
- Any host-referenced accuracy: both screens compare guest clocks only.
- That Python version plays any role: the interpreter differed between the two guests only because each distro ships a different default.
