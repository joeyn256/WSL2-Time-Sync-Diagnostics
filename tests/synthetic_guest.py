"""Parametric synthetic shapes: newly authored, with no historical evidence bytes.

Names describe qualitative failure shapes only. They do not reproduce a historical
measurement, establish a service cause, or change C1's INCONCLUSIVE result.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

NS = 1_000_000_000


def trace(*, duration_s: int = 30, cadence_s: int = 1, bracket_width_ns: int = 2_000,
          rate_segments: tuple[tuple[int, int], ...] = ((0, 0),),
          realtime_steps: tuple[tuple[int, int], ...] = (),
          common_mode_ppm: int = 0) -> dict[str, Any]:
    """Build clocks algebraically; segment times and steps are synthetic seconds."""
    samples = []
    seconds = list(range(0, duration_s + 1, cadence_s))
    if seconds[-1] != duration_s:
        seconds.append(duration_s)
    for index, second in enumerate(seconds):
        raw = second * (NS + common_mode_ppm * 1_000)
        relative_offset = Fraction(0)
        for segment, (start, ppm) in enumerate(rate_segments):
            end = rate_segments[segment + 1][0] if segment + 1 < len(rate_segments) else second
            span = max(0, min(second, end) - start)
            relative_offset += Fraction(span * (NS + common_mode_ppm * 1_000) * ppm, 1_000_000)
        midpoint = raw + bracket_width_ns // 2
        mono = midpoint + int(relative_offset)
        realtime_offset = sum(size for when, size in realtime_steps if second >= when)
        samples.append({"index": index, "raw_before_ns": raw,
                        "raw_after_ns": raw + bracket_width_ns,
                        "bracket_width_ns": bracket_width_ns,
                        "monotonic_ns": mono, "realtime_ns": mono + realtime_offset,
                        "boottime_ns": mono, "errors": {}})
    duration_ns, cadence_ns = duration_s * NS, cadence_s * NS
    for row in samples:
        row["target_raw_ns"] = min(row["index"] * cadence_ns, duration_ns)
        row["schedule_lateness_ns"] = row["raw_before_ns"] - row["target_raw_ns"]
        row["observation_elapsed_ns"] = row["raw_after_ns"]
    return {"schema_version": 2, "acquisition": "raw_bracket_v1",
            "reference": "CLOCK_MONOTONIC_RAW",
            "clock_pair": "CLOCK_MONOTONIC/CLOCK_MONOTONIC_RAW",
            "duration_requested_s": duration_s, "cadence_requested_s": cadence_s,
            "continuity_label": "synthetic_uninterrupted", "samples": samples,
            "collection_complete": True, "collection_errors": [],
            "observations_planned": (duration_ns + cadence_ns - 1) // cadence_ns + 1,
            "observation_clock": "perf_counter_ns",
            "elapsed_observation_ns": samples[-1]["observation_elapsed_ns"],
            "schedule": {"method": "raw_origin_v1", "clock": "CLOCK_MONOTONIC_RAW",
                         "origin_raw_ns": samples[0]["raw_before_ns"],
                         "duration_ns": duration_ns, "cadence_ns": cadence_ns,
                         "guard_clock": "perf_counter_ns",
                         "guard_budget_ns": duration_ns + max(NS, duration_ns // 10),
                         "max_wait_iterations_per_target": 64}}


def early_slew(*, early_ppm: int = 1_000, early_s: int = 10,
               duration_s: int = 200) -> dict[str, Any]:
    return trace(duration_s=duration_s, rate_segments=((0, early_ppm), (early_s, 0)))


def sawtooth(*, period_s: int = 5, increment_ns: int = 150_000_000,
             duration_s: int = 30) -> dict[str, Any]:
    payload = trace(duration_s=duration_s)
    for row in payload["samples"]:
        offset = (row["index"] % period_s) * increment_ns
        row["realtime_ns"] += offset
        row["monotonic_ns"] += offset
    return payload


def missing_sample(*, position: int = 5, remove: bool = False) -> dict[str, Any]:
    payload = trace()
    if remove:
        del payload["samples"][position]
    else:
        payload["samples"][position]["monotonic_ns"] = None
        payload["samples"][position]["errors"] = {"monotonic_ns": "synthetic unavailable"}
    return payload


def duplicate_sample(*, position: int = 5) -> dict[str, Any]:
    payload = trace()
    payload["samples"].insert(position, dict(payload["samples"][position - 1]))
    return payload
