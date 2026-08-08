# Contributing to AutoCron

Thank you for improving AutoCron. Changes should keep scheduling behavior
predictable, tests isolated, and published artifacts installable.

## Development setup

```bash
git clone https://github.com/mdshoaibuddinchanda/autocron.git
cd autocron
python -m venv .venv
```

Activate the environment, then install all development features:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev,all,demo,docs]"
```

The maintained Windows environment can instead use:

```powershell
conda activate PY312
python -m pip install -e ".[dev,all,demo,docs]"
```

## Before making a change

1. Search existing issues and tests.
2. Add or update a test that describes the intended behavior.
3. Keep public APIs backward compatible unless the changelog includes a clear
   migration path.
4. Update documentation and notebooks when user-visible behavior changes.

## Test safety

The default test command must never use a developer's real home directory,
AutoCron database, logs, analytics, Windows Task Scheduler, or crontab.

- Use `tmp_path` for files and databases.
- Mock clocks instead of adding long sleeps.
- Mock subprocess and OS-adapter boundaries in unit tests.
- Mark real platform tests with `system` and require
  `AUTOCRON_RUN_SYSTEM_TESTS=1`.
- Ensure background threads and child processes are stopped before a test exits.

Run the normal suite with:

```bash
pytest
```

Run an explicitly authorized system test with:

```bash
AUTOCRON_RUN_SYSTEM_TESTS=1 pytest -m system
```

## Quality checks

```bash
python -m compileall -q autocron tests examples
black --check autocron tests examples
isort --check-only autocron tests examples
flake8 autocron tests examples
mypy autocron
pytest --cov=autocron --cov-branch
mkdocs build --strict
```

The built distribution must also work outside the source checkout:

```bash
python -m build
python -m twine check dist/*
```

CI installs the wheel in a clean environment and verifies imports plus
`autocron --help`.

## Documentation and notebooks

Serve documentation locally with `mkdocs serve`. Notebook examples must be
deterministic, non-interactive, use temporary paths, avoid real notifications or
OS scheduling, and contain no credentials or machine-specific paths. Execute and
inspect their committed outputs before submission.

## Pull requests

Keep each pull request focused. Describe the user-visible outcome, tests run,
platform limitations, and any compatibility impact. CI must pass before merge.

## Releases

Release versions are sourced from one package version module. A release requires:

1. Updated changelog and documentation.
2. Passing multi-platform CI and coverage gates.
3. A clean wheel/sdist installation smoke test.
4. Executed and validated demo notebooks.
5. A signed or annotated version tag and GitHub release.
6. PyPI publication through trusted publishing.
