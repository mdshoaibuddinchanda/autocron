"""Tests for OS adapters."""

import platform

import pytest

from autocron.os_adapters import OSAdapterError, UnixAdapter, WindowsAdapter, get_os_adapter
from autocron.utils import is_linux, is_macos, is_windows


class TestGetOSAdapter:
    """Test getting appropriate OS adapter."""

    def test_get_adapter(self):
        """Test getting adapter for current platform."""
        adapter = get_os_adapter()

        assert adapter is not None

        # sourcery skip: no-conditionals-in-tests
        if is_windows():
            assert isinstance(adapter, WindowsAdapter)
        elif is_linux() or is_macos():
            assert isinstance(adapter, UnixAdapter)


@pytest.mark.windows
class TestWindowsAdapter:
    """Test Windows adapter."""

    def test_create_adapter(self):
        """Test creating Windows adapter."""
        # sourcery skip: no-conditionals-in-tests
        if not is_windows():
            pytest.skip("Windows-only test")

        adapter = WindowsAdapter()
        assert adapter is not None

    def test_task_prefix(self):
        """Test task prefix."""
        # sourcery skip: no-conditionals-in-tests
        if not is_windows():
            pytest.skip("Windows-only test")

        adapter = WindowsAdapter()
        assert adapter.TASK_PREFIX == "AutoCron_"


@pytest.mark.linux
@pytest.mark.darwin
class TestUnixAdapter:
    """Test Unix adapter."""

    def test_create_adapter(self):
        """Test creating Unix adapter."""
        # sourcery skip: no-conditionals-in-tests
        if not (is_linux() or is_macos()):
            pytest.skip("Unix-only test")

        adapter = UnixAdapter()
        assert adapter is not None

    def test_cron_comment(self):
        """Test cron comment marker."""
        # sourcery skip: no-conditionals-in-tests
        if not (is_linux() or is_macos()):
            pytest.skip("Unix-only test")

        adapter = UnixAdapter()
        assert adapter.CRON_COMMENT == "# AutoCron:"


class TestOSAdapterMethods:
    """Test OS adapter methods."""

    def test_adapter_has_required_methods(self):
        """Test that adapter has all required methods."""
        adapter = get_os_adapter()

        assert hasattr(adapter, "create_scheduled_task")
        assert hasattr(adapter, "remove_scheduled_task")
        assert hasattr(adapter, "list_scheduled_tasks")
        assert hasattr(adapter, "task_exists")

    def test_list_scheduled_tasks(self):
        """Test listing scheduled tasks."""
        adapter = get_os_adapter()

        # Should not raise exception
        tasks = adapter.list_scheduled_tasks()

        assert isinstance(tasks, list)
