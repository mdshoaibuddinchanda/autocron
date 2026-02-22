"""
Test Dashboard with Failures - Show how dashboard handles problematic tasks.
"""

import random
import time

from autocron import get_global_scheduler, schedule


# Task that fails frequently to trigger warnings
@schedule(every="2s", retries=1)
def problematic_task():
 """A task that fails 70% of the time."""
 if random.random() < 0.7: # 70% failure rate
 raise Exception("Frequent failure - needs attention!")
 print(" Problematic task succeeded (rare)")
 time.sleep(0.1)


# Task that succeeds but is slow
@schedule(every="3s")
def slow_task():
 """A very slow task."""
 print("⏱️ Slow task started...")
 time.sleep(3.5) # Longer than 3 seconds
 print(" Slow task completed")


if __name__ == "__main__":
 print("=" * 70)
 print(" Dashboard Test: Problematic Tasks")
 print("=" * 70)
 print()
 print("This test demonstrates dashboard recommendations for:")
 print(" • Low success rate tasks")
 print(" • High retry rate tasks")
 print(" • Long-running tasks")
 print()
 print("Running for 20 seconds...")
 print()

 # Get the global scheduler and start it
 scheduler = get_global_scheduler()
 scheduler.start(blocking=False)

 try:
 # Run for 20 seconds
 for i in range(20):
 time.sleep(1)
 if (i + 1) % 5 == 0:
 print(f"⏱️ {i + 1}/20 seconds")

 print()
 print("=" * 70)
 print("️ Test complete! Showing dashboard with warnings...")
 print("=" * 70)
 print()

 except KeyboardInterrupt:
 print("\n\n️ Stopping...")
 finally:
 scheduler.stop()
 time.sleep(1)

 # Show dashboard
 try:
 from autocron import show_dashboard, show_task

 print("\n Dashboard Summary:\n")
 show_dashboard()

 print("\n" + "=" * 70)
 print("️ Detailed Analysis: 'problematic_task'")
 print("=" * 70 + "\n")
 show_task("problematic_task")

 print("\n" + "=" * 70)
 print("⏱️ Detailed Analysis: 'slow_task'")
 print("=" * 70 + "\n")
 show_task("slow_task")

 except Exception as e:
 print(f"\n️ Error: {e}")
