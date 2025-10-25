"""
Core scheduling engine for AutoCron.

Provides the main scheduler class and decorators for task scheduling.
"""

import time
import threading
import subprocess  # nosec B404 - Required for executing Python scripts
import uuid
import contextlib
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List, Union
from functools import wraps
import sys
import os

from autocron.logger import get_logger, AutoCronLogger
from autocron.notifications import get_notification_manager, NotificationManager
from autocron.utils import (
    parse_interval,
    validate_cron_expression,
    get_next_run_time,
    calculate_retry_delay,
    sanitize_task_name,
    TimeParseError,
)
from autocron.os_adapters import get_os_adapter, OSAdapter, OSAdapterError


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

        # Schedule configuration
        if every is not None:
            self.schedule_type = "interval"
            self.schedule_value = every
            self.interval_seconds = parse_interval(every)
        else:
            self.schedule_type = "cron"
            self.schedule_value = cron
            if not validate_cron_expression(cron):
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
                tasks_to_run = []

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
        """Execute a single task with retries."""
        for attempt in range(task.retries + 1):
            try:
                self.logger.log_task_start(task.name, task.task_id)
                start_time = time.time()

                # Execute task
                if task.func:
                    result = self._execute_function(task.func, task.timeout)
                else:
                    result = self._execute_script(task.script, task.timeout)

                duration = time.time() - start_time

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

                return

            except Exception as e:
                task.increment_fail_count()

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

                    return

                # Retry with backoff
                delay = calculate_retry_delay(attempt, task.retry_delay)
                self.logger.log_task_retry(task.name, task.task_id, attempt + 2, delay)
                time.sleep(delay)

    def _execute_function(self, func: Callable, timeout: Optional[int]) -> Any:
        """Execute a function with timeout."""
        if timeout is None:
            return func()

        # Execute with timeout using threading
        result = [None]
        exception = [None]

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
            raise exception[0]

        return result[0]

    def _execute_script(self, script: str, timeout: Optional[int]) -> Any:
        """Execute a script with timeout."""
        try:
            result = subprocess.run(  # nosec B603 - Controlled execution of user-specified Python scripts with timeout
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

    def _setup_task_notifications(self, task: Task) -> None:
        """Set up notifications for a task."""
        channels = [task.notify] if isinstance(task.notify, str) else task.notify

        for channel in channels:
            if channel == "desktop":
                self.notification_manager.setup_desktop()
            elif channel == "email":
                if task.email_config:
                    self.notification_manager.setup_email(task.email_config)
                else:
                    self.logger.warning(
                        f"Email notification requested but no config provided for task '{task.name}'"
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

            self.os_adapter.create_scheduled_task(
                task_name=task.name,
                script_path=task.script,
                cron_expr=cron_expr,
                python_executable=sys.executable,
            )
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
    global _global_scheduler

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
