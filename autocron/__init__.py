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

# Optional dashboard imports
try:
    from autocron.dashboard import Dashboard, TaskAnalytics, live_monitor, show_dashboard, show_task
    _dashboard_available = True
except ImportError:
    _dashboard_available = False
    Dashboard = None
    TaskAnalytics = None
    live_monitor = None
    show_dashboard = None
    show_task = None

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
