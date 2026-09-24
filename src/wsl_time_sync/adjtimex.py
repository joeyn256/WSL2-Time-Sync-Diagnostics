"""Read-only Linux kernel clock state for one explicitly verified native ABI.

Layout basis: Linux UAPI ``struct timex`` and the Linux adjtimex(2) manual.
Only Linux x86-64 LP64 little-endian layouts are accepted. No historical
controller or private evidence is used by this implementation.
"""

from __future__ import annotations

import ctypes
import os
import platform
import sys
from typing import Any


class _Timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]


class _Timex(ctypes.Structure):
    _fields_ = [
        ("modes", ctypes.c_uint),
        ("offset", ctypes.c_long),
        ("freq", ctypes.c_long),
        ("maxerror", ctypes.c_long),
        ("esterror", ctypes.c_long),
        ("status", ctypes.c_int),
        ("constant", ctypes.c_long),
        ("precision", ctypes.c_long),
        ("tolerance", ctypes.c_long),
        ("time", _Timeval),
        ("tick", ctypes.c_long),
        ("ppsfreq", ctypes.c_long),
        ("jitter", ctypes.c_long),
        ("shift", ctypes.c_int),
        ("stabil", ctypes.c_long),
        ("jitcnt", ctypes.c_long),
        ("calcnt", ctypes.c_long),
        ("errcnt", ctypes.c_long),
        ("stbcnt", ctypes.c_long),
        ("tai", ctypes.c_int),
        ("_padding", ctypes.c_int * 11),
    ]


_EXPECTED_OFFSETS = {
    "modes": 0, "offset": 8, "freq": 16, "maxerror": 24, "esterror": 32,
    "status": 40, "constant": 48, "precision": 56, "tolerance": 64,
    "time": 72, "tick": 88, "ppsfreq": 96, "jitter": 104, "shift": 112,
    "stabil": 120, "jitcnt": 128, "calcnt": 136, "errcnt": 144,
    "stbcnt": 152, "tai": 160, "_padding": 164,
}
_STATES = {
    0: "TIME_OK", 1: "TIME_INS", 2: "TIME_DEL", 3: "TIME_OOP",
    4: "TIME_WAIT", 5: "TIME_ERROR",
}
_STA_NANO = 0x2000


def validate_abi() -> dict[str, Any]:
    """Return the actual layout and failures; never infer an unfamiliar ABI."""
    actual = {
        "system": platform.system(),
        "machine": platform.machine().lower(),
        "byteorder": sys.byteorder,
        "int_size": ctypes.sizeof(ctypes.c_int),
        "uint_size": ctypes.sizeof(ctypes.c_uint),
        "long_size": ctypes.sizeof(ctypes.c_long),
        "pointer_size": ctypes.sizeof(ctypes.c_void_p),
        "timex_size": ctypes.sizeof(_Timex),
        "timex_alignment": ctypes.alignment(_Timex),
        "timeval_size": ctypes.sizeof(_Timeval),
        "timeval_alignment": ctypes.alignment(_Timeval),
        "timeval_offsets": {name: getattr(_Timeval, name).offset
                            for name in ("tv_sec", "tv_usec")},
        "field_offsets": {name: getattr(_Timex, name).offset
                          for name in _EXPECTED_OFFSETS},
    }
    expected = {
        "system": "Linux", "byteorder": "little", "int_size": 4,
        "uint_size": 4, "long_size": 8, "pointer_size": 8,
        "timex_size": 208, "timex_alignment": 8,
        "timeval_size": 16, "timeval_alignment": 8,
        "timeval_offsets": {"tv_sec": 0, "tv_usec": 8},
        "field_offsets": _EXPECTED_OFFSETS,
    }
    failures = [key for key, value in expected.items() if actual[key] != value]
    if actual["machine"] not in ("x86_64", "amd64"):
        failures.append("machine")
    return {
        "name": "linux-x86_64-lp64-le",
        "validated": not failures,
        "actual": actual,
        "failed_checks": failures,
    }


def observe_adjtimex() -> dict[str, Any]:
    """Call libc adjtimex with a fresh zeroed structure and modes=0 only.

    TIME_ERROR is a returned clock state, not a failed system call. The
    snapshot does not identify a clock writer or prove that no slew remains.
    """
    abi = validate_abi()
    result: dict[str, Any] = {
        "available": False,
        "mode": "read_only",
        "modes": 0,
        "abi": abi,
        "raw": None,
        "freq_ppm": None,
        "return_state": None,
        "notes": [
            "A snapshot cannot prove that a pending slew is absent.",
            "Kernel state does not identify the active clock writer or host agreement.",
        ],
    }
    if not abi["validated"]:
        result["unavailable_reason"] = "unsupported_abi"
        return result
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        reader = libc.adjtimex
        reader.argtypes = [ctypes.POINTER(_Timex)]
        reader.restype = ctypes.c_int
    except (AttributeError, OSError) as exc:
        result.update(unavailable_reason="libc_adjtimex_unavailable", detail=str(exc))
        return result

    state = _Timex()  # ctypes initializes every byte, including padding, to zero.
    state.modes = 0  # No caller-supplied mode or write-capable API is exposed.
    ctypes.set_errno(0)
    try:
        return_code = reader(ctypes.byref(state))
    except (OSError, ctypes.ArgumentError) as exc:
        result.update(unavailable_reason="adjtimex_call_failed", detail=str(exc))
        return result
    if return_code < 0:
        error = ctypes.get_errno()
        result.update(unavailable_reason="adjtimex_call_failed", errno=error,
                      detail=os.strerror(error))
        return result

    raw = {name: int(getattr(state, name)) for name in _EXPECTED_OFFSETS
           if name not in ("time", "_padding")}
    raw["time"] = {"tv_sec": int(state.time.tv_sec),
                   "tv_usec": int(state.time.tv_usec)}
    resolution = "nanoseconds" if state.status & _STA_NANO else "microseconds"
    result.update(
        available=True,
        raw=raw,
        freq_ppm=state.freq / 65536.0,
        return_state={"code": return_code, "name": _STATES.get(return_code, "UNKNOWN")},
        units={
            "freq": "scaled_ppm_65536", "ppsfreq": "scaled_ppm_65536",
            "stabil": "scaled_ppm_65536", "tick": "microseconds",
            "maxerror": "microseconds", "esterror": "microseconds",
            "precision": "microseconds", "offset": resolution,
            "jitter": resolution, "time.tv_usec": resolution,
            "time.tv_sec": "seconds", "tai": "seconds",
        },
    )
    return result
