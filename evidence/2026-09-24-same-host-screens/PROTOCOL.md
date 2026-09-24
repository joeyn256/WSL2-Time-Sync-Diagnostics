# Protocol scripts (verbatim)

These are the exact scripts that produced the committed files. Paths under the scratchpad were local to the reviewing machine. Every guest-side command is read-only: no service, package or elevation change.

## screen.sh

```
#!/bin/bash
# Read-only guest-side timing screen. Usage: screen.sh <tag> <venv-name>
# Performs no service mutation, no package installation into the system, no elevation.
set -u
SP=<scratchpad>
TAG="$1"; VENV="$SP/$2"; OUT="$SP/evidence/$TAG"
mkdir -p "$OUT"
PY="$VENV/bin/python"; CLI="$VENV/bin/wsl-time-sync"
{
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) start ==="
echo "repo_rev=$(cd "$SP/rc" && git rev-parse HEAD)"
"$PY" -m pip install --quiet -e "$SP/rc" || echo "pip install failed"
echo "cli_version=$("$PY" -c 'import wsl_time_sync; print(wsl_time_sync.__version__)')"
echo "python=$("$PY" --version 2>&1)"
echo "uname=$(uname -r)"
echo "pretty_name=$(. /etc/os-release; echo "$PRETTY_NAME")"
echo "cmdline=$(cat /proc/cmdline)"
echo "clocksource=$(cat /sys/devices/system/clocksource/clocksource0/current_clocksource)"
echo "uptime_s=$(cut -d' ' -f1 /proc/uptime)"
echo "timesyncd_active=$(systemctl is-active systemd-timesyncd 2>&1) enabled=$(systemctl is-enabled systemd-timesyncd 2>&1)"
echo "chrony_active=$(systemctl is-active chrony 2>&1) enabled=$(systemctl is-enabled chrony 2>&1)"
echo "chronyd_args=$(ps -o args= -C chronyd 2>/dev/null | tr '\n' ' ')"
echo "timesyncd_args=$(ps -o args= -C systemd-timesyncd 2>/dev/null | tr '\n' ' ')"
echo "ptp=$(ls /dev/ptp* 2>/dev/null | tr '\n' ' ')"
echo "--- timedatectl show (pre) ---"; timedatectl show 2>&1
echo "--- timedatectl timesync-status (pre, read-only property query) ---"; timedatectl show-timesync 2>&1 | head -20
echo "=== diagnose PRE $(date -u +%H:%M:%SZ) ==="
"$CLI" diagnose --output "$OUT/diagnose-pre.json" >/dev/null && echo "ok"
echo "=== settle 60 s ==="; sleep 60
echo "=== probe 300 s / 1 s $(date -u +%H:%M:%SZ) ==="
"$CLI" probe --duration 300 --cadence 1 --output "$OUT/probe.json" >/dev/null && echo "ok"
echo "=== diagnose POST $(date -u +%H:%M:%SZ) ==="
"$CLI" diagnose --output "$OUT/diagnose-post.json" >/dev/null && echo "ok"
echo "--- timedatectl show (post) ---"; timedatectl show 2>&1
echo "=== analyze ==="
"$CLI" analyze "$OUT/probe.json" --window 30 --rate-band-ppm 1000 --output "$OUT/analysis-window30-band1000.json" >/dev/null && echo "ok band1000"
"$CLI" analyze "$OUT/probe.json" --window 30 --output "$OUT/analysis-window30-band100.json" >/dev/null && echo "ok band100"
"$PY" - "$OUT" <<'PY'
import json, sys, hashlib, pathlib
out = pathlib.Path(sys.argv[1])
p = json.load(open(out / "probe.json")); a = json.load(open(out / "analysis-window30-band1000.json")); b = json.load(open(out / "analysis-window30-band100.json"))
pre = json.load(open(out / "diagnose-pre.json")); post = json.load(open(out / "diagnose-post.json"))
print("probe complete:", p["collection_complete"], p["collection_errors"], "samples", len(p["samples"]))
c = a["coverage"]
print("coverage: verified", c["collection_completion_verified"], "windows", c["window_count"], "complete", c["complete_window_count"], "partial", c["partial_window_count"], "issues", c["issues"])
print("classification band1000:", a["classification"], "| band100:", b["classification"])
print("full_run rate_interval_ppm:", a["full_run"]["rate_interval_ppm"], "point", a["full_run"]["monotonic_vs_raw_ppm"])
print("full_run realtime offset change ns:", a["full_run"]["realtime_offset_change_interval_ns"], a["full_run"]["realtime_offset_direction"])
for w in a["windows"]:
    print("window", w["window_index"], w["classification"], w["rate_interval_ppm"], "rt", w["realtime_offset_classification"], w["realtime_offset_change_interval_ns"])
print("backward events:", a["realtime_backward_events"], "large changes:", a["large_realtime_minus_raw_changes"], "outside rt windows:", a["outside_realtime_offset_windows"])
for name, d in (("PRE", pre), ("POST", post)):
    adj = d["adjtimex"]
    raw = adj.get("raw", {})
    print(name, "adjtimex available", adj.get("available"), "tick", raw.get("tick"), "freq", raw.get("freq"), "freq_ppm", adj.get("freq_ppm"), "status", raw.get("status"), "return_state", adj.get("return_state"))
    print(name, "services", [(s["unit"], s["active"], s["enabled"]) for s in d["services"]], "clocksource", d["clocksource"], "ptp", [x["clock_name"] for x in d["ptp"]])
for f in ("diagnose-pre.json", "probe.json", "diagnose-post.json", "analysis-window30-band1000.json", "analysis-window30-band100.json"):
    print("sha256", f, hashlib.sha256((out / f).read_bytes()).hexdigest())
PY
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) end ==="
} 2>&1 | tee "$OUT/run.log"
```

## followup.sh

```
#!/bin/bash
# Read-only follow-up diagnostics while the distro is still up. Usage: followup.sh <tag> <venv-name>
set -u
SP=<scratchpad>
TAG="$1"; VENV="$SP/$2"; OUT="$SP/evidence/$TAG"
PY="$VENV/bin/python"; CLI="$VENV/bin/wsl-time-sync"
{
echo "=== followup $(date -u +%Y-%m-%dT%H:%M:%SZ) uptime_s=$(cut -d' ' -f1 /proc/uptime) ==="
echo "--- timedatectl show-timesync ---"; timedatectl show-timesync 2>&1 | grep -v -E '^NTPMessage' ; timedatectl show-timesync 2>&1 | grep -E '^NTPMessage' | cut -c1-400
echo "--- systemd version ---"; systemctl --version | head -1
echo "--- running services ---"; systemctl list-units --type=service --state=running --no-pager --no-legend 2>&1 | awk '{print $1}'
echo "--- timesyncd journal (read-only) ---"; journalctl -u systemd-timesyncd --no-pager -o short-precise 2>&1 | tail -n 40
echo "--- kernel journal: time-related lines ---"; journalctl -k --no-pager 2>&1 | grep -i -E 'hv_utils|timesync|clocksource|tsc|ptp|hyperv|time' | tail -n 40
echo "--- independent two-clock check over 20 s (python, no CLI) ---"
"$PY" - <<'PY'
import time
r0 = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW); m0 = time.clock_gettime_ns(time.CLOCK_MONOTONIC); w0 = time.clock_gettime_ns(time.CLOCK_REALTIME); b0 = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
time.sleep(20)
r1 = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW); m1 = time.clock_gettime_ns(time.CLOCK_MONOTONIC); w1 = time.clock_gettime_ns(time.CLOCK_REALTIME); b1 = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
dr, dm, dw, db = r1 - r0, m1 - m0, w1 - w0, b1 - b0
print(f"RAW elapsed {dr/1e9:.6f} s | MONOTONIC {dm/1e9:.6f} s | REALTIME {dw/1e9:.6f} s | BOOTTIME {db/1e9:.6f} s")
print(f"MONOTONIC vs RAW: {(dm/dr - 1)*1e6:+.1f} ppm | REALTIME vs RAW: {(dw/dr - 1)*1e6:+.1f} ppm | BOOTTIME vs RAW: {(db/dr - 1)*1e6:+.1f} ppm")
PY
echo "--- adjtimex now ---"
"$CLI" diagnose --output "$OUT/diagnose-followup.json" >/dev/null && "$PY" -c "import json; d=json.load(open('$OUT/diagnose-followup.json'))['adjtimex']; print('tick', d['raw']['tick'], 'freq', d['raw']['freq'], 'freq_ppm', d['freq_ppm'], 'status', d['raw']['status'], 'offset', d['raw'].get('offset'), 'maxerror', d['raw'].get('maxerror'), 'esterror', d['raw'].get('esterror'))"
echo "--- second probe 60 s ---"
"$CLI" probe --duration 60 --cadence 1 --output "$OUT/probe-followup-60s.json" >/dev/null
"$CLI" analyze "$OUT/probe-followup-60s.json" --window 30 --rate-band-ppm 1000 --output "$OUT/analysis-followup-60s.json" >/dev/null
"$PY" - "$OUT" <<'PY'
import json, sys
a = json.load(open(sys.argv[1] + "/analysis-followup-60s.json"))
print("followup 60 s:", a["classification"], "full", a["full_run"]["rate_interval_ppm"], [(w["classification"], [round(x, 1) for x in w["rate_interval_ppm"]], w["realtime_offset_change_interval_ns"]) for w in a["windows"]])
PY
echo "--- adjtimex after ---"
"$CLI" diagnose --output "$OUT/diagnose-followup2.json" >/dev/null && "$PY" -c "import json; d=json.load(open('$OUT/diagnose-followup2.json'))['adjtimex']; print('tick', d['raw']['tick'], 'freq', d['raw']['freq'], 'freq_ppm', d['freq_ppm'], 'status', d['raw']['status'])"
echo "=== end $(date -u +%H:%M:%SZ) ==="
} 2>&1 | tee "$OUT/followup.log"
```

## offline_2404.sh

```
#!/bin/bash
set -u
SP=<scratchpad>
OUT="$SP/evidence/ubuntu-24.04-timesyncd-enabled"
CLI="$SP/venv2404/bin/wsl-time-sync"; PY="$SP/venv2404/bin/python"
"$CLI" analyze "$OUT/probe.json" --window 5 --rate-band-ppm 1000 --output "$OUT/analysis-window5-band1000.json" >/dev/null && echo "ok window5"
"$CLI" analyze "$OUT/probe.json" --window 10 --rate-band-ppm 1000 --output "$OUT/analysis-window10-band1000.json" >/dev/null && echo "ok window10"
"$PY" - "$OUT" <<'PY'
import json, sys
out = sys.argv[1]
a5 = json.load(open(out + "/analysis-window5-band1000.json"))
print("5 s windows (index: lo..hi ppm, class):")
for w in a5["windows"]:
    lo, hi = w["rate_interval_ppm"]; print(f"  {w['window_index']*5:3d}-{(w['window_index']+1)*5:3d} s  {lo:+10.1f} .. {hi:+10.1f}  {w['classification']}")
a30 = json.load(open(out + "/analysis-window30-band1000.json"))
print("large adjacent REALTIME-RAW events (>0.5 s):")
for e in a30["realtime_events"]:
    if e["classification"] == "OUTSIDE":
        iv = e["offset_change_interval_ns"]; print(f"  samples {e['first_index']}->{e['last_index']} (t≈{e['first_index']} s): {iv[0]/1e9:+.3f} .. {iv[1]/1e9:+.3f} s {e['direction']}")
p = json.load(open(out + "/probe.json"))
print("probe started_wall_ns:", p["started_wall_ns"], "elapsed_observation_ns:", p["elapsed_observation_ns"])
s0, sN = p["samples"][0], p["samples"][-1]
print("RAW span s:", (sN["raw_before_ns"] - s0["raw_before_ns"]) / 1e9, "MONO span s:", (sN["monotonic_ns"] - s0["monotonic_ns"]) / 1e9, "REALTIME span s:", (sN["realtime_ns"] - s0["realtime_ns"]) / 1e9, "BOOTTIME span s:", (sN["boottime_ns"] - s0["boottime_ns"]) / 1e9)
print("first sample monotonic_ns (≈uptime at probe start):", s0["monotonic_ns"] / 1e9, "s; boottime:", s0["boottime_ns"] / 1e9, "s")
PY
```

## tickseries.sh

```
#!/bin/bash
# Read-only kernel-state time series from a fresh boot. Usage: tickseries.sh <tag> <venv-name>
# Uses the project's settle-check (repeated adjtimex(modes=0) reads) at 0.2 s cadence for 150 s.
set -u
SP=<scratchpad>
TAG="$1"; VENV="$SP/$2"; OUT="$SP/evidence/$TAG"
mkdir -p "$OUT"
PY="$VENV/bin/python"; CLI="$VENV/bin/wsl-time-sync"
{
echo "=== tickseries $(date -u +%Y-%m-%dT%H:%M:%SZ) uptime_s=$(cut -d' ' -f1 /proc/uptime) pretty=$(. /etc/os-release; echo "$PRETTY_NAME") ==="
echo "timesyncd_active=$(systemctl is-active systemd-timesyncd 2>&1) chrony_active=$(systemctl is-active chrony 2>&1) chronyd_args=$(ps -o args= -C chronyd 2>/dev/null | head -1)"
echo "--- /etc/wsl.conf ---"; cat /etc/wsl.conf 2>/dev/null || echo "(none)"
"$CLI" probe --duration 150 --cadence 1 --output "$OUT/probe-150s.json" >/dev/null &
PROBE_PID=$!
"$CLI" settle-check --duration 150 --cadence 0.2 --output "$OUT/settle-150s-0.2s.json" >/dev/null && echo "settle ok"
wait "$PROBE_PID" && echo "probe ok"
"$CLI" analyze "$OUT/probe-150s.json" --window 10 --rate-band-ppm 1000 --output "$OUT/analysis-150s-window10.json" >/dev/null && echo "analyze ok"
"$PY" - "$OUT" <<'PY'
import json, sys
a = json.load(open(sys.argv[1] + "/analysis-150s-window10.json"))
print("150 s probe:", a["classification"], "full", [round(x, 1) for x in a["full_run"]["rate_interval_ppm"]])
for w in a["windows"]:
    lo, hi = w["rate_interval_ppm"]; r = w["realtime_offset_change_interval_ns"]
    print(f"  {w['window_index']*10:3d}-{(w['window_index']+1)*10:3d} s {lo:+10.1f}..{hi:+10.1f} ppm  rt {r[0]/1e9:+.3f}..{r[1]/1e9:+.3f} s")
print("large events:", [(e["first_index"], round(e["offset_change_interval_ns"][0]/1e9, 3)) for e in a["realtime_events"] if e["classification"] == "OUTSIDE"])
PY
"$PY" - "$OUT" <<'PY'
import json, sys
out = sys.argv[1]
s = json.load(open(out + "/settle-150s-0.2s.json"))
print("classification:", s["classification"], "collected", s["observations_collected"], "of", s["observations_planned"], "complete", s["complete"], "anomalies", s["anomaly_count"])
rows = []
for o in s["observations"]:
    adj = o["adjtimex"]; raw = adj.get("raw") or {}
    rows.append((o["elapsed_before_ns"] / 1e9, raw.get("tick"), raw.get("freq"), raw.get("offset"), raw.get("status"), raw.get("esterror"), raw.get("maxerror")))
# compact series: print transitions of tick only
prev = None; transitions = []
for t, tick, freq, off, st, est, maxe in rows:
    if tick != prev:
        transitions.append((round(t, 1), tick)); prev = tick
print("tick transitions (elapsed s, tick):", transitions[:80], "... total", len(transitions))
ticks = [r[1] for r in rows if r[1] is not None]
from collections import Counter
print("tick value histogram:", Counter(ticks).most_common(10))
print("freq range:", min(r[2] for r in rows if r[2] is not None), max(r[2] for r in rows if r[2] is not None))
print("status values:", Counter(r[4] for r in rows).most_common(5))
json.dump([{"t": round(r[0], 3), "tick": r[1], "freq": r[2], "offset": r[3], "status": r[4]} for r in rows], open(out + "/tick-series-compact.json", "w"))
print("wrote tick-series-compact.json", len(rows), "rows")
PY
echo "=== end $(date -u +%H:%M:%SZ) uptime_s=$(cut -d' ' -f1 /proc/uptime) ==="
} 2>&1 | tee "$OUT/tickseries.log"
```

## tickchain.ps1

```
$sp = "<scratchpad>"
wsl.exe --shutdown; Start-Sleep -Seconds 8
"=== 24.04 tick series ==="
wsl.exe -d Ubuntu-24.04 -- bash "$sp/tickseries.sh" ubuntu-24.04-timesyncd-enabled venv2404
wsl.exe --shutdown; Start-Sleep -Seconds 8
"=== 26.04 tick series ==="
wsl.exe -d Ubuntu-26.04 -- bash "$sp/tickseries.sh" ubuntu-26.04-fresh-default venv2604
"=== chain done ==="
```
