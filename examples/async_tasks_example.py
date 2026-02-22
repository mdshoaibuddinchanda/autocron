"""
Async/Await Task Example

This example demonstrates async task support in AutoCron v1.2+.
You can now schedule async functions alongside regular sync functions.

Key Features:
- Schedule async functions with @schedule decorator
- Mix sync and async tasks in the same scheduler
- Async functions run efficiently without blocking
- Full support for retries, timeouts, and callbacks
"""

import asyncio
import time
from datetime import datetime

import aiohttp # pip install aiohttp (optional)

from autocron import AutoCron, schedule, start_scheduler


# Example 1: Basic Async Task
async def check_website():
 """Async function to check website status."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking website...")

 # Simulate async HTTP request
 await asyncio.sleep(1)

 print(" Website is up!")
 return "success"


# Example 2: Async Task with External Library
async def fetch_api_data():
 """Fetch data from an API asynchronously."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching API data...")

 # Example with aiohttp (if installed)
 try:
 async with aiohttp.ClientSession() as session:
 async with session.get("https://api.github.com") as response:
 data = await response.json()
 print(f" API Response: {response.status}")
 return data
 except ImportError:
 # Fallback if aiohttp not installed
 await asyncio.sleep(0.5)
 print(" API data fetched (simulated)")
 return {"status": "ok"}
 except Exception as e:
 print(f" API error: {e}")
 raise


# Example 3: Multiple Async Operations
async def process_data():
 """Process multiple items concurrently."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing data...")

 # Process multiple items concurrently
 async def process_item(item_id):
 await asyncio.sleep(0.3)
 return f"Item {item_id} processed"

 results = await asyncio.gather(
 process_item(1), process_item(2), process_item(3), process_item(4)
 )

 print(f" Processed {len(results)} items")
 return results


# Example 4: Async Task with Error Handling
async def flaky_task():
 """Async task that occasionally fails."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Running flaky task...")

 await asyncio.sleep(0.2)

 import random

 if random.random() < 0.3: # 30% failure rate
 raise Exception("Random failure!")

 print(" Flaky task succeeded")
 return "success"


# Example 5: Mix Sync and Async Tasks
def sync_task():
 """Regular synchronous task."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Running sync task...")
 time.sleep(0.5)
 print(" Sync task complete")


async def async_task():
 """Asynchronous task."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Running async task...")
 await asyncio.sleep(0.5)
 print(" Async task complete")


def example_scheduler_api():
 """Example using AutoCron class directly."""
 print("\n" + "=" * 60)
 print("Example 1: Using AutoCron Class API")
 print("=" * 60 + "\n")

 scheduler = AutoCron()

 # Add async tasks
 scheduler.add_task(name="website_check", func=check_website, every="5s")

 scheduler.add_task(name="data_processor", func=process_data, every="8s")

 scheduler.add_task(name="flaky_task", func=flaky_task, every="6s", retries=2, retry_delay=1)

 # Mix in a sync task
 scheduler.add_task(name="sync_task", func=sync_task, every="7s")

 print(f"Scheduled {len(scheduler.list_tasks())} tasks (mixed sync/async)")
 print("Running for 15 seconds...\n")

 # Run scheduler
 scheduler.start(blocking=False)
 time.sleep(15)
 scheduler.stop()

 print("\n Scheduler stopped\n")


def example_decorator_async():
 """Example using @schedule decorator with async functions."""
 print("=" * 60)
 print("Example 2: Using @schedule Decorator with Async")
 print("=" * 60 + "\n")

 @schedule(every="3s")
 async def monitor_service():
 """Monitor service health asynchronously."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring service...")
 await asyncio.sleep(0.5)
 print(" Service is healthy")

 @schedule(every="4s", retries=1)
 async def backup_data():
 """Backup data asynchronously."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Backing up data...")
 await asyncio.sleep(0.7)
 print(" Backup complete")

 @schedule(every="5s")
 def regular_task():
 """Regular sync task."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Running regular task...")
 time.sleep(0.3)
 print(" Regular task complete")

 print("Scheduled 3 tasks using decorator (2 async, 1 sync)")
 print("Running for 12 seconds...\n")

 # Start global scheduler
 start_scheduler(blocking=False)
 time.sleep(12)

 # Stop
 from autocron import get_global_scheduler

 scheduler = get_global_scheduler()
 if scheduler:
 scheduler.stop()

 print("\n Scheduler stopped\n")


def example_async_with_callbacks():
 """Example with success/failure callbacks for async tasks."""
 print("=" * 60)
 print("Example 3: Async Tasks with Callbacks")
 print("=" * 60 + "\n")

 success_count = [0]
 failure_count = [0]

 def on_success():
 success_count[0] += 1
 print(f" → Success callback (total: {success_count[0]})")

 def on_failure(error):
 failure_count[0] += 1
 print(f" → Failure callback (total: {failure_count[0]}): {error}")

 async def monitored_task():
 """Task with monitoring callbacks."""
 await asyncio.sleep(0.2)
 import random

 if random.random() < 0.4: # 40% failure
 raise Exception("Task failed!")
 return "success"

 scheduler = AutoCron()
 scheduler.add_task(
 name="monitored_task",
 func=monitored_task,
 every="2s",
 retries=1,
 retry_delay=1,
 on_success=on_success,
 on_failure=on_failure,
 )

 print("Running monitored task for 10 seconds...\n")

 scheduler.start(blocking=False)
 time.sleep(10)
 scheduler.stop()

 print("\n Statistics:")
 print(f" Successes: {success_count[0]}")
 print(f" Failures: {failure_count[0]}")
 print()


def example_async_timeout():
 """Example demonstrating async task timeout."""
 print("=" * 60)
 print("Example 4: Async Task Timeout")
 print("=" * 60 + "\n")

 async def slow_task():
 """Task that takes too long."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting slow task...")
 await asyncio.sleep(10) # Will timeout before this completes
 print("This won't be printed")

 async def fast_task():
 """Task that completes within timeout."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting fast task...")
 await asyncio.sleep(0.5)
 print(" Fast task completed")

 scheduler = AutoCron()

 # This task will timeout
 scheduler.add_task(name="slow_task", func=slow_task, every="5s", timeout=2, retries=0)

 # This task will succeed
 scheduler.add_task(name="fast_task", func=fast_task, every="3s", timeout=5)

 print("Testing timeout behavior (8 seconds)...\n")

 scheduler.start(blocking=False)
 time.sleep(8)
 scheduler.stop()

 print("\n Timeout test complete\n")


def example_real_world_async():
 """Real-world example: Async monitoring and notifications."""
 print("=" * 60)
 print("Example 5: Real-World Async Monitoring")
 print("=" * 60 + "\n")

 services = ["api.example.com", "db.example.com", "cache.example.com"]

 async def monitor_services():
 """Monitor multiple services concurrently."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring {len(services)} services...")

 async def check_service(service):
 await asyncio.sleep(0.3) # Simulate health check
 status = "healthy"
 print(f" {service}: {status}")
 return (service, status)

 # Check all services concurrently
 results = await asyncio.gather(*[check_service(s) for s in services])

 # All healthy
 print(f" All {len(results)} services healthy")
 return results

 async def aggregate_metrics():
 """Aggregate metrics from multiple sources."""
 print(f"[{datetime.now().strftime('%H:%M:%S')}] Aggregating metrics...")

 # Simulate fetching from multiple sources
 async def fetch_metrics(source):
 await asyncio.sleep(0.2)
 return {"source": source, "cpu": 45, "memory": 60}

 metrics = await asyncio.gather(
 fetch_metrics("server1"), fetch_metrics("server2"), fetch_metrics("server3")
 )

 avg_cpu = sum(m["cpu"] for m in metrics) / len(metrics)
 print(f" Average CPU across {len(metrics)} servers: {avg_cpu}%")
 return metrics

 scheduler = AutoCron()

 # Monitor every 5 seconds
 scheduler.add_task(name="service_monitor", func=monitor_services, every="5s")

 # Aggregate metrics every 8 seconds
 scheduler.add_task(name="metrics_aggregator", func=aggregate_metrics, every="8s")

 print("Running real-world monitoring simulation (15 seconds)...\n")

 scheduler.start(blocking=False)
 time.sleep(15)
 scheduler.stop()

 print("\n Monitoring complete\n")


if __name__ == "__main__":
 print("\n" + "=" * 60)
 print("AutoCron Async/Await Examples")
 print("=" * 60)

 example_scheduler_api()
 example_decorator_async()
 example_async_with_callbacks()
 example_async_timeout()
 example_real_world_async()

 print("=" * 60)
 print("All Examples Complete!")
 print("=" * 60 + "\n")
