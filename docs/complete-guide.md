# AutoCron ⏰

[![PyPI version](https://badge.fury.io/py/autocron.svg)](https://badge.fury.io/py/autocron)
[![Python Support](https://img.shields.io/pypi/pyversions/autocron.svg)](https://pypi.org/project/autocron/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](https://github.com/mdshoaibuddinchanda/autocron)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/mdshoaibuddinchanda/autocron/workflows/CI/badge.svg)](https://github.com/mdshoaibuddinchanda/autocron/actions)
[![codecov](https://codecov.io/gh/mdshoaibuddinchanda/autocron/branch/main/graph/badge.svg)](https://codecov.io/gh/mdshoaibuddinchanda/autocron)

**Automate scripts with zero setup. Run Python tasks anytime, anywhere.**

AutoCron is a cross-platform Python library that makes scheduling tasks incredibly simple. No more wrestling with cron syntax or Windows Task Scheduler GUI. Just one line of code.

## ✨ Features

- 🚀 **Zero Configuration** - Schedule tasks in seconds with minimal code
- 🌍 **Cross-Platform** - Works on Windows, Linux, and macOS
- 🔄 **Flexible Scheduling** - Support for intervals, cron expressions, and custom schedules
- ⚡ **Async/Await Support** (v1.2+) - Native async function scheduling
- 💾 **Task Persistence** (v1.2+) - Save and restore tasks across system restarts
- 📊 **Visual Dashboard** (v1.1+) - Monitor tasks with beautiful terminal UI
- 📈 **Smart Analytics** (v1.1+) - Automatic execution tracking and recommendations
- 📊 **Built-in Logging** - Automatic execution tracking and error logging
- 🔔 **Notifications** - Optional email and desktop notifications
- ⚡ **Retry Logic** - Configurable retry mechanisms with exponential backoff
- 🎯 **Type Safe** - Full type hints and mypy support
- 🧪 **Well Tested** - 113 tests, 63% coverage, core at 80%+

## 📦 Installation

```bash
# Basic installation
pip install autocron-scheduler

# With dashboard support
pip install autocron-scheduler[dashboard]

# With all features (recommended)
pip install autocron-scheduler[all]
```

For desktop notifications support:
```bash
pip install autocron-scheduler[notifications]
```

### From Source / Development

If you want to contribute or modify the code:

```bash
# Clone the repository
git clone https://github.com/mdshoaibuddinchanda/autocron.git
cd autocron

# Install dependencies
pip install -r requirements.txt

# For development (includes testing, linting, etc.)
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e .
```

## 🚀 Quick Start

### Schedule a Script

```python
from autocron import schedule

# Run a script every 5 minutes
schedule('myscript.py', every='5m')

# Run every hour with retries
schedule('backup.py', every='1h', retries=3)

# Run at specific times using cron syntax
schedule('report.py', cron='0 9 * * *')  # Every day at 9 AM
```

### Schedule a Function

```python
from autocron import schedule

@schedule(every='30m', retries=2)
def fetch_data():
    """Fetch data every 30 minutes"""
    print("Fetching data...")
    # Your code here

@schedule(cron='0 */2 * * *')
def cleanup_logs():
    """Clean up logs every 2 hours"""
    print("Cleaning logs...")
    # Your code here
```

### Using the Scheduler Class

```python
from autocron import AutoCron

scheduler = AutoCron()

# Add multiple tasks
scheduler.add_task(
    name="data_sync",
    func=sync_data,
    every='15m',
    retries=3,
    notify='desktop'
)

scheduler.add_task(
    name="daily_report",
    script='generate_report.py',
    cron='0 8 * * *',
    notify='email',
    email_config={
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'from_email': 'mdshoaibuddinchanda@gmail.com',
        'to_email': 'recipient@email.com',
        'password': 'your_password'
    }
)

# Start the scheduler
scheduler.start()
```

## 🆕 New in v1.2.0: Async/Await Support

AutoCron now natively supports async functions! Schedule async tasks alongside regular sync tasks seamlessly.

### Basic Async Task

```python
from autocron import schedule
import aiohttp
import asyncio

@schedule(every='5m')
async def fetch_api_data():
    """Async function - runs every 5 minutes"""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.example.com/data') as resp:
            data = await resp.json()
            print(f"Fetched {len(data)} items")
            return data

@schedule(every='10m', retries=2)
async def process_async_batch():
    """Process multiple items concurrently"""
    async def process_item(item_id):
        await asyncio.sleep(0.5)  # Simulate async work
        return f"Processed {item_id}"
    
    # Process 10 items concurrently
    results = await asyncio.gather(
        *[process_item(i) for i in range(10)]
    )
    print(f"Completed: {len(results)} items")
```

### Mixed Sync and Async Tasks

```python
from autocron import AutoCron
import asyncio

scheduler = AutoCron()

# Regular sync task
def sync_backup():
    print("Running sync backup...")
    # Your sync code here

# Async task
async def async_monitor():
    print("Running async monitor...")
    await asyncio.sleep(1)
    # Your async code here

# Both work together!
scheduler.add_task(name="backup", func=sync_backup, every="1h")
scheduler.add_task(name="monitor", func=async_monitor, every="5m")

scheduler.start()
```

### Async with Timeout and Retries

```python
@schedule(every='10m', timeout=60, retries=3)
async def api_with_timeout():
    """Async task with 60-second timeout and 3 retries"""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://slow-api.example.com') as resp:
            return await resp.json()
```

**Key Benefits:**
- ✅ Works with async libraries (aiohttp, asyncpg, httpx, etc.)
- ✅ Efficient I/O-bound task execution
- ✅ No thread blocking for async operations
- ✅ Automatic detection - just use `async def`
- ✅ Full retry and timeout support

See [async_tasks_example.py](../examples/async_tasks_example.py) for more examples.

## 🆕 New in v1.2.0: Task Persistence

Save tasks to disk and restore them after system restarts. Perfect for production deployments!

### Save and Load Tasks

```python
from autocron import AutoCron

scheduler = AutoCron()

# Add tasks
scheduler.add_task(
    name="backup",
    script="backup.py",
    every="1h",
    retries=3
)

scheduler.add_task(
    name="monitor",
    script="monitor.py",
    every="5m"
)

# Save all tasks to file
scheduler.save_tasks()  # Saves to ~/.autocron/tasks.yaml

# Or save to custom location
scheduler.save_tasks("production_tasks.yaml")
scheduler.save_tasks("backup_tasks.json")  # JSON also supported
```

### Load Tasks After Restart

```python
from autocron import AutoCron

# After system restart...
scheduler = AutoCron()

# Load saved tasks
scheduler.load_tasks()  # Loads from ~/.autocron/tasks.yaml

# Merge with existing tasks (default)
scheduler.load_tasks("production_tasks.yaml")

# Or replace all tasks
scheduler.load_tasks("production_tasks.yaml", replace=True)

# Start scheduler - tasks will run as configured
scheduler.start()
```

### Task State is Preserved!

Persistence saves not just configuration, but also execution state:
- ✅ Run counts and fail counts
- ✅ Last run and next run times
- ✅ Schedule configuration
- ✅ Retry settings
- ✅ Notification preferences

**Example saved task (YAML):**
```yaml
version: "1.0"
saved_at: "2025-10-27T15:30:00"
tasks:
  - task_id: "abc-123"
    name: "backup"
    script: "/path/to/backup.py"
    schedule_type: "interval"
    schedule_value: "1h"
    retries: 3
    retry_delay: 60
    timeout: null
    run_count: 145
    fail_count: 2
    last_run: "2025-10-27T14:00:00"
    next_run: "2025-10-27T15:00:00"
    enabled: true
```

**Important Notes:**
- Only **script-based tasks** can be persisted
- Function-based tasks must be registered programmatically (they contain code/closures)
- Both YAML and JSON formats supported
- Perfect for version control and deployment

See [persistence_example.py](../examples/persistence_example.py) for more examples.

## 📊 Dashboard & Analytics (v1.1+)

Monitor your tasks with the built-in dashboard and analytics system.

### CLI Commands

```bash
# View task summary
autocron dashboard

# View specific task details
autocron stats backup_task

# Live monitoring (updates every 2 seconds)
autocron dashboard --live --refresh 2

# Export analytics to file
autocron stats --export analytics.json
```

### Programmatic API

```python
from autocron import show_dashboard, show_task, Dashboard

# Show summary of all tasks
show_dashboard()

# Show detailed task analysis
show_task("backup_task")

# Custom dashboard usage
dashboard = Dashboard()
dashboard.show_summary()
dashboard.show_task_details("backup_task")
```

**Features:**
- ✅ Success/failure rates with visual indicators
- ✅ Average execution duration tracking
- ✅ Retry pattern analysis
- ✅ Smart recommendations (low success, high retries, etc.)
- ✅ Last 100 executions stored
- ✅ Beautiful terminal UI with rich formatting

See [dashboard_example.py](../examples/dashboard_example.py) for more examples.

## 🎛️ Cross-Platform Sample Code

AutoCron works seamlessly across **Windows**, **Linux**, and **macOS**. Here's a complete example that demonstrates common use cases on all platforms:

### Complete Working Example

```python
"""
AutoCron Cross-Platform Example
Works on Windows, Linux, and macOS
"""
from autocron import schedule, AutoCron, start_scheduler
import os
import platform

# ============================================================================
# EXAMPLE 1: Simple Decorator Pattern (Recommended for Quick Tasks)
# ============================================================================

@schedule(every='1m')
def check_system_health():
    """Runs every minute on all platforms"""
    system = platform.system()
    print(f"✓ Health check on {system} - Memory usage checked")

@schedule(cron='0 9 * * *')
def daily_morning_task():
    """Runs daily at 9 AM on all platforms"""
    print(f"📅 Good morning! Running daily task on {platform.system()}")

@schedule(every='30m', retries=3, timeout=60)
def fetch_api_data():
    """Fetch data with retry logic - works on all OS"""
    print("🌐 Fetching API data...")
    # Your API call here

# ============================================================================
# EXAMPLE 2: Using AutoCron Class (Recommended for Complex Projects)
# ============================================================================

def main():
    """Main function showing AutoCron class usage"""
    
    # Create scheduler instance
    scheduler = AutoCron(
        log_path='./logs/autocron.log',  # Works on all platforms
        log_level='INFO',
        max_workers=4
    )
    
    # ========================================================================
    # Task 1: Data Backup (Daily at 2 AM)
    # ========================================================================
    def backup_data():
        """Backup important data - cross-platform paths"""
        system = platform.system()
        
        if system == 'Windows':
            source = 'C:\\Users\\SHOAIIB_CHANDA\\Documents\\data'
            backup = 'C:\\Backups\\data'
        else:  # Linux or macOS
            source = os.path.expanduser('~/Documents/data')
            backup = os.path.expanduser('~/Backups/data')
        
        print(f"💾 Backing up from {source} to {backup}")
        # Your backup logic here
    
    scheduler.add_task(
        name="daily_backup",
        func=backup_data,
        cron='0 2 * * *',  # 2 AM daily
        retries=3,
        notify='desktop'
    )
    
    # ========================================================================
    # Task 2: Log Cleanup (Every Sunday)
    # ========================================================================
    def cleanup_old_logs():
        """Clean old logs - works on all platforms"""
        log_dir = './logs'
        if os.path.exists(log_dir):
            print(f"🧹 Cleaning logs on {platform.system()}")
            # Your cleanup logic here
    
    scheduler.add_task(
        name="weekly_cleanup",
        func=cleanup_old_logs,
        cron='0 0 * * 0',  # Every Sunday midnight
        retries=2
    )
    
    # ========================================================================
    # Task 3: System Monitoring (Every 15 minutes)
    # ========================================================================
    def monitor_system():
        """Monitor system resources - cross-platform"""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            print(f"📊 {platform.system()} - CPU: {cpu}%, Memory: {memory}%")
        except ImportError:
            print("⚠️  Install psutil: pip install psutil")
    
    scheduler.add_task(
        name="system_monitor",
        func=monitor_system,
        every='15m',
        timeout=30
    )
    
    # ========================================================================
    # Task 4: Database Sync (Every 2 hours)
    # ========================================================================
    def sync_database():
        """Sync database - with email notifications"""
        print(f"🔄 Syncing database on {platform.system()}")
        # Your database sync logic here
    
    scheduler.add_task(
        name="db_sync",
        func=sync_database,
        every='2h',
        retries=5,
        retry_delay=60,
        on_success=lambda: print("  ✓ Database sync successful!"),
        on_failure=lambda e: print(f"  ✗ Database sync failed: {e}")
    )
    
    # ========================================================================
    # Task 5: API Health Check (Every 5 minutes)
    # ========================================================================
    def check_api_health():
        """Check API endpoints - works everywhere"""
        endpoints = [
            'https://api.example.com/health',
            'https://api.example.com/status'
        ]
        print(f"🔍 Checking {len(endpoints)} API endpoints...")
        # Your API health check logic here
    
    scheduler.add_task(
        name="api_health",
        func=check_api_health,
        every='5m',
        timeout=15
    )
    
    # Start the scheduler
    print("=" * 70)
    print("🚀 AutoCron Started!")
    print(f"📍 Platform: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {platform.python_version()}")
    print(f"📝 Logs: ./logs/autocron.log")
    print(f"⏰ Tasks: {len(scheduler.tasks)} scheduled")
    print("=" * 70)
    print("\nPress Ctrl+C to stop\n")
    
    scheduler.start(blocking=True)

# ============================================================================
# EXAMPLE 3: Using Decorator Pattern (Simplest Approach)
# ============================================================================

def decorator_example():
    """Quick start with decorator pattern"""
    
    @schedule(every='1m')
    def quick_task():
        print(f"⚡ Quick task on {platform.system()}")
    
    @schedule(cron='0 */2 * * *')
    def hourly_task():
        print(f"⏰ Runs every 2 hours on {platform.system()}")
    
    # Start all decorated tasks
    print("🚀 Starting decorator-based tasks...")
    print("Press Ctrl+C to stop\n")
    start_scheduler(blocking=True)

# ============================================================================
# EXAMPLE 4: Platform-Specific Tasks
# ============================================================================

def platform_specific_example():
    """Handle platform-specific requirements"""
    
    scheduler = AutoCron()
    
    if platform.system() == 'Windows':
        # Windows-specific task
        def windows_task():
            print("🪟 Running Windows-specific task")
            # e.g., Windows Event Log cleanup
        
        scheduler.add_task(
            name="windows_maintenance",
            func=windows_task,
            every='1d'
        )
    
    elif platform.system() == 'Linux':
        # Linux-specific task
        def linux_task():
            print("🐧 Running Linux-specific task")
            # e.g., apt cache cleanup
        
        scheduler.add_task(
            name="linux_maintenance",
            func=linux_task,
            every='1d'
        )
    
    elif platform.system() == 'Darwin':
        # macOS-specific task
        def macos_task():
            print("🍎 Running macOS-specific task")
            # e.g., Homebrew cleanup
        
        scheduler.add_task(
            name="macos_maintenance",
            func=macos_task,
            every='1d'
        )
    
    scheduler.start(blocking=True)

# ============================================================================
# RUN THE EXAMPLE
# ============================================================================

if __name__ == '__main__':
    # Choose which example to run:
    
    # Option 1: Complete example with AutoCron class
    main()
    
    # Option 2: Simple decorator pattern
    # decorator_example()
    
    # Option 3: Platform-specific tasks
    # platform_specific_example()
```

### Running on Different Platforms

**Windows (PowerShell/CMD):**
```powershell
# Install AutoCron
pip install autocron

# Save the example as my_scheduler.py and run
python my_scheduler.py
```

**Linux/macOS (Terminal):**
```bash
# Install AutoCron
pip3 install autocron

# Save the example as my_scheduler.py and run
python3 my_scheduler.py

# Run in background (Linux/macOS)
nohup python3 my_scheduler.py &
```

**As a System Service (Production):**

*Windows (Task Scheduler):*
```powershell
# Create a scheduled task that runs on startup
schtasks /create /tn "AutoCron" /tr "python C:\path\to\my_scheduler.py" /sc onstart /ru SYSTEM
```

*Linux (systemd):*
```bash
# Create /etc/systemd/system/autocron.service
[Unit]
Description=AutoCron Scheduler
After=network.target

[Service]
Type=simple
User=mdshoaibuddinchanda
ExecStart=/usr/bin/python3 /path/to/my_scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable autocron
sudo systemctl start autocron
```

*macOS (launchd):*
```xml
<!-- Create ~/Library/LaunchAgents/com.autocron.scheduler.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.autocron.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/my_scheduler.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>

<!-- Load the service -->
launchctl load ~/Library/LaunchAgents/com.autocron.scheduler.plist
```

### Key Points for Cross-Platform Compatibility

✅ **Use `os.path.join()` or `pathlib.Path`** for file paths  
✅ **Use `os.path.expanduser('~')`** for home directory  
✅ **Use `platform.system()`** to detect OS  
✅ **Test on all target platforms** before deployment  
✅ **Use forward slashes** or raw strings for paths  

## �📖 Time Format Examples

AutoCron supports multiple time format styles:

### Interval-based (simple)
- `'30s'` - Every 30 seconds
- `'5m'` - Every 5 minutes
- `'2h'` - Every 2 hours
- `'1d'` - Every day

### Cron expressions (powerful)
- `'0 9 * * *'` - Every day at 9:00 AM
- `'*/15 * * * *'` - Every 15 minutes
- `'0 0 * * 0'` - Every Sunday at midnight
- `'0 12 * * 1-5'` - Weekdays at noon

### Advanced Configuration

```python
from autocron import AutoCron

scheduler = AutoCron(
    log_path='./logs/autocron.log',
    log_level='INFO',
    max_workers=4
)

scheduler.add_task(
    name="complex_task",
    func=my_function,
    every='1h',
    retries=5,
    retry_delay=60,  # Wait 60 seconds between retries
    timeout=300,  # Maximum 5 minutes per execution
    notify='desktop',
    on_success=lambda: print("Success!"),
    on_failure=lambda e: print(f"Failed: {e}")
)

scheduler.start()
```

## 🎯 Use Cases

- **Data Pipeline Automation** - Schedule ETL jobs, data syncs, and backups
- **Web Scraping** - Periodic data collection from websites
- **System Maintenance** - Log cleanup, cache clearing, health checks
- **Report Generation** - Automated daily/weekly reports
- **API Monitoring** - Regular health checks and status updates
- **Social Media Automation** - Scheduled posts and content updates

## 🛠️ CLI Usage

AutoCron includes a command-line interface:

```bash
# Schedule a script from command line
autocron schedule myscript.py --every 5m --retries 3

# List all scheduled tasks
autocron list

# Stop a scheduled task
autocron stop task_name

# View logs
autocron logs task_name
```

## 📊 Configuration File

Create an `autocron.yaml` file for complex setups:

```yaml
tasks:
  - name: data_sync
    script: sync_data.py
    schedule: "*/30 * * * *"
    retries: 3
    notify: desktop
    
  - name: backup
    script: backup.py
    schedule: "0 2 * * *"
    retries: 5
    notify: email
    email:
      smtp_server: smtp.gmail.com
      smtp_port: 587
      from_email: mdshoaibuddinchanda@gmail.com
      to_email: mdshoaibuddinchanda@gmail.com

logging:
  level: INFO
  path: ./logs/autocron.log

notifications:
  desktop: true
  email: true
```

Load configuration:
```python
from autocron import AutoCron

scheduler = AutoCron.from_config('autocron.yaml')
scheduler.start()
```

## 🧪 Testing

AutoCron is thoroughly tested across all supported platforms:

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=autocron

# Run platform-specific tests
pytest -m linux
pytest -m windows
pytest -m darwin
```

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with modern Python best practices
- Inspired by the simplicity of `schedule` and robustness of `APScheduler`
- Cross-platform compatibility thanks to `python-crontab` and `pywin32`

## 📚 Documentation

Full documentation is available at [https://autocron.readthedocs.io](https://autocron.readthedocs.io)

## 💬 Support

- 📫 Report bugs and request features via [GitHub Issues](https://github.com/mdshoaibuddinchanda/autocron/issues)
- 💡 Discuss ideas in [GitHub Discussions](https://github.com/mdshoaibuddinchanda/autocron/discussions)
- 📖 Read the [Documentation](https://autocron.readthedocs.io)

---

Made with ❤️ by the AutoCron team. Happy Automating! 🎉
