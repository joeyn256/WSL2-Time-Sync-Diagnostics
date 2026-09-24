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
    # The guard only bounds waiting; it never supplies the acquisition reference.
    # Ten percent (at least one second) permits ordinary clock-rate differences
    # and scheduling delay, while a stopped RAW clock cannot keep us waiting.
    guard_budget_ns = duration_ns + max(1_000_000_000, duration_ns // 10)
    guard_deadline = started_perf + guard_budget_ns
    max_wait_iterations = 64
    samples: list[dict[str, Any]] = []
    collection_errors: list[str] = []
    origin_raw_ns: int | None = None
    last_raw_ns: int | None = None

    for index in range(planned_count):
        target_ns = None if origin_raw_ns is None else origin_raw_ns + min(index * cadence_ns, duration_ns)
        if index:
            for _ in range(max_wait_iterations):
                remaining_guard_ns = guard_deadline - time.perf_counter_ns()
                if remaining_guard_ns <= 0:
                    collection_errors.append("observation_guard_exhausted")
                    break
                errors: dict[str, str] = {}
                current_raw_ns = _read_clock("CLOCK_MONOTONIC_RAW", errors, "schedule_raw_ns")
                if current_raw_ns is None:
                    collection_errors.append("schedule_raw_unavailable: " + errors["schedule_raw_ns"])
                    break
                if last_raw_ns is not None and current_raw_ns < last_raw_ns:
                    collection_errors.append("schedule_raw_regressed")
                    break
                last_raw_ns = current_raw_ns
                remaining_raw_ns = target_ns - current_raw_ns
                if remaining_raw_ns <= 0:
                    break
                time.sleep(min(remaining_raw_ns, remaining_guard_ns) / 1_000_000_000)
            else:
                collection_errors.append("raw_target_wait_limit_exhausted")
            if collection_errors:
                break

        sample = capture_sample(index)
        sample["observation_elapsed_ns"] = time.perf_counter_ns() - started_perf
        before, after = sample.get("raw_before_ns"), sample.get("raw_after_ns")
        valid_raw = before is not None and after is not None and after >= before
        if index == 0 and valid_raw:
            origin_raw_ns = before
            target_ns = before
        sample["target_raw_ns"] = target_ns
        sample["schedule_lateness_ns"] = before - target_ns if before is not None and target_ns is not None else None
        samples.append(sample)
        if not valid_raw:
            collection_errors.append("sample_raw_unavailable_or_reversed")
        elif last_raw_ns is not None and before < last_raw_ns:
            collection_errors.append("sample_raw_regressed")
        elif target_ns is None or before < target_ns:
            collection_errors.append("sample_raw_target_not_reached")
        elif index + 1 < planned_count and after >= origin_raw_ns + min((index + 1) * cadence_ns, duration_ns):
            # A missed grid point cannot be repaired by a burst of catch-up reads.
            collection_errors.append("sample_raw_next_target_missed")
        if sample["observation_elapsed_ns"] > guard_budget_ns:
            collection_errors.append("observation_guard_exhausted")
        if collection_errors:
            break
        last_raw_ns = after

    elapsed_ns = time.perf_counter_ns() - started_perf
    if elapsed_ns > guard_budget_ns and "observation_guard_exhausted" not in collection_errors:
        collection_errors.append("observation_guard_exhausted")
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
        "schedule": {
            "method": "raw_origin_v1",
            "clock": "CLOCK_MONOTONIC_RAW",
            "origin_raw_ns": origin_raw_ns,
            "duration_ns": duration_ns,
            "cadence_ns": cadence_ns,
            "guard_clock": "perf_counter_ns",
            "guard_budget_ns": guard_budget_ns,
            "max_wait_iterations_per_target": max_wait_iterations,
        },
        "collection_complete": len(samples) == planned_count and not collection_errors,
        "collection_errors": collection_errors,
        "samples": samples,
        "notes": [
            "Guest-side probe only; RAW brackets bound acquisition skew, not clock accuracy.",
            "No Windows QPC or external time reference is collected.",
            "Missing clocks are null with an explicit error; no reference is substituted.",
            "RAW target waits have finite observation-clock and iteration guards; failure leaves collection incomplete.",
            "No service mutation, elevation, or package installation occurs.",
        ],
    }
