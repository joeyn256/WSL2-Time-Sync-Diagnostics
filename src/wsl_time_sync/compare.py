from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    lppm = (left.get("full_run") or {}).get("monotonic_vs_raw_ppm")
    rppm = (right.get("full_run") or {}).get("monotonic_vs_raw_ppm")

    result: dict[str, Any] = {
        "left_sample_count": left.get("sample_count"),
        "right_sample_count": right.get("sample_count"),
        "left_monotonic_vs_raw_ppm": lppm,
        "right_monotonic_vs_raw_ppm": rppm,
        "difference_ppm": None,
        "notes": [
            "This comparison is descriptive.",
            "It does not establish a distro ranking unless the two runs used a matched design.",
        ],
    }
    if isinstance(lppm, (int, float)) and isinstance(rppm, (int, float)):
        result["difference_ppm"] = rppm - lppm
    return result


def compare_paths(left_path: str | Path, right_path: str | Path) -> dict[str, Any]:
    return compare_reports(_load(left_path), _load(right_path))
