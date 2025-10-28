"""
AutoCron Core Module.

Contains the core scheduling logic, OS adapters, and utility functions.
This module is the foundation of AutoCron's task scheduling capabilities.
"""

# Lazy imports to avoid circular dependencies
__all__ = [
    # Scheduler classes
    "AutoCron",
    "Task",
    "TaskExecutionError",
    "SchedulingError",
    # OS Adapters
    "OSAdapter",
    "WindowsAdapter",
    "UnixAdapter",
    "get_os_adapter",
    # Utilities
    "validate_cron_expression",
    "get_next_run_time",
    "calculate_retry_delay",
    "is_windows",
    "is_macos",
    "is_linux",
    "safe_import",
    "SingletonMeta",
    "ensure_directory",
    "get_default_log_path",
]
