"""
Simple scheduling example.

This example demonstrates basic usage of AutoCron.
"""

from autocron import schedule, start_scheduler


# Example 1: Schedule a function with interval
@schedule(every="30s")
def fetch_data():
 """Fetch data every 30 seconds."""
 print("Fetching data...")
 # Your data fetching logic here


# Example 2: Schedule with cron expression
@schedule(cron="0 9 * * *")
def daily_report():
 """Generate daily report at 9 AM."""
 print("Generating daily report...")
 # Your report generation logic here


# Example 3: Schedule with retries
@schedule(every="5m", retries=3, retry_delay=60)
def api_sync():
 """Sync with API every 5 minutes with retries."""
 print("Syncing with API...")
 # Your API sync logic here


# Example 4: Schedule with notifications
@schedule(
 every="1h",
 notify="desktop",
 on_success=lambda: print(" Success!"),
 on_failure=lambda e: print(f" Failed: {e}"),
)
def cleanup_task():
 """Cleanup task with notifications."""
 print("Running cleanup...")
 # Your cleanup logic here


if __name__ == "__main__":
 print("Starting AutoCron scheduler...")
 print("Press Ctrl+C to stop")
 print()

 # Start the scheduler (blocking)
 start_scheduler(blocking=True)
