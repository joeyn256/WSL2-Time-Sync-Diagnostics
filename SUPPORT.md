# Support

WSL2 Time Sync Diagnostics is a small open-source engineering project with a stable 1.x software contract and no guaranteed response-time SLA.

## Bug reports

Use the GitHub issue tracker for reproducible software bugs.

For CLI or analysis bugs, include:

- the exact package version from `wsl-time-sync --version`;
- Python version;
- the command that was run;
- the smallest synthetic or redacted input that reproduces the problem;
- expected behavior;
- observed behavior.

Do not attach private evidence roots, credentials, tokens, or unrelated project data.

## Timing observations

A report about live WSL timing should also include, when available:

- Windows build;
- `wsl.exe --version`;
- distro and Linux kernel version;
- whether the distro was freshly started or already running;
- `diagnose.json`;
- the raw probe and analysis outputs;
- the exact thresholds/window lengths used.

Please distinguish guest-side observations from host-referenced observations.

A host admission failure should not be reported as a guest scientific result.

## Security reports

Do not put security-sensitive details into an ordinary public issue. Follow [SECURITY.md](SECURITY.md).

## Stable compatibility

For intentional interface changes, consult [docs/stable-contract-v1.0.md](docs/stable-contract-v1.0.md).

Breaking changes to the stable command/data contract require a future major release.

## Reproduction help

Start with [docs/reproducibility.md](docs/reproducibility.md). If the documented clean workflow fails, open an issue with the minimum redacted evidence necessary to reproduce it.
