"""
AutoCron - Automate scripts with zero setup.

A cross-platform Python library for scheduling tasks with minimal configuration.
"""

from autocron.scheduler import AutoCron, schedule
from autocron.version import __version__

__all__ = ["AutoCron", "schedule", "__version__"]
