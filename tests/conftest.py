"""Pytest configuration and fixtures."""

import os
import tempfile

import pytest


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "windows: mark test as Windows-only")
    config.addinivalue_line("markers", "linux: mark test as Linux-only")
    config.addinivalue_line("markers", "darwin: mark test as macOS-only")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_script(temp_dir):
    """Create a test script file."""
    script_path = os.path.join(temp_dir, "test_script.py")

    with open(script_path, "w") as f:
        f.write(
            """
import sys
print("Test script executed")
sys.exit(0)
"""
        )

    return script_path


@pytest.fixture
def failing_script(temp_dir):
    """Create a failing test script."""
    script_path = os.path.join(temp_dir, "failing_script.py")

    with open(script_path, "w") as f:
        f.write(
            """
import sys
print("Test script failed")
sys.exit(1)
"""
        )

    return script_path


@pytest.fixture(autouse=True)
def cleanup_global_state():
    """Clean up global state after each test."""
    yield

    # Reset global scheduler
    from autocron.scheduler import reset_global_scheduler

    reset_global_scheduler()

    # Reset logger
    from autocron.logger import reset_logger

    reset_logger()

    # Reset notification manager
    from autocron.notifications import reset_notification_manager

    reset_notification_manager()
