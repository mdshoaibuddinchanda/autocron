# Installation Guide

This guide covers installing AutoCron on different platforms and environments.

## Requirements

- **Python**: 3.10 or higher
- **Operating Systems**: Windows, Linux, macOS
- **Dependencies**: Automatically installed with pip

## Quick Installation

### Using pip (Recommended)

```bash
pip install autocron
```

### With Notifications Support

```bash
pip install autocron[notifications]
```

### Latest Development Version

```bash
pip install git+https://github.com/mdshoaibuddinchanda/autocron.git
```

## Platform-Specific Installation

### Windows

**Using PowerShell:**

```powershell
# Install Python 3.10+ from python.org first
python -m pip install --upgrade pip
pip install autocron
```

**Verify Installation:**

```powershell
python -c "from autocron import AutoCron; print('AutoCron installed successfully!')"
autocron --version
```

### Optional: Install for all users

```powershell
pip install --user autocron
```

### Linux

**Ubuntu/Debian:**

```bash
# Ensure Python 3.10+ is installed
sudo apt update
sudo apt install python3 python3-pip

# Install AutoCron
pip3 install autocron
```

**Fedora/RHEL/CentOS:**

```bash
sudo dnf install python3 python3-pip
pip3 install autocron
```

**Arch Linux:**

```bash
sudo pacman -S python python-pip
pip install autocron
```

### macOS

**Using Homebrew:**

```bash
# Install Python 3.10+ if not already installed
brew install python@3.10

# Install AutoCron
pip3 install autocron
```

**Using system Python:**

```bash
python3 -m pip install --upgrade pip
pip3 install autocron
```

## Installing from Source

### Clone Repository

```bash
git clone https://github.com/mdshoaibuddinchanda/autocron.git
cd autocron
```

### Install Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Or install development dependencies (includes testing, linting, etc.)
pip install -r requirements-dev.txt
```

### Development Installation

```bash
# Install in editable mode with dev dependencies
pip install -e .[dev,notifications]

# Or using requirements file
pip install -r requirements-dev.txt
pip install -e .
```

### Building from Source

```bash
# Install build tools
pip install build

# Build the package
python -m build

# Install the built package
pip install dist/autocron-*.whl
```

## Docker Installation (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install autocron

COPY your_scheduler.py .

CMD ["python", "your_scheduler.py"]
```

Build and run:

```bash
docker build -t autocron-app .
docker run -d autocron-app
```

## Virtual Environment (Recommended)

### Using venv

```bash
# Create virtual environment
python -m venv autocron-env

# Activate (Linux/macOS)
source autocron-env/bin/activate

# Activate (Windows)
autocron-env\Scripts\activate

# Install AutoCron
pip install autocron
```

### Using conda

```bash
# Create conda environment
conda create -n autocron python=3.11

# Activate environment
conda activate autocron

# Install AutoCron
pip install autocron
```

## Verifying Installation

Run the verification script:

```python
# verify_autocron.py
from autocron import AutoCron, schedule, __version__
import sys

print(f" AutoCron version: {__version__}")
print(f" Python version: {sys.version}")
print(f" Installation path: {AutoCron.__module__}")

# Test basic functionality
@schedule(every='1m')
def test_task():
 print("Test task works!")

print(" All checks passed! AutoCron is ready to use.")
```

Run it:

```bash
python verify_autocron.py
```

## Upgrading

### Upgrade to Latest Version

```bash
pip install --upgrade autocron
```

### Upgrade with Notifications

```bash
pip install --upgrade autocron[notifications]
```

## ️ Uninstalling

```bash
pip uninstall autocron
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied

```bash
# Use --user flag
pip install --user autocron
```

### 2. Python Version Too Old

```bash
# Check Python version
python --version

# Install Python 3.10+ from python.org
```

### 3. Module Not Found

```bash
# Ensure pip is using the correct Python
python -m pip install autocron
```

### 4. SSL Certificate Errors

```bash
# Use trusted host
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org autocron
```

### Platform-Specific Issues

### Windows: "python is not recognized"

- Add Python to PATH during installation
- Or use full path: `C:\Python310\python.exe`

### Linux: "pip: command not found"

```bash
sudo apt install python3-pip
```

### macOS: "command not found: pip"

```bash
python3 -m ensurepip --upgrade
```

## Dependencies

AutoCron automatically installs these dependencies:

- **croniter** (≥1.4.0) - Cron expression parsing
- **python-crontab** (≥3.0.0) - Linux/macOS cron management
- **pywin32** (≥305) - Windows Task Scheduler (Windows only)
- **tqdm** (≥4.65.0) - Progress bars
- **psutil** (≥5.9.0) - System monitoring
- **pyyaml** (≥6.0) - Configuration files

**Optional:**

- **plyer** (≥2.1.0) - Desktop notifications

## Next Steps

After installation:

1. **[Quick Start Guide](quickstart.md)** - Get started in 5 minutes
2. **[Tutorial](tutorial.md)** - Complete walkthrough
3. **[Examples](../examples/)** - Sample code

---

**Need help?** [Open an issue](https://github.com/mdshoaibuddinchanda/autocron/issues) or check the [FAQ](faq.md)
