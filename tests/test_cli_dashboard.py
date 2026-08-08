"""CLI and dashboard integration tests using isolated temporary state."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from autocron.interface.cli import _task_from_args, create_parser, main
from autocron.interface.dashboard import Dashboard, TaskAnalytics
from autocron.storage import SQLiteStore


def _script(tmp_path: Path, body: str = "print('ok')") -> Path:
    path = tmp_path / "job.py"
    path.write_text(body, encoding="utf-8")
    return path


def test_cli_schedule_list_run_stats_and_stop(tmp_path, capsys):
    database = tmp_path / "cli.db"
    script = _script(tmp_path)

    assert main(["--database", str(database), "schedule", str(script), "--every", "1h"]) == 0
    output = capsys.readouterr().out
    assert "Scheduled 'job'" in output

    assert main(["--database", str(database), "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["name"] == "job"

    assert main(["--database", str(database), "run", "job", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["success"] is True

    assert main(["--database", str(database), "stats", "job", "--json"]) == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["total_runs"] == 1

    export = tmp_path / "stats.json"
    assert main(["--database", str(database), "stats", "job", "--export", str(export)]) == 0
    assert json.loads(export.read_text(encoding="utf-8"))["task_name"] == "job"
    capsys.readouterr()

    assert main(["--database", str(database), "stop", "job", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["removed"] is True


def test_cli_error_paths_and_empty_commands(tmp_path, capsys):
    database = tmp_path / "errors.db"
    missing = tmp_path / "missing.py"
    assert main(["--database", str(database), "schedule", str(missing), "--every", "1m"]) == 1
    assert "Error scheduling task" in capsys.readouterr().err

    assert main(["--database", str(database), "list"]) == 0
    assert "No scheduled tasks" in capsys.readouterr().out
    assert main(["--database", str(database), "run", "missing"]) == 1
    capsys.readouterr()
    assert main(["--database", str(database), "stop", "missing"]) == 1
    capsys.readouterr()
    assert main(["logs", "--lines", "-1"]) == 1
    assert "non-negative" in capsys.readouterr().err
    assert main(["--database", str(database), "stats", "unknown", "--json"]) == 1
    capsys.readouterr()
    assert main(["--database", str(database), "dashboard", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert main(["--database", str(database), "start"]) == 0
    assert "No enabled tasks" in capsys.readouterr().out
    assert main([]) == 0
    assert "usage:" in capsys.readouterr().out.lower()


def test_cli_duplicate_and_imported_config(tmp_path, capsys):
    database = tmp_path / "duplicate.db"
    script = _script(tmp_path)
    assert main(["--database", str(database), "schedule", str(script), "--every", "1m"]) == 0
    capsys.readouterr()
    assert main(["--database", str(database), "schedule", str(script), "--every", "1m"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_cli_human_views_logs_and_config_start(tmp_path, capsys, monkeypatch):
    database = tmp_path / "human.db"
    script = _script(tmp_path)
    assert main(["--database", str(database), "schedule", str(script), "--every", "1m"]) == 0
    capsys.readouterr()
    assert main(["--database", str(database), "list"]) == 0
    assert "Total tasks" in capsys.readouterr().out
    assert main(["--database", str(database), "dashboard"]) == 0
    capsys.readouterr()
    assert main(["--database", str(database), "stats"]) == 0
    capsys.readouterr()
    assert main(["logs", "--lines", "1"]) == 0
    capsys.readouterr()
    assert main(["--database", str(database), "stop", "job"]) == 0
    assert "Removed task" in capsys.readouterr().out

    config = tmp_path / "config.yaml"
    config.write_text(
        "tasks:\n  - name: imported\n    script: job.py\n    schedule: 1h\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        "autocron.core.scheduler.AutoCron.start",
        lambda self, blocking=True: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert main(["--database", str(database), "start", "--config", str(config)]) == 130
    assert "Imported" in capsys.readouterr().out


def test_task_argument_validation(tmp_path):
    parser = create_parser()
    script = _script(tmp_path)
    for option in (
        ["--retries", "-1"],
        ["--retry-delay", "-1"],
        ["--timeout", "0"],
        ["--max-instances", "0"],
        ["--misfire-grace-time", "-1"],
        ["--max-memory-mb", "0"],
        ["--max-output-bytes", "0"],
    ):
        args = parser.parse_args(["schedule", str(script), "--every", "1m", *option])
        with pytest.raises(ValueError):
            _task_from_args(args)


def test_analytics_json_backend_and_recommendations(tmp_path):
    path = tmp_path / "analytics.json"
    analytics = TaskAnalytics(storage_path=path)
    assert analytics.get_task_stats("none") is None
    assert analytics.get_recommendations("none") == ["No execution history available yet."]
    analytics.record_execution("job", False, 301.0, "boom", retry_count=2)
    analytics.record_execution("job", False, 301.0, "boom", retry_count=1)
    analytics.record_execution("job", False, 301.0, "boom", retry_count=1)
    stats = analytics.get_task_stats("job")
    assert stats and stats["failed_runs"] == 3
    assert analytics.get_recommendations("job")
    assert analytics.get_all_stats()[0]["task_name"] == "job"


def test_sqlite_dashboard_render_and_export(tmp_path, capsys):
    database = tmp_path / "dashboard.db"
    with SQLiteStore(database) as store:
        store.record_execution("job", True, 0.2, timestamp="2026-01-01T00:00:00+00:00")
    analytics = TaskAnalytics(database_path=database)
    dashboard = Dashboard(analytics)
    dashboard.show_summary()
    dashboard.show_task_details("job")
    assert dashboard.show_task_details("missing") is False
    table = dashboard._generate_live_view()
    assert table is not None
    exported = dashboard.export_stats(tmp_path / "export.json")
    assert exported.exists()
    assert "Task Summary" in capsys.readouterr().out or "AutoCron" in capsys.readouterr().out
    analytics.close()


def test_dashboard_validation_and_live_interrupt(tmp_path):
    analytics = TaskAnalytics(database_path=tmp_path / "a.db")
    with pytest.raises(ValueError):
        Dashboard(analytics, database_path=tmp_path / "b.db")
    with pytest.raises(ValueError):
        TaskAnalytics(storage_path=tmp_path / "a.json", database_path=tmp_path / "b.db")
    dashboard = Dashboard(analytics)
    with pytest.raises(ValueError):
        dashboard.show_live_monitor(refresh_rate=0)
    with patch("autocron.interface.dashboard.Live", side_effect=KeyboardInterrupt):
        dashboard.show_live_monitor(refresh_rate=0.01)
    analytics.close()
