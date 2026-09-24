from __future__ import annotations

import math


def finite_json_integer(value: str) -> int:
    """Reject JSON integers that cannot enter finite numeric calculations."""
    number = int(value)
    try:
        finite = math.isfinite(number)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("JSON integer is outside the supported finite numeric range")
    return number


def positive_seconds(value: float, name: str) -> int:
    """Convert finite positive seconds to integer ns, rejecting sub-ns values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite positive number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value <= 0:
        raise ValueError(f"{name} must be finite and > 0")
    try:
        ns = int(value * 1_000_000_000)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} is out of range") from exc
    if ns < 1:
        raise ValueError(f"{name} must be at least one nanosecond")
    return ns
