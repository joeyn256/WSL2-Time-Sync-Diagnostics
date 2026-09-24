# Release Checklist

Before publishing this repository:

- [ ] Read the public README and all docs once in rendered Markdown.
- [ ] Confirm no private paths, usernames, boot IDs, tokens, or unrelated project data remain.
- [ ] Run `pytest`.
- [ ] Run `wsl-time-sync --help`.
- [ ] Run `wsl-time-sync diagnose` inside WSL2 and inspect the output before sharing it.
- [ ] Confirm example JSON remains synthetic.
- [ ] Confirm no mutating command was added to a default CLI path.
- [ ] Enable GitHub secret scanning / push protection where available.
- [ ] Enable Dependabot alerts.
- [ ] Enable private vulnerability reporting if desired.
- [ ] Create the first release only after CI is green.
