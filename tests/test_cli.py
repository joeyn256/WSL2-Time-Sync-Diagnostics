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
