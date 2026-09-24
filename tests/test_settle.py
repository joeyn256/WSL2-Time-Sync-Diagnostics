"""Parameterized states model shapes, never private captured evidence."""

import pytest

from wsl_time_sync import settle


def reading(*, tick=10000, freq_ppm=10):
    return {"available": True, "raw": {"tick": tick, "freq": int(freq_ppm * 65536)}}


class SyntheticClock:
    def __init__(self):
        self.now = 0
        self.sleeps = []

    def perf_counter_ns(self):
        return self.now

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.now += round(duration * 1_000_000_000)


def install_clock(monkeypatch):
    clock = SyntheticClock()
    monkeypatch.setattr(settle.time, "perf_counter_ns", clock.perf_counter_ns)
    monkeypatch.setattr(settle.time, "sleep", clock.sleep)
    return clock


def test_nominal_historical_example_requires_repeated_observations():
    result = settle.classify_settle_readings([reading()] * 3)
    assert result["classification"] == "WITHIN_CONFIGURED_BAND"
    assert result["policy"]["name"] == "historical_example_tick10000_freq100ppm"
    assert result["longest_consecutive_within"] == 3
    assert settle.classify_settle_readings([reading()] * 2)["classification"] == "INDETERMINATE"
    assert settle.classify_settle_readings([])["classification"] == "INDETERMINATE"


@pytest.mark.parametrize("anomaly", [reading(tick=10009), reading(freq_ppm=450),
                                    reading(freq_ppm=100), reading(freq_ppm=-100)])
def test_synthetic_early_correction_survives_later_nominal_reads(anomaly):
    result = settle.classify_settle_readings([anomaly] + [reading()] * 10)
    assert result["classification"] == "ANOMALY_OBSERVED"
    assert result["anomaly_count"] == 1
    assert result["longest_consecutive_within"] == 10


def test_strict_frequency_boundary_uses_raw_fixed_point_value():
    just_inside = reading(freq_ppm=100)
    just_inside["raw"]["freq"] -= 1
    assert settle.classify_settle_readings([just_inside] * 3)["classification"] == "WITHIN_CONFIGURED_BAND"


@pytest.mark.parametrize("missing", [{"available": False}, {}, {"available": True, "raw": {}},
                                    {"available": True, "raw": {"tick": True, "freq": 0}},
                                    {"available": True, "raw": {"tick": 10000, "freq": float("nan")}}])
def test_missing_or_malformed_state_prevents_within_result(missing):
    result = settle.classify_settle_readings([reading()] * 3 + [missing] + [reading()] * 3)
    assert result["classification"] == "INDETERMINATE"
    assert result["indeterminate_count"] == 1
    assert result["longest_consecutive_within"] == 3
    result = settle.classify_settle_readings([missing, reading(tick=9990)])
    assert result["classification"] == "ANOMALY_OBSERVED"


def test_custom_band_is_named_as_configuration():
    result = settle.classify_settle_readings([reading(tick=9999)] * 2,
                                           expected_tick=9999, max_abs_freq_ppm=20,
                                           required_consecutive=2)
    assert result["classification"] == "WITHIN_CONFIGURED_BAND"
    assert result["policy"]["name"] == "configured_tick_frequency_band"


def test_finite_schedule_ends_at_deadline_without_retries(monkeypatch):
    clock = install_clock(monkeypatch)
    calls = []
    def observe():
        calls.append(clock.now)
        return reading()
    monkeypatch.setattr(settle, "observe_adjtimex", observe)
    result = settle.run_settle_check(duration_s=2.5, cadence_s=1)
    assert calls == [0, 1_000_000_000, 2_000_000_000, 2_500_000_000]
    assert result["complete"]
    assert result["observations_planned"] == result["observations_collected"] == 4
    assert result["elapsed_s"] == 2.5
    assert result["classification"] == "WITHIN_CONFIGURED_BAND"
    assert result["mode"] == "read_only"
    assert result["schema_version"] == 2
    assert set(result["reading_classifications"]) == {"WITHIN_CONFIGURED_BAND"}


def test_cadence_longer_than_duration_does_not_extend_deadline(monkeypatch):
    clock = install_clock(monkeypatch)
    monkeypatch.setattr(settle, "observe_adjtimex", reading)
    result = settle.run_settle_check(duration_s=0.25, cadence_s=60, required_consecutive=2)
    assert clock.sleeps == [0.25]
    assert result["observations_collected"] == 2
    assert result["elapsed_s"] == 0.25


@pytest.mark.parametrize("anomaly", [False, True])
def test_slow_read_stops_at_deadline_and_retains_anomaly(monkeypatch, anomaly):
    clock = install_clock(monkeypatch)
    def slow_observe():
        clock.now += 2_000_000_000
        return reading(freq_ppm=300 if anomaly else 0)
    monkeypatch.setattr(settle, "observe_adjtimex", slow_observe)
    result = settle.run_settle_check(duration_s=1, cadence_s=0.1)
    assert result["observations_collected"] == 1
    assert not result["complete"]
    assert result["elapsed_s"] == 2
    assert result["classification"] == ("ANOMALY_OBSERVED" if anomaly else "INDETERMINATE")


def test_unavailable_snapshots_do_not_retry_or_certify(monkeypatch):
    install_clock(monkeypatch)
    monkeypatch.setattr(settle, "observe_adjtimex", lambda: {"available": False})
    result = settle.run_settle_check(duration_s=2, cadence_s=1)
    assert result["observations_collected"] == 3
    assert result["classification"] == "INDETERMINATE"
    assert result["indeterminate_count"] == 3


@pytest.mark.parametrize("kwargs", [
    {"duration_s": float("inf")}, {"duration_s": float("nan")},
    {"duration_s": 0}, {"duration_s": -1}, {"duration_s": True},
    {"cadence_s": float("nan")}, {"cadence_s": float("inf")},
    {"cadence_s": 0}, {"cadence_s": -1}, {"cadence_s": 1e-20},
    {"duration_s": 1e-20}, {"duration_s": 86401},
    {"duration_s": 1, "cadence_s": 1e-9},
    {"required_consecutive": 1}, {"required_consecutive": 2.5},
    {"expected_tick": -1}, {"expected_tick": True},
    {"max_abs_freq_ppm": float("nan")}, {"max_abs_freq_ppm": 0},
])
def test_invalid_or_unbounded_requests_fail_before_observing(monkeypatch, kwargs):
    monkeypatch.setattr(settle, "observe_adjtimex", lambda: pytest.fail("read before validation"))
    with pytest.raises(ValueError):
        settle.run_settle_check(**kwargs)


@pytest.mark.parametrize("raw", [{"tick": 10009}, {"freq": 200 * 65536}])
def test_known_partial_anomaly_remains_visible(raw):
    result = settle.classify_settle_readings([{"available": True, "raw": raw}])
    assert result["classification"] == "ANOMALY_OBSERVED"


def test_extreme_finite_band_does_not_overflow():
    result = settle.classify_settle_readings([reading()] * 3, max_abs_freq_ppm=1e308)
    assert result["classification"] == "WITHIN_CONFIGURED_BAND"


def test_unrepresentable_numeric_argument_is_rejected():
    with pytest.raises(ValueError):
        settle.run_settle_check(duration_s=10**1000)


@pytest.mark.parametrize("sign", [-1, 1])
def test_fractional_frequency_boundary_is_strict_and_exact(sign):
    at_boundary = {"available": True, "raw": {"tick": 10000, "freq": sign * 32768}}
    just_inside = {"available": True, "raw": {"tick": 10000, "freq": sign * 32767}}
    result = settle.classify_settle_readings([at_boundary] * 3, max_abs_freq_ppm=0.5)
    assert result["classification"] == "ANOMALY_OBSERVED"
    result = settle.classify_settle_readings([just_inside] * 3, max_abs_freq_ppm=0.5)
    assert result["classification"] == "WITHIN_CONFIGURED_BAND"
