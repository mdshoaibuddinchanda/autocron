# Quick start

## Schedule a function

```python
from autocron import schedule, start_scheduler


@schedule(every="10s")
def heartbeat() -> None:
    print("alive")


if __name__ == "__main__":
    start_scheduler()
```

Intervals use `s`, `m`, `h`, or `d`. Cron expressions use the standard five-field
format.

## Use an explicit scheduler

```python
from autocron import AutoCron


scheduler = AutoCron(timezone="Asia/Kolkata", max_workers=4)
scheduler.add_task(
    name="daily-report",
    script="reports.py",
    cron="0 9 * * 1-5",
    overlap_policy="skip",
    misfire_grace_time=300,
)
scheduler.start()
```

Using an IANA timezone makes daylight-saving behavior explicit. `UTC` is a good
default for services; use a local zone when the schedule represents a local
business time.

## Use the persistent CLI

```bash
autocron schedule reports.py --name daily-report --cron "0 9 * * 1-5" --timezone Asia/Kolkata
autocron list
autocron start
autocron stats daily-report
autocron stop daily-report
```

CLI task definitions and history use a local SQLite database. Use `--database`
to select a different file for an application, test, or service account.

## Async functions

```python
import asyncio

from autocron import schedule, start_scheduler


@schedule(every="30s")
async def poll_services() -> None:
    await asyncio.sleep(0.1)


start_scheduler()
```

See the [complete guide](complete-guide.md) for retries, persistence,
notifications, dashboards, and subprocess execution.
