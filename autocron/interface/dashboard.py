"""Terminal dashboard and execution analytics for AutoCron."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from autocron.storage import SQLiteStore, default_database_path

try:
    from rich import box
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    if TYPE_CHECKING:
        from rich.table import Table


class TaskAnalytics:
    """Record and analyze task executions.

    New installations use AutoCron's SQLite database. Passing a path ending in
    ``.json`` keeps the v1.2 JSON format available for existing callers and
    data exports.
    """

    def __init__(
        self,
        storage_path: Optional[Union[str, Path]] = None,
        *,
        database_path: Optional[Union[str, Path]] = None,
        store: Optional[SQLiteStore] = None,
    ) -> None:
        supplied = sum(value is not None for value in (database_path, store))
        if storage_path is not None and supplied:
            raise ValueError("storage_path cannot be combined with database_path or store")
        if supplied > 1:
            raise ValueError("database_path and store are mutually exclusive")

        self._lock = threading.RLock()
        self._store: Optional[SQLiteStore] = None
        self._json_mode = False
        self._data: Dict[str, Dict[str, Any]] = {}

        if store is not None:
            self._store = store
            self.storage_path = store.path
        elif database_path is not None:
            self._store = SQLiteStore(database_path)
            self.storage_path = self._store.path
        elif storage_path is not None and Path(storage_path).suffix.casefold() == ".json":
            self._json_mode = True
            self.storage_path = Path(storage_path).expanduser()
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._data = self._load_json()
        else:
            selected_path = default_database_path() if storage_path is None else Path(storage_path)
            self._store = SQLiteStore(selected_path)
            self.storage_path = self._store.path

    @property
    def store(self) -> Optional[SQLiteStore]:
        """Return the SQLite backend, or ``None`` for legacy JSON mode."""

        return self._store

    def close(self) -> None:
        """Close this analytics object's SQLite store."""

        if self._store is not None:
            self._store.close()

    def _load_json(self) -> Dict[str, Dict[str, Any]]:
        if not self.storage_path.exists():
            return {}
        try:
            with self.storage_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError, TypeError):
            return {}

    def _save_json(self) -> None:
        """Atomically replace the legacy JSON analytics file."""

        temporary_name: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.storage_path.parent,
                prefix=f".{self.storage_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_name = handle.name
                json.dump(self._data, handle, indent=2, default=str)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.storage_path)
        except OSError:
            if temporary_name:
                try:
                    Path(temporary_name).unlink(missing_ok=True)
                except OSError:
                    pass

    def record_execution(
        self,
        task_name: str,
        success: bool,
        duration: float,
        error: Optional[str] = None,
        retry_count: int = 0,
    ) -> None:
        """Record one completed task execution."""

        if self._store is not None:
            self._store.record_execution(
                task_name=task_name,
                success=success,
                duration=duration,
                error=error,
                retry_count=retry_count,
            )
            return

        if duration < 0:
            raise ValueError("duration must be non-negative")
        if retry_count < 0:
            raise ValueError("retry_count must be non-negative")

        with self._lock:
            if task_name not in self._data:
                self._data[task_name] = {
                    "total_runs": 0,
                    "successful_runs": 0,
                    "failed_runs": 0,
                    "total_duration": 0.0,
                    "total_retries": 0,
                    "history": [],
                    "first_run": None,
                    "last_run": None,
                }

            task_data = self._data[task_name]
            task_data["total_runs"] += 1
            task_data["total_duration"] += duration
            task_data["total_retries"] += retry_count
            task_data["successful_runs" if success else "failed_runs"] += 1

            execution_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": bool(success),
                "duration": float(duration),
                "error": error,
                "retry_count": int(retry_count),
            }
            task_data["history"].append(execution_record)
            task_data["history"] = task_data["history"][-100:]
            if task_data["first_run"] is None:
                task_data["first_run"] = execution_record["timestamp"]
            task_data["last_run"] = execution_record["timestamp"]
            self._save_json()

    def get_task_stats(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Return aggregate and recent statistics for a task."""

        if self._store is not None:
            return self._store.get_task_stats(task_name)

        with self._lock:
            task_data = self._data.get(task_name)
            if not task_data or not task_data.get("total_runs"):
                return None
            total_runs = int(task_data["total_runs"])
            return {
                "task_name": task_name,
                "total_runs": total_runs,
                "successful_runs": int(task_data["successful_runs"]),
                "failed_runs": int(task_data["failed_runs"]),
                "success_rate": (task_data["successful_runs"] / total_runs) * 100,
                "avg_duration": task_data["total_duration"] / total_runs,
                "total_retries": int(task_data["total_retries"]),
                "first_run": task_data["first_run"],
                "last_run": task_data["last_run"],
                "recent_history": list(task_data["history"][-10:]),
            }

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Return statistics for every task with execution history."""

        if self._store is not None:
            return self._store.get_all_stats()
        with self._lock:
            names = list(self._data)
        stats = [self.get_task_stats(task_name) for task_name in names]
        return sorted(
            (item for item in stats if item is not None),
            key=lambda item: item["last_run"],
            reverse=True,
        )

    def get_recommendations(self, task_name: str) -> List[str]:
        """Analyze a task's history and return actionable recommendations."""

        stats = self.get_task_stats(task_name)
        if not stats:
            return ["No execution history available yet."]

        recommendations: List[str] = []
        if stats["success_rate"] < 80:
            recommendations.append(
                f"⚠️  Low success rate ({stats['success_rate']:.1f}%). "
                "Consider adding error handling or increasing retry attempts."
            )
        average_retries = stats["total_retries"] / stats["total_runs"]
        if average_retries > 0.5:
            recommendations.append(
                f"🔄 High retry rate ({average_retries:.1f} per run). "
                "The task may be failing frequently. Check error logs."
            )
        if stats["avg_duration"] > 300:
            recommendations.append(
                f"⏱️  Long average duration ({stats['avg_duration']:.1f}s). "
                "Consider optimizing the task or running it less frequently."
            )
        recent_failures = sum(not record["success"] for record in stats["recent_history"][-5:])
        if recent_failures >= 3:
            recommendations.append(
                "❌ Multiple recent failures detected. Check task implementation."
            )
        if not recommendations:
            recommendations.append("✅ Task is performing well! No recommendations.")
        return recommendations


class Dashboard:
    """Rich terminal dashboard for monitoring AutoCron tasks."""

    def __init__(
        self,
        analytics: Optional[TaskAnalytics] = None,
        *,
        database_path: Optional[Union[str, Path]] = None,
    ) -> None:
        if analytics is not None and database_path is not None:
            raise ValueError("analytics and database_path are mutually exclusive")
        self.analytics = analytics or TaskAnalytics(database_path=database_path)
        self.console: Any = Console() if RICH_AVAILABLE else None

    def _check_rich(self) -> None:
        if not RICH_AVAILABLE:
            raise ImportError(
                "The 'rich' package is required for dashboard features. "
                "Install it with: pip install autocron-scheduler[dashboard]"
            )

    def show_summary(self) -> None:
        """Display a summary table of all recorded tasks."""

        self._check_rich()
        stats = self.analytics.get_all_stats()
        if not stats:
            self.console.print("[yellow]No task execution history available yet.[/yellow]")
            return

        table = Table(
            title="📊 AutoCron Task Summary",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Task Name", style="cyan", no_wrap=True)
        table.add_column("Total Runs", justify="right", style="white")
        table.add_column("Success Rate", justify="right", style="green")
        table.add_column("Avg Duration", justify="right", style="blue")
        table.add_column("Last Run", justify="right", style="yellow")
        table.add_column("Status", justify="center")

        for task_stat in stats:
            rate = task_stat["success_rate"]
            status = "✅" if rate >= 95 else "⚠️" if rate >= 80 else "❌"
            last_run = datetime.fromisoformat(task_stat["last_run"])
            table.add_row(
                task_stat["task_name"],
                str(task_stat["total_runs"]),
                f"{rate:.1f}%",
                f"{task_stat['avg_duration']:.2f}s",
                self._format_time_ago(last_run),
                status,
            )
        self.console.print(table)

    def show_task_details(self, task_name: str) -> bool:
        """Display detailed information for one task.

        Returns ``False`` when the task has no execution history.
        """

        self._check_rich()
        stats = self.analytics.get_task_stats(task_name)
        if not stats:
            self.console.print(f"[red]No data found for task: {task_name}[/red]")
            return False

        info_table = Table(
            title=f"📋 Task Details: {task_name}",
            box=box.DOUBLE,
            show_header=False,
            padding=(0, 2),
        )
        info_table.add_column("Metric", style="bold cyan")
        info_table.add_column("Value", style="white")
        info_table.add_row("Total Runs", str(stats["total_runs"]))
        info_table.add_row("Successful", f"✅ {stats['successful_runs']}")
        info_table.add_row("Failed", f"❌ {stats['failed_runs']}")
        info_table.add_row("Success Rate", f"{stats['success_rate']:.2f}%")
        info_table.add_row("Avg Duration", f"{stats['avg_duration']:.2f}s")
        info_table.add_row("Total Retries", str(stats["total_retries"]))
        first_run = datetime.fromisoformat(stats["first_run"])
        last_run = datetime.fromisoformat(stats["last_run"])
        info_table.add_row("First Run", first_run.strftime("%Y-%m-%d %H:%M:%S %Z"))
        info_table.add_row("Last Run", last_run.strftime("%Y-%m-%d %H:%M:%S %Z"))
        self.console.print(info_table)
        self.console.print()

        history_table = Table(
            title="📈 Recent Execution History",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        history_table.add_column("Time", style="yellow")
        history_table.add_column("Status", justify="center")
        history_table.add_column("Duration", justify="right", style="blue")
        history_table.add_column("Retries", justify="right", style="cyan")
        history_table.add_column("Error", style="red")
        for record in reversed(stats["recent_history"][-10:]):
            timestamp = datetime.fromisoformat(record["timestamp"])
            error = str(record["error"])
            if record["error"] and len(error) > 40:
                error = f"{error[:40]}..."
            history_table.add_row(
                timestamp.strftime("%m-%d %H:%M:%S"),
                "✅" if record["success"] else "❌",
                f"{record['duration']:.2f}s",
                str(record["retry_count"]) if record["retry_count"] else "-",
                error if record["error"] else "-",
            )
        self.console.print(history_table)
        self.console.print()
        self.console.print(
            Panel(
                "\n".join(self.analytics.get_recommendations(task_name)),
                title="💡 Recommendations",
                border_style="green",
                padding=(1, 2),
            )
        )
        return True

    def show_live_monitor(self, refresh_rate: float = 2) -> None:
        """Display a live-updating dashboard until interrupted."""

        self._check_rich()
        if refresh_rate <= 0:
            raise ValueError("refresh_rate must be greater than zero")
        self.console.print("[cyan]Starting live monitor... Press Ctrl+C to exit[/cyan]")
        self.console.print()
        try:
            with Live(
                self._generate_live_view(),
                refresh_per_second=1 / refresh_rate,
                console=self.console,
            ) as live:
                while True:
                    import time

                    time.sleep(refresh_rate)
                    live.update(self._generate_live_view())
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Live monitor stopped.[/yellow]")

    def _generate_live_view(self) -> "Table":
        stats = self.analytics.get_all_stats()
        table = Table(
            title=f"📊 AutoCron Live Dashboard - {datetime.now().strftime('%H:%M:%S')}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Task", style="cyan", no_wrap=True)
        table.add_column("Runs", justify="right", style="white")
        table.add_column("Success", justify="right", style="green")
        table.add_column("Avg Time", justify="right", style="blue")
        table.add_column("Last Run", justify="right", style="yellow")
        table.add_column("Status", justify="center")
        if not stats:
            table.add_row("No tasks", "-", "-", "-", "-", "⏳")
            return table

        for task_stat in stats:
            rate = task_stat["success_rate"]
            status = "✅" if rate >= 95 else "⚠️" if rate >= 80 else "❌"
            table.add_row(
                task_stat["task_name"],
                str(task_stat["total_runs"]),
                f"{rate:.1f}%",
                f"{task_stat['avg_duration']:.1f}s",
                self._format_time_ago(datetime.fromisoformat(task_stat["last_run"])),
                status,
            )
        return table

    @staticmethod
    def _format_time_ago(dt: datetime) -> str:
        """Format a datetime as a compact relative time."""

        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        difference = max(now - dt, timedelta(0))
        if difference < timedelta(minutes=1):
            return "just now"
        if difference < timedelta(hours=1):
            return f"{int(difference.total_seconds() / 60)}m ago"
        if difference < timedelta(days=1):
            return f"{int(difference.total_seconds() / 3600)}h ago"
        return f"{difference.days}d ago"

    def export_stats(self, output_file: Optional[Union[str, Path]] = None) -> Path:
        """Atomically export all statistics to JSON and return the path."""

        output_path = Path(output_file or "autocron_stats.json").expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_name: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_name = handle.name
                json.dump(self.analytics.get_all_stats(), handle, indent=2, default=str)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, output_path)
        except Exception:
            if temporary_name:
                try:
                    Path(temporary_name).unlink(missing_ok=True)
                except OSError:
                    pass
            raise

        message = f"✅ Stats exported to {output_path}"
        if self.console:
            self.console.print(f"[green]{message}[/green]")
        else:
            print(message)
        return output_path


def show_dashboard(database_path: Optional[Union[str, Path]] = None) -> None:
    """Show the task summary dashboard."""

    Dashboard(database_path=database_path).show_summary()


def show_task(task_name: str, database_path: Optional[Union[str, Path]] = None) -> None:
    """Show detailed statistics for one task."""

    Dashboard(database_path=database_path).show_task_details(task_name)


def live_monitor(refresh_rate: float = 2, database_path: Optional[Union[str, Path]] = None) -> None:
    """Start the live task monitor."""

    Dashboard(database_path=database_path).show_live_monitor(refresh_rate)


__all__ = [
    "Dashboard",
    "RICH_AVAILABLE",
    "TaskAnalytics",
    "live_monitor",
    "show_dashboard",
    "show_task",
]
