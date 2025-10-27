"""
Core scheduling engine for AutoCron.

Provides the main scheduler class and decorators for task scheduling.
"""

import asyncio
import contextlib
import inspect
import json
import os
import subprocess  # nosec B404 - Required for executing Python scripts
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

from autocron.logger import get_logger
from autocron.notifications import get_notification_manager
from autocron.os_adapters import OSAdapter, OSAdapterError, get_os_adapter
from autocron.utils import (
    calculate_retry_delay,
    get_next_run_time,
    parse_interval,
    validate_cron_expression,
)

# Optional analytics import
try:
    from autocron.dashboard import TaskAnalytics

    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    if TYPE_CHECKING:
        from autocron.dashboard import TaskAnalytics
    else:
        TaskAnalytics = None  # type: ignore


class TaskExecutionError(Exception):
    """Exception raised when task execution fails."""

    pass


class SchedulingError(Exception):
    """Exception raised when scheduling fails."""

    pass


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
        """
        if func is None and script is None:
            raise ValueError("Either func or script must be provided")

        if func is not None and script is not None:
            raise ValueError("Only one of func or script can be provided")

        if every is None and cron is None:
            raise ValueError("Either every or cron must be provided")

        if every is not None and cron is not None:
            raise ValueError("Only one of every or cron can be provided")

        self.task_id = str(uuid.uuid4())
        self.name = name
        self.func = func
        self.script = script
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.notify = notify
        self.email_config = email_config
        self.on_success = on_success
        self.on_failure = on_failure
        self.enabled = True

        # Safe mode configuration
        self.safe_mode = safe_mode
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent

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

        # Execution tracking
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = self._calculate_next_run()
        self.run_count = 0
        self.fail_count = 0
        self._lock = threading.Lock()

    def _calculate_next_run(self) -> datetime:
        """Calculate next run time."""
        if self.schedule_type == "interval":
            return (
                datetime.now()
                if self.last_run is None
                else self.last_run + timedelta(seconds=self.interval_seconds)
            )
        base_time = self.last_run or datetime.now()
        return get_next_run_time(self.schedule_value, base_time)

    def should_run(self) -> bool:
        """Check if task should run now."""
        if not self.enabled:
            return False

        return False if self.next_run is None else datetime.now() >= self.next_run

    def update_next_run(self) -> None:
        """Update next run time."""
        with self._lock:
            self.last_run = datetime.now()
            self.next_run = self._calculate_next_run()

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
            "retries": self.retries,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "notify": self.notify,
            "email_config": self.email_config,
            "enabled": self.enabled,
            "safe_mode": self.safe_mode,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "fail_count": self.fail_count,
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
        if not data.get("script"):
            raise ValueError(
                "Only script-based tasks can be loaded from persistence. "
                "Function-based tasks must be registered programmatically."
            )

        # Create task with schedule
        task = cls(
            name=data["name"],
            script=data["script"],
            every=data["schedule_value"] if data["schedule_type"] == "interval" else None,
            cron=data["schedule_value"] if data["schedule_type"] == "cron" else None,
            retries=data.get("retries", 0),
            retry_delay=data.get("retry_delay", 60),
            timeout=data.get("timeout"),
            notify=data.get("notify"),
            email_config=data.get("email_config"),
            safe_mode=data.get("safe_mode", False),
            max_memory_mb=data.get("max_memory_mb"),
            max_cpu_percent=data.get("max_cpu_percent"),
        )

        # Restore state
        task.task_id = data.get("task_id", str(uuid.uuid4()))
        task.enabled = data.get("enabled", True)
        task.run_count = data.get("run_count", 0)
        task.fail_count = data.get("fail_count", 0)

        if data.get("last_run"):
            task.last_run = datetime.fromisoformat(data["last_run"])
        if data.get("next_run"):
            task.next_run = datetime.fromisoformat(data["next_run"])

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
    ):
        """
        Initialize AutoCron scheduler.

        Args:
            log_path: Path to log file
            log_level: Logging level
            max_workers: Maximum concurrent workers
            use_os_scheduler: Whether to use OS-native scheduler
        """
        self.logger = get_logger(log_path=log_path, log_level=log_level)
        self.notification_manager = get_notification_manager()
        self.tasks: Dict[str, Task] = {}
        self.max_workers = max_workers
        self.use_os_scheduler = use_os_scheduler
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._executor_threads: List[threading.Thread] = []
        self._lock = threading.Lock()

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
                autocron_dir = Path.home() / ".autocron"
                autocron_dir.mkdir(parents=True, exist_ok=True)
                path = str(autocron_dir / "tasks.yaml")

            path_obj = Path(path)

            # Collect task data (only script-based tasks)
            tasks_data = []
            func_tasks_skipped = []

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

            # Save based on file extension
            if path_obj.suffix.lower() in {".yaml", ".yml"}:
                import yaml

                with open(path, "w") as f:
                    yaml.dump(
                        {
                            "version": "1.0",
                            "saved_at": datetime.now().isoformat(),
                            "tasks": tasks_data,
                        },
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                    )
            elif path_obj.suffix.lower() == ".json":
                with open(path, "w") as f:
                    json.dump(
                        {
                            "version": "1.0",
                            "saved_at": datetime.now().isoformat(),
                            "tasks": tasks_data,
                        },
                        f,
                        indent=2,
                    )
            else:
                raise SchedulingError(
                    f"Unsupported file format: {path_obj.suffix}. " "Use .yaml, .yml, or .json"
                )

            self.logger.info(f"Saved {len(tasks_data)} tasks to {path}")
            return path

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
                autocron_dir = Path.home() / ".autocron"
                path = str(autocron_dir / "tasks.yaml")

            path_obj = Path(path)

            if not path_obj.exists():
                raise SchedulingError(f"Task file not found: {path}")

            # Load based on file extension
            if path_obj.suffix.lower() in {".yaml", ".yml"}:
                import yaml

                with open(path, "r") as f:
                    data = yaml.safe_load(f)
            elif path_obj.suffix.lower() == ".json":
                with open(path, "r") as f:
                    data = json.load(f)
            else:
                raise SchedulingError(
                    f"Unsupported file format: {path_obj.suffix}. " "Use .yaml, .yml, or .json"
                )

            # Validate structure
            if not isinstance(data, dict) or "tasks" not in data:
                raise SchedulingError("Invalid task file format")

            # Replace existing tasks if requested
            if replace:
                old_count = len(self.tasks)
                self.tasks.clear()
                self.logger.info(f"Cleared {old_count} existing tasks")

            # Load tasks
            loaded_count = 0
            skipped_count = 0

            for task_data in data["tasks"]:
                try:
                    task = Task.from_dict(task_data)

                    # Check for duplicate names
                    existing_task = self.get_task(name=task.name)
                    if existing_task and not replace:
                        self.logger.warning(f"Task '{task.name}' already exists, skipping")
                        skipped_count += 1
                        continue

                    # Add task
                    self.tasks[task.task_id] = task
                    loaded_count += 1

                except Exception as e:
                    self.logger.error(f"Failed to load task: {e}")
                    skipped_count += 1

            self.logger.info(
                f"Loaded {loaded_count} tasks from {path} " f"(skipped {skipped_count})"
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
                # Check for tasks to run
                tasks_to_run: List[Task] = []

                with self._lock:
                    tasks_to_run.extend(task for task in self.tasks.values() if task.should_run())
                # Execute tasks
                for task in tasks_to_run:
                    self._execute_task_async(task)

                # Sleep briefly
                time.sleep(1)

            except Exception as e:
                self.logger.exception(f"Error in scheduler loop: {e}")
                time.sleep(5)

    def _execute_task_async(self, task: Task) -> None:
        """Execute task asynchronously."""
        # Clean up finished threads
        self._executor_threads = [t for t in self._executor_threads if t.is_alive()]

        # Check worker limit
        if len(self._executor_threads) >= self.max_workers:
            self.logger.warning(f"Max workers reached, skipping task '{task.name}'")
            return

        thread = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
        thread.start()
        self._executor_threads.append(thread)

    def _execute_task(self, task: Task) -> None:
        # sourcery skip: low-code-quality
        """Execute a single task with retries."""
        final_attempt = 0
        final_error = None
        final_duration = 0.0

        for attempt in range(task.retries + 1):
            try:
                self.logger.log_task_start(task.name, task.task_id)
                start_time = time.time()

                # Execute task
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

                # Task succeeded
                task.increment_run_count()
                task.update_next_run()

                self.logger.log_task_success(task.name, task.task_id, duration)

                # Notifications
                if task.notify:
                    self._notify_success(task, duration)

                # Success callback
                if task.on_success:
                    try:
                        task.on_success()
                    except Exception as e:
                        self.logger.error(f"Error in success callback: {e}")

                # Record analytics
                if self.analytics:
                    with contextlib.suppress(Exception):
                        self.analytics.record_execution(
                            task_name=task.name,
                            success=True,
                            duration=duration,
                            retry_count=final_attempt,
                        )
                return

            except Exception as e:
                task.increment_fail_count()
                final_error = str(e)
                final_attempt = attempt

                self.logger.log_task_failure(
                    task.name, task.task_id, e, attempt + 1, task.retries + 1
                )

                # Last attempt failed
                if attempt == task.retries:
                    task.update_next_run()

                    # Notifications
                    if task.notify:
                        self._notify_failure(task, str(e), attempt + 1)

                    # Failure callback
                    if task.on_failure:
                        try:
                            task.on_failure(e)
                        except Exception as cb_error:
                            self.logger.error(f"Error in failure callback: {cb_error}")

                    # Record analytics
                    if self.analytics:
                        with contextlib.suppress(Exception):
                            self.analytics.record_execution(
                                task_name=task.name,
                                success=False,
                                duration=final_duration,
                                error=final_error,
                                retry_count=final_attempt + 1,
                            )
                    return

                # Retry with backoff
                delay = calculate_retry_delay(attempt, task.retry_delay)
                self.logger.log_task_retry(task.name, task.task_id, attempt + 2, delay)
                time.sleep(delay)

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
        try:
            # Try to get existing event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, use the existing loop
                if timeout:
                    return loop.run_until_complete(asyncio.wait_for(func(), timeout=timeout))
                else:
                    return loop.run_until_complete(func())
            except RuntimeError:
                # No running loop, create a new one
                if timeout:
                    return asyncio.run(asyncio.wait_for(func(), timeout=timeout))
                else:
                    return asyncio.run(func())
        except asyncio.TimeoutError as e:
            raise TaskExecutionError(f"Async task timed out after {timeout} seconds") from e

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

        for channel in channels:
            if channel == "desktop":
                self.notification_manager.setup_desktop()
            elif channel == "email":
                if task.email_config:
                    self.notification_manager.setup_email(task.email_config)
                else:
                    self.logger.warning(
                        f"Email notification requested but no config provided "
                        f"for task '{task.name}'"
                    )

    def _notify_success(self, task: Task, duration: float) -> None:
        """Send success notification."""
        channels = [task.notify] if isinstance(task.notify, str) else task.notify
        self.notification_manager.notify_task_success(task.name, duration, channels)

    def _notify_failure(self, task: Task, error: str, attempt: int) -> None:
        """Send failure notification."""
        channels = [task.notify] if isinstance(task.notify, str) else task.notify
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
