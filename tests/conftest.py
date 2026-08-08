"""Pytest configuration and safety fixtures.

The test suite creates log, analytics, and persistence files by design.  Keep
those writes out of the developer's real profile, and never call the host OS
scheduler unless a test explicitly opts into system testing.
"""

import contextlib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

import pytest

_HOME_ENV_VARS = (
    "AUTOCRON_HOME",
    "HOME",
    "USERPROFILE",
    "LOCALAPPDATA",
    "APPDATA",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
)
_ORIGINAL_HOME_ENV: Dict[str, Optional[str]] = {
    name: os.environ.get(name) for name in _HOME_ENV_VARS
}
_COLLECTION_HOME = tempfile.TemporaryDirectory(prefix="autocron-pytest-")


def _configure_home(root: Path) -> None:
    """Route platform-specific user data into ``root``."""
    root.mkdir(parents=True, exist_ok=True)
    values = {
        "AUTOCRON_HOME": root / ".autocron",
        "HOME": root,
        "USERPROFILE": root,
        "LOCALAPPDATA": root / "local",
        "APPDATA": root / "roaming",
        "XDG_CACHE_HOME": root / ".cache",
        "XDG_CONFIG_HOME": root / ".config",
        "XDG_DATA_HOME": root / ".local" / "share",
    }
    for name, path in values.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(path)


# conftest.py is imported before test modules are collected.  This protects
# against import-time decorators in legacy demo-style test modules.
_configure_home(Path(_COLLECTION_HOME.name))


def _reset_global_state() -> None:
    """Reset process-wide AutoCron state between tests."""
    with contextlib.suppress(Exception):
        from autocron.core.scheduler import reset_global_scheduler

        reset_global_scheduler()

    with contextlib.suppress(Exception):
        from autocron.logging.logger import reset_logger

        reset_logger()

    with contextlib.suppress(Exception):
        from autocron.interface.notifications import reset_notification_manager

        reset_notification_manager()

    with contextlib.suppress(Exception):
        from autocron.core.utils import SingletonMeta

        SingletonMeta._instances.clear()


def _blocked_system_runner(command, *args, **kwargs):
    """Return a deterministic failure instead of invoking cron/schtasks."""
    del args, kwargs
    return subprocess.CompletedProcess(
        command,
        returncode=127,
        stdout="",
        stderr=(
            "OS scheduler calls are disabled under pytest. "
            "Set AUTOCRON_RUN_SYSTEM_TESTS=1 and use @pytest.mark.system "
            "for an explicit host integration test."
        ),
    )


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "windows: mark test as Windows-only")
    config.addinivalue_line("markers", "linux: mark test as Linux-only")
    config.addinivalue_line("markers", "darwin: mark test as macOS-only")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "packaging: mark isolated build/install tests")
    config.addinivalue_line("markers", "system: mark tests that may modify the host OS scheduler")


def pytest_collection_modifyitems(config, items):
    """Skip host-mutating tests unless the operator explicitly enables them."""
    del config
    if os.environ.get("AUTOCRON_RUN_SYSTEM_TESTS") == "1":
        return

    skip_system = pytest.mark.skip(
        reason="set AUTOCRON_RUN_SYSTEM_TESTS=1 to run host OS scheduler tests"
    )
    for item in items:
        if "system" in item.keywords:
            item.add_marker(skip_system)


def pytest_unconfigure(config):
    """Restore environment variables after the test session."""
    del config
    _reset_global_state()
    for name, original_value in _ORIGINAL_HOME_ENV.items():
        if original_value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = original_value
    with contextlib.suppress(Exception):
        _COLLECTION_HOME.cleanup()


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
        f.write("""
import sys
print("Test script executed")
sys.exit(0)
""")

    return script_path


@pytest.fixture
def failing_script(temp_dir):
    """Create a failing test script."""
    script_path = os.path.join(temp_dir, "failing_script.py")

    with open(script_path, "w") as f:
        f.write("""
import sys
print("Test script failed")
sys.exit(1)
""")

    return script_path


@pytest.fixture(autouse=True)
def isolated_test_state(tmp_path, monkeypatch):
    """Give every test an isolated home and deterministic global state."""
    _reset_global_state()

    test_home = tmp_path / "home"
    values = {
        "AUTOCRON_HOME": test_home / ".autocron",
        "HOME": test_home,
        "USERPROFILE": test_home,
        "LOCALAPPDATA": test_home / "local",
        "APPDATA": test_home / "roaming",
        "XDG_CACHE_HOME": test_home / ".cache",
        "XDG_CONFIG_HOME": test_home / ".config",
        "XDG_DATA_HOME": test_home / ".local" / "share",
    }
    for name, path in values.items():
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(name, str(path))

    if os.environ.get("AUTOCRON_RUN_SYSTEM_TESTS") != "1":
        from autocron.core import os_adapters

        monkeypatch.setattr(os_adapters, "_default_runner", _blocked_system_runner)

    yield

    _reset_global_state()
