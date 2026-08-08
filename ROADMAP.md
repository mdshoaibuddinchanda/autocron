# AutoCron Roadmap

This roadmap tracks work that has a concrete user outcome and an automated
acceptance check. It replaces older, conflicting plans that were spread across
the README and changelog.

## Now — v1.3 stabilization

- Recover the source, documentation, examples, notebooks, and GitHub Actions
  workflows from the February 2026 whitespace regression.
- Build and install both wheel and source distributions in a clean Python 3.12
  environment.
- Make CLI task creation, listing, removal, execution, and statistics persistent.
- Add timezone-aware schedules and explicit overlap, maximum-instance, misfire,
  and coalescing policies.
- Store task definitions and execution history transactionally in SQLite.
- Isolate all tests from real user files and operating-system schedulers.
- Publish deterministic, executed notebooks with no credentials or local paths.
- Ship a concise README and a working documentation site.

### Release acceptance criteria

- All supported Python files compile.
- Unit and integration tests pass on Windows, Linux, and macOS.
- Statement coverage is at least 75% on the Windows baseline, with critical
  scheduling, persistence, CLI, and packaging paths covered by focused tests;
  90%+ remains a follow-up target.
- A clean environment can install the built wheel, import every public package,
  and run `autocron --help`.
- Documentation links and notebook execution pass in CI.
- No default test command writes outside pytest temporary directories.

## Next — reliability and platform parity

- Improve DST transition and timezone migration test coverage.
- Add opt-in, real-system tests for Windows Task Scheduler and POSIX cron.
- Add process-tree resource monitoring and platform-specific hard limits.
- Add database migration and recovery tooling.
- Add structured JSON logging and richer operational metrics.

## Later — extensibility

- Stable `TaskStore`, executor, and notifier protocols for third-party adapters.
- Optional HTTP management API.
- Additional notification channels.
- Multi-node coordination only after the single-node scheduling contract is
  proven under stress and failure testing.

Distributed execution and cloud synchronization are intentionally not v1.3
goals. Correctness, portability, and a dependable release take priority.
