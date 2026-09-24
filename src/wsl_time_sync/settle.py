"""Finite read-only observation of an explicitly configured kernel-state band."""

from __future__ import annotations

import math
import time
from fractions import Fraction
from typing import Any

from .adjtimex import observe_adjtimex


MAX_OBSERVATIONS = 100_000
MAX_DURATION_S = 86_400.0


def _positive_finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite positive number")
    try:
        valid = math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite positive number")


def _policy(expected_tick: int, max_abs_freq_ppm: float,
            required_consecutive: int) -> dict[str, Any]:
    if type(expected_tick) is not int or expected_tick <= 0:
        raise ValueError("expected_tick must be a positive integer")
    _positive_finite(max_abs_freq_ppm, "max_abs_freq_ppm")
    if type(required_consecutive) is not int or required_consecutive < 2:
        raise ValueError("required_consecutive must be an integer >= 2")
    return {
        "name": ("historical_example_tick10000_freq100ppm"
                 if expected_tick == 10000 and max_abs_freq_ppm == 100.0
                 else "configured_tick_frequency_band"),
        "expected_tick": expected_tick,
        "max_abs_freq_ppm": max_abs_freq_ppm,
        "frequency_comparison": "strict_less_than",
        "required_consecutive": required_consecutive,
        "scope": "Observed tick and freq fields only; no certification or host reference.",
    }


def classify_settle_readings(
    readings: list[dict[str, Any]], *, expected_tick: int = 10000,
    max_abs_freq_ppm: float = 100.0, required_consecutive: int = 3,
) -> dict[str, Any]:
    """Keep every observed anomaly visible, even after later nominal readings.

    Missing/malformed observations prevent a within-band result. An observed
    tick/frequency anomaly takes precedence over unavailable observations.
    """
    policy = _policy(expected_tick, max_abs_freq_ppm, required_consecutive)
    # An exact rational comparison also avoids overflow for large finite bands.
    band = Fraction(str(max_abs_freq_ppm))
    band_numerator, band_denominator = band.numerator, band.denominator
    results = []
    run = longest = 0
    for reading in readings:
        raw = reading.get("raw") if isinstance(reading, dict) else None
        available = (isinstance(reading, dict) and reading.get("available") is True
                     and isinstance(raw, dict))
        has_tick = available and type(raw.get("tick")) is int
        has_freq = available and type(raw.get("freq")) is int
        tick_anomaly = has_tick and raw["tick"] != expected_tick
        freq_anomaly = (has_freq and abs(raw["freq"]) * band_denominator
                        >= band_numerator * 65536)
        if tick_anomaly or freq_anomaly:
            results.append("ANOMALY_OBSERVED")
            run = 0
        elif not (has_tick and has_freq):
            results.append("INDETERMINATE")
            run = 0
        else:
            results.append("WITHIN_CONFIGURED_BAND")
            run += 1
            longest = max(longest, run)
    if "ANOMALY_OBSERVED" in results:
        classification = "ANOMALY_OBSERVED"
        reason = "At least one observed tick/freq value was outside the configured band."
    elif "INDETERMINATE" in results or longest < required_consecutive:
        classification = "INDETERMINATE"
        reason = "Unavailable/malformed readings or too few consecutive within-band readings."
    else:
        classification = "WITHIN_CONFIGURED_BAND"
        reason = "All collected tick/freq values were within the configured band."
    return {
        "classification": classification,
        "reason": reason,
        "policy": policy,
        "reading_classifications": results,
        "longest_consecutive_within": longest,
        "anomaly_count": results.count("ANOMALY_OBSERVED"),
        "indeterminate_count": results.count("INDETERMINATE"),
    }


def run_settle_check(
    duration_s: float = 30.0, cadence_s: float = 1.0, *,
    expected_tick: int = 10000, max_abs_freq_ppm: float = 100.0,
    required_consecutive: int = 3,
) -> dict[str, Any]:
    """Observe for at most one scheduled finite window, without any retry loop.

    The last target is the requested deadline, including when cadence exceeds
    duration. A delayed read can overrun that deadline; its actual timing is
    retained. Duration is limited to one day and at most 100,000 planned reads.
    """
    _positive_finite(duration_s, "duration_s")
    _positive_finite(cadence_s, "cadence_s")
    _policy(expected_tick, max_abs_freq_ppm, required_consecutive)
    if duration_s > MAX_DURATION_S:
        raise ValueError(f"duration_s must be <= {MAX_DURATION_S:g}")
    duration_ns = int(duration_s * 1_000_000_000)
    cadence_ns = int(cadence_s * 1_000_000_000) if cadence_s <= duration_s else duration_ns
    if duration_ns < 1 or cadence_ns < 1:
        raise ValueError("duration_s and cadence_s must be at least one nanosecond")
    planned_count = (duration_ns + cadence_ns - 1) // cadence_ns + 1
    if planned_count > MAX_OBSERVATIONS:
        raise ValueError(f"at most {MAX_OBSERVATIONS} observations may be requested")

    start = time.perf_counter_ns()
    observations = []
    for index in range(planned_count):
        target_ns = min(index * cadence_ns, duration_ns)
        remaining_ns = start + target_ns - time.perf_counter_ns()
        if remaining_ns > 0:
            time.sleep(remaining_ns / 1_000_000_000)
        before_ns = time.perf_counter_ns()
        reading = observe_adjtimex()
        after_ns = time.perf_counter_ns()
        observations.append({
            "index": index, "target_elapsed_ns": target_ns,
            "elapsed_before_ns": before_ns - start,
            "elapsed_after_ns": after_ns - start, "adjtimex": reading,
        })
        if after_ns - start >= duration_ns:
            break
    summary = classify_settle_readings(
        [observation["adjtimex"] for observation in observations],
        expected_tick=expected_tick, max_abs_freq_ppm=max_abs_freq_ppm,
        required_consecutive=required_consecutive,
    )
    complete = len(observations) == planned_count
    if not complete and summary["classification"] != "ANOMALY_OBSERVED":
        summary.update(classification="INDETERMINATE",
                       reason="Observation deadline reached before all scheduled readings.")
    return {
        "schema_version": 2,
        "mode": "read_only",
        "method": "adjtimex_modes0_finite_observation",
        "duration_requested_s": duration_s,
        "cadence_requested_s": cadence_s,
        "elapsed_s": observations[-1]["elapsed_after_ns"] / 1_000_000_000,
        "observations_planned": planned_count,
        "observations_collected": len(observations),
        "complete": complete,
        **summary,
        "observations": observations,
        "notes": [
            "This is a finite observation, not a universal settling or benchmark certification.",
            "The default tick/frequency band is an explicitly named historical example policy.",
            "No snapshot or repeated band match proves a pending slew is absent.",
            "No clock or service state is changed; no Windows-host reference is collected.",
        ],
    }
