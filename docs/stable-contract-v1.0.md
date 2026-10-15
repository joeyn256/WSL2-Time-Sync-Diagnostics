# Stable public contract — v1.0

WSL2 Time Sync Diagnostics v1.0.0 is the first stable release line.

This page defines the compatibility surface that the project intends to preserve throughout the 1.x series. It does **not** turn finite timing observations into universal guarantees and does not broaden the scientific claims in the evidence pages.

## Stable command surface

The installed command is:

```text
wsl-time-sync
```

The stable 1.x command names are:

- `diagnose`
- `probe`
- `analyze`
- `settle-check`
- `compare`
- `python-check`

The global `--version` and `--help` interfaces are also part of the stable command surface.

Removing or renaming one of these commands, changing a required positional argument incompatibly, or changing the documented meaning of an existing option is a breaking change and requires a new major release.

Additive optional flags may be introduced in a 1.x minor release when existing invocations retain their meaning.

## Stable data and method identifiers

Package release numbers and measurement-schema identifiers are intentionally separate.

v1.0.0 keeps these established identifiers:

```text
probe schema_version = 2
analysis schema_version = 2
acquisition = raw_bracket_v1
analysis method = fixed_window_interval_v2
```

The documented meanings of existing required fields and classification values are stable for the 1.x line.

Additive fields may appear in a 1.x minor release when old fields keep their meaning and old valid inputs remain readable. Removing a required field, reusing a field name with incompatible semantics, or changing an established classification meaning requires a new major release.

The analyzer continues to accept the documented legacy v0.1 probe input format. Removing that compatibility is a breaking change.

## Classification vocabulary

The analysis vocabulary remains:

- `WITHIN`
- `OUTSIDE`
- `INDETERMINATE`

The finite kernel-state observation vocabulary remains:

- `WITHIN_CONFIGURED_BAND`
- `ANOMALY_OBSERVED`
- `INDETERMINATE`

These labels describe the bounded evidence collected under the recorded settings. They are not universal clock-health certifications.

## Exit and error behavior

A completed command can exit successfully even when its JSON reports an anomaly or unavailable/indeterminate observation. Consumers must inspect the structured result rather than treating process exit 0 as a timing pass.

Invalid command-line input and supported file/input errors continue to be usage failures rather than silent nominal results.

## Read-only default

The public v1.0 CLI is read-only with respect to system time configuration.

Normal CLI operation does not:

- stop or start time services;
- change the system clock;
- change WSL configuration;
- alter firewall rules;
- modify Windows Time registry or policy;
- install packages into the system interpreter.

A future mutating experiment must remain clearly separated from the default diagnostic CLI. Adding a hidden mutation to an existing read-only command would violate the 1.x contract.

## Runtime and platform policy

The package requires Python 3.12 or newer and is continuously tested on the Python versions declared in CI.

The runtime package remains standard-library-only at v1.0.0.

The Linux clock reader has explicit platform/ABI limits documented in the CLI/schema and limitations pages. Unsupported environments remain structured unavailability rather than guessed binary layouts.

## Scientific interpretation is not an API guarantee

The stable software interface does not convert this repository into a universal benchmark.

The evidence remains bounded by:

- the clocks actually compared;
- the host and WSL versions recorded;
- observation duration and cadence;
- the configured thresholds;
- whether the result is guest-side or host-referenced;
- the explicit limitations pages.

In particular, v1.0 does not claim a synchronized-host reproduction of the Ubuntu 24.04 pathology. The v0.7 synchronized-host campaign did not launch because its Windows-host admission prerequisite was not achieved.

## Semantic versioning policy

For the 1.x line:

- **patch** releases fix bugs, documentation, tests, or packaging without intentionally changing the stable contract;
- **minor** releases may add backwards-compatible commands, options, fields, or diagnostics;
- **major** releases are required for intentional incompatible changes to the command/data contract above.

Security or correctness emergencies may require retiring unsafe behavior. Any such exception will be called out explicitly in the release notes.

## Related references

- [CLI and schema reference](cli-schema.md)
- [Methodology](methodology.md)
- [Limitations](limitations.md)
- [Reproducibility guide](reproducibility.md)
- [v0.7 synchronized-host closure](v0.7-synchronized-host-rerun.md)
