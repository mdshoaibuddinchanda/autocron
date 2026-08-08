"""Host-adapter behavior tests with injected command runners."""

import subprocess
from unittest.mock import patch

import pytest

from autocron.core.os_adapters import (
    OSAdapterError,
    UnixAdapter,
    WindowsAdapter,
    _cron_shell_quote,
    _normalize_cron_expression,
    _safe_task_name,
)


def completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def test_adapter_helpers_validate_and_quote_values():
    assert _normalize_cron_expression("@daily") == "0 0 * * *"
    assert _cron_shell_quote("50% done") == "'50\\% done'"
    assert _safe_task_name("a task") == "a_task"
    for bad in ("", "bad\nname", "\x00"):
        with pytest.raises(OSAdapterError):
            _safe_task_name(bad)
    with pytest.raises(OSAdapterError):
        _normalize_cron_expression("*/10 * * *")
    with pytest.raises(OSAdapterError):
        _normalize_cron_expression("0 0 * * *\n0 1 * * *")


def test_windows_adapter_xml_commands_and_errors():
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        if command[1] == "/Query":
            return completed('"\\AutoCron_one","Ready"\n"\\Other","Ready"\n')
        return completed()

    with patch("autocron.core.os_adapters.is_windows", return_value=True):
        adapter = WindowsAdapter(runner=runner)
        assert "ScheduleByDay" in adapter._generate_task_xml(
            "task", "job.py", "python", "0 9 * * *"
        )
        assert "TimeTrigger" in adapter._generate_task_xml(
            "task", "job.py", "python", "*/15 * * * *"
        )
        assert "ScheduleByWeek" in adapter._generate_task_xml(
            "task", "job.py", "python", "30 8 * * mon-fri"
        )
        assert adapter.create_scheduled_task("task", "job.py", "0 9 * * *", "python") is True
        assert adapter.remove_scheduled_task("task") is True
        assert adapter.list_scheduled_tasks() == ["one"]
        assert adapter.task_exists("one") is True
        with pytest.raises(OSAdapterError):
            adapter._generate_task_xml("task", "job.py", "python", "0 9 1 * *")
        with pytest.raises(OSAdapterError):
            adapter._generate_task_xml("task", "job.py", "python", "*/2 */3 * * *")


def test_unix_adapter_crontab_lifecycle_and_runner_failures():
    state = {"crontab": "0 9 * * * python job.py # AutoCron: old\n"}

    def runner(command, **kwargs):
        if command == ["crontab", "-l"]:
            return completed(state["crontab"])
        if command == ["crontab", "-"]:
            state["crontab"] = kwargs["input"]
            return completed()
        raise AssertionError(command)

    with patch("autocron.core.os_adapters.is_linux", return_value=True):
        adapter = UnixAdapter(runner=runner)
        assert adapter.create_scheduled_task("new task", "job file.py", "0 9 * * *", "python")
        assert "AutoCron: new_task" in state["crontab"]
        assert adapter.list_scheduled_tasks() == ["old", "new_task"]
        assert adapter.remove_scheduled_task("new task") is True
        assert adapter.remove_scheduled_task("missing") is False
        assert adapter.list_scheduled_tasks() == ["old"]

    def failing_runner(*_args, **_kwargs):
        raise OSError("blocked")

    with patch("autocron.core.os_adapters.is_linux", return_value=True):
        adapter = UnixAdapter(runner=failing_runner)
        assert adapter.remove_scheduled_task("x") is False
        assert adapter.list_scheduled_tasks() == []
        with pytest.raises(OSAdapterError):
            adapter.create_scheduled_task("x", "job.py", "0 9 * * *")
