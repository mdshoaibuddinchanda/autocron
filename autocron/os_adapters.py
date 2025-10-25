"""
OS-specific adapters for task scheduling.

Provides platform-specific implementations for Windows, Linux, and macOS.
"""

import contextlib
import os
import subprocess  # nosec B404 - Required for cross-platform task scheduling
import tempfile
from abc import ABC, abstractmethod
from typing import List, Optional

from autocron.utils import get_platform_info, is_linux, is_macos, is_windows, sanitize_task_name


class OSAdapterError(Exception):
    """Exception raised when OS adapter operations fail."""

    pass


class OSAdapter(ABC):
    """Abstract base class for OS-specific adapters."""

    @abstractmethod
    def create_scheduled_task(
        self,
        task_name: str,
        script_path: str,
        cron_expr: str,
        python_executable: Optional[str] = None,
    ) -> bool:
        """
        Create a scheduled task in the OS.

        Args:
            task_name: Name of the task
            script_path: Path to the script to execute
            cron_expr: Cron expression for scheduling
            python_executable: Path to Python executable

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def remove_scheduled_task(self, task_name: str) -> bool:
        """
        Remove a scheduled task from the OS.

        Args:
            task_name: Name of the task

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def list_scheduled_tasks(self) -> List[str]:
        """
        List all AutoCron scheduled tasks.

        Returns:
            List of task names
        """
        pass

    @abstractmethod
    def task_exists(self, task_name: str) -> bool:
        """
        Check if a task exists.

        Args:
            task_name: Name of the task

        Returns:
            True if exists, False otherwise
        """
        pass


class WindowsAdapter(OSAdapter):
    """
    Windows Task Scheduler adapter.

    Uses Windows Task Scheduler via schtasks command.
    """

    TASK_PREFIX = "AutoCron_"

    def __init__(self):
        """Initialize Windows adapter."""
        if not is_windows():
            raise OSAdapterError("WindowsAdapter can only be used on Windows")

    def create_scheduled_task(
        self,
        task_name: str,
        script_path: str,
        cron_expr: str,
        python_executable: Optional[str] = None,
    ) -> bool:
        """Create Windows scheduled task."""
        try:
            if python_executable is None:
                import sys

                python_executable = sys.executable

            full_task_name = f"{self.TASK_PREFIX}{sanitize_task_name(task_name)}"

            # Convert cron to Task Scheduler time
            # For simplicity, we'll use Task Scheduler's repetition interval
            # A full implementation would parse cron and convert appropriately

            # Create XML for task
            xml_content = self._generate_task_xml(
                task_name=full_task_name,
                script_path=script_path,
                python_executable=python_executable,
                cron_expr=cron_expr,
            )

            # Write XML to temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
                f.write(xml_content)
                xml_file = f.name

            try:
                # Create task using schtasks
                cmd = [
                    "schtasks",
                    "/Create",
                    "/TN",
                    full_task_name,
                    "/XML",
                    xml_file,
                    "/F",  # Force create, overwrite if exists
                ]

                # nosec B603 B607 - Controlled schtasks command with validated inputs
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)

                if result.returncode == 0:
                    return True
                else:
                    raise OSAdapterError(f"Failed to create task: {result.stderr}")
            finally:
                # Clean up temp XML file
                with contextlib.suppress(OSError):
                    os.unlink(xml_file)

        except Exception as e:
            raise OSAdapterError(f"Failed to create scheduled task: {e}") from e

    def remove_scheduled_task(self, task_name: str) -> bool:
        """Remove Windows scheduled task."""
        try:
            full_task_name = f"{self.TASK_PREFIX}{sanitize_task_name(task_name)}"

            cmd = ["schtasks", "/Delete", "/TN", full_task_name, "/F"]
            # nosec B603 B607 - Controlled schtasks command with validated task name
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            return result.returncode == 0
        except Exception:
            return False

    def list_scheduled_tasks(self) -> List[str]:
        """List all AutoCron scheduled tasks."""
        try:
            cmd = ["schtasks", "/Query", "/FO", "LIST"]
            result = subprocess.run(  # nosec B603 B607 - Controlled schtasks query command
                cmd, capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                return []

            tasks = []
            for line in result.stdout.split("\n"):
                if self.TASK_PREFIX in line and "TaskName" in line:
                    # Extract task name
                    parts = line.split(":")
                    if len(parts) > 1:
                        task_name = parts[1].strip()
                        if task_name.startswith(self.TASK_PREFIX):
                            # Remove prefix to get original name
                            original_name = task_name[len(self.TASK_PREFIX) :]
                            tasks.append(original_name)

            return tasks
        except Exception:
            return []

    def task_exists(self, task_name: str) -> bool:
        """Check if task exists."""
        tasks = self.list_scheduled_tasks()
        return task_name in tasks

    def _generate_task_xml(
        self, task_name: str, script_path: str, python_executable: str, cron_expr: str
    ) -> str:
        """Generate Task Scheduler XML configuration."""
        return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>AutoCron scheduled task: {task_name}</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT5M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2020-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
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
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{python_executable}"</Command>
      <Arguments>"{script_path}"</Arguments>
    </Exec>
  </Actions>
</Task>"""


class UnixAdapter(OSAdapter):
    """
    Unix (Linux/macOS) cron adapter.

    Uses system crontab to schedule tasks.
    """

    CRON_COMMENT = "# AutoCron:"

    def __init__(self):
        """Initialize Unix adapter."""
        if not (is_linux() or is_macos()):
            raise OSAdapterError("UnixAdapter can only be used on Linux or macOS")

    def create_scheduled_task(
        self,
        task_name: str,
        script_path: str,
        cron_expr: str,
        python_executable: Optional[str] = None,
    ) -> bool:
        """Create cron job."""
        try:
            if python_executable is None:
                import sys

                python_executable = sys.executable

            # Remove existing task if it exists
            self.remove_scheduled_task(task_name)

            # Get current crontab
            result = (
                subprocess.run(  # nosec B603 B607 - Controlled crontab command with no user input
                    ["crontab", "-l"], capture_output=True, text=True, check=False
                )
            )

            current_cron = result.stdout if result.returncode == 0 else ""

            # Add new job
            comment = f"{self.CRON_COMMENT} {task_name}"
            job_line = f'{cron_expr} {python_executable} "{script_path}" {comment}'

            new_cron = f"{current_cron.rstrip()}\n{job_line}\n"

            # Write new crontab
            result = (
                subprocess.run(  # nosec B603 B607 - Controlled crontab write with validated input
                    ["crontab", "-"], input=new_cron, capture_output=True, text=True, check=False
                )
            )

            return result.returncode == 0
        except Exception as e:
            raise OSAdapterError(f"Failed to create cron job: {e}") from e

    def remove_scheduled_task(self, task_name: str) -> bool:
        """Remove cron job."""
        try:
            # Get current crontab
            result = subprocess.run(  # nosec B603 B607 - Controlled crontab read command
                ["crontab", "-l"], capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                return False

            current_cron = result.stdout
            comment = f"{self.CRON_COMMENT} {task_name}"

            # Filter out the task
            new_lines = [line for line in current_cron.split("\n") if comment not in line]
            new_cron = "\n".join(new_lines)

            # Write new crontab
            result = (
                subprocess.run(  # nosec B603 B607 - Controlled crontab delete with validated input
                    ["crontab", "-"], input=new_cron, capture_output=True, text=True, check=False
                )
            )

            return result.returncode == 0
        except Exception:
            return False

    def list_scheduled_tasks(self) -> List[str]:
        """List all AutoCron cron jobs."""
        try:
            result = subprocess.run(  # nosec B603 B607 - Controlled crontab list command
                ["crontab", "-l"], capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                return []

            tasks = []
            for line in result.stdout.split("\n"):
                if self.CRON_COMMENT in line:
                    # Extract task name from comment
                    parts = line.split(self.CRON_COMMENT)
                    if len(parts) > 1:
                        task_name = parts[1].strip()
                        tasks.append(task_name)

            return tasks
        except Exception:
            return []

    def task_exists(self, task_name: str) -> bool:
        """Check if task exists."""
        tasks = self.list_scheduled_tasks()
        return task_name in tasks


def get_os_adapter() -> OSAdapter:
    """
    Get appropriate OS adapter for current platform.

    Returns:
        OS adapter instance

    Raises:
        OSAdapterError: If platform is not supported
    """
    if is_windows():
        return WindowsAdapter()
    elif is_linux() or is_macos():
        return UnixAdapter()
    else:
        platform_info = get_platform_info()
        raise OSAdapterError(
            f"Unsupported platform: {platform_info['system']}. "
            "AutoCron supports Windows, Linux, and macOS."
        )
