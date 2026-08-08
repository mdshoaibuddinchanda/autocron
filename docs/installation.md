# Installation

## Supported Python

AutoCron supports CPython 3.10 and newer. CI validates the supported version and
operating-system matrix declared in `pyproject.toml`.

## Install from PyPI

```bash
python -m pip install autocron-scheduler
```

Optional terminal dashboard and desktop notification dependencies are available
through extras:

```bash
python -m pip install "autocron-scheduler[dashboard]"
python -m pip install "autocron-scheduler[notifications]"
python -m pip install "autocron-scheduler[all]"
```

The distribution name is `autocron-scheduler`; the import package and executable
are both named `autocron`.

## Install from source

```bash
git clone https://github.com/mdshoaibuddinchanda/autocron.git
cd autocron
python -m pip install -e ".[dev,all]"
```

For this repository's Windows development environment:

```powershell
conda activate PY312
python -m pip install -e ".[dev,all,demo,docs]"
```

## Verify the installed artifact

```bash
python -c "import autocron; print(autocron.__version__)"
autocron --help
```

Release validation installs the built wheel in a clean environment. This is
important because an editable install can hide missing packages or an incorrect
console entry point.
