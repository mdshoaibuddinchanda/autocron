# Contributing to AutoCron

Thank you for your interest in contributing to AutoCron! We welcome contributions from the community.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- pip

### Setting Up Development Environment

1. **Fork and clone the repository**

```bash
git clone https://github.com/yourusername/autocron.git
cd autocron
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -e .[dev,notifications]
```

4. **Run tests**

```bash
pytest
```

## Development Workflow

### Branch Strategy

- `main` - stable production code
- `develop` - integration branch for features
- `feature/*` - feature branches
- `bugfix/*` - bug fix branches
- `hotfix/*` - urgent fixes for production

### Making Changes

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**

- Write clean, readable code
- Follow PEP 8 style guide
- Add type hints
- Write docstrings for all public functions/classes

3. **Format your code**

```bash
black autocron tests
isort autocron tests
```

4. **Run linters**

```bash
flake8 autocron tests
mypy autocron
pylint autocron
```

5. **Write tests**

- Add unit tests for new functionality
- Ensure all tests pass
- Aim for >90% code coverage

```bash
pytest --cov=autocron
```

6. **Commit your changes**

```bash
git add .
git commit -m "feat: add awesome feature"
```

Use conventional commit messages:
- `feat:` - new feature
- `fix:` - bug fix
- `docs:` - documentation changes
- `test:` - test changes
- `refactor:` - code refactoring
- `chore:` - maintenance tasks

7. **Push and create pull request**

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style

### Python Style Guide

- Follow PEP 8
- Maximum line length: 100 characters
- Use type hints
- Write comprehensive docstrings

### Docstring Format

```python
def function_name(arg1: str, arg2: int) -> bool:
    """
    Brief description of function.
    
    Longer description if needed.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When input is invalid
        
    Examples:
        >>> function_name("test", 42)
        True
    """
    pass
```

## Testing Guidelines

### Writing Tests

- Place tests in the `tests/` directory
- Name test files as `test_*.py`
- Name test functions as `test_*`
- Use descriptive test names
- Use fixtures for common setup
- Mock external dependencies

### Test Structure

```python
class TestFeature:
    """Test suite for feature."""
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        expected = "result"
        
        # Act
        actual = function_under_test()
        
        # Assert
        assert actual == expected
    
    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=autocron

# Run specific test file
pytest tests/test_scheduler.py

# Run specific test
pytest tests/test_scheduler.py::TestAutoCron::test_create_scheduler

# Run platform-specific tests
pytest -m windows
pytest -m linux
pytest -m darwin
```

## Documentation

### Adding Documentation

- Update README.md for user-facing changes
- Add docstrings to all public APIs
- Update examples if needed
- Add inline comments for complex logic

### Building Documentation

```bash
cd docs
make html
```

## Pull Request Process

1. **Ensure CI passes**
   - All tests pass
   - Code coverage maintained
   - Linting passes
   - No security issues

2. **Update documentation**
   - Update README if needed
   - Add/update docstrings
   - Update CHANGELOG.md

3. **Request review**
   - Assign reviewers
   - Respond to feedback
   - Make requested changes

4. **Merge**
   - Squash commits if needed
   - Merge to develop branch
   - Delete feature branch

## Release Process

1. Update version in `autocron/version.py`
2. Update CHANGELOG.md
3. Create release branch
4. Tag release: `git tag v1.0.0`
5. Push tags: `git push --tags`
6. GitHub Actions will automatically publish to PyPI

## Code Review Guidelines

### For Contributors

- Keep PRs focused and small
- Write clear PR descriptions
- Respond to feedback promptly
- Be open to suggestions

### For Reviewers

- Be constructive and respectful
- Focus on code quality and correctness
- Check for test coverage
- Verify documentation is updated

## Issue Reporting

### Bug Reports

Include:
- Python version
- Operating system
- AutoCron version
- Minimal reproduction example
- Expected vs actual behavior
- Error messages/stack traces

### Feature Requests

Include:
- Use case description
- Proposed API/interface
- Alternative solutions considered
- Willingness to contribute

## Community

- Be respectful and inclusive
- Follow the Code of Conduct
- Help others in discussions
- Share your use cases

## Questions?

- Open a GitHub Discussion
- Check existing issues
- Read the documentation

Thank you for contributing to AutoCron! 🎉
