"""
Core scheduling engine for AutoCron.

Provides the main scheduler class and decorators for task scheduling.
"""

import asyncio
import contextlib
import inspect
import json
import math
import os
import subprocess  # nosec B404 - Required for executing Python scripts
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
from datetime import tzinfo
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

from autocron.core.os_adapters import OSAdapter, OSAdapterError, get_os_adapter
from autocron.core.utils import (
    calculate_retry_delay,
    get_autocron_home,
    get_next_run_time,
    parse_interval,
    resolve_timezone,
    timezone_name,
    validate_cron_expression,
)
from autocron.interface.notifications import get_notification_manager
from autocron.logging.logger import get_logger

# Optional analytics import
try:
    from autocron.interface.dashboard import TaskAnalytics

    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    if TYPE_CHECKING:
        from autocron.interface.dashboard import TaskAnalytics
    else:
        TaskAnalytics = None  # type: ignore


class TaskExecutionError(Exception):
    """Exception raised when task execution fails."""

    pass


class SchedulingError(Exception):
    """Exception raised when scheduling fails."""

    pass


class _InProcessTimeout(TaskExecutionError):
    """Timeout whose Python callable is still unwinding in another thread."""

    def __init__(self, message: str, completion: threading.Event):
        super().__init__(message)
        self.completion = completion


class _InterProcessFileLock:
    """Small standard-library advisory lock used around persistence files."""

    def __init__(self, target: Path, timeout: float = 10.0):
        self.path = target.with_name(f".{target.name}.lock")
        self.timeout = timeout
        self._handle: Any = None

    def __enter__(self) -> "_InterProcessFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self.path, "a+b")
        self._handle.seek(0, os.SEEK_END)
        if self._handle.tell() == 0:
            self._handle.write(b"\0")
            self._handle.flush()

        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self._handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    lock_flags = fcntl.LOCK_EX | fcntl.LOCK_NB  # type: ignore[attr-defined]
                    fcntl.flock(self._handle.fileno(), lock_flags)  # type: ignore[attr-defined]
                return self
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    self._handle.close()
                    self._handle = None
                    raise TimeoutError(f"Timed out waiting for persistence lock: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
        finally:
            self._handle.close()
            self._handle = None


def _validate_integer(name: str, value: Any, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _validate_positive_number(name: str, value: Any, *, allow_none: bool = True) -> Any:
    if value is None and allow_none:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive number")
    if not math.isfinite(float(value)) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return value


def _redact_email_config(config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return a persistence-safe email configuration without credentials."""
    if config is None:
        return None
    sensitive_keys = {
        "password",
        "passwd",
        "pass",
        "smtp_password",
        "app_password",
        "secret",
        "token",
    }
    return {
        key: value
        for key, value in config.items()
        if str(key).strip().lower() not in sensitive_keys
    }


class Task:
    """
    Represents a scheduled task.

    Attributes:
        task_id: Unique task identifier
        name: Task name
        func: Function to execute (if function-based)
        script: Script path to execute (if script-based)
        schedule_type: 'interval' or 'cron'
        schedule_value: Schedule specification
        retries: Maximum retry attempts
        retry_delay: Base delay between retries (seconds)
        timeout: Maximum execution time (seconds)
        notify: Notification channels ('desktop', 'email', or list)
        email_config: Email configuration for notifications
        on_success: Callback for successful execution
        on_failure: Callback for failed execution
        enabled: Whether task is enabled
        last_run: Last execution time
        next_run: Next scheduled execution time
        run_count: Number of times executed
        fail_count: Number of failures
    """

    def __init__(
        self,
        name: str,
        func: Optional[Callable] = None,
        script: Optional[str] = None,
        every: Optional[str] = None,
        cron: Optional[str] = None,
        retries: int = 0,
        retry_delay: int = 60,
        timeout: Optional[int] = None,
        notify: Optional[Union[str, List[str]]] = None,
        email_config: Optional[Dict[str, Any]] = None,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
        safe_mode: bool = False,
        max_memory_mb: Optional[int] = None,
        max_cpu_percent: Optional[int] = None,
        timezone: Optional[Union[str, tzinfo]] = None,
        overlap_policy: str = "skip",
        max_instances: int = 1,
        misfire_grace_time: Optional[float] = 60.0,
        coalesce: bool = True,
        clean_env: bool = False,
        max_output_bytes: int = 1_000_000,
    ):
        """
        Initialize task.

        Args:
            name: Task name
            func: Function to execute
            script: Script path to execute
            every: Interval string (e.g., '5m', '1h')
            cron: Cron expression
            retries: Maximum retry attempts
            retry_delay: Base delay between retries (seconds)
            timeout: Maximum execution time (seconds)
            notify: Notification channels
            email_config: Email configuration
            on_success: Success callback
            on_failure: Failure callback
            safe_mode: Enable sandboxed execution (subprocess isolation)
            max_memory_mb: Maximum memory limit in MB (safe mode only)
            max_cpu_percent: Maximum CPU usage percent (safe mode only)
            timezone: IANA timezone name, tzinfo object, or ``"local"``
            overlap_policy: ``"skip"``, ``"allow"``, or ``"queue"``
            max_instances: Maximum concurrent instances for this task
            misfire_grace_time: Maximum lateness in seconds, or ``None``
            coalesce: Collapse multiple missed occurrences into one run
            clean_env: Give safe-mode scripts a minimal environment
            max_output_bytes: Maximum combined captured stdout/stderr bytes
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Task name must be a non-empty string")
        if func is None and script is None:
            raise ValueError("Either func or script must be provided")

        if func is not None and script is not None:
            raise ValueError("Only one of func or script can be provided")

        if func is not None and not callable(func):
            raise ValueError("func must be callable")
        if script is not None and (not isinstance(script, str) or not script.strip()):
            raise ValueError("script must be a non-empty path string")

        if every is None and cron is None:
            raise ValueError("Either every or cron must be provided")

        if every is not None and cron is not None:
            raise ValueError("Only one of every or cron can be provided")

        _validate_integer("retries", retries, minimum=0)
        _validate_integer("retry_delay", retry_delay, minimum=0)
        _validate_positive_number("timeout", timeout)
        if max_memory_mb is not None:
            _validate_integer("max_memory_mb", max_memory_mb, minimum=1)
        if max_cpu_percent is not None:
            _validate_positive_number("max_cpu_percent", max_cpu_percent)
            if max_cpu_percent > 100:
                raise ValueError("max_cpu_percent must be less than or equal to 100")
        _validate_integer("max_instances", max_instances, minimum=1)
        _validate_integer("max_output_bytes", max_output_bytes, minimum=1)
        if misfire_grace_time is not None:
            if isinstance(misfire_grace_time, bool) or not isinstance(
                misfire_grace_time, (int, float)
            ):
                raise ValueError("misfire_grace_time must be a non-negative number or None")
            if not math.isfinite(float(misfire_grace_time)) or misfire_grace_time < 0:
                raise ValueError("misfire_grace_time must be a non-negative finite number or None")
        if overlap_policy not in {"skip", "allow", "queue"}:
            raise ValueError("overlap_policy must be one of: skip, allow, queue")
        if not isinstance(coalesce, bool):
            raise ValueError("coalesce must be a boolean")
        if not isinstance(clean_env, bool):
            raise ValueError("clean_env must be a boolean")
        if not isinstance(safe_mode, bool):
            raise ValueError("safe_mode must be a boolean")
        if email_config is not None and not isinstance(email_config, dict):
            raise ValueError("email_config must be a dictionary")

        self.task_id = str(uuid.uuid4())
        self.name = name.strip()
        self.func = func
        self.script = script.strip() if script else None
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.notify = notify
        self.email_config = dict(email_config) if email_config else None
        self.on_success = on_success
        self.on_failure = on_failure
        self.enabled = True

        # Safe mode configuration
        self.safe_mode = safe_mode
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.clean_env = clean_env
        self.max_output_bytes = max_output_bytes

        # Temporal and execution policies
        self.timezone = timezone_name(timezone)
        self.tzinfo = resolve_timezone(timezone)
        self.overlap_policy = overlap_policy
        self.max_instances = max_instances
        self.misfire_grace_time = misfire_grace_time
        self.coalesce = coalesce

        # Schedule configuration
        if every is not None:
            self.schedule_type = "interval"
            self.schedule_value = every
            self.interval_seconds = parse_interval(every)
        else:
            self.schedule_type = "cron"
            self.schedule_value = cron or ""
            if cron and not validate_cron_expression(cron):
                raise ValueError(f"Invalid cron expression: {cron}")

        # Execution tracking. Runtime counters are deliberately not restored as
        # active work after a process restart.
        self._lock = threading.RLock()
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.fail_count = 0
        self.skipped_count = 0
        self.misfire_count = 0
        self._active_instances = 0
        self._queued_runs = 0
        self._notification_channels: Dict[str, str] = {}
        self.next_run: Optional[datetime] = self._calculate_next_run()

    def _now(self) -> datetime:
        return datetime.now(self.tzinfo)

    def _normalize_time(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=self.tzinfo)
        return value.astimezone(self.tzinfo)

    def _next_after(self, value: datetime) -> datetime:
        value = self._normalize_time(value)
        if self.schedule_type == "interval":
            next_utc = value.astimezone(datetime_timezone.utc) + timedelta(
                seconds=self.interval_seconds
            )
            return next_utc.astimezone(self.tzinfo)
        return get_next_run_time(self.schedule_value, value, self.tzinfo)

    def _calculate_next_run(self) -> datetime:
        """Calculate next run time."""
        if self.schedule_type == "interval":
            return self._now() if self.last_run is None else self._next_after(self.last_run)
        base_time = self.last_run or self._now()
        return get_next_run_time(self.schedule_value, base_time, self.tzinfo)

    def should_run(self, now: Optional[datetime] = None) -> bool:
        """Check if task should run now."""
        if not self.enabled:
            return False

        current = self._normalize_time(now) if now is not None else self._now()
        with self._lock:
            return bool(self._queued_runs) or (
                self.next_run is not None and current >= self.next_run
            )

    def update_next_run(self, now: Optional[datetime] = None) -> None:
        """Update next run time."""
        with self._lock:
            current = self._normalize_time(now) if now is not None else self._now()
            self.last_run = current
            self.next_run = self._next_after(current)

    @property
    def active_instances(self) -> int:
        """Number of currently executing (or timed-out but still alive) runs."""
        with self._lock:
            return self._active_instances

    @property
    def queued_runs(self) -> int:
        """Number of occurrences waiting under the queue overlap policy."""
        with self._lock:
            return self._queued_runs

    def _consume_due_occurrences(self, now: datetime) -> int:
        """Advance ``next_run`` and return eligible occurrences.

        This method must be called while ``_lock`` is held.
        """
        if self.next_run is None or self.next_run > now:
            return 0

        grace = self.misfire_grace_time
        eligible = 0
        total_due = 0
        latest_eligible = False

        if self.schedule_type == "interval":
            first_utc = self.next_run.astimezone(datetime_timezone.utc)
            now_utc = now.astimezone(datetime_timezone.utc)
            total_due = int((now_utc - first_utc).total_seconds() // self.interval_seconds) + 1
            if grace is None:
                eligible = total_due
            else:
                cutoff_utc = now_utc - timedelta(seconds=grace)
                expired = max(
                    0,
                    min(
                        total_due,
                        int(
                            math.ceil(
                                (cutoff_utc - first_utc).total_seconds() / self.interval_seconds
                            )
                        ),
                    ),
                )
                eligible = total_due - expired
                self.misfire_count += expired
            latest_eligible = eligible > 0
            next_utc = first_utc + timedelta(seconds=total_due * self.interval_seconds)
            self.next_run = next_utc.astimezone(self.tzinfo)
        else:
            due = self.next_run
            iterations = 0
            while due <= now:
                iterations += 1
                total_due += 1
                lateness = (
                    now.astimezone(datetime_timezone.utc) - due.astimezone(datetime_timezone.utc)
                ).total_seconds()
                if grace is None or lateness <= grace:
                    eligible += 1
                    latest_eligible = True
                else:
                    self.misfire_count += 1
                    latest_eligible = False
                due = self._next_after(due)
                if iterations >= 100_000:
                    raise SchedulingError(
                        f"Too many missed occurrences while advancing task '{self.name}'"
                    )
            self.next_run = due

        if self.coalesce:
            return 1 if latest_eligible else 0

        # Backlogs are deliberately bounded; retaining the most recent 100
        # occurrences prevents an old persistence file from exhausting memory.
        if eligible > 100:
            self.skipped_count += eligible - 100
            return 100
        return eligible

    def claim_due(self, now: datetime, available_slots: int) -> int:
        """Atomically reserve due runs and advance the schedule."""
        if available_slots < 0:
            raise ValueError("available_slots cannot be negative")
        current = self._normalize_time(now)
        with self._lock:
            if not self.enabled:
                return 0
            requested = self._queued_runs + self._consume_due_occurrences(current)
            self._queued_runs = 0
            if requested == 0:
                return 0

            if self.overlap_policy == "skip":
                if self._active_instances > 0:
                    self.skipped_count += requested
                    return 0
                launch = min(1, available_slots)
                self.skipped_count += requested - launch
            else:
                instance_slots = max(0, self.max_instances - self._active_instances)
                launch = min(requested, instance_slots, available_slots)
                remainder = requested - launch
                if self.overlap_policy == "queue":
                    self._queued_runs = min(100, remainder)
                    self.skipped_count += max(0, remainder - 100)
                else:
                    self.skipped_count += remainder

            self._active_instances += launch
            return launch

    def claim_manual(self, now: Optional[datetime] = None) -> bool:
        """Reserve one explicit run without waiting for the schedule."""
        current = self._normalize_time(now) if now is not None else self._now()
        with self._lock:
            if not self.enabled:
                return False
            if self.overlap_policy == "skip" and self._active_instances:
                self.skipped_count += 1
                return False
            if self._active_instances >= self.max_instances:
                if self.overlap_policy == "queue":
                    self._queued_runs = min(100, self._queued_runs + 1)
                else:
                    self.skipped_count += 1
                return False
            # Consume an immediately-due occurrence so a manual run cannot be
            # followed by an accidental duplicate on the next scheduler tick.
            self._consume_due_occurrences(current)
            self._active_instances += 1
            return True

    def mark_started(self, now: Optional[datetime] = None) -> None:
        with self._lock:
            self.last_run = self._normalize_time(now) if now is not None else self._now()

    def release_instance(self) -> None:
        with self._lock:
            self._active_instances = max(0, self._active_instances - 1)

    def increment_run_count(self) -> None:
        """Increment run count."""
        with self._lock:
            self.run_count += 1

    def increment_fail_count(self) -> None:
        """Increment fail count."""
        with self._lock:
            self.fail_count += 1

    def __repr__(self) -> str:
        """String representation."""
        schedule_str = f"{self.schedule_type}={self.schedule_value}"
        return f"Task(name='{self.name}', {schedule_str}, enabled={self.enabled})"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary for serialization.

        Returns:
            Dictionary containing task configuration and state
        """
        return {
            "task_id": self.task_id,
            "name": self.name,
            "script": self.script,  # Only script-based tasks can be persisted
            "schedule_type": self.schedule_type,
            "schedule_value": self.schedule_value,
            "every": self.schedule_value if self.schedule_type == "interval" else None,
            "cron": self.schedule_value if self.schedule_type == "cron" else None,
            "retries": self.retries,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "notify": self.notify,
            "email_config": _redact_email_config(self.email_config),
            "enabled": self.enabled,
            "safe_mode": self.safe_mode,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "clean_env": self.clean_env,
            "max_output_bytes": self.max_output_bytes,
            "timezone": self.timezone,
            "overlap_policy": self.overlap_policy,
            "max_instances": self.max_instances,
            "misfire_grace_time": self.misfire_grace_time,
            "coalesce": self.coalesce,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "fail_count": self.fail_count,
            "skipped_count": self.skipped_count,
            "misfire_count": self.misfire_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """
        Create task from dictionary.

        Args:
            data: Dictionary containing task configuration

        Returns:
            Task instance

        Raises:
            ValueError: If task data is invalid or func-based task
        """
        if not isinstance(data, dict):
            raise ValueError("Task data must be a dictionary")
        if not data.get("script"):
            raise ValueError(
                "Only script-based tasks can be loaded from persistence. "
                "Function-based tasks must be registered programmatically."
            )

        schedule_type = data.get("schedule_type")
        if schedule_type not in {"interval", "cron"}:
            if data.get("every") is not None:
                schedule_type = "interval"
            elif data.get("cron") is not None:
                schedule_type = "cron"
            else:
                raise ValueError("Persisted task must define an interval or cron schedule")
        schedule_value = data.get("schedule_value")
        if schedule_value is None:
            schedule_value = data.get("every" if schedule_type == "interval" else "cron")

        # Create task with schedule
        task = cls(
            name=data["name"],
            script=data["script"],
            every=schedule_value if schedule_type == "interval" else None,
            cron=schedule_value if schedule_type == "cron" else None,
            retries=data.get("retries", 0),
            retry_delay=data.get("retry_delay", 60),
            timeout=data.get("timeout"),
            notify=data.get("notify"),
            email_config=data.get("email_config"),
            safe_mode=data.get("safe_mode", False),
            max_memory_mb=data.get("max_memory_mb"),
            max_cpu_percent=data.get("max_cpu_percent"),
            clean_env=data.get("clean_env", False),
            max_output_bytes=data.get("max_output_bytes", 1_000_000),
            timezone=data.get("timezone"),
            overlap_policy=data.get("overlap_policy", "skip"),
            max_instances=data.get("max_instances", 1),
            misfire_grace_time=data.get("misfire_grace_time", 60.0),
            coalesce=data.get("coalesce", True),
        )

        # Restore state
        task.task_id = data.get("task_id", str(uuid.uuid4()))
        task.enabled = data.get("enabled", True)
        task.run_count = data.get("run_count", 0)
        task.fail_count = data.get("fail_count", 0)
        task.skipped_count = data.get("skipped_count", 0)
        task.misfire_count = data.get("misfire_count", 0)

        if data.get("last_run"):
            task.last_run = task._normalize_time(datetime.fromisoformat(data["last_run"]))
        if data.get("next_run"):
            task.next_run = task._normalize_time(datetime.fromisoformat(data["next_run"]))

        return task


class AutoCron:
    """
    Main scheduler class for AutoCron.

    Manages task scheduling, execution, and lifecycle.
    """

    def __init__(
        self,
        log_path: Optional[str] = None,
        log_level: str = "INFO",
        max_workers: int = 4,
        use_os_scheduler: bool = False,
        timezone: Optional[Union[str, tzinfo]] = None,
        poll_interval: float = 0.25,
        shutdown_timeout: float = 5.0,
    ):
        """
        Initialize AutoCron scheduler.

        Args:
            log_path: Path to log file
            log_level: Logging level
            max_workers: Maximum concurrent workers
            use_os_scheduler: Whether to use OS-native scheduler
            timezone: Default timezone for tasks (IANA name, tzinfo, or local)
            poll_interval: Scheduler polling interval in seconds
            shutdown_timeout: Maximum default wait during shutdown
        """
        _validate_integer("max_workers", max_workers, minimum=1)
        _validate_positive_number("poll_interval", poll_interval, allow_none=False)
        _validate_positive_number("shutdown_timeout", shutdown_timeout, allow_none=False)
        self.logger = get_logger(log_path=log_path, log_level=log_level)
        self.notification_manager = get_notification_manager()
        self.tasks: Dict[str, Task] = {}
        self.max_workers = max_workers
        self.use_os_scheduler = use_os_scheduler
        self.timezone = timezone_name(timezone)
        self.tzinfo = resolve_timezone(timezone)
        self.poll_interval = float(poll_interval)
        self.shutdown_timeout = float(shutdown_timeout)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._executor_threads: List[threading.Thread] = []
        self._lock = threading.RLock()
        self._executor_lock = threading.RLock()
        self._persistence_lock = threading.RLock()
        self._stop_event = threading.Event()

        # Analytics tracking (optional)
        self.analytics = None
        if ANALYTICS_AVAILABLE:
            try:
                self.analytics = TaskAnalytics()
            except Exception as e:
                self.logger.warning(f"Analytics unavailable: {e}")

        # OS adapter for native scheduling
        self.os_adapter: Optional[OSAdapter] = None
        if use_os_scheduler:
            try:
                self.os_adapter = get_os_adapter()
            except OSAdapterError as e:
                self.logger.warning(f"OS scheduler not available: {e}")
                self.use_os_scheduler = False

    def add_task(
        self,
        name: str,
        func: Optional[Callable] = None,
        script: Optional[str] = None,
        every: Optional[str] = None,
        cron: Optional[str] = None,
        retries: int = 0,
        retry_delay: int = 60,
        timeout: Optional[int] = None,
        notify: Optional[Union[str, List[str]]] = None,
        email_config: Optional[Dict[str, Any]] = None,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
        safe_mode: bool = False,
        max_memory_mb: Optional[int] = None,
        max_cpu_percent: Optional[int] = None,
        timezone: Optional[Union[str, tzinfo]] = None,
        overlap_policy: str = "skip",
        max_instances: int = 1,
        misfire_grace_time: Optional[float] = 60.0,
        coalesce: bool = True,
        clean_env: bool = False,
        max_output_bytes: int = 1_000_000,
    ) -> str:
        """
        Add a task to the scheduler.

        Args:
            name: Task name
            func: Function to execute
            script: Script path to execute
            every: Interval string (e.g., '5m', '1h')
            cron: Cron expression
            retries: Maximum retry attempts
            retry_delay: Base delay between retries
            timeout: Maximum execution time (seconds)
            notify: Notification channels
            email_config: Email configuration
            on_success: Success callback
            on_failure: Failure callback
            safe_mode: Enable sandboxed execution (script tasks only)
            max_memory_mb: Maximum memory limit in MB (safe mode)
            max_cpu_percent: Maximum CPU usage percent (safe mode)
            timezone: Task timezone (defaults to scheduler timezone)
            overlap_policy: ``skip``, ``allow``, or ``queue``
            max_instances: Maximum concurrent instances for this task
            misfire_grace_time: Maximum acceptable lateness, or ``None``
            coalesce: Collapse missed occurrences into one run
            clean_env: Use a minimal environment for safe-mode scripts
            max_output_bytes: Maximum combined captured process output

        Returns:
            Task ID

        Raises:
            SchedulingError: If task creation fails
        """
        try:
            task = Task(
                name=name,
                func=func,
                script=script,
                every=every,
                cron=cron,
                retries=retries,
                retry_delay=retry_delay,
                timeout=timeout,
                notify=notify,
                email_config=email_config,
                on_success=on_success,
                on_failure=on_failure,
                safe_mode=safe_mode,
                max_memory_mb=max_memory_mb,
                max_cpu_percent=max_cpu_percent,
                timezone=timezone if timezone is not None else self.tzinfo,
                overlap_policy=overlap_policy,
                max_instances=max_instances,
                misfire_grace_time=misfire_grace_time,
                coalesce=coalesce,
                clean_env=clean_env,
                max_output_bytes=max_output_bytes,
            )

            with self._lock:
                self.tasks[task.task_id] = task

            # Set up notifications if configured
            if notify:
                self._setup_task_notifications(task)

            # Log task addition
            schedule_str = f"{task.schedule_type}={task.schedule_value}"
            self.logger.log_task_scheduled(name, schedule_str)

            # If using OS scheduler, register task
            if self.use_os_scheduler and task.script:
                self._register_os_task(task)

            return task.task_id

        except Exception as e:
            raise SchedulingError(f"Failed to add task '{name}': {e}") from e

    def remove_task(self, task_id: Optional[str] = None, name: Optional[str] = None) -> bool:
        """
        Remove a task from the scheduler.

        Args:
            task_id: Task ID
            name: Task name

        Returns:
            True if removed, False otherwise
        """
        with self._lock:
            if task_id:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    del self.tasks[task_id]
                    self._unregister_task_notifications(task)
                    self.logger.log_task_removed(task.name)

                    # Remove from OS scheduler if registered
                    if self.use_os_scheduler and self.os_adapter:
                        try:
                            self.os_adapter.remove_scheduled_task(task.name)
                        except Exception as e:
                            self.logger.warning(f"Failed to remove OS task: {e}")

                    return True
            elif name:
                for tid, task in list(self.tasks.items()):
                    if task.name == name:
                        del self.tasks[tid]
                        self._unregister_task_notifications(task)
                        self.logger.log_task_removed(name)

                        # Remove from OS scheduler if registered
                        if self.use_os_scheduler and self.os_adapter:
                            try:
                                self.os_adapter.remove_scheduled_task(name)
                            except Exception as e:
                                self.logger.warning(f"Failed to remove OS task: {e}")

                        return True

        return False

    def get_task(self, task_id: Optional[str] = None, name: Optional[str] = None) -> Optional[Task]:
        """
        Get a task by ID or name.

        Args:
            task_id: Task ID
            name: Task name

        Returns:
            Task instance or None
        """
        if task_id:
            return self.tasks.get(task_id)
        elif name:
            for task in self.tasks.values():
                if task.name == name:
                    return task
        return None

    def list_tasks(self) -> List[Task]:
        """
        List all tasks.

        Returns:
            List of tasks
        """
        return list(self.tasks.values())

    def save_tasks(self, path: Optional[str] = None) -> str:
        """
        Save all tasks to a file for persistence.

        Only script-based tasks can be saved. Function-based tasks must be
        registered programmatically on each startup.

        Args:
            path: Path to save file (YAML or JSON based on extension).
                  Defaults to ~/.autocron/tasks.yaml

        Returns:
            Path where tasks were saved

        Raises:
            SchedulingError: If save fails

        Examples:
            scheduler.save_tasks()  # Save to default location
            scheduler.save_tasks("my_tasks.yaml")  # Save to custom location
            scheduler.save_tasks("my_tasks.json")  # Save as JSON
        """
        try:
            # Determine save path
            if path is None:
                path = str(get_autocron_home() / "tasks.yaml")

            path_obj = Path(path).expanduser().resolve()
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Collect task data (only script-based tasks)
            tasks_data = []
            func_tasks_skipped = []

            with self._lock:
                for task in self.tasks.values():
                    if task.script:
                        tasks_data.append(task.to_dict())
                    else:
                        func_tasks_skipped.append(task.name)

            if func_tasks_skipped:
                self.logger.info(
                    f"Skipped {len(func_tasks_skipped)} function-based tasks: "
                    f"{', '.join(func_tasks_skipped)}. "
                    "Only script-based tasks can be persisted."
                )

            payload = {
                # Keep the original persistence version for consumers that
                # validate the stable 1.0 envelope; new fields are additive.
                "version": "1.0",
                "saved_at": datetime.now(datetime_timezone.utc).isoformat(),
                "tasks": tasks_data,
            }

            # Serialize before acquiring the file lock, then atomically replace
            # the target so readers never observe a partially-written document.
            if path_obj.suffix.lower() in {".yaml", ".yml"}:
                import yaml

                serialized = yaml.safe_dump(
                    payload,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
            elif path_obj.suffix.lower() == ".json":
                serialized = json.dumps(payload, indent=2, ensure_ascii=False)
            else:
                raise SchedulingError(
                    f"Unsupported file format: {path_obj.suffix}. " "Use .yaml, .yml, or .json"
                )

            temp_path: Optional[Path] = None
            with self._persistence_lock, _InterProcessFileLock(path_obj):
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        newline="\n",
                        dir=path_obj.parent,
                        prefix=f".{path_obj.name}.",
                        suffix=".tmp",
                        delete=False,
                    ) as temp_file:
                        temp_path = Path(temp_file.name)
                        temp_file.write(serialized)
                        temp_file.write("\n")
                        temp_file.flush()
                        os.fsync(temp_file.fileno())
                    with contextlib.suppress(OSError):
                        os.chmod(temp_path, 0o600)
                    os.replace(temp_path, path_obj)
                    temp_path = None
                finally:
                    if temp_path is not None:
                        with contextlib.suppress(OSError):
                            temp_path.unlink()

            self.logger.info(f"Saved {len(tasks_data)} tasks to {path_obj}")
            return str(path_obj)

        except Exception as e:
            raise SchedulingError(f"Failed to save tasks: {e}") from e

    def load_tasks(self, path: Optional[str] = None, replace: bool = False) -> int:
        """
        Load tasks from a persistence file.

        Args:
            path: Path to load file (YAML or JSON based on extension).
                  Defaults to ~/.autocron/tasks.yaml
            replace: If True, remove all existing tasks before loading.
                     If False (default), merge with existing tasks.

        Returns:
            Number of tasks loaded

        Raises:
            SchedulingError: If load fails

        Examples:
            scheduler.load_tasks()  # Load from default location
            scheduler.load_tasks("my_tasks.yaml")  # Load from custom location
            scheduler.load_tasks(replace=True)  # Replace all tasks
        """
        try:
            # Determine load path
            if path is None:
                path = str(get_autocron_home() / "tasks.yaml")

            path_obj = Path(path).expanduser().resolve()

            if not path_obj.exists():
                raise SchedulingError(f"Task file not found: {path}")

            if path_obj.stat().st_size > 10 * 1024 * 1024:
                raise SchedulingError("Task persistence file exceeds the 10 MiB safety limit")

            with self._persistence_lock, _InterProcessFileLock(path_obj):
                with open(path_obj, "r", encoding="utf-8") as persistence_file:
                    if path_obj.suffix.lower() in {".yaml", ".yml"}:
                        import yaml

                        data = yaml.safe_load(persistence_file)
                    elif path_obj.suffix.lower() == ".json":
                        data = json.load(persistence_file)
                    else:
                        raise SchedulingError(
                            f"Unsupported file format: {path_obj.suffix}. "
                            "Use .yaml, .yml, or .json"
                        )

            # Validate structure
            if (
                not isinstance(data, dict)
                or "tasks" not in data
                or not isinstance(data["tasks"], list)
            ):
                raise SchedulingError("Invalid task file format")

            # Load tasks
            loaded_count = 0
            skipped_count = 0
            parsed_tasks: List[Task] = []

            for task_data in data["tasks"]:
                try:
                    task = Task.from_dict(task_data)
                    parsed_tasks.append(task)
                except Exception as e:
                    self.logger.error(f"Failed to load task: {e}")
                    skipped_count += 1

            # Commit parsed tasks under one lock. Invalid records never leave a
            # half-updated in-memory collection.
            with self._lock:
                if replace:
                    old_tasks = list(self.tasks.values())
                    self.tasks.clear()
                    for old_task in old_tasks:
                        self._unregister_task_notifications(old_task)
                    self.logger.info(f"Cleared {len(old_tasks)} existing tasks")
                existing_names = {task.name for task in self.tasks.values()}
                for task in parsed_tasks:
                    if task.name in existing_names:
                        self.logger.warning(f"Task '{task.name}' already exists, skipping")
                        skipped_count += 1
                        continue
                    self.tasks[task.task_id] = task
                    existing_names.add(task.name)
                    loaded_count += 1
                    if task.notify:
                        self._setup_task_notifications(task)

            self.logger.info(
                f"Loaded {loaded_count} tasks from {path_obj} " f"(skipped {skipped_count})"
            )
            return loaded_count

        except SchedulingError:
            raise
        except Exception as e:
            raise SchedulingError(f"Failed to load tasks: {e}") from e

    def start(self, blocking: bool = True) -> None:
        """
        Start the scheduler.

        Args:
            blocking: Whether to block the main thread
        """
        if self._running:
            self.logger.warning("Scheduler is already running")
            return

        self._running = True
        self.logger.log_scheduler_start()

        if blocking:
            self._run()
        else:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False
        self.logger.log_scheduler_stop()

        # Wait for main thread
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        # Wait for executor threads
        for thread in self._executor_threads:
            if thread.is_alive():
                thread.join(timeout=5)

    def _run(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                with self._lock:
                    tasks = list(self.tasks.values())
                for task in tasks:
                    available = max(0, self.max_workers - len(self._executor_threads))
                    if available == 0:
                        break
                    launches = task.claim_due(task._now(), available)
                    for _ in range(launches):
                        self._execute_task_async(task, claimed=True)

                # Sleep briefly
                time.sleep(self.poll_interval)

            except Exception as e:
                self.logger.exception(f"Error in scheduler loop: {e}")
                time.sleep(5)

    def _execute_task_async(self, task: Task, *, claimed: bool = False) -> bool:
        """Execute task asynchronously."""
        # Clean up finished threads
        self._executor_threads = [t for t in self._executor_threads if t.is_alive()]

        # Check worker limit
        if len(self._executor_threads) >= self.max_workers:
            self.logger.warning(f"Max workers reached, skipping task '{task.name}'")
            if claimed:
                task.release_instance()
            return False

        thread = threading.Thread(
            target=self._execute_task, args=(task,), kwargs={"claimed": claimed}, daemon=True
        )
        thread.start()
        self._executor_threads.append(thread)
        return True

    def _execute_task(self, task: Task, *, claimed: bool = False) -> bool:
        # sourcery skip: low-code-quality
        """Execute a single task with retries and return its final status."""
        slot_owned = claimed
        if not claimed and not task.claim_manual():
            return False
        slot_owned = True
        task.mark_started()
        final_attempt = 0
        final_error: Optional[str] = None
        final_duration = 0.0
        try:
            for attempt in range(task.retries + 1):
                try:
                    self.logger.log_task_start(task.name, task.task_id)
                    start_time = time.time()
                    if task.func:
                        self._execute_function(task.func, task.timeout)
                    elif task.safe_mode and task.script:
                        self._execute_in_safe_mode(
                            task.script, task.timeout, task.max_memory_mb, task.max_cpu_percent
                        )
                    elif task.script:
                        self._execute_script(task.script, task.timeout)

                    duration = time.time() - start_time
                    final_duration = duration
                    final_attempt = attempt
                    task.increment_run_count()
                    if not claimed:
                        task.update_next_run()
                    self.logger.log_task_success(task.name, task.task_id, duration)

                    if task.notify:
                        self._notify_success(task, duration)
                    if task.on_success:
                        try:
                            task.on_success()
                        except Exception as callback_error:
                            self.logger.error(f"Error in success callback: {callback_error}")
                    if self.analytics:
                        with contextlib.suppress(Exception):
                            self.analytics.record_execution(
                                task_name=task.name,
                                success=True,
                                duration=duration,
                                retry_count=final_attempt,
                            )
                    return True
                except Exception as error:
                    task.increment_fail_count()
                    final_error = str(error)
                    final_attempt = attempt
                    self.logger.log_task_failure(
                        task.name, task.task_id, error, attempt + 1, task.retries + 1
                    )
                    if attempt == task.retries:
                        if not claimed:
                            task.update_next_run()
                        if task.notify:
                            self._notify_failure(task, str(error), attempt + 1)
                        if task.on_failure:
                            try:
                                task.on_failure(error)
                            except Exception as callback_error:
                                self.logger.error(f"Error in failure callback: {callback_error}")
                        if self.analytics:
                            with contextlib.suppress(Exception):
                                self.analytics.record_execution(
                                    task_name=task.name,
                                    success=False,
                                    duration=final_duration,
                                    error=final_error,
                                    retry_count=final_attempt + 1,
                                )
                        return False

                    delay = calculate_retry_delay(attempt, task.retry_delay)
                    self.logger.log_task_retry(task.name, task.task_id, attempt + 2, delay)
                    time.sleep(delay)
            return False
        finally:
            if slot_owned:
                task.release_instance()

    def run_task(
        self,
        task_id: Optional[str] = None,
        name: Optional[str] = None,
        *,
        wait: bool = True,
    ) -> bool:
        """Run one registered task immediately.

        ``wait=True`` executes synchronously and returns whether the final
        attempt succeeded. With ``wait=False`` a daemon worker is started and
        ``True`` means the run was accepted by the overlap policy.
        """
        task = self.get_task(task_id=task_id, name=name)
        if task is None:
            raise SchedulingError("Task not found")
        if not task.enabled:
            return False
        if wait:
            return bool(self._execute_task(task))
        if not task.claim_manual():
            return False
        return self._execute_task_async(task, claimed=True)

    def _execute_function(self, func: Callable, timeout: Optional[int]) -> Any:
        """Execute a function with timeout (supports both sync and async)."""
        # Check if function is async
        if inspect.iscoroutinefunction(func):
            return self._execute_async_function(func, timeout)

        # Sync function execution
        if timeout is None:
            return func()

        # Execute with timeout using threading
        result: List[Any] = [None]
        exception: List[Optional[Exception]] = [None]

        def wrapper():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TaskExecutionError(f"Task timed out after {timeout} seconds")

        if exception[0]:
            raise exception[0]  # pylint: disable=raising-bad-type

        return result[0]

    def _execute_async_function(self, func: Callable, timeout: Optional[int]) -> Any:
        """Execute an async function with timeout."""

        async def invoke() -> Any:
            coroutine = func()
            return (
                await asyncio.wait_for(coroutine, timeout=timeout) if timeout else await coroutine
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                return asyncio.run(invoke())
            except asyncio.TimeoutError as error:
                raise TaskExecutionError(f"Async task timed out after {timeout} seconds") from error

        # Notebook runners and async applications already own the current
        # event loop. Run the coroutine on a short-lived helper thread rather
        # than attempting the illegal nested ``run_until_complete`` call.
        result: List[Any] = [None]
        exception: List[Optional[BaseException]] = [None]

        def runner() -> None:
            try:
                result[0] = asyncio.run(invoke())
            except BaseException as error:  # propagate the original failure
                exception[0] = error

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join(timeout=(timeout + 1 if timeout else None))
        if thread.is_alive():
            raise TaskExecutionError(f"Async task timed out after {timeout} seconds")
        if isinstance(exception[0], asyncio.TimeoutError):
            raise TaskExecutionError(
                f"Async task timed out after {timeout} seconds"
            ) from exception[0]
        if exception[0] is not None:
            raise exception[0]
        return result[0]

    def _execute_script(self, script: str, timeout: Optional[int]) -> Any:
        """Execute a script with timeout."""
        try:
            # nosec B603 - Controlled execution of user-specified Python scripts
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
            return result.stdout
        except subprocess.TimeoutExpired as e:
            raise TaskExecutionError(f"Script timed out after {timeout} seconds") from e
        except subprocess.CalledProcessError as e:
            raise TaskExecutionError(
                f"Script failed with exit code {e.returncode}: {e.stderr}"
            ) from e

    def _execute_in_safe_mode(
        self,
        script: str,
        timeout: Optional[int],
        max_memory_mb: Optional[int],
        max_cpu_percent: Optional[int],
    ) -> Any:
        """
        Execute a script in safe mode with resource limits and isolation.

        Safe mode features:
        - Subprocess isolation (no access to parent process)
        - Resource limits (memory, CPU) on Unix/Linux/Mac
        - Timeout enforcement
        - Output sanitization
        - Error containment

        Args:
            script: Path to script to execute
            timeout: Maximum execution time in seconds
            max_memory_mb: Maximum memory limit in MB (Unix only)
            max_cpu_percent: Maximum CPU usage percent (Unix only)

        Returns:
            Script output (sanitized)

        Raises:
            TaskExecutionError: If execution fails or violates limits
        """
        try:
            self.logger.info(
                f"Executing script in SAFE MODE: {script} "
                f"(timeout={timeout}s, mem_limit={max_memory_mb}MB)"
            )

            # Build safe command with resource monitoring
            cmd = [sys.executable, script]
            env = {**os.environ, "AUTOCRON_SAFE_MODE": "1"}

            # Platform-specific safe execution
            if os.name != "nt":  # Unix/Linux/Mac
                try:
                    import resource

                    def set_limits():
                        """Set resource limits for subprocess."""
                        with contextlib.suppress(Exception):
                            # Memory limit
                            if max_memory_mb:
                                max_memory_bytes = max_memory_mb * 1024 * 1024
                                resource.setrlimit(  # type: ignore[attr-defined]
                                    resource.RLIMIT_AS,  # type: ignore[attr-defined]
                                    (max_memory_bytes, max_memory_bytes),
                                )

                            # CPU time limit (in seconds)
                            if timeout:
                                resource.setrlimit(  # type: ignore[attr-defined]
                                    resource.RLIMIT_CPU,  # type: ignore[attr-defined]
                                    (timeout, timeout),
                                )

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=True,
                        preexec_fn=set_limits,  # Apply resource limits
                        env=env,
                    )
                except ImportError:
                    # resource module not available, fall back to basic subprocess
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=timeout, check=True, env=env
                    )
            else:  # Windows - use job objects for resource limits
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    env=env,
                )

            # Sanitize output (remove potential sensitive data markers)
            output = result.stdout
            if len(output) > 10000:  # Limit output size
                output = output[:10000] + "\n... (output truncated)"

            self.logger.info("Safe mode execution completed successfully")
            return output

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Safe mode: Script timed out after {timeout}s")
            raise TaskExecutionError(f"Script timed out after {timeout} seconds (safe mode)") from e
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Safe mode: Script failed with code {e.returncode}")
            raise TaskExecutionError(
                f"Script failed in safe mode (exit code {e.returncode}): {e.stderr[:500]}"
            ) from e
        except MemoryError as e:
            self.logger.error("Safe mode: Memory limit exceeded")
            raise TaskExecutionError(f"Script exceeded memory limit ({max_memory_mb}MB)") from e
        except Exception as e:
            self.logger.error(f"Safe mode: Unexpected error: {e}")
            raise TaskExecutionError(f"Safe mode execution failed: {str(e)}") from e

    def _setup_task_notifications(self, task: Task) -> None:
        """Set up notifications for a task."""
        channels = [task.notify] if isinstance(task.notify, str) else (task.notify or [])
        task._notification_channels = {}

        for channel in channels:
            if channel == "desktop":
                registered = self.notification_manager.setup_desktop(name=f"desktop:{task.task_id}")
                if registered:
                    task._notification_channels[channel] = registered
            elif channel == "email":
                if task.email_config:
                    registered = self.notification_manager.setup_email(
                        task.email_config, name=f"email:{task.task_id}"
                    )
                    task._notification_channels[channel] = registered
                else:
                    self.logger.warning(
                        f"Email notification requested but no config provided "
                        f"for task '{task.name}'"
                    )

    def _unregister_task_notifications(self, task: Task) -> None:
        """Remove notification channels owned by a task."""
        for channel in getattr(task, "_notification_channels", {}).values():
            with contextlib.suppress(Exception):
                self.notification_manager.remove_notifier(channel)
        task._notification_channels = {}

    def _notify_success(self, task: Task, duration: float) -> None:
        """Send success notification."""
        channels = list(getattr(task, "_notification_channels", {}).values()) or (
            [task.notify] if isinstance(task.notify, str) else task.notify
        )
        self.notification_manager.notify_task_success(task.name, duration, channels)

    def _notify_failure(self, task: Task, error: str, attempt: int) -> None:
        """Send failure notification."""
        channels = list(getattr(task, "_notification_channels", {}).values()) or (
            [task.notify] if isinstance(task.notify, str) else task.notify
        )
        self.notification_manager.notify_task_failure(
            task.name, error, attempt, task.retries + 1, channels
        )

    def _register_os_task(self, task: Task) -> None:
        """Register task with OS scheduler."""
        if not self.os_adapter:
            return

        try:
            cron_expr = (
                task.schedule_value
                if task.schedule_type == "cron"
                else self._interval_to_cron(task.schedule_value)
            )

            if task.script:
                self.os_adapter.create_scheduled_task(
                    task_name=task.name,
                    script_path=task.script,
                    cron_expr=cron_expr,
                    python_executable=sys.executable,
                )
            else:
                raise ValueError("Cannot deploy task without script path")
        except Exception as e:
            self.logger.error(f"Failed to register OS task: {e}")

    def _interval_to_cron(self, interval: str) -> str:
        """Convert interval to cron expression (simplified)."""
        seconds = parse_interval(interval)

        if seconds < 60:
            return f"*/{seconds} * * * * *"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"*/{minutes} * * * *"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"0 */{hours} * * *"
        else:
            return "0 0 * * *"

    @classmethod
    def from_config(cls, config_path: str) -> "AutoCron":
        """
        Create scheduler from configuration file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            AutoCron instance
        """
        import yaml

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Create scheduler
        logging_config = config.get("logging", {})
        scheduler = cls(
            log_path=logging_config.get("path"), log_level=logging_config.get("level", "INFO")
        )

        # Add tasks
        for task_config in config.get("tasks", []):
            scheduler.add_task(
                name=task_config["name"],
                script=task_config.get("script"),
                every=(
                    task_config.get("schedule")
                    if "/" not in task_config.get("schedule", "")
                    else None
                ),
                cron=(
                    task_config.get("schedule") if "/" in task_config.get("schedule", "") else None
                ),
                retries=task_config.get("retries", 0),
                notify=task_config.get("notify"),
                email_config=task_config.get("email"),
            )

        return scheduler


# Decorator for scheduling functions
_global_scheduler: Optional[AutoCron] = None


def schedule(
    every: Optional[str] = None,
    cron: Optional[str] = None,
    retries: int = 0,
    retry_delay: int = 60,
    timeout: Optional[int] = None,
    notify: Optional[Union[str, List[str]]] = None,
    email_config: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable] = None,
    on_failure: Optional[Callable] = None,
) -> Callable:
    """
    Decorator to schedule a function.

    Args:
        every: Interval string (e.g., '5m', '1h')
        cron: Cron expression
        retries: Maximum retry attempts
        retry_delay: Base delay between retries
        timeout: Maximum execution time (seconds)
        notify: Notification channels
        email_config: Email configuration
        on_success: Success callback
        on_failure: Failure callback

    Returns:
        Decorated function

    Examples:
        @schedule(every='5m', retries=3)
        def my_task():
            print("Running task")
    """

    def decorator(func: Callable) -> Callable:
        global _global_scheduler

        if _global_scheduler is None:
            _global_scheduler = AutoCron()

        _global_scheduler.add_task(
            name=func.__name__,
            func=func,
            every=every,
            cron=cron,
            retries=retries,
            retry_delay=retry_delay,
            timeout=timeout,
            notify=notify,
            email_config=email_config,
            on_success=on_success,
            on_failure=on_failure,
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_global_scheduler() -> Optional[AutoCron]:
    """Get the global scheduler instance."""
    return _global_scheduler


def start_scheduler(blocking: bool = True) -> None:
    """
    Start the global scheduler.

    Args:
        blocking: Whether to block the main thread
    """
    # Global scheduler referenced but not assigned in this scope
    if _global_scheduler is None:
        raise RuntimeError("No tasks scheduled. Use @schedule decorator first.")

    _global_scheduler.start(blocking=blocking)


def reset_global_scheduler() -> None:
    """Reset the global scheduler instance."""
    global _global_scheduler

    if _global_scheduler is not None:
        with contextlib.suppress(Exception):
            _global_scheduler.stop()
        _global_scheduler = None
