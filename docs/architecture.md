# Architecture

AutoCron is organized around a small scheduling core with replaceable boundaries
for persistence, user interfaces, notifications, and operating-system adapters.

```text
Python API / CLI
       |
       v
Scheduler -----> Executor threads / subprocesses
   |  |                   |
   |  +-----> Notifications
   |
   +--------> SQLite task and history store
   |
   +--------> Optional Windows Task Scheduler / POSIX cron adapter
```

## Scheduling core

`autocron.core.scheduler` owns task validation, next-run calculation, retries,
overlap limits, misfire handling, execution, and lifecycle management. A task has
an explicit timezone and never relies on silently mixing naive and aware
datetimes.

## Persistence

`autocron.storage` stores CLI task definitions and execution history in SQLite.
Transactions protect multi-step updates and schema metadata supports future
migrations. User credentials are not stored in task rows.

YAML and JSON remain useful interchange formats for script-based tasks. File
writes use replacement semantics so a process interruption cannot leave a
half-written configuration in place.

## Interfaces

`autocron.interface.cli` is a persistent management interface rather than an
in-memory demonstration. `autocron.interface.dashboard` reads execution history
and presents it through Rich when the optional dependency is installed.

## Platform adapters

Platform adapters are optional. Unit tests mock all external commands; real
`schtasks` and `crontab` tests require explicit opt-in. This keeps the normal test
suite safe on developer machines and CI runners.

## Security boundary

Launching a Python file in a subprocess isolates its interpreter and permits
timeouts or selected resource limits. It does not remove the child process's OS
permissions. Run untrusted code inside an appropriately configured container,
virtual machine, or restricted operating-system account.
