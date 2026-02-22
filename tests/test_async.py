"""Tests for async task execution."""

import asyncio
import time

import pytest

from autocron.core.scheduler import AutoCron, TaskExecutionError


class TestAsyncTasks:
 """Test async/await task execution."""

 @pytest.fixture
 def scheduler(self):
 """Create a scheduler instance."""
 return AutoCron()

 @pytest.mark.asyncio
 async def test_basic_async_task(self, scheduler):
 """Test basic async task execution."""
 # Track execution
 executed = []

 async def async_task():
 await asyncio.sleep(0.1)
 executed.append(1)
 return "async result"

 # Add and start scheduler
 scheduler.add_task(name="async_task", func=async_task, every="1s")

 # Start scheduler in background
 import threading

 def run_scheduler():
 scheduler.start(blocking=False)
 time.sleep(2)
 scheduler.stop()

 thread = threading.Thread(target=run_scheduler, daemon=True)
 thread.start()
 thread.join(timeout=5)

 # Verify task executed
 assert executed

 def test_async_function_execution(self, scheduler):
 """Test direct async function execution."""
 result = []

 async def async_func():
 await asyncio.sleep(0.05)
 result.append("done")
 return "success"

 # Execute directly
 ret = scheduler._execute_function(async_func, timeout=5)

 assert ret == "success"
 assert result == ["done"]

 def test_async_function_timeout(self, scheduler):
 """Test async function with timeout."""

 async def slow_async_func():
 await asyncio.sleep(10)
 return "should not reach"

 with pytest.raises(TaskExecutionError, match="timed out"):
 scheduler._execute_function(slow_async_func, timeout=1)

 def test_async_function_error(self, scheduler):
 """Test async function that raises error."""

 async def failing_async_func():
 await asyncio.sleep(0.05)
 raise ValueError("Async task failed")

 with pytest.raises(ValueError, match="Async task failed"):
 scheduler._execute_function(failing_async_func, timeout=5)

 def test_mixed_sync_and_async_tasks(self, scheduler):
 """Test scheduler with both sync and async tasks."""
 sync_executed = []
 async_executed = []

 def sync_task():
 time.sleep(0.1)
 sync_executed.append(1)

 async def async_task():
 await asyncio.sleep(0.1)
 async_executed.append(1)

 # Add both types of tasks
 scheduler.add_task(name="sync_task", func=sync_task, every="1s")
 scheduler.add_task(name="async_task", func=async_task, every="1s")

 # Start scheduler briefly
 scheduler.start(blocking=False)
 time.sleep(2)
 scheduler.stop()

 # Both should have executed
 assert sync_executed
 assert async_executed

 def test_async_task_with_retries(self, scheduler):
 """Test async task with retry logic."""
 attempts = []

 async def flaky_async_task():
 await asyncio.sleep(0.05)
 attempts.append(1)
 # sourcery skip: no-conditionals-in-tests
 if len(attempts) < 2:
 raise ValueError("First attempt fails")
 return "success"

 # Add task with retries
 scheduler.add_task(
 name="flaky_task", func=flaky_async_task, every="1s", retries=2, retry_delay=1
 )

 # Start scheduler
 scheduler.start(blocking=False)
 time.sleep(4)
 scheduler.stop()

 # Should have retried and succeeded
 assert len(attempts) >= 2

 def test_async_task_with_callback(self, scheduler):
 """Test async task with success/failure callbacks."""
 success_called = []
 failure_called = []

 def on_success():
 success_called.append(1)

 def on_failure(error):
 failure_called.append(str(error))

 async def async_task():
 await asyncio.sleep(0.05)
 return "done"

 # Add task with callbacks
 scheduler.add_task(
 name="callback_task",
 func=async_task,
 every="1s",
 on_success=on_success,
 on_failure=on_failure,
 )

 # Start scheduler
 scheduler.start(blocking=False)
 time.sleep(2)
 scheduler.stop()

 # Success callback should be called
 assert success_called
 assert not failure_called

 def test_async_task_failure_callback(self, scheduler):
 """Test async task failure callback."""
 failure_called = []

 def on_failure(error):
 failure_called.append(str(error))

 async def failing_task():
 await asyncio.sleep(0.05)
 raise RuntimeError("Async failure")

 # Add task with failure callback
 scheduler.add_task(
 name="failing_task", func=failing_task, every="1s", retries=0, on_failure=on_failure
 )

 # Start scheduler
 scheduler.start(blocking=False)
 time.sleep(2)
 scheduler.stop()

 # Failure callback should be called
 assert failure_called
 assert "Async failure" in failure_called[0]

 def test_async_task_without_timeout(self, scheduler):
 """Test async task executes without timeout."""
 result = []

 async def async_task():
 await asyncio.sleep(0.1)
 result.append("done")

 # Execute without timeout
 scheduler._execute_function(async_task, timeout=None)

 assert result == ["done"]

 def test_async_with_asyncio_operations(self, scheduler):
 """Test async task with various asyncio operations."""
 results = []

 async def complex_async_task():
 # Multiple async operations
 await asyncio.sleep(0.05)
 results.append("step1")

 await asyncio.sleep(0.05)
 results.append("step2")

 # Concurrent operations
 await asyncio.gather(asyncio.sleep(0.05), asyncio.sleep(0.05))
 results.append("step3")

 return "complete"

 ret = scheduler._execute_function(complex_async_task, timeout=5)

 assert ret == "complete"
 assert results == ["step1", "step2", "step3"]

 def test_sync_function_still_works(self, scheduler):
 """Ensure sync functions still work after async support."""
 result = []

 def sync_func():
 time.sleep(0.1)
 result.append("sync")
 return "sync_result"

 ret = scheduler._execute_function(sync_func, timeout=5)

 assert ret == "sync_result"
 assert result == ["sync"]

 def test_sync_function_timeout(self, scheduler):
 """Test sync function timeout still works."""

 def slow_sync_func():
 time.sleep(10)
 return "should not reach"

 with pytest.raises(TaskExecutionError, match="timed out"):
 scheduler._execute_function(slow_sync_func, timeout=1)


class TestAsyncTaskIntegration:
 """Integration tests for async tasks."""

 @pytest.fixture
 def scheduler(self):
 """Create a scheduler instance."""
 return AutoCron()

 def test_async_decorator(self, scheduler):
 """Test @schedule decorator with async functions."""
 from autocron.core.scheduler import get_global_scheduler, reset_global_scheduler, schedule

 # Reset any existing global scheduler
 reset_global_scheduler()

 executed = []

 @schedule(every="1s")
 async def async_scheduled():
 await asyncio.sleep(0.05)
 executed.append(1)

 # Get global scheduler and start
 global_sched = get_global_scheduler()
 assert global_sched is not None

 global_sched.start(blocking=False)
 time.sleep(2)
 global_sched.stop()

 # Task should have executed
 assert executed

 # Cleanup
 reset_global_scheduler()

 def test_multiple_async_tasks_concurrent(self, scheduler):
 """Test multiple async tasks running concurrently."""
 task1_count = []
 task2_count = []
 task3_count = []

 async def task1():
 await asyncio.sleep(0.1)
 task1_count.append(1)

 async def task2():
 await asyncio.sleep(0.15)
 task2_count.append(1)

 async def task3():
 await asyncio.sleep(0.2)
 task3_count.append(1)

 # Add all tasks
 scheduler.add_task(name="task1", func=task1, every="1s")
 scheduler.add_task(name="task2", func=task2, every="1s")
 scheduler.add_task(name="task3", func=task3, every="1s")

 # Start scheduler
 scheduler.start(blocking=False)
 time.sleep(3)
 scheduler.stop()

 # All should have executed
 assert len(task1_count) >= 2
 assert task2_count
 assert task3_count
