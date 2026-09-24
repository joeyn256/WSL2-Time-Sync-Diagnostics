from __future__ import annotations

import time
from typing import Any


def _clock_id(name: str) -> int | None:
    return getattr(time, name, None)


def capture_sample(index: int) -> dict[str, int]:
    sample = {
        "index": index,
        "realtime_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "perf_counter_ns": time.perf_counter_ns(),
    }
    raw_id = _clock_id("CLOCK_MONOTONIC_RAW")
    if raw_id is not None:
        sample["monotonic_raw_ns"] = time.clock_gettime_ns(raw_id)
    boot_id = _clock_id("CLOCK_BOOTTIME")
    if boot_id is not None:
        sample["boottime_ns"] = time.clock_gettime_ns(boot_id)
    return sample


def run_probe(duration_s: float = 30.0, cadence_s: float = 1.0) -> dict[str, Any]:
    if duration_s <= 0:
        raise ValueError("duration_s must be > 0")
    if cadence_s <= 0:
        raise ValueError("cadence_s must be > 0")

    started_wall = time.time_ns()
    started_perf = time.perf_counter_ns()
    samples: list[dict[str, int]] = []
    index = 0

    while True:
        target_ns = started_perf + int(index * cadence_s * 1_000_000_000)
        now_ns = time.perf_counter_ns()
        if now_ns < target_ns:
            time.sleep((target_ns - now_ns) / 1_000_000_000)

        samples.append(capture_sample(index))

        elapsed_ns = time.perf_counter_ns() - started_perf
        if elapsed_ns >= int(duration_s * 1_000_000_000):
            break
        index += 1

    return {
        "schema_version": 1,
        "mode": "read_only",
        "duration_requested_s": duration_s,
        "cadence_requested_s": cadence_s,
        "started_wall_ns": started_wall,
        "samples": samples,
        "notes": [
            "Guest-side probe only.",
            "No Windows QPC or external time reference is collected.",
            "No service mutation, elevation, package installation, or retry occurs.",
        ],
    }
