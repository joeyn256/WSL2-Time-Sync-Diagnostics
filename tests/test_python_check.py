from wsl_time_sync.python_check import _requirement_name


def test_requirement_name_simple():
    assert _requirement_name("numpy>=2") == "numpy"


def test_requirement_name_skips_comments():
    assert _requirement_name("# numpy") is None


def test_requirement_name_skips_nested_requirements():
    assert _requirement_name("-r base.txt") is None
