# AutoCron ⏰

[![PyPI version](https://badge.fury.io/py/autocron.svg)](https://badge.fury.io/py/autocron)
[![Python Support](https://img.shields.io/pypi/pyversions/autocron.svg)](https://pypi.org/project/autocron/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](https://github.com/mdshoaibuddinchanda/autocron)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/mdshoaibuddinchanda/autocron/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/mdshoaibuddinchanda/autocron/actions)
[![codecov](https://codecov.io/gh/mdshoaibuddinchanda/autocron/branch/main/graph/badge.svg)](https://codecov.io/gh/mdshoaibuddinchanda/autocron)

**Schedule Python tasks with one line of code. Works everywhere.**

AutoCron makes task scheduling painless—no cron syntax, no platform-specific setup. Just Python.

---

## 🚀 Quick Start

**Install:**
```bash
pip install autocron-scheduler
```

**Schedule a task:**
```python
from autocron import schedule

@schedule(every='5m')
def my_task():
    print("Running every 5 minutes!")
```

That's it. AutoCron handles the rest.

---

## ✨ Why AutoCron?

| Feature | AutoCron | cron/Task Scheduler |
|---------|----------|---------------------|
| 🌍 Cross-platform | ✅ Windows, Linux, macOS | ❌ Platform-specific |
| 💻 Pure Python | ✅ No system config | ❌ Requires system setup |
| 🔄 Retry logic | ✅ Built-in | ❌ Manual implementation |
| 📊 Logging | ✅ Automatic | ❌ Manual setup |
| 🔔 Notifications | ✅ Desktop + Email | ❌ Not included |
| ⚡ Type hints | ✅ Fully typed | N/A |

---

## 📦 Installation

**Basic:**
```bash
pip install autocron-scheduler
```

**With notifications:**
```bash
pip install autocron-scheduler[notifications]
```

**From source:**
```bash
git clone https://github.com/mdshoaibuddinchanda/autocron.git
cd autocron
pip install -e .
```

---

## 💡 Examples

### Simple Decorator

```python
from autocron import schedule

@schedule(every='30m')
def fetch_data():
    # Runs every 30 minutes
    print("Fetching data...")

@schedule(cron='0 9 * * *')  # Every day at 9 AM
def daily_report():
    print("Generating report...")
```

### Scheduler Class

```python
from autocron import AutoCron

scheduler = AutoCron()

scheduler.add_task(
    name="backup",
    func=backup_database,
    every='1h',
    retries=3,
    notify='desktop'
)

scheduler.start()
```

### With Retry & Timeout

```python
@schedule(every='10m', retries=3, timeout=60)
def api_call():
    # Retries up to 3 times, max 60 seconds
    response = requests.get('https://api.example.com/data')
    return response.json()
```

### Email Notifications

```python
scheduler.add_task(
    name="critical_task",
    func=process_payments,
    cron='0 */4 * * *',  # Every 4 hours
    notify='email',
    email_config={
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'from_email': 'YOUR_EMAIL@gmail.com',
        'to_email': 'ADMIN_EMAIL@gmail.com',
        'password': 'YOUR_APP_PASSWORD_HERE'
    }
)
```

---

## 📖 Time Formats

**Intervals:**
- `'30s'` → Every 30 seconds
- `'5m'` → Every 5 minutes
- `'2h'` → Every 2 hours
- `'1d'` → Every day

**Cron expressions:**
- `'0 9 * * *'` → Daily at 9 AM
- `'*/15 * * * *'` → Every 15 minutes
- `'0 0 * * 0'` → Sundays at midnight
- `'0 12 * * 1-5'` → Weekdays at noon

---

## 🛠️ CLI

```bash
# Schedule from command line
autocron schedule script.py --every 5m --retries 3

# List tasks
autocron list

# View logs
autocron logs task_name
```

---

## 🎯 Use Cases

- **Data pipelines** – ETL jobs, backups, syncs
- **Web scraping** – Periodic data collection
- **Monitoring** – Health checks, API status
- **Reports** – Automated daily/weekly reports
- **Maintenance** – Log cleanup, cache clearing

---

## 📚 Documentation

**📖 New to AutoCron?** Check out our [Complete Guide](docs/complete-guide.md) for detailed examples, production setup, and platform-specific instructions!

- **[Complete Guide](docs/complete-guide.md)** – Full manual with all examples
- **[Quick Start](docs/quickstart.md)** – Get started in 5 minutes
- **[API Reference](docs/api-reference.md)** – Complete API docs
- **[Examples](examples/)** – Real-world use cases
- **[FAQ](docs/faq.md)** – Common questions

---

## 🧪 Testing

AutoCron is tested across **12 combinations** (3 OS × 4 Python versions):

```bash
pytest                    # Run all tests
pytest --cov=autocron     # With coverage
pytest -m linux           # Platform-specific
```

**Test matrix:**
- ✅ Windows, Linux, macOS
- ✅ Python 3.10, 3.11, 3.12, 3.13, 3.14
- ✅ 82/84 tests passing (69% coverage)

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📝 License

MIT License – see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- **PyPI:** [https://pypi.org/project/autocron/](https://pypi.org/project/autocron/)
- **Issues:** [GitHub Issues](https://github.com/mdshoaibuddinchanda/autocron/issues)
- **Discussions:** [GitHub Discussions](https://github.com/mdshoaibuddinchanda/autocron/discussions)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)

---

**Made with ❤️ by [mdshoaibuddinchanda](https://github.com/mdshoaibuddinchanda)**
