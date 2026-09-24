from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "2026-09-24-same-host-screens"
LEFT = EVIDENCE / "ubuntu-24.04-timesyncd-enabled"
RIGHT = EVIDENCE / "ubuntu-26.04-fresh-default"
HERO = ROOT / "docs" / "assets" / "three-model-timing-comparison.svg"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _analysis(folder: Path) -> dict:
    return _load(folder / "analysis-window30-band1000.json")


def test_same_host_2404_published_measurements_are_committed() -> None:
    report = _analysis(LEFT)
    assert report["classification"] == "OUTSIDE"
    assert report["coverage"]["collection_completion_verified"] is True
    assert report["coverage"]["complete_window_count"] == 10
    assert report["coverage"]["partial_window_count"] == 0
    assert report["large_realtime_minus_raw_changes"] == 8
    assert report["full_run"]["rate_interval_ppm"] == pytest.approx(
        [-48010.755673874926, -48010.74025787105]
    )
    expected = [
        [-55088.61213999473, -55088.44882400224],
        [-54399.437838790654, -54399.233129189524],
        [-49693.79932044417, -49693.639564004814],
        [-52680.920257298654, -52680.77753541252],
    ]
    for window, interval in zip(report["windows"][:4], expected, strict=True):
        assert window["classification"] == "OUTSIDE"
        assert window["rate_interval_ppm"] == pytest.approx(interval)


def test_same_host_2604_published_measurements_are_committed() -> None:
    report = _analysis(RIGHT)
    assert report["classification"] == "WITHIN"
    assert report["coverage"]["collection_completion_verified"] is True
    assert report["coverage"]["complete_window_count"] == 10
    assert report["coverage"]["partial_window_count"] == 0
    assert report["large_realtime_minus_raw_changes"] == 0
    assert report["full_run"]["rate_interval_ppm"] == pytest.approx(
        [-0.5345689622982942, -0.5114890189060929]
    )
    expected = [
        [-0.5697894897580369, -0.2738950288234865],
        [-0.6577732767838056, -0.4226710135562604],
        [-0.6671329809759307, -0.4914998267299277],
        [-0.4639279402328852, -0.2695969183634381],
    ]
    for window, interval in zip(report["windows"][:4], expected, strict=True):
        assert window["classification"] == "WITHIN"
        assert window["rate_interval_ppm"] == pytest.approx(interval)


def test_committed_environment_snapshots_keep_private_fields_redacted() -> None:
    snapshots = list(LEFT.glob("diagnose*.json")) + list(RIGHT.glob("diagnose*.json"))
    assert snapshots
    for path in snapshots:
        report = _load(path)
        assert report["boot_id"].startswith("[redacted:")
        assert report["python_executable"].startswith("[redacted:")

    for path in list(LEFT.glob("*.log")) + list(RIGHT.glob("*.log")):
        text = path.read_text(encoding="utf-8")
        assert "/home/" not in text
        assert "C:\\Users\\" not in text
        assert "/mnt/c/Users/" not in text


def test_three_model_visual_is_bound_to_committed_evidence() -> None:
    root = ET.parse(HERO).getroot()
    text = " ".join(part.strip() for part in root.itertext() if part.strip())

    assert "two documented control paths" in text
    assert "one default control path" in text
    assert "two default writers" not in text
    assert "one writer ·" not in text

    assert "first 4 windows: −55,089 to −49,693 ppm" in text
    assert "10 windows: −0.73 to −0.27 ppm" in text
    assert "mean 0–60 s ≈ −54.7k ppm*" in text
    assert "mean 0–60 s ≈ −0.48 ppm*" in text
    assert "mean 0–90 s ≈ +8.9k ppm*" in text
    assert "run +6,661.607 to +6,676.217 ppm" in text
    assert text.count("collecting first 30 s window…") == 3

    svg = HERO.read_text(encoding="utf-8")
    assert "@keyframes k30{0%,16.64%{opacity:0}16.67%,100%{opacity:1}}" in svg
    assert "@media (prefers-reduced-motion:reduce){.a{animation:none !important}}" in svg
