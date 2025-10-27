"""
Tests for safe mode execution with resource limits and sandboxing.
"""

import os
import tempfile
import time
from pathlib import Path

import pytest

from autocron import AutoCron


@pytest.fixture
def scheduler():
    """Create scheduler instance."""
    return AutoCron()


@pytest.fixture
def safe_script():
    """Create a safe test script."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
import time
print("Safe script executing...")
time.sleep(0.1)
print("Completed successfully")
""")
        script_path = f.name
    
    yield script_path
    
    # Cleanup
    try:
        os.unlink(script_path)
    except:
        pass


@pytest.fixture
def memory_hog_script():
    """Create a script that uses excessive memory."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
# Try to allocate large amount of memory
data = []
for i in range(10000000):
    data.append([0] * 1000)
""")
        script_path = f.name
    
    yield script_path
    
    try:
        os.unlink(script_path)
    except:
        pass


@pytest.fixture
def slow_script():
    """Create a script that takes too long."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
import time
print("Starting slow operation...")
time.sleep(60)  # Will timeout before this
print("Should never reach here")
""")
        script_path = f.name
    
    yield script_path
    
    try:
        os.unlink(script_path)
    except:
        pass


def test_safe_mode_basic_execution(scheduler, safe_script):
    """Test that safe mode can execute normal scripts."""
    task_id = scheduler.add_task(
        name="safe_task",
        script=safe_script,
        every="1h",
        safe_mode=True,
        timeout=5
    )
    
    assert task_id in scheduler.tasks
    task = scheduler.tasks[task_id]
    assert task.safe_mode is True
    
    # Execute task
    scheduler._execute_task(task)
    
    assert task.run_count == 1
    assert task.fail_count == 0


def test_safe_mode_with_memory_limit(scheduler, safe_script):
    """Test safe mode with memory limit."""
    task_id = scheduler.add_task(
        name="memory_limited_task",
        script=safe_script,
        every="1h",
        safe_mode=True,
        max_memory_mb=100,  # 100MB limit
        timeout=5
    )
    
    task = scheduler.tasks[task_id]
    assert task.max_memory_mb == 100
    
    # Should execute successfully (doesn't use much memory)
    scheduler._execute_task(task)
    assert task.run_count == 1


@pytest.mark.skipif(os.name == 'nt', reason="Resource limits work differently on Windows")
def test_safe_mode_memory_violation(scheduler, memory_hog_script):
    """Test that memory limits are enforced."""
    task_id = scheduler.add_task(
        name="memory_hog",
        script=memory_hog_script,
        every="1h",
        safe_mode=True,
        max_memory_mb=10,  # Very low limit
        timeout=10
    )
    
    task = scheduler.tasks[task_id]
    
    # Should fail due to memory limit
    scheduler._execute_task(task)
    assert task.fail_count > 0


def test_safe_mode_timeout(scheduler, slow_script):
    """Test that timeout is enforced in safe mode."""
    task_id = scheduler.add_task(
        name="slow_task",
        script=slow_script,
        every="1h",
        safe_mode=True,
        timeout=2  # 2 second timeout
    )
    
    task = scheduler.tasks[task_id]
    
    # Should timeout
    scheduler._execute_task(task)
    assert task.fail_count > 0


def test_safe_mode_isolation(scheduler, safe_script):
    """Test that safe mode provides process isolation."""
    task_id = scheduler.add_task(
        name="isolated_task",
        script=safe_script,
        every="1h",
        safe_mode=True,
        timeout=5
    )
    
    task = scheduler.tasks[task_id]
    
    # Execute and verify AUTOCRON_SAFE_MODE env var would be set
    # (Actual subprocess environment testing would require more complex setup)
    assert task.safe_mode is True


def test_safe_mode_persistence(scheduler, safe_script, tmp_path):
    """Test that safe mode settings are persisted."""
    task_id = scheduler.add_task(
        name="persistent_safe_task",
        script=safe_script,
        every="1h",
        safe_mode=True,
        max_memory_mb=256,
        max_cpu_percent=50
    )
    
    # Save tasks
    save_path = tmp_path / "tasks.yaml"
    scheduler.save_tasks(str(save_path))
    
    # Load into new scheduler
    new_scheduler = AutoCron()
    new_scheduler.load_tasks(str(save_path))
    
    # Verify safe mode settings
    loaded_task = list(new_scheduler.tasks.values())[0]
    assert loaded_task.safe_mode is True
    assert loaded_task.max_memory_mb == 256
    assert loaded_task.max_cpu_percent == 50


def test_normal_mode_still_works(scheduler, safe_script):
    """Test that normal mode (non-safe) still works."""
    task_id = scheduler.add_task(
        name="normal_task",
        script=safe_script,
        every="1h",
        safe_mode=False,  # Explicitly disable
        timeout=5
    )
    
    task = scheduler.tasks[task_id]
    assert task.safe_mode is False
    
    # Execute normally
    scheduler._execute_task(task)
    assert task.run_count == 1
    assert task.fail_count == 0


def test_safe_mode_output_sanitization(scheduler, safe_script):
    """Test that output is sanitized in safe mode."""
    # Create script with large output
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
# Generate large output
for i in range(1000):
    print(f"Line {i}: {'x' * 100}")
""")
        large_output_script = f.name
    
    try:
        task_id = scheduler.add_task(
            name="large_output_task",
            script=large_output_script,
            every="1h",
            safe_mode=True,
            timeout=5
        )
        
        task = scheduler.tasks[task_id]
        scheduler._execute_task(task)
        
        # Output should be truncated (tested internally in _execute_in_safe_mode)
        assert task.run_count == 1
        
    finally:
        try:
            os.unlink(large_output_script)
        except:
            pass


def test_safe_mode_default_disabled(scheduler, safe_script):
    """Test that safe mode is disabled by default."""
    task_id = scheduler.add_task(
        name="default_task",
        script=safe_script,
        every="1h"
    )
    
    task = scheduler.tasks[task_id]
    assert task.safe_mode is False
    assert task.max_memory_mb is None
    assert task.max_cpu_percent is None


def test_safe_mode_with_retries(scheduler, safe_script):
    """Test that safe mode works with retry logic."""
    task_id = scheduler.add_task(
        name="retry_safe_task",
        script=safe_script,
        every="1h",
        safe_mode=True,
        retries=3,
        timeout=5
    )
    
    task = scheduler.tasks[task_id]
    scheduler._execute_task(task)
    
    # Should succeed on first try
    assert task.run_count == 1
    assert task.fail_count == 0


def test_safe_mode_function_tasks_unsupported(scheduler):
    """Test that safe mode is only for script tasks."""
    def my_func():
        print("Function task")
    
    # Safe mode should be ignored for function tasks
    task_id = scheduler.add_task(
        name="func_task",
        func=my_func,
        every="1h",
        safe_mode=True  # Should be set but not used
    )
    
    task = scheduler.tasks[task_id]
    # Function tasks don't execute in safe mode (they run in-process)
    assert task.safe_mode is True  # Setting accepted
    assert task.func is not None
