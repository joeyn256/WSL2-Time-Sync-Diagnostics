import pytest

from wsl_time_sync.analyze import analyze_probe, rate_ppm


def test_rate_ppm_zero():
    assert rate_ppm(1_000_000_000, 1_000_000_000) == 0.0


def test_rate_ppm_positive():
    assert rate_ppm(1_001_000_000, 1_000_000_000) == pytest.approx(1000.0)


def test_analyze_detects_guest_relative_rate():
    payload = {
        "schema_version": 1,
        "samples": [
            {
                "index": 0,
                "realtime_ns": 0,
                "monotonic_ns": 0,
                "monotonic_raw_ns": 0,
            },
            {
                "index": 1,
                "realtime_ns": 1_000_000_000,
                "monotonic_ns": 1_000_500_000,
                "monotonic_raw_ns": 1_000_000_000,
            },
        ],
    }
    result = analyze_probe(payload)
    assert result["sample_count"] == 2
    assert result["full_run"]["monotonic_vs_raw_ppm"] == pytest.approx(500.0)
    assert result["realtime_backward_events"] == 0


def test_analyze_detects_backward_realtime():
    payload = {
        "schema_version": 1,
        "samples": [
            {
                "index": 0,
                "realtime_ns": 2_000_000_000,
                "monotonic_ns": 0,
                "monotonic_raw_ns": 0,
            },
            {
                "index": 1,
                "realtime_ns": 1_000_000_000,
                "monotonic_ns": 1_000_000_000,
                "monotonic_raw_ns": 1_000_000_000,
            },
        ],
    }
    result = analyze_probe(payload)
    assert result["realtime_backward_events"] == 1
