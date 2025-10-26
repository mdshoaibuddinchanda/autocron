"""
AutoCron - Automate scripts with zero setup.

A cross-platform Python library for scheduling tasks with minimal configuration.
"""

from autocron.scheduler import (
    AutoCron,
    SchedulingError,
    Task,
    TaskExecutionError,
    get_global_scheduler,
    reset_global_scheduler,
    schedule,
    start_scheduler,
)
from autocron.version import __version__

__all__ = [
    "AutoCron",
    "SchedulingError",
    "Task",
    "TaskExecutionError",
    "__version__",
    "get_global_scheduler",
    "reset_global_scheduler",
    "schedule",
    "start_scheduler",
]
