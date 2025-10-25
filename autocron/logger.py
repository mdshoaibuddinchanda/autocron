"""
Logging utilities for AutoCron.

Provides comprehensive logging functionality with rotation, formatting,
and multiple output handlers.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

from autocron.utils import ensure_directory, get_default_log_path


class AutoCronLogger:
    """
    Custom logger for AutoCron with enhanced features.

    Features:
        - File and console logging
        - Automatic log rotation
        - Custom formatting
        - Task-specific logging
        - Performance tracking
    """

    def __init__(
        self,
        name: str = "autocron",
        log_path: Optional[str] = None,
        log_level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True,
    ):
        """
        Initialize logger.

        Args:
            name: Logger name
            log_path: Path to log file (default: platform-specific)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            console_output: Whether to output to console
        """
        self.name = name
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

        # Set up log directory
        if log_path is None:
            log_dir = get_default_log_path()
        else:
            log_dir = os.path.dirname(log_path) or "."

        ensure_directory(log_dir)

        # Create log file path
        if log_path is None:
            self.log_file = os.path.join(log_dir, f"{name}.log")
        else:
            self.log_file = log_path

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)

        # Remove existing handlers
        self.logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        simple_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(simple_formatter)
            self.logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)

    def log_task_start(self, task_name: str, task_id: str) -> None:
        """Log task execution start."""
        self.info(f"Task '{task_name}' (ID: {task_id}) started")

    def log_task_success(self, task_name: str, task_id: str, duration: float) -> None:
        """Log successful task completion."""
        self.info(
            f"Task '{task_name}' (ID: {task_id}) completed successfully "
            f"in {duration:.2f} seconds"
        )

    def log_task_failure(
        self, task_name: str, task_id: str, error: Exception, attempt: int, max_retries: int
    ) -> None:
        """Log task failure."""
        self.error(
            f"Task '{task_name}' (ID: {task_id}) failed "
            f"(attempt {attempt}/{max_retries}): {str(error)}"
        )

    def log_task_retry(self, task_name: str, task_id: str, attempt: int, delay: int) -> None:
        """Log task retry."""
        self.warning(
            f"Task '{task_name}' (ID: {task_id}) will retry in {delay} seconds "
            f"(attempt {attempt})"
        )

    def log_scheduler_start(self) -> None:
        """Log scheduler start."""
        self.info("AutoCron scheduler started")

    def log_scheduler_stop(self) -> None:
        """Log scheduler stop."""
        self.info("AutoCron scheduler stopped")

    def log_task_scheduled(self, task_name: str, schedule: str) -> None:
        """Log task scheduling."""
        self.info(f"Task '{task_name}' scheduled with: {schedule}")

    def log_task_removed(self, task_name: str) -> None:
        """Log task removal."""
        self.info(f"Task '{task_name}' removed from scheduler")

    def get_log_file_path(self) -> str:
        """Get path to log file."""
        return self.log_file

    def get_recent_logs(self, lines: int = 100) -> list:
        """
        Get recent log entries.

        Args:
            lines: Number of lines to retrieve

        Returns:
            List of log lines
        """
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        except Exception as e:
            self.error(f"Failed to read log file: {e}")
            return []

    def clear_logs(self) -> None:
        """Clear all logs."""
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("")
            self.info("Log file cleared")
        except Exception as e:
            self.error(f"Failed to clear log file: {e}")


# Global logger instance
_default_logger: Optional[AutoCronLogger] = None


def get_logger(
    name: str = "autocron", log_path: Optional[str] = None, log_level: str = "INFO", **kwargs
) -> AutoCronLogger:
    """
    Get or create logger instance.

    Args:
        name: Logger name
        log_path: Path to log file
        log_level: Logging level
        **kwargs: Additional logger arguments

    Returns:
        Logger instance
    """
    global _default_logger

    if _default_logger is None:
        _default_logger = AutoCronLogger(
            name=name, log_path=log_path, log_level=log_level, **kwargs
        )

    return _default_logger


def reset_logger() -> None:
    """Reset the global logger instance."""
    global _default_logger
    _default_logger = None
