"""
Notification system for AutoCron.

Supports desktop notifications and email alerts for task events.
"""

import contextlib
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from autocron.utils import safe_import


class NotificationError(Exception):
    """Exception raised when notification fails."""

    pass


class Notifier(ABC):
    """Abstract base class for notifiers."""

    @abstractmethod
    def send(self, title: str, message: str, **kwargs) -> bool:
        """
        Send notification.

        Args:
            title: Notification title
            message: Notification message
            **kwargs: Additional parameters

        Returns:
            True if successful, False otherwise
        """
        pass


class DesktopNotifier(Notifier):
    """
    Desktop notification handler.

    Uses plyer library for cross-platform desktop notifications.
    """

    def __init__(self):
        """Initialize desktop notifier."""
        self.plyer = safe_import("plyer")
        if self.plyer is None:
            raise NotificationError(
                "Desktop notifications require 'plyer' package. "
                "Install with: pip install autocron[notifications]"
            )

    def send(self, title: str, message: str, **kwargs) -> bool:
        """
        Send desktop notification.

        Args:
            title: Notification title
            message: Notification message
            **kwargs: Additional parameters (app_name, timeout)

        Returns:
            True if successful, False otherwise
        """
        try:
            from plyer import notification

            notification.notify(
                title=title,
                message=message,
                app_name=kwargs.get("app_name", "AutoCron"),
                timeout=kwargs.get("timeout", 10),
            )
            return True
        except Exception as e:
            raise NotificationError(f"Failed to send desktop notification: {e}") from e


class EmailNotifier(Notifier):
    """
    Email notification handler.

    Supports SMTP-based email notifications.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email notifier.

        Args:
            config: Email configuration dictionary with keys:
                - smtp_server: SMTP server address
                - smtp_port: SMTP server port
                - from_email: Sender email address
                - to_email: Recipient email address (or list)
                - password: Email password
                - use_tls: Whether to use TLS (default: True)
        """
        required_keys = ["smtp_server", "smtp_port", "from_email", "to_email", "password"]
        if missing_keys := [key for key in required_keys if key not in config]:
            raise NotificationError(
                f"Email configuration missing required keys: {', '.join(missing_keys)}"
            )

        self.smtp_server = config["smtp_server"]
        self.smtp_port = config["smtp_port"]
        self.from_email = config["from_email"]
        self.to_email = config["to_email"]
        self.password = config["password"]
        self.use_tls = config.get("use_tls", True)

    def send(self, title: str, message: str, **kwargs) -> bool:
        """
        Send email notification.

        Args:
            title: Email subject
            message: Email body
            **kwargs: Additional parameters (html)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = self.from_email
            msg["To"] = (
                self.to_email if isinstance(self.to_email, str) else ", ".join(self.to_email)
            )

            # Add text content
            text_part = MIMEText(message, "plain")
            msg.attach(text_part)

            # Add HTML content if provided
            if "html" in kwargs:
                html_part = MIMEText(kwargs["html"], "html")
                msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.from_email, self.password)

                recipients = [self.to_email] if isinstance(self.to_email, str) else self.to_email
                server.sendmail(self.from_email, recipients, msg.as_string())

            return True
        except Exception as e:
            raise NotificationError(f"Failed to send email notification: {e}") from e


class NotificationManager:
    """
    Manages multiple notification channels.

    Coordinates desktop and email notifications with error handling.
    """

    def __init__(self):
        """Initialize notification manager."""
        self.notifiers: Dict[str, Notifier] = {}

    def add_notifier(self, name: str, notifier: Notifier) -> None:
        """
        Add a notifier.

        Args:
            name: Notifier identifier
            notifier: Notifier instance
        """
        self.notifiers[name] = notifier

    def setup_desktop(self) -> None:
        """Set up desktop notifications."""
        with contextlib.suppress(NotificationError):
            notifier = DesktopNotifier()
            self.add_notifier("desktop", notifier)

    def setup_email(self, config: Dict[str, Any]) -> None:
        """
        Set up email notifications.

        Args:
            config: Email configuration dictionary
        """
        notifier = EmailNotifier(config)
        self.add_notifier("email", notifier)

    def notify(
        self, title: str, message: str, channels: Optional[list] = None, **kwargs
    ) -> Dict[str, bool]:
        """
        Send notification through specified channels.

        Args:
            title: Notification title
            message: Notification message
            channels: List of channel names (None = all channels)
            **kwargs: Additional parameters for notifiers

        Returns:
            Dictionary mapping channel names to success status
        """
        if channels is None:
            channels = list(self.notifiers.keys())

        results = {}
        for channel in channels:
            if channel in self.notifiers:
                try:
                    success = self.notifiers[channel].send(title, message, **kwargs)
                    results[channel] = success
                except Exception as e:
                    results[channel] = False
            else:
                results[channel] = False

        return results

    def notify_task_success(
        self, task_name: str, duration: float, channels: Optional[list] = None
    ) -> Dict[str, bool]:
        """
        Notify task success.

        Args:
            task_name: Name of the task
            duration: Execution duration in seconds
            channels: Notification channels

        Returns:
            Notification results
        """
        title = f"AutoCron: Task '{task_name}' Completed"
        message = f"Task '{task_name}' completed successfully in {duration:.2f} seconds."

        return self.notify(title, message, channels)

    def notify_task_failure(
        self,
        task_name: str,
        error: str,
        attempt: int,
        max_retries: int,
        channels: Optional[list] = None,
    ) -> Dict[str, bool]:
        """
        Notify task failure.

        Args:
            task_name: Name of the task
            error: Error message
            attempt: Current attempt number
            max_retries: Maximum retry attempts
            channels: Notification channels

        Returns:
            Notification results
        """
        title = f"AutoCron: Task '{task_name}' Failed"
        message = (
            f"Task '{task_name}' failed (attempt {attempt}/{max_retries}).\n\n" f"Error: {error}"
        )

        return self.notify(title, message, channels)

    def notify_scheduler_error(
        self, error: str, channels: Optional[list] = None
    ) -> Dict[str, bool]:
        """
        Notify scheduler error.

        Args:
            error: Error message
            channels: Notification channels

        Returns:
            Notification results
        """
        title = "AutoCron: Scheduler Error"
        message = f"An error occurred in the scheduler:\n\n{error}"

        return self.notify(title, message, channels)


# Global notification manager instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """
    Get or create notification manager instance.

    Returns:
        NotificationManager instance
    """
    global _notification_manager

    if _notification_manager is None:
        _notification_manager = NotificationManager()

    return _notification_manager


def reset_notification_manager() -> None:
    """Reset the global notification manager instance."""
    global _notification_manager
    _notification_manager = None
