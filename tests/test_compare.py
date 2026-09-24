from copy import deepcopy

import pytest

from wsl_time_sync.compare import compare_reports


def report(ppm=0.0):
    return {
        "schema_version": 2, "source_schema_version": 2, "sample_count": 11,
        "method": {"acquisition": "raw_bracket_v1", "reference": "CLOCK_MONOTONIC_RAW",
                   "clock_pair": "CLOCK_MONOTONIC/CLOCK_MONOTONIC_RAW",
                   "analysis": "fixed_window_interval_v1", "uncertainty": "raw_bracket"},
        "settings": {"window_s": 10.0, "rate_band_ppm": 100.0, "event_threshold_ns": 500_000_000},
        "coverage": {"sample_count": 11, "valid_sample_count": 11, "invalid_sample_count": 0,
                     "complete_window_count": 1, "partial_window_count": 0,
                     "invalid_window_count": 0, "complete": True},
        "continuity_label": None,
        "full_run": {"monotonic_vs_raw_ppm": ppm, "rate_interval_ppm": [ppm - 1, ppm + 1]},
    }


def test_compare_is_descriptive_and_encloses_interval_difference():
    result = compare_reports(report(-0.5), report(0.25))
    assert result["comparability"] == "COMPARABLE"
    assert result["difference_ppm"] == 0.75
    assert result["difference_interval_ppm"][0] <= -1.25
    assert result["difference_interval_ppm"][1] >= 2.75
    assert "does not establish a distro ranking" in result["notes"][1]


def test_old_reports_without_context_no_longer_get_numeric_difference():
    left = {"sample_count": 31, "full_run": {"monotonic_vs_raw_ppm": -0.5}}
    right = {"sample_count": 31, "full_run": {"monotonic_vs_raw_ppm": 0.25}}
    result = compare_reports(left, right)
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert result["difference_ppm"] is None
    assert result["left_monotonic_vs_raw_ppm"] == -0.5


@pytest.mark.parametrize("section,key,value", [
    ("method", "reference", "Windows QPC"), ("method", "acquisition", "legacy_sequential"),
    ("method", "clock_pair", "REALTIME/RAW"), ("method", "uncertainty", "unbounded_legacy"),
    ("settings", "window_s", 30), ("settings", "rate_band_ppm", 1000),
    ("settings", "event_threshold_ns", 1), ("coverage", "sample_count", 12),
])
def test_different_context_never_gets_equivalent_comparison(section, key, value):
    left = report()
    right = deepcopy(left)
    right[section][key] = value
    result = compare_reports(left, right)
    assert result["comparability"] == "DIFFERENT_METHOD"
    assert result["difference_ppm"] is None
    assert f"{section}.{key}" in result["differences"]


def test_schema_version_and_continuity_checked():
    left, right = report(), report()
    right["source_schema_version"] = 1
    assert compare_reports(left, right)["comparability"] == "DIFFERENT_METHOD"
    right = report()
    right["continuity_label"] = "continuous"
    assert compare_reports(left, right)["comparability"] == "INSUFFICIENT_CONTEXT"
    left["continuity_label"] = "interrupted"
    assert compare_reports(left, right)["comparability"] == "DIFFERENT_METHOD"


def test_incomplete_coverage_and_missing_settings_are_insufficient():
    left, right = report(), report()
    left["coverage"]["complete"] = False
    assert compare_reports(left, right)["comparability"] == "INSUFFICIENT_CONTEXT"
    left = report()
    del left["settings"]["window_s"]
    assert compare_reports(left, right)["comparability"] == "INSUFFICIENT_CONTEXT"


@pytest.mark.parametrize("section,key,value", [
    ("settings", "window_s", float("nan")), ("settings", "rate_band_ppm", "100"),
    ("method", "reference", ""), ("coverage", "sample_count", -1),
    ("coverage", "complete", "true"),
])
def test_matching_malformed_metadata_is_insufficient(section, key, value):
    left = report()
    left[section][key] = value
    result = compare_reports(left, deepcopy(left))
    assert result["comparability"] != "COMPARABLE"
    assert result["difference_ppm"] is None


def test_malformed_report_objects_fail_cleanly():
    with pytest.raises(ValueError, match="JSON objects"):
        compare_reports([], report())
    left = report()
    left["full_run"] = [1]
    assert compare_reports(left, report())["comparability"] == "INSUFFICIENT_CONTEXT"


def test_requested_sampling_geometry_checked_when_available():
    left, right = report(), report()
    left["settings"]["cadence_requested_s"] = 1
    assert compare_reports(left, right)["comparability"] == "INSUFFICIENT_CONTEXT"
    right["settings"]["cadence_requested_s"] = 2
    assert compare_reports(left, right)["comparability"] == "DIFFERENT_METHOD"
    right["settings"]["cadence_requested_s"] = 1
    assert compare_reports(left, right)["comparability"] == "COMPARABLE"


def test_enormous_integer_metadata_does_not_crash_comparison():
    left = report()
    left['settings']['window_s'] = 10 ** 400
    assert compare_reports(left, deepcopy(left))['comparability'] == 'INSUFFICIENT_CONTEXT'
