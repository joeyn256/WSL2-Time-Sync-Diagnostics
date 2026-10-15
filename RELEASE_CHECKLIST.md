# Release Checklist

Before publishing a stable 1.x release:

- [ ] Confirm `pyproject.toml`, installed distribution metadata, `MANIFEST.json`, and `RELEASE_MANIFEST.json` agree on the intended release version.
- [ ] Confirm `wsl_time_sync.__version__` resolves to the installed distribution version and `wsl-time-sync --version` reports it.
- [ ] Confirm the README title, CI badge, repository links, issue links, and clone/path examples use the current repository identity.
- [ ] Read the public README and all changed docs once in rendered Markdown.
- [ ] Render changed public SVGs at normal size and verify the reduced-motion/static state when visual assets changed.
- [ ] Confirm no private paths, usernames, boot IDs, tokens, credentials, or unrelated project data remain.
- [ ] Run the complete test suite.
- [ ] Build a normal wheel, install it into a clean environment, and verify the distribution/import/CLI versions.
- [ ] Run the semantic CLI smoke used by CI.
- [ ] Run `wsl-time-sync diagnose` inside WSL2 and inspect the output before publishing environment evidence.
- [ ] Confirm example JSON remains synthetic.
- [ ] Run `tests/test_public_evidence.py` and confirm hero values, redactions, and same-host evidence still agree.
- [ ] Run the stable release-contract tests.
- [ ] Confirm no mutating command was added to a default CLI path.
- [ ] Confirm schema/method identifiers remain compatible with [docs/stable-contract-v1.0.md](docs/stable-contract-v1.0.md).
- [ ] Confirm GitHub Actions is green on all supported Python matrix entries at the exact release-candidate commit.
- [ ] Confirm the tag matches `v<pyproject version>`.
- [ ] Confirm the tag-driven release workflow builds and verifies wheel/sdist artifacts.
- [ ] Enable GitHub secret scanning / push protection where available.
- [ ] Enable Dependabot alerts.
- [ ] Enable private vulnerability reporting if desired.
- [ ] Create the stable release tag only after the exact candidate passes CI.

v1.0.0 freezes the first stable public contract. The v0.7.0 synchronized-host closure remains a bounded negative/limited scientific result and does not expand the stable software API.
