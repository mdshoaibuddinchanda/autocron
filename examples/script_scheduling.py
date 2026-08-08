"""
Example of scheduling Python scripts.

This example shows how to schedule external Python scripts.
"""

from autocron import AutoCron


def main():
    """Main function."""
    scheduler = AutoCron(log_level="DEBUG")

    # Schedule script to run every 5 minutes
    scheduler.add_task(
        name="data_sync", script="./scripts/sync_data.py", every="5m", retries=3, timeout=600
    )

    # Schedule script with cron expression
    scheduler.add_task(
        name="report_generation",
        script="./scripts/generate_report.py",
        cron="0 9 * * 1-5",  # Weekdays at 9 AM
        retries=2,
        timeout=1800,
    )

    # Schedule cleanup script
    scheduler.add_task(
        name="cleanup",
        script="./scripts/cleanup.py",
        cron="0 0 * * 0",  # Weekly on Sunday at midnight
        retries=1,
    )

    print("Scheduled scripts:")
    for task in scheduler.list_tasks():
        print(f"  - {task.name}: {task.script}")
        print(f"    Schedule: {task.schedule_value}")
        print(f"    Retries: {task.retries}")
        print()

    print("Starting scheduler...")
    print("Press Ctrl+C to stop\n")

    try:
        scheduler.start(blocking=True)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        scheduler.stop()


if __name__ == "__main__":
    main()
