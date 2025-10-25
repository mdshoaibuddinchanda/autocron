# AutoCron Documentation

Welcome to AutoCron documentation!

## 📖 Documentation Pages

- **[Complete Guide](complete-guide.md)** – Comprehensive manual with all examples, production setup, and platform-specific instructions
- **[Quick Start](quickstart.md)** – Get started in 5 minutes
- **[API Reference](api-reference.md)** – Complete API documentation
- **[Installation Guide](installation.md)** – Detailed installation instructions
- **[Architecture](architecture.md)** – How AutoCron works internally
- **[FAQ](faq.md)** – Frequently asked questions

## Quick Links

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Examples](../examples/)
- [Contributing](../CONTRIBUTING.md)
- [Changelog](../CHANGELOG.md)

## Installation

### Using pip

```bash
pip install autocron
```

### With notifications support

```bash
pip install autocron[notifications]
```

### From source

```bash
git clone https://github.com/mdshoaibuddinchanda/autocron.git
cd autocron
pip install -e .
```

## Quick Start

### 1. Schedule a Function

```python
from autocron import schedule, start_scheduler

@schedule(every='5m')
def my_task():
    print("Running every 5 minutes!")

if __name__ == '__main__':
    start_scheduler()
```

### 2. Schedule a Script

```python
from autocron import AutoCron

scheduler = AutoCron()
scheduler.add_task(
    name='backup',
    script='backup.py',
    every='1h'
)
scheduler.start()
```

### 3. Using Cron Expressions

```python
@schedule(cron='0 9 * * *')  # Daily at 9 AM
def daily_report():
    print("Generating report...")
```

## Core Concepts

### Scheduling Methods

**Interval-based:**
- `'30s'` - Every 30 seconds
- `'5m'` - Every 5 minutes
- `'2h'` - Every 2 hours
- `'1d'` - Every day

**Cron-based:**
- `'0 9 * * *'` - Daily at 9 AM
- `'*/15 * * * *'` - Every 15 minutes
- `'0 0 * * 0'` - Weekly on Sunday

### Features

- ✅ Cross-platform (Windows, Linux, macOS)
- ✅ Zero configuration required
- ✅ Automatic retries with exponential backoff
- ✅ Comprehensive logging
- ✅ Desktop and email notifications
- ✅ Timeout support
- ✅ Type hints and mypy support
- ✅ CLI interface

## API Reference

### AutoCron Class

```python
class AutoCron:
    def __init__(
        self,
        log_path: Optional[str] = None,
        log_level: str = "INFO",
        max_workers: int = 4,
        use_os_scheduler: bool = False
    )
```

**Methods:**

- `add_task()` - Add a scheduled task
- `remove_task()` - Remove a task
- `get_task()` - Get task by ID or name
- `list_tasks()` - List all tasks
- `start()` - Start the scheduler
- `stop()` - Stop the scheduler

### schedule Decorator

```python
@schedule(
    every: Optional[str] = None,
    cron: Optional[str] = None,
    retries: int = 0,
    retry_delay: int = 60,
    timeout: Optional[int] = None,
    notify: Optional[Union[str, List[str]]] = None,
    on_success: Optional[Callable] = None,
    on_failure: Optional[Callable] = None
)
```

## Configuration File

Create `autocron.yaml`:

```yaml
tasks:
  - name: data_sync
    script: sync.py
    schedule: "*/30 * * * *"
    retries: 3
    notify: desktop

logging:
  level: INFO
  path: ./logs/autocron.log
```

Load with:

```python
scheduler = AutoCron.from_config('autocron.yaml')
scheduler.start()
```

## CLI Usage

```bash
# Schedule a script
autocron schedule script.py --every 5m --retries 3

# List tasks
autocron list

# Stop a task
autocron stop task_name

# View logs
autocron logs task_name --lines 100

# Start from config
autocron start --config autocron.yaml
```

## Advanced Usage

### Retry Mechanism

```python
scheduler.add_task(
    name='api_call',
    func=call_api,
    every='5m',
    retries=5,
    retry_delay=60  # Exponential backoff from 60s
)
```

### Notifications

```python
# Desktop notifications
scheduler.add_task(
    name='monitor',
    func=check_system,
    every='1m',
    notify='desktop'
)

# Email notifications
scheduler.add_task(
    name='backup',
    func=backup_data,
    cron='0 2 * * *',
    notify='email',
    email_config={
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'from_email': 'backup@example.com',
        'to_email': 'admin@example.com',
        'password': os.environ['EMAIL_PASSWORD']
    }
)
```

### Callbacks

```python
def on_success_callback():
    print("Task completed successfully!")

def on_failure_callback(error):
    print(f"Task failed: {error}")
    # Send alert, log to monitoring system, etc.

scheduler.add_task(
    name='critical_task',
    func=important_function,
    every='10m',
    on_success=on_success_callback,
    on_failure=on_failure_callback
)
```

### Timeouts

```python
scheduler.add_task(
    name='long_task',
    func=potentially_long_running,
    every='1h',
    timeout=300  # 5 minutes max
)
```

## Best Practices

### 1. Use Environment Variables for Secrets

```python
import os

email_config = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'from_email': os.environ['EMAIL_FROM'],
    'password': os.environ['EMAIL_PASSWORD']
}
```

### 2. Implement Proper Error Handling

```python
def my_task():
    try:
        # Your task logic
        pass
    except SpecificException as e:
        # Handle specific errors
        logging.error(f"Specific error: {e}")
        raise
    except Exception as e:
        # Handle general errors
        logging.error(f"Unexpected error: {e}")
        raise
```

### 3. Use Absolute Paths for Scripts

```python
import os

script_path = os.path.abspath('path/to/script.py')
scheduler.add_task(name='task', script=script_path, every='5m')
```

### 4. Monitor Logs Regularly

```python
# Enable detailed logging
scheduler = AutoCron(log_level='DEBUG')

# Review logs
logger = get_logger()
recent_logs = logger.get_recent_logs(lines=100)
```

### 5. Test Tasks Before Scheduling

```python
# Test your function first
result = my_task()
assert result is not None

# Then schedule it
@schedule(every='5m')
def my_task():
    # Task logic
    pass
```

## Troubleshooting

### Task Not Running

1. Check if scheduler is started: `scheduler.start()`
2. Verify task schedule: `print(task.next_run)`
3. Check logs: `autocron logs task_name`
4. Verify task is enabled: `task.enabled`

### Import Errors

```bash
# Install with all dependencies
pip install autocron[notifications]

# Verify installation
python -c "import autocron; print(autocron.__version__)"
```

### Permission Errors (Unix/Linux)

```bash
# Check crontab permissions
crontab -l

# Ensure Python executable is accessible
which python
```

### Platform-Specific Issues

**Windows:**
- Run as Administrator for Task Scheduler access
- Check Windows Event Viewer for errors

**Linux/macOS:**
- Verify cron service is running: `service cron status`
- Check system logs: `journalctl -u cron`

## Performance Tips

### 1. Optimize Task Execution

```python
# Use max_workers for concurrent execution
scheduler = AutoCron(max_workers=8)

# Set reasonable timeouts
scheduler.add_task(func=task, every='5m', timeout=300)
```

### 2. Efficient Logging

```python
# Use appropriate log levels
scheduler = AutoCron(log_level='INFO')  # Not DEBUG in production

# Rotate logs regularly
logger = AutoCronLogger(max_bytes=10*1024*1024, backup_count=5)
```

### 3. Resource Management

```python
def efficient_task():
    # Clean up resources
    try:
        # Task logic
        pass
    finally:
        # Cleanup code
        pass
```

## Examples

See the [examples](../examples/) directory for:

- `simple_schedule.py` - Basic usage with decorators
- `advanced_scheduling.py` - Advanced features
- `script_scheduling.py` - Scheduling Python scripts
- `config_example.py` - Using configuration files

## Support

- 📖 [Documentation](https://autocron.readthedocs.io)
- 🐛 [Bug Reports](https://github.com/mdshoaibuddinchanda/autocron/issues)
- 💬 [Discussions](https://github.com/mdshoaibuddinchanda/autocron/discussions)
- 📧 Email: mdshoaibuddinchanda@gmail.com

## License

MIT License - see [LICENSE](../LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

---

Made with ❤️ by the AutoCron team
