# Frequently Asked Questions (FAQ)

Common questions and answers about AutoCron.

## General Questions

### What is AutoCron?

AutoCron is a cross-platform Python library for scheduling and automating tasks. It provides a simple API to run Python functions or scripts at specified intervals or times.

### Which platforms are supported?

- **Windows** (7, 8, 10, 11, Server)
- **Linux** (Ubuntu, Debian, Fedora, CentOS, Arch, etc.)
- **macOS** (10.14+)

### What Python versions are supported?

Python 3.10, 3.11, 3.12, 3.13, and 3.14.

### Is AutoCron free?

Yes! AutoCron is open-source and released under the MIT License.

---

## Installation & Setup

### How do I install AutoCron?

```bash
pip install autocron
```

### How do I install with notifications?

```bash
pip install autocron[notifications]
```

### Can I use AutoCron without installing?

Yes, you can run from source:
```bash
git clone https://github.com/mdshoaibuddinchanda/autocron.git
cd autocron
pip install -e .
```

### Do I need admin/root privileges?

No, AutoCron works without admin privileges. However, some OS-level task scheduling features may require elevated permissions.

---

## Usage Questions

### How do I schedule a task every 5 minutes?

```python
from autocron import schedule

@schedule(every='5m')
def my_task():
    print("Runs every 5 minutes")
```

### How do I schedule a task at a specific time?

```python
@schedule(cron='0 9 * * *')  # Every day at 9 AM
def morning_task():
    print("Good morning!")
```

### Can I schedule multiple tasks?

Yes! Just decorate multiple functions:

```python
@schedule(every='1m')
def task1():
    pass

@schedule(every='5m')
def task2():
    pass

@schedule(cron='0 * * * *')
def task3():
    pass
```

### How do I stop a running scheduler?

Press `Ctrl+C` or call `scheduler.stop()`:

```python
scheduler = AutoCron()
# ... add tasks ...
scheduler.start(blocking=False)

# Later:
scheduler.stop()
```

### Can I run tasks in parallel?

Yes, AutoCron uses threading. Configure max workers:

```python
scheduler = AutoCron(max_workers=10)
```

---

## Time Formats

### What interval formats are supported?

- Seconds: `'30s'`
- Minutes: `'5m'`
- Hours: `'2h'`
- Days: `'1d'`

### What cron expressions can I use?

Standard cron format (5 fields):
```
* * * * *
│ │ │ │ └─ Day of week (0-6)
│ │ │ └─── Month (1-12)
│ │ └───── Day of month (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

Examples:
- `'0 9 * * *'` - Every day at 9 AM
- `'*/15 * * * *'` - Every 15 minutes
- `'0 0 * * 0'` - Every Sunday at midnight
- `'0 12 * * 1-5'` - Weekdays at noon

### Can I use both interval and cron?

No, use either `every=` or `cron=`, not both.

---

## Features

### Does AutoCron support retries?

Yes!

```python
@schedule(every='1h', retries=3, retry_delay=60)
def task_with_retries():
    pass
```

### Can I set execution timeouts?

Yes!

```python
@schedule(every='30m', timeout=300)  # 5 minutes
def time_limited_task():
    pass
```

### Does it support notifications?

Yes, desktop and email notifications:

```python
@schedule(every='1h', notify='desktop')
def task_with_notification():
    pass
```

### Can I get notified on success/failure?

Yes, use callbacks:

```python
@schedule(
    every='1h',
    on_success=lambda: print("Success!"),
    on_failure=lambda e: print(f"Failed: {e}")
)
def my_task():
    pass
```

### Can I schedule Python scripts?

Yes!

```python
scheduler.add_task(
    name="backup",
    script='backup.py',
    every='1h'
)
```

---

## Troubleshooting

### My task isn't running

**Check:**
1. Is the scheduler started? (`scheduler.start()`)
2. Is the time format correct?
3. Check logs for errors
4. Verify the task function has no errors

### ImportError: No module named 'autocron'

```bash
# Reinstall
pip install --upgrade autocron

# Or check Python path
python -c "import sys; print(sys.path)"
```

### Task runs but does nothing

- Check if your function has any code
- Verify the function doesn't have errors
- Check logs: `tail -f autocron.log`

### Scheduler stops unexpectedly

- Check for unhandled exceptions
- Use `try/except` in your tasks
- Enable debug logging:
  ```python
  scheduler = AutoCron(log_level='DEBUG')
  ```

### Desktop notifications not working

```bash
# Install notifications support
pip install autocron[notifications]
```

### Email notifications failing

Check:
1. SMTP credentials are correct
2. Port is correct (usually 587 for TLS)
3. Less secure app access enabled (Gmail)
4. Firewall allows outbound SMTP

---

## Performance

### How many tasks can I schedule?

There's no hard limit, but consider:
- System resources
- Task frequency
- Execution time

Typical setups handle hundreds of tasks.

### Does AutoCron use a lot of CPU?

No, AutoCron is lightweight and uses minimal CPU when idle.

### Can I run long-running tasks?

Yes, but use timeouts to prevent hanging:

```python
@schedule(every='1h', timeout=3600)  # 1 hour timeout
def long_task():
    # Long-running code
    pass
```

---

## Configuration

### Can I use a configuration file?

Yes, create `autocron.yaml`:

```yaml
tasks:
  - name: my_task
    script: task.py
    schedule: "*/5 * * * *"
    retries: 3

logging:
  level: INFO
  path: ./logs/autocron.log
```

Load it:
```python
scheduler = AutoCron.from_config('autocron.yaml')
```

### Where are logs stored?

Default: `./autocron.log`

Customize:
```python
scheduler = AutoCron(log_path='/var/log/autocron.log')
```

### How do I change log level?

```python
scheduler = AutoCron(log_level='DEBUG')
```

Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`

---

## Deployment

### Can I run AutoCron in production?

Yes! AutoCron is production-ready.

**Best practices:**
- Use virtual environments
- Set up proper logging
- Configure retries
- Use timeouts
- Monitor with notifications

### How do I run AutoCron as a service?

**Linux (systemd):**
```bash
# Create /etc/systemd/system/autocron.service
sudo systemctl enable autocron
sudo systemctl start autocron
```

**Windows (Task Scheduler):**
```powershell
schtasks /create /tn "AutoCron" /tr "python scheduler.py" /sc onstart
```

**macOS (launchd):**
```bash
# Create ~/Library/LaunchAgents/com.autocron.plist
launchctl load ~/Library/LaunchAgents/com.autocron.plist
```

### Can I use AutoCron with Docker?

Yes! Example Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install autocron
COPY scheduler.py .
CMD ["python", "scheduler.py"]
```

### How do I handle secrets?

Use environment variables:

```python
import os

email_config = {
    'password': os.environ['EMAIL_PASSWORD'],
    'from_email': os.environ['FROM_EMAIL']
}
```

---

## Comparison

### AutoCron vs cron (Linux)

| Feature | AutoCron | cron |
|---------|----------|------|
| Cross-platform | ✅ Yes | ❌ Linux/Unix only |
| Python API | ✅ Yes | ❌ Shell only |
| Retries | ✅ Built-in | ❌ Manual |
| Notifications | ✅ Built-in | ❌ Manual |
| Easy syntax | ✅ Simple | ❌ Complex |

### AutoCron vs APScheduler

| Feature | AutoCron | APScheduler |
|---------|----------|-------------|
| Simplicity | ✅ Very simple | ⚠️ Complex |
| Setup | ✅ Zero config | ⚠️ Requires config |
| Documentation | ✅ Clear | ⚠️ Dense |
| OS Integration | ✅ Native | ❌ None |

### AutoCron vs Celery

| Feature | AutoCron | Celery |
|---------|----------|--------|
| Complexity | ✅ Simple | ❌ Complex |
| Dependencies | ✅ Minimal | ❌ Requires broker |
| Setup time | ✅ Minutes | ❌ Hours |
| Use case | ✅ Scheduling | ✅ Task queue |

---

## New Features (v1.2.0)

### Does AutoCron support async/await?

Yes! As of v1.2.0, you can schedule async functions:

```python
@schedule(every='5m')
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        data = await session.get('https://api.example.com')
        return await data.json()
```

AutoCron automatically detects async functions and executes them properly.

### Can tasks survive system restarts?

Yes! Use task persistence (v1.2.0):

```python
# Save tasks before shutdown
scheduler.save_tasks()  # Saves to ~/.autocron/tasks.yaml

# After restart, load tasks back
scheduler.load_tasks()
scheduler.start()
```

### What's the difference between save_tasks() and from_config()?

- **`save_tasks()`** (v1.2.0) - Saves task configuration AND execution state (run counts, schedules, etc.) to YAML/JSON
- **`from_config()`** - Creates a new scheduler from a static YAML configuration file (configuration only)

Use `save_tasks()` for persistence across restarts, and `from_config()` for initial setup from configuration.

### Can I schedule async and sync tasks together?

Yes! Mix them freely:

```python
@schedule(every='5m')
def sync_task():
    print("Sync task")

@schedule(every='10m')
async def async_task():
    await asyncio.sleep(1)
    print("Async task")
```

### Does the dashboard require additional installation?

Yes, the dashboard requires the `rich` library:

```bash
pip install autocron-scheduler[dashboard]
# or
pip install autocron-scheduler[all]
```

### How do I view the dashboard?

```bash
# CLI
autocron dashboard          # Summary view
autocron stats task_name    # Task details
autocron dashboard --live   # Live monitoring

# Or in Python
from autocron import show_dashboard
show_dashboard()
```

### What data does the dashboard track?

- Total runs and success/failure rates
- Average execution duration
- Retry patterns and failure analysis
- Last 100 executions with timestamps
- Smart recommendations based on patterns

### Can I export analytics data?

Yes:

```bash
autocron stats --export analytics.json
```

Or programmatically:

```python
from autocron.dashboard import TaskAnalytics

analytics = TaskAnalytics()
stats = analytics.get_task_stats("my_task")
```

### Why can't I persist function-based tasks?

Functions contain code and closures that can't be serialized. Only script-based tasks can be saved:

```python
# ❌ Can't be persisted
@schedule(every='1h')
def my_function():
    pass

# ✅ Can be persisted
scheduler.add_task(
    name="my_task",
    script="my_script.py",
    every="1h"
)
```

For production, use scripts for tasks that need persistence.

---

## Development

### Can I contribute to AutoCron?

Yes! See [CONTRIBUTING.md](../CONTRIBUTING.md)

### How do I report bugs?

[Open an issue](https://github.com/mdshoaibuddinchanda/autocron/issues)

### Where can I ask questions?

- [GitHub Discussions](https://github.com/mdshoaibuddinchanda/autocron/discussions)
- [GitHub Issues](https://github.com/mdshoaibuddinchanda/autocron/issues)

### Is there a community?

Join us on:
- GitHub Discussions
- Issue tracker

---

## Still Have Questions?

- 📖 [Documentation](README.md)
- 💬 [GitHub Discussions](https://github.com/mdshoaibuddinchanda/autocron/discussions)
- 🐛 [Report Issues](https://github.com/mdshoaibuddinchanda/autocron/issues)
- 📧 Email: mdshoaibuddinchanda@gmail.com
