from __future__ import annotations

import importlib.metadata
import platform
import re
import sys
from pathlib import Path
from typing import Any


_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def installed_versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            result[name.lower()] = dist.version
    return result


def _requirement_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith(("-r ", "--")):
        return None
    match = _REQ_NAME.match(stripped)
    return match.group(1) if match else None


def check_python(requirements_path: str | None = None) -> dict[str, Any]:
    inventory = installed_versions()
    result: dict[str, Any] = {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "implementation": platform.python_implementation(),
        "architecture": platform.machine(),
        "requirements": [],
        "notes": [
            "This command performs no installation and no network access.",
            "Presence of a distribution does not prove application compatibility.",
            "Requirement-name parsing is intentionally simple and is not a dependency resolver.",
        ],
    }

    if requirements_path:
        path = Path(requirements_path)
        for line in path.read_text(encoding="utf-8").splitlines():
            name = _requirement_name(line)
            if not name:
                continue
            result["requirements"].append(
                {
                    "requirement_line": line.strip(),
                    "distribution": name,
                    "installed_version": inventory.get(name.lower()),
                    "installed": name.lower() in inventory,
                }
            )
    return result
