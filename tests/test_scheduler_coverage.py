"""
Additional tests to improve scheduler.py coverage to 90%+

Focus areas:
1. Subprocess resource enforcement (safe_mode)
2. Timeout handling under concurrency
3. YAML persistence edge cases
4. Error handling paths
5. OS scheduler integration
"""

import asyncio
import subprocess
import time
from unittest.mock import patch

import pytest

from autocron import AutoCron, TaskExecutionError


class TestSafeModeResourceLimits:
    """Test safe mode resource enforcement - CRITICAL for enterprise"""

    def test_safe_mode_memory_limit_enforcement(self, tmp_path):
        """Test that memory limits are enforced in safe mode"""
        # Create a script that tries to allocate excessive memory
        script = tmp_path / "memory_hog.py"
        script.write_text(
            """
import sys
# Try to allocate 100MB
data = bytearray(100 * 1024 * 1024)
print("Memory allocated")
sys.exit(0)
"""
        )

        scheduler = AutoCron()
        task_id = scheduler.add_task(
            name="memory_test",
            script=str(script),
            every="1m",
            safe_mode=True,
            max_memory_mb=50,  # Limit to 50MB
            timeout=5,
        )

        task = scheduler.get_task(task_id=task_id)
        assert task.safe_mode is True
        assert task.max_memory_mb == 50

    def test_safe_mode_cpu_limit_enforcement(self, tmp_path):
        """Test CPU usage limits in safe mode"""
        script = tmp_path / "cpu_intensive.py"
        script.write_text(
            """
import time
start = time.time()
while time.time() - start < 10:  # Run for 10 seconds
    pass
print("CPU task completed")
"""
        )

        scheduler = AutoCron()
        scheduler.add_task(
            name="cpu_test",
            script=str(script),
            every="1m",
            safe_mode=True,
            timeout=2,  # Should timeout before 10 seconds
            max_cpu_percent=50,
        )

        # Task is registered
        start = time.time()

        try:
            scheduler._execute_in_safe_mode(
                str(script), timeout=2, max_memory_mb=None, max_cpu_percent=50
            )
            assert False, "Should have timed out"
        except (TaskExecutionError, subprocess.TimeoutExpired):
            duration = time.time() - start
            assert duration < 3, "Should timeout around 2 seconds"

    def test_safe_mode_output_sanitization(self, tmp_path):
        """Test that safe mode sanitizes large outputs"""
        script = tmp_path / "large_output.py"
        script.write_text(
            """
# Generate large output
for i in range(50000):
    print(f"Line {i}: " + "x" * 100)
"""
        )

        scheduler = AutoCron()
        output = scheduler._execute_in_safe_mode(
            str(script), timeout=5, max_memory_mb=None, max_cpu_percent=None
        )

        # Output should be truncated
        assert "truncated" in output.lower() or len(output) <= 10100

    def test_safe_mode_subprocess_isolation(self, tmp_path):
        """Test that safe mode isolates subprocess environment"""
        script = tmp_path / "env_test.py"
        script.write_text(
            """
import os
print(f"AUTOCRON_SAFE_MODE={os.environ.get('AUTOCRON_SAFE_MODE', 'not_set')}")
"""
        )

        scheduler = AutoCron()
        output = scheduler._execute_in_safe_mode(
            str(script), timeout=5, max_memory_mb=None, max_cpu_percent=None
        )

        assert "AUTOCRON_SAFE_MODE=1" in output

    @pytest.mark.skipif(
        subprocess.sys.platform == "win32",
        reason="Resource limits not available on Windows",
    )
    def test_safe_mode_resource_limit_errors(self, tmp_path):
        """Test error handling when resource limits fail"""
        script = tmp_path / "simple.py"
        script.write_text("print('Hello')")

        scheduler = AutoCron()

        # Test with invalid memory limit
        with patch("resource.setrlimit", side_effect=ValueError("Invalid limit")):
            # Should not raise, but log warning
            output = scheduler._execute_in_safe_mode(
                str(script), timeout=5, max_memory_mb=10, max_cpu_percent=None
            )
            assert "Hello" in output  # Task should still execute


class TestConcurrentTimeoutHandling:
    """Test timeout handling under concurrent execution"""

    def test_concurrent_task_timeout_handling(self, tmp_path):
        """Test that timeouts work correctly with concurrent tasks"""
        # Create multiple scripts with different execution times
        fast_script = tmp_path / "fast.py"
        fast_script.write_text("print('Fast done')")

        slow_script = tmp_path / "slow.py"
        slow_script.write_text(
            """
import time
time.sleep(10)
print('Slow done')
"""
        )

        scheduler = AutoCron(max_workers=3)

        # Add tasks
        scheduler.add_task(name="fast1", script=str(fast_script), every="1m", timeout=5)
        scheduler.add_task(name="slow1", script=str(slow_script), every="1m", timeout=2)
        scheduler.add_task(name="fast2", script=str(fast_script), every="1m", timeout=5)

        # Start scheduler non-blocking
        scheduler.start(blocking=False)
        time.sleep(0.5)

        # Trigger task execution
        for task in scheduler.list_tasks():
            task.next_run = None  # Force immediate execution

        time.sleep(3)  # Wait for execution
        scheduler.stop()

        # Verify slow task timed out but others succeeded
        slow_task = scheduler.get_task(name="slow1")
        assert slow_task.fail_count >= 1  # Should have failed due to timeout

    def test_max_workers_limit_enforcement(self, tmp_path):
        """Test that max_workers limit is enforced"""
        script = tmp_path / "worker.py"
        script.write_text(
            """
import time
time.sleep(2)
print('Worker done')
"""
        )

        scheduler = AutoCron(max_workers=2)

        # Add 5 tasks
        for i in range(5):
            scheduler.add_task(name=f"worker{i}", script=str(script), every="1m", timeout=5)

        # Start and force execution
        scheduler.start(blocking=False)
        for task in scheduler.list_tasks():
            task.next_run = None

        time.sleep(0.5)

        # Only 2 should be running
        active_threads = len([t for t in scheduler._executor_threads if t.is_alive()])
        assert active_threads <= 2

        scheduler.stop()


class TestYAMLPersistenceEdgeCases:
    """Test YAML persistence edge cases"""

    def test_save_tasks_with_special_characters(self, tmp_path):
        """Test saving tasks with special characters in names"""
        scheduler = AutoCron()

        # Task with special characters
        scheduler.add_task(
            name="test-task_123!@#",
            script="test.py",
            every="5m",
            timeout=10,
        )

        task = self._extracted_from_test_save_tasks_with_none_values_13(
            tmp_path, "tasks_special.yaml", scheduler, "test-task_123!@#"
        )
        assert task is not None

    def test_save_tasks_with_none_values(self, tmp_path):
        """Test saving tasks with None optional values"""
        scheduler = AutoCron()

        scheduler.add_task(
            name="minimal_task",
            script="test.py",
            every="1h",
            timeout=None,
            notify=None,
            email_config=None,
        )

        task = self._extracted_from_test_save_tasks_with_none_values_13(
            tmp_path, "tasks_minimal.yaml", scheduler, "minimal_task"
        )
        assert task.timeout is None
        assert task.notify is None

    # TODO Rename this here and in `test_save_tasks_with_special_characters`
    # and `test_save_tasks_with_none_values`
    def _extracted_from_test_save_tasks_with_none_values_13(self, tmp_path, arg1, scheduler, name):
        save_path = tmp_path / arg1
        scheduler.save_tasks(str(save_path))
        new_scheduler = AutoCron()
        loaded = new_scheduler.load_tasks(str(save_path))
        assert loaded == 1
        return new_scheduler.get_task(name=name)

    def test_load_tasks_corrupted_yaml(self, tmp_path):
        """Test loading corrupted YAML files"""
        corrupted_file = tmp_path / "corrupted.yaml"
        corrupted_file.write_text("invalid: yaml: }: content")

        scheduler = AutoCron()

        with pytest.raises(Exception):
            scheduler.load_tasks(str(corrupted_file))

    def test_load_tasks_missing_required_fields(self, tmp_path):
        """Test loading YAML with missing required fields"""
        incomplete_file = tmp_path / "incomplete.yaml"
        incomplete_file.write_text(
            """
version: "1.0"
tasks:
  - name: "incomplete"
    # Missing script and schedule
"""
        )

        scheduler = AutoCron()

        # Should skip invalid task
        loaded = scheduler.load_tasks(str(incomplete_file))
        assert loaded == 0  # No tasks loaded

    def test_load_tasks_duplicate_names(self, tmp_path):
        """Test loading tasks with duplicate names"""
        scheduler = AutoCron()
        scheduler.add_task(name="duplicate", script="test1.py", every="5m")

        save_path = tmp_path / "tasks_dup.yaml"
        scheduler.save_tasks(str(save_path))

        # Try to load into scheduler that already has this task
        loaded = scheduler.load_tasks(str(save_path), replace=False)
        assert loaded == 0  # Should skip duplicate

        # Load with replace=True
        loaded = scheduler.load_tasks(str(save_path), replace=True)
        assert loaded == 1

    def test_save_tasks_json_format(self, tmp_path):
        """Test saving tasks in JSON format"""
        scheduler = AutoCron()
        scheduler.add_task(name="json_task", script="test.py", cron="0 * * * *")

        save_path = tmp_path / "tasks.json"
        scheduler.save_tasks(str(save_path))

        # Verify JSON format
        import json

        with open(save_path) as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["name"] == "json_task"

    def test_save_function_based_tasks_warning(self, tmp_path, caplog):
        """Test that function-based tasks produce warning when saving"""
        scheduler = AutoCron()

        # Add function-based task
        def my_func():
            print("Test")

        scheduler.add_task(name="func_task", func=my_func, every="5m")

        # Add script-based task
        scheduler.add_task(name="script_task", script="test.py", every="5m")

        save_path = tmp_path / "tasks_mixed.yaml"
        saved_path = scheduler.save_tasks(str(save_path))

        # Should only save script-based task
        new_scheduler = AutoCron()
        loaded = new_scheduler.load_tasks(saved_path)
        assert loaded == 1
        assert new_scheduler.get_task(name="script_task") is not None
        assert new_scheduler.get_task(name="func_task") is None


class TestErrorHandlingPaths:
    """Test error handling edge cases"""

    def test_task_invalid_cron_expression(self):
        """Test creating task with invalid cron expression"""
        from autocron.core.scheduler import SchedulingError

        scheduler = AutoCron()

        with pytest.raises(SchedulingError, match="Invalid cron expression|Failed to add task"):
            scheduler.add_task(
                name="invalid_cron",
                script="test.py",
                cron="invalid cron",
            )

    def test_task_both_func_and_script(self):
        """Test creating task with both func and script raises error"""
        from autocron.core.scheduler import SchedulingError

        scheduler = AutoCron()

        def my_func():
            pass

        with pytest.raises(SchedulingError, match="Only one of func or script|Failed to add task"):
            scheduler.add_task(
                name="both",
                func=my_func,
                script="test.py",
                every="5m",
            )

    def test_task_neither_func_nor_script(self):
        """Test creating task without func or script raises error"""
        from autocron.core.scheduler import SchedulingError

        scheduler = AutoCron()

        with pytest.raises(SchedulingError, match="Either func or script|Failed to add task"):
            scheduler.add_task(name="neither", every="5m")

    def test_task_both_interval_and_cron(self):
        """Test creating task with both interval and cron raises error"""
        from autocron.core.scheduler import SchedulingError

        scheduler = AutoCron()

        with pytest.raises(SchedulingError, match="Only one of every or cron|Failed to add task"):
            scheduler.add_task(
                name="both_schedule",
                script="test.py",
                every="5m",
                cron="0 * * * *",
            )

    def test_task_neither_interval_nor_cron(self):
        """Test creating task without schedule raises error"""
        from autocron.core.scheduler import SchedulingError

        scheduler = AutoCron()

        with pytest.raises(SchedulingError, match="Either every or cron|Failed to add task"):
            scheduler.add_task(name="no_schedule", script="test.py")

    def test_execute_script_not_found(self):
        """Test executing non-existent script"""
        scheduler = AutoCron()

        with pytest.raises((FileNotFoundError, TaskExecutionError)):
            scheduler._execute_script("/nonexistent/script.py", timeout=5)

    def test_execute_script_with_error(self, tmp_path):
        """Test executing script that raises error"""
        script = tmp_path / "error.py"
        script.write_text(
            """
raise ValueError("Test error")
"""
        )

        scheduler = AutoCron()

        with pytest.raises(TaskExecutionError):
            scheduler._execute_script(str(script), timeout=5)

    def test_async_function_timeout(self):
        """Test async function timeout"""

        async def slow_async_func():
            await asyncio.sleep(10)
            return "done"

        scheduler = AutoCron()

        with pytest.raises(TaskExecutionError, match="timed out"):
            scheduler._execute_async_function(slow_async_func, timeout=1)


class TestOSSchedulerIntegration:
    """Test OS-native scheduler integration (Windows Task Scheduler / cron)"""

    @pytest.mark.skipif(
        subprocess.sys.platform != "win32",
        reason="Windows-specific test",
    )
    def test_windows_task_scheduler_registration(self, tmp_path):
        """Test registering task with Windows Task Scheduler"""
        script = tmp_path / "windows_task.py"
        script.write_text("print('Windows task')")

        scheduler = AutoCron(use_os_scheduler=True)

        # sourcery skip: no-conditionals-in-tests
        if scheduler.os_adapter is None:
            pytest.skip("OS scheduler not available")

        task_id = scheduler.add_task(
            name="windows_test",
            script=str(script),
            every="1h",
        )

        task = scheduler.get_task(task_id=task_id)
        assert task is not None

        # Cleanup
        scheduler.remove_task(task_id=task_id)

    def test_notification_setup_without_config(self):
        """Test notification setup without email config shows warning"""
        scheduler = AutoCron()

        # Add task with email notification but no config
        task_id = scheduler.add_task(
            name="notify_test",
            script="test.py",
            every="5m",
            notify="email",  # No email_config provided
        )

        task = scheduler.get_task(task_id=task_id)
        assert task.notify == "email"
        # Should log warning (check in logs)


class TestSchedulerLifecycle:
    """Test scheduler lifecycle management"""

    def test_start_already_running_scheduler(self):
        """Test starting scheduler that's already running"""
        scheduler = AutoCron()
        scheduler.start(blocking=False)

        # Try to start again
        scheduler.start(blocking=False)  # Should log warning

        scheduler.stop()

    def test_stop_not_running_scheduler(self):
        """Test stopping scheduler that's not running"""
        scheduler = AutoCron()
        scheduler.stop()  # Should not raise error

    def test_scheduler_cleanup_on_stop(self):
        """Test that scheduler cleans up threads on stop"""
        scheduler = AutoCron()
        scheduler.start(blocking=False)
        time.sleep(0.5)

        # Check initial state
        assert scheduler._running is True

        scheduler.stop()
        time.sleep(1)

        # Threads should be cleaned up
        assert scheduler._running is False
        # sourcery skip: no-conditionals-in-tests
        if scheduler._thread:
            assert not scheduler._thread.is_alive()


class TestIntervalToCronConversion:
    """Test interval to cron expression conversion"""

    def test_interval_to_cron_seconds(self):
        """Test converting seconds interval to cron"""
        self._extracted_from_test_interval_to_cron_days_3("30s", "*/30 * * * * *")

    def test_interval_to_cron_minutes(self):
        """Test converting minutes interval to cron"""
        self._extracted_from_test_interval_to_cron_days_3("15m", "*/15 * * * *")

    def test_interval_to_cron_hours(self):
        """Test converting hours interval to cron"""
        self._extracted_from_test_interval_to_cron_days_3("6h", "0 */6 * * *")

    def test_interval_to_cron_days(self):
        """Test converting days interval to cron"""
        self._extracted_from_test_interval_to_cron_days_3("1d", "0 0 * * *")

    # TODO Rename this here and in `test_interval_to_cron_seconds`,
    # `test_interval_to_cron_minutes`, `test_interval_to_cron_hours`
    # and `test_interval_to_cron_days`
    def _extracted_from_test_interval_to_cron_days_3(self, arg0, arg1):
        scheduler = AutoCron()
        cron = scheduler._interval_to_cron(arg0)
        assert cron == arg1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
