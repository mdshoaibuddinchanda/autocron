"""Tests for scheduler functionality."""

import pytest
import time
from datetime import datetime
from autocron.scheduler import AutoCron, Task, schedule, SchedulingError


class TestTask:
    """Test Task class."""

    def test_create_task_with_function(self):
        """Test creating task with function."""

        def my_func():
            return "test"

        task = Task(name="test_task", func=my_func, every="5m")

        assert task.name == "test_task"
        assert task.func == my_func
        assert task.script is None
        assert task.schedule_type == "interval"
        assert task.schedule_value == "5m"
        assert task.interval_seconds == 300

    def test_create_task_with_script(self):
        """Test creating task with script."""
        task = Task(name="test_task", script="test.py", cron="0 9 * * *")

        assert task.name == "test_task"
        assert task.script == "test.py"
        assert task.func is None
        assert task.schedule_type == "cron"
        assert task.schedule_value == "0 9 * * *"

    def test_task_requires_func_or_script(self):
        """Test that task requires func or script."""
        with pytest.raises(ValueError, match="Either func or script must be provided"):
            Task(name="test_task", every="5m")

    def test_task_requires_schedule(self):
        """Test that task requires schedule."""

        def my_func():
            pass

        with pytest.raises(ValueError, match="Either every or cron must be provided"):
            Task(name="test_task", func=my_func)

    def test_task_invalid_cron(self):
        """Test invalid cron expression."""

        def my_func():
            pass

        with pytest.raises(ValueError, match="Invalid cron expression"):
            Task(name="test_task", func=my_func, cron="invalid")

    def test_should_run_when_due(self):
        """Test should_run when task is due."""

        def my_func():
            pass

        task = Task(name="test_task", func=my_func, every="1s")

        # Should run immediately
        assert task.should_run()

        # Update next run to future
        task.update_next_run()
        time.sleep(0.1)

        # Should not run yet
        assert not task.should_run()

    def test_task_disabled(self):
        """Test disabled task."""

        def my_func():
            pass

        task = Task(name="test_task", func=my_func, every="1s")
        task.enabled = False

        assert not task.should_run()


class TestAutoCron:
    """Test AutoCron scheduler."""

    def test_create_scheduler(self):
        """Test creating scheduler."""
        scheduler = AutoCron()

        assert scheduler is not None
        assert len(scheduler.tasks) == 0
        assert not scheduler._running

    def test_add_task(self):
        """Test adding task."""
        scheduler = AutoCron()

        def my_func():
            return "test"

        task_id = scheduler.add_task(name="test_task", func=my_func, every="5m")

        assert task_id is not None
        assert len(scheduler.tasks) == 1
        assert task_id in scheduler.tasks

    def test_add_multiple_tasks(self):
        """Test adding multiple tasks."""
        scheduler = AutoCron()

        def func1():
            pass

        def func2():
            pass

        id1 = scheduler.add_task(name="task1", func=func1, every="5m")
        id2 = scheduler.add_task(name="task2", func=func2, every="10m")

        assert len(scheduler.tasks) == 2
        assert id1 != id2

    def test_remove_task_by_id(self):
        """Test removing task by ID."""
        scheduler = AutoCron()

        def my_func():
            pass

        task_id = scheduler.add_task(name="test_task", func=my_func, every="5m")

        assert len(scheduler.tasks) == 1

        removed = scheduler.remove_task(task_id=task_id)

        assert removed
        assert len(scheduler.tasks) == 0

    def test_remove_task_by_name(self):
        """Test removing task by name."""
        scheduler = AutoCron()

        def my_func():
            pass

        scheduler.add_task(name="test_task", func=my_func, every="5m")

        removed = scheduler.remove_task(name="test_task")

        assert removed
        assert len(scheduler.tasks) == 0

    def test_get_task_by_id(self):
        """Test getting task by ID."""
        scheduler = AutoCron()

        def my_func():
            pass

        task_id = scheduler.add_task(name="test_task", func=my_func, every="5m")
        task = scheduler.get_task(task_id=task_id)

        assert task is not None
        assert task.name == "test_task"

    def test_get_task_by_name(self):
        """Test getting task by name."""
        scheduler = AutoCron()

        def my_func():
            pass

        scheduler.add_task(name="test_task", func=my_func, every="5m")
        task = scheduler.get_task(name="test_task")

        assert task is not None
        assert task.name == "test_task"

    def test_list_tasks(self):
        """Test listing tasks."""
        scheduler = AutoCron()

        def func1():
            pass

        def func2():
            pass

        scheduler.add_task(name="task1", func=func1, every="5m")
        scheduler.add_task(name="task2", func=func2, every="10m")

        tasks = scheduler.list_tasks()

        assert len(tasks) == 2
        assert tasks[0].name in ["task1", "task2"]
        assert tasks[1].name in ["task1", "task2"]

    def test_execute_function_task(self):
        """Test executing function task."""
        scheduler = AutoCron()

        executed = []

        def my_func():
            executed.append(True)

        task_id = scheduler.add_task(name="test_task", func=my_func, every="1s")
        task = scheduler.get_task(task_id=task_id)

        # Execute task directly
        scheduler._execute_task(task)

        assert len(executed) == 1
        assert task.run_count == 1

    def test_execute_function_with_retry(self):
        """Test executing function with retry."""
        scheduler = AutoCron()

        call_count = []

        def failing_func():
            call_count.append(1)
            # sourcery skip: no-conditionals-in-tests
            if len(call_count) < 2:
                # sourcery skip: raise-specific-error
                raise Exception("Test error")

        task_id = scheduler.add_task(
            name="test_task", func=failing_func, every="1s", retries=2, retry_delay=1
        )
        task = scheduler.get_task(task_id=task_id)

        # Execute task
        scheduler._execute_task(task)

        # Should have retried and succeeded
        assert len(call_count) == 2
        assert task.run_count == 1
        assert task.fail_count == 1

    def test_execute_function_with_timeout(self):
        """Test executing function with timeout."""
        scheduler = AutoCron()

        def slow_func():
            time.sleep(5)

        task_id = scheduler.add_task(name="test_task", func=slow_func, every="1s", timeout=1)
        task = scheduler.get_task(task_id=task_id)

        # Execute task (should timeout)
        scheduler._execute_task(task)

        assert task.run_count == 0
        assert task.fail_count == 1


class TestScheduleDecorator:
    """Test schedule decorator."""

    def test_decorator_basic(self):
        """Test basic decorator usage."""
        executed = []

        @schedule(every="5m")
        def my_task():
            executed.append(True)

        # Function should be registered
        from autocron.scheduler import get_global_scheduler

        scheduler = get_global_scheduler()

        assert scheduler is not None
        assert len(scheduler.tasks) > 0

    def test_decorator_with_cron(self):
        """Test decorator with cron."""

        @schedule(cron="0 9 * * *")
        def my_task():
            pass

        from autocron.scheduler import get_global_scheduler

        scheduler = get_global_scheduler()

        task = scheduler.get_task(name="my_task")
        assert task is not None
        assert task.schedule_type == "cron"

    def test_decorator_function_callable(self):
        """Test that decorated function is still callable."""

        @schedule(every="5m")
        def my_func():
            return "test"

        result = my_func()
        assert result == "test"


class TestAdvancedScheduler:
    """Test advanced scheduler functionality."""

    def test_task_with_callbacks(self):
        """Test task with success/failure callbacks."""
        scheduler = AutoCron()
        success_called = []
        failure_called = []

        def on_success():
            success_called.append(True)

        def on_failure(error):
            failure_called.append(error)

        def success_task():
            return "done"

        task_id = scheduler.add_task(
            name="callback_task", func=success_task, every="1s", on_success=on_success
        )

        task = scheduler.get_task(task_id=task_id)
        scheduler._execute_task(task)

        assert len(success_called) == 1

    def test_task_timeout(self):
        """Test task timeout handling."""
        scheduler = AutoCron()

        def slow_task():
            import time

            time.sleep(10)

        task_id = scheduler.add_task(name="slow_task", func=slow_task, every="1m", timeout=1)

        task = scheduler.get_task(task_id=task_id)
        # Should handle timeout gracefully
        scheduler._execute_task(task)

        assert task.fail_count > 0

    def test_scheduler_warning_when_already_running(self):
        """Test warning when starting already running scheduler."""
        scheduler = AutoCron()
        scheduler.add_task(name="test", func=lambda: None, every="1h")

        scheduler._running = True
        scheduler.start(blocking=False)
        # Should log warning

        scheduler._running = False

    def test_stop_scheduler_when_not_running(self):
        """Test stopping scheduler that's not running."""
        scheduler = AutoCron()
        scheduler.stop()
        # Should not raise error

    def test_task_repr(self):
        """Test task string representation."""
        from autocron.scheduler import Task

        task = Task(name="test_task", func=lambda: None, every="5m")
        repr_str = repr(task)

        assert "test_task" in repr_str
        assert "interval" in repr_str
        assert "enabled=True" in repr_str
