"""Tests for task persistence (save/load functionality)."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from autocron.core.scheduler import AutoCron, SchedulingError


class TestTaskPersistence:
 """Test task save and load functionality."""

 @pytest.fixture
 def scheduler(self):
 """Create a scheduler instance."""
 return AutoCron()

 @pytest.fixture
 def test_script(self, tmp_path):
 """Create a test script."""
 script = tmp_path / "test_script.py"
 script.write_text("print('Hello from script')\n")
 return str(script)

 def test_save_tasks_yaml(self, scheduler, test_script, tmp_path):
 """Test saving tasks to YAML file."""
 # Add tasks
 scheduler.add_task(name="task1", script=test_script, every="5m")
 scheduler.add_task(name="task2", script=test_script, cron="0 * * * *", retries=3)

 # Save tasks
 save_path = tmp_path / "tasks.yaml"
 result_path = scheduler.save_tasks(str(save_path))

 assert result_path == str(save_path)
 assert save_path.exists()

 # Verify YAML content
 with open(save_path, "r") as f:
 data = yaml.safe_load(f)

 assert "version" in data
 assert "saved_at" in data
 assert "tasks" in data
 assert len(data["tasks"]) == 2

 # Verify task data
 task1_data = next(t for t in data["tasks"] if t["name"] == "task1")
 assert task1_data["script"] == test_script
 assert task1_data["schedule_type"] == "interval"
 assert task1_data["schedule_value"] == "5m"
 assert task1_data["retries"] == 0

 task2_data = next(t for t in data["tasks"] if t["name"] == "task2")
 assert task2_data["schedule_type"] == "cron"
 assert task2_data["schedule_value"] == "0 * * * *"
 assert task2_data["retries"] == 3

 def test_save_tasks_json(self, scheduler, test_script, tmp_path):
 """Test saving tasks to JSON file."""
 # Add task
 scheduler.add_task(name="task1", script=test_script, every="10m")

 # Save tasks
 save_path = tmp_path / "tasks.json"
 result_path = scheduler.save_tasks(str(save_path))

 assert result_path == str(save_path)
 assert save_path.exists()

 # Verify JSON content
 with open(save_path, "r") as f:
 data = json.load(f)

 assert "version" in data
 assert "saved_at" in data
 assert "tasks" in data
 assert len(data["tasks"]) == 1

 def test_save_tasks_default_location(self, scheduler, test_script):
 """Test saving tasks to default location."""
 scheduler.add_task(name="task1", script=test_script, every="5m")

 # Save to default location
 result_path = scheduler.save_tasks()

 # Should save to ~/.autocron/tasks.yaml
 expected_path = Path.home() / ".autocron" / "tasks.yaml"
 assert result_path == str(expected_path)
 assert expected_path.exists()

 # Cleanup
 expected_path.unlink()

 def test_save_tasks_skips_function_tasks(self, scheduler, test_script):
 """Test that function-based tasks are skipped during save."""
 # Add script task
 scheduler.add_task(name="script_task", script=test_script, every="5m")

 # Add function task
 def my_func():
 print("Hello")

 scheduler.add_task(name="func_task", func=my_func, every="10m")

 # Save tasks
 with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
 temp_path = f.name

 try:
 scheduler.save_tasks(temp_path)

 # Verify only script task was saved
 with open(temp_path, "r") as f:
 data = yaml.safe_load(f)

 assert len(data["tasks"]) == 1
 assert data["tasks"][0]["name"] == "script_task"

 finally:
 os.unlink(temp_path)

 def test_save_tasks_unsupported_format(self, scheduler, test_script):
 """Test saving tasks with unsupported format."""
 scheduler.add_task(name="task1", script=test_script, every="5m")

 with pytest.raises(SchedulingError, match="Unsupported file format"):
 scheduler.save_tasks("tasks.txt")

 def test_load_tasks_yaml(self, scheduler, test_script, tmp_path):
 """Test loading tasks from YAML file."""
 # Create YAML file
 tasks_data = {
 "version": "1.0",
 "saved_at": "2025-10-27T12:00:00",
 "tasks": [
 {
 "task_id": "test-id-1",
 "name": "task1",
 "script": test_script,
 "schedule_type": "interval",
 "schedule_value": "5m",
 "retries": 2,
 "retry_delay": 60,
 "timeout": None,
 "notify": None,
 "email_config": None,
 "enabled": True,
 "last_run": None,
 "next_run": None,
 "run_count": 0,
 "fail_count": 0,
 }
 ],
 }

 load_path = tmp_path / "tasks.yaml"
 with open(load_path, "w") as f:
 yaml.dump(tasks_data, f)

 # Load tasks
 count = scheduler.load_tasks(str(load_path))

 assert count == 1
 assert len(scheduler.tasks) == 1

 task = scheduler.get_task(name="task1")
 assert task is not None
 assert task.name == "task1"
 assert task.script == test_script
 assert task.schedule_type == "interval"
 assert task.schedule_value == "5m"
 assert task.retries == 2

 def test_load_tasks_json(self, scheduler, test_script, tmp_path):
 """Test loading tasks from JSON file."""
 # Create JSON file
 tasks_data = {
 "version": "1.0",
 "saved_at": "2025-10-27T12:00:00",
 "tasks": [
 {
 "task_id": "test-id-1",
 "name": "task1",
 "script": test_script,
 "schedule_type": "cron",
 "schedule_value": "0 * * * *",
 "retries": 0,
 "retry_delay": 60,
 "timeout": None,
 "notify": None,
 "email_config": None,
 "enabled": True,
 "last_run": None,
 "next_run": None,
 "run_count": 0,
 "fail_count": 0,
 }
 ],
 }

 load_path = tmp_path / "tasks.json"
 with open(load_path, "w") as f:
 json.dump(tasks_data, f)

 # Load tasks
 count = scheduler.load_tasks(str(load_path))

 assert count == 1
 task = scheduler.get_task(name="task1")
 assert task.schedule_type == "cron"
 assert task.schedule_value == "0 * * * *"

 def test_load_tasks_with_state(self, scheduler, test_script, tmp_path):
 """Test loading tasks with execution state."""
 # Create tasks with state
 tasks_data = {
 "version": "1.0",
 "saved_at": "2025-10-27T12:00:00",
 "tasks": [
 {
 "task_id": "test-id-1",
 "name": "task1",
 "script": test_script,
 "schedule_type": "interval",
 "schedule_value": "5m",
 "retries": 0,
 "retry_delay": 60,
 "timeout": None,
 "notify": None,
 "email_config": None,
 "enabled": True,
 "last_run": "2025-10-27T11:00:00",
 "next_run": "2025-10-27T11:05:00",
 "run_count": 10,
 "fail_count": 2,
 }
 ],
 }

 load_path = tmp_path / "tasks.yaml"
 with open(load_path, "w") as f:
 yaml.dump(tasks_data, f)

 # Load tasks
 scheduler.load_tasks(str(load_path))

 task = scheduler.get_task(name="task1")
 assert task.run_count == 10
 assert task.fail_count == 2
 assert task.last_run is not None
 assert task.next_run is not None

 def test_load_tasks_merge_with_existing(self, scheduler, test_script, tmp_path):
 """Test loading tasks merges with existing tasks."""
 # Add existing task
 scheduler.add_task(name="existing_task", script=test_script, every="5m")

 # Create file with new task
 tasks_data = {
 "version": "1.0",
 "saved_at": "2025-10-27T12:00:00",
 "tasks": [
 {
 "task_id": "test-id-1",
 "name": "new_task",
 "script": test_script,
 "schedule_type": "interval",
 "schedule_value": "10m",
 "retries": 0,
 "retry_delay": 60,
 "timeout": None,
 "notify": None,
 "email_config": None,
 "enabled": True,
 "last_run": None,
 "next_run": None,
 "run_count": 0,
 "fail_count": 0,
 }
 ],
 }

 load_path = tmp_path / "tasks.yaml"
 with open(load_path, "w") as f:
 yaml.dump(tasks_data, f)

 # Load tasks (merge mode)
 count = scheduler.load_tasks(str(load_path), replace=False)

 assert count == 1
 assert len(scheduler.tasks) == 2 # Both tasks present
 assert scheduler.get_task(name="existing_task") is not None
 assert scheduler.get_task(name="new_task") is not None

 def test_load_tasks_replace_existing(self, scheduler, test_script, tmp_path):
 """Test loading tasks replaces existing tasks."""
 # Add existing tasks
 scheduler.add_task(name="task1", script=test_script, every="5m")
 scheduler.add_task(name="task2", script=test_script, every="10m")

 # Create file with different task
 tasks_data = {
 "version": "1.0",
 "saved_at": "2025-10-27T12:00:00",
 "tasks": [
 {
 "task_id": "test-id-1",
 "name": "task3",
 "script": test_script,
 "schedule_type": "interval",
 "schedule_value": "15m",
 "retries": 0,
 "retry_delay": 60,
 "timeout": None,
 "notify": None,
 "email_config": None,
 "enabled": True,
 "last_run": None,
 "next_run": None,
 "run_count": 0,
 "fail_count": 0,
 }
 ],
 }

 load_path = tmp_path / "tasks.yaml"
 with open(load_path, "w") as f:
 yaml.dump(tasks_data, f)

 # Load tasks (replace mode)
 count = scheduler.load_tasks(str(load_path), replace=True)

 assert count == 1
 assert len(scheduler.tasks) == 1 # Only new task
 assert scheduler.get_task(name="task1") is None
 assert scheduler.get_task(name="task2") is None
 assert scheduler.get_task(name="task3") is not None

 def test_load_tasks_skip_duplicates(self, scheduler, test_script, tmp_path):
 """Test loading tasks skips duplicates."""
 # Add existing task
 scheduler.add_task(name="task1", script=test_script, every="5m")

 # Create file with same task name
 tasks_data = {
 "version": "1.0",
 "saved_at": "2025-10-27T12:00:00",
 "tasks": [
 {
 "task_id": "test-id-1",
 "name": "task1", # Duplicate name
 "script": test_script,
 "schedule_type": "interval",
 "schedule_value": "10m",
 "retries": 0,
 "retry_delay": 60,
 "timeout": None,
 "notify": None,
 "email_config": None,
 "enabled": True,
 "last_run": None,
 "next_run": None,
 "run_count": 0,
 "fail_count": 0,
 }
 ],
 }

 load_path = tmp_path / "tasks.yaml"
 with open(load_path, "w") as f:
 yaml.dump(tasks_data, f)

 # Load tasks (merge mode)
 count = scheduler.load_tasks(str(load_path), replace=False)

 assert count == 0 # Skipped duplicate
 assert len(scheduler.tasks) == 1 # Only original task

 def test_load_tasks_file_not_found(self, scheduler):
 """Test loading tasks from non-existent file."""
 with pytest.raises(SchedulingError, match="Task file not found"):
 scheduler.load_tasks("nonexistent.yaml")

 def test_load_tasks_invalid_format(self, scheduler, tmp_path):
 """Test loading tasks with invalid format."""
 # Create invalid file
 load_path = tmp_path / "invalid.yaml"
 with open(load_path, "w") as f:
 yaml.dump({"invalid": "data"}, f)

 with pytest.raises(SchedulingError, match="Invalid task file format"):
 scheduler.load_tasks(str(load_path))

 def test_load_tasks_unsupported_format(self, scheduler, tmp_path):
 """Test loading tasks with unsupported format."""
 # Create a file with unsupported extension
 load_path = tmp_path / "tasks.txt"
 load_path.write_text("some content")

 with pytest.raises(SchedulingError, match="Unsupported file format"):
 scheduler.load_tasks(str(load_path))

 def test_save_and_load_roundtrip(self, scheduler, test_script, tmp_path):
 """Test full save and load roundtrip."""
 # Add tasks
 scheduler.add_task(name="task1", script=test_script, every="5m", retries=2)
 scheduler.add_task(name="task2", script=test_script, cron="0 * * * *", timeout=300)

 # Save tasks
 save_path = tmp_path / "tasks.yaml"
 scheduler.save_tasks(str(save_path))

 # Create new scheduler and load tasks
 new_scheduler = AutoCron()
 count = new_scheduler.load_tasks(str(save_path))

 assert count == 2
 assert len(new_scheduler.tasks) == 2

 # Verify tasks match
 task1 = new_scheduler.get_task(name="task1")
 assert task1.script == test_script
 assert task1.schedule_value == "5m"
 assert task1.retries == 2

 task2 = new_scheduler.get_task(name="task2")
 assert task2.schedule_value == "0 * * * *"
 assert task2.timeout == 300
