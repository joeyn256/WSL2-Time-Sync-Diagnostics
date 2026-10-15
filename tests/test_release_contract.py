from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path
import tomllib

import wsl_time_sync


ROOT = Path(__file__).resolve().parents[1]


def test_stable_release_metadata_is_consistent() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project_version = tomllib.load(handle)["project"]["version"]

    publication = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    release = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))

    assert project_version == "1.0.0"
    assert version("wsl2-time-sync-diagnostics") == project_version
    assert wsl_time_sync.__version__ == project_version
    assert publication["version"] == f"public-v{project_version}"
    assert release["release"] == project_version
    assert release["status"] == "stable-public-release"


def test_v1_contract_freezes_existing_identifiers() -> None:
    release = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    contract = release["stable_public_contract"]

    assert contract["cli"] == "wsl-time-sync"
    assert contract["commands"] == [
        "diagnose",
        "probe",
        "analyze",
        "settle-check",
        "compare",
        "python-check",
    ]
    assert contract["probe_schema"] == 2
    assert contract["analysis_schema"] == 2
    assert contract["acquisition"] == "raw_bracket_v1"
    assert contract["analysis_method"] == "fixed_window_interval_v2"
    assert contract["read_only_default"] is True
    assert contract["classifications"] == ["WITHIN", "OUTSIDE", "INDETERMINATE"]


def test_stable_docs_and_release_workflow_are_present() -> None:
    stable = (ROOT / "docs" / "stable-contract-v1.0.md").read_text(encoding="utf-8")
    reproducibility = (ROOT / "docs" / "reproducibility.md").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "first stable release line" in stable
    assert "Read-only default" in stable
    assert "wsl-time-sync probe" in reproducibility
    assert "Latest `1.x` release" in security
    assert 'tags:' in workflow
    assert '"v*"' in workflow
    assert "softprops/action-gh-release@v2" in workflow


def test_v07_closure_remains_a_non_launch_result() -> None:
    closure = (ROOT / "docs" / "v0.7-synchronized-host-rerun.md").read_text(encoding="utf-8")
    assert "scientific launches consumed: **0 / 8**" in closure
    assert "Seq 2 was never opened" in closure
    assert "formal host-admission observation remained **UNUSED**" in closure
