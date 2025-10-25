"""
Advanced scheduling example using AutoCron class.

This example shows advanced features and configuration options.
"""

from autocron import AutoCron
import time


def data_processor():
    """Process data."""
    print("Processing data...")
    # Simulate processing
    time.sleep(2)
    print("Data processed successfully!")


def backup_database():
    """Backup database."""
    print("Starting database backup...")
    # Simulate backup
    time.sleep(3)
    print("Backup completed!")


def send_notifications():
    """Send notifications."""
    print("Sending notifications...")
    # Your notification logic


def main():
    """Main function."""
    # Create scheduler with custom configuration
    scheduler = AutoCron(log_path="./logs/autocron.log", log_level="INFO", max_workers=4)

    # Add tasks with different configurations
    scheduler.add_task(
        name="data_processor",
        func=data_processor,
        every="2m",
        retries=3,
        retry_delay=30,
        timeout=300,
        on_success=lambda: print("✓ Data processing successful"),
        on_failure=lambda e: print(f"✗ Data processing failed: {e}"),
    )

    scheduler.add_task(
        name="database_backup",
        func=backup_database,
        cron="0 2 * * *",  # Daily at 2 AM
        retries=5,
        retry_delay=60,
        timeout=3600,
    )

    scheduler.add_task(name="notification_service", func=send_notifications, every="15m", retries=2)

    # Print scheduled tasks
    print("\n=== Scheduled Tasks ===")
    for task in scheduler.list_tasks():
        print(f"- {task.name}: {task.schedule_type}={task.schedule_value}")
    print()

    # Start scheduler
    print("Starting scheduler...")
    print("Press Ctrl+C to stop\n")

    try:
        scheduler.start(blocking=True)
    except KeyboardInterrupt:
        print("\n\nStopping scheduler...")
        scheduler.stop()
        print("Scheduler stopped.")


if __name__ == "__main__":
    main()
