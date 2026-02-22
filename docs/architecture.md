# Architecture & Design

Understanding AutoCron's internal architecture and design principles.

## ️ High-Level Architecture

```flow
┌─────────────────────────────────────────────────────────┐
│ User Application                                        │
│ (@schedule decorator or AutoCron class)                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ Core Scheduler                                          │
│ - Task Management                                       │
│ - Thread Pool Executor                                  │
│ - Schedule Calculation                                  │  
└──────┬──────────────┬──────────────┬────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌───────────┐ ┌──────────┐ ┌─────────────┐
│ Logger    │ │ Notifier │ │  OS Adapter │
└───────────┘ └──────────┘ └─────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
 ┌──────────┐ ┌──────────┐ ┌──────────┐
 │ Windows  │ │ Linux    │ │ macOS    │
 │ Adapter  │ │ Adapter  │ │ Adapter  │
 └──────────┘ └──────────┘ └──────────┘
```

## Module Structure

### Core Modules

#### `scheduler.py`

**Purpose:** Main scheduling engine

**Components:**

- `Task` class - Represents a scheduled task
- `AutoCron` class - Main scheduler
- `@schedule` decorator - Convenience decorator
- Global scheduler management

**Key Functions:**

- Task execution with timeout
- Retry logic with exponential backoff
- Thread pool management
- Next run calculation

**Design Patterns:**

- **Singleton**: Global scheduler instance
- **Decorator**: `@schedule` for easy task registration
- **Factory**: Task creation and management

#### `os_adapters.py`

**Purpose:** Platform-specific task scheduling

**Components:**

- `OSAdapter` (ABC) - Base adapter interface
- `WindowsAdapter` - Windows Task Scheduler integration
- `UnixAdapter` - Linux/macOS cron integration

**Key Functions:**

- Create OS-level scheduled tasks
- Remove scheduled tasks
- List existing tasks

**Design Patterns:**

- **Strategy**: Different implementations for each OS
- **Factory**: Adapter selection based on platform
- **Adapter**: Unified interface for different OSes

#### `logger.py`

**Purpose:** Centralized logging

**Components:**

- `get_logger()` - Logger factory function
- `AutoCronLogger` - Custom logger class
- File and console handlers

**Features:**

- Rotating file logs
- Colored console output
- Thread-safe logging
- Configurable log levels

**Design Patterns:**

- **Singleton**: One logger per name
- **Factory**: Logger creation

#### `notifications.py`

**Purpose:** Task notification system

**Components:**

- `NotificationManager` - Main notification handler
- `EmailNotifier` - Email notifications
- `DesktopNotifier` - Desktop notifications

**Features:**

- Desktop notifications (cross-platform)
- Email notifications (SMTP)
- Notification templates
- Error handling

**Design Patterns:**

- **Observer**: Notifies on task events
- **Strategy**: Different notification methods

#### `utils.py`

**Purpose:** Utility functions

**Functions:**

- `parse_interval()` - Convert interval strings to seconds
- `parse_cron()` - Parse cron expressions
- `sanitize_task_name()` - Clean task names
- `is_windows()`, `is_linux()`, `is_macos()` - Platform detection
- `get_platform_info()` - System information

#### `cli.py`

**Purpose:** Command-line interface

**Commands:**

- `autocron schedule` - Schedule from CLI
- `autocron list` - List tasks
- `autocron stop` - Stop tasks
- `autocron logs` - View logs

## Data Flow

### Task Execution Flow

```text
1. User defines task
 @schedule(every='5m')
 def my_task():
 ...

2. Task registered with scheduler
 - Parse schedule expression
 - Create Task object
 - Calculate next run time

3. Scheduler main loop
 - Check which tasks should run
 - Execute ready tasks in thread pool
 - Handle retries on failure
 - Update next run time

4. Task execution
 - Execute in separate thread
 - Apply timeout if configured
 - Catch and log exceptions
 - Trigger callbacks
 - Send notifications

5. Post-execution
 - Log results
 - Update task status
 - Schedule next run
```

### Configuration Loading Flow

```text
1. Load YAML file
 autocron.yaml

2. Parse configuration
 - Tasks section
 - Logging settings
 - Scheduler options

3. Create scheduler
 AutoCron(log_path=..., log_level=...)

4. Register tasks
 For each task in config:
 scheduler.add_task(...)

5. Start scheduler
 scheduler.start()
```

## Threading Model

AutoCron uses Python's `ThreadPoolExecutor` for concurrent task execution:

```python
# Main thread
└─ Scheduler loop (monitors and schedules)
 ├─ Worker thread 1 (executes task A)
 ├─ Worker thread 2 (executes task B)
 ├─ Worker thread 3 (executes task C)
 └─ Worker thread N (up to max_workers)
```

**Benefits:**

- Non-blocking task execution
- Configurable concurrency
- Automatic thread management
- Thread-safe operations

**Considerations:**

- GIL limitations for CPU-bound tasks
- Shared resource access requires locking
- Thread pool size affects memory usage

## Design Principles

### 1. **Simplicity First**

- Minimal API surface
- Sensible defaults
- Clear naming conventions
- No complex configuration required

### 2. **Cross-Platform**

- Abstract OS differences
- Provide unified API
- Handle platform-specific edge cases
- Test on all supported platforms

### 3. **Reliability**

- Retry mechanisms
- Timeout protection
- Exception handling
- Comprehensive logging

### 4. **Extensibility**

- Plugin-friendly architecture
- Callback system
- Custom notifiers
- Easy to subclass

### 5. **Production-Ready**

- Thread-safe operations
- Resource cleanup
- Memory efficient
- Proper error handling

## Security Considerations

### Input Validation

```python
# Task names sanitized
def sanitize_task_name(name: str) -> str:
 return re.sub(r'[^\w\-]', '_', name)

# Script paths validated
if not os.path.exists(script):
 raise ValueError(f"Script not found: {script}")
```

### Safe Subprocess Execution

```python
# nosec comments for security scanners
result = subprocess.run( # nosec B603
 [sys.executable, script],
 timeout=timeout,
 check=True
)
```

### Credential Management

- Never log passwords
- Environment variables recommended
- No plaintext storage

## Performance Characteristics

### Time Complexity

- Task registration: O(1)
- Task lookup: O(1)
- Schedule check: O(n) where n = number of tasks
- Task execution: O(1) per task

### Space Complexity

- Memory per task: ~1-2 KB
- Thread overhead: ~8 MB per thread
- Log file: Configurable with rotation

### Optimization Strategies

1. **Lazy Loading**: Load tasks only when needed
2. **Efficient Scheduling**: Binary heap for next-run calculation
3. **Thread Pooling**: Reuse threads instead of creating new ones
4. **Batch Operations**: Group OS adapter calls

## Testing Strategy

### Unit Tests

- Individual function testing
- Mock external dependencies
- Edge case coverage
- Platform-specific tests

### Integration Tests

- End-to-end workflows
- Multi-task scenarios
- OS adapter integration
- Configuration loading

### Platform Tests

```python
@pytest.mark.windows
def test_windows_adapter():
 ...

@pytest.mark.linux
def test_unix_adapter():
 ...
```

## Extension Points

### Custom Notifiers

```python
class CustomNotifier:
 def notify(self, message: str):
 # Your notification logic
 pass

# Use it
scheduler.add_task(
 name="task",
 func=my_func,
 notifier=CustomNotifier()
)
```

### Custom OS Adapters

```python
class CustomAdapter(OSAdapter):
 def create_task(self, ...):
 # Your implementation
 pass
```

### Custom Task Types

```python
class CustomTask(Task):
 def execute(self):
 # Custom execution logic
 return super().execute()
```

## Scalability

### Vertical Scaling

- Increase `max_workers` for more parallelism
- Optimize task execution time
- Use efficient data structures

### Horizontal Scaling

- Run multiple scheduler instances
- Use distributed locking (Redis, etc.)
- Share configuration via network storage

### Limitations

- Single-machine by default
- No built-in distributed locking
- Shared state via global variables

## New in v1.2.0: Async & Persistence Architecture

### Async/Await Support

**Module:** `scheduler.py` (enhanced)

**Implementation:**

```python
# Automatic async detection
if inspect.iscoroutinefunction(func):
 return self._execute_async_function(func, timeout)
else:
 return self._execute_sync_function(func, timeout)
```

**Key Components:**

- `_execute_async_function()` - Handles async execution with `asyncio.run()`
- Event loop management - Isolated loops for each async task
- Timeout support via `asyncio.wait_for()`
- Mixed execution - Both sync and async in same scheduler

**Design Decisions:**

- Use `asyncio.run()` for clean isolation
- No shared event loops (avoids complexity)
- Automatic detection (zero config)
- Full backward compatibility

### Task Persistence

**New Methods:**

- `Task.to_dict()` - Serialize task to dictionary
- `Task.from_dict()` - Deserialize task from dictionary
- `AutoCron.save_tasks()` - Save all tasks to YAML/JSON
- `AutoCron.load_tasks()` - Load tasks from file

**Storage Format:**

```yaml
version: "1.0"
saved_at: "2025-10-27T15:30:00"
tasks:
 - task_id: "unique-id"
 name: "task_name"
 script: "/path/to/script.py"
 schedule_type: "interval"
 schedule_value: "1h"
 retries: 3
 run_count: 145
 last_run: "2025-10-27T14:00:00"
 next_run: "2025-10-27T15:00:00"
```

**Design Decisions:**

- Only script-based tasks (functions can't be serialized)
- Both YAML and JSON supported
- State preservation (run counts, schedules, etc.)
- Merge and replace modes for loading
- Default location: `~/.autocron/tasks.yaml`

**Data Flow:**

1. User calls `scheduler.save_tasks()`
2. Iterate through `self.tasks`
3. Call `task.to_dict()` on each task
4. Serialize to YAML/JSON with metadata
5. Write to file with atomic operations

### Dashboard & Analytics (v1.1.0)

**Module:** `dashboard.py`

**Components:**

- `TaskAnalytics` - Execution data storage and analysis
- `Dashboard` - Rich terminal UI rendering
- JSON storage at `~/.autocron/analytics.json`

**Integration:**

- Scheduler calls `analytics.record_execution()` after each task
- Fail-safe design - analytics never breaks tasks
- Last 100 executions stored per task
- Smart recommendations based on patterns

## Future Enhancements

Potential areas for improvement:

1. **Distributed Scheduling**

- Multi-node support
- Shared task queue
- Leader election

1. **Advanced Scheduling**

- Dependencies between tasks
- Conditional execution
- Dynamic schedules

1. **Monitoring**

- Prometheus metrics
- Health check endpoints
- Performance dashboards

1. **Storage Backends**

- Database storage for tasks
- Redis for state management
- S3 for log archiving

## References

- [Design Patterns](https://refactoring.guru/design-patterns)
- [Python Threading](https://docs.python.org/3/library/threading.html)
- [Cron Expression Format](https://en.wikipedia.org/wiki/Cron)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)

---

**Want to contribute?** See [Development Guide](development.md) and [Contributing Guide](../CONTRIBUTING.md)
