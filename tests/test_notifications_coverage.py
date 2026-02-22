"""
Additional tests to improve notifications.py coverage to 85%+

Focus areas:
1. Email notification sending
2. Desktop notification edge cases
3. Notification manager error handling
4. Multi-channel notifications
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from autocron.interface.notifications import (
 DesktopNotifier,
 EmailNotifier,
 NotificationError,
 NotificationManager,
)


class TestDesktopNotifier:
 """Test desktop notifications"""

 @patch("autocron.interface.notifications.safe_import")
 @patch("plyer.notification")
 def test_desktop_notifier_send_success(self, mock_notification, mock_safe_import):
 """Test successful desktop notification"""
 # Mock safe_import to return a mock plyer object
 mock_plyer = Mock()
 mock_safe_import.return_value = mock_plyer

 notifier = DesktopNotifier()
 result = notifier.send("Test Title", "Test message")

 assert result is True
 mock_notification.notify.assert_called_once_with(
 title="Test Title",
 message="Test message",
 app_name="AutoCron",
 timeout=10,
 )

 @patch("autocron.interface.notifications.safe_import")
 @patch("plyer.notification")
 def test_desktop_notifier_send_failure(self, mock_notification, mock_safe_import):
 """Test desktop notification failure"""
 mock_plyer = Mock()
 mock_safe_import.return_value = mock_plyer
 mock_notification.notify.side_effect = Exception("Notification failed")

 notifier = DesktopNotifier()

 # Should raise NotificationError
 with pytest.raises(NotificationError):
 notifier.send("Title", "Message")

 @patch("autocron.interface.notifications.safe_import")
 def test_desktop_notifier_without_plyer(self, mock_safe_import):
 """Test desktop notifier when plyer not available"""
 mock_safe_import.return_value = None

 # Should raise NotificationError during initialization
 with pytest.raises(NotificationError, match="plyer"):
 DesktopNotifier()


class TestEmailNotifier:
 """Test email notifications"""

 def test_email_notifier_initialization(self):
 """Test email notifier initialization"""
 config = {
 "smtp_server": "smtp.gmail.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "password": "testpass",
 "to_email": "recipient@example.com",
 }

 notifier = EmailNotifier(config)
 assert notifier.smtp_server == "smtp.gmail.com"
 assert notifier.smtp_port == 587
 assert notifier.from_email == "sender@example.com"
 assert notifier.to_email == "recipient@example.com"

 @patch("smtplib.SMTP")
 def test_email_notifier_send_success(self, mock_smtp):
 """Test successful email sending"""
 config = {
 "smtp_server": "smtp.gmail.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "password": "testpass",
 "to_email": "recipient@example.com",
 }

 mock_server = MagicMock()
 mock_smtp.return_value.__enter__.return_value = mock_server

 notifier = EmailNotifier(config)
 result = notifier.send("Test Subject", "Test body")

 assert result is True
 mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
 mock_server.starttls.assert_called_once()
 mock_server.login.assert_called_once_with("sender@example.com", "testpass")
 mock_server.sendmail.assert_called_once()

 @patch("smtplib.SMTP")
 def test_email_notifier_send_failure(self, mock_smtp):
 """Test email sending failure"""
 config = {
 "smtp_server": "smtp.gmail.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "password": "testpass",
 "to_email": "recipient@example.com",
 }

 mock_smtp.side_effect = Exception("SMTP connection failed")

 notifier = EmailNotifier(config)

 # Should raise NotificationError
 with pytest.raises(NotificationError):
 notifier.send("Subject", "Body")

 @patch("smtplib.SMTP")
 def test_email_notifier_authentication_failure(self, mock_smtp):
 """Test email authentication failure"""
 config = {
 "smtp_server": "smtp.gmail.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "password": "wrongpass",
 "to_email": "recipient@example.com",
 }

 mock_server = MagicMock()
 mock_server.login.side_effect = Exception("Authentication failed")
 mock_smtp.return_value.__enter__.return_value = mock_server

 notifier = EmailNotifier(config)

 # Should raise NotificationError
 with pytest.raises(NotificationError):
 notifier.send("Subject", "Body")

 @patch("smtplib.SMTP")
 def test_email_notifier_multiple_recipients(self, mock_smtp):
 """Test sending email to multiple recipients"""
 config = {
 "smtp_server": "smtp.gmail.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "password": "testpass",
 "to_email": [
 "recipient1@example.com",
 "recipient2@example.com",
 "recipient3@example.com",
 ],
 }

 mock_server = MagicMock()
 mock_smtp.return_value.__enter__.return_value = mock_server

 notifier = EmailNotifier(config)
 result = notifier.send("Multi-recipient Test", "Body")

 # Verify email sent
 assert result is True
 mock_server.sendmail.assert_called_once()


class TestNotificationManager:
 """Test notification manager"""

 def test_notification_manager_add_notifier(self):
 """Test adding notifiers to manager"""
 manager = NotificationManager()
 notifier = Mock()

 manager.add_notifier("test", notifier)
 assert "test" in manager.notifiers

 def test_notification_manager_setup_desktop(self):
 """Test setting up desktop notifications"""
 manager = NotificationManager()
 manager.setup_desktop()

 assert "desktop" in manager.notifiers
 assert isinstance(manager.notifiers["desktop"], DesktopNotifier)

 def test_notification_manager_setup_email(self):
 """Test setting up email notifications"""
 config = {
 "smtp_server": "smtp.gmail.com",
 "smtp_port": 587,
 "from_email": "sender@example.com",
 "password": "testpass",
 "to_email": "recipient@example.com",
 }

 manager = NotificationManager()
 manager.setup_email(config)

 assert "email" in manager.notifiers
 assert isinstance(manager.notifiers["email"], EmailNotifier)

 def test_notification_manager_notify_single_channel(self):
 """Test notifying through single channel"""
 manager = NotificationManager()
 mock_notifier = Mock()
 manager.add_notifier("test", mock_notifier)

 manager.notify("Test Title", "Test message", channels=["test"])

 mock_notifier.send.assert_called_once_with("Test Title", "Test message")

 def test_notification_manager_notify_multiple_channels(self):
 """Test notifying through multiple channels"""
 manager = NotificationManager()

 mock_notifier1 = Mock()
 mock_notifier2 = Mock()

 manager.add_notifier("channel1", mock_notifier1)
 manager.add_notifier("channel2", mock_notifier2)

 manager.notify("Title", "Message", channels=["channel1", "channel2"])

 mock_notifier1.send.assert_called_once_with("Title", "Message")
 mock_notifier2.send.assert_called_once_with("Title", "Message")

 def test_notification_manager_notify_unknown_channel(self):
 """Test notifying through unknown channel"""
 manager = NotificationManager()

 # Should not raise, just log warning
 manager.notify("Title", "Message", channels=["unknown"])

 def test_notification_manager_notify_with_exception(self):
 """Test notification when notifier raises exception"""
 manager = NotificationManager()

 mock_notifier = Mock()
 mock_notifier.send.side_effect = Exception("Send failed")
 manager.add_notifier("faulty", mock_notifier)

 # Should not raise, exception caught
 manager.notify("Title", "Message", channels=["faulty"])

 def test_notification_manager_task_success(self):
 """Test task success notification"""
 manager = NotificationManager()
 mock_notifier = Mock()
 manager.add_notifier("test", mock_notifier)

 manager.notify_task_success("test_task", 1.5, channels=["test"])

 # Verify notification was sent with correct format
 mock_notifier.send.assert_called_once()
 args = mock_notifier.send.call_args[0]
 assert "test_task" in args[1]
 assert "1.5" in args[1] or "1.50" in args[1]

 def test_notification_manager_task_failure(self):
 """Test task failure notification"""
 manager = NotificationManager()
 mock_notifier = Mock()
 manager.add_notifier("test", mock_notifier)

 manager.notify_task_failure(
 "test_task",
 "Test error",
 attempt=2,
 max_retries=3,
 channels=["test"],
 )

 # Verify notification sent with error details
 mock_notifier.send.assert_called_once()
 args = mock_notifier.send.call_args[0]
 assert "test_task" in args[1]
 assert "Test error" in args[1]
 assert "2" in args[1]

 def test_notification_manager_scheduler_error(self):
 """Test scheduler error notification"""
 manager = NotificationManager()
 mock_notifier = Mock()
 manager.add_notifier("test", mock_notifier)

 manager.notify_scheduler_error("Critical error", channels=["test"])

 mock_notifier.send.assert_called_once()
 args = mock_notifier.send.call_args[0]
 assert "Critical error" in args[1]


class TestNotificationIntegration:
 """Test notification integration scenarios"""

 def test_notification_with_no_channels(self):
 """Test notification when no channels specified"""
 manager = NotificationManager()
 mock_notifier = Mock()
 mock_notifier.send.return_value = True
 manager.add_notifier("test", mock_notifier)

 # channels=None means use all available channels
 result = manager.notify("Title", "Message", channels=None)
 assert mock_notifier.send.call_count == 1
 assert result == {"test": True}

 # Reset mock
 mock_notifier.send.reset_mock()

 # Empty list = no notifications
 result = manager.notify("Title", "Message", channels=[])
 mock_notifier.send.assert_not_called()
 assert result == {}

 def test_notification_manager_singleton_pattern(self):
 """Test notification manager singleton behavior"""
 from autocron.interface.notifications import (
 get_notification_manager,
 reset_notification_manager,
 )

 manager1 = get_notification_manager()
 manager2 = get_notification_manager()

 # Should be same instance
 assert manager1 is manager2

 # Reset and get new instance
 reset_notification_manager()
 manager3 = get_notification_manager()

 # Should be different instance
 assert manager1 is not manager3


if __name__ == "__main__":
 pytest.main([__file__, "-v"])
