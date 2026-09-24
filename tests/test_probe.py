import math

import pytest

from wsl_time_sync import probe


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
    now = [0]
    monkeypatch.setattr(probe.time, "perf_counter_ns", lambda: now[0])
    def sleep(seconds):
        now[0] += round(seconds * 1e9)
    monkeypatch.setattr(probe.time, "sleep", sleep)
    monkeypatch.setattr(probe, "capture_sample", lambda index: {"index": index})
    result = probe.run_probe(0.001, 600)
    assert now[0] == 1_000_000
    assert len(result["samples"]) == 2


def test_probe_marks_read_overrun_incomplete(monkeypatch):
    now = [0]
    monkeypatch.setattr(probe.time, "perf_counter_ns", lambda: now[0])
    def capture(index):
        now[0] += 20_000_000
        return {"index": index}
    monkeypatch.setattr(probe, "capture_sample", capture)
    result = probe.run_probe(0.01, 0.005)
    assert result["collection_complete"] is False
    assert result["observations_planned"] == 3
    assert result["elapsed_observation_ns"] == 20_000_000


@pytest.mark.parametrize("settings", [{"duration_s": 86401}, {"duration_s": 1, "cadence_s": 1e-9}])
def test_probe_rejects_excessive_observation_grid(settings):
    with pytest.raises(ValueError):
        probe.run_probe(**settings)


def test_enormous_integer_duration_is_rejected_cleanly():
    with pytest.raises(ValueError):
        probe.run_probe(duration_s=10 ** 400)
