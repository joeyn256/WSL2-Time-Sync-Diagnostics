"""Synthetic kernel states; no recorded/private evidence bytes are used."""

import ctypes
import errno
import platform
from types import SimpleNamespace

import pytest

from wsl_time_sync import adjtimex, diagnose


class FakeAdjtimex:
    def __init__(self, *, tick=10000, freq=12 * 65536, status=0, code=0):
        self.tick = tick
        self.freq = freq
        self.status = status
        self.code = code
        self.calls = 0

    def __call__(self, pointer):
        assert self.argtypes == [ctypes.POINTER(adjtimex._Timex)]
        assert self.restype is ctypes.c_int
        state = ctypes.cast(pointer, ctypes.POINTER(adjtimex._Timex)).contents
        assert bytes(state) == b"\0" * ctypes.sizeof(state)
        assert state.modes == 0
        self.calls += 1
        state.tick = self.tick
        state.freq = self.freq
        state.status = self.status
        state.offset = -125
        state.maxerror = 3000
        state.esterror = 40
        state.time.tv_sec = 12345
        state.time.tv_usec = 678
        if self.code == -1:
            ctypes.set_errno(errno.EPERM)
        return self.code


def install_fake(monkeypatch, reader):
    monkeypatch.setattr(adjtimex, "validate_abi", lambda: {"validated": True})
    def fake_cdll(name, *, use_errno):
        assert name is None
        assert use_errno is True
        return SimpleNamespace(adjtimex=reader)
    monkeypatch.setattr(adjtimex.ctypes, "CDLL", fake_cdll)


def test_native_verified_layout():
    validation = adjtimex.validate_abi()
    if platform.system() == "Linux" and platform.machine() == "x86_64":
        assert validation["validated"]
        assert validation["actual"]["timex_size"] == 208
        assert validation["actual"]["timex_alignment"] == 8
        assert validation["actual"]["field_offsets"]["tick"] == 88
        assert validation["actual"]["field_offsets"]["tai"] == 160
    else:
        assert not validation["validated"]


@pytest.mark.parametrize("attribute,value,failed", [
    ("system", "Windows", "system"),
    ("machine", "aarch64", "machine"),
])
def test_platform_checks_fail_closed_before_loading_libc(monkeypatch, attribute, value, failed):
    monkeypatch.setattr(adjtimex.platform, attribute, lambda: value)
    monkeypatch.setattr(adjtimex.ctypes, "CDLL", lambda *a, **k: pytest.fail("loaded libc"))
    result = adjtimex.observe_adjtimex()
    assert not result["available"]
    assert result["unavailable_reason"] == "unsupported_abi"
    assert failed in result["abi"]["failed_checks"]
    assert result["raw"] is None


def test_endian_and_field_offsets_are_validated(monkeypatch):
    monkeypatch.setattr(adjtimex.sys, "byteorder", "big")
    offsets = dict(adjtimex._EXPECTED_OFFSETS, tick=80)
    monkeypatch.setattr(adjtimex, "_EXPECTED_OFFSETS", offsets)
    validation = adjtimex.validate_abi()
    assert "byteorder" in validation["failed_checks"]
    assert "field_offsets" in validation["failed_checks"]


def test_c_type_sizes_and_structure_alignment_are_validated(monkeypatch):
    original_sizeof = ctypes.sizeof
    original_alignment = ctypes.alignment
    monkeypatch.setattr(adjtimex.ctypes, "sizeof", lambda value: (
        4 if value is ctypes.c_long else original_sizeof(value)))
    monkeypatch.setattr(adjtimex.ctypes, "alignment", lambda value: (
        4 if value is adjtimex._Timex else original_alignment(value)))
    validation = adjtimex.validate_abi()
    assert "long_size" in validation["failed_checks"]
    assert "timex_alignment" in validation["failed_checks"]


@pytest.mark.parametrize("status,resolution", [(0, "microseconds"), (0x2000, "nanoseconds")])
def test_snapshot_readonly_layout_units_and_raw_fields(monkeypatch, status, resolution):
    reader = FakeAdjtimex(status=status)
    install_fake(monkeypatch, reader)
    result = adjtimex.observe_adjtimex()
    assert reader.calls == 1
    assert result["available"]
    assert result["modes"] == result["raw"]["modes"] == 0
    assert result["mode"] == "read_only"
    assert result["freq_ppm"] == 12
    assert result["raw"]["maxerror"] == 3000
    assert result["raw"]["esterror"] == 40
    assert result["raw"]["offset"] == -125
    assert result["raw"]["time"] == {"tv_sec": 12345, "tv_usec": 678}
    assert result["return_state"] == {"code": 0, "name": "TIME_OK"}
    for field in ("offset", "jitter", "time.tv_usec"):
        assert result["units"][field] == resolution
    assert result["units"]["maxerror"] == "microseconds"


def test_time_error_is_observed_clock_state_not_syscall_failure(monkeypatch):
    reader = FakeAdjtimex(tick=10009, freq=-450 * 65536, status=0x40, code=5)
    install_fake(monkeypatch, reader)
    result = adjtimex.observe_adjtimex()
    assert result["available"]
    assert result["return_state"] == {"code": 5, "name": "TIME_ERROR"}
    assert result["raw"]["tick"] == 10009
    assert result["freq_ppm"] == -450


def test_failed_syscall_is_structured_unavailable(monkeypatch):
    reader = FakeAdjtimex(code=-1)
    install_fake(monkeypatch, reader)
    result = adjtimex.observe_adjtimex()
    assert not result["available"]
    assert result["unavailable_reason"] == "adjtimex_call_failed"
    assert result["errno"] == errno.EPERM
    assert result["raw"] is None
    assert result["return_state"] is None


def test_missing_libc_symbol_is_structured_unavailable(monkeypatch):
    monkeypatch.setattr(adjtimex, "validate_abi", lambda: {"validated": True})
    monkeypatch.setattr(adjtimex.ctypes, "CDLL", lambda *a, **k: object())
    result = adjtimex.observe_adjtimex()
    assert not result["available"]
    assert result["unavailable_reason"] == "libc_adjtimex_unavailable"


def test_diagnose_adds_snapshot_without_service_writes(monkeypatch):
    snapshot = {"available": False, "unavailable_reason": "unsupported_abi"}
    commands = []
    monkeypatch.setattr(diagnose, "observe_adjtimex", lambda: snapshot)
    monkeypatch.setattr(diagnose, "read_text", lambda path: None)
    monkeypatch.setattr(diagnose.glob, "glob", lambda pattern: [])
    def run_command(command):
        commands.append(command)
        return {"stdout": "unknown", "stderr": ""}
    monkeypatch.setattr(diagnose, "run_readonly", run_command)
    result = diagnose.collect_diagnosis()
    assert result["schema_version"] == 1  # Additive v0.1 diagnosis compatibility.
    assert result["adjtimex"] == snapshot
    assert len(commands) == 6
    assert all(cmd[:2] in (["systemctl", "is-active"], ["systemctl", "is-enabled"])
               for cmd in commands)
