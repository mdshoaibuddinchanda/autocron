"""
Dashboard Example - Monitor your AutoCron tasks with beautiful visualizations.

This example demonstrates the dashboard feature that tracks task execution
statistics, shows performance metrics, and provides smart recommendations.
"""

import random
import time

from autocron import schedule, start_scheduler


# Example 1: Simple tasks that will generate analytics data
@schedule(every="5s")
def quick_task():
 """A fast, reliable task."""
 print("Quick task executed")
 time.sleep(0.1)


@schedule(every="8s")
def medium_task():
 """A task with moderate duration."""
 print("Medium task executed")
 time.sleep(0.5)


@schedule(every="10s", retries=3)
def sometimes_fails():
 """A task that occasionally fails to demonstrate failure tracking."""
 if random.random() < 0.3: # 30% chance of failure
 raise Exception("Simulated random failure")
 print("Sometimes fails task executed")
 time.sleep(0.2)


@schedule(every="15s")
def slow_task():
 """A slower task to demonstrate duration tracking."""
 print("Slow task executed")
 time.sleep(2.0)


if __name__ == "__main__":
 print("=" * 70)
 print(" AutoCron Dashboard Example")
 print("=" * 70)
 print()
 print("This example runs multiple tasks and tracks their execution stats.")
 print()
 print("While this is running, open a NEW terminal and try:")
 print()
 print(" autocron dashboard # View task summary")
 print(" autocron stats quick_task # View specific task details")
 print(" autocron dashboard --live # Live monitoring dashboard")
 print()
 print("The scheduler will run for 60 seconds to generate sample data...")
 print("Press Ctrl+C to stop earlier")
 print()
 print("-" * 70)
 print()

 # Start scheduler for 60 seconds to generate data
 scheduler = start_scheduler(blocking=False)

 try:
 # Let it run for 60 seconds
 for i in range(60):
 time.sleep(1)
 if (i + 1) % 10 == 0:
 print(f"⏱️ Running... {i + 1}/60 seconds")

 print()
 print("=" * 70)
 print(" Sample data generated!")
 print("=" * 70)
 print()
 print("Now run these commands to see the dashboard:")
 print()
 print(" autocron dashboard # Summary view")
 print(" autocron stats quick_task # Detailed task stats")
 print(" autocron dashboard --live # Live monitoring")
 print()

 except KeyboardInterrupt:
 print("\n\n️ Stopping scheduler...")
 finally:
 scheduler.stop()

 # Show a quick summary using the API
 try:
 from autocron import show_dashboard

 print("\n Final Dashboard Summary:\n")
 show_dashboard()
 except ImportError:
 print("\nTo see the dashboard, install: pip install autocron-scheduler[dashboard]")
 except Exception:
 pass # No data generated yet
