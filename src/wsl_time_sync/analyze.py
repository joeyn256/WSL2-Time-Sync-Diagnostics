from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any

from .validation import finite_json_integer

WITHIN = "WITHIN"
OUTSIDE = "OUTSIDE"
INDETERMINATE = "INDETERMINATE"


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _finite(value: Any) -> bool:
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def rate_ppm(delta_clock_ns: int, delta_ref_ns: int) -> float:
    """Legacy descriptive point estimate; this does not provide an uncertainty bound."""
    if delta_ref_ns <= 0:
        raise ValueError("reference delta must be > 0")
    return float(Fraction(delta_clock_ns - delta_ref_ns, delta_ref_ns) * 1_000_000)


def _outward(value: Fraction, *, lower: bool) -> float:
    """Round toward the outside so binary float conversion cannot narrow the interval."""
    rounded = float(value)
    exact_float = Fraction.from_float(rounded)
    if (lower and exact_float > value) or (not lower and exact_float < value):
        return math.nextafter(rounded, -math.inf if lower else math.inf)
    return rounded


def rate_interval_ppm(delta_clock_ns: int, delta_reference_ns: tuple[int, int]) -> list[float] | None:
    """Enclose ppm for a fixed signed clock delta and a positive reference interval."""
    lo, hi = delta_reference_ns
    if not all(_integer(x) for x in (delta_clock_ns, lo, hi)) or lo <= 0 or hi < lo:
        return None
    endpoints = [Fraction(delta_clock_ns - ref, ref) * 1_000_000 for ref in (lo, hi)]
    return [_outward(min(endpoints), lower=True), _outward(max(endpoints), lower=False)]


def classify_interval(interval: list[float] | tuple[float, float] | None, band: float) -> str:
    """Classify the entire interval against the inclusive configured [-band, band]."""
    if not _finite(band) or band < 0:
        raise ValueError("band must be finite and >= 0")
    if interval is None or len(interval) != 2:
        return INDETERMINATE
    lo, hi = interval
    if not _finite(lo) or not _finite(hi) or lo > hi:
        return INDETERMINATE
    if lo >= -band and hi <= band:
        return WITHIN
    if lo > band or hi < -band:
        return OUTSIDE
    return INDETERMINATE


def _classify_rate(delta: int, elapsed: tuple[int, int], band: float) -> str:
    # Interpret user-facing decimal settings as decimals, and classify before
    # the JSON display enclosure is rounded outward to binary floating point.
    threshold = Fraction(str(band))
    endpoints = [(Fraction(delta, ref) - 1) * 1_000_000 for ref in elapsed]
    lo, hi = min(endpoints), max(endpoints)
    if lo >= -threshold and hi <= threshold:
        return WITHIN
    if lo > threshold or hi < -threshold:
        return OUTSIDE
    return INDETERMINATE


def raw_delta_interval(first: dict[str, Any], last: dict[str, Any]) -> tuple[int, int] | None:
    """Elapsed RAW bounds for readings made inside two ordered acquisition brackets."""
    values = [first.get("raw_before_ns"), first.get("raw_after_ns"),
              last.get("raw_before_ns"), last.get("raw_after_ns")]
    if not all(_integer(x) for x in values):
        return None
    start_before, start_after, end_before, end_after = values
    if start_after < start_before or end_after < end_before:
        return None
    lo, hi = end_before - start_after, end_after - start_before
    return (lo, hi) if 0 < lo <= hi else None


def realtime_event(first: dict[str, Any], last: dict[str, Any], threshold_ns: int) -> dict[str, Any]:
    """Enclose signed change in REALTIME minus RAW between two bracketed samples."""
    if not _integer(threshold_ns) or threshold_ns < 0:
        raise ValueError("event threshold must be an integer >= 0")
    interval = None
    elapsed = raw_delta_interval(first, last)
    if elapsed and _integer(first.get("realtime_ns")) and _integer(last.get("realtime_ns")):
        delta = last["realtime_ns"] - first["realtime_ns"]
        interval = [delta - elapsed[1], delta - elapsed[0]]
    direction = "UNRESOLVED"
    if interval is not None:
        if interval[0] > 0:
            direction = "POSITIVE"
        elif interval[1] < 0:
            direction = "NEGATIVE"
    return {"offset_change_interval_ns": interval,
            "classification": classify_interval(interval, threshold_ns), "direction": direction}


def fixed_windows(timestamps_ns: list[int | None], window_ns: int) -> list[dict[str, Any]]:
    """Anchor fixed RAW boundaries; use the first sample at/after each boundary.

    Adjacent windows share endpoints. Sampling does not drift the nominal boundaries.
    Endpoint displacement is exposed; a missing endpoint or a displacement of at
    least one window is incomplete. A final partial window remains in the output.
    """
    if not _integer(window_ns) or window_ns <= 0:
        raise ValueError("window_ns must be a positive integer")
    usable = [(i, value) for i, value in enumerate(timestamps_ns) if _integer(value)]
    if len(usable) < 2:
        return []
    anchor = usable[0][1]
    end = usable[-1][1]
    duration = end - anchor
    if duration <= 0:
        return []
    count = (duration + window_ns - 1) // window_ns
    if count > 100_000:
        raise ValueError("requested window size would produce more than 100000 windows")
    windows = []
    cursor = 0
    for number in range(count):
        nominal_start = anchor + number * window_ns
        nominal_end = nominal_start + window_ns
        while cursor < len(usable) - 1 and usable[cursor][1] < nominal_start:
            cursor += 1
        first_position, first_time = usable[cursor]
        while cursor < len(usable) - 1 and usable[cursor][1] < nominal_end:
            cursor += 1
        last_position, last_time = usable[cursor]
        partial = last_time < nominal_end
        # An overshooting sample may already have closed the preceding full
        # window. Do not invent a trailing window with that same sole endpoint.
        if partial and first_position == last_position and windows:
            break
        covered = (first_position < last_position and
                   0 <= first_time - nominal_start < window_ns and
                   0 <= last_time - nominal_end < window_ns)
        windows.append({"window_index": number, "nominal_start_ns": nominal_start,
                        "nominal_end_ns": nominal_end, "first_position": first_position,
                        "last_position": last_position, "start_displacement_ns": first_time - nominal_start,
                        "end_displacement_ns": last_time - nominal_end,
                        "partial": partial, "boundary_coverage": covered})
    return windows


def _prepare_samples(samples: list[Any], bracketed: bool) -> tuple[list[dict[str, Any]], list[list[str]]]:
    prepared: list[dict[str, Any]] = []
    reasons: list[list[str]] = []
    seen_indices: set[int] = set()
    previous_index = None
    for position, item in enumerate(samples):
        row = dict(item) if isinstance(item, dict) else {}
        issues = []
        for field in ("realtime_ns", "monotonic_ns"):
            if not _integer(row.get(field)):
                issues.append("missing_or_invalid_" + field)
        if bracketed:
            before, after = row.get("raw_before_ns"), row.get("raw_after_ns")
            if not _integer(before) or not _integer(after):
                issues.append("missing_or_invalid_raw_bracket")
            elif after < before:
                issues.append("reversed_raw_bracket")
            elif not _integer(row.get("bracket_width_ns")) or row["bracket_width_ns"] != after - before:
                issues.append("inconsistent_bracket_width")
        else:
            raw = row.get("monotonic_raw_ns")
            if not _integer(raw):
                issues.append("missing_or_invalid_monotonic_raw_ns")
            # These coordinates are useful for descriptive windows only: legacy
            # sequential acquisition has no bounded relation to the other reads.
            row["raw_before_ns"] = raw
            row["raw_after_ns"] = raw
        index = row.get("index")
        if (bracketed or index is not None) and not _integer(index):
            issues.append("invalid_index")
        elif _integer(index):
            if bracketed and index < 0:
                issues.append("invalid_negative_index")
            if index in seen_indices:
                issues.append("duplicate_index")
            if previous_index is not None:
                if index < previous_index:
                    issues.append("decreasing_index")
                elif index > previous_index + 1:
                    issues.append("missing_sample_index")
            previous_index = index
            seen_indices.add(index)
        if prepared:
            previous = prepared[-1]
            raw_values = (previous.get("raw_before_ns"), previous.get("raw_after_ns"),
                          row.get("raw_before_ns"), row.get("raw_after_ns"))
            if all(_integer(x) for x in raw_values):
                if row["raw_before_ns"] <= previous["raw_before_ns"]:
                    issues.append("nonincreasing_raw")
                elif row["raw_before_ns"] <= previous["raw_after_ns"]:
                    issues.append("overlapping_raw_brackets")
            if (_integer(previous.get("monotonic_ns")) and _integer(row.get("monotonic_ns")) and
                    row["monotonic_ns"] <= previous["monotonic_ns"]):
                issues.append("nonincreasing_monotonic")
        row["_position"] = position
        prepared.append(row)
        reasons.append(issues)
    return prepared, reasons


def _span(first: dict[str, Any], last: dict[str, Any], *, bounded: bool,
          band: float, issues: list[str], complete: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"monotonic_vs_raw_ppm": None, "raw_duration_ns": None,
                              "raw_duration_interval_ns": None, "rate_interval_ppm": None,
                              "classification": INDETERMINATE,
                              "complete": complete and not issues, "issues": sorted(set(issues))}
    elapsed = raw_delta_interval(first, last)
    if elapsed:
        # A point estimate is retained for v0.1 readers, never used for classification.
        total = elapsed[0] + elapsed[1]
        result["raw_duration_ns"] = total // 2 if total % 2 == 0 else total / 2
        if bounded:
            result["raw_duration_interval_ns"] = list(elapsed)
    if (elapsed and _integer(first.get("monotonic_ns")) and _integer(last.get("monotonic_ns"))):
        delta = last["monotonic_ns"] - first["monotonic_ns"]
        if delta > 0:
            result["monotonic_vs_raw_ppm"] = float(
                (Fraction(2 * delta, elapsed[0] + elapsed[1]) - 1) * 1_000_000)
            if bounded and not issues:
                result["rate_interval_ppm"] = rate_interval_ppm(delta, elapsed)
                if complete:
                    result["classification"] = _classify_rate(delta, elapsed, band)
        else:
            result["issues"].append("nonpositive_monotonic_elapsed")
            result["complete"] = False
    else:
        result["issues"].append("unavailable_elapsed_geometry")
        result["complete"] = False
    return result


def analyze_probe(payload: dict[str, Any], *, window_s: float = 10.0,
                  rate_band_ppm: float = 100.0,
                  event_threshold_ns: int = 500_000_000) -> dict[str, Any]:
    if not _finite(window_s) or window_s <= 0 or not _finite(window_s * 1_000_000_000) or int(window_s * 1_000_000_000) <= 0:
        raise ValueError("window_s must be finite and >= one nanosecond")
    if not _finite(rate_band_ppm) or rate_band_ppm < 0:
        raise ValueError("rate_band_ppm must be finite and >= 0")
    if not _integer(event_threshold_ns) or event_threshold_ns < 0:
        raise ValueError("event_threshold_ns must be an integer >= 0")
    if not isinstance(payload, dict):
        raise ValueError("probe must be a JSON object")
    source_schema = payload.get("schema_version", 1)
    if not _integer(source_schema) or source_schema not in (1, 2):
        raise ValueError("unsupported probe schema_version")
    samples = payload.get("samples")
    if not isinstance(samples, list) or len(samples) < 2:
        raise ValueError("at least two samples are required")
    bracketed = source_schema == 2
    rows, issues = _prepare_samples(samples, bracketed)
    all_issues = [reason for item in issues for reason in item]
    context = {
        "acquisition": payload.get("acquisition") if bracketed else "legacy_sequential",
        "reference": payload.get("reference") if bracketed else "CLOCK_MONOTONIC_RAW",
        "clock_pair": payload.get("clock_pair") if bracketed else "CLOCK_MONOTONIC/CLOCK_MONOTONIC_RAW",
        "analysis": "fixed_window_interval_v2",
        "uncertainty": "raw_bracket" if bracketed else "unbounded_legacy",
    }
    known_method = (not bracketed or (context["acquisition"] == "raw_bracket_v1" and
                    context["reference"] == "CLOCK_MONOTONIC_RAW" and
                    context["clock_pair"] == "CLOCK_MONOTONIC/CLOCK_MONOTONIC_RAW"))
    if not known_method:
        all_issues.append("unsupported_or_missing_method_context")
    bounded = bracketed and known_method
    full_run = _span(rows[0], rows[-1], bounded=bounded, band=rate_band_ppm,
                     issues=all_issues, complete=True)
    full_change = realtime_event(rows[0], rows[-1], event_threshold_ns) if bounded and not all_issues else None
    # The full-run change is descriptive: a fixed event threshold is not a
    # duration-independent limit on an arbitrarily long accumulated offset.
    full_run["realtime_offset_change_interval_ns"] = (
        full_change["offset_change_interval_ns"] if full_change else None)
    full_run["realtime_offset_direction"] = full_change["direction"] if full_change else "UNRESOLVED"
    windows = fixed_windows([row.get("raw_before_ns") for row in rows], int(window_s * 1_000_000_000))
    for window in windows:
        first, last = window["first_position"], window["last_position"]
        window_issues = [reason for item in issues[first:last + 1] for reason in item]
        if not known_method:
            window_issues.append("unsupported_or_missing_method_context")
        if not window["boundary_coverage"]:
            window_issues.append("incomplete_window_boundaries")
        window.update(_span(rows[first], rows[last], bounded=bounded, band=rate_band_ppm,
                            issues=window_issues, complete=not window["partial"]))
        change = (realtime_event(rows[first], rows[last], event_threshold_ns)
                  if bounded and window["complete"] else None)
        window["realtime_offset_change_interval_ns"] = (
            change["offset_change_interval_ns"] if change else None)
        window["realtime_offset_classification"] = change["classification"] if change else INDETERMINATE
        window["realtime_offset_direction"] = change["direction"] if change else "UNRESOLVED"
        window["sample_count"] = last - first + 1
        window["first_index"] = rows[first].get("index")
        window["last_index"] = rows[last].get("index")
    events = []
    backward = 0
    legacy_large_changes = 0
    for position, (first, last) in enumerate(zip(rows, rows[1:])):
        backward_event = (_integer(first.get("realtime_ns")) and _integer(last.get("realtime_ns")) and
                          last["realtime_ns"] < first["realtime_ns"])
        backward += int(backward_event)
        event = {"first_position": position, "last_position": position + 1,
                 "first_index": first.get("index"), "last_index": last.get("index"),
                 "realtime_backward": bool(backward_event),
                 "issues": sorted(set(issues[position] + issues[position + 1]))}
        if bounded and not event["issues"]:
            event.update(realtime_event(first, last, event_threshold_ns))
        else:
            event.update({"offset_change_interval_ns": None, "classification": INDETERMINATE,
                          "direction": "UNRESOLVED"})
        if not bracketed and all(_integer(row.get(key)) for row in (first, last)
                                 for key in ("realtime_ns", "monotonic_raw_ns")):
            change = ((last["realtime_ns"] - first["realtime_ns"]) -
                      (last["monotonic_raw_ns"] - first["monotonic_raw_ns"]))
            legacy_large_changes += abs(change) > event_threshold_ns
        events.append(event)
    complete_windows = sum(window["complete"] for window in windows)
    invalid_windows = sum(bool(window["issues"]) and not window["partial"] for window in windows)
    partial_windows = sum(window["partial"] for window in windows)
    invalid_samples = sum(bool(item) for item in issues)
    usable_times = [row["raw_before_ns"] for row in rows if _integer(row.get("raw_before_ns"))]
    duration = usable_times[-1] - usable_times[0] if len(usable_times) > 1 else None
    requested_s = payload.get("duration_requested_s")
    cadence_s = payload.get("cadence_requested_s")
    requested_ns = (int(requested_s * 1_000_000_000)
                    if _finite(requested_s) and requested_s > 0 and _finite(requested_s * 1_000_000_000)
                    else None)
    requested_covered = None if requested_ns is None else duration is not None and duration >= requested_ns
    collection_complete = payload.get("collection_complete")
    completion_issues = []
    if not isinstance(collection_complete, bool):
        if bracketed:
            completion_issues.append("missing_or_invalid_collection_complete")
        collection_complete = None
    planned = payload.get("observations_planned")
    valid_planned = _integer(planned) and planned > 0
    cadence_ns = (int(cadence_s * 1_000_000_000)
                  if _finite(cadence_s) and cadence_s > 0 and _finite(cadence_s * 1_000_000_000)
                  else None)
    expected_planned = ((requested_ns + cadence_ns - 1) // cadence_ns + 1
                        if requested_ns and cadence_ns else None)
    if bracketed:
        if not requested_ns:
            completion_issues.append("missing_or_invalid_requested_duration")
        if not cadence_ns:
            completion_issues.append("missing_or_invalid_requested_cadence")
        if rows[0].get("index") != 0:
            completion_issues.append("missing_initial_sample_index")
        if not valid_planned:
            completion_issues.append("missing_or_invalid_observations_planned")
        else:
            if len(rows) != planned:
                completion_issues.append("planned_observation_count_mismatch")
            if expected_planned is not None and planned != expected_planned:
                completion_issues.append("planned_observation_schedule_mismatch")
        if any(row.get("index") != position for position, row in enumerate(rows)):
            completion_issues.append("observation_index_sequence_mismatch")
        schedule = payload.get("schedule")
        if not isinstance(schedule, dict):
            schedule = {}
        origin = schedule.get("origin_raw_ns")
        if (schedule.get("method") != "raw_origin_v1" or
                schedule.get("clock") != "CLOCK_MONOTONIC_RAW" or
                not _integer(origin) or origin != rows[0].get("raw_before_ns") or
                not _integer(schedule.get("duration_ns")) or schedule["duration_ns"] != requested_ns or
                not _integer(schedule.get("cadence_ns")) or schedule["cadence_ns"] != cadence_ns):
            completion_issues.append("missing_or_inconsistent_raw_schedule")
        elapsed_observation = payload.get("elapsed_observation_ns")
        guard_budget = schedule.get("guard_budget_ns")
        if (schedule.get("guard_clock") != "perf_counter_ns" or
                not _integer(guard_budget) or not requested_ns or
                guard_budget != requested_ns + max(1_000_000_000, requested_ns // 10) or
                not _integer(schedule.get("max_wait_iterations_per_target")) or
                schedule["max_wait_iterations_per_target"] != 64 or
                payload.get("observation_clock") != "perf_counter_ns" or
                not _integer(elapsed_observation) or elapsed_observation < 0 or
                (_integer(guard_budget) and _integer(elapsed_observation) and elapsed_observation > guard_budget)):
            completion_issues.append("missing_or_inconsistent_schedule_guard")
        if payload.get("collection_errors") != []:
            completion_issues.append("missing_or_nonempty_collection_errors")
        if _integer(origin) and requested_ns and cadence_ns:
            previous_elapsed = -1
            for position, row in enumerate(rows):
                target = origin + min(position * cadence_ns, requested_ns)
                before, after = row.get("raw_before_ns"), row.get("raw_after_ns")
                lateness = row.get("schedule_lateness_ns")
                observed = row.get("observation_elapsed_ns")
                if (not _integer(row.get("target_raw_ns")) or row["target_raw_ns"] != target or
                        not _integer(before) or before < target or
                        not _integer(lateness) or not _integer(before) or lateness != before - target):
                    completion_issues.append("sample_raw_schedule_mismatch")
                if (not _integer(observed) or observed < 0 or observed < previous_elapsed or
                        not _integer(elapsed_observation) or observed > elapsed_observation):
                    completion_issues.append("sample_observation_elapsed_mismatch")
                if _integer(observed):
                    previous_elapsed = observed
                if (expected_planned and position < expected_planned - 1 and _integer(after) and
                        after >= origin + min((position + 1) * cadence_ns, requested_ns)):
                    completion_issues.append("sample_raw_next_target_missed")
    if collection_complete is False:
        completion_issues.append("collection_incomplete")
    if requested_covered is False:
        completion_issues.append("requested_raw_duration_shortfall")
    # Claims cannot override observed geometry, missing schedule context, or a
    # requested RAW-duration shortfall. Old schema-2 captures remain readable,
    # but lack the evidence needed to verify the corrected acquisition policy.
    completion_verified = (bracketed and known_method and collection_complete is True and
                           requested_covered is True and not completion_issues and not all_issues)
    all_issues.extend(completion_issues)
    full_run["span_complete"] = full_run["complete"]
    full_run["acquisition_complete"] = completion_verified
    full_run["complete"] = full_run["span_complete"] and completion_verified
    coverage = {"sample_count": len(rows), "valid_sample_count": len(rows) - invalid_samples,
                "invalid_sample_count": invalid_samples,
                "complete_window_count": complete_windows, "partial_window_count": partial_windows,
                "invalid_window_count": invalid_windows, "window_count": len(windows),
                "observed_duration_ns": duration,
                "duration_requested_s": requested_s if _finite(requested_s) and requested_s > 0 else None,
                "cadence_requested_s": cadence_s if _finite(cadence_s) and cadence_s > 0 else None,
                "requested_raw_duration_covered": requested_covered,
                "collection_complete": collection_complete,
                "collection_completion_verified": completion_verified,
                "observations_planned": planned if valid_planned else None,
                "observations_expected_from_schedule": expected_planned,
                "elapsed_observation_ns": (payload.get("elapsed_observation_ns")
                                           if _integer(payload.get("elapsed_observation_ns")) else None),
                "requested_duration_fraction": (max(0, duration) / requested_ns
                                                if duration is not None and requested_ns else None),
                "complete": bool(windows) and complete_windows == len(windows) and
                            not all_issues and full_run["span_complete"] and
                            (not bracketed or completion_verified),
                "issues": sorted(set(all_issues))}
    if any(event["realtime_backward"] and not event["issues"] and known_method for event in events) or any(item["classification"] == OUTSIDE for item in windows + events) or any(
            window["realtime_offset_classification"] == OUTSIDE for window in windows):
        classification = OUTSIDE
    elif (bounded and coverage["complete"] and
          all(item["classification"] == WITHIN for item in windows + events) and
          all(window["realtime_offset_classification"] == WITHIN for window in windows)):
        classification = WITHIN
    else:
        classification = INDETERMINATE
    return {
        "schema_version": 2, "source_schema_version": source_schema,
        "sample_count": len(rows), "first_index": rows[0].get("index"), "last_index": rows[-1].get("index"),
        "method": context,
        "settings": {"window_s": window_s, "rate_band_ppm": rate_band_ppm,
                     "event_threshold_ns": event_threshold_ns,
                     "duration_requested_s": coverage["duration_requested_s"],
                     "cadence_requested_s": coverage["cadence_requested_s"]},
        "continuity_label": payload.get("continuity_label"), "coverage": coverage,
        "classification": classification, "full_run": full_run, "windows": windows,
        "realtime_events": events, "realtime_backward_events": backward,
        "large_realtime_minus_raw_changes": (sum(event["classification"] == OUTSIDE for event in events)
                                               if bracketed else legacy_large_changes),
        "outside_realtime_offset_windows": sum(
            window["realtime_offset_classification"] == OUTSIDE for window in windows),
        "notes": [
            "Analysis describes configured guest-relative observations, not universal health or readiness.",
            "MONOTONIC-vs-RAW agreement does not prove absolute accuracy against Windows or an external clock.",
            "Point ppm estimates are descriptive only; classifications use exact rational intervals and decimal settings before outward JSON rounding.",
            "Schema-2 completion requires consistent RAW-origin scheduling, count, indexes, bounded guard metadata, and requested RAW-duration coverage; a completion claim never overrides a shortfall.",
            "Full-run rate classification describes the observed span; span_complete and acquisition_complete distinguish valid local geometry from a finished requested acquisition.",
            "Fixed-window cumulative REALTIME-minus-RAW changes use the configured event band; full-run cumulative change is descriptive and is not thresholded as one event.",
            "Legacy sequential acquisition has unbounded timing uncertainty and cannot establish WITHIN.",
            "Fixed nominal RAW boundaries use the first sample at/after each boundary; partial windows remain indeterminate.",
        ],
    }


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_int=finite_json_integer)
