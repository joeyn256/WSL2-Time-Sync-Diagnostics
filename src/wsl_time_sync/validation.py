from __future__ import annotations

import math


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
