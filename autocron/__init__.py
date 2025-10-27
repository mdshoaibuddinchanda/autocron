"""
AutoCron - Automate scripts with zero setup.

A cross-platform Python library for scheduling tasks with minimal configuration.
"""

from typing import TYPE_CHECKING

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

# Optional dashboard imports
try:
    from autocron.dashboard import Dashboard, TaskAnalytics, live_monitor, show_dashboard, show_task

    _dashboard_available = True
except ImportError:
    _dashboard_available = False
    if TYPE_CHECKING:
        from autocron.dashboard import (
            Dashboard,
            TaskAnalytics,
            live_monitor,
            show_dashboard,
            show_task,
        )
    else:
        Dashboard = None  # type: ignore
        TaskAnalytics = None  # type: ignore
        live_monitor = None  # type: ignore
        show_dashboard = None  # type: ignore
        show_task = None  # type: ignore

__all__ = [
    "AutoCron",
    "Dashboard",
    "SchedulingError",
    "Task",
    "TaskAnalytics",
    "TaskExecutionError",
    "__version__",
    "get_global_scheduler",
    "live_monitor",
    "reset_global_scheduler",
    "schedule",
    "show_dashboard",
    "show_task",
    "start_scheduler",
]
