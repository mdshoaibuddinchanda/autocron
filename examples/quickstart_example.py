"""
Quick Start Examples from README.

These examples demonstrate the simplest ways to get started with AutoCron.
"""

from autocron import schedule, start_scheduler


# Example 1: Schedule a function every 30 minutes
@schedule(every='30m', retries=2)
def fetch_data():
    """Fetch data every 30 minutes."""
    print("Fetching data...")
    # Your code here


# Example 2: Schedule with cron expression
@schedule(cron='0 */2 * * *')
def cleanup_logs():
    """Clean up logs every 2 hours."""
    print("Cleaning logs...")
    # Your code here


# Example 3: Simple interval scheduling
@schedule(every='5m')
def check_status():
    """Check status every 5 minutes."""
    print("Checking status...")


# Example 4: Daily task at specific time
@schedule(cron='0 8 * * *')
def morning_report():
    """Generate report every morning at 8 AM."""
    print("Generating morning report...")


if __name__ == '__main__':
    print("=" * 60)
    print("AutoCron - Quick Start Examples")
    print("=" * 60)
    print("\nScheduled tasks:")
    print("  - fetch_data: Every 30 minutes")
    print("  - cleanup_logs: Every 2 hours")
    print("  - check_status: Every 5 minutes")
    print("  - morning_report: Daily at 8:00 AM")
    print("\nPress Ctrl+C to stop the scheduler")
    print("=" * 60)
    print()
    
    # Start the scheduler (blocking)
    start_scheduler(blocking=True)
