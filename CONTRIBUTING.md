# Contributing

Thanks for helping improve this WSL2 timing and environment-selection guide.

## Good contributions

Useful contributions include:

- reproducible WSL2 timing observations;
- fixes to the read-only diagnostic tooling;
- additional synthetic/unit tests;
- corrections to documentation;
- dated Python package-compatibility observations;
- improvements that make evidence boundaries easier to understand.

## Evidence rules

Please distinguish clearly between:

- a historical observation;
- a guest-side measurement;
- a Windows-host-referenced measurement;
- a live qualification;
- an interpretation or hypothesis.

Do not promote correlation into causation.

In particular, contributions should not claim without appropriate evidence
that:

- `systemd-timesyncd` is the sole cause of a timing problem;
- Ubuntu 26.04 universally fixes WSL2 timing;
- `chronyd` is universally preferable;
- Python 3.14 is categorically better than Python 3.12.

## Privacy

Before opening an issue or pull request, remove:

- usernames and home-directory paths;
- machine identifiers;
- boot IDs unless they are synthetic;
- credentials, tokens, cookies, or secrets;
- unrelated project data;
- private evidence roots.

Use synthetic examples when possible.

## Development

Create a virtual environment and install the development extras:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

The runtime package is intentionally standard-library-only.

## Pull requests

Keep changes focused.

For code changes:

1. add or update tests;
2. preserve read-only defaults;
3. avoid hidden retries;
4. document any new collected field;
5. update the relevant guide page if interpretation changes.

For documentation changes, link each material claim to the evidence category it
depends on.

## Mutating experiments

The default public CLI does not stop services, alter the firewall, change WSL
configuration, replace system Python, or install packages.

Do not add such behavior to a default command.

A future mutating experiment should be clearly separated, opt-in, reversible,
and documented with restoration steps.
