# Release Checklist

Before publishing a preview or stable release:

- [ ] Confirm `pyproject.toml`, `src/wsl_time_sync/__init__.py`, `MANIFEST.json`, and `RELEASE_MANIFEST.json` agree on the intended release version.
- [ ] Confirm the README title, CI badge, repository links, issue links, and clone/path examples use the current repository identity.
- [ ] Read the public README and all docs once in rendered Markdown.
- [ ] Render each public SVG at normal size and verify the reduced-motion/static state is coherent.
- [ ] Confirm no private paths, usernames, boot IDs, tokens, credentials, or unrelated project data remain.
- [ ] Run the complete test suite.
- [ ] Build a normal wheel, install it, and verify the distribution name/version plus `wsl_time_sync.__version__` before running `wsl-time-sync --help`.
- [ ] Run the semantic CLI smoke used by CI.
- [ ] Run `wsl-time-sync diagnose` inside WSL2 and inspect the output before sharing it.
- [ ] Confirm example JSON remains synthetic.
- [ ] Run `tests/test_public_evidence.py` and confirm the hero values, redactions, and same-host evidence still agree.
- [ ] Confirm no mutating command was added to a default CLI path.
- [ ] Confirm current GitHub Actions is green on both supported Python matrix entries at the exact release-candidate commit.
- [ ] Confirm schema/method version labels are not being confused with the package release number.
- [ ] Enable GitHub secret scanning / push protection where available.
- [ ] Enable Dependabot alerts.
- [ ] Enable private vulnerability reporting if desired.
- [ ] Create the release tag only after the exact candidate passes CI.
- [ ] Close the implementation issue only after the stable content is merged.

For v0.6.1, v0.6.0 is the prior normal public release; `0.2.0`, `0.3.0`, `0.3.1`, and `0.5.0` remain development-lineage labels rather than public tags. v0.6.1 is a documentation/presentation patch with no runtime/schema change. The official stable v1.0.0 release remains deferred.
