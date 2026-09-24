from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def rate_ppm(delta_clock_ns: int, delta_ref_ns: int) -> float:
    if delta_ref_ns <= 0:
        raise ValueError("reference delta must be > 0")
    return ((delta_clock_ns / delta_ref_ns) - 1.0) * 1_000_000.0


def analyze_probe(payload: dict[str, Any]) -> dict[str, Any]:
    samples = payload.get("samples") or []
    if len(samples) < 2:
        raise ValueError("at least two samples are required")

    first = samples[0]
    last = samples[-1]

    result: dict[str, Any] = {
        "schema_version": 1,
        "source_schema_version": payload.get("schema_version"),
        "sample_count": len(samples),
        "first_index": first.get("index"),
        "last_index": last.get("index"),
        "realtime_backward_events": 0,
        "large_realtime_minus_raw_changes": 0,
        "full_run": {},
        "notes": [],
    }

    if "monotonic_raw_ns" in first and "monotonic_raw_ns" in last:
        d_raw = last["monotonic_raw_ns"] - first["monotonic_raw_ns"]
        d_mono = last["monotonic_ns"] - first["monotonic_ns"]
        result["full_run"]["monotonic_vs_raw_ppm"] = rate_ppm(d_mono, d_raw)
        result["full_run"]["raw_duration_ns"] = d_raw

    previous = first
    for current in samples[1:]:
        if current["realtime_ns"] < previous["realtime_ns"]:
            result["realtime_backward_events"] += 1

        if (
            "monotonic_raw_ns" in previous
            and "monotonic_raw_ns" in current
        ):
            d_rt = current["realtime_ns"] - previous["realtime_ns"]
            d_raw = current["monotonic_raw_ns"] - previous["monotonic_raw_ns"]
            offset_change = d_rt - d_raw
            if abs(offset_change) > 500_000_000:
                result["large_realtime_minus_raw_changes"] += 1

        previous = current

    result["notes"].extend(
        [
            "Analysis is guest-side unless the input contains a separately documented host reference.",
            "MONOTONIC-vs-RAW agreement does not prove absolute accuracy against Windows or an external clock.",
        ]
    )
    return result


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
