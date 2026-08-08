# Changelog

All notable changes to AutoCron are documented here. The project follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Time-zone aware interval and cron scheduling with DST-safe calculations.
- Explicit overlap policies: `skip`, `allow`, and bounded `queue`.
- Misfire grace periods, coalescing, and execution counters.
- Thread-safe SQLite task/history storage with credential redaction.
- A persistent CLI for scheduling, running, listing, stopping, statistics,
  logs, and dashboard views.
- Portable `AUTOCRON_HOME` and `AUTOCRON_DATABASE` state configuration.
- Windows-safe test isolation, wheel build checks, strict documentation checks,
  and executable demo notebooks.

### Changed

- Reworked the README, API documentation, security guidance, and contributor
  workflow around the `autocron-scheduler` distribution name.
- Persistence files remain compatible with the original `1.0` envelope while
  accepting additive scheduling fields.
- Notifications use task-scoped channels so one task cannot overwrite another
  task's SMTP configuration.

### Known limitations

- Windows safe mode provides subprocess isolation and timeouts; memory/CPU
  enforcement is platform dependent and is not a hostile-code sandbox.
- Native OS registration is opt-in and requires the host scheduler tools.
- The development line is not a release candidate until CI and wheel checks
  pass on all supported runners.

## [1.2.0] - 2025-10-27

- Added async functions, retries, timeout handling, YAML/JSON persistence,
  subprocess safe mode, notifications, and the first analytics dashboard.

## [1.1.0] - 2025-10-27

- Added the original Rich dashboard, JSON analytics backend, and dashboard CLI
  commands.

## [1.0.0] - 2025-10-27

- Initial public release with interval/cron scheduling and decorator support.
