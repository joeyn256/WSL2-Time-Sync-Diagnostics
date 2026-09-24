from __future__ import annotations

import glob
import os
import platform
import sys
from pathlib import Path
from typing import Any

from .adjtimex import observe_adjtimex
from .utils import read_text, run_readonly


def _os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    text = read_text("/etc/os-release")
    if not text:
        return values
    for line in text.splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def _service_state(unit: str) -> dict[str, Any]:
    active = run_readonly(["systemctl", "is-active", unit])
    enabled = run_readonly(["systemctl", "is-enabled", unit])
    return {
        "unit": unit,
        "active": active["stdout"] or active["stderr"],
        "enabled": enabled["stdout"] or enabled["stderr"],
    }


def collect_diagnosis() -> dict[str, Any]:
    proc_version = read_text("/proc/version") or ""
    wsl_detected = (
        "microsoft" in proc_version.lower()
        or bool(os.environ.get("WSL_INTEROP"))
        or bool(os.environ.get("WSL_DISTRO_NAME"))
    )

    ptp_devices = []
    for path in sorted(glob.glob("/sys/class/ptp/ptp*")):
        name = Path(path).name
        ptp_devices.append(
            {
                "name": name,
                "clock_name": read_text(Path(path) / "clock_name"),
                "dev_path": f"/dev/{name}" if Path(f"/dev/{name}").exists() else None,
            }
        )

    return {
        "schema_version": 1,
        "mode": "read_only",
        "wsl_detected": wsl_detected,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "wsl": {
            "distro_name_env": os.environ.get("WSL_DISTRO_NAME"),
            "interop_present": bool(os.environ.get("WSL_INTEROP")),
            "proc_version": proc_version,
        },
        "ubuntu": _os_release(),
        "boot_id": read_text("/proc/sys/kernel/random/boot_id"),
        "clocksource": read_text(
            "/sys/devices/system/clocksource/clocksource0/current_clocksource"
        ),
        "available_clocksources": read_text(
            "/sys/devices/system/clocksource/clocksource0/available_clocksource"
        ),
        "services": [
            _service_state("systemd-timesyncd.service"),
            _service_state("chrony.service"),
            _service_state("chronyd.service"),
        ],
        "ptp": ptp_devices,
        "adjtimex": observe_adjtimex(),
        "python_executable": sys.executable,
        "notes": [
            "Presence of a service or PTP device does not identify the active clock writer.",
            "This command performs no service mutation, package installation, or elevation.",
        ],
    }
