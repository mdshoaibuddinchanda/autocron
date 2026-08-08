"""Durable SQLite persistence for AutoCron tasks and execution history.

The storage layer deliberately uses only the Python standard library.  Each
operation runs in an explicit transaction, and file-backed stores use a fresh
connection per operation so one :class:`SQLiteStore` can safely be shared by
the scheduler's worker threads.
"""

from __future__ import annotations

import copy
import json
import os
import sqlite3
import sys
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Union

PathLike = Union[str, os.PathLike[str]]

SCHEMA_VERSION = 1
_SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "smtp_password",
    "token",
}


class StorageError(RuntimeError):
    """Base exception raised for persistence failures."""


class DuplicateTaskError(StorageError):
    """Raised when a task ID or name already exists."""


class UnsupportedSchemaError(StorageError):
    """Raised when a database was created by a newer AutoCron version."""


def default_database_path() -> Path:
    """Return the configured AutoCron database path.

    ``AUTOCRON_DATABASE`` selects the complete path. ``AUTOCRON_HOME`` selects
    the state directory and is especially useful for tests and portable
    installations.
    """

    configured = os.environ.get("AUTOCRON_DATABASE")
    if configured:
        return Path(configured).expanduser()

    state_dir = os.environ.get("AUTOCRON_HOME")
    if state_dir:
        return Path(state_dir).expanduser() / "autocron.db"

    if sys.platform == "win32":
        local_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        base = Path(local_data) if local_data else Path.home() / "AppData" / "Local"
        return base / "AutoCron" / "autocron.db"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AutoCron" / "autocron.db"

    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return base / "autocron" / "autocron.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, Path)):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _strip_secrets(value: Any) -> Any:
    """Return a deep copy with common credential fields removed."""

    if isinstance(value, Mapping):
        return {
            str(key): _strip_secrets(item)
            for key, item in value.items()
            if str(key).casefold() not in _SECRET_KEYS
        }
    if isinstance(value, list):
        return [_strip_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_secrets(item) for item in value]
    return copy.deepcopy(value)


class SQLiteStore:
    """Thread-safe task and execution-history store backed by SQLite."""

    schema_version = SCHEMA_VERSION

    def __init__(self, path: Optional[PathLike] = None, timeout: float = 5.0) -> None:
        requested_path = default_database_path() if path is None else Path(path).expanduser()
        self.path = (
            requested_path if str(requested_path) == ":memory:" else requested_path.resolve()
        )
        self.timeout = timeout
        self._lock = threading.RLock()
        self._memory_connection: Optional[sqlite3.Connection] = None
        self._closed = False

        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self._memory_connection = self._new_connection()

        self._initialize()

    def __enter__(self) -> "SQLiteStore":
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close an in-memory store; file-backed operations close eagerly."""

        with self._lock:
            if self._memory_connection is not None:
                self._memory_connection.close()
                self._memory_connection = None
            self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise StorageError("The SQLite store is closed")

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path),
            timeout=self.timeout,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {max(0, int(self.timeout * 1000))}")
        return connection

    @contextmanager
    def transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        """Yield a connection inside an atomic transaction.

        Write transactions use ``BEGIN IMMEDIATE`` to reserve the writer lock
        before work starts. Exceptions always roll the transaction back.
        """

        with self._lock:
            self._ensure_open()
            connection = self._memory_connection or self._new_connection()
            should_close = self._memory_connection is None
            try:
                connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                if should_close:
                    connection.close()

    def _initialize(self) -> None:
        try:
            with self.transaction(write=True) as connection:
                current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if current_version > SCHEMA_VERSION:
                    raise UnsupportedSchemaError(
                        f"Database schema {current_version} is newer than supported "
                        f"schema {SCHEMA_VERSION}"
                    )
                if current_version == 0:
                    self._migrate_to_v1(connection)
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

            if str(self.path) != ":memory:":
                with self._lock:
                    connection = self._new_connection()
                    try:
                        connection.execute("PRAGMA journal_mode = WAL")
                    finally:
                        connection.close()
        except (sqlite3.Error, OSError) as exc:
            raise StorageError(f"Unable to initialize database '{self.path}': {exc}") from exc

    @staticmethod
    def _migrate_to_v1(connection: sqlite3.Connection) -> None:
        statements = (
            """CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                script TEXT NOT NULL,
                schedule_type TEXT NOT NULL CHECK (schedule_type IN ('interval', 'cron')),
                schedule_value TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE INDEX IF NOT EXISTS idx_tasks_enabled_name
                ON tasks(enabled, name)""",
            """CREATE TABLE IF NOT EXISTS executions (
                execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                task_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success INTEGER NOT NULL CHECK (success IN (0, 1)),
                duration REAL NOT NULL CHECK (duration >= 0),
                error TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
            )""",
            """CREATE INDEX IF NOT EXISTS idx_executions_task_time
                ON executions(task_name, timestamp DESC, execution_id DESC)""",
        )
        for statement in statements:
            connection.execute(statement)

    def get_schema_version(self) -> int:
        """Return the on-disk schema version."""

        with self.transaction() as connection:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])

    @staticmethod
    def _task_payload(task: Any) -> Dict[str, Any]:
        if hasattr(task, "to_dict"):
            task = task.to_dict()
        if not isinstance(task, Mapping):
            raise TypeError("task must be a mapping or expose to_dict()")

        payload = _strip_secrets(dict(task))
        required = ("name", "script", "schedule_type", "schedule_value")
        missing = [field for field in required if not payload.get(field)]
        if missing:
            raise ValueError(f"Missing required task field(s): {', '.join(missing)}")
        if payload["schedule_type"] not in {"interval", "cron"}:
            raise ValueError("schedule_type must be 'interval' or 'cron'")

        payload.setdefault("task_id", str(uuid.uuid4()))
        payload.setdefault("enabled", True)
        payload.setdefault("run_count", 0)
        payload.setdefault("fail_count", 0)
        return payload

    @staticmethod
    def _task_values(payload: Mapping[str, Any], now: str) -> tuple[Any, ...]:
        return (
            str(payload["task_id"]),
            str(payload["name"]),
            str(payload["script"]),
            str(payload["schedule_type"]),
            str(payload["schedule_value"]),
            int(bool(payload.get("enabled", True))),
            json.dumps(payload, default=_json_default, sort_keys=True),
            now,
            now,
        )

    def add_task(self, task: Any) -> str:
        """Insert a new task and return its ID.

        Task IDs and names are unique. Use :meth:`save_task` when updating an
        existing record.
        """

        payload = self._task_payload(task)
        now = _utc_now()
        try:
            with self.transaction(write=True) as connection:
                connection.execute(
                    """
                    INSERT INTO tasks (
                        task_id, name, script, schedule_type, schedule_value,
                        enabled, payload_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._task_values(payload, now),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateTaskError(f"A task named '{payload['name']}' already exists") from exc
        except sqlite3.Error as exc:
            raise StorageError(f"Unable to add task '{payload['name']}': {exc}") from exc
        return str(payload["task_id"])

    def save_task(self, task: Any) -> str:
        """Insert or update a task by ID and return its ID."""

        payload = self._task_payload(task)
        now = _utc_now()
        values = self._task_values(payload, now)
        try:
            with self.transaction(write=True) as connection:
                connection.execute(
                    """
                    INSERT INTO tasks (
                        task_id, name, script, schedule_type, schedule_value,
                        enabled, payload_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        name = excluded.name,
                        script = excluded.script,
                        schedule_type = excluded.schedule_type,
                        schedule_value = excluded.schedule_value,
                        enabled = excluded.enabled,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    values,
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateTaskError(f"A task named '{payload['name']}' already exists") from exc
        except sqlite3.Error as exc:
            raise StorageError(f"Unable to save task '{payload['name']}': {exc}") from exc
        return str(payload["task_id"])

    @staticmethod
    def _decode_task(row: sqlite3.Row) -> Dict[str, Any]:
        payload = json.loads(row["payload_json"])
        payload.update(
            {
                "task_id": row["task_id"],
                "name": row["name"],
                "script": row["script"],
                "schedule_type": row["schedule_type"],
                "schedule_value": row["schedule_value"],
                "enabled": bool(row["enabled"]),
            }
        )
        return payload

    def get_task(
        self,
        identifier: Optional[str] = None,
        *,
        task_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return one task by ID or name, or ``None`` when it does not exist."""

        if identifier is not None:
            if task_id is not None or name is not None:
                raise ValueError("identifier cannot be combined with task_id or name")
            task_id = identifier
            name = identifier
        elif (task_id is None) == (name is None):
            raise ValueError("Specify exactly one of identifier, task_id, or name")

        with self.transaction() as connection:
            if identifier is not None:
                row = connection.execute(
                    "SELECT * FROM tasks WHERE task_id = ? OR name = ? LIMIT 1",
                    (task_id, name),
                ).fetchone()
            elif task_id is not None:
                row = connection.execute(
                    "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
                ).fetchone()
            else:
                row = connection.execute("SELECT * FROM tasks WHERE name = ?", (name,)).fetchone()
        return self._decode_task(row) if row is not None else None

    def list_tasks(self, *, enabled: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Return all tasks ordered by name."""

        query = "SELECT * FROM tasks"
        parameters: tuple[Any, ...] = ()
        if enabled is not None:
            query += " WHERE enabled = ?"
            parameters = (int(enabled),)
        query += " ORDER BY name COLLATE NOCASE, task_id"

        with self.transaction() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._decode_task(row) for row in rows]

    def remove_task(
        self,
        identifier: Optional[str] = None,
        *,
        task_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> bool:
        """Delete a task by ID or name while retaining its execution history."""

        if identifier is not None:
            if task_id is not None or name is not None:
                raise ValueError("identifier cannot be combined with task_id or name")
            clause = "task_id = ? OR name = ?"
            parameters: tuple[str, ...] = (identifier, identifier)
        elif (task_id is None) == (name is None):
            raise ValueError("Specify exactly one of identifier, task_id, or name")
        elif task_id is not None:
            clause = "task_id = ?"
            parameters = (task_id,)
        else:
            assert name is not None
            clause = "name = ?"
            parameters = (name,)

        try:
            with self.transaction(write=True) as connection:
                # ``clause`` is selected exclusively from the fixed branches
                # above; user values remain DB parameters (B608 is a false
                # positive for this allow-listed query shape).
                cursor = connection.execute(
                    f"DELETE FROM tasks WHERE {clause}",  # nosec B608
                    parameters,
                )
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            raise StorageError(f"Unable to remove task: {exc}") from exc

    def set_task_enabled(self, identifier: str, enabled: bool) -> bool:
        """Enable or disable a persisted task."""

        with self.transaction(write=True) as connection:
            row = connection.execute(
                "SELECT task_id, payload_json FROM tasks WHERE task_id = ? OR name = ? LIMIT 1",
                (identifier, identifier),
            ).fetchone()
            if row is None:
                return False
            payload = json.loads(row["payload_json"])
            payload["enabled"] = bool(enabled)
            connection.execute(
                """
                UPDATE tasks SET enabled = ?, payload_json = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (int(enabled), json.dumps(payload, sort_keys=True), _utc_now(), row["task_id"]),
            )
            return True

    def sync_tasks(self, tasks: Any) -> None:
        """Persist the current state of every task in an iterable or scheduler."""

        if hasattr(tasks, "list_tasks"):
            tasks = tasks.list_tasks()
        for task in tasks:
            self.save_task(task)

    def record_execution(
        self,
        task_name: str,
        success: bool,
        duration: float,
        error: Optional[str] = None,
        retry_count: int = 0,
        *,
        task_id: Optional[str] = None,
        timestamp: Optional[Union[str, datetime]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> int:
        """Atomically append an execution event and return its numeric ID."""

        if duration < 0:
            raise ValueError("duration must be non-negative")
        if retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if isinstance(timestamp, datetime):
            timestamp_value = timestamp.isoformat()
        else:
            timestamp_value = timestamp or _utc_now()

        clean_metadata = _strip_secrets(dict(metadata or {}))
        try:
            with self.transaction(write=True) as connection:
                resolved_task_id = task_id
                if resolved_task_id is None:
                    row = connection.execute(
                        "SELECT task_id FROM tasks WHERE name = ?", (task_name,)
                    ).fetchone()
                    resolved_task_id = row["task_id"] if row else None
                cursor = connection.execute(
                    """
                    INSERT INTO executions (
                        task_id, task_name, timestamp, success, duration,
                        error, retry_count, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        resolved_task_id,
                        task_name,
                        timestamp_value,
                        int(bool(success)),
                        float(duration),
                        error,
                        int(retry_count),
                        json.dumps(clean_metadata, default=_json_default, sort_keys=True),
                    ),
                )
                return int(cursor.lastrowid or 0)
        except sqlite3.Error as exc:
            raise StorageError(f"Unable to record execution for '{task_name}': {exc}") from exc

    @staticmethod
    def _decode_execution(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "execution_id": row["execution_id"],
            "task_id": row["task_id"],
            "task_name": row["task_name"],
            "timestamp": row["timestamp"],
            "success": bool(row["success"]),
            "duration": float(row["duration"]),
            "error": row["error"],
            "retry_count": int(row["retry_count"]),
            "metadata": json.loads(row["metadata_json"]),
        }

    def list_executions(
        self, task_name: Optional[str] = None, *, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Return execution events newest first."""

        query = "SELECT * FROM executions"
        parameters: List[Any] = []
        if task_name is not None:
            query += " WHERE task_name = ?"
            parameters.append(task_name)
        query += " ORDER BY timestamp DESC, execution_id DESC"
        if limit is not None:
            if limit < 0:
                raise ValueError("limit must be non-negative")
            query += " LIMIT ?"
            parameters.append(limit)

        with self.transaction() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._decode_execution(row) for row in rows]

    def get_task_stats(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Return aggregate and recent execution statistics for one task."""

        with self.transaction() as connection:
            aggregate = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_runs,
                    COALESCE(SUM(success), 0) AS successful_runs,
                    COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) AS failed_runs,
                    COALESCE(SUM(duration), 0.0) AS total_duration,
                    COALESCE(SUM(retry_count), 0) AS total_retries,
                    MIN(timestamp) AS first_run,
                    MAX(timestamp) AS last_run
                FROM executions WHERE task_name = ?
                """,
                (task_name,),
            ).fetchone()
            if aggregate is None or aggregate["total_runs"] == 0:
                return None
            history_rows = connection.execute(
                """
                SELECT * FROM executions WHERE task_name = ?
                ORDER BY timestamp DESC, execution_id DESC LIMIT 10
                """,
                (task_name,),
            ).fetchall()

        total_runs = int(aggregate["total_runs"])
        successful_runs = int(aggregate["successful_runs"])
        history = [self._decode_execution(row) for row in reversed(history_rows)]
        for record in history:
            record.pop("task_name", None)
            record.pop("task_id", None)
            record.pop("execution_id", None)
            record.pop("metadata", None)
        return {
            "task_name": task_name,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": int(aggregate["failed_runs"]),
            "success_rate": (successful_runs / total_runs) * 100,
            "avg_duration": float(aggregate["total_duration"]) / total_runs,
            "total_retries": int(aggregate["total_retries"]),
            "first_run": aggregate["first_run"],
            "last_run": aggregate["last_run"],
            "recent_history": history,
        }

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Return statistics for every task with execution history."""

        with self.transaction() as connection:
            rows = connection.execute("""
                SELECT DISTINCT task_name FROM executions
                ORDER BY task_name COLLATE NOCASE
                """).fetchall()
        stats = [self.get_task_stats(row["task_name"]) for row in rows]
        return sorted(
            (item for item in stats if item is not None),
            key=lambda item: item["last_run"],
            reverse=True,
        )


# A concise alias reads naturally in application code while SQLiteStore keeps
# the backend explicit for callers that may add other stores in the future.
TaskStore = SQLiteStore


__all__ = [
    "DuplicateTaskError",
    "SCHEMA_VERSION",
    "SQLiteStore",
    "StorageError",
    "TaskStore",
    "UnsupportedSchemaError",
    "default_database_path",
]
