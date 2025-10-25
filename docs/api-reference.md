# API Reference

Complete API documentation for AutoCron.

## Core Classes

### AutoCron

Main scheduler class for managing tasks.

```python
class AutoCron:
    def __init__(
        self,
        log_path: Optional[str] = None,
        log_level: str = 'INFO',
        max_workers: int = 5
    )
```

**Parameters:**
- `log_path` (str, optional): Path to log file. Default: `./autocron.log`
- `log_level` (str): Logging level. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `INFO`
- `max_workers` (int): Maximum concurrent tasks. Default: `5`

**Methods:**

#### add_task()

```python
def add_task(
    self,
    name: str,
    func: Optional[Callable] = None,
    script: Optional[str] = None,
    every: Optional[str] = None,
    cron: Optional[str] = None,
    retries: int = 0,
    retry_delay: int = 5,
    timeout: Optional[int] = None,
    notify: Optional[str] = None,
    email_config: Optional[Dict] = None,
    on_success: Optional[Callable] = None,
    on_failure: Optional[Callable] = None,
    **kwargs
) -> str
```

**Parameters:**
- `name` (str): Unique task identifier
- `func` (Callable, optional): Python function to execute
- `script` (str, optional): Python script path to execute
- `every` (str, optional): Interval format (e.g., `'5m'`, `'1h'`, `'30s'`)
- `cron` (str, optional): Cron expression (e.g., `'0 9 * * *'`)
- `retries` (int): Number of retry attempts. Default: `0`
- `retry_delay` (int): Seconds between retries. Default: `5`
- `timeout` (int, optional): Maximum execution time in seconds
- `notify` (str, optional): Notification type: `'desktop'` or `'email'`
- `email_config` (dict, optional): Email configuration dictionary
- `on_success` (Callable, optional): Callback on successful execution
- `on_failure` (Callable, optional): Callback on failed execution

**Returns:** Task ID (str)

**Example:**
```python
scheduler = AutoCron()
task_id = scheduler.add_task(
    name="backup",
    func=backup_data,
    every='1h',
    retries=3,
    notify='desktop'
)
```

#### remove_task()

```python
def remove_task(self, task_id: str) -> bool
```

Remove a scheduled task.

**Parameters:**
- `task_id` (str): Task identifier

**Returns:** `True` if successful, `False` otherwise

#### start()

```python
def start(self, blocking: bool = False) -> None
```

Start the scheduler.

**Parameters:**
- `blocking` (bool): If `True`, blocks until interrupted. Default: `False`

#### stop()

```python
def stop(self) -> None
```

Stop the scheduler gracefully.

#### get_tasks()

```python
def get_tasks(self) -> List[Dict[str, Any]]
```

Get list of all scheduled tasks.

**Returns:** List of task dictionaries

#### from_config()

```python
@classmethod
def from_config(cls, config_path: str) -> 'AutoCron'
```

Create scheduler from YAML configuration file.

**Parameters:**
- `config_path` (str): Path to YAML config file

**Returns:** Configured `AutoCron` instance

---

### Task

Task representation class.

```python
class Task:
    def __init__(
        self,
        name: str,
        func: Optional[Callable],
        script: Optional[str],
        schedule_expr: str,
        retries: int = 0,
        retry_delay: int = 5,
        timeout: Optional[int] = None,
        **kwargs
    )
```

**Attributes:**
- `id` (str): Unique task identifier
- `name` (str): Task name
- `func` (Callable): Function to execute
- `script` (str): Script path to execute
- `schedule_expr` (str): Schedule expression
- `retries` (int): Number of retries
- `last_run` (datetime): Last execution timestamp
- `next_run` (datetime): Next scheduled execution
- `status` (str): Current status

**Methods:**

#### execute()

```python
def execute(self) -> Any
```

Execute the task.

**Returns:** Task execution result

#### should_run()

```python
def should_run(self) -> bool
```

Check if task should run now.

**Returns:** `True` if ready to run

---

## Decorators

### @schedule

Decorator for scheduling functions.

```python
def schedule(
    every: Optional[str] = None,
    cron: Optional[str] = None,
    retries: int = 0,
    retry_delay: int = 5,
    timeout: Optional[int] = None,
    notify: Optional[str] = None,
    email_config: Optional[Dict] = None,
    on_success: Optional[Callable] = None,
    on_failure: Optional[Callable] = None
) -> Callable
```

**Parameters:** Same as `AutoCron.add_task()`

**Example:**
```python
from autocron import schedule

@schedule(every='5m', retries=2)
def my_task():
    print("Task running!")
```

---

## Helper Functions

### start_scheduler()

```python
def start_scheduler(blocking: bool = True) -> None
```

Start the global scheduler with decorated tasks.

**Parameters:**
- `blocking` (bool): Block until interrupted. Default: `True`

### reset_global_scheduler()

```python
def reset_global_scheduler() -> None
```

Reset the global scheduler (useful for testing).

---

## Time Format Utilities

### parse_interval()

```python
def parse_interval(interval: str) -> int
```

Parse interval string to seconds.

**Parameters:**
- `interval` (str): Interval string (e.g., `'5m'`, `'2h'`, `'30s'`)

**Returns:** Seconds (int)

**Example:**
```python
from autocron.utils import parse_interval

seconds = parse_interval('5m')  # Returns 300
```

### parse_cron()

```python
def parse_cron(cron_expr: str) -> croniter
```

Parse cron expression.

**Parameters:**
- `cron_expr` (str): Cron expression

**Returns:** `croniter` object

---

## Logging

### get_logger()

```python
def get_logger(
    name: str = 'autocron',
    log_path: Optional[str] = None,
    log_level: str = 'INFO'
) -> logging.Logger
```

Get configured logger instance.

**Parameters:**
- `name` (str): Logger name. Default: `'autocron'`
- `log_path` (str, optional): Log file path
- `log_level` (str): Logging level. Default: `'INFO'`

**Returns:** Configured logger

---

## Notifications

### NotificationManager

```python
class NotificationManager:
    def __init__(self)
    
    def send_desktop(self, title: str, message: str) -> None
    
    def send_email(
        self,
        subject: str,
        body: str,
        smtp_server: str,
        smtp_port: int,
        from_email: str,
        to_email: str,
        password: str,
        use_tls: bool = True
    ) -> None
```

**Methods:**

#### send_desktop()

Send desktop notification.

**Parameters:**
- `title` (str): Notification title
- `message` (str): Notification body

#### send_email()

Send email notification.

**Parameters:**
- `subject` (str): Email subject
- `body` (str): Email body
- `smtp_server` (str): SMTP server address
- `smtp_port` (int): SMTP port
- `from_email` (str): Sender email
- `to_email` (str): Recipient email
- `password` (str): Email password
- `use_tls` (bool): Use TLS encryption. Default: `True`

---

## Exceptions

### AutoCronError

```python
class AutoCronError(Exception):
    """Base exception for AutoCron"""
```

### TaskExecutionError

```python
class TaskExecutionError(AutoCronError):
    """Raised when task execution fails"""
```

### ScheduleError

```python
class ScheduleError(AutoCronError):
    """Raised when schedule parsing fails"""
```

### OSAdapterError

```python
class OSAdapterError(AutoCronError):
    """Raised when OS adapter operation fails"""
```

---

## Constants

### Time Units

```python
SECOND = 1
MINUTE = 60
HOUR = 3600
DAY = 86400
WEEK = 604800
```

### Task Status

```python
STATUS_PENDING = 'pending'
STATUS_RUNNING = 'running'
STATUS_SUCCESS = 'success'
STATUS_FAILED = 'failed'
```

---

## Type Hints

AutoCron is fully typed. Import types:

```python
from typing import Callable, Optional, Dict, Any, List
from autocron import AutoCron, Task
```

---

## Configuration Schema

YAML configuration file structure:

```yaml
tasks:
  - name: string (required)
    func: string (optional, function name)
    script: string (optional, file path)
    schedule: string (required, cron or interval)
    retries: integer (optional, default: 0)
    retry_delay: integer (optional, default: 5)
    timeout: integer (optional)
    notify: string (optional: 'desktop' or 'email')
    email:
      smtp_server: string
      smtp_port: integer
      from_email: string
      to_email: string
      password: string
      use_tls: boolean (default: true)

logging:
  level: string (default: 'INFO')
  path: string (default: './autocron.log')

scheduler:
  max_workers: integer (default: 5)
```

---

## Version Information

```python
from autocron import __version__, __author__, __email__

print(__version__)  # '1.0.0'
print(__author__)   # 'MD Shoaib Uddin Chanda'
print(__email__)    # 'mdshoaibuddinchanda@gmail.com'
```

---

**Need examples?** Check [Examples Directory](../examples/) or [User Guide](user-guide.md)
