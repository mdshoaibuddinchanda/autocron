"""
AutoCron Core Module.

Contains the core scheduling logic, OS adapters, and utility functions.
This module is the foundation of AutoCron's task scheduling capabilities.
"""

from autocron.core.os_adapters import (
    OSAdapter,
    OSAdapterError,
    UnixAdapter,
    WindowsAdapter,
    get_os_adapter,
)
from autocron.core.scheduler import AutoCron, SchedulingError, Task, TaskExecutionError
from autocron.core.utils import (
    SingletonMeta,
    TimeParseError,
    calculate_retry_delay,
    ensure_directory,
    format_timedelta,
    get_default_log_path,
    get_next_run_time,
    get_platform_info,
    is_linux,
    is_macos,
    is_windows,
    parse_interval,
    safe_import,
    sanitize_task_name,
    validate_cron_expression,
)

__all__ = [
    # Scheduler classes
    "AutoCron",
    "Task",
    "TaskExecutionError",
    "SchedulingError",
    "OSAdapterError",
    # OS Adapters
    "OSAdapter",
    "WindowsAdapter",
    "UnixAdapter",
    "get_os_adapter",
    # Utilities
    "TimeParseError",
    "parse_interval",
    "validate_cron_expression",
    "get_next_run_time",
    "calculate_retry_delay",
    "format_timedelta",
    "sanitize_task_name",
    "get_platform_info",
    "is_windows",
    "is_macos",
    "is_linux",
    "safe_import",
    "SingletonMeta",
    "ensure_directory",
    "get_default_log_path",
]
