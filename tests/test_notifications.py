"""Tests for notification functionality."""

import pytest

from autocron.interface.notifications import (
 EmailNotifier,
 NotificationError,
 NotificationManager,
 get_notification_manager,
 reset_notification_manager,
)


class TestEmailNotifier:
 """Test EmailNotifier class."""

 def test_create_with_valid_config(self):
 """Test creating notifier with valid config."""
 config = {
 "smtp_server": "smtp.example.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "to_email": "recipient@example.com",
 "password": "password123",
 }

 notifier = EmailNotifier(config)

 assert notifier.smtp_server == "smtp.example.com"
 assert notifier.smtp_port == 587
 assert notifier.from_email == "sender@example.com"
 assert notifier.to_email == "recipient@example.com"

 def test_create_with_missing_config(self):
 """Test creating notifier with missing config."""
 config = {"smtp_server": "smtp.example.com", "smtp_port": 587}

 with pytest.raises(NotificationError, match="missing required keys"):
 EmailNotifier(config)

 def test_default_use_tls(self):
 """Test default use_tls setting."""
 config = {
 "smtp_server": "smtp.example.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "to_email": "recipient@example.com",
 "password": "password123",
 }

 notifier = EmailNotifier(config)

 assert notifier.use_tls is True


class TestNotificationManager:
 """Test NotificationManager class."""

 def test_create_manager(self):
 """Test creating notification manager."""
 manager = NotificationManager()

 assert manager is not None
 assert len(manager.notifiers) == 0

 def test_add_notifier(self):
 """Test adding notifier."""
 manager = NotificationManager()

 config = {
 "smtp_server": "smtp.example.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "to_email": "recipient@example.com",
 "password": "password123",
 }

 notifier = EmailNotifier(config)
 manager.add_notifier("email", notifier)

 assert "email" in manager.notifiers
 assert manager.notifiers["email"] == notifier

 def test_setup_email(self):
 """Test setting up email notifications."""
 manager = NotificationManager()

 config = {
 "smtp_server": "smtp.example.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "to_email": "recipient@example.com",
 "password": "password123",
 }

 manager.setup_email(config)

 assert "email" in manager.notifiers

 def test_notify_nonexistent_channel(self):
 """Test notifying nonexistent channel."""
 manager = NotificationManager()

 results = manager.notify("Test", "Message", channels=["nonexistent"])

 assert results["nonexistent"] is False


class TestGetNotificationManager:
 """Test get_notification_manager function."""

 def teardown_method(self):
 """Reset manager after each test."""
 reset_notification_manager()

 def test_get_default_manager(self):
 """Test getting default manager."""
 manager = get_notification_manager()

 assert manager is not None

 def test_get_manager_singleton(self):
 """Test manager singleton behavior."""
 manager1 = get_notification_manager()
 manager2 = get_notification_manager()

 assert manager1 is manager2

 def test_reset_manager(self):
 """Test resetting manager."""
 manager1 = get_notification_manager()
 reset_notification_manager()
 manager2 = get_notification_manager()

 assert manager1 is not manager2


class TestNotificationManagerAdvanced:
 """Test advanced notification manager functionality."""

 def test_setup_desktop_notifier(self):
 """Test setting up desktop notifier."""
 manager = NotificationManager()
 manager.setup_desktop()

 assert "desktop" in manager.notifiers

 def test_notify_task_success(self):
 """Test task success notification."""
 manager = NotificationManager()

 # Should not raise error even without notifiers
 manager.notify_task_success("test_task", 5.5, channels=["desktop"])

 def test_notify_task_failure(self):
 """Test task failure notification."""
 manager = NotificationManager()

 # Should not raise error even without notifiers
 manager.notify_task_failure("test_task", "Error message", 1, 3, channels=["desktop"])

 def test_add_custom_notifier(self):
 """Test adding custom notifier."""
 manager = NotificationManager()

 # Mock notifier
 class MockNotifier:
 def send(self, title, message):
 return True

 manager.add_notifier("custom", MockNotifier())

 assert "custom" in manager.notifiers
 results = manager.notify("Test", "Message", channels=["custom"])
 assert results["custom"] is True
