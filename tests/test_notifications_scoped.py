"""Task-scoped and thread-safe notification manager tests."""

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import pytest

from autocron.interface.notifications import (
    NotificationError,
    NotificationManager,
    get_notification_manager,
    reset_notification_manager,
)


def test_notifier_registration_validation_and_removal():
    manager = NotificationManager()

    with pytest.raises(ValueError, match="cannot be empty"):
        manager.add_notifier("", Mock())
    with pytest.raises(TypeError, match="callable send"):
        manager.add_notifier("invalid", object())

    notifier = Mock()
    manager.add_notifier("task:email", notifier)

    assert manager.remove_notifier("task:email") is True
    assert manager.remove_notifier("task:email") is False


def test_named_email_registration_does_not_replace_other_tasks():
    manager = NotificationManager()
    first = {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "from_email": "first@example.com",
        "to_email": "ops@example.com",
        "password": "first-secret",
    }
    second = {**first, "from_email": "second@example.com", "password": "second-secret"}

    assert manager.setup_email(first, name="email:first") == "email:first"
    assert manager.setup_email(second, name="email:second") == "email:second"

    assert manager.notifiers["email:first"].from_email == "first@example.com"
    assert manager.notifiers["email:second"].from_email == "second@example.com"


def test_desktop_setup_returns_none_when_optional_dependency_fails():
    manager = NotificationManager()
    with patch(
        "autocron.interface.notifications.DesktopNotifier",
        side_effect=NotificationError("not installed"),
    ):
        assert manager.setup_desktop(name="desktop:task") is None
    assert manager.notifiers == {}


def test_notify_uses_snapshot_when_channel_is_removed_during_send():
    manager = NotificationManager()
    first = Mock()
    second = Mock()
    first.send.side_effect = lambda *_args, **_kwargs: manager.remove_notifier("second") or True
    second.send.return_value = True
    manager.add_notifier("first", first)
    manager.add_notifier("second", second)

    assert manager.notify("title", "message") == {"first": True, "second": True}
    second.send.assert_called_once_with("title", "message")


def test_global_notification_manager_is_singleton_under_threads():
    reset_notification_manager()
    with ThreadPoolExecutor(max_workers=8) as executor:
        managers = list(executor.map(lambda _index: get_notification_manager(), range(32)))

    assert len({id(manager) for manager in managers}) == 1
