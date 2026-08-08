"""
Utility functions for AutoCron.

This module provides helper functions for time parsing, validation,
and general utilities used throughout the library.
"""

import platform
import re
import sys
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
from datetime import tzinfo
from pathlib import Path
from typing import Any, Dict, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
    if not isinstance(interval, str):
        raise TimeParseError("Interval must be a string such as '30s', '5m', '2h', or '1d'")

    pattern = r"^(\d+)([smhd])$"
    match = re.match(pattern, interval.lower().strip())

    if not match:
        raise TimeParseError(
            f"Invalid interval format: {interval}. " "Use format like '30s', '5m', '2h', '1d'"
        )

    value, unit = match.groups()
    value = int(value)

    if value <= 0:
        raise TimeParseError("Interval must be greater than zero")

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

        return (
            isinstance(cron_expr, str) and bool(cron_expr.strip()) and croniter.is_valid(cron_expr)
        )
    except Exception:
        return False


TimezoneLike = Optional[Union[str, tzinfo]]


def resolve_timezone(value: TimezoneLike = None) -> tzinfo:
    """Resolve an IANA timezone name or timezone object.

    ``None`` and ``"local"`` select the operating-system local timezone. Named
    zones are loaded through :mod:`zoneinfo`, so their daylight-saving rules are
    retained. A :class:`TimeParseError` is raised for an unknown or invalid zone.
    """
    if value is None or (isinstance(value, str) and value.strip().lower() == "local"):
        return datetime.now().astimezone().tzinfo or datetime_timezone.utc
    if isinstance(value, tzinfo):
        return value
    if not isinstance(value, str) or not value.strip():
        raise TimeParseError("Timezone must be an IANA name, tzinfo instance, or 'local'")
    try:
        return ZoneInfo(value.strip())
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TimeParseError(f"Unknown timezone: {value}") from exc


def timezone_name(value: TimezoneLike = None) -> str:
    """Return a stable name suitable for persistence."""
    if value is None or (isinstance(value, str) and value.strip().lower() == "local"):
        return "local"
    zone = resolve_timezone(value)
    # Windows exposes the local zone as a tzinfo object whose string
    # representation (for example, ``India Standard Time``) is a Windows
    # registry label rather than an IANA name. Persisting that label makes a
    # task impossible to reload on another platform, so use the portable
    # local sentinel for unnamed local zones.
    key = getattr(zone, "key", None)
    if key:
        return key
    if value is None or str(zone) == str(datetime.now().astimezone().tzinfo):
        return "local"
    return str(zone)


def _valid_wall_times(wall_time: datetime, zone: tzinfo) -> list[datetime]:
    """Return real instants represented by a naive local wall time.

    A wall time in a spring-forward gap returns no candidates. An ambiguous
    fall-back wall time returns both folds in chronological order.
    """
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = wall_time.replace(tzinfo=zone, fold=fold)
        normalized = candidate.astimezone(datetime_timezone.utc).astimezone(zone)
        if normalized.replace(tzinfo=None) != wall_time or normalized.fold != fold:
            continue
        if all(
            existing.astimezone(datetime_timezone.utc)
            != candidate.astimezone(datetime_timezone.utc)
            for existing in candidates
        ):
            candidates.append(candidate)
    return sorted(candidates, key=lambda item: item.astimezone(datetime_timezone.utc))


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


def get_next_run_time(
    cron_expr: str,
    base_time: Optional[datetime] = None,
    timezone: TimezoneLike = None,
) -> datetime:
    """
    Get next run time for a cron expression.

    Args:
        cron_expr: Cron expression
        base_time: Base time to calculate from (default: now)
        timezone: Optional IANA timezone name or tzinfo. When supplied (or when
            ``base_time`` is aware), the result is timezone-aware and DST-safe.

    Returns:
        Next run datetime

    Raises:
        TimeParseError: If cron expression is invalid
    """
    try:
        from croniter import croniter

        if not validate_cron_expression(cron_expr):
            raise ValueError("invalid cron expression")

        use_aware_time = timezone is not None or (
            base_time is not None and base_time.tzinfo is not None
        )
        if not use_aware_time:
            naive_base = base_time or datetime.now()
            return croniter(cron_expr, naive_base).get_next(datetime)

        zone = resolve_timezone(timezone or (base_time.tzinfo if base_time else None))
        if base_time is None:
            local_base = datetime.now(zone)
        elif base_time.tzinfo is None:
            candidates = _valid_wall_times(base_time, zone)
            if not candidates:
                raise TimeParseError(
                    f"Base time {base_time.isoformat()} does not exist in "
                    f"timezone {timezone_name(zone)}"
                )
            local_base = candidates[0]
        else:
            local_base = base_time.astimezone(zone)

        base_utc = local_base.astimezone(datetime_timezone.utc)
        wall_base = local_base.replace(tzinfo=None)

        # croniter advances wall-clock values and does not consistently emit the
        # second fold of an ambiguous time. Check that fold before moving on.
        if croniter.match(cron_expr, wall_base):
            same_wall_candidates = [
                candidate
                for candidate in _valid_wall_times(wall_base, zone)
                if candidate.astimezone(datetime_timezone.utc) > base_utc
            ]
            if same_wall_candidates:
                return same_wall_candidates[0]

        cron = croniter(cron_expr, wall_base)
        # Invalid local times are rare (normally one transition hour), but keep
        # a hard bound so a pathological tzinfo cannot make this loop infinite.
        for _ in range(100_000):
            next_wall = cron.get_next(datetime).replace(tzinfo=None)
            candidates = [
                candidate
                for candidate in _valid_wall_times(next_wall, zone)
                if candidate.astimezone(datetime_timezone.utc) > base_utc
            ]
            if candidates:
                return candidates[0]
        raise TimeParseError("Unable to find a real future wall time for cron expression")
    except Exception as e:
        if isinstance(e, TimeParseError):
            raise
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

    _instances: Dict[type, Any] = {}

    def __call__(cls, *args, **kwargs):  # type: ignore
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


def get_autocron_home() -> Path:
    """Return the configurable directory used for AutoCron state.

    ``AUTOCRON_HOME`` is intentionally checked first so applications and tests
    can isolate databases, logs, analytics, and legacy task files without
    changing the process' complete home-directory semantics.
    """
    import os

    configured = os.environ.get("AUTOCRON_HOME")
    if configured:
        home = Path(configured).expanduser()
    elif is_windows():
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        home = Path(base) / "AutoCron"
    else:
        home = Path.home() / ".autocron"
    home.mkdir(parents=True, exist_ok=True)
    return home


def get_default_log_path() -> str:
    """
    Get default log directory path.

    Returns:
        Path to log directory
    """
    return str(get_autocron_home() / "logs")
