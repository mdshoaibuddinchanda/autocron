# FAQ

## Which package do I install?

Install `autocron-scheduler`. The separate PyPI project named `autocron` is not
this repository.

```bash
python -m pip install autocron-scheduler
```

## Why did my decorated task not run?

Registration does not keep a process alive. Call `start_scheduler()` or start an
`AutoCron` instance, normally behind an `if __name__ == "__main__"` guard.

## Do CLI schedules run after the terminal closes?

The SQLite definition remains, but execution needs `autocron start` running under
a terminal, service manager, or operating-system scheduler.

## Is subprocess mode a sandbox?

No. It isolates the Python process and supports operational limits, but the child
normally retains the current user's filesystem and network permissions.

## Where is persistent CLI data stored?

The CLI displays its database path and accepts `--database` for an explicit
location. Tests always use temporary locations.

## Can I use Windows Task Scheduler?

Yes, through the optional OS adapter. Creating or removing system tasks changes
the current Windows account's Task Scheduler state, so normal unit tests mock the
adapter. Real system tests are opt-in.

## How should I test schedules?

Inject or mock clocks and platform adapters. Avoid long `sleep()` calls and avoid
using real home-directory paths. The project test suite demonstrates temporary
state and focused system-test markers.

## How do I report a security issue?

Follow the private reporting instructions in the repository's
[security policy](https://github.com/mdshoaibuddinchanda/autocron/security/policy).
