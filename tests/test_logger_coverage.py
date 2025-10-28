"""
Additional tests for logger module to improve coverage.

Covers:
- debug() method
- critical() method
- exception() method
- get_log_file_path() method
- get_recent_logs() with file errors
- clear_logs() with file errors
"""

import os

from autocron.logging.logger import AutoCronLogger


class TestLoggerAdditionalCoverage:
    """Additional tests for logger coverage"""

    def test_debug_logging(self, tmp_path):
        """Test debug level logging"""
        log_file = tmp_path / "test_debug.log"
        logger = AutoCronLogger(
            name="test_debug",
            log_path=str(log_file),
            log_level="DEBUG",
            console_output=False,
        )

        logger.debug("Debug message")

        # Verify debug message in log file
        with open(log_file, "r") as f:
            self._extracted_from_test_exception_with_kwargs_15(f, "Debug message", "DEBUG")

    def test_critical_logging(self, tmp_path):
        """Test critical level logging"""
        log_file = tmp_path / "test_critical.log"
        logger = AutoCronLogger(
            name="test_critical",
            log_path=str(log_file),
            log_level="INFO",
            console_output=False,
        )

        logger.critical("Critical error occurred")

        # Verify critical message in log file
        with open(log_file, "r") as f:
            self._extracted_from_test_exception_with_kwargs_15(
                f, "Critical error occurred", "CRITICAL"
            )

    def test_exception_logging(self, tmp_path):
        """Test exception logging with traceback"""
        log_file = tmp_path / "test_exception.log"
        logger = AutoCronLogger(
            name="test_exception",
            log_path=str(log_file),
            log_level="INFO",
            console_output=False,
        )

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception occurred")

        # Verify exception and traceback in log file
        with open(log_file, "r") as f:
            self._extracted_from_test_exception_with_kwargs_15(
                f, "Exception occurred", "ValueError"
            )

    def test_get_log_file_path(self, tmp_path):
        """Test getting log file path"""
        log_file = tmp_path / "test_path.log"
        logger = AutoCronLogger(
            name="test_path",
            log_path=str(log_file),
            console_output=False,
        )

        path = logger.get_log_file_path()
        assert path == str(log_file)
        assert os.path.exists(path)

    def test_get_recent_logs_file_error(self, tmp_path):
        """Test get_recent_logs when file read fails"""
        log_file = tmp_path / "test_read_error.log"
        logger = AutoCronLogger(
            name="test_read_error",
            log_path=str(log_file),
            console_output=False,
        )

        # Close handlers to release file lock on Windows
        for handler in logger.logger.handlers[:]:
            handler.close()
            logger.logger.removeHandler(handler)

        # Delete the log file to cause read error
        os.remove(log_file)

        # Should return empty list and log error
        result = logger.get_recent_logs()
        assert result == []

    def test_get_recent_logs_with_lines_limit(self, tmp_path):
        """Test get_recent_logs with line limit"""
        log_file = tmp_path / "test_lines.log"
        logger = AutoCronLogger(
            name="test_lines",
            log_path=str(log_file),
            console_output=False,
        )

        # Write multiple log entries
        for i in range(50):
            logger.info(f"Log entry {i}")

        # Get only last 10 lines
        recent = logger.get_recent_logs(lines=10)
        assert len(recent) <= 10

    def test_clear_logs_success(self, tmp_path):
        """Test clearing log file"""
        log_file = tmp_path / "test_clear.log"
        logger = AutoCronLogger(
            name="test_clear",
            log_path=str(log_file),
            console_output=False,
        )

        # Write some logs
        logger.info("Message 1")
        logger.info("Message 2")

        # Verify logs exist
        with open(log_file, "r") as f:
            content = f.read()
            assert len(content) > 0

        # Clear logs
        logger.clear_logs()

        # Verify logs cleared
        with open(log_file, "r") as f:
            content = f.read()
            # Should only contain the "Log file cleared" message
            assert "Log file cleared" in content or content == ""

    def test_debug_with_kwargs(self, tmp_path):
        """Test debug logging with extra kwargs"""
        log_file = tmp_path / "test_debug_kwargs.log"
        logger = AutoCronLogger(
            name="test_debug_kwargs",
            log_path=str(log_file),
            log_level="DEBUG",
            console_output=False,
        )

        logger.debug("Debug with context", extra={"user": "test_user"})

        with open(log_file, "r") as f:
            content = f.read()
            assert "Debug with context" in content

    def test_critical_with_kwargs(self, tmp_path):
        """Test critical logging with extra kwargs"""
        log_file = tmp_path / "test_critical_kwargs.log"
        logger = AutoCronLogger(
            name="test_critical_kwargs",
            log_path=str(log_file),
            console_output=False,
        )

        logger.critical("Critical with context", extra={"severity": "high"})

        with open(log_file, "r") as f:
            content = f.read()
            assert "Critical with context" in content

    def test_exception_with_kwargs(self, tmp_path):
        """Test exception logging with extra kwargs"""
        log_file = tmp_path / "test_exception_kwargs.log"
        logger = AutoCronLogger(
            name="test_exception_kwargs",
            log_path=str(log_file),
            console_output=False,
        )

        try:
            1 / 0
        except ZeroDivisionError:
            logger.exception("Math error", extra={"operation": "division"})

        with open(log_file, "r") as f:
            self._extracted_from_test_exception_with_kwargs_15(f, "Math error", "ZeroDivisionError")

    # TODO Rename this here and in `test_debug_logging`, `test_critical_logging`,
    # `test_exception_logging` and `test_exception_with_kwargs`
    def _extracted_from_test_exception_with_kwargs_15(self, f, arg1, arg2):
        content = f.read()
        assert arg1 in content
        assert arg2 in content
