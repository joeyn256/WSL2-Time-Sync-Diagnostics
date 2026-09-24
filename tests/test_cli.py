import json

import pytest

from wsl_time_sync import cli


def invoke(monkeypatch, capsys, args):
    monkeypatch.setattr("sys.argv", ["wsl-time-sync", *args])
    assert cli.main() == 0
    return json.loads(capsys.readouterr().out)


def test_analyze_accepts_legacy_example(monkeypatch, capsys):
    result = invoke(monkeypatch, capsys, ["analyze", "examples/sample-probe.json", "--window", "1"])
    assert result["source_schema_version"] == 1
    assert result["schema_version"] == 2


def test_settle_cli_passes_explicit_policy(monkeypatch, capsys):
    calls = []
    def observe(*args, **kwargs):
        calls.append((args, kwargs))
        return {"classification": "INDETERMINATE"}
    monkeypatch.setattr(cli, "run_settle_check", observe)
    result = invoke(monkeypatch, capsys, ["settle-check", "--duration", "2", "--cadence", "0.5",
        "--expected-tick", "9999", "--max-abs-freq-ppm", "50", "--required-consecutive", "4"])
    assert result["classification"] == "INDETERMINATE"
    assert calls == [((2.0, 0.5), {"expected_tick": 9999, "max_abs_freq_ppm": 50.0, "required_consecutive": 4})]


def test_invalid_probe_cli_is_usage_error(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["wsl-time-sync", "probe", "--duration", "nan"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "finite" in capsys.readouterr().err


def test_json_file_output_rejects_nonfinite_numbers(tmp_path):
    from wsl_time_sync.utils import write_json
    output = tmp_path / 'output.json'
    with pytest.raises(ValueError):
        write_json(output, {'invalid': float('nan')})
    assert not output.exists()


@pytest.mark.parametrize("field", ["realtime_ns", "monotonic_ns", "monotonic_raw_ns"])
def test_analyze_huge_json_integer_is_usage_error(tmp_path, monkeypatch, capsys, field):
    from pathlib import Path
    payload = json.loads(Path("examples/sample-probe.json").read_text())
    payload["samples"][-1][field] = 10 ** 400
    source = tmp_path / "huge.json"
    source.write_text(json.dumps(payload))
    monkeypatch.setattr("sys.argv", ["wsl-time-sync", "analyze", str(source)])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "finite" in captured.err
    assert "Traceback" not in captured.err
    assert not captured.out


def test_compare_huge_json_integer_is_usage_error(tmp_path, monkeypatch, capsys):
    source = tmp_path / "huge.json"
    source.write_text(json.dumps({"settings": {"window_s": 10 ** 400}}))
    monkeypatch.setattr("sys.argv", ["wsl-time-sync", "compare", str(source), str(source)])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "finite" in captured.err
    assert "Traceback" not in captured.err
    assert not captured.out


def test_analyze_derived_numeric_overflow_is_usage_error(tmp_path, monkeypatch, capsys):
    from pathlib import Path
    payload = json.loads(Path("examples/sample-probe.json").read_text())
    # The input integer is finite as a float, but its derived ppm is not.
    for index, row in enumerate(payload["samples"]):
        row["monotonic_raw_ns"] = index
    payload["samples"][-1]["monotonic_ns"] = 10 ** 308
    source = tmp_path / "overflow.json"
    source.write_text(json.dumps(payload))
    monkeypatch.setattr("sys.argv", ["wsl-time-sync", "analyze", str(source)])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "finite" in captured.err
    assert "Traceback" not in captured.err
    assert not captured.out
