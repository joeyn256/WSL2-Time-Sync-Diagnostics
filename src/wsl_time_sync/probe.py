from __future__ import annotations

import time
from typing import Any

from .validation import positive_seconds


def _read_clock(name: str, errors: dict[str, str], field: str) -> int | None:
    clock_id = getattr(time, name, None)
    if clock_id is None or not hasattr(time, "clock_gettime_ns"):
        errors[field] = f"{name} unavailable"
        return None
    try:
        return time.clock_gettime_ns(clock_id)
    except (OSError, ValueError) as exc:
        errors[field] = f"{type(exc).__name__}: {exc}"
        return None


def capture_sample(index: int) -> dict[str, Any]:
    """Read guest clocks inside a RAW bracket; never substitute another reference."""
    errors: dict[str, str] = {}
    before = _read_clock("CLOCK_MONOTONIC_RAW", errors, "raw_before_ns")
    realtime = _read_clock("CLOCK_REALTIME", errors, "realtime_ns")
    monotonic = _read_clock("CLOCK_MONOTONIC", errors, "monotonic_ns")
    boottime = _read_clock("CLOCK_BOOTTIME", errors, "boottime_ns")
    after = _read_clock("CLOCK_MONOTONIC_RAW", errors, "raw_after_ns")
    width = after - before if before is not None and after is not None else None
    if width is not None and width < 0:
        errors["bracket_width_ns"] = "RAW bracket reversed"
    return {
        "index": index,
        "realtime_ns": realtime,
        "monotonic_ns": monotonic,
        "boottime_ns": boottime,
        "raw_before_ns": before,
        "raw_after_ns": after,
        "bracket_width_ns": width,
        "errors": errors,
    }


def run_probe(duration_s: float = 30.0, cadence_s: float = 1.0) -> dict[str, Any]:
    duration_ns = positive_seconds(duration_s, "duration_s")
    cadence_ns = positive_seconds(cadence_s, "cadence_s")
    if duration_ns > 86_400_000_000_000:
        raise ValueError("duration_s must be <= 86400")
    planned_count = (duration_ns + cadence_ns - 1) // cadence_ns + 1
    if planned_count > 100_000:
        raise ValueError("at most 100000 observations may be requested")
    started_wall = time.time_ns()
    started_perf = time.perf_counter_ns()
    deadline = started_perf + duration_ns
    samples: list[dict[str, Any]] = []

    for index in range(planned_count):
        # Include a final observation at the deadline, even when cadence > duration.
        target_ns = min(started_perf + index * cadence_ns, deadline)
        remaining_ns = target_ns - time.perf_counter_ns()
        if remaining_ns > 0:
            time.sleep(remaining_ns / 1_000_000_000)
        samples.append(capture_sample(index))
        elapsed_ns = time.perf_counter_ns() - started_perf
        if elapsed_ns >= duration_ns:
            break

    return {
        "schema_version": 2,
        "mode": "read_only",
        "acquisition": "raw_bracket_v1",
        "reference": "CLOCK_MONOTONIC_RAW",
        "clock_pair": "CLOCK_MONOTONIC/CLOCK_MONOTONIC_RAW",
        "continuity_label": None,
        "duration_requested_s": duration_s,
        "cadence_requested_s": cadence_s,
        "started_wall_ns": started_wall,
        "elapsed_observation_ns": elapsed_ns,
        "observation_clock": "perf_counter_ns",
        "observations_planned": planned_count,
        "collection_complete": len(samples) == planned_count,
        "samples": samples,
        "notes": [
            "Guest-side probe only; RAW brackets bound acquisition skew, not clock accuracy.",
            "No Windows QPC or external time reference is collected.",
            "Missing clocks are null with an explicit error; no reference is substituted.",
            "No service mutation, elevation, package installation, or retry occurs.",
        ],
    }
