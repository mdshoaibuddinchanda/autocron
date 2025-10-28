# Test Coverage Improvement Roadmap
## From 62% to 85%+ Enterprise-Grade Coverage

**Current Status**: 62.5% coverage (685/1096 lines)  
**Target**: ≥85% coverage (931+ lines)  
**Gap**: 246+ lines to cover

---

## 📊 Module-by-Module Breakdown

### Priority 1: CRITICAL (Production Blockers)

#### 1. **scheduler.py** - 78% → 90%+ (12% gap)
**Missing Coverage (105 lines)**:

- ✅ **Safe Mode Tests** (Created: `test_scheduler_coverage.py`)
  - Memory limit enforcement
  - CPU limit enforcement
  - Output sanitization
  - Subprocess isolation
  - Resource limit error handling

- ✅ **Concurrent Timeout Handling** (Created)
  - Multiple tasks with different timeouts
  - Max workers limit enforcement
  - Thread cleanup verification

- ✅ **YAML Persistence Edge Cases** (Created)
  - Special characters in task names
  - None values handling
  - Corrupted YAML files
  - Missing required fields
  - Duplicate task names
  - JSON format support
  - Function vs script task warnings

- ✅ **Error Handling Paths** (Created)
  - Invalid cron expressions
  - Both func and script provided
  - Neither func nor script
  - Both interval and cron
  - Script not found
  - Script execution errors
  - Async function timeouts

- ⚠️ **OS Scheduler Integration** (Partially covered)
  - Windows Task Scheduler registration
  - Unix cron integration
  - Notification setup edge cases

- ⚠️ **Lifecycle Management** (Partially covered)
  - Starting already running scheduler
  - Stopping not running scheduler
  - Thread cleanup verification

**Impact**: HIGH - Core execution engine, security-critical

---

#### 2. **notifications.py** - 67% → 85%+ (18% gap)
**Missing Coverage (31 lines)**:

- ✅ **Desktop Notifications** (Created: `test_notifications_coverage.py`)
  - Successful sending
  - Plyer import failures
  - Notification exceptions

- ✅ **Email Notifications** (Created)
  - SMTP connection success/failure
  - Authentication failures
  - Multiple recipients
  - Email formatting

- ✅ **NotificationManager** (Created)
  - Multi-channel notifications
  - Unknown channel handling
  - Error handling in notifiers
  - Task success/failure notifications
  - Scheduler error notifications
  - Singleton pattern verification

**Impact**: MEDIUM - Nice-to-have for production monitoring

---

#### 3. **logger.py** - 84% → 90%+ (6% gap)
**Missing Coverage (13 lines)**:

- ⚠️ **Untested Methods**:
  - `debug()` method (line 99)
  - `critical()` method (line 115)
  - `exception()` method (line 119)
  - `get_log_file_path()` method (line 166)
  - `clear_logs()` method (lines 188-193)
  - `get_recent_logs()` edge cases (lines 182-184)

**Quick Wins**:
```python
# test_logger_coverage.py
def test_debug_logging():
    logger = get_logger(log_level="DEBUG")
    logger.debug("Debug message")
    # Verify in log file

def test_critical_logging():
    logger = get_logger()
    logger.critical("Critical error")

def test_exception_logging():
    logger = get_logger()
    try:
        raise ValueError("Test")
    except ValueError:
        logger.exception("Exception occurred")

def test_get_log_file_path():
    logger = get_logger(log_path="test.log")
    path = logger.get_log_file_path()
    assert path == "test.log"

def test_clear_logs(tmp_path):
    log_file = tmp_path / "test.log"
    logger = get_logger(log_path=str(log_file))
    logger.info("Test message")
    logger.clear_logs()
    # Verify file cleared
```

**Impact**: LOW - Logging utility, not critical

---

### Priority 2: MEDIUM (Quality Enhancements)

#### 4. **utils.py** - 87% → 95%+ (8% gap)
**Missing Coverage (11 lines)**:

- Lines 81-82: `validate_cron_expression` exception handling
- Line 197: `get_next_run_time` edge case
- Lines 242, 244-245: `safe_import` exception handling
- Lines 258-260: `SingletonMeta.__call__` method
- Lines 288-289: `get_default_log_path` exception handling

**Quick Wins**:
```python
def test_validate_cron_invalid_expression():
    assert not validate_cron_expression("invalid")

def test_singleton_metaclass():
    class TestSingleton(metaclass=SingletonMeta):
        pass
    instance1 = TestSingleton()
    instance2 = TestSingleton()
    assert instance1 is instance2

def test_safe_import_failure():
    result = safe_import("nonexistent.module", "Class")
    assert result is None

def test_get_default_log_path_error():
    with patch("pathlib.Path.mkdir", side_effect=OSError):
        # Should handle error gracefully
```

**Impact**: MEDIUM - Utility functions, quality of life

---

#### 5. **dashboard.py** - 28% → 80%+ (52% gap)
**Missing Coverage (157 lines)**:

- ⚠️ **Dashboard Class** (0% coverage):
  - All methods untested: `show_summary()`, `show_task_details()`, `show_live_monitor()`
  - Helper functions: `_generate_live_view()`, `_format_time_ago()`, `export_stats()`

- ⚠️ **TaskAnalytics**:
  - `get_task_stats()` (lines 128-143)
  - `get_all_stats()` (lines 162-166)
  - `get_recommendations()` (lines 177-216)

**Testing Strategy**:
```python
# test_dashboard_coverage.py
@pytest.mark.skipif(not RICH_AVAILABLE, reason="rich not installed")
class TestDashboard:
    def test_show_summary(self, capsys):
        dashboard = Dashboard(scheduler)
        dashboard.show_summary()
        output = capsys.readouterr()
        assert "AutoCron" in output.out

    def test_show_task_details(self):
        # Test task details display

    def test_show_live_monitor(self):
        # Test live monitoring

    def test_export_stats(self, tmp_path):
        # Test exporting statistics
```

**Impact**: LOW - Optional feature, not core functionality

---

#### 6. **os_adapters.py** - 29% → 75%+ (46% gap)
**Missing Coverage (87 lines)**:

- ⚠️ **WindowsAdapter** (18% coverage):
  - `create_scheduled_task()` (lines 107-157)
  - `remove_scheduled_task()` (lines 161-170)
  - `task_exists()` (lines 201-202)
  - `_generate_task_xml()` (line 208)

- ⚠️ **UnixAdapter** (0% coverage):
  - All methods untested

**Testing Strategy** (Platform-specific):
```python
@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
class TestWindowsAdapter:
    def test_create_task(self):
        # Test Windows Task Scheduler integration

@pytest.mark.skipif(sys.platform == "win32", reason="Unix only")
class TestUnixAdapter:
    def test_crontab_create(self):
        # Test crontab integration
```

**Impact**: LOW - Platform-specific features, not always used

---

#### 7. **__init__.py** - 46% → 85%+ (39% gap)
**Missing Coverage (7 lines)**:

- Lines 23-29: Dashboard import fallback

**Quick Win**:
```python
def test_init_imports():
    # Test all exports
    from autocron import AutoCron, schedule, Task
    assert AutoCron is not None
    assert schedule is not None
    assert Task is not None

def test_dashboard_import_fallback():
    # Test optional dashboard import
```

**Impact**: TRIVIAL - Import statements

---

## 📈 Implementation Timeline

### Week 1: Critical Path (scheduler.py → 90%)
- **Day 1-2**: Run new test suite (`test_scheduler_coverage.py`)
- **Day 3**: Fix any failures, add missing edge cases
- **Day 4-5**: Run new notification tests (`test_notifications_coverage.py`)

### Week 2: Medium Priority (utils, logger → 90%+)
- **Day 1-2**: Implement logger coverage tests
- **Day 3-4**: Implement utils coverage tests
- **Day 5**: Run full test suite, verify 75%+ coverage

### Week 3: Optional (dashboard, os_adapters)
- **Day 1-3**: Dashboard tests (if rich available)
- **Day 4-5**: OS adapter tests (platform-specific)

---

## 🎯 Success Criteria

✅ **Phase 1 (Critical)** - Required for 9.5/10:
- scheduler.py: ≥90% coverage
- notifications.py: ≥85% coverage
- logger.py: ≥90% coverage
- **Total**: ≥75% coverage

✅ **Phase 2 (Enterprise)** - Required for production:
- utils.py: ≥95% coverage
- All core modules: ≥85% coverage
- **Total**: ≥85% coverage

⭐ **Phase 3 (Excellence)** - Stretch goal:
- dashboard.py: ≥80% coverage
- os_adapters.py: ≥75% coverage
- **Total**: ≥90% coverage

---

## 🚀 Quick Start

### Run New Tests:
```powershell
# Run scheduler coverage tests
pytest tests/test_scheduler_coverage.py -v --cov=autocron.scheduler

# Run notification coverage tests
pytest tests/test_notifications_coverage.py -v --cov=autocron.notifications

# Run full coverage report
pytest --cov=autocron --cov-report=html --cov-report=term-missing

# View detailed HTML report
start htmlcov/index.html
```

### Check Progress:
```powershell
# Current coverage
pytest --cov=autocron --cov-report=term | Select-String "TOTAL"

# Target: "TOTAL ... 85%"
```

---

## 📋 Next Steps

1. ✅ **Created Files**:
   - `tests/test_scheduler_coverage.py` (360+ lines, 15+ test classes)
   - `tests/test_notifications_coverage.py` (250+ lines, 10+ test classes)

2. **Run Tests**:
   ```powershell
   pytest tests/test_scheduler_coverage.py -v
   pytest tests/test_notifications_coverage.py -v
   ```

3. **Measure Impact**:
   ```powershell
   pytest --cov=autocron --cov-report=term
   ```

4. **Expected Results**:
   - scheduler.py: 78% → 88%+ (+10%)
   - notifications.py: 67% → 83%+ (+16%)
   - **Total: 62% → 76%+** (+14%)

5. **Remaining Work**:
   - Add logger tests (6% gap) → Total: 80%+
   - Add utils tests (8% gap) → Total: 85%+

---

## 💡 Key Insights

**Why These Tests Matter**:
1. **Safe Mode Tests**: Security-critical - prevents resource abuse
2. **Timeout Handling**: Reliability-critical - prevents hanging tasks
3. **Persistence Tests**: Data integrity - ensures task state survival
4. **Notification Tests**: Monitoring-critical - alerts on failures

**Enterprise Reviewers Will Check**:
- ✅ Resource limit enforcement (security)
- ✅ Concurrent execution handling (scalability)
- ✅ Error recovery paths (reliability)
- ✅ Data persistence integrity (durability)

**Coverage ≠ Quality, but**:
- 85%+ coverage signals: "We've thought about edge cases"
- Comprehensive tests signal: "We've handled error paths"
- Well-organized tests signal: "This code is maintainable"

---

## 🎓 Coverage Philosophy

> "100% coverage doesn't mean zero bugs. But 60% coverage definitely means missing critical paths."

**Focus on**:
- ✅ Error handling paths (try/except blocks)
- ✅ Edge cases (empty inputs, None values, special characters)
- ✅ Resource limits (memory, CPU, timeouts)
- ✅ Concurrent execution (race conditions, deadlocks)
- ✅ Data persistence (corruption, missing fields)

**Don't obsess over**:
- ❌ Import statements coverage
- ❌ Platform-specific code on all platforms
- ❌ Unreachable defensive code
- ❌ Third-party library integration (mock instead)

---

**Status**: 🚧 In Progress  
**Next Milestone**: Run new tests → Verify 76%+ coverage → Iterate  
**Final Goal**: 85%+ coverage for production readiness
