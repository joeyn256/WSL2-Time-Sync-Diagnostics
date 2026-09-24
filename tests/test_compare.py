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
        "full_run": {"monotonic_vs_raw_ppm": ppm, "rate_interval_ppm": [ppm - 1, ppm + 1],
                     "raw_duration_ns": 10_000_000_000,
                     "raw_duration_interval_ns": [9_999_998_000, 10_000_002_000]},
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


@pytest.mark.parametrize("key", ["acquisition", "reference", "clock_pair", "analysis", "uncertainty"])
def test_matching_unknown_method_vocabulary_is_insufficient(key):
    left = report()
    left["method"][key] = "invented_method"
    result = compare_reports(left, deepcopy(left))
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert f"left.method.{key}.invalid" in result["missing_context"]
    assert result["difference_ppm"] is None


def test_known_analysis_versions_remain_distinct():
    left, right = report(), report()
    right["method"]["analysis"] = "fixed_window_interval_v2"
    assert compare_reports(right, deepcopy(right))["comparability"] == "COMPARABLE"
    result = compare_reports(left, right)
    assert result["comparability"] == "DIFFERENT_METHOD"
    assert "method.analysis" in result["differences"]


def test_inconsistent_known_acquisition_and_uncertainty_is_insufficient():
    left = report()
    left["method"]["uncertainty"] = "unbounded_legacy"
    result = compare_reports(left, deepcopy(left))
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert "left.method.inconsistent_uncertainty" in result["missing_context"]


@pytest.mark.parametrize("value", [None, "0", False, float("nan"), float("inf"), -(10 ** 400)])
def test_missing_or_invalid_full_run_point_estimate_is_insufficient(value):
    import json
    left = report()
    left["full_run"]["monotonic_vs_raw_ppm"] = value
    result = compare_reports(left, report())
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert "left.full_run.monotonic_vs_raw_ppm.invalid" in result["missing_context"]
    assert result["left_monotonic_vs_raw_ppm"] is None
    assert result["difference_ppm"] is None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("value", [None, [], [0], [1, -1], [None, 1], [False, 1],
                                  [float("-inf"), 1], [0, float("nan")], [0, 10 ** 400]])
def test_missing_or_invalid_bounded_full_run_enclosure_is_insufficient(value):
    left = report()
    left["full_run"]["rate_interval_ppm"] = value
    result = compare_reports(left, report())
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert "left.full_run.rate_interval_ppm.invalid" in result["missing_context"]
    assert result["difference_interval_ppm"] is None


def test_absent_required_numeric_keys_are_insufficient():
    left = report()
    left["full_run"] = {}
    result = compare_reports(left, report())
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert "left.full_run.monotonic_vs_raw_ppm.invalid" in result["missing_context"]
    assert "left.full_run.rate_interval_ppm.invalid" in result["missing_context"]


def test_legacy_report_can_compare_descriptive_points_without_enclosure():
    left = report()
    left["source_schema_version"] = 1
    left["method"].update(acquisition="legacy_sequential", uncertainty="unbounded_legacy")
    left["full_run"]["rate_interval_ppm"] = None
    left["full_run"]["raw_duration_interval_ns"] = None
    result = compare_reports(left, deepcopy(left))
    assert result["comparability"] == "COMPARABLE"
    assert result["difference_ppm"] == 0
    assert result["difference_interval_ppm"] is None


@pytest.mark.parametrize("value", [1e308, 10 ** 308])
def test_finite_inputs_cannot_emit_nonfinite_difference(value):
    import json
    result = compare_reports(report(-value), report(value))
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert result["difference_ppm"] is None
    assert result["difference_interval_ppm"] is None
    json.dumps(result, allow_nan=False)


def test_comparison_retains_early_slew_aggregate_and_anomaly_context():
    from synthetic_guest import early_slew, trace
    from wsl_time_sync.analyze import analyze_probe
    left = analyze_probe(early_slew())
    right = analyze_probe(trace(duration_s=200))
    result = compare_reports(left, right)
    assert result["comparability"] == "COMPARABLE"
    assert result["left_classification"] == "OUTSIDE"
    assert result["right_classification"] == "WITHIN"
    assert result["left_anomaly_counts"]["rate_windows_outside"] == 1
    assert result["right_anomaly_counts"]["rate_windows_outside"] == 0
    assert result["left_anomaly_counts"]["realtime_events_outside"] == 0
    assert result["left_anomaly_counts"]["realtime_backward_events"] == 0


def test_comparison_exposes_cumulative_and_adjacent_realtime_counts():
    left = report()
    left.update(
        classification="OUTSIDE",
        windows=[{"classification": "WITHIN", "realtime_offset_classification": "OUTSIDE"}],
        realtime_events=[{"classification": "OUTSIDE"}, {"classification": "WITHIN"}],
        realtime_backward_events=1,
    )
    result = compare_reports(left, report())
    assert result["left_anomaly_counts"] == {
        "rate_windows_outside": 0, "realtime_offset_windows_outside": 1,
        "realtime_events_outside": 1, "realtime_backward_events": 1,
    }
    assert all(value is None for value in result["right_anomaly_counts"].values())


@pytest.mark.parametrize("value", [None, 0, -1, "10", False, float("nan"), float("inf"), 10 ** 400])
def test_missing_or_invalid_full_run_duration_is_insufficient(value):
    left = report()
    left["full_run"]["raw_duration_ns"] = value
    result = compare_reports(left, report())
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert "left.full_run.raw_duration_ns.invalid" in result["missing_context"]
    assert result["difference_ppm"] is None


@pytest.mark.parametrize("value", [None, [], [0, 1], [-1, 1], [2, 1],
                                  [1, float("inf")], [1, 10 ** 400]])
def test_missing_or_invalid_bounded_duration_enclosure_is_insufficient(value):
    left = report()
    left["full_run"]["raw_duration_interval_ns"] = value
    result = compare_reports(left, report())
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert "left.full_run.raw_duration_interval_ns.invalid" in result["missing_context"]
    assert result["difference_interval_ppm"] is None


def test_finite_wide_integer_enclosures_cannot_overflow_difference():
    left, right = report(), report()
    left["full_run"]["rate_interval_ppm"] = [-10 ** 308, 10 ** 308]
    right["full_run"]["rate_interval_ppm"] = [-10 ** 308, 10 ** 308]
    result = compare_reports(left, right)
    assert result["comparability"] == "INSUFFICIENT_CONTEXT"
    assert "full_run.difference_interval_ppm.out_of_range" in result["missing_context"]
