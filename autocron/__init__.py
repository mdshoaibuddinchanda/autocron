"""
AutoCron - Automate scripts with zero setup.

A cross-platform Python library for scheduling tasks with minimal configuration.

Note: As of v1.3.0, the internal structure has been reorganized into subpackages:
- autocron.core: Core scheduling logic and utilities
- autocron.interface: CLI, dashboard, and notifications
- autocron.logging: Logging infrastructure
- autocron.config: Configuration management (future)

For backward compatibility, all public APIs remain importable from autocron directly.
"""

from typing import TYPE_CHECKING

# Import from new structure (v1.3.0+)
from autocron.core.scheduler import (
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
    from autocron.interface.dashboard import (
        Dashboard,
        TaskAnalytics,
        live_monitor,
        show_dashboard,
        show_task,
    )

    _dashboard_available = True
except ImportError:
    _dashboard_available = False
    if TYPE_CHECKING:
        from autocron.interface.dashboard import (
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
