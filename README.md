# AutoCron Scheduler

[![CI](https://github.com/mdshoaibuddinchanda/autocron/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/mdshoaibuddinchanda/autocron/actions/workflows/ci-cd.yml)
[![PyPI](https://img.shields.io/pypi/v/autocron-scheduler.svg)](https://pypi.org/project/autocron-scheduler/)
[![Python](https://img.shields.io/pypi/pyversions/autocron-scheduler.svg)](https://pypi.org/project/autocron-scheduler/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

AutoCron is a small, cross-platform Python scheduler for scripts and Python
callables. It combines interval and cron schedules with retries, time-zone
aware next-run calculation, overlap policies, durable SQLite storage, a CLI,
and an optional Rich dashboard.

The current development line is `1.3.0.dev0`. The project is developed and
tested on Windows with Python 3.12 and has platform adapters for Windows Task
Scheduler, cron, and launchd.

## Install

```bash
python -m pip install autocron-scheduler

# Optional terminal dashboard and notification integrations
python -m pip install "autocron-scheduler[dashboard,notifications]"
```

For a source checkout, use the supported Conda environment and install the
complete developer toolchain:

```powershell
conda activate PY312
python -m pip install -e ".[dev,all,demo,docs]"
```

## Python quick start

```python
from autocron import AutoCron

scheduler = AutoCron(timezone="Asia/Kolkata")
scheduler.add_task(
    name="daily-report",
    script="scripts/report.py",
    cron="0 9 * * *",
    retries=2,
    timeout=300,
    overlap_policy="skip",
    misfire_grace_time=120,
)
scheduler.start()                 # blocking=True by default
```

For in-process Python functions, the decorator is convenient:

```python
from autocron import schedule, start_scheduler

@schedule(every="15m", timezone="UTC")
def refresh_cache():
    print("refreshing")

start_scheduler()
```

Use `scheduler.run_task(name="daily-report")` for an immediate synchronous
run. Function tasks are registered in code; script tasks can be persisted and
restored.

## Scheduling policies

- Intervals: `30s`, `5m`, `2h`, and `1d`.
- Cron: standard five-field expressions, evaluated in the task's IANA time
  zone (for example `Europe/London` or `Asia/Kolkata`). DST gaps and repeated
  wall times are handled deterministically.
- `overlap_policy="skip"` (default) drops a due occurrence while a run is
  active; `allow` permits up to `max_instances`; `queue` retains a bounded
  backlog.
- `misfire_grace_time` controls how late an occurrence may be before it is
  counted as a misfire. `coalesce=False` runs each eligible missed occurrence.

## Durable storage and CLI

The CLI stores task definitions and execution history in SQLite. Set
`AUTOCRON_DATABASE` to choose a database path, or `AUTOCRON_HOME` to choose a
portable application state directory. Credentials are stripped before task
payloads and analytics metadata are persisted.

```bash
autocron schedule scripts/report.py --cron "0 9 * * *" \
  --timezone Asia/Kolkata --retries 2
autocron list
autocron run daily-report
autocron stats daily-report --json
autocron dashboard
autocron dashboard --live --refresh 2
autocron logs --lines 50
autocron stop daily-report
```

The same commands are available as `python -m autocron.interface.cli ...`.

## Execution and platform notes

`safe_mode=True` runs a script in a separate subprocess, applies a timeout,
limits captured output, and uses platform resource controls where available.
On Windows, process isolation and timeout are supported; Unix-only resource
limits are intentionally reported as platform limitations. Safe mode is
defence-in-depth, not a security sandbox for hostile code.

Native OS registration is opt-in with `AutoCron(use_os_scheduler=True)` and
uses the platform adapter selected at runtime. The normal scheduler remains
portable and does not modify the host OS.

## Project layout

```text
autocron/
├── core/           scheduling engine, time policies, and OS adapters
├── interface/      CLI, Rich dashboard, and notifications
├── logging/        rotating application logger
└── storage.py      thread-safe SQLite task/history store
docs/               MkDocs documentation
demo/               executable notebooks
examples/           copy-and-adapt Python examples
tests/              isolated unit and integration tests
```

## Development checks

```powershell
conda activate PY312
python -m pip install -e ".[dev,all,demo,docs]"

# Tests never touch the user's real AutoCron state
pytest -q
pytest --cov=autocron --cov-branch --cov-report=term-missing --cov-fail-under=70

python -m build
python -m twine check dist/*
mkdocs build --strict
pytest --no-cov --nbmake demo --nbmake-timeout=120
```

The Windows baseline currently reports 218 passing tests, 4 intentional host
integration skips, and 83.14% statement coverage. Coverage is enforced in CI;
host scheduler tests are opt-in with `AUTOCRON_RUN_SYSTEM_TESTS=1`.

## Documentation and roadmap

- [Documentation](docs/index.md)
- [Complete guide](docs/complete-guide.md)
- [API reference](docs/api-reference.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## License

AutoCron is released under the [MIT License](LICENSE).
