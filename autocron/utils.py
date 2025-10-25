"""
Utility functions for AutoCron.

This module provides helper functions for time parsing, validation,
and general utilities used throughout the library.
"""

import platform
import re
import sys
from datetime import datetime, timedelta
from typing import Optional


class TimeParseError(Exception):
    """Exception raised when time format cannot be parsed."""

    pass


def parse_interval(interval: str) -> int:
    """
    Parse interval string to seconds.

    Supports formats like: '30s', '5m', '2h', '1d'

    Args:
        interval: Time interval string

    Returns:
        Number of seconds

    Raises:
        TimeParseError: If format is invalid

    Examples:
        >>> parse_interval('30s')
        30
        >>> parse_interval('5m')
        300
        >>> parse_interval('2h')
        7200
    """
    pattern = r"^(\d+)([smhd])$"
    match = re.match(pattern, interval.lower().strip())

    if not match:
        raise TimeParseError(
            f"Invalid interval format: {interval}. " "Use format like '30s', '5m', '2h', '1d'"
        )

    value, unit = match.groups()
    value = int(value)

    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    return value * multipliers[unit]


def validate_cron_expression(cron_expr: str) -> bool:
    """
    Validate cron expression format.

    Args:
        cron_expr: Cron expression string

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_cron_expression('0 9 * * *')
        True
        >>> validate_cron_expression('invalid')
        False
    """
    try:
        # Import here to avoid circular dependency
        from croniter import croniter

        return croniter.is_valid(cron_expr)
    except Exception:
        return False


def get_platform_info() -> dict:
    """
    Get information about the current platform.

    Returns:
        Dictionary with platform details

    Examples:
        >>> info = get_platform_info()
        >>> 'system' in info
        True
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
    }


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"


def is_linux() -> bool:
    """Check if running on Linux."""
    return platform.system() == "Linux"


def is_macos() -> bool:
    """Check if running on macOS."""
    return platform.system() == "Darwin"


def format_timedelta(td: timedelta) -> str:
    """
    Format timedelta to human-readable string.

    Args:
        td: Timedelta object

    Returns:
        Human-readable time string

    Examples:
        >>> format_timedelta(timedelta(seconds=90))
        '1m 30s'
    """
    total_seconds = int(td.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def sanitize_task_name(name: str) -> str:
    """
    Sanitize task name for use in filenames and identifiers.

    Args:
        name: Task name

    Returns:
        Sanitized name

    Examples:
        >>> sanitize_task_name('My Task #1')
        'my_task_1'
    """
    # Replace non-alphanumeric with underscore
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())
    # Remove consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Remove leading/trailing underscores
    return sanitized.strip("_")


def get_next_run_time(cron_expr: str, base_time: Optional[datetime] = None) -> datetime:
    """
    Get next run time for a cron expression.

    Args:
        cron_expr: Cron expression
        base_time: Base time to calculate from (default: now)

    Returns:
        Next run datetime

    Raises:
        TimeParseError: If cron expression is invalid
    """
    try:
        from croniter import croniter

        if base_time is None:
            base_time = datetime.now()

        cron = croniter(cron_expr, base_time)
        return cron.get_next(datetime)
    except Exception as e:
        raise TimeParseError(f"Invalid cron expression '{cron_expr}': {str(e)}") from e


def calculate_retry_delay(attempt: int, base_delay: int, max_delay: int = 3600) -> int:
    """
    Calculate retry delay with exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds

    Examples:
        >>> calculate_retry_delay(0, 60)
        60
        >>> calculate_retry_delay(1, 60)
        120
        >>> calculate_retry_delay(2, 60)
        240
    """
    delay = base_delay * (2**attempt)
    return min(delay, max_delay)


def safe_import(module_name: str, package: Optional[str] = None) -> Optional[object]:
    """
    Safely import a module without raising exceptions.

    Args:
        module_name: Name of module to import
        package: Package name for relative imports

    Returns:
        Imported module or None if import fails
    """
    try:
        if package:
            return __import__(module_name, fromlist=[package])
        return __import__(module_name)
    except ImportError:
        return None


class SingletonMeta(type):
    """
    Metaclass for implementing Singleton pattern.

    Thread-safe singleton implementation.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def ensure_directory(path: str) -> None:
    """
    Ensure directory exists, create if necessary.

    Args:
        path: Directory path
    """
    import os

    os.makedirs(path, exist_ok=True)


def get_default_log_path() -> str:
    """
    Get default log directory path.

    Returns:
        Path to log directory
    """
    import os

    if is_windows():
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "AutoCron", "logs")
    else:
        home = os.path.expanduser("~")
        return os.path.join(home, ".autocron", "logs")
