# Quick Start Guide

Get up and running with AutoCron in 5 minutes!

## Your First Scheduled Task

### 1. Install AutoCron

```bash
# Basic installation
pip install autocron-scheduler

# With all features (dashboard, async support)
pip install autocron-scheduler[all]
```

### 2. Create Your First Script

Create a file `my_first_scheduler.py`:

```python
from autocron import schedule, start_scheduler

@schedule(every='1m')
def hello_world():
 """This runs every minute"""
 print("Hello from AutoCron!")

# NEW in v1.2: Async support!
@schedule(every='2m')
async def async_hello():
 """This runs every 2 minutes"""
 import asyncio
 await asyncio.sleep(1)
 print("Hello from async AutoCron!")

if __name__ == '__main__':
 print(" Scheduler started! Press Ctrl+C to stop")
 start_scheduler(blocking=True)
```

### 3. Run It

```bash
python my_first_scheduler.py
```

That's it! Your tasks are now running.

### 4. Monitor Your Tasks (v1.1+)

While your script is running, open a **new terminal** and try:

```bash
autocron dashboard # View task summary
autocron stats hello_world # View task details
```

## Common Patterns

### Every X Time

```python
from autocron import schedule

@schedule(every='30s') # Every 30 seconds
def quick_task():
 print("Runs every 30 seconds")

@schedule(every='5m') # Every 5 minutes
def frequent_task():
 print("Runs every 5 minutes")

@schedule(every='2h') # Every 2 hours
def hourly_task():
 print("Runs every 2 hours")

@schedule(every='1d') # Every day
def daily_task():
 print("Runs once a day")
```

### Cron Expressions

```python
@schedule(cron='0 9 * * *') # Every day at 9 AM
def morning_task():
 print("Good morning!")

@schedule(cron='*/15 * * * *') # Every 15 minutes
def quarter_hourly():
 print("Every 15 minutes")

@schedule(cron='0 12 * * 1-5') # Weekdays at noon
def weekday_lunch():
 print("Lunch time on weekdays!")
```

### With Retries

```python
@schedule(every='1h', retries=3, retry_delay=60)
def reliable_task():
 """Retries up to 3 times if it fails"""
 # Your code here
 print("This task will retry on failure")
```

### With Timeout

```python
@schedule(every='30m', timeout=300)
def time_limited_task():
 """Must complete within 5 minutes"""
 # Your code here
 print("This task has a 5-minute timeout")
```

## Using the Scheduler Class

For more control, use the `AutoCron` class:

```python
from autocron import AutoCron

def my_task():
 print("Task running!")

# Create scheduler
scheduler = AutoCron()

# Add task
scheduler.add_task(
 name="my_task",
 func=my_task,
 every='5m'
)

# Start scheduler
scheduler.start(blocking=True)
```

## Scheduling Scripts

You can also schedule entire Python scripts:

```python
from autocron import AutoCron

scheduler = AutoCron()

# Schedule a script to run every hour
scheduler.add_task(
 name="backup_script",
 script='backup.py',
 every='1h'
)

scheduler.start(blocking=True)
```

## Adding Notifications

Get notified when tasks complete:

```python
from autocron import schedule

@schedule(
 every='1h',
 notify='desktop', # Desktop notification
 on_success=lambda: print(" Success!"),
 on_failure=lambda e: print(f" Failed: {e}")
)
def important_task():
 # Your important code
 pass
```

## Multiple Tasks Example

```python
from autocron import schedule, start_scheduler
import requests

@schedule(every='5m')
def check_website():
 """Check if website is up"""
 try:
 response = requests.get('https://example.com')
 print(f" Website is up! Status: {response.status_code}")
 except Exception as e:
 print(f" Website is down: {e}")

@schedule(cron='0 */2 * * *') # Every 2 hours
def cleanup_logs():
 """Clean up old log files"""
 print(" Cleaning up logs...")
 # Your cleanup code

@schedule(every='1d')
def daily_report():
 """Generate daily report"""
 print(" Generating daily report...")
 # Your report generation code

if __name__ == '__main__':
 print("=" * 50)
 print(" Multi-Task Scheduler Started!")
 print("=" * 50)
 start_scheduler(blocking=True)
```

## ️ Configuration File

For complex setups, use a YAML configuration file:

**`autocron.yaml`:**

```yaml
tasks:
 - name: website_monitor
 func: check_website
 schedule: "*/5 * * * *"
 retries: 3
 
 - name: daily_backup
 script: backup.py
 schedule: "0 2 * * *"
 notify: desktop

logging:
 level: INFO
 path: ./logs/autocron.log
```

**Load and run:**

```python
from autocron import AutoCron

scheduler = AutoCron.from_config('autocron.yaml')
scheduler.start(blocking=True)
```

## Next Steps

Now that you have the basics, explore:

1. **[Tutorial](tutorial.md)** - Detailed walkthrough
2. **[User Guide](user-guide.md)** - Complete documentation
3. **[Examples](../examples/)** - More code samples
4. **[API Reference](api-reference.md)** - Full API docs

## Pro Tips

### Run in Background (Linux/macOS)

```bash
nohup python my_scheduler.py > scheduler.log 2>&1 &
```

### Run as Windows Service

```powershell
schtasks /create /tn "AutoCron" /tr "python C:\path\to\scheduler.py" /sc onstart
```

### Virtual Environment

```bash
python -m venv env
source env/bin/activate # Linux/macOS
pip install autocron
```

## Troubleshooting

**Task not running?**

- Check the time format is correct
- Verify the function has no errors
- Check logs for error messages

**ImportError?**

```bash
pip install --upgrade autocron
```

**Need help?**

- [FAQ](faq.md)
- [GitHub Issues](https://github.com/mdshoaibuddinchanda/autocron/issues)

---

**Ready to dive deeper?** Check out the [Tutorial](tutorial.md)!
