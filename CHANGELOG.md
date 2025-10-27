# Changelog

All notable changes to AutoCron will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-10-27

### Added - 🎯 Hero Feature: Dashboard & Analytics
- **Interactive Dashboard**: Beautiful terminal dashboard with rich formatting
- **Task Analytics**: Automatic execution tracking for all tasks
  - Success/failure rates with visual indicators (✅⚠️❌)
  - Average execution duration tracking
  - Retry pattern analysis
  - Last 100 executions stored in JSON database (~/.autocron/analytics.json)
- **CLI Commands**:
  - `autocron dashboard` - View task summary with metrics
  - `autocron dashboard --live` - Real-time monitoring with auto-refresh
  - `autocron stats <task>` - Detailed task analysis
  - `autocron stats --export file.json` - Export analytics to JSON
- **Smart Recommendations**: AI-powered suggestions based on execution patterns
  - Low success rate warnings
  - High retry rate detection
  - Long duration alerts
  - Recent failure pattern analysis
- **Programmatic API**:
  - `show_dashboard()` - Display summary in code
  - `show_task(name)` - Show specific task details
  - `live_monitor()` - Start live monitoring
  - `Dashboard` and `TaskAnalytics` classes for custom integrations

### Changed
- Scheduler now automatically tracks all task executions
- Added optional `[dashboard]` extras for rich dependency
- Added optional `[all]` extras for all optional features
- Updated `__init__.py` to export dashboard functions
- Version bumped to 1.1.0

### Documentation
- Added `dashboard_example.py` demonstrating the feature
- Updated README with dashboard showcase (pending)
- Added dashboard feature to comparison table

### Technical Details
- Zero-impact design: Analytics tracking fails silently to never break tasks
- Optional dependency: Dashboard requires `rich>=13.0.0`
- Storage: JSON-based analytics at `~/.autocron/analytics.json`
- Performance: Minimal overhead (<1ms per task execution)

## [1.0.2] - 2025-10-26

### Fixed
- Fixed missing exports in `__init__.py`
- Added `start_scheduler`, `get_global_scheduler`, `reset_global_scheduler` to public API
- Fixed isort formatting issues

## [1.0.1] - 2025-10-26

### Fixed
- Security updates for dependencies
- Updated tqdm to 4.66.5 (from 4.65.0)
- Updated black to 24.8.0 (from 23.7.0)

## [1.0.0] - 2025-10-25

### Added
- Initial release of AutoCron
- Cross-platform task scheduling (Windows, Linux, macOS)
- Support for interval-based scheduling (`5m`, `1h`, etc.)
- Support for cron expressions
- Decorator-based function scheduling
- Script scheduling capabilities
- Automatic retry mechanism with exponential backoff
- Comprehensive logging system
- Desktop notifications (via plyer)
- Email notifications (SMTP)
- Configuration file support (YAML)
- Command-line interface (CLI)
- OS-native scheduler integration (Windows Task Scheduler, cron)
- Timeout support for task execution
- Success/failure callbacks
- Full type hints and mypy support
- Comprehensive test suite (>90% coverage)
- CI/CD pipeline with GitHub Actions
- Support for Python 3.10, 3.11, 3.12, 3.13

### Documentation
- Complete README with examples
- API documentation
- Contributing guidelines
- Multiple usage examples
- Configuration file examples

### Infrastructure
- GitHub Actions workflows for CI/CD
- Automated testing on all platforms
- Code quality checks (black, flake8, mypy, pylint)
- Security scanning
- Automated PyPI publishing
- Code coverage reporting

## [Unreleased]

### Planned Features
- Web dashboard with Flask/FastAPI (optional)
- Real-time WebSocket updates for dashboard
- Enhanced cron parsing and validation
- Task dependency management
- Distributed scheduling support
- Task dependencies and chains
- Distributed task execution
- More notification channels (Slack, Discord, etc.)
- Task execution history and analytics
- Rate limiting and throttling
- Resource usage monitoring
- Plugin system for extensibility

---

## Version History

### Version Numbering

AutoCron follows semantic versioning:
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Support Policy

- Latest major version: Full support
- Previous major version: Security fixes only
- Older versions: No support

### Migration Guides

#### Upgrading to 1.0.0

First release - no migration needed!

---

For more information, visit our [GitHub repository](https://github.com/mdshoaibuddinchanda/autocron).
