from wsl_time_sync.compare import compare_reports


def test_compare_is_descriptive():
    left = {"sample_count": 31, "full_run": {"monotonic_vs_raw_ppm": -0.5}}
    right = {"sample_count": 31, "full_run": {"monotonic_vs_raw_ppm": 0.25}}
    result = compare_reports(left, right)
    assert result["difference_ppm"] == 0.75
    assert "does not establish a distro ranking" in result["notes"][1]
