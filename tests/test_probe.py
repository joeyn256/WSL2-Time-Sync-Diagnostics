from wsl_time_sync.probe import run_probe


def test_probe_collects_samples_without_mutation():
    result = run_probe(duration_s=0.01, cadence_s=0.005)
    assert result["mode"] == "read_only"
    assert len(result["samples"]) >= 2
    assert result["samples"][0]["index"] == 0
