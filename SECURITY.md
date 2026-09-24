# Security Policy

## Supported versions

This is an early-stage engineering side project.

| Version | Security fixes |
|---|---|
| Latest `0.1.x` release | Supported |
| `main` | Best effort |
| Older snapshots | Not supported |

## Reporting a vulnerability

Please use GitHub's **private vulnerability reporting** feature for this
repository when it is available.

If private vulnerability reporting is not available, open a public issue that
contains only a request for a private contact channel. **Do not include exploit
details, credentials, private paths, tokens, or sensitive logs in a public
issue.**

For ordinary bugs that are not security-sensitive, use the normal issue
tracker.

## Scope

Security reports are especially useful for problems involving:

- command execution beyond the documented read-only behavior;
- unsafe handling of file paths or user-supplied output paths;
- accidental collection or disclosure of credentials or private data;
- shell injection or argument-injection behavior;
- unsafe assumptions about elevated privileges;
- behavior that mutates time services, firewall state, WSL configuration, or
  system Python despite the documented read-only/default-safe design.

## Disclosure

Please give maintainers a reasonable opportunity to investigate and publish a
fix before disclosing security-sensitive details publicly.

This project has no guaranteed response-time SLA.
