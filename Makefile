# AutoCron Makefile

.PHONY: help install install-dev test test-cov lint format clean build publish docs

help:
	@echo "AutoCron Development Commands"
	@echo ""
	@echo "  install       Install package"
	@echo "  install-dev   Install package with dev dependencies"
	@echo "  test          Run tests"
	@echo "  test-cov      Run tests with coverage"
	@echo "  lint          Run linters"
	@echo "  format        Format code"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build distribution"
	@echo "  publish       Publish to PyPI"
	@echo "  docs          Build documentation"

install:
	pip install -e .

install-dev:
	pip install -e .[dev,notifications]

test:
	pytest -v

test-cov:
	pytest --cov=autocron --cov-report=html --cov-report=term

lint:
	black --check autocron tests
	isort --check-only autocron tests
	flake8 autocron tests --max-line-length=100 --extend-ignore=E203,W503
	mypy autocron --ignore-missing-imports
	pylint autocron --disable=C0111,R0903,R0913

format:
	black autocron tests
	isort autocron tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	twine upload dist/*

docs:
	cd docs && make html
