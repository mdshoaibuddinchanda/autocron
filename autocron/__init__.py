"""
AutoCron - Automate scripts with zero setup.

A cross-platform Python library for scheduling tasks with minimal configuration.
"""

from autocron.scheduler import (
    AutoCron,
    schedule,
    start_scheduler,
    get_global_scheduler,
    reset_global_scheduler,
    Task,
    TaskExecutionError,
    SchedulingError,
)
from autocron.version import __version__

__all__ = [
    "AutoCron",
    "schedule",
    "start_scheduler",
    "get_global_scheduler",
    "reset_global_scheduler",
    "Task",
    "TaskExecutionError",
    "SchedulingError",
    "__version__",
]
