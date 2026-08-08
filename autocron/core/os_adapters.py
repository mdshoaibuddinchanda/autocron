"""Adapters for registering AutoCron script tasks with host schedulers.

The adapters intentionally support a documented subset of cron on Windows.
Unsupported expressions fail explicitly instead of silently running at a
different time.  Command execution is injectable so tests never need to touch
the developer's real Task Scheduler or crontab.
"""

import csv
import io
import os
import shlex
import subprocess  # nosec B404 - required for host scheduler integration
import sys
import tempfile
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from xml.sax.saxutils import escape

from croniter import croniter

from autocron.core.utils import (
    get_platform_info,
    is_linux,
    is_macos,
    is_windows,
    sanitize_task_name,
)

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def _default_runner(command: List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a host command; kept indirect for safe dependency injection in tests."""
    return subprocess.run(command, **kwargs)  # nosec B603


def _safe_task_name(task_name: str) -> str:
    """Return a stable scheduler identifier without control characters."""
    if any(character in task_name for character in ("\x00", "\r", "\n")):
        raise OSAdapterError("Task names cannot contain control characters")
    safe_name = sanitize_task_name(task_name)
    if not safe_name:
        raise OSAdapterError("Task name must contain at least one letter or number")
    return safe_name


def _validate_command_value(value: str, label: str) -> str:
    """Reject values that could create an additional cron line or XML node."""
    if not value or any(character in value for character in ("\x00", "\r", "\n")):
        raise OSAdapterError(f"{label} must be a non-empty, single-line value")
    return value


def _normalize_cron_expression(cron_expr: str) -> str:
    """Normalize common aliases and validate standard five-field cron."""
    aliases = {
        "@hourly": "0 * * * *",
        "@daily": "0 0 * * *",
        "@midnight": "0 0 * * *",
        "@weekly": "0 0 * * 0",
    }
    expression = aliases.get(cron_expr.strip().lower(), cron_expr.strip())
    if any(character in expression for character in ("\x00", "\r", "\n")):
        raise OSAdapterError("Cron expression must be a single line")
    if len(expression.split()) != 5:
        raise OSAdapterError(
            "OS schedulers require a standard five-field cron expression; "
            "sub-minute schedules must use AutoCron's in-process scheduler"
        )
    if not croniter.is_valid(expression):
        raise OSAdapterError(f"Invalid cron expression: {cron_expr}")
    return expression


def _cron_shell_quote(value: str) -> str:
    """Quote one shell argument and escape cron's special percent delimiter."""
    return shlex.quote(_validate_command_value(value, "Command argument")).replace("%", r"\%")


class OSAdapterError(Exception):
    """Raised when a host scheduler operation cannot be represented or completed."""


class OSAdapter(ABC):
    """Abstract base class for OS-specific schedulers."""

    def __init__(self, runner: Optional[CommandRunner] = None) -> None:
        self._runner = runner or _default_runner

    @abstractmethod
    def create_scheduled_task(
        self,
        task_name: str,
        script_path: str,
        cron_expr: str,
        python_executable: Optional[str] = None,
    ) -> bool:
        """Create or replace a scheduled script task."""

    @abstractmethod
    def remove_scheduled_task(self, task_name: str) -> bool:
        """Remove a scheduled task by name."""

    @abstractmethod
    def list_scheduled_tasks(self) -> List[str]:
        """List AutoCron-owned task names."""

    def task_exists(self, task_name: str) -> bool:
        """Return whether a sanitized task identifier is registered."""
        return _safe_task_name(task_name) in self.list_scheduled_tasks()


class WindowsAdapter(OSAdapter):
    """Windows Task Scheduler adapter using ``schtasks`` XML registration."""

    TASK_PREFIX = "AutoCron_"
    _DAY_NAMES: Dict[str, str] = {
        "0": "Sunday",
        "7": "Sunday",
        "sun": "Sunday",
        "1": "Monday",
        "mon": "Monday",
        "2": "Tuesday",
        "tue": "Tuesday",
        "3": "Wednesday",
        "wed": "Wednesday",
        "4": "Thursday",
        "thu": "Thursday",
        "5": "Friday",
        "fri": "Friday",
        "6": "Saturday",
        "sat": "Saturday",
    }
    _DAY_ORDER = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]

    def __init__(self, runner: Optional[CommandRunner] = None) -> None:
        if not is_windows():
            raise OSAdapterError("WindowsAdapter can only be used on Windows")
        super().__init__(runner)

    @staticmethod
    def _exact_number(field: str, minimum: int, maximum: int, label: str) -> int:
        if not field.isdigit():
            raise OSAdapterError(f"Windows adapter requires an exact {label}: {field}")
        value = int(field)
        if not minimum <= value <= maximum:
            raise OSAdapterError(f"{label.capitalize()} must be between {minimum} and {maximum}")
        return value

    @staticmethod
    def _step(field: str, maximum: int) -> Optional[int]:
        if field == "*":
            return 1
        if not field.startswith("*/") or not field[2:].isdigit():
            return None
        value = int(field[2:])
        return value if 1 <= value <= maximum else None

    @classmethod
    def _days_of_week(cls, field: str) -> List[str]:
        """Expand cron day names, comma lists, and non-wrapping ranges."""
        resolved: List[str] = []
        for part in field.lower().split(","):
            if "-" in part:
                start_token, end_token = part.split("-", 1)
                try:
                    start_name = cls._DAY_NAMES[start_token]
                    end_name = cls._DAY_NAMES[end_token]
                except KeyError as exc:
                    raise OSAdapterError(f"Unsupported day-of-week field: {field}") from exc
                start = cls._DAY_ORDER.index(start_name)
                end = cls._DAY_ORDER.index(end_name)
                if start > end:
                    raise OSAdapterError(
                        "Wrapping day-of-week ranges are not supported by the Windows adapter"
                    )
                resolved.extend(cls._DAY_ORDER[start : end + 1])
            else:
                try:
                    resolved.append(cls._DAY_NAMES[part])
                except KeyError as exc:
                    raise OSAdapterError(f"Unsupported day-of-week field: {field}") from exc
        return [day for day in cls._DAY_ORDER if day in resolved]

    @classmethod
    def _trigger_xml(cls, cron_expr: str) -> str:
        expression = _normalize_cron_expression(cron_expr)
        minute, hour, day_of_month, month, day_of_week = expression.split()

        if day_of_month != "*" or month != "*":
            raise OSAdapterError(
                "Windows adapter supports recurring minute, hour, daily, and weekly cron; "
                "day-of-month and month constraints require the in-process scheduler"
            )

        if day_of_week != "*":
            minute_value = cls._exact_number(minute, 0, 59, "minute")
            hour_value = cls._exact_number(hour, 0, 23, "hour")
            days = cls._days_of_week(day_of_week)
            day_nodes = "".join(f"<{day} />" for day in days)
            return f"""<CalendarTrigger>
      <StartBoundary>2000-01-03T{hour_value:02d}:{minute_value:02d}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>{day_nodes}</DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>"""

        if minute.isdigit() and hour.isdigit():
            minute_value = cls._exact_number(minute, 0, 59, "minute")
            hour_value = cls._exact_number(hour, 0, 23, "hour")
            return f"""<CalendarTrigger>
      <StartBoundary>2000-01-01T{hour_value:02d}:{minute_value:02d}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>"""

        minute_step = cls._step(minute, 59)
        hour_step = cls._step(hour, 23)
        if hour == "*" and minute_step is not None:
            interval = f"PT{minute_step}M"
            start_minute = 0
        elif minute.isdigit() and hour_step is not None:
            start_minute = cls._exact_number(minute, 0, 59, "minute")
            interval = f"PT{hour_step}H"
        else:
            raise OSAdapterError(
                "Cron expression is valid but cannot be represented faithfully by Windows "
                "Task Scheduler; use AutoCron's in-process scheduler"
            )

        return f"""<TimeTrigger>
      <Repetition>
        <Interval>{interval}</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2000-01-01T00:{start_minute:02d}:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>"""

    def create_scheduled_task(
        self,
        task_name: str,
        script_path: str,
        cron_expr: str,
        python_executable: Optional[str] = None,
    ) -> bool:
        """Register a task whose requested schedule is faithfully representable."""
        executable = _validate_command_value(
            python_executable or sys.executable, "Python executable"
        )
        script = _validate_command_value(script_path, "Script path")
        full_task_name = f"{self.TASK_PREFIX}{_safe_task_name(task_name)}"
        xml_content = self._generate_task_xml(
            task_name=full_task_name,
            script_path=script,
            python_executable=executable,
            cron_expr=cron_expr,
        )

        xml_file = ""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", delete=False, encoding="utf-16"
            ) as file_handle:
                file_handle.write(xml_content)
                xml_file = file_handle.name

            command = ["schtasks", "/Create", "/TN", full_task_name, "/XML", xml_file, "/F"]
            result = self._runner(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise OSAdapterError(
                    f"Failed to create Windows scheduled task: {result.stderr.strip()}"
                )
            return True
        except OSAdapterError:
            raise
        except (OSError, subprocess.SubprocessError) as exc:
            raise OSAdapterError(f"Failed to create Windows scheduled task: {exc}") from exc
        finally:
            if xml_file:
                try:
                    os.unlink(xml_file)
                except OSError:
                    pass

    def remove_scheduled_task(self, task_name: str) -> bool:
        full_task_name = f"{self.TASK_PREFIX}{_safe_task_name(task_name)}"
        try:
            result = self._runner(
                ["schtasks", "/Delete", "/TN", full_task_name, "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def list_scheduled_tasks(self) -> List[str]:
        try:
            result = self._runner(
                ["schtasks", "/Query", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return []
            tasks: List[str] = []
            for row in csv.reader(io.StringIO(result.stdout)):
                if not row:
                    continue
                task_path = row[0].strip().lstrip("\\")
                if task_path.startswith(self.TASK_PREFIX):
                    tasks.append(task_path[len(self.TASK_PREFIX) :])
            return tasks
        except (OSError, subprocess.SubprocessError, csv.Error):
            return []

    def _generate_task_xml(
        self, task_name: str, script_path: str, python_executable: str, cron_expr: str
    ) -> str:
        """Generate valid Task Scheduler XML for the supported cron subset."""
        trigger = self._trigger_xml(cron_expr)
        safe_name = escape(_validate_command_value(task_name, "Task name"))
        safe_command = escape(_validate_command_value(python_executable, "Python executable"))
        safe_arguments = escape(subprocess.list2cmdline([script_path]))
        return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>AutoCron scheduled task: {safe_name}</Description>
  </RegistrationInfo>
  <Triggers>
    {trigger}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{safe_command}</Command>
      <Arguments>{safe_arguments}</Arguments>
    </Exec>
  </Actions>
</Task>"""


class UnixAdapter(OSAdapter):
    """Linux/macOS adapter using the current user's ``crontab``."""

    CRON_COMMENT = "# AutoCron:"

    def __init__(self, runner: Optional[CommandRunner] = None) -> None:
        if not (is_linux() or is_macos()):
            raise OSAdapterError("UnixAdapter can only be used on Linux or macOS")
        super().__init__(runner)

    @classmethod
    def _comment(cls, task_name: str) -> str:
        return f"{cls.CRON_COMMENT} {_safe_task_name(task_name)}"

    @classmethod
    def _without_task(cls, crontab: str, task_name: str) -> str:
        comment = cls._comment(task_name)
        retained = [
            line
            for line in crontab.splitlines()
            if not (
                cls.CRON_COMMENT in line
                and line.split(cls.CRON_COMMENT, 1)[1].strip()
                == comment.split(cls.CRON_COMMENT, 1)[1].strip()
            )
        ]
        return "\n".join(retained).rstrip()

    def _read_crontab(self) -> str:
        result = self._runner(["crontab", "-l"], capture_output=True, text=True, check=False)
        return result.stdout if result.returncode == 0 else ""

    def _write_crontab(self, content: str) -> bool:
        result = self._runner(
            ["crontab", "-"],
            input=f"{content.rstrip()}\n" if content else "",
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def create_scheduled_task(
        self,
        task_name: str,
        script_path: str,
        cron_expr: str,
        python_executable: Optional[str] = None,
    ) -> bool:
        expression = _normalize_cron_expression(cron_expr)
        executable = _cron_shell_quote(python_executable or sys.executable)
        script = _cron_shell_quote(script_path)
        comment = self._comment(task_name)
        try:
            current = self._read_crontab()
            retained = self._without_task(current, task_name)
            job = f"{expression} {executable} {script} {comment}"
            return self._write_crontab(f"{retained}\n{job}" if retained else job)
        except (OSError, subprocess.SubprocessError) as exc:
            raise OSAdapterError(f"Failed to create cron job: {exc}") from exc

    def remove_scheduled_task(self, task_name: str) -> bool:
        try:
            current = self._read_crontab()
            if not current:
                return False
            updated = self._without_task(current, task_name)
            if updated == current.rstrip():
                return False
            return self._write_crontab(updated)
        except (OSError, subprocess.SubprocessError):
            return False

    def list_scheduled_tasks(self) -> List[str]:
        try:
            current = self._read_crontab()
            tasks: List[str] = []
            for line in current.splitlines():
                if self.CRON_COMMENT in line:
                    task_name = line.split(self.CRON_COMMENT, 1)[1].strip()
                    if task_name:
                        tasks.append(task_name)
            return tasks
        except (OSError, subprocess.SubprocessError):
            return []


def get_os_adapter(runner: Optional[CommandRunner] = None) -> OSAdapter:
    """Return the adapter for the current platform."""
    if is_windows():
        return WindowsAdapter(runner=runner)
    if is_linux() or is_macos():
        return UnixAdapter(runner=runner)
    platform_info = get_platform_info()
    raise OSAdapterError(
        f"Unsupported platform: {platform_info['system']}. "
        "AutoCron supports Windows, Linux, and macOS."
    )
