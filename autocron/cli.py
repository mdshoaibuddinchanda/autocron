"""
Command-line interface for AutoCron.

Provides CLI commands for managing scheduled tasks.
"""

import argparse
import sys
from typing import Optional

from autocron import AutoCron, __version__
from autocron.logger import get_logger


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="autocron",
        description="AutoCron - Automate scripts with zero setup",
        epilog="For more information, visit: https://github.com/mdshoaibuddinchanda/autocron",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Schedule a script")
    schedule_parser.add_argument("script", help="Path to script")
    schedule_parser.add_argument("--every", help="Interval (e.g., 5m, 1h)")
    schedule_parser.add_argument("--cron", help="Cron expression")
    schedule_parser.add_argument("--name", help="Task name")
    schedule_parser.add_argument("--retries", type=int, default=0, help="Max retries")
    schedule_parser.add_argument("--timeout", type=int, help="Timeout in seconds")
    schedule_parser.add_argument("--notify", choices=["desktop", "email"], help="Notification type")

    # List command
    subparsers.add_parser("list", help="List scheduled tasks")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop a scheduled task")
    stop_parser.add_argument("name", help="Task name")

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View task logs")
    logs_parser.add_argument("name", nargs="?", help="Task name")
    logs_parser.add_argument("--lines", type=int, default=100, help="Number of lines")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start scheduler from config")
    start_parser.add_argument("--config", default="autocron.yaml", help="Config file path")

    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Show task dashboard")
    dashboard_parser.add_argument("--live", action="store_true", help="Live monitoring mode")
    dashboard_parser.add_argument(
        "--refresh", type=int, default=2, help="Refresh interval (seconds)"
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show task statistics")
    stats_parser.add_argument("task", nargs="?", help="Specific task name")
    stats_parser.add_argument("--export", help="Export stats to JSON file")

    return parser


def cmd_schedule(args: argparse.Namespace) -> int:
    """Handle schedule command."""
    if not args.every and not args.cron:
        print("Error: Either --every or --cron must be specified", file=sys.stderr)
        return 1

    try:
        scheduler = AutoCron()

        task_name = args.name or args.script

        task_id = scheduler.add_task(
            name=task_name,
            script=args.script,
            every=args.every,
            cron=args.cron,
            retries=args.retries,
            timeout=args.timeout,
            notify=args.notify,
        )

        print(f"✓ Task '{task_name}' scheduled successfully")
        print(f"  Task ID: {task_id}")
        print(f"  Schedule: {args.every or args.cron}")

        return 0
    except Exception as e:
        print(f"Error scheduling task: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """Handle list command."""
    try:
        scheduler = AutoCron()
        tasks = scheduler.list_tasks()

        if not tasks:
            print("No scheduled tasks found")
            return 0

        print(f"\n{'Task Name':<30} {'Schedule':<20} {'Status':<10} {'Runs':<10} {'Failures':<10}")
        print("-" * 90)

        for task in tasks:
            status = "Enabled" if task.enabled else "Disabled"
            schedule = f"{task.schedule_type}={task.schedule_value}"

            print(
                f"{task.name:<30} {schedule:<20} {status:<10} "
                f"{task.run_count:<10} {task.fail_count:<10}"
            )

        print(f"\nTotal tasks: {len(tasks)}\n")
        return 0
    except Exception as e:
        print(f"Error listing tasks: {e}", file=sys.stderr)
        return 1


def cmd_stop(args: argparse.Namespace) -> int:
    """Handle stop command."""
    try:
        scheduler = AutoCron()

        if scheduler.remove_task(name=args.name):
            print(f"✓ Task '{args.name}' stopped successfully")
            return 0
        else:
            print(f"Error: Task '{args.name}' not found", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error stopping task: {e}", file=sys.stderr)
        return 1


def cmd_logs(args: argparse.Namespace) -> int:
    """Handle logs command."""
    try:
        logger = get_logger()
        logs = logger.get_recent_logs(lines=args.lines)

        if not logs:
            print("No logs found")
            return 0

        # Filter by task name if specified
        if args.name:
            logs = [line for line in logs if args.name in line]

        print("\n".join(logs))
        return 0
    except Exception as e:
        print(f"Error reading logs: {e}", file=sys.stderr)
        return 1


def cmd_start(args: argparse.Namespace) -> int:
    """Handle start command."""
    try:
        import os

        if not os.path.exists(args.config):
            print(f"Error: Config file '{args.config}' not found", file=sys.stderr)
            return 1

        scheduler = AutoCron.from_config(args.config)

        print(f"✓ Loaded configuration from '{args.config}'")
        print(f"✓ Starting scheduler with {len(scheduler.tasks)} task(s)...")
        print("\nPress Ctrl+C to stop\n")

        scheduler.start(blocking=True)
        return 0
    except KeyboardInterrupt:
        print("\n\nStopping scheduler...")
        return 0
    except Exception as e:
        print(f"Error starting scheduler: {e}", file=sys.stderr)
        return 1


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Handle dashboard command."""
    try:
        from autocron.dashboard import Dashboard

        dashboard = Dashboard()

        if args.live:
            dashboard.show_live_monitor(refresh_rate=args.refresh)
        else:
            dashboard.show_summary()

        return 0
    except ImportError:
        print("Error: Dashboard requires 'rich' package.", file=sys.stderr)
        print("Install it with: pip install autocron-scheduler[dashboard]", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error showing dashboard: {e}", file=sys.stderr)
        return 1


def cmd_stats(args: argparse.Namespace) -> int:
    """Handle stats command."""
    try:
        from autocron.dashboard import Dashboard

        dashboard = Dashboard()

        if args.task:
            # Show specific task stats
            dashboard.show_task_details(args.task)
        elif args.export:
            # Export all stats
            dashboard.export_stats(args.export)
        else:
            # Show summary
            dashboard.show_summary()

        return 0
    except ImportError:
        print("Error: Stats requires 'rich' package.", file=sys.stderr)
        print("Install it with: pip install autocron-scheduler[dashboard]", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error showing stats: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[list] = None) -> int:
    """
    Main CLI entry point.

    Args:
        argv: Command-line arguments (default: sys.argv[1:])

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Route to command handler
    handlers = {
        "schedule": cmd_schedule,
        "list": cmd_list,
        "stop": cmd_stop,
        "logs": cmd_logs,
        "start": cmd_start,
        "dashboard": cmd_dashboard,
        "stats": cmd_stats,
    }

    if handler := handlers.get(args.command):
        return handler(args)
    print(f"Error: Unknown command '{args.command}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
