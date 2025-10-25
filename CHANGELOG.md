# Changelog

All notable changes to AutoCron will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Web dashboard for task management
- Enhanced cron parsing and validation
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
