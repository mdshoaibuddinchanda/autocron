"""Integration tests for AutoCron."""

import os
import time

import pytest

from autocron import AutoCron, schedule


@pytest.mark.integration
class TestIntegration:
 """Integration tests."""

 def test_complete_workflow(self, test_script):
 """Test complete workflow from start to finish."""
 scheduler = AutoCron(log_level="DEBUG")

 # Add task
 task_id = scheduler.add_task(
 name="test_integration", script=test_script, every="2s", retries=1
 )

 assert task_id is not None

 # Get task
 task = scheduler.get_task(task_id=task_id)
 assert task is not None
 assert task.name == "test_integration"

 # Start scheduler in background
 scheduler.start(blocking=False)

 # Wait for task to run
 time.sleep(3)

 # Check execution
 task = scheduler.get_task(task_id=task_id)
 assert task.run_count >= 1

 # Stop scheduler
 scheduler.stop()

 def test_multiple_tasks_execution(self):
 """Test executing multiple tasks."""
 scheduler = AutoCron()

 executed_tasks = []

 def task1():
 executed_tasks.append("task1")

 def task2():
 executed_tasks.append("task2")

 scheduler.add_task(name="task1", func=task1, every="1s")
 scheduler.add_task(name="task2", func=task2, every="1s")

 # Start and wait
 scheduler.start(blocking=False)
 time.sleep(2)
 scheduler.stop()

 # Both tasks should have executed
 assert "task1" in executed_tasks
 assert "task2" in executed_tasks

 def test_decorator_integration(self):
 """Test decorator integration."""
 executed = []

 @schedule(every="1s")
 def my_task():
 executed.append(True)

 # Get global scheduler and start
 from autocron.core.scheduler import get_global_scheduler, start_scheduler

 scheduler = get_global_scheduler()
 assert scheduler is not None

 # Start in background
 import threading

 thread = threading.Thread(target=lambda: start_scheduler(blocking=True), daemon=True)
 thread.start()

 # Wait for execution
 time.sleep(2)

 scheduler.stop()

 assert executed

 def test_task_retry_mechanism(self):
 """Test task retry mechanism."""
 scheduler = AutoCron()

 call_count = []

 def failing_task():
 call_count.append(1)
 # sourcery skip: no-conditionals-in-tests
 if len(call_count) < 3:
 # sourcery skip: raise-specific-error
 raise Exception("Intentional code failure")

 task_id = scheduler.add_task(
 name="retry_test", func=failing_task, every="1s", retries=3, retry_delay=1
 )

 # Execute task directly (not through scheduler)
 task = scheduler.get_task(task_id=task_id)
 scheduler._execute_task(task)

 # Should have retried and succeeded on 3rd attempt
 assert len(call_count) == 3
 assert task.run_count == 1
 assert task.fail_count == 2

 def test_config_file_loading(self, temp_dir):
 """Test loading configuration from file."""
 config_path = os.path.join(temp_dir, "autocron.yaml")

 config_content = """
tasks:
 - name: test_task
 script: test.py
 schedule: "*/5 * * * *"
 retries: 2

logging:
 level: INFO
"""

 with open(config_path, "w") as f:
 f.write(config_content)

 # Create dummy script
 script_path = os.path.join(temp_dir, "test.py")
 with open(script_path, "w") as f:
 f.write('print("Test")')

 # Change config to use existing script
 config_content = f"""
tasks:
 - name: test_task
 script: {script_path}
 schedule: "*/5 * * * *"
 retries: 2

logging:
 level: INFO
"""
 with open(config_path, "w") as f:
 f.write(config_content)

 # Load configuration
 scheduler = AutoCron.from_config(config_path)

 assert scheduler is not None
 assert len(scheduler.tasks) == 1

 task = scheduler.list_tasks()[0]
 assert task.name == "test_task"
 assert task.retries == 2
