"""
AutoCron Interface Module.

Contains user-facing interfaces: CLI, dashboard, and notification systems.
These modules handle interaction with users and external systems.
"""

# Import selectively to avoid circular imports
from .notifications import (
    DesktopNotifier,
    EmailNotifier,
    NotificationError,
    NotificationManager,
    Notifier,
)

__all__ = [
    # Notifications
    "Notifier",
    "DesktopNotifier",
    "EmailNotifier",
    "NotificationManager",
    "NotificationError",
]
