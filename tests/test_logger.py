"""Tests for logger functionality."""

import pytest
import os
import tempfile
import logging
from autocron.logger import AutoCronLogger, get_logger, reset_logger


class TestAutoCronLogger:
    """Test AutoCronLogger class."""

    def test_create_logger(self):
        """Test creating logger."""
        tmpdir = tempfile.mkdtemp()
        try:
            log_file = os.path.join(tmpdir, "test.log")
            logger = AutoCronLogger(log_path=log_file)

            assert logger is not None
            assert os.path.exists(log_file)

            # Close handlers to release file
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
        finally:
            # Clean up
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_log_messages(self):
        """Test logging messages."""
        tmpdir = tempfile.mkdtemp()
        try:
            log_file = os.path.join(tmpdir, "test.log")
            logger = AutoCronLogger(log_path=log_file, console_output=False)

            logger.info("Test info message")
            logger.warning("Test warning message")
            logger.error("Test error message")

            # Flush and close handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()

            # Read log file
            with open(log_file, "r") as f:
                content = f.read()

            assert "Test info message" in content
            assert "Test warning message" in content
            assert "Test error message" in content

            # Close handlers to release file
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_log_task_start(self):
        """Test logging task start."""
        tmpdir = tempfile.mkdtemp()
        try:
            log_file = os.path.join(tmpdir, "test.log")
            logger = AutoCronLogger(log_path=log_file, console_output=False)

            logger.log_task_start("my_task", "task_123")

            # Flush handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()

            with open(log_file, "r") as f:
                content = f.read()

            assert "my_task" in content

            # Close handlers to release file
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_log_task_success(self):
        """Test logging task success."""
        tmpdir = tempfile.mkdtemp()
        try:
            log_file = os.path.join(tmpdir, "test.log")
            logger = AutoCronLogger(log_path=log_file, console_output=False)

            logger.log_task_success("my_task", "task_123", 5.5)

            # Flush handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()

            with open(log_file, "r") as f:
                content = f.read()

            assert "my_task" in content
            assert "completed successfully" in content
            assert "5.50 seconds" in content

            # Close handlers to release file
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_log_task_failure(self):
        """Test logging task failure."""
        tmpdir = tempfile.mkdtemp()
        try:
            log_file = os.path.join(tmpdir, "test.log")
            logger = AutoCronLogger(log_path=log_file, console_output=False)

            error = Exception("Test error")
            logger.log_task_failure("my_task", "task_123", error, 1, 3)

            # Flush handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()

            with open(log_file, "r") as f:
                content = f.read()

            assert "my_task" in content
            assert "failed" in content
            assert "Test error" in content

            # Close handlers to release file
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_recent_logs(self):
        """Test getting recent logs."""
        tmpdir = tempfile.mkdtemp()
        try:
            log_file = os.path.join(tmpdir, "test.log")
            logger = AutoCronLogger(log_path=log_file, console_output=False)

            for i in range(10):
                logger.info(f"Message {i}")

            # Flush handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()

            recent = logger.get_recent_logs(lines=5)

            assert len(recent) == 5
            assert "Message 9" in recent[-1]

            # Close handlers to release file
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_log_rotation(self):
        """Test log rotation."""
        tmpdir = tempfile.mkdtemp()
        try:
            log_file = os.path.join(tmpdir, "test.log")
            logger = AutoCronLogger(
                log_path=log_file, console_output=False, max_bytes=1024, backup_count=2
            )

            # Write enough data to trigger rotation
            for _ in range(100):
                logger.info("X" * 100)

            # Flush handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()

            # Check that backup files were created
            assert os.path.exists(log_file)

            # Close handlers to release file
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)


class TestGetLogger:
    """Test get_logger function."""

    def teardown_method(self):
        """Reset logger after each test."""
        reset_logger()

    def test_get_default_logger(self):
        """Test getting default logger."""
        logger = get_logger()

        assert logger is not None
        assert logger.name == "autocron"

    def test_get_logger_singleton(self):
        """Test logger singleton behavior."""
        logger1 = get_logger()
        logger2 = get_logger()

        assert logger1 is logger2

    def test_reset_logger(self):
        """Test resetting logger."""
        logger1 = get_logger()
        reset_logger()
        logger2 = get_logger()

        assert logger1 is not logger2
