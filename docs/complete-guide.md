# Complete guide

## Choosing an API

Use the decorator API for a small application whose schedules are defined in
code. Use `AutoCron` when you need task inspection, lifecycle control, callbacks,
or custom policies. Use the CLI and SQLite store when schedules must be managed
outside the application source.

## Retries and callbacks

```python
from autocron import AutoCron


def completed() -> None:
    print("completed")


def failed(error: Exception) -> None:
    print(f"failed: {error}")


scheduler = AutoCron()
scheduler.add_task(
    name="sync-catalog",
    script="sync_catalog.py",
    every="15m",
    retries=3,
    retry_delay=5,
    timeout=120,
    on_success=completed,
    on_failure=failed,
)
```

Retry delays use bounded exponential backoff. A final failure advances the
schedule and records one failed execution.

## Overlap and misfires

An overlap policy controls what happens when a task becomes due while an earlier
instance is still active. Prefer `skip` for periodic maintenance and monitoring
work. Use a higher `max_instances` only when concurrent execution is safe.

A misfire grace time limits how late a run may start. Coalescing turns several
missed occurrences into one catch-up run instead of a burst after downtime.

## Timezones

Use IANA names such as `UTC`, `Asia/Kolkata`, or `America/New_York`. Cron schedules
are calculated in the task timezone. Store and compare instants consistently,
especially around daylight-saving transitions.

## Persistence

SQLite is the primary store for persistent CLI workflows. JSON and YAML exports
are intended for review and source control. Do not put SMTP passwords or other
secrets in task files; load them from a secret manager or environment at runtime.

## Notifications

Install the relevant extra and configure notification channels explicitly.
Notification delivery failures are recorded but do not change a successful task
execution into a failure.

## Subprocess execution

Script tasks use the active Python interpreter. Timeouts terminate the spawned
process tree where the operating system permits it, and captured output is
bounded. Subprocess mode is failure isolation, not a sandbox for hostile code.

## Operations

- Run the scheduler under a service manager for long-lived use.
- Use UTC unless schedules represent a specific local civil time.
- Back up the SQLite database and test restoration.
- Keep system-adapter tests opt-in.
- Monitor failures, duration, skipped overlaps, and misfires.

See [Architecture](architecture.md), [API reference](api-reference.md), and the
[demo notebooks](https://github.com/mdshoaibuddinchanda/autocron/tree/main/demo).
