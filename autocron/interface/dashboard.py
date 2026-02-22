"""
AutoCron Dashboard - Visualize and monitor your scheduled tasks.

This module provides CLI and programmatic interfaces to visualize task
execution statistics, history, and performance metrics with rich formatting.
"""

import contextlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

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
 """Store and analyze task execution history."""

 def __init__(self, storage_path: Optional[Path] = None):
 """Initialize task analytics storage.

 Args:
 storage_path: Path to JSON file for storing analytics data.
 Defaults to ~/.autocron/analytics.json
 """
 if storage_path is None:
 storage_path = Path.home() / ".autocron" / "analytics.json"

 self.storage_path = Path(storage_path)
 self.storage_path.parent.mkdir(parents=True, exist_ok=True)
 self._data: Dict[str, Dict[str, Any]] = self._load()

 def _load(self) -> Dict[str, Dict[str, Any]]:
 """Load analytics data from disk."""
 if self.storage_path.exists():
 try:
 with open(self.storage_path, "r") as f:
 return json.load(f)
 except (json.JSONDecodeError, IOError):
 return {}
 return {}

 def _save(self) -> None:
 """Save analytics data to disk."""
 with contextlib.suppress(IOError):
 with open(self.storage_path, "w") as f:
 json.dump(self._data, f, indent=2, default=str)

 def record_execution(
 self,
 task_name: str,
 success: bool,
 duration: float,
 error: Optional[str] = None,
 retry_count: int = 0,
 ) -> None:
 """Record a task execution event.

 Args:
 task_name: Name of the executed task
 success: Whether the execution succeeded
 duration: Execution duration in seconds
 error: Error message if execution failed
 retry_count: Number of retries attempted
 """
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

 if success:
 task_data["successful_runs"] += 1
 else:
 task_data["failed_runs"] += 1

 # Record history (keep last 100 executions)
 execution_record = {
 "timestamp": datetime.now().isoformat(),
 "success": success,
 "duration": duration,
 "error": error,
 "retry_count": retry_count,
 }

 task_data["history"].append(execution_record)
 task_data["history"] = task_data["history"][-100:] # Keep last 100

 # Update timestamps
 if task_data["first_run"] is None:
 task_data["first_run"] = execution_record["timestamp"]
 task_data["last_run"] = execution_record["timestamp"]

 self._save()

 def get_task_stats(self, task_name: str) -> Optional[Dict[str, Any]]:
 """Get statistics for a specific task.

 Args:
 task_name: Name of the task

 Returns:
 Dictionary of task statistics or None if task not found
 """
 if task_name not in self._data:
 return None

 task_data = self._data[task_name]
 total_runs = task_data["total_runs"]

 if total_runs == 0:
 return None

 avg_duration = task_data["total_duration"] / total_runs
 success_rate = (task_data["successful_runs"] / total_runs) * 100

 # Get recent history
 recent_history = task_data["history"][-10:]

 return {
 "task_name": task_name,
 "total_runs": total_runs,
 "successful_runs": task_data["successful_runs"],
 "failed_runs": task_data["failed_runs"],
 "success_rate": success_rate,
 "avg_duration": avg_duration,
 "total_retries": task_data["total_retries"],
 "first_run": task_data["first_run"],
 "last_run": task_data["last_run"],
 "recent_history": recent_history,
 }

 def get_all_stats(self) -> List[Dict[str, Any]]:
 """Get statistics for all tasks.

 Returns:
 List of task statistics dictionaries
 """
 stats = []
 for task_name in self._data:
 if task_stats := self.get_task_stats(task_name):
 stats.append(task_stats)
 return sorted(stats, key=lambda x: x["last_run"], reverse=True)

 def get_recommendations(self, task_name: str) -> List[str]:
 """Analyze task history and provide recommendations.

 Args:
 task_name: Name of the task to analyze

 Returns:
 List of recommendation strings
 """
 stats = self.get_task_stats(task_name)
 if not stats:
 return ["No execution history available yet."]

 recommendations = []

 # Check success rate
 if stats["success_rate"] < 80:
 recommendations.append(
 f"️ Low success rate ({stats['success_rate']:.1f}%). "
 "Consider adding error handling or increasing retry attempts."
 )

 # Check for frequent retries
 avg_retries = stats["total_retries"] / stats["total_runs"]
 if avg_retries > 0.5:
 recommendations.append(
 f" High retry rate ({avg_retries:.1f} per run). "
 "The task may be failing frequently. Check error logs."
 )

 # Check execution duration
 if stats["avg_duration"] > 300: # 5 minutes
 recommendations.append(
 f"⏱️ Long average duration ({stats['avg_duration']:.1f}s). "
 "Consider optimizing the task or running it less frequently."
 )

 # Check recent failures
 recent = stats["recent_history"][-5:]
 recent_failures = sum(not r["success"] for r in recent)
 if recent_failures >= 3:
 recommendations.append(
 " Multiple recent failures detected. Check task implementation."
 )

 if not recommendations:
 recommendations.append(" Task is performing well! No recommendations.")

 return recommendations


class Dashboard:
 """Interactive dashboard for monitoring AutoCron tasks."""

 def __init__(self, analytics: Optional[TaskAnalytics] = None):
 """Initialize the dashboard.

 Args:
 analytics: TaskAnalytics instance to use for data
 """
 self.analytics = analytics or TaskAnalytics()
 self.console = Console() if RICH_AVAILABLE else None

 def _check_rich(self) -> None:
 """Check if rich is available."""
 if not RICH_AVAILABLE:
 raise ImportError(
 "The 'rich' package is required for dashboard features. "
 "Install it with: pip install autocron-scheduler[dashboard]"
 )

 def show_summary(self) -> None:
 """Display a summary table of all tasks."""
 self._check_rich()

 stats = self.analytics.get_all_stats()

 if not stats:
 self.console.print("[yellow]No task execution history available yet.[/yellow]")
 return

 table = Table(
 title=" AutoCron Task Summary",
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
 # Status emoji based on success rate
 if task_stat["success_rate"] >= 95:
 status = ""
 elif task_stat["success_rate"] >= 80:
 status = "️"
 else:
 status = ""

 # Format last run time
 last_run = datetime.fromisoformat(task_stat["last_run"])
 time_ago = self._format_time_ago(last_run)

 # Format duration
 duration = f"{task_stat['avg_duration']:.2f}s"

 table.add_row(
 task_stat["task_name"],
 str(task_stat["total_runs"]),
 f"{task_stat['success_rate']:.1f}%",
 duration,
 time_ago,
 status,
 )

 self.console.print(table)

 def show_task_details(self, task_name: str) -> None:
 """Display detailed information for a specific task.

 Args:
 task_name: Name of the task to display
 """
 self._check_rich()

 stats = self.analytics.get_task_stats(task_name)

 if not stats:
 self.console.print(f"[red]No data found for task: {task_name}[/red]")
 return

 # Create main info table
 info_table = Table(
 title=f" Task Details: {task_name}", box=box.DOUBLE, show_header=False, padding=(0, 2)
 )

 info_table.add_column("Metric", style="bold cyan")
 info_table.add_column("Value", style="white")

 info_table.add_row("Total Runs", str(stats["total_runs"]))
 info_table.add_row("Successful", f" {stats['successful_runs']}")
 info_table.add_row("Failed", f" {stats['failed_runs']}")
 info_table.add_row("Success Rate", f"{stats['success_rate']:.2f}%")
 info_table.add_row("Avg Duration", f"{stats['avg_duration']:.2f}s")
 info_table.add_row("Total Retries", str(stats["total_retries"]))

 first_run = datetime.fromisoformat(stats["first_run"])
 last_run = datetime.fromisoformat(stats["last_run"])
 info_table.add_row("First Run", first_run.strftime("%Y-%m-%d %H:%M:%S"))
 info_table.add_row("Last Run", last_run.strftime("%Y-%m-%d %H:%M:%S"))

 self.console.print(info_table)
 self.console.print()

 # Show recent history
 history_table = Table(
 title=" Recent Execution History",
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
 time_str = timestamp.strftime("%m-%d %H:%M:%S")
 status = "" if record["success"] else ""
 duration = f"{record['duration']:.2f}s"
 retries = str(record["retry_count"]) if record["retry_count"] > 0 else "-"
 error = record["error"][:40] + "..." if record["error"] else "-"

 history_table.add_row(time_str, status, duration, retries, error)

 self.console.print(history_table)
 self.console.print()

 # Show recommendations
 recommendations = self.analytics.get_recommendations(task_name)

 panel = Panel(
 "\n".join(recommendations),
 title=" Recommendations",
 border_style="green",
 padding=(1, 2),
 )

 self.console.print(panel)

 def show_live_monitor(self, refresh_rate: int = 2) -> None:
 """Display a live-updating dashboard (Ctrl+C to exit).

 Args:
 refresh_rate: Refresh interval in seconds
 """
 self._check_rich()

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
 """Generate the live dashboard view."""
 stats = self.analytics.get_all_stats()

 table = Table(
 title=f" AutoCron Live Dashboard - {datetime.now().strftime('%H:%M:%S')}",
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
 else:
 for task_stat in stats:
 status = (
 ""
 if task_stat["success_rate"] >= 95
 else "️" if task_stat["success_rate"] >= 80 else ""
 )
 last_run = datetime.fromisoformat(task_stat["last_run"])
 time_ago = self._format_time_ago(last_run)

 table.add_row(
 task_stat["task_name"],
 str(task_stat["total_runs"]),
 f"{task_stat['success_rate']:.1f}%",
 f"{task_stat['avg_duration']:.1f}s",
 time_ago,
 status,
 )

 return table

 def _format_time_ago(self, dt: datetime) -> str:
 """Format a datetime as 'time ago' string.

 Args:
 dt: Datetime to format

 Returns:
 Human-readable time ago string
 """
 now = datetime.now()
 diff = now - dt

 if diff < timedelta(minutes=1):
 return "just now"
 elif diff < timedelta(hours=1):
 mins = int(diff.total_seconds() / 60)
 return f"{mins}m ago"
 elif diff < timedelta(days=1):
 hours = int(diff.total_seconds() / 3600)
 return f"{hours}h ago"
 else:
 days = diff.days
 return f"{days}d ago"

 def export_stats(self, output_file: Optional[str] = None) -> None:
 """Export all statistics to a JSON file.

 Args:
 output_file: Path to output file. Defaults to autocron_stats.json
 """
 if output_file is None:
 output_file = "autocron_stats.json"

 stats = self.analytics.get_all_stats()

 with open(output_file, "w") as f:
 json.dump(stats, f, indent=2, default=str)

 if self.console:
 self.console.print(f"[green] Stats exported to {output_file}[/green]")
 else:
 print(f" Stats exported to {output_file}")


# Convenience functions
def show_dashboard() -> None:
 """Show the task summary dashboard."""
 dashboard = Dashboard()
 dashboard.show_summary()


def show_task(task_name: str) -> None:
 """Show detailed stats for a specific task.

 Args:
 task_name: Name of the task to display
 """
 dashboard = Dashboard()
 dashboard.show_task_details(task_name)


def live_monitor(refresh_rate: int = 2) -> None:
 """Start the live monitoring dashboard.

 Args:
 refresh_rate: Refresh interval in seconds
 """
 dashboard = Dashboard()
 dashboard.show_live_monitor(refresh_rate)
