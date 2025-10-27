"""
Quick Dashboard Test - Generate sample data and show dashboard.
"""

import time
import random
from autocron import schedule, get_global_scheduler

# Example tasks that will generate analytics data
@schedule(every="3s")
def quick_task():
    """A fast, reliable task."""
    print("✓ Quick task executed")
    time.sleep(0.1)

@schedule(every="5s")
def medium_task():
    """A task with moderate duration."""
    print("✓ Medium task executed")
    time.sleep(0.5)

@schedule(every="7s", retries=2)
def sometimes_fails():
    """A task that occasionally fails."""
    if random.random() < 0.4:  # 40% chance of failure
        print("✗ Sometimes fails - FAILED")
        raise Exception("Simulated random failure")
    print("✓ Sometimes fails task executed")
    time.sleep(0.2)

if __name__ == "__main__":
    print("=" * 70)
    print("🎯 AutoCron Dashboard Test")
    print("=" * 70)
    print()
    print("Running tasks for 30 seconds to generate analytics data...")
    print()
    
    # Get the global scheduler and start it
    scheduler = get_global_scheduler()
    scheduler.start(blocking=False)
    
    try:
        # Run for 30 seconds
        for i in range(30):
            time.sleep(1)
            if (i + 1) % 10 == 0:
                print(f"\n⏱️  Progress: {i + 1}/30 seconds\n")
        
        print()
        print("=" * 70)
        print("✅ Test complete! Showing dashboard...")
        print("=" * 70)
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopping...")
    finally:
        scheduler.stop()
        time.sleep(1)  # Wait for tasks to finish
        
        # Show dashboard
        try:
            from autocron import show_dashboard
            print("\n📊 Dashboard Summary:\n")
            show_dashboard()
            
            print("\n" + "=" * 70)
            print("📈 Detailed Stats for 'quick_task':")
            print("=" * 70 + "\n")
            
            from autocron import show_task
            show_task("quick_task")
            
        except ImportError as e:
            print(f"\n❌ Dashboard not available: {e}")
            print("Install with: pip install autocron-scheduler[dashboard]")
        except Exception as e:
            print(f"\n⚠️  Error showing dashboard: {e}")
