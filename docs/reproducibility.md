# Reproducibility guide

This guide is the shortest supported path from a fresh WSL2 Linux environment to a shareable diagnostic bundle.

It intentionally uses the public read-only CLI. The private Windows-host admission machinery used during the v0.7 investigation is not required.

## 1. Record the environment first

Before changing time services or WSL settings, capture the surrounding versions.

From Windows PowerShell:

```powershell
wsl.exe --version
wsl.exe --list --verbose
```

Inside the target distro:

```bash
uname -a
python3 --version
cat /etc/os-release
```

Record whether the distro was freshly started, resumed, or already running. Do not infer a clean boot from elapsed time alone.

## 2. Clone into the Linux filesystem

For Linux-side tools, prefer a path under the distro's Linux filesystem rather than `/mnt/c`.

```bash
git clone https://github.com/joeyn256/WSL2-Time-Sync-Diagnostics.git
cd WSL2-Time-Sync-Diagnostics
```

For an exact published release:

```bash
git checkout v1.0.0
```

## 3. Create an isolated Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
wsl-time-sync --version
```

The runtime package is standard-library-only.

## 4. Capture the read-only diagnosis

```bash
wsl-time-sync diagnose --output diagnose.json
```

Inspect the output rather than assuming every clock/kernel field is available on every ABI.

## 5. Run a bounded probe

A useful first screen is:

```bash
wsl-time-sync probe --duration 60 --cadence 1 --output probe.json
```

Longer captures can be useful, but a longer run is not automatically a stronger causal experiment.

## 6. Analyze fixed windows

```bash
wsl-time-sync analyze probe.json \
  --window 10 \
  --rate-band-ppm 100 \
  --output analysis.json
```

Keep the settings with the result. Thresholds are part of the question being asked, not universal definitions of correctness.

## 7. Observe finite kernel state when useful

```bash
wsl-time-sync settle-check \
  --duration 30 \
  --cadence 1 \
  --output settle.json
```

A within-band settle result concerns the sampled kernel fields under that policy. It does not certify future benchmark readiness or host agreement.

## 8. Compare compatible analyses

```bash
wsl-time-sync compare analysis-before.json analysis-after.json --output comparison.json
```

Read the `comparability` field. The tool deliberately refuses to turn unlike methods or missing context into a confident numerical comparison.

## 9. Preserve provenance

Keep at least:

- the exact repository tag or commit;
- `wsl.exe --version`;
- Windows build when available;
- distro and Linux kernel versions;
- Python version;
- `diagnose.json`;
- raw `probe.json`;
- `analysis.json`;
- any `settle.json` or comparison output;
- the command lines and thresholds used.

For public sharing, redact usernames, private paths, machine identifiers, boot identifiers when they are not scientifically necessary, credentials, tokens, and unrelated project data.

Generate hashes after the final redacted/public files are frozen:

```bash
sha256sum diagnose.json probe.json analysis.json settle.json 2>/dev/null
```

## 10. Interpret within the evidence boundary

A guest-side MONOTONIC-versus-MONOTONIC_RAW result measures guest clock discipline. It does not by itself establish absolute accuracy against Windows, UTC, or an external NTP source.

A host admission failure is not a guest scientific result.

The v0.7 synchronized-host campaign is an example: the guest campaign never launched because its Windows-host prerequisite was not satisfied.

## Fresh-environment release check

Before a stable project release, the project also requires:

1. a clean virtual environment;
2. wheel build and installation;
3. distribution/import version agreement;
4. `wsl-time-sync --version` and `--help`;
5. the semantic CLI smoke suite;
6. the complete automated test suite on the supported CI matrix.

See [RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md).
