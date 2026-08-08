# Security policy

## Supported versions

Security fixes are applied to the latest released minor version. Older releases
may receive a fix when the change can be backported safely.

| Version | Support |
|---|---|
| 1.3.x | Supported after release |
| 1.2.x | Critical fixes during the v1.3 transition |
| < 1.2 | Not supported |

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting flow from the repository's
Security tab. If that is unavailable, email the maintainer address published in
`pyproject.toml` with the subject `AutoCron security report`.

Include the affected version, operating system, a minimal reproduction, impact,
and any suggested mitigation. Do not open a public issue until a fix or disclosure
plan is available. An initial acknowledgement should arrive within five business
days.

## Security boundaries

### Subprocess execution is not a sandbox

AutoCron can launch a Python script in a separate process, cap output, terminate
process trees, apply selected resource limits, and reduce inherited environment
variables. These controls improve operational isolation. They do not remove the
child's operating-system identity, filesystem permissions, or network access.

Run hostile or multi-tenant code in a container, virtual machine, or restricted
account configured as a real security boundary.

### Secrets

- Do not commit SMTP passwords, API keys, or tokens.
- Task persistence intentionally omits notification passwords.
- Provide credentials at runtime through an appropriate secret store.
- Remember that child processes may inherit explicitly allowed environment
  variables.

### Persistent data

Protect the SQLite database, logs, exports, and analytics files with suitable
filesystem permissions. They can contain script paths, task names, errors, and
execution history. Back up persistent state and verify database recovery.

### Operating-system adapters

Windows Task Scheduler and POSIX cron adapters change user-level system state.
Validate task names and paths, use least privilege, and review generated commands
before enabling system integration in production. The normal test suite mocks
these adapters; real system tests require explicit opt-in.

### Notifications

SMTP uses TLS when configured, but server authenticity and credential handling
remain deployment responsibilities. Notification messages may include task names
or error summaries, so avoid including sensitive values in exceptions.

## Security checks

CI performs dependency, static-analysis, packaging, and test checks. A passing
scanner is useful evidence, not a guarantee that the project has no
vulnerabilities. Security-sensitive scheduling and subprocess behavior is also
covered by behavioral tests.
