# Changelog

## 1.0.0 — 2026-10-15

### Stable contract

- Declares the first stable 1.x command/data compatibility contract.
- Keeps the public CLI read-only by default.
- Freezes the established command names, classification vocabulary, `schema_version: 2`, `raw_bracket_v1`, and `fixed_window_interval_v2` semantics for the 1.x line.
- Adds `wsl-time-sync --version`.
- Derives `wsl_time_sync.__version__` from installed distribution metadata instead of maintaining a second hardcoded version.
- Makes CI wheel/version checks release-version agnostic.
- Adds tag-driven wheel/sdist release packaging.
- Adds a fresh-environment reproducibility guide and stable support/security language.
- Adds regression checks for release-manifest and stable-contract consistency.

### Scientific scope

No timing algorithm, threshold, schema identifier, or prior evidence interpretation is changed by the 1.0 release.

The v0.7 synchronized-host campaign remains closed without a guest scientific launch because the Windows host did not satisfy its frozen admission prerequisite.

### Release-engineering note

The originally planned v0.8 reproducibility cleanup and v0.9 release-candidate hardening were folded into the v1.0 release-candidate branch rather than published as separate tags.

## 0.7.0 — 2026-10-15

### Added

- Public closure report for the synchronized-Windows-host rerun effort.
- Sanitized evidence index with retained private-evidence SHA-256 provenance.
- Explicit documentation of the frozen host-admission boundary and terminal scientific accounting.

### Result

The synchronized-host guest campaign was not launched because the Windows host did not reach the frozen synchronization admission state. The final bounded plain-`/resync` correction attempt ended:

```text
FINAL_W32TIME_CORRECTION_FAILED — RESTORATION_PROVEN
```

No Seq 2 was opened, no synchronized-host Ubuntu scientific run was launched, and the formal host-admission observation remained unused.

### Preserved findings

The existing public Ubuntu 24.04, Ubuntu 26.04, historical D4R2, CLI, methodology, and same-host evidence remain unchanged in interpretation.

## 0.6.1

Pinned public tooling baseline preceding the v0.7 synchronized-host closure work.
