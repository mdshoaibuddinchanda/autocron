"""
Persistence Example - Save and Load Tasks

This example demonstrates how to persist tasks across system restarts.
AutoCron v1.2+ supports saving tasks to YAML/JSON and loading them back.

Key Features:
- Save all script-based tasks to a file
- Load tasks from a file (merge or replace mode)
- Preserve task state (run counts, schedules, etc.)
- Support for both YAML and JSON formats
"""

import time
from pathlib import Path

from autocron import AutoCron

# Example: Create tasks and save them


def example_save_tasks():
    """Demonstrate saving tasks."""
    print("=== Example 1: Saving Tasks ===\n")

    # Create scheduler
    scheduler = AutoCron()

    # Create example scripts
    scripts_dir = Path("example_scripts")
    scripts_dir.mkdir(exist_ok=True)

    # Backup script
    backup_script = scripts_dir / "backup.py"
    backup_script.write_text(
        """
import datetime
print(f"Running backup at {datetime.datetime.now()}")
# Your backup logic here
"""
    )

    # Cleanup script
    cleanup_script = scripts_dir / "cleanup.py"
    cleanup_script.write_text(
        """
import datetime
print(f"Running cleanup at {datetime.datetime.now()}")
# Your cleanup logic here
"""
    )

    # Add tasks
    scheduler.add_task(
        name="daily_backup",
        script=str(backup_script),
        cron="0 2 * * *",  # 2 AM daily
        retries=3,
        retry_delay=300,
        timeout=3600,
    )

    scheduler.add_task(
        name="weekly_cleanup",
        script=str(cleanup_script),
        cron="0 3 * * 0",  # 3 AM every Sunday
        retries=1,
        timeout=1800,
    )

    scheduler.add_task(
        name="hourly_check",
        script=str(cleanup_script),
        every="1h",
        retries=2,
    )

    print(f"Created {len(scheduler.list_tasks())} tasks")

    # Save to default location (~/.autocron/tasks.yaml)
    path = scheduler.save_tasks()
    print(f"✓ Saved tasks to: {path}\n")

    # Save to custom location (JSON format)
    json_path = "my_tasks.json"
    scheduler.save_tasks(json_path)
    print(f"✓ Saved tasks to: {json_path}\n")


def example_load_tasks():
    """Demonstrate loading tasks."""
    print("=== Example 2: Loading Tasks ===\n")

    # Create new scheduler
    scheduler = AutoCron()

    # Load from default location
    try:
        count = scheduler.load_tasks()
        print(f"✓ Loaded {count} tasks from default location")
        print("Tasks loaded:")
        for task in scheduler.list_tasks():
            print(f"  - {task.name}: {task.schedule_type}={task.schedule_value}")
    except Exception as e:
        print(f"Could not load default tasks: {e}")

    print()


def example_merge_vs_replace():
    """Demonstrate merge vs replace modes."""
    print("=== Example 3: Merge vs Replace Modes ===\n")

    # Create scheduler with some tasks
    scheduler = AutoCron()

    # Create a simple script
    scripts_dir = Path("example_scripts")
    scripts_dir.mkdir(exist_ok=True)
    test_script = scripts_dir / "test.py"
    test_script.write_text("print('test')")

    scheduler.add_task(name="existing_task", script=str(test_script), every="30m")
    print(f"Initial tasks: {len(scheduler.list_tasks())}")

    # Load tasks in merge mode (default)
    try:
        _extracted_from_example_merge_vs_replace_19(
            scheduler,
            False,
            "After merge load: ",
            " loaded, existing tasks preserved)",
        )
    except Exception:
        print("No saved tasks to load")

    # Load tasks in replace mode
    new_scheduler = AutoCron()
    new_scheduler.add_task(name="temp_task", script=str(test_script), every="5m")
    print(f"\nNew scheduler tasks: {len(new_scheduler.list_tasks())}")

    try:
        _extracted_from_example_merge_vs_replace_19(
            new_scheduler,
            True,
            "After replace load: ",
            " loaded, existing tasks cleared)",
        )
    except Exception:
        print("No saved tasks to load")

    print()


# TODO Rename this here and in `example_merge_vs_replace`
def _extracted_from_example_merge_vs_replace_19(arg0, replace, arg2, arg3):
    count = arg0.load_tasks(replace=replace)
    print(f"{arg2}{len(arg0.list_tasks())} tasks")
    print(f"  ({count}{arg3}")


def example_task_state_preservation():
    """Demonstrate preserving task execution state."""
    print("=== Example 4: Task State Preservation ===\n")

    # Create scheduler with a task
    scheduler = AutoCron()

    scripts_dir = Path("example_scripts")
    scripts_dir.mkdir(exist_ok=True)
    test_script = scripts_dir / "counter.py"
    test_script.write_text("print('Running task')")

    scheduler.add_task(name="counter_task", script=str(test_script), every="2s")

    # Run scheduler briefly to accumulate stats
    print("Running scheduler for 10 seconds...")
    scheduler.start(blocking=False)
    time.sleep(10)
    scheduler.stop()

    if task := scheduler.get_task(name="counter_task"):
        print("Task stats before save:")
        _extracted_from_example_task_state_preservation_41(task)
        # Save tasks (preserves state)
        save_path = "tasks_with_state.yaml"
        scheduler.save_tasks(save_path)
        print(f"\n✓ Saved tasks with state to {save_path}")

        # Load into new scheduler
        new_scheduler = AutoCron()
        new_scheduler.load_tasks(save_path)

        if loaded_task := new_scheduler.get_task(name="counter_task"):
            print(f"\nTask stats after load:")
            _extracted_from_example_task_state_preservation_41(loaded_task)
            print("\n✓ Task state successfully preserved!")

    print()


# TODO Rename this here and in `example_task_state_preservation`
def _extracted_from_example_task_state_preservation_41(arg0):
    print(f"  Run count: {arg0.run_count}")
    print(f"  Fail count: {arg0.fail_count}")
    print(f"  Last run: {arg0.last_run}")
    print(f"  Next run: {arg0.next_run}")


def example_persistence_workflow():
    """Real-world persistence workflow."""
    print("=== Example 5: Complete Persistence Workflow ===\n")

    # Initial setup
    scheduler = AutoCron()

    # Create tasks
    scripts_dir = Path("example_scripts")
    scripts_dir.mkdir(exist_ok=True)

    monitor_script = scripts_dir / "monitor.py"
    monitor_script.write_text(
        """
import requests
print("Monitoring service health...")
# Check your services here
"""
    )

    scheduler.add_task(
        name="health_monitor",
        script=str(monitor_script),
        every="5m",
        retries=2,
    )

    # Save configuration
    config_file = "production_tasks.yaml"
    scheduler.save_tasks(config_file)
    print(f"✓ Configuration saved to {config_file}")
    print("  You can now:")
    print("  1. Version control this file")
    print("  2. Deploy it to multiple servers")
    _extracted_from_example_persistence_workflow_33(
        "  3. Load it on system restart", "Simulating system restart...\n"
    )
    # New scheduler loads saved configuration
    production_scheduler = AutoCron()
    count = production_scheduler.load_tasks(config_file)
    print(f"✓ Loaded {count} tasks from {config_file}")
    _extracted_from_example_persistence_workflow_33(
        "✓ System ready to resume scheduling", "Starting scheduler..."
    )
    production_scheduler.start(blocking=False)
    time.sleep(3)
    production_scheduler.stop()
    print("✓ Scheduler running successfully\n")


# TODO Rename this here and in `example_persistence_workflow`
def _extracted_from_example_persistence_workflow_33(arg0, arg1):
    print(arg0)
    print()

    # Simulate system restart
    print(arg1)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AutoCron Task Persistence Examples")
    print("=" * 60 + "\n")

    example_save_tasks()
    example_load_tasks()
    example_merge_vs_replace()
    example_task_state_preservation()
    example_persistence_workflow()

    print("=" * 60)
    print("Examples Complete!")
    print("=" * 60)
