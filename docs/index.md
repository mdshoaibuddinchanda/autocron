# AutoCron

AutoCron is a Python scheduler for applications and scripts that need readable
interval or cron schedules without maintaining separate platform-specific code.

```python
from autocron import schedule, start_scheduler


@schedule(every="5m")
def refresh_cache() -> None:
    print("cache refreshed")


start_scheduler()
```

## Capabilities

- Function and Python-script tasks
- Interval and cron schedules
- Synchronous and asynchronous callables
- Timezone-aware schedules
- Retry, timeout, overlap, and misfire policies
- SQLite-backed CLI task definitions and execution history
- JSON/YAML import and export
- Desktop and SMTP notifications
- Terminal dashboards and JSON statistics
- Optional Windows Task Scheduler and POSIX cron adapters

## Project scope

AutoCron is designed for dependable single-machine scheduling. The in-process
scheduler runs only while its Python process is alive. Persistent CLI definitions
still require `autocron start` or an operating-system service to execute them.

Subprocess isolation limits failure propagation and can enforce selected resource
limits. It is not a security boundary for hostile code: subprocesses normally run
with the same operating-system account, filesystem access, and network access as
their parent.

## Next steps

- [Install AutoCron](installation.md)
- [Run the quick start](quickstart.md)
- [Understand the architecture](architecture.md)
- [Browse the API reference](api-reference.md)
- [Open the demo notebooks](https://github.com/mdshoaibuddinchanda/autocron/tree/main/demo)
