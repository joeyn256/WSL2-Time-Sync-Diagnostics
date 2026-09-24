from __future__ import annotations

import math
from fractions import Fraction

import pytest

from synthetic_guest import duplicate_sample, early_slew, missing_sample, sawtooth, trace
from wsl_time_sync.analyze import (
    analyze_probe, classify_interval, fixed_windows, rate_interval_ppm,
    raw_delta_interval, realtime_event,
)


def test_nominal_brackets_remain_bounded_and_relative():
    result = analyze_probe(trace())
    assert result["classification"] == "WITHIN"
    assert result["coverage"]["complete"]
    assert len(result["windows"]) == 3
    assert all(window["classification"] == "WITHIN" for window in result["windows"])
    lo, hi = result["full_run"]["rate_interval_ppm"]
    assert lo < 0 < hi
    assert result["full_run"]["monotonic_vs_raw_ppm"] == 0
    assert "does not prove absolute accuracy" in " ".join(result["notes"])


def test_early_slew_stays_visible_when_full_run_looks_nominal():
    result = analyze_probe(early_slew())
    assert result["full_run"]["classification"] == "WITHIN"
    assert result["windows"][0]["classification"] == "OUTSIDE"
    assert all(window["classification"] == "WITHIN" for window in result["windows"][1:])
    assert result["classification"] == "OUTSIDE"


def test_periodic_sawtooth_is_not_hidden_by_average():
    result = analyze_probe(sawtooth())
    assert result["full_run"]["classification"] == "WITHIN"
    events = [event for event in result["realtime_events"] if event["classification"] == "OUTSIDE"]
    assert len(events) == 6
    assert all(event["direction"] == "NEGATIVE" for event in events)
    assert result["classification"] == "OUTSIDE"


@pytest.mark.parametrize("size,direction", [(750_000_000, "POSITIVE"), (-750_000_000, "NEGATIVE")])
def test_signed_realtime_steps(size, direction):
    result = analyze_probe(trace(realtime_steps=((5, size),)))
    events = [event for event in result["realtime_events"] if event["classification"] == "OUTSIDE"]
    assert len(events) == 1
    assert events[0]["direction"] == direction
    assert events[0]["offset_change_interval_ns"][0] <= size <= events[0]["offset_change_interval_ns"][1]
    assert result["realtime_backward_events"] == 0
    assert result["classification"] == "OUTSIDE"


def test_backward_realtime_is_reported_even_below_configured_event_threshold():
    result = analyze_probe(trace(realtime_steps=((5, -1_500_000_000),)), event_threshold_ns=2_000_000_000)
    assert result["realtime_backward_events"] == 1
    assert any(event["realtime_backward"] for event in result["realtime_events"])
    assert result["classification"] == "OUTSIDE"


@pytest.mark.parametrize("payload", [missing_sample(), missing_sample(remove=True), duplicate_sample()])
def test_missing_and_duplicate_geometry_cannot_establish_within(payload):
    result = analyze_probe(payload)
    assert result["classification"] == "INDETERMINATE"
    assert not result["coverage"]["complete"]
    assert result["coverage"]["invalid_sample_count"] >= 1
    assert result["windows"][0]["classification"] == "INDETERMINATE"
    assert result["windows"][0]["rate_interval_ppm"] is None
    assert result["windows"][-1]["classification"] == "WITHIN"


def test_rate_threshold_straddling_interval_is_not_replaced_with_midpoint():
    result = analyze_probe(trace(duration_s=10, bracket_width_ns=2_000_000,
                                 rate_segments=((0, 50),)))
    assert result["full_run"]["monotonic_vs_raw_ppm"] == 50
    lo, hi = result["windows"][0]["rate_interval_ppm"]
    assert lo < 100 < hi
    assert result["windows"][0]["classification"] == "INDETERMINATE"
    assert result["classification"] == "INDETERMINATE"


def test_event_threshold_straddling_interval_is_indeterminate():
    payload = trace(realtime_steps=((5, 500_000_000),))
    event = analyze_probe(payload)["realtime_events"][4]
    assert event["offset_change_interval_ns"][0] < 500_000_000 < event["offset_change_interval_ns"][1]
    assert event["classification"] == "INDETERMINATE"
    assert event["direction"] == "POSITIVE"


def test_common_mode_guest_agreement_does_not_detect_host_rate_error():
    # The synthetic external time axis advances 30 s while every guest clock
    # advances 30.003 s. The analyzer has no access to that external truth.
    payload = trace(common_mode_ppm=100)
    result = analyze_probe(payload)
    assert payload["samples"][-1]["raw_before_ns"] == 30_003_000_000
    assert result["full_run"]["classification"] == "WITHIN"
    assert result["classification"] == "WITHIN"
    assert all(window["classification"] == "WITHIN" for window in result["windows"] if not window["partial"])
    assert result["method"]["reference"] == "CLOCK_MONOTONIC_RAW"
    assert "Windows or an external clock" in " ".join(result["notes"])


@pytest.mark.parametrize("interval,expected", [([-100, 100], "WITHIN"), ([100, 100], "WITHIN"),
    ([101, 102], "OUTSIDE"), ([-102, -101], "OUTSIDE"), ([99, 101], "INDETERMINATE"),
    ([-101, -99], "INDETERMINATE"), ([-200, 200], "INDETERMINATE"),
    (None, "INDETERMINATE"), ([math.nan, 0], "INDETERMINATE"),
    ([0, math.inf], "INDETERMINATE"), ([2, 1], "INDETERMINATE")])
def test_three_way_interval_classification(interval, expected):
    assert classify_interval(interval, 100) == expected


@pytest.mark.parametrize("delta", [-2_000_000_001, -1, 0, 1, 1_000_000_001])
def test_signed_rate_interval_encloses_exact_rational_endpoints(delta):
    interval = rate_interval_ppm(delta, (999_999_000, 1_000_001_000))
    endpoints = [(Fraction(delta, ref) - 1) * 1_000_000 for ref in (999_999_000, 1_000_001_000)]
    assert Fraction.from_float(interval[0]) <= min(endpoints)
    assert Fraction.from_float(interval[1]) >= max(endpoints)


@pytest.mark.parametrize("reference", [(0, 10), (-1, 10), (10, 1), (True, 10)])
def test_invalid_rate_reference_has_no_enclosure(reference):
    assert rate_interval_ppm(100, reference) is None


def test_exact_boundary_rate_is_within_inclusive_band():
    assert classify_interval(rate_interval_ppm(1_000_100_000, (1_000_000_000, 1_000_000_000)), 100) == "WITHIN"


def test_bracket_elapsed_bounds_and_signed_event_math():
    first = {"raw_before_ns": 0, "raw_after_ns": 20, "realtime_ns": 10}
    last = {"raw_before_ns": 1_000, "raw_after_ns": 1_030, "realtime_ns": 500}
    assert raw_delta_interval(first, last) == (980, 1030)
    event = realtime_event(first, last, 500)
    assert event["offset_change_interval_ns"] == [-540, -490]
    assert event["classification"] == "INDETERMINATE"


def test_fixed_window_boundaries_do_not_drift_with_sampling_jitter():
    windows = fixed_windows([0, 6, 11, 16, 23, 26, 32], 10)
    assert [window["nominal_end_ns"] for window in windows] == [10, 20, 30]
    assert [(window["first_position"], window["last_position"]) for window in windows] == [(0, 2), (2, 4), (4, 6)]
    assert [window["end_displacement_ns"] for window in windows] == [1, 3, 2]
    assert not windows[-1]["partial"]


def test_partial_tail_is_retained_and_noncertifying():
    result = analyze_probe(trace(duration_s=25))
    assert len(result["windows"]) == 3
    assert result["windows"][-1]["partial"]
    assert result["windows"][-1]["rate_interval_ppm"] is None
    assert result["windows"][-1]["classification"] == "INDETERMINATE"
    assert result["classification"] == "INDETERMINATE"


def test_unsampled_fixed_windows_are_visible():
    result = analyze_probe(trace(duration_s=30, cadence_s=30))
    assert len(result["windows"]) == 3
    assert result["coverage"]["invalid_window_count"] == 3
    assert result["classification"] == "INDETERMINATE"


@pytest.mark.parametrize("field,value", [("raw_after_ns", -1), ("raw_before_ns", None),
    ("bracket_width_ns", -1), ("monotonic_ns", True), ("realtime_ns", "bad")])
def test_invalid_geometry_fails_closed(field, value):
    payload = trace()
    payload["samples"][5][field] = value
    result = analyze_probe(payload)
    assert result["coverage"]["invalid_sample_count"] > 0
    assert not result["coverage"]["complete"]
    assert result["classification"] == "INDETERMINATE"


def test_overlapping_brackets_cannot_establish_rate():
    payload = trace(duration_s=10, bracket_width_ns=1_000_000_001)
    result = analyze_probe(payload)
    assert "overlapping_raw_brackets" in result["coverage"]["issues"]
    assert result["classification"] == "INDETERMINATE"


def test_missing_and_unknown_schema2_method_context_is_not_assumed():
    for method in (None, "different_acquisition"):
        payload = trace()
        payload["acquisition"] = method
        result = analyze_probe(payload)
        assert result["method"]["acquisition"] == method
        assert result["classification"] == "INDETERMINATE"
        assert result["full_run"]["rate_interval_ppm"] is None


def test_legacy_descriptive_ppm_retains_unknown_uncertainty():
    payload = trace()
    payload["schema_version"] = 1
    for row in payload["samples"]:
        row["monotonic_raw_ns"] = row["raw_before_ns"] + row["bracket_width_ns"] // 2
    result = analyze_probe(payload)
    assert result["full_run"]["monotonic_vs_raw_ppm"] == 0
    assert result["method"]["uncertainty"] == "unbounded_legacy"
    assert result["classification"] == "INDETERMINATE"
    assert all(window["rate_interval_ppm"] is None for window in result["windows"])
    assert all(event["classification"] == "INDETERMINATE" for event in result["realtime_events"])


@pytest.mark.parametrize("setting,value", [("window_s", 0), ("window_s", math.inf),
    ("window_s", math.nan), ("window_s", 0.1e-9), ("rate_band_ppm", -1),
    ("rate_band_ppm", math.nan), ("rate_band_ppm", math.inf),
    ("event_threshold_ns", -1), ("event_threshold_ns", math.inf), ("event_threshold_ns", True)])
def test_analysis_rejects_invalid_settings(setting, value):
    with pytest.raises(ValueError):
        analyze_probe(trace(), **{setting: value})


def test_all_missing_samples_have_explicit_indeterminate_coverage():
    result = analyze_probe({"schema_version": 2, "samples": [{"index": 0}, {"index": 1}]})
    assert result["classification"] == "INDETERMINATE"
    assert result["coverage"]["invalid_sample_count"] == 2
    assert result["coverage"]["observed_duration_ns"] is None
    assert not result["windows"]


def test_serialization_remains_strict_json():
    import json
    json.dumps(analyze_probe(trace()), allow_nan=False)


@pytest.mark.parametrize("sign", [1, -1])
def test_fractional_configured_band_boundary_uses_exact_rational_arithmetic(sign):
    payload = trace(duration_s=10, bracket_width_ns=0)
    for row in payload["samples"]:
        row["monotonic_ns"] += sign * row["index"] * 100_100
    result = analyze_probe(payload, rate_band_ppm=100.1)
    assert result["full_run"]["classification"] == "WITHIN"
    assert result["windows"][0]["classification"] == "WITHIN"
    payload["samples"][-1]["monotonic_ns"] += sign
    assert analyze_probe(payload, rate_band_ppm=100.1)["windows"][0]["classification"] == "OUTSIDE"


def test_missing_schema2_indexes_cannot_claim_complete_coverage():
    payload = trace()
    for row in payload["samples"]:
        del row["index"]
    result = analyze_probe(payload)
    assert result["classification"] == "INDETERMINATE"
    assert "invalid_index" in result["coverage"]["issues"]


def test_truncated_capture_at_window_boundary_does_not_claim_requested_coverage():
    payload = trace(duration_s=30)
    payload["samples"] = payload["samples"][:11]
    result = analyze_probe(payload)
    assert result["windows"][0]["classification"] == "WITHIN"
    assert result["classification"] == "INDETERMINATE"
    assert not result["coverage"]["complete"]
    assert result["coverage"]["requested_raw_duration_covered"] is False
    assert result["coverage"]["requested_duration_fraction"] == pytest.approx(1 / 3)
    assert "requested_raw_duration_shortfall" in result["coverage"]["issues"]


def test_huge_finite_window_setting_is_rejected_cleanly():
    with pytest.raises(ValueError):
        analyze_probe(trace(), window_s=1e308)



def test_sampling_overshoot_does_not_invent_single_sample_partial_tail():
    payload = trace()
    for row in payload["samples"][1:]:
        for key in ("raw_before_ns", "raw_after_ns", "monotonic_ns", "realtime_ns"):
            row[key] += 10_000
        row["schedule_lateness_ns"] += 10_000
        row["observation_elapsed_ns"] += 10_000
    payload["elapsed_observation_ns"] += 10_000
    result = analyze_probe(payload)
    assert len(result["windows"]) == 3
    assert result["coverage"]["complete"]
    assert result["classification"] == "WITHIN"
    assert result["windows"][-1]["end_displacement_ns"] == 10_000


def test_sampling_completion_never_overrides_raw_duration_shortfall():
    payload = trace(common_mode_ppm=-1)
    payload["collection_complete"] = True
    payload["observations_planned"] = 31
    payload["elapsed_observation_ns"] = 30_000_000_000
    result = analyze_probe(payload, window_s=9)
    # A completed-collection claim cannot excuse contradictory RAW coverage.
    assert result["coverage"]["collection_complete"] is True
    assert result["coverage"]["requested_raw_duration_covered"] is False
    assert "requested_raw_duration_shortfall" in result["coverage"]["issues"]
    assert not result["coverage"]["collection_completion_verified"]
    assert result["coverage"]["partial_window_count"] == 1
    assert result["settings"]["duration_requested_s"] == 30
    assert result["settings"]["cadence_requested_s"] == 1


def test_explicit_incomplete_acquisition_is_indeterminate():
    payload = trace()
    payload["collection_complete"] = False
    result = analyze_probe(payload)
    assert result["classification"] == "INDETERMINATE"
    assert "collection_incomplete" in result["coverage"]["issues"]


def test_reordered_input_cannot_claim_trustworthy_backward_clock_event():
    payload = trace()
    payload["samples"][4], payload["samples"][5] = payload["samples"][5], payload["samples"][4]
    result = analyze_probe(payload)
    assert result["realtime_backward_events"] == 1
    assert result["classification"] == "INDETERMINATE"
    assert any(event["realtime_backward"] and event["issues"] for event in result["realtime_events"])


@pytest.mark.parametrize("schema", [True, 1.0, 3, "2"])
def test_unsupported_schema_values_are_rejected(schema):
    payload = trace()
    payload["schema_version"] = schema
    with pytest.raises(ValueError):
        analyze_probe(payload)


@pytest.mark.parametrize("payload", [None, [], "bad"])
def test_nonobject_probe_is_rejected(payload):
    with pytest.raises(ValueError, match="JSON object"):
        analyze_probe(payload)


def _complete_probe_metadata(payload):
    # trace() already supplies the complete, internally consistent schedule.
    payload["collection_complete"] = True
    return payload


def test_truncated_serialized_tail_cannot_reuse_complete_capture_metadata():
    payload = _complete_probe_metadata(trace())
    payload["samples"] = payload["samples"][:11]
    result = analyze_probe(payload)
    assert result["windows"][0]["classification"] == "WITHIN"
    assert result["coverage"]["collection_complete"] is True
    assert result["coverage"]["collection_completion_verified"] is False
    assert result["coverage"]["observations_planned"] == 31
    assert "planned_observation_count_mismatch" in result["coverage"]["issues"]
    assert not result["coverage"]["complete"]
    assert result["classification"] == "INDETERMINATE"


def test_complete_capture_metadata_is_verified_against_serialized_evidence():
    result = analyze_probe(_complete_probe_metadata(trace()))
    assert result["coverage"]["collection_completion_verified"] is True
    assert result["coverage"]["observations_expected_from_schedule"] == 31
    assert result["coverage"]["complete"]
    assert result["classification"] == "WITHIN"


@pytest.mark.parametrize("planned", [None, False, 0, -1, 31.0, "31"])
def test_malformed_planned_count_cannot_establish_complete_coverage(planned):
    payload = _complete_probe_metadata(trace())
    payload["observations_planned"] = planned
    result = analyze_probe(payload)
    assert result["classification"] == "INDETERMINATE"
    assert "missing_or_invalid_observations_planned" in result["coverage"]["issues"]
    assert result["windows"][0]["classification"] == "WITHIN"


def test_completion_claim_requires_planned_count_metadata():
    payload = _complete_probe_metadata(trace())
    del payload["observations_planned"]
    result = analyze_probe(payload)
    assert result["classification"] == "INDETERMINATE"
    assert not result["coverage"]["collection_completion_verified"]


def test_planned_count_cannot_contradict_requested_schedule():
    payload = _complete_probe_metadata(trace())
    payload["samples"] = payload["samples"][:11]
    payload["observations_planned"] = 11
    result = analyze_probe(payload)
    assert "planned_observation_schedule_mismatch" in result["coverage"]["issues"]
    assert result["classification"] == "INDETERMINATE"


def test_missing_serialized_prefix_does_not_claim_zero_based_complete_capture():
    payload = _complete_probe_metadata(trace(duration_s=40))
    payload["samples"] = payload["samples"][10:]
    result = analyze_probe(payload)
    assert "missing_initial_sample_index" in result["coverage"]["issues"]
    assert "observation_index_sequence_mismatch" in result["coverage"]["issues"]
    assert not result["coverage"]["complete"]
    assert result["classification"] == "INDETERMINATE"
    assert all(window["classification"] == "WITHIN" for window in result["windows"])


def test_negative_schema2_indexes_are_invalid_geometry():
    payload = trace()
    for row in payload["samples"]:
        row["index"] -= 1
    result = analyze_probe(payload)
    assert "invalid_negative_index" in result["coverage"]["issues"]
    assert result["coverage"]["invalid_sample_count"] == 1
    assert result["classification"] == "INDETERMINATE"


def test_truncated_capture_keeps_confirmed_local_anomaly():
    payload = _complete_probe_metadata(trace(rate_segments=((0, 1_000),)))
    payload["samples"] = payload["samples"][:11]
    result = analyze_probe(payload)
    assert not result["coverage"]["complete"]
    assert result["windows"][0]["classification"] == "OUTSIDE"
    assert result["classification"] == "OUTSIDE"


@pytest.mark.parametrize("field", ["cadence_requested_s", "duration_requested_s", "schedule",
                                   "collection_complete", "collection_errors", "elapsed_observation_ns"])
def test_missing_completion_context_fails_closed(field):
    payload = trace()
    del payload[field]
    result = analyze_probe(payload)
    assert not result["coverage"]["collection_completion_verified"]
    assert result["classification"] == "INDETERMINATE"


def test_rewritten_cadence_and_count_cannot_certify_one_third_duration():
    payload = trace()
    payload["samples"] = payload["samples"][:11]
    payload["observations_planned"] = 11
    payload["cadence_requested_s"] = 3
    payload["schedule"]["cadence_ns"] = 3_000_000_000
    result = analyze_probe(payload)
    assert result["coverage"]["observations_expected_from_schedule"] == 11
    assert result["coverage"]["requested_duration_fraction"] == pytest.approx(1 / 3)
    assert "requested_raw_duration_shortfall" in result["coverage"]["issues"]
    assert "sample_raw_schedule_mismatch" in result["coverage"]["issues"]
    assert not result["coverage"]["collection_completion_verified"]
    assert result["classification"] == "INDETERMINATE"


def test_renumbered_removed_prefix_still_contradicts_raw_origin_and_targets():
    payload = trace(duration_s=40)
    payload["samples"] = payload["samples"][10:]
    for index, row in enumerate(payload["samples"]):
        row["index"] = index
    payload["observations_planned"] = 31
    payload["duration_requested_s"] = 30
    payload["schedule"]["duration_ns"] = 30_000_000_000
    result = analyze_probe(payload)
    assert result["coverage"]["requested_raw_duration_covered"]
    assert "missing_or_inconsistent_raw_schedule" in result["coverage"]["issues"]
    assert "sample_raw_schedule_mismatch" in result["coverage"]["issues"]
    assert not result["coverage"]["collection_completion_verified"]
    assert result["classification"] == "INDETERMINATE"


def test_truncated_full_run_distinguishes_geometry_from_acquisition():
    payload = trace(rate_segments=((0, 1000),))
    payload["samples"] = payload["samples"][:11]
    result = analyze_probe(payload)
    assert result["full_run"]["span_complete"]
    assert not result["full_run"]["acquisition_complete"]
    assert not result["full_run"]["complete"]
    assert result["full_run"]["classification"] == "OUTSIDE"
    assert result["classification"] == "OUTSIDE"


@pytest.mark.parametrize("sign,direction", [(1, "POSITIVE"), (-1, "NEGATIVE")])
def test_subthreshold_adjacent_changes_accumulate_outside_fixed_windows(sign, direction):
    payload = trace(realtime_steps=tuple((second, sign * 400_000_000) for second in range(1, 31)))
    result = analyze_probe(payload)
    assert all(event["classification"] == "WITHIN" for event in result["realtime_events"])
    assert all(window["classification"] == "WITHIN" for window in result["windows"])
    assert all(window["realtime_offset_classification"] == "OUTSIDE" for window in result["windows"])
    assert all(window["realtime_offset_direction"] == direction for window in result["windows"])
    for window in result["windows"]:
        lo, hi = window["realtime_offset_change_interval_ns"]
        assert lo < sign * 4_000_000_000 < hi
    lo, hi = result["full_run"]["realtime_offset_change_interval_ns"]
    assert lo < sign * 12_000_000_000 < hi
    assert result["outside_realtime_offset_windows"] == 3
    assert result["classification"] == "OUTSIDE"


@pytest.mark.parametrize("sign", [1, -1])
def test_fixed_window_cumulative_change_preserves_threshold_uncertainty(sign):
    payload = trace(duration_s=10, realtime_steps=tuple((second, sign * 50_000_000) for second in range(1, 11)))
    result = analyze_probe(payload)
    window = result["windows"][0]
    lo, hi = window["realtime_offset_change_interval_ns"]
    assert lo < sign * 500_000_000 < hi
    assert window["realtime_offset_classification"] == "INDETERMINATE"
    assert result["classification"] == "INDETERMINATE"


def test_full_run_cumulative_change_is_descriptive_not_a_fixed_threshold_event():
    payload = trace(duration_s=100, realtime_steps=tuple((second, 10_000_000) for second in range(1, 101)))
    result = analyze_probe(payload)
    assert result["full_run"]["realtime_offset_change_interval_ns"][0] > 500_000_000
    assert "realtime_offset_classification" not in result["full_run"]
    assert all(window["realtime_offset_classification"] == "WITHIN" for window in result["windows"])
    assert result["classification"] == "WITHIN"


def test_legacy_exact_duration_keeps_integer_json_type():
    payload = trace()
    payload["schema_version"] = 1
    for row in payload["samples"]:
        row["monotonic_raw_ns"] = row["raw_before_ns"]
    result = analyze_probe(payload)
    assert type(result["full_run"]["raw_duration_ns"]) is int
    assert result["full_run"]["raw_duration_ns"] == 30_000_000_000


@pytest.mark.parametrize("field,value,issue", [
    ("target_raw_ns", 1, "sample_raw_schedule_mismatch"),
    ("schedule_lateness_ns", -1, "sample_raw_schedule_mismatch"),
    ("observation_elapsed_ns", -1, "sample_observation_elapsed_mismatch"),
])
def test_contradictory_sample_schedule_context_prevents_completion(field, value, issue):
    payload = trace()
    payload["samples"][0][field] = value
    result = analyze_probe(payload)
    assert issue in result["coverage"]["issues"]
    assert not result["coverage"]["collection_completion_verified"]
    assert result["classification"] == "INDETERMINATE"
