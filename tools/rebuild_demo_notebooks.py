"""Build and execute the deterministic AutoCron demonstration notebooks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"


NOTEBOOKS = {
    "01_basic_scheduling.ipynb": [
        ("markdown", "# Basic scheduling\n\nCreate an interval task and inspect its next run."),
        ("code", """from autocron import AutoCron\n\nscheduler = AutoCron(timezone=\"UTC\", log_level=\"WARNING\")\ntask_id = scheduler.add_task(name=\"heartbeat\", func=lambda: None, every=\"5m\")\ntask = scheduler.get_task(task_id=task_id)\nprint(task.name, task.schedule_type, task.schedule_value, task.timezone)\nprint(task.next_run.tzinfo)"""),
    ],
    "02_advanced_features.ipynb": [
        ("markdown", "# Advanced scheduling policies\n\nTimezone, overlap, coalescing, and misfire settings are explicit task policy."),
        ("code", """from autocron.core.scheduler import Task\n\ntask = Task(\n    name=\"etl\", func=lambda: None, every=\"1m\", timezone=\"Europe/London\",\n    overlap_policy=\"queue\", max_instances=2, misfire_grace_time=30, coalesce=False,\n)\nprint(task.timezone, task.overlap_policy, task.max_instances)\nprint(task.misfire_grace_time, task.coalesce)"""),
    ],
    "03_async_tasks.ipynb": [
        ("markdown", "# Async tasks\n\nAsync callables use the same scheduler execution API."),
        ("code", """import asyncio\nfrom autocron import AutoCron\n\nasync def fetch_value():\n    await asyncio.sleep(0)\n    return 42\n\nscheduler = AutoCron(timezone=\"UTC\", log_level=\"WARNING\")\nprint(scheduler._execute_function(fetch_value, timeout=1))"""),
    ],
    "04_persistence.ipynb": [
        ("markdown", "# YAML persistence\n\nScript tasks can be saved and restored across process restarts."),
        ("code", """import tempfile\nfrom pathlib import Path\nfrom autocron import AutoCron\n\nwith tempfile.TemporaryDirectory() as directory:\n    script = Path(directory) / \"job.py\"\n    script.write_text(\"print('job')\", encoding=\"utf-8\")\n    save_path = Path(directory) / \"tasks.yaml\"\n    first = AutoCron(timezone=\"UTC\", log_level=\"WARNING\")\n    first.add_task(name=\"persisted\", script=str(script), every=\"1h\")\n    first.save_tasks(str(save_path))\n    second = AutoCron(timezone=\"UTC\", log_level=\"WARNING\")\n    print(second.load_tasks(str(save_path)), second.get_task(name=\"persisted\").timezone)"""),
    ],
    "05_safe_mode.ipynb": [
        ("markdown", "# Safe-mode subprocess execution\n\nSafe mode isolates script failures and captures bounded output."),
        ("code", """import tempfile\nfrom pathlib import Path\nfrom autocron import AutoCron\n\nwith tempfile.TemporaryDirectory() as directory:\n    script = Path(directory) / \"safe_job.py\"\n    script.write_text(\"print('isolated')\", encoding=\"utf-8\")\n    output = AutoCron(timezone=\"UTC\", log_level=\"WARNING\")._execute_in_safe_mode(str(script), 10, None, None)\n    print(output.strip())"""),
    ],
    "06_dashboard.ipynb": [
        ("markdown", "# Dashboard analytics\n\nExecution history is stored in SQLite and rendered by the optional dashboard."),
        ("code", """import tempfile\nfrom pathlib import Path\nfrom autocron.interface.dashboard import Dashboard, TaskAnalytics\n\nwith tempfile.TemporaryDirectory() as directory:\n    analytics = TaskAnalytics(database_path=Path(directory) / \"analytics.db\")\n    analytics.record_execution(\"report\", True, 0.25, retry_count=0)\n    print(analytics.get_task_stats(\"report\")[\"success_rate\"])\n    print(type(Dashboard(analytics)._generate_live_view()).__name__)\n    analytics.close()"""),
    ],
    "07_notifications.ipynb": [
        ("markdown", "# Notifications\n\nCustom notifiers make notifications testable without desktop or SMTP credentials."),
        ("code", """from autocron.interface.notifications import NotificationManager\n\nclass RecordingNotifier:\n    def __init__(self):\n        self.messages = []\n    def send(self, title, message, **kwargs):\n        self.messages.append((title, message))\n        return True\n\nmanager = NotificationManager()\nnotifier = RecordingNotifier()\nmanager.add_notifier(\"demo\", notifier)\nprint(manager.notify(\"AutoCron\", \"completed\", channels=[\"demo\"]))\nprint(len(notifier.messages))"""),
    ],
    "08_cli_and_logging.ipynb": [
        ("markdown", "# CLI and logging\n\nThe CLI exposes the durable task store as scriptable commands."),
        ("code", """import contextlib\nimport io\nimport json\nimport tempfile\nfrom pathlib import Path\nfrom autocron.interface.cli import main\n\nwith tempfile.TemporaryDirectory() as directory:\n    root = Path(directory)\n    script = root / \"job.py\"\n    script.write_text(\"print('cli')\", encoding=\"utf-8\")\n    database = root / \"autocron.db\"\n    main([\"--database\", str(database), \"schedule\", str(script), \"--every\", \"1h\"])\n    captured = io.StringIO()\n    with contextlib.redirect_stdout(captured):\n        main([\"--database\", str(database), \"list\", \"--json\"])\n    print(json.loads(captured.getvalue())[0][\"name\"])"""),
    ],
}


def build_notebook(name: str, cells: list[tuple[str, str]]) -> None:
    notebook = nbformat.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    notebook["cells"] = [
        nbformat.v4.new_markdown_cell(source) if kind == "markdown" else nbformat.v4.new_code_cell(source)
        for kind, source in cells
    ]
    client = NotebookClient(notebook, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
    client.execute()
    # Notebook output is committed as documentation. Remove timestamps and
    # machine-specific temporary paths so diffs stay reproducible across OSes.
    for index, cell in enumerate(notebook.cells):
        cell["id"] = f"cell-{index}"
        cell.get("metadata", {}).pop("execution", None)
        for output in cell.get("outputs", []):
            if "text" in output:
                output["text"] = _sanitize_output(output["text"])
            if "traceback" in output:
                output["traceback"] = [_sanitize_output(line) for line in output["traceback"]]
    (DEMO / name).write_text(nbformat.writes(notebook), encoding="utf-8")


def _sanitize_output(value: str) -> str:
    value = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - ", "<timestamp> - ", value)
    value = re.sub(r"[A-Za-z]:\\Users\\[^\r\n ]+", "<temporary path>", value)
    return re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        "<task id>",
        value,
        flags=re.IGNORECASE,
    )


if __name__ == "__main__":
    DEMO.mkdir(parents=True, exist_ok=True)
    for notebook_name, notebook_cells in NOTEBOOKS.items():
        build_notebook(notebook_name, notebook_cells)
    print(json.dumps({"rebuilt": sorted(NOTEBOOKS)}))
