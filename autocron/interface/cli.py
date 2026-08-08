"""Command-line interface for AutoCron's persistent scheduler."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Sequence

from autocron.core.scheduler import AutoCron, SchedulingError, Task
from autocron.logging.logger import get_logger
from autocron.storage import DuplicateTaskError, SQLiteStore, default_database_path
from autocron.version import __version__


def _add_database_argument(parser: argparse.ArgumentParser) -> None:
    # SUPPRESS preserves the value parsed by the root parser when this option is
    # not repeated after a subcommand.
    parser.add_argument(
        "--database",
        metavar="PATH",
        default=argparse.SUPPRESS,
        help="SQLite database path (also configurable with AUTOCRON_DATABASE)",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the AutoCron command-line parser."""

    parser = argparse.ArgumentParser(
        prog="autocron",
        description="Schedule, run, and inspect Python tasks from one durable task database.",
        epilog="Documentation: https://github.com/mdshoaibuddinchanda/autocron",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--database",
        metavar="PATH",
        default=None,
        help="SQLite database path (may also follow a subcommand)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    schedule_parser = subparsers.add_parser("schedule", help="Persist a scheduled Python script")
    _add_database_argument(schedule_parser)
    schedule_parser.add_argument("script", help="Path to a Python script")
    schedule_group = schedule_parser.add_mutually_exclusive_group(required=True)
    schedule_group.add_argument("--every", help="Interval such as 30s, 5m, or 1h")
    schedule_group.add_argument("--cron", help="Five-field cron expression")
    schedule_parser.add_argument("--name", help="Unique task name (defaults to the script stem)")
    schedule_parser.add_argument("--retries", type=int, default=0, help="Maximum retry attempts")
    schedule_parser.add_argument(
        "--retry-delay", type=int, default=60, help="Base retry delay in seconds"
    )
    schedule_parser.add_argument("--timeout", type=float, help="Execution timeout in seconds")
    schedule_parser.add_argument(
        "--notify",
        action="append",
        choices=["desktop", "email"],
        help="Notification channel; repeat to select more than one",
    )
    schedule_parser.add_argument("--timezone", help="IANA timezone, for example Asia/Kolkata")
    schedule_parser.add_argument(
        "--overlap-policy",
        choices=["skip", "allow", "queue"],
        default="skip",
        help="What to do when the previous run is still active",
    )
    schedule_parser.add_argument(
        "--max-instances", type=int, default=1, help="Maximum simultaneous task instances"
    )
    schedule_parser.add_argument(
        "--misfire-grace-time",
        type=float,
        default=60.0,
        help="Seconds a late run remains eligible; use 0 for no grace",
    )
    schedule_parser.add_argument(
        "--no-coalesce",
        dest="coalesce",
        action="store_false",
        default=True,
        help="Run each missed occurrence instead of merging missed runs",
    )
    schedule_parser.add_argument(
        "--isolated", dest="safe_mode", action="store_true", help="Run the script in isolation"
    )
    schedule_parser.add_argument(
        "--clean-env", action="store_true", help="Use a minimal environment in isolated mode"
    )
    schedule_parser.add_argument(
        "--max-memory-mb", type=int, help="Memory limit for supported isolated runners"
    )
    schedule_parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=1_000_000,
        help="Maximum captured subprocess output",
    )
    schedule_parser.add_argument("--disabled", action="store_true", help="Create the task disabled")
    schedule_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    list_parser = subparsers.add_parser("list", help="List persisted tasks")
    _add_database_argument(list_parser)
    list_parser.add_argument("--enabled", action="store_true", help="Show only enabled tasks")
    list_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    stop_parser = subparsers.add_parser("stop", help="Remove a persisted task")
    _add_database_argument(stop_parser)
    stop_parser.add_argument("task", help="Task name or ID")
    stop_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    run_parser = subparsers.add_parser("run", help="Run a persisted task immediately")
    _add_database_argument(run_parser)
    run_parser.add_argument("task", help="Task name or ID")
    run_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    logs_parser = subparsers.add_parser("logs", help="View AutoCron log output")
    logs_parser.add_argument("name", nargs="?", help="Optional task-name filter")
    logs_parser.add_argument("--lines", type=int, default=100, help="Maximum number of lines")

    start_parser = subparsers.add_parser("start", help="Run enabled tasks from the database")
    _add_database_argument(start_parser)
    start_parser.add_argument(
        "--config", help="Import tasks from a YAML/JSON config before starting"
    )

    dashboard_parser = subparsers.add_parser("dashboard", help="Show task execution analytics")
    _add_database_argument(dashboard_parser)
    dashboard_parser.add_argument("--live", action="store_true", help="Continuously refresh")
    dashboard_parser.add_argument(
        "--refresh", type=float, default=2.0, help="Live refresh interval in seconds"
    )
    dashboard_parser.add_argument("--json", action="store_true", help="Emit analytics as JSON")

    stats_parser = subparsers.add_parser("stats", help="Show or export execution statistics")
    _add_database_argument(stats_parser)
    stats_parser.add_argument("task", nargs="?", help="Optional task name")
    stats_parser.add_argument("--export", metavar="PATH", help="Export statistics to JSON")
    stats_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def _database(args: argparse.Namespace) -> Path:
    value = getattr(args, "database", None)
    return Path(value).expanduser().resolve() if value else default_database_path()


def _write_json(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str, sort_keys=True))


@contextmanager
def _selected_database(path: Path) -> Iterator[None]:
    """Make scheduler-created analytics use the selected CLI database."""

    previous = os.environ.get("AUTOCRON_DATABASE")
    os.environ["AUTOCRON_DATABASE"] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("AUTOCRON_DATABASE", None)
        else:
            os.environ["AUTOCRON_DATABASE"] = previous


def _new_scheduler(database: Path) -> AutoCron:
    database.parent.mkdir(parents=True, exist_ok=True)
    with _selected_database(database):
        scheduler = AutoCron(log_path=str(database.parent / "autocron.log"))

    from autocron.interface.dashboard import TaskAnalytics

    old_analytics = scheduler.analytics
    scheduler.analytics = TaskAnalytics(database_path=database)
    if old_analytics is not None and hasattr(old_analytics, "close"):
        old_analytics.close()
    return scheduler


def _task_from_args(args: argparse.Namespace) -> Task:
    script = Path(args.script).expanduser()
    if not script.exists():
        raise ValueError(f"Script does not exist: {script}")
    if not script.is_file():
        raise ValueError(f"Script is not a file: {script}")
    if args.retries < 0:
        raise ValueError("retries must be non-negative")
    if args.retry_delay < 0:
        raise ValueError("retry-delay must be non-negative")
    if args.timeout is not None and args.timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if args.max_instances < 1:
        raise ValueError("max-instances must be at least one")
    if args.misfire_grace_time < 0:
        raise ValueError("misfire-grace-time must be non-negative")
    if args.max_memory_mb is not None and args.max_memory_mb <= 0:
        raise ValueError("max-memory-mb must be greater than zero")
    if args.max_output_bytes < 1:
        raise ValueError("max-output-bytes must be at least one")

    notify: Any = args.notify
    if notify and len(notify) == 1:
        notify = notify[0]
    task = Task(
        name=args.name or script.stem,
        script=str(script.resolve()),
        every=args.every,
        cron=args.cron,
        retries=args.retries,
        retry_delay=args.retry_delay,
        timeout=args.timeout,
        notify=notify,
        timezone=args.timezone,
        overlap_policy=args.overlap_policy,
        max_instances=args.max_instances,
        misfire_grace_time=args.misfire_grace_time,
        coalesce=args.coalesce,
        safe_mode=args.safe_mode,
        clean_env=args.clean_env,
        max_memory_mb=args.max_memory_mb,
        max_output_bytes=args.max_output_bytes,
    )
    task.enabled = not args.disabled
    return task


def cmd_schedule(args: argparse.Namespace) -> int:
    """Persist a new script task."""

    try:
        task = _task_from_args(args)
        with SQLiteStore(_database(args)) as store:
            task_id = store.add_task(task)
            record = store.get_task(task_id=task_id)
        if args.json:
            _write_json(record)
        else:
            print(f"Scheduled '{task.name}' ({task_id})")
            print(f"Schedule: {task.schedule_type}={task.schedule_value}")
        return 0
    except (DuplicateTaskError, OSError, ValueError) as exc:
        print(f"Error scheduling task: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error scheduling task: {exc}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """List tasks from persistent storage."""

    try:
        with SQLiteStore(_database(args)) as store:
            tasks = store.list_tasks(enabled=True if args.enabled else None)
        if args.json:
            _write_json(tasks)
            return 0
        if not tasks:
            print("No scheduled tasks found")
            return 0

        print(f"{'Task Name':<28} {'Schedule':<24} {'Status':<10} {'Runs':>7} {'Failures':>9}")
        print("-" * 84)
        for task in tasks:
            schedule = f"{task['schedule_type']}={task['schedule_value']}"
            status = "Enabled" if task.get("enabled", True) else "Disabled"
            print(
                f"{task['name']:<28.28} {schedule:<24.24} {status:<10} "
                f"{int(task.get('run_count', 0)):>7} {int(task.get('fail_count', 0)):>9}"
            )
        print(f"\nTotal tasks: {len(tasks)}")
        return 0
    except Exception as exc:
        print(f"Error listing tasks: {exc}", file=sys.stderr)
        return 1


def cmd_stop(args: argparse.Namespace) -> int:
    """Remove a task from persistent storage."""

    try:
        with SQLiteStore(_database(args)) as store:
            removed = store.remove_task(args.task)
        result = {"removed": removed, "task": args.task}
        if args.json:
            _write_json(result)
        elif removed:
            print(f"Removed task '{args.task}'")
        else:
            print(f"Error: Task '{args.task}' not found", file=sys.stderr)
        return 0 if removed else 1
    except Exception as exc:
        print(f"Error stopping task: {exc}", file=sys.stderr)
        return 1


def cmd_logs(args: argparse.Namespace) -> int:
    """Print recent application log lines."""

    if args.lines < 0:
        print("Error: --lines must be non-negative", file=sys.stderr)
        return 1
    try:
        logs = get_logger().get_recent_logs(lines=args.lines)
        if args.name:
            logs = [line for line in logs if args.name in line]
        if not logs:
            print("No logs found")
            return 0
        print("\n".join(logs))
        return 0
    except Exception as exc:
        print(f"Error reading logs: {exc}", file=sys.stderr)
        return 1


def _load_persisted_tasks(scheduler: AutoCron, store: SQLiteStore) -> int:
    loaded = 0
    for record in store.list_tasks(enabled=True):
        task = Task.from_dict(record)
        scheduler.tasks[task.task_id] = task
        loaded += 1
    return loaded


def _import_config(config_path: str, store: SQLiteStore, database: Path) -> int:
    path = Path(config_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    with _selected_database(database):
        imported = AutoCron.from_config(str(path))
    count = 0
    for task in imported.list_tasks():
        existing = store.get_task(name=task.name)
        if existing:
            task.task_id = existing["task_id"]
        store.save_task(task)
        count += 1
    return count


def cmd_start(args: argparse.Namespace) -> int:
    """Start the scheduler with enabled tasks from persistent storage."""

    database = _database(args)
    scheduler: Optional[AutoCron] = None
    interrupted = False
    try:
        with SQLiteStore(database) as store:
            if args.config:
                imported = _import_config(args.config, store, database)
                print(f"Imported {imported} task(s) from '{args.config}'")
            scheduler = _new_scheduler(database)
            loaded = _load_persisted_tasks(scheduler, store)
            if loaded == 0:
                print("No enabled tasks found")
                return 0
            print(f"Starting scheduler with {loaded} task(s). Press Ctrl+C to stop.")
            try:
                scheduler.start(blocking=True)
            except KeyboardInterrupt:
                interrupted = True
            finally:
                scheduler.stop()
                store.sync_tasks(scheduler)
        if interrupted:
            print("Scheduler stopped")
            return 130
        return 0
    except (FileNotFoundError, SchedulingError, ValueError) as exc:
        print(f"Error starting scheduler: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error starting scheduler: {exc}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Execute one persisted task synchronously."""

    database = _database(args)
    try:
        with SQLiteStore(database) as store:
            record = store.get_task(args.task)
            if record is None:
                print(f"Error: Task '{args.task}' not found", file=sys.stderr)
                return 1
            scheduler = _new_scheduler(database)
            task = Task.from_dict(record)
            scheduler.tasks[task.task_id] = task
            succeeded = scheduler.run_task(task_id=task.task_id, wait=True)
            store.save_task(task)

        result: Dict[str, Any] = {
            "success": succeeded,
            "task": task.name,
            "task_id": task.task_id,
        }
        if args.json:
            _write_json(result)
        else:
            print(f"Task '{task.name}' {'completed successfully' if succeeded else 'failed'}")
        return 0 if succeeded else 1
    except (SchedulingError, ValueError) as exc:
        print(f"Error running task: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error running task: {exc}", file=sys.stderr)
        return 1


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Show dashboard output for the selected database."""

    try:
        from autocron.interface.dashboard import Dashboard, TaskAnalytics

        analytics = TaskAnalytics(database_path=_database(args))
        if args.json:
            _write_json(analytics.get_all_stats())
            return 0
        dashboard = Dashboard(analytics)
        if args.live:
            dashboard.show_live_monitor(refresh_rate=args.refresh)
        else:
            dashboard.show_summary()
        return 0
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"Error showing dashboard: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error showing dashboard: {exc}", file=sys.stderr)
        return 1


def cmd_stats(args: argparse.Namespace) -> int:
    """Show or export execution statistics."""

    try:
        from autocron.interface.dashboard import Dashboard, TaskAnalytics

        analytics = TaskAnalytics(database_path=_database(args))
        selected: Any = (
            analytics.get_task_stats(args.task) if args.task else analytics.get_all_stats()
        )
        if args.task and selected is None:
            print(f"Error: No execution history for task '{args.task}'", file=sys.stderr)
            return 1
        if args.export:
            output = Path(args.export).expanduser()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(selected, indent=2, default=str), encoding="utf-8")
            print(f"Stats exported to {output}")
            return 0
        if args.json:
            _write_json(selected)
            return 0
        dashboard = Dashboard(analytics)
        if args.task:
            return 0 if dashboard.show_task_details(args.task) else 1
        dashboard.show_summary()
        return 0
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error showing stats: {exc}", file=sys.stderr)
        return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the command-line interface and return a process exit code."""

    parser = create_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    handlers = {
        "schedule": cmd_schedule,
        "list": cmd_list,
        "stop": cmd_stop,
        "logs": cmd_logs,
        "start": cmd_start,
        "run": cmd_run,
        "dashboard": cmd_dashboard,
        "stats": cmd_stats,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.error(f"unknown command: {args.command}")
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
