"""Tests for utility functions."""

from datetime import datetime, timedelta

import pytest

from autocron.core.utils import (
    TimeParseError,
    calculate_retry_delay,
    format_timedelta,
    get_next_run_time,
    get_platform_info,
    is_linux,
    is_macos,
    is_windows,
    parse_interval,
    sanitize_task_name,
    validate_cron_expression,
)


class TestParseInterval:
    """Test interval parsing."""

    def test_parse_seconds(self):
        """Test parsing seconds."""
        assert parse_interval("30s") == 30
        assert parse_interval("1s") == 1
        assert parse_interval("60s") == 60

    def test_parse_minutes(self):
        """Test parsing minutes."""
        assert parse_interval("5m") == 300
        assert parse_interval("1m") == 60
        assert parse_interval("30m") == 1800

    def test_parse_hours(self):
        """Test parsing hours."""
        assert parse_interval("1h") == 3600
        assert parse_interval("2h") == 7200
        assert parse_interval("24h") == 86400

    def test_parse_days(self):
        """Test parsing days."""
        assert parse_interval("1d") == 86400
        assert parse_interval("7d") == 604800

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert parse_interval("5M") == 300
        assert parse_interval("1H") == 3600
        assert parse_interval("1D") == 86400

    def test_invalid_format(self):
        """Test invalid format."""
        with pytest.raises(TimeParseError):
            parse_interval("invalid")

        with pytest.raises(TimeParseError):
            parse_interval("5")

        with pytest.raises(TimeParseError):
            parse_interval("m5")


class TestValidateCronExpression:
    """Test cron expression validation."""

    def test_valid_expressions(self):
        """Test valid cron expressions."""
        assert validate_cron_expression("0 9 * * *")
        assert validate_cron_expression("*/5 * * * *")
        assert validate_cron_expression("0 0 * * 0")
        assert validate_cron_expression("0 12 * * 1-5")

    def test_invalid_expressions(self):
        """Test invalid cron expressions."""
        assert not validate_cron_expression("invalid")
        assert not validate_cron_expression("60 * * * *")
        assert not validate_cron_expression("* * * *")


class TestPlatformInfo:
    """Test platform information."""

    def test_get_platform_info(self):
        """Test getting platform info."""
        info = get_platform_info()

        assert "system" in info
        assert "release" in info
        assert "version" in info
        assert "machine" in info
        assert "processor" in info
        assert "python_version" in info
        assert "python_implementation" in info

    def test_platform_detection(self):
        """Test platform detection functions."""
        # Exactly one should be True
        platforms = [is_windows(), is_linux(), is_macos()]
        assert sum(platforms) == 1


class TestFormatTimedelta:
    """Test timedelta formatting."""

    def test_format_seconds(self):
        """Test formatting seconds."""
        assert format_timedelta(timedelta(seconds=30)) == "30s"
        assert format_timedelta(timedelta(seconds=59)) == "59s"

    def test_format_minutes(self):
        """Test formatting minutes."""
        assert format_timedelta(timedelta(minutes=5)) == "5m"
        assert format_timedelta(timedelta(minutes=5, seconds=30)) == "5m 30s"

    def test_format_hours(self):
        """Test formatting hours."""
        assert format_timedelta(timedelta(hours=2)) == "2h"
        assert format_timedelta(timedelta(hours=2, minutes=30)) == "2h 30m"

    def test_format_days(self):
        """Test formatting days."""
        assert format_timedelta(timedelta(days=1)) == "1d"
        assert format_timedelta(timedelta(days=1, hours=2, minutes=30)) == "1d 2h 30m"

    def test_format_zero(self):
        """Test formatting zero."""
        assert format_timedelta(timedelta(seconds=0)) == "0s"


class TestSanitizeTaskName:
    """Test task name sanitization."""

    def test_basic_sanitization(self):
        """Test basic sanitization."""
        assert sanitize_task_name("my_task") == "my_task"
        assert sanitize_task_name("My Task") == "my_task"
        assert sanitize_task_name("My-Task #1") == "my_task_1"

    def test_remove_special_chars(self):
        """Test special character removal."""
        assert sanitize_task_name("task!@#$%") == "task"
        assert sanitize_task_name("task (v1.0)") == "task_v1_0"

    def test_consecutive_underscores(self):
        """Test consecutive underscore removal."""
        assert sanitize_task_name("my___task") == "my_task"
        assert sanitize_task_name("__my_task__") == "my_task"


class TestGetNextRunTime:
    """Test next run time calculation."""

    def test_simple_cron(self):
        """Test simple cron expression."""
        base_time = datetime(2025, 1, 1, 0, 0, 0)
        next_time = get_next_run_time("0 9 * * *", base_time)

        assert next_time.hour == 9
        assert next_time.minute == 0

    def test_invalid_cron(self):
        """Test invalid cron expression."""
        with pytest.raises(TimeParseError):
            get_next_run_time("invalid", datetime.now())


class TestCalculateRetryDelay:
    """Test retry delay calculation."""

    def test_exponential_backoff(self):
        """Test exponential backoff."""
        assert calculate_retry_delay(0, 60) == 60
        assert calculate_retry_delay(1, 60) == 120
        assert calculate_retry_delay(2, 60) == 240
        assert calculate_retry_delay(3, 60) == 480

    def test_max_delay(self):
        """Test maximum delay."""
        assert calculate_retry_delay(10, 60, max_delay=300) == 300
        assert calculate_retry_delay(20, 60, max_delay=1000) == 1000
