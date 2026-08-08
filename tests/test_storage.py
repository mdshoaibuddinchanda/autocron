"""Tests for the durable SQLite storage layer."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from autocron.storage import (
    DuplicateTaskError,
    SQLiteStore,
    StorageError,
    UnsupportedSchemaError,
    default_database_path,
)


def task_data(name="backup", task_id="task-1", **overrides):
    data = {
        "task_id": task_id,
        "name": name,
        "script": "backup.py",
        "schedule_type": "interval",
        "schedule_value": "5m",
        "enabled": True,
        "run_count": 0,
        "fail_count": 0,
    }
    data.update(overrides)
    return data


def test_default_database_path_precedence(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit.db"
    state = tmp_path / "state"
    monkeypatch.setenv("AUTOCRON_HOME", str(state))
    monkeypatch.setenv("AUTOCRON_DATABASE", str(explicit))
    assert default_database_path() == explicit

    monkeypatch.delenv("AUTOCRON_DATABASE")
    assert default_database_path() == state / "autocron.db"


def test_task_crud_and_schema(tmp_path):
    database = tmp_path / "nested" / "autocron.db"
    with SQLiteStore(database) as store:
        assert database.exists()
        assert store.get_schema_version() == store.schema_version
        assert store.add_task(task_data()) == "task-1"
        assert store.get_task(task_id="task-1")["name"] == "backup"
        assert store.get_task(name="backup")["task_id"] == "task-1"
        assert store.get_task("backup")["schedule_value"] == "5m"
        assert store.list_tasks(enabled=True)[0]["enabled"] is True
        assert store.list_tasks(enabled=False) == []

        assert store.set_task_enabled("backup", False) is True
        assert store.list_tasks(enabled=True) == []
        assert store.list_tasks(enabled=False)[0]["enabled"] is False
        assert store.set_task_enabled("missing", True) is False

        updated = store.get_task("backup")
        updated["schedule_value"] = "10m"
        store.save_task(updated)
        assert store.get_task("task-1")["schedule_value"] == "10m"
        assert store.remove_task(name="backup") is True
        assert store.remove_task(task_id="task-1") is False
        assert store.list_tasks() == []


def test_duplicate_names_and_invalid_task_data(tmp_path):
    with SQLiteStore(tmp_path / "tasks.db") as store:
        store.add_task(task_data())
        with pytest.raises(DuplicateTaskError):
            store.add_task(task_data(task_id="different"))
        with pytest.raises(DuplicateTaskError):
            store.save_task(task_data(task_id="different"))
        with pytest.raises(ValueError, match="Missing required"):
            store.add_task({"name": "broken"})
        with pytest.raises(ValueError, match="schedule_type"):
            store.add_task(task_data(task_id="bad", schedule_type="calendar"))
        with pytest.raises(TypeError):
            store.add_task(object())


def test_credentials_are_never_serialized(tmp_path):
    database = tmp_path / "secrets.db"
    secret_task = task_data(
        email_config={
            "host": "smtp.example.com",
            "username": "person@example.com",
            "password": "do-not-store",
            "nested": {"api_key": "also-secret", "safe": "retained"},
        }
    )
    with SQLiteStore(database) as store:
        store.add_task(secret_task)
        saved = store.get_task("backup")
        assert saved["email_config"] == {
            "host": "smtp.example.com",
            "username": "person@example.com",
            "nested": {"safe": "retained"},
        }

        store.record_execution("backup", True, 0.1, metadata={"token": "hidden", "worker": "one"})
        assert store.list_executions()[0]["metadata"] == {"worker": "one"}

    assert b"do-not-store" not in database.read_bytes()
    assert b"also-secret" not in database.read_bytes()


def test_execution_history_and_aggregates(tmp_path):
    with SQLiteStore(tmp_path / "history.db") as store:
        store.add_task(task_data())
        first_id = store.record_execution(
            "backup",
            True,
            2.0,
            retry_count=1,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        second_id = store.record_execution(
            "backup",
            False,
            4.0,
            error="boom",
            retry_count=2,
            timestamp="2026-01-02T00:00:00+00:00",
        )
        assert second_id > first_id

        records = store.list_executions("backup", limit=1)
        assert len(records) == 1
        assert records[0]["success"] is False
        assert records[0]["error"] == "boom"

        stats = store.get_task_stats("backup")
        assert stats == {
            "task_name": "backup",
            "total_runs": 2,
            "successful_runs": 1,
            "failed_runs": 1,
            "success_rate": 50.0,
            "avg_duration": 3.0,
            "total_retries": 3,
            "first_run": "2026-01-01T00:00:00+00:00",
            "last_run": "2026-01-02T00:00:00+00:00",
            "recent_history": [
                {
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "success": True,
                    "duration": 2.0,
                    "error": None,
                    "retry_count": 1,
                },
                {
                    "timestamp": "2026-01-02T00:00:00+00:00",
                    "success": False,
                    "duration": 4.0,
                    "error": "boom",
                    "retry_count": 2,
                },
            ],
        }
        assert store.get_all_stats() == [stats]
        assert store.get_task_stats("missing") is None

        assert store.remove_task("backup") is True
        assert store.list_executions("backup")[0]["task_id"] is None


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"duration": -1}, "duration"),
        ({"duration": 0, "retry_count": -1}, "retry_count"),
    ],
)
def test_execution_validation(tmp_path, kwargs, message):
    with SQLiteStore(tmp_path / "validation.db") as store:
        with pytest.raises(ValueError, match=message):
            store.record_execution("task", True, **kwargs)
        with pytest.raises(ValueError, match="limit"):
            store.list_executions(limit=-1)


def test_transactions_roll_back_and_store_is_thread_safe(tmp_path):
    with SQLiteStore(tmp_path / "atomic.db") as store:
        with pytest.raises(RuntimeError):
            with store.transaction(write=True) as connection:
                connection.execute("""
                    INSERT INTO tasks (
                        task_id, name, script, schedule_type, schedule_value,
                        enabled, payload_json, created_at, updated_at
                    ) VALUES ('rolled-back', 'rolled-back', 'x.py', 'interval',
                              '1m', 1, '{}', 'now', 'now')
                    """)
                raise RuntimeError("abort")
        assert store.list_tasks() == []

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(store.record_execution, "parallel", index % 2 == 0, 0.1)
                for index in range(40)
            ]
            assert all(future.result() > 0 for future in futures)
        assert store.get_task_stats("parallel")["total_runs"] == 40


def test_identifier_validation_and_in_memory_lifecycle(tmp_path):
    store = SQLiteStore(":memory:")
    store.add_task(task_data())
    with pytest.raises(ValueError, match="exactly one"):
        store.get_task()
    with pytest.raises(ValueError, match="combined"):
        store.get_task("backup", name="backup")
    with pytest.raises(ValueError, match="exactly one"):
        store.remove_task()
    with pytest.raises(ValueError, match="combined"):
        store.remove_task("backup", task_id="task-1")
    store.close()
    with pytest.raises(StorageError, match="closed"):
        store.list_tasks()


def test_newer_schema_is_rejected(tmp_path):
    database = tmp_path / "future.db"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version = 999")
    connection.close()
    with pytest.raises(UnsupportedSchemaError):
        SQLiteStore(database)
