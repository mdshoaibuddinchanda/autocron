"""
Example using configuration file.

This example shows how to configure AutoCron using a YAML file.
"""

from autocron import AutoCron
import sys


def main():
    """Main function."""
    config_file = "autocron.yaml"

    try:
        # Load scheduler from configuration file
        scheduler = AutoCron.from_config(config_file)

        print(f"Loaded configuration from '{config_file}'")
        print(f"\nScheduled {len(scheduler.tasks)} task(s):")

        for task in scheduler.list_tasks():
            print(f"\n  Task: {task.name}")
            print(f"  Schedule: {task.schedule_value}")
            print(f"  Type: {task.schedule_type}")
            if task.script:
                print(f"  Script: {task.script}")

        print("\n" + "=" * 50)
        print("Starting scheduler...")
        print("Press Ctrl+C to stop")
        print("=" * 50 + "\n")

        scheduler.start(blocking=True)

    except KeyboardInterrupt:
        print("\n\nStopping scheduler...")
        scheduler.stop()
        print("Scheduler stopped gracefully.")
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found")
        print("\nCreate a configuration file like:")
        print(
            """
tasks:
  - name: example_task
    script: example.py
    schedule: "*/5 * * * *"
    retries: 3
    notify: desktop

logging:
  level: INFO
  path: ./logs/autocron.log
"""
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
