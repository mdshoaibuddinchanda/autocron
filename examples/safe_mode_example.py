"""
Safe Mode Examples - Secure Task Execution with Resource Limits
================================================================

AutoCron's Safe Mode provides sandboxed execution with resource limits
to prevent runaway tasks and protect system resources.

Features:
- Process isolation (subprocess execution)
- Memory limits
- CPU limits (Unix/Linux/Mac)
- Timeout enforcement
- Output sanitization
- Error containment

Use Cases:
- Running untrusted scripts
- Resource-constrained environments
- Production systems with strict SLAs
- Multi-tenant task scheduling
"""

from autocron import AutoCron
import tempfile
import os


# Example 1: Basic Safe Mode
# ===========================
# Enable safe mode to run tasks in isolated subprocesses


def example_1_basic_safe_mode():
    """Basic safe mode execution."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Safe Mode")
    print("=" * 60)

    scheduler = AutoCron()

    # Create a test script
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
import time
print("Running in safe mode...")
time.sleep(1)
print("Task completed successfully!")
"""
        )
        script_path = f.name

    try:
        # Add task with safe mode enabled
        scheduler.add_task(
            name="safe_task",
            script=script_path,
            every="5m",
            safe_mode=True,  # ⚡ Enable safe mode
            timeout=10,
        )

        print("✅ Task added with safe mode enabled")
        print("   - Runs in isolated subprocess")
        print("   - Protected from parent process issues")
        print("   - Output is captured and sanitized")

    finally:
        os.unlink(script_path)


# Example 2: Memory Limits
# =========================
# Prevent memory-hungry tasks from consuming all RAM


def example_2_memory_limits():
    """Enforce memory limits on tasks."""
    print("\n" + "=" * 60)
    print("Example 2: Memory Limits")
    print("=" * 60)

    scheduler = AutoCron()

    # Create a script that uses memory
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
import time
# This task will stay within limits
data = [i for i in range(1000)]
print(f"Processed {len(data)} items")
time.sleep(0.5)
print("Memory usage OK")
"""
        )
        script_path = f.name

    try:
        scheduler.add_task(
            name="memory_limited_task",
            script=script_path,
            every="10m",
            safe_mode=True,
            max_memory_mb=100,  # ⚡ Limit to 100MB
            timeout=30,
        )

        print("✅ Task added with 100MB memory limit")
        print("   - Task will be killed if it exceeds 100MB")
        print("   - Protects system from memory leaks")
        print("   - Ideal for processing large datasets safely")

    finally:
        os.unlink(script_path)


# Example 3: Combined Resource Limits
# ====================================
# Apply both memory and timeout limits


def example_3_combined_limits():
    """Apply multiple resource limits."""
    print("\n" + "=" * 60)
    print("Example 3: Combined Resource Limits")
    print("=" * 60)

    scheduler = AutoCron()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
import requests
import time

# Fetch data from API with limits
print("Fetching API data...")
try:
    response = requests.get('https://api.github.com', timeout=5)
    print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
"""
        )
        script_path = f.name

    try:
        scheduler.add_task(
            name="api_fetcher",
            script=script_path,
            every="15m",
            safe_mode=True,
            max_memory_mb=256,  # 256MB memory limit
            max_cpu_percent=50,  # 50% CPU limit (Unix only)
            timeout=30,  # 30 second timeout
            retries=2,  # Retry on failure
        )

        print("✅ Task added with comprehensive limits:")
        print("   📊 Memory: 256MB max")
        print("   ⚡ CPU: 50% max (Unix/Linux/Mac)")
        print("   ⏱️  Timeout: 30 seconds")
        print("   🔄 Retries: 2 attempts")
        print("\n   Perfect for:")
        print("   - API calls with rate limits")
        print("   - Web scraping tasks")
        print("   - Data processing pipelines")

    finally:
        os.unlink(script_path)


# Example 4: Production Setup with Safe Mode
# ===========================================
# Real-world production configuration


def example_4_production_setup():
    """Production-ready safe mode configuration."""
    print("\n" + "=" * 60)
    print("Example 4: Production Setup")
    print("=" * 60)

    scheduler = AutoCron()

    backup_script = _extracted_from_example_4_production_setup_10(
        """
import os
import tarfile
import time

print("Starting backup...")
# Simulate backup operation
time.sleep(2)
print("Backup completed successfully")
"""
    )
    analytics_script = _extracted_from_example_4_production_setup_10(
        """
import json
import time

print("Processing analytics...")
time.sleep(1)
data = {"users": 1000, "events": 5000}
print(json.dumps(data))
"""
    )
    try:
        # Critical backup task with strict limits
        scheduler.add_task(
            name="nightly_backup",
            script=backup_script.name,
            cron="0 2 * * *",  # 2 AM daily
            safe_mode=True,
            max_memory_mb=512,
            timeout=3600,  # 1 hour max
            retries=3,
            notify="email",
            email_config={
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "from_email": "backup@company.com",
                "to_email": "admin@company.com",
                "password": "app_password",
            },
        )

        # Analytics task with moderate limits
        scheduler.add_task(
            name="hourly_analytics",
            script=analytics_script.name,
            every="1h",
            safe_mode=True,
            max_memory_mb=256,
            timeout=600,  # 10 minutes
            retries=2,
        )

        print("✅ Production tasks configured:")
        print("\n   🔒 Nightly Backup:")
        print("      - Safe mode with 512MB limit")
        print("      - 1 hour timeout")
        print("      - Email notifications")
        print("      - 3 retry attempts")

        print("\n   📊 Hourly Analytics:")
        print("      - Safe mode with 256MB limit")
        print("      - 10 minute timeout")
        print("      - 2 retry attempts")

        print("\n   🎯 Benefits:")
        print("      ✓ Tasks can't crash parent process")
        print("      ✓ Resource usage is controlled")
        print("      ✓ Failures are isolated")
        print("      ✓ System remains stable")

    finally:
        os.unlink(backup_script.name)
        os.unlink(analytics_script.name)


# TODO Rename this here and in `example_4_production_setup`
def _extracted_from_example_4_production_setup_10(arg0):
    # Create production scripts
    result = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    result.write(arg0)
    result.close()

    return result


# Example 5: Safe Mode with Task Persistence
# ===========================================
# Combine safe mode with persistence for reliability


def example_5_safe_mode_with_persistence():
    """Safe mode + persistence for maximum reliability."""
    print("\n" + "=" * 60)
    print("Example 5: Safe Mode + Persistence")
    print("=" * 60)

    scheduler = AutoCron()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
import time
print("Critical task executing...")
time.sleep(1)
print("Task completed")
"""
        )
        script_path = f.name

    try:
        # Add critical task with safe mode
        scheduler.add_task(
            name="critical_task",
            script=script_path,
            every="30m",
            safe_mode=True,
            max_memory_mb=200,
            timeout=300,
            retries=3,
        )

        # Save tasks with safe mode settings
        scheduler.save_tasks()  # Saves to ~/.autocron/tasks.yaml

        print("✅ Task saved with safe mode configuration")
        print("\n   Saved settings:")
        print("   - safe_mode: True")
        print("   - max_memory_mb: 200")
        print("   - timeout: 300")
        print("   - retries: 3")

        print("\n   After system restart:")
        print("   1. Load tasks: scheduler.load_tasks()")
        print("   2. Start scheduler: scheduler.start()")
        print("   3. Safe mode settings are preserved!")

        # Demonstrate loading
        new_scheduler = AutoCron()
        new_scheduler.load_tasks()

        loaded_task = list(new_scheduler.tasks.values())[0]
        print(f"\n   ✓ Loaded task '{loaded_task.name}'")
        print(f"   ✓ Safe mode: {loaded_task.safe_mode}")
        print(f"   ✓ Memory limit: {loaded_task.max_memory_mb}MB")

    finally:
        os.unlink(script_path)


# Example 6: Comparison - Normal vs Safe Mode
# ============================================
# Understand the differences


def example_6_comparison():
    """Compare normal and safe mode execution."""
    print("\n" + "=" * 60)
    print("Example 6: Normal vs Safe Mode")
    print("=" * 60)

    print("\n   NORMAL MODE (safe_mode=False):")
    print("   ✓ Faster execution (no subprocess overhead)")
    print("   ✓ Direct access to parent process")
    print("   ✓ Best for trusted, lightweight tasks")
    print("   ⚠️  No resource limits")
    print("   ⚠️  Errors can affect other tasks")

    print("\n   SAFE MODE (safe_mode=True):")
    print("   ✓ Process isolation")
    print("   ✓ Resource limits enforced")
    print("   ✓ Output sanitization")
    print("   ✓ Error containment")
    print("   ⚠️  Slight overhead (subprocess)")
    print("   ⚠️  Only for script tasks")

    print("\n   📋 WHEN TO USE SAFE MODE:")
    print("   ✅ Running untrusted scripts")
    print("   ✅ Production environments")
    print("   ✅ Tasks with known memory issues")
    print("   ✅ Multi-tenant systems")
    print("   ✅ Critical systems requiring isolation")

    print("\n   📋 WHEN NORMAL MODE IS OK:")
    print("   ✅ Development/testing")
    print("   ✅ Trusted internal scripts")
    print("   ✅ Simple, quick tasks")
    print("   ✅ Function-based tasks (safe mode doesn't apply)")


# Run all examples
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AutoCron Safe Mode Examples")
    print("=" * 60)
    print("\nSafe Mode provides:")
    print("  🔒 Process isolation")
    print("  📊 Memory limits")
    print("  ⚡ CPU limits (Unix)")
    print("  ⏱️  Timeout enforcement")
    print("  🛡️  Output sanitization")
    print("  🔐 Error containment")

    try:
        example_1_basic_safe_mode()
        example_2_memory_limits()
        example_3_combined_limits()
        example_4_production_setup()
        example_5_safe_mode_with_persistence()
        example_6_comparison()

        print("\n" + "=" * 60)
        print("✅ All examples completed!")
        print("=" * 60)
        print("\n💡 Key Takeaways:")
        print("   1. Safe mode = subprocess isolation + resource limits")
        print("   2. Use for untrusted code or production systems")
        print("   3. Combine with persistence for reliability")
        print("   4. Memory/CPU limits protect system resources")
        print("   5. Normal mode is fine for trusted, simple tasks")
        print("\n📚 Next Steps:")
        print("   - Read SECURITY.md for best practices")
        print("   - Run tests: pytest tests/test_safe_mode.py")
        print("   - Check logs for safe mode execution details")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()
