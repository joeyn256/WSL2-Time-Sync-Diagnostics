from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


_METHOD_KEYS = ("acquisition", "reference", "clock_pair", "analysis", "uncertainty")
_SETTING_KEYS = ("window_s", "rate_band_ppm", "event_threshold_ns")
_COVERAGE_KEYS = ("sample_count", "valid_sample_count", "invalid_sample_count",
                  "complete_window_count", "partial_window_count", "invalid_window_count", "complete")


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _context(report: dict[str, Any]) -> dict[str, Any]:
    return {key: report.get(key) for key in (
        "schema_version", "source_schema_version", "method", "settings", "coverage", "continuity_label"
    )}


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _interval(value: Any) -> bool:
    return (isinstance(value, list) and len(value) == 2
            and all(_finite_number(v) for v in value) and value[0] <= value[1])


def compare_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare matched report methods; unknown context never licenses a difference."""
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError("comparison inputs must be JSON objects")
    contexts = [_context(left), _context(right)]
    missing: list[str] = []
    differences: list[str] = []
    for label, context in zip(("left", "right"), contexts):
        for key in ("schema_version", "source_schema_version"):
            if type(context[key]) is not int or context[key] not in (1, 2):
                missing.append(f"{label}.{key}")
        for section, keys in (("method", _METHOD_KEYS), ("settings", _SETTING_KEYS),
                              ("coverage", _COVERAGE_KEYS)):
            values = context[section]
            if not isinstance(values, dict):
                missing.append(f"{label}.{section}")
            else:
                missing.extend(f"{label}.{section}.{key}" for key in keys if values.get(key) is None)
        method = context.get("method")
        if isinstance(method, dict):
            missing.extend(f"{label}.method.{key}.invalid" for key in _METHOD_KEYS
                           if not isinstance(method.get(key), str) or not method[key].strip())
        settings = context.get("settings")
        if isinstance(settings, dict):
            for key in _SETTING_KEYS:
                value = settings.get(key)
                if (not _finite_number(value) or value < 0
                        or (key == "window_s" and value == 0)
                        or (key == "event_threshold_ns" and type(value) is not int)):
                    missing.append(f"{label}.settings.{key}.invalid")
            for key in ("duration_requested_s", "cadence_requested_s"):
                if settings.get(key) is not None and (
                        not _finite_number(settings[key]) or settings[key] <= 0):
                    missing.append(f"{label}.settings.{key}.invalid")
        coverage = context.get("coverage") or {}
        if isinstance(coverage, dict) and coverage.get("complete") is not True:
            missing.append(f"{label}.coverage.incomplete")
        if isinstance(coverage, dict):
            for key in _COVERAGE_KEYS[:-1]:
                if type(coverage.get(key)) is not int or coverage[key] < 0:
                    missing.append(f"{label}.coverage.{key}.invalid")
            if all(type(coverage.get(k)) is int for k in ("sample_count", "valid_sample_count", "invalid_sample_count")):
                if coverage["sample_count"] != coverage["valid_sample_count"] + coverage["invalid_sample_count"]:
                    missing.append(f"{label}.coverage.inconsistent_counts")
            if any(coverage.get(k) != 0 for k in ("invalid_sample_count", "partial_window_count", "invalid_window_count")):
                missing.append(f"{label}.coverage.invalid_or_partial")
            if not isinstance(coverage.get("complete_window_count"), int) or coverage["complete_window_count"] < 1:
                missing.append(f"{label}.coverage.no_complete_windows")
        if context["continuity_label"] is not None and not isinstance(context["continuity_label"], str):
            missing.append(f"{label}.continuity_label.invalid")
    lctx, rctx = contexts
    for key in ("schema_version", "source_schema_version"):
        if lctx[key] is not None and rctx[key] is not None and lctx[key] != rctx[key]:
            differences.append(key)
    for section, keys in (("method", _METHOD_KEYS), ("settings", _SETTING_KEYS),
                          ("coverage", _COVERAGE_KEYS[:-1])):
        lv, rv = lctx[section], rctx[section]
        if isinstance(lv, dict) and isinstance(rv, dict):
            differences.extend(f"{section}.{key}" for key in keys
                               if lv.get(key) is not None and rv.get(key) is not None and lv[key] != rv[key])
    ls, rs = lctx["settings"], rctx["settings"]
    if isinstance(ls, dict) and isinstance(rs, dict):
        for key in ("duration_requested_s", "cadence_requested_s"):
            if (ls.get(key) is None) != (rs.get(key) is None):
                missing.append(f"settings.{key} present on only one report")
            elif ls.get(key) != rs.get(key):
                differences.append(f"settings.{key}")
    lc, rc = lctx["continuity_label"], rctx["continuity_label"]
    if (lc is None) != (rc is None):
        missing.append("continuity_label present on only one report")
    elif lc is not None and lc != rc:
        differences.append("continuity_label")
    # Known methodological differences remain visible even with incomplete context.
    status = "DIFFERENT_METHOD" if differences else "INSUFFICIENT_CONTEXT" if missing else "COMPARABLE"
    lf, rf = left.get("full_run"), right.get("full_run")
    if not isinstance(lf, dict):
        lf = {}
        missing.append("left.full_run")
    if not isinstance(rf, dict):
        rf = {}
        missing.append("right.full_run")
    lppm, rppm = lf.get("monotonic_vs_raw_ppm"), rf.get("monotonic_vs_raw_ppm")
    li, ri = lf.get("rate_interval_ppm"), rf.get("rate_interval_ppm")
    if not differences and missing:
        status = "INSUFFICIENT_CONTEXT"
    result: dict[str, Any] = {
        "schema_version": 2,
        "comparability": status,
        "differences": differences,
        "missing_context": missing,
        "left_context": lctx,
        "right_context": rctx,
        "left_sample_count": left.get("sample_count"),
        "right_sample_count": right.get("sample_count"),
        "left_monotonic_vs_raw_ppm": lppm,
        "right_monotonic_vs_raw_ppm": rppm,
        "difference_ppm": None,
        "difference_interval_ppm": None,
        "notes": [
            "This comparison is descriptive; differences use right minus left.",
            "It does not establish a distro ranking unless the two runs used a matched design.",
            "COMPARABLE checks recorded methods/settings/coverage, not host agreement or causal equivalence.",
        ],
    }
    if status == "COMPARABLE":
        if _finite_number(lppm) and _finite_number(rppm):
            result["difference_ppm"] = rppm - lppm
        if _interval(li) and _interval(ri):
            # Round outwards so subtraction cannot narrow the serialized enclosure.
            result["difference_interval_ppm"] = [
                math.nextafter(ri[0] - li[1], -math.inf),
                math.nextafter(ri[1] - li[0], math.inf),
            ]
    return result


def compare_paths(left_path: str | Path, right_path: str | Path) -> dict[str, Any]:
    return compare_reports(_load(left_path), _load(right_path))
