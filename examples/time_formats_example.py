"""
Time Format Examples.

Demonstrates all supported time format styles.
"""

from autocron import schedule, start_scheduler

# ============================================================================
# INTERVAL-BASED SCHEDULING (Simple)
# ============================================================================


@schedule(every="30s")
def every_30_seconds():
    """Run every 30 seconds."""
    print("⏱️  Every 30 seconds")


@schedule(every="5m")
def every_5_minutes():
    """Run every 5 minutes."""
    print("⏱️  Every 5 minutes")


@schedule(every="2h")
def every_2_hours():
    """Run every 2 hours."""
    print("⏱️  Every 2 hours")


@schedule(every="1d")
def every_day():
    """Run every day."""
    print("⏱️  Every day")


# ============================================================================
# CRON EXPRESSIONS (Powerful)
# ============================================================================


@schedule(cron="0 9 * * *")
def daily_at_9am():
    """Run every day at 9:00 AM."""
    print("📅 Daily at 9:00 AM")


@schedule(cron="*/15 * * * *")
def every_15_minutes():
    """Run every 15 minutes."""
    print("📅 Every 15 minutes")


@schedule(cron="0 0 * * 0")
def every_sunday_midnight():
    """Run every Sunday at midnight."""
    print("📅 Every Sunday at midnight")


@schedule(cron="0 12 * * 1-5")
def weekdays_at_noon():
    """Run weekdays at noon."""
    print("📅 Weekdays at noon")


@schedule(cron="0 */2 * * *")
def every_2_hours_on_the_hour():
    """Run every 2 hours at the start of the hour."""
    print("📅 Every 2 hours (on the hour)")


@schedule(cron="30 8 * * 1,3,5")
def monday_wednesday_friday():
    """Run Mon, Wed, Fri at 8:30 AM."""
    print("📅 Mon/Wed/Fri at 8:30 AM")


@schedule(cron="0 0 1 * *")
def first_day_of_month():
    """Run on the 1st of every month at midnight."""
    print("📅 First day of month at midnight")


@schedule(cron="0 6 * * 1-5")
def weekday_mornings():
    """Run weekday mornings at 6:00 AM."""
    print("📅 Weekday mornings at 6:00 AM")


# ============================================================================
# ADVANCED CONFIGURATIONS
# ============================================================================


@schedule(every="1h", retries=5, retry_delay=60, timeout=300, notify="desktop")
def complex_task():
    """Complex task with all options."""
    print("🔧 Complex task with retries, timeout, and notifications")


@schedule(
    cron="0 */4 * * *",
    retries=3,
    on_success=lambda: print("  ✓ Success!"),
    on_failure=lambda e: print(f"  ✗ Failed: {e}"),
)
def task_with_callbacks():
    """Task with success/failure callbacks."""
    print("🔔 Task with callbacks")


if __name__ == "__main__":
    print("=" * 70)
    print("AutoCron - Time Format Examples")
    print("=" * 70)
    print("\n📝 INTERVAL-BASED (Simple):")
    print("  '30s' - Every 30 seconds")
    print("  '5m'  - Every 5 minutes")
    print("  '2h'  - Every 2 hours")
    print("  '1d'  - Every day")

    print("\n📝 CRON EXPRESSIONS (Powerful):")
    print("  '0 9 * * *'     - Every day at 9:00 AM")
    print("  '*/15 * * * *'  - Every 15 minutes")
    print("  '0 0 * * 0'     - Every Sunday at midnight")
    print("  '0 12 * * 1-5'  - Weekdays at noon")
    print("  '0 */2 * * *'   - Every 2 hours")
    print("  '30 8 * * 1,3,5'- Mon/Wed/Fri at 8:30 AM")
    print("  '0 0 1 * *'     - First day of month")
    print("  '0 6 * * 1-5'   - Weekday mornings at 6:00 AM")

    print("\n📝 ADVANCED:")
    print("  - With retries and timeout")
    print("  - With callbacks")
    print("  - With notifications")

    print("\n⚠️  Note: This example shows all formats but runs quickly")
    print("    for demonstration. Actual schedules will execute at specified times.")
    print("\nPress Ctrl+C to stop")
    print("=" * 70)
    print()

    # Start the scheduler
    start_scheduler(blocking=True)
