import math

import pytest

from wsl_time_sync import probe
from wsl_time_sync.analyze import analyze_probe


class ScheduledClocks:
    """Advance independent RAW/MONOTONIC clocks through real probe read/wait calls."""

    def __init__(self, monkeypatch, *, raw_ppm=0, initial_delay_ns=0,
                 oversleep_ns=0, read_cost_ns=200, stop_raw_at_ns=None,
                 fail_raw_at_ns=None):
        self.now = 0
        self.raw_origin = 8_000_000_000_000
        self.raw_ppm = raw_ppm
        self.initial_delay_ns = initial_delay_ns
        self.oversleep_ns = oversleep_ns
        self.read_cost_ns = read_cost_ns
        self.stop_raw_at_ns = stop_raw_at_ns
        self.fail_raw_at_ns = fail_raw_at_ns
        self.raw_reads = 0
        self.sleeps = []
        for clock, name in enumerate(("CLOCK_MONOTONIC_RAW", "CLOCK_REALTIME", "CLOCK_MONOTONIC", "CLOCK_BOOTTIME")):
            monkeypatch.setattr(probe.time, name, clock, raising=False)
        monkeypatch.setattr(probe.time, "clock_gettime_ns", self.read, raising=False)
        monkeypatch.setattr(probe.time, "perf_counter_ns", lambda: self.now)
        monkeypatch.setattr(probe.time, "time_ns", lambda: 1_700_000_000_000_000_000 + self.now)
        monkeypatch.setattr(probe.time, "sleep", self.sleep)

    def read(self, clock):
        if clock == 0:
            if self.raw_reads == 0:
                self.now += self.initial_delay_ns
            self.raw_reads += 1
            if self.fail_raw_at_ns is not None and self.now >= self.fail_raw_at_ns:
                raise OSError("synthetic RAW failure")
            elapsed = self.now if self.stop_raw_at_ns is None else min(self.now, self.stop_raw_at_ns)
            value = self.raw_origin + elapsed * (1_000_000 + self.raw_ppm) // 1_000_000
        elif clock == 1:
            value = 1_700_000_000_000_000_000 + self.now
        else:
            value = 900_000_000_000 + self.now
        self.now += self.read_cost_ns
        return value

    def sleep(self, seconds):
        elapsed = round(seconds * 1_000_000_000)
        assert elapsed > 0
        self.sleeps.append(elapsed)
        self.now += elapsed + self.oversleep_ns


def test_probe_collects_samples_without_mutation():
    result = probe.run_probe(duration_s=0.01, cadence_s=0.005)
    assert result["schema_version"] == 2
    assert result["mode"] == "read_only"
    assert result["acquisition"] == "raw_bracket_v1"
    assert len(result["samples"]) >= 2
    assert result["samples"][0]["index"] == 0


def test_capture_order_and_bracket(monkeypatch):
    calls = []
    readings = iter([100, 2000, 110, 112, 120])
    for i, name in enumerate(("CLOCK_MONOTONIC_RAW", "CLOCK_REALTIME", "CLOCK_MONOTONIC", "CLOCK_BOOTTIME")):
        monkeypatch.setattr(probe.time, name, i, raising=False)
    def read(clock):
        calls.append(clock)
        return next(readings)
    monkeypatch.setattr(probe.time, "clock_gettime_ns", read, raising=False)
    sample = probe.capture_sample(7)
    assert calls == [0, 1, 2, 3, 0]
    assert sample == {"index": 7, "raw_before_ns": 100, "raw_after_ns": 120,
                      "bracket_width_ns": 20, "realtime_ns": 2000,
                      "monotonic_ns": 110, "boottime_ns": 112, "errors": {}}


def test_unavailable_clocks_are_explicit_and_not_substituted(monkeypatch):
    monkeypatch.delattr(probe.time, "CLOCK_MONOTONIC_RAW", raising=False)
    monkeypatch.delattr(probe.time, "CLOCK_BOOTTIME", raising=False)
    result = probe.capture_sample(0)
    assert result["raw_before_ns"] is None
    assert result["raw_after_ns"] is None
    assert result["bracket_width_ns"] is None
    assert result["boottime_ns"] is None
    assert set(result["errors"]) >= {"raw_before_ns", "raw_after_ns", "boottime_ns"}


def test_read_error_preserves_missing_field(monkeypatch):
    monkeypatch.setattr(probe.time, "CLOCK_MONOTONIC_RAW", 42, raising=False)
    def fail(clock):
        raise OSError("unavailable")
    monkeypatch.setattr(probe.time, "clock_gettime_ns", fail, raising=False)
    result = probe.capture_sample(0)
    assert result["raw_after_ns"] is None
    assert "OSError" in result["errors"]["raw_after_ns"]


@pytest.mark.parametrize("value", [0, -1, math.inf, -math.inf, math.nan, 1e-12, True])
@pytest.mark.parametrize("argument", ["duration_s", "cadence_s"])
def test_probe_rejects_unbounded_or_invalid_settings(argument, value):
    with pytest.raises(ValueError):
        probe.run_probe(**{argument: value})


def test_cadence_larger_than_duration_does_not_extend_requested_wait(monkeypatch):
    clocks = ScheduledClocks(monkeypatch, read_cost_ns=0)
    result = probe.run_probe(0.001, 600)
    assert clocks.now == 1_000_000
    assert len(result["samples"]) == 2
    assert result["collection_complete"] is True
    assert result["samples"][-1]["target_raw_ns"] == clocks.raw_origin + 1_000_000
    analysis = analyze_probe(result, window_s=0.001)
    assert analysis["classification"] == "WITHIN"
    assert all(not window["partial"] for window in analysis["windows"])


def test_probe_marks_read_overrun_incomplete(monkeypatch):
    clocks = ScheduledClocks(monkeypatch, read_cost_ns=4_000_000)
    result = probe.run_probe(0.01, 0.005)
    assert result["collection_complete"] is False
    assert result["observations_planned"] == 3
    assert result["elapsed_observation_ns"] == clocks.now == 20_000_000
    assert result["collection_errors"] == ["sample_raw_next_target_missed"]
    assert len(result["samples"]) == 1


@pytest.mark.parametrize("settings", [{"duration_s": 86401}, {"duration_s": 1, "cadence_s": 1e-9}])
def test_probe_rejects_excessive_observation_grid(settings):
    with pytest.raises(ValueError):
        probe.run_probe(**settings)


def test_enormous_integer_duration_is_rejected_cleanly():
    with pytest.raises(ValueError):
        probe.run_probe(duration_s=10 ** 400)


@pytest.mark.parametrize("clock_settings", [
    {"initial_delay_ns": 25_000_000},
    {"raw_ppm": -50},
    {"raw_ppm": 50},
    {"oversleep_ns": 2_000_000},
    {"raw_ppm": -50, "initial_delay_ns": 25_000_000, "oversleep_ns": 2_000_000},
], ids=["initial_origin_offset", "raw_slower", "raw_faster", "scheduler_overshoot", "combined"])
def test_scheduled_raw_capture_covers_analysis_windows(monkeypatch, clock_settings):
    clocks = ScheduledClocks(monkeypatch, **clock_settings)
    payload = probe.run_probe(30, 1)
    samples = payload["samples"]
    origin = samples[0]["raw_before_ns"]
    assert payload["collection_complete"] is True
    assert payload["collection_errors"] == []
    assert len(samples) == 31
    assert payload["schedule"]["origin_raw_ns"] == origin
    assert samples[-1]["raw_before_ns"] - origin >= 30_000_000_000
    assert payload["elapsed_observation_ns"] == clocks.now
    assert all(row["target_raw_ns"] == origin + row["index"] * 1_000_000_000 for row in samples)
    assert all(row["schedule_lateness_ns"] == row["raw_before_ns"] - row["target_raw_ns"] >= 0 for row in samples)
    analysis = analyze_probe(payload)
    assert analysis["classification"] == "WITHIN"
    assert analysis["coverage"]["requested_raw_duration_covered"] is True
    assert analysis["coverage"]["collection_completion_verified"] is True
    assert len(analysis["windows"]) == 3
    assert all(not window["partial"] for window in analysis["windows"])


@pytest.mark.parametrize("clock_settings", [
    {"stop_raw_at_ns": 1_100_000_000},
    {"raw_ppm": -999_999},
    {"fail_raw_at_ns": 1_500_000_000},
], ids=["stopped_raw", "severely_slow_raw", "failed_raw"])
def test_failed_raw_progress_terminates_without_completion(monkeypatch, clock_settings):
    clocks = ScheduledClocks(monkeypatch, **clock_settings)
    payload = probe.run_probe(2, 1)
    assert payload["collection_complete"] is False
    assert payload["collection_errors"]
    assert payload["elapsed_observation_ns"] <= payload["schedule"]["guard_budget_ns"] + 1_000
    assert len(clocks.sleeps) <= payload["schedule"]["max_wait_iterations_per_target"]
    if len(payload["samples"]) >= 2:
        assert analyze_probe(payload)["classification"] != "WITHIN"
    else:
        with pytest.raises(ValueError, match="at least two samples"):
            analyze_probe(payload)


def test_missing_initial_raw_stays_explicit_and_incomplete(monkeypatch):
    clocks = ScheduledClocks(monkeypatch, fail_raw_at_ns=0)
    payload = probe.run_probe(2, 1)
    assert not payload["collection_complete"]
    assert payload["schedule"]["origin_raw_ns"] is None
    assert payload["samples"][0]["raw_before_ns"] is None
    assert payload["samples"][0]["target_raw_ns"] is None
    assert clocks.sleeps == []


def test_large_scheduler_overshoot_does_not_burst_catch_up(monkeypatch):
    clocks = ScheduledClocks(monkeypatch, oversleep_ns=1_500_000_000)
    payload = probe.run_probe(5, 1)
    assert not payload["collection_complete"]
    assert payload["collection_errors"] == ["sample_raw_next_target_missed"]
    assert len(payload["samples"]) == 2
    assert len(clocks.sleeps) == 1
    assert payload["samples"][-1]["schedule_lateness_ns"] >= 1_500_000_000


def test_wait_iteration_limit_even_if_observation_guard_stops(monkeypatch):
    clocks = ScheduledClocks(monkeypatch, stop_raw_at_ns=0, read_cost_ns=0)
    monkeypatch.setattr(probe.time, "perf_counter_ns", lambda: 0)
    payload = probe.run_probe(2, 1)
    assert not payload["collection_complete"]
    assert payload["collection_errors"] == ["raw_target_wait_limit_exhausted"]
    assert len(clocks.sleeps) == payload["schedule"]["max_wait_iterations_per_target"]
