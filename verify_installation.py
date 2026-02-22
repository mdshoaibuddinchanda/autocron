"""
Quick verification script for AutoCron installation.

Run this script to verify that AutoCron is correctly installed
and working on your system.
"""

import importlib
import platform
import sys
from typing import List, Tuple


def print_header(text: str) -> None:
 """Print section header."""
 print(f"\n{'='*60}")
 print(f" {text}")
 print("=" * 60)


def check_python_version() -> bool:
 """Check Python version."""
 print_header("Python Version Check")
 version = sys.version_info
 print(f"Python version: {version.major}.{version.minor}.{version.micro}")

 if version >= (3, 10):
 print(" Python version is compatible")
 return True
 else:
 print(" Python 3.10+ required")
 return False


def check_platform() -> bool:
 """Check platform compatibility."""
 print_header("Platform Check")
 system = platform.system()
 print(f"Operating System: {system}")
 print(f"Platform: {platform.platform()}")
 print(f"Machine: {platform.machine()}")

 if system in ["Windows", "Linux", "Darwin"]:
 print(f" Platform '{system}' is supported")
 return True
 else:
 print(f" Platform '{system}' may not be fully supported")
 return False


def check_dependencies() -> Tuple[bool, List[str]]:
 """Check required dependencies."""
 print_header("Dependencies Check")

 # Map package names to import names
 required = {"croniter": "croniter", "psutil": "psutil", "pyyaml": "yaml", "tqdm": "tqdm"}

 platform_specific = {
 "Windows": {"pywin32": "win32api"},
 "Linux": {"python-crontab": "crontab"},
 "Darwin": {"python-crontab": "crontab"},
 }

 optional = ["plyer"]

 missing = []

 # Check required dependencies
 print("\nRequired dependencies:")
 for package_name, import_name in required.items():
 try:
 importlib.import_module(import_name)
 print(f" {package_name}")
 except ImportError:
 print(f" {package_name} - MISSING")
 missing.append(package_name)

 # Check platform-specific dependencies
 system = platform.system()
 if system in platform_specific:
 print(f"\nPlatform-specific dependencies ({system}):")
 for package_name, import_name in platform_specific[system].items():
 try:
 importlib.import_module(import_name)
 print(f" {package_name}")
 except ImportError:
 print(f" {package_name} - MISSING")
 missing.append(package_name)

 # Check optional dependencies
 print("\nOptional dependencies:")
 for package in optional:
 try:
 importlib.import_module(package)
 print(f" {package}")
 except ImportError:
 print(f" {package} - Not installed (optional)")

 return not missing, missing


def check_autocron_import() -> bool:
 """Check AutoCron import."""
 print_header("AutoCron Import Check")

 try:
 import autocron

 print(" AutoCron imported successfully")
 print(f" Version: {autocron.__version__}")
 return True
 except ImportError as e:
 print(f" Failed to import AutoCron: {e}")
 return False


def check_autocron_components() -> bool:
 """Check AutoCron components."""
 print_header("AutoCron Components Check")

 components = {
 "AutoCron": "autocron.AutoCron",
 "schedule": "autocron.schedule",
 "Task": "autocron.scheduler.Task",
 "Logger": "autocron.logger.AutoCronLogger",
 "Notifier": "autocron.notifications.NotificationManager",
 "Utils": "autocron.utils",
 "OS Adapters": "autocron.os_adapters",
 }

 all_ok = True
 for name, import_path in components.items():
 try:
 parts = import_path.split(".")
 module = importlib.import_module(".".join(parts[:-1]))
 if len(parts) > 1 and hasattr(module, parts[-1]):
 print(f" {name}")
 else:
 print(f" {name} module")
 except Exception as e:
 print(f" {name}: {e}")
 all_ok = False

 return all_ok


def run_basic_test() -> bool:
 """Run basic functionality test."""
 print_header("Basic Functionality Test")

 try:
 from autocron import AutoCron

 # Create scheduler
 print(" Creating scheduler...")
 scheduler = AutoCron(log_level="ERROR")
 print(" Scheduler created")

 # Add a simple task
 print(" Adding task...")
 executed = []

 def test_task():
 executed.append(True)

 task_id = scheduler.add_task(name="test_task", func=test_task, every="1s")
 print(f" Task added (ID: {task_id[:8]}...)")

 # Verify task
 task = scheduler.get_task(task_id=task_id)
 if task:
 print(f" Task retrieved: {task.name}")
 else:
 print(" Failed to retrieve task")
 return False

 # Execute task directly
 print(" Executing task...")
 scheduler._execute_task(task)

 if executed:
 print(" Task executed successfully")
 else:
 print(" Task did not execute")
 return False

 # Clean up
 removed = scheduler.remove_task(task_id=task_id)
 if removed:
 print(" Task removed")
 else:
 print(" Failed to remove task")

 print("\n All basic tests passed!")
 return True

 except Exception as e:
 print(f"\n Test failed: {e}")
 import traceback

 traceback.print_exc()
 return False


def print_summary(results: dict) -> None:
 """Print summary of checks."""
 print_header("Summary")

 total = len(results)
 passed = sum(results.values())

 for check, result in results.items():
 status = " PASS" if result else " FAIL"
 print(f" {status} - {check}")

 print(f"\nTotal: {passed}/{total} checks passed")

 if passed == total:
 print("\n All checks passed! AutoCron is ready to use.")
 print("\nNext steps:")
 print(" 1. Read the documentation: docs/index.md")
 print(" 2. Try the examples: examples/")
 print(" 3. Run: python examples/simple_schedule.py")
 else:
 print("\n Some checks failed. Please review the output above.")
 print("\nTo fix:")
 print(" 1. Install missing dependencies: pip install autocron[dev,notifications]")
 print(" 2. Check Python version (3.10+ required)")
 print(" 3. Verify platform compatibility")


def main() -> int:
 """Main verification function."""
 print("\n" + "=" * 60)
 print(" AutoCron Installation Verification")
 print("=" * 60)

 # Run checks
 results = {"Python Version": check_python_version(), "Platform": check_platform()}

 deps_ok, missing = check_dependencies()
 results["Dependencies"] = deps_ok

 if missing:
 print(f"\nMissing dependencies: {', '.join(missing)}")
 print(f"Install with: pip install {' '.join(missing)}")

 results["AutoCron Import"] = check_autocron_import()

 if results["AutoCron Import"]:
 results["Components"] = check_autocron_components()
 results["Basic Test"] = run_basic_test()
 else:
 results["Components"] = False
 results["Basic Test"] = False

 # Print summary
 print_summary(results)

 # Return exit code
 return 0 if all(results.values()) else 1


if __name__ == "__main__":
 sys.exit(main())
