# MPU-6050 Test Framework Makefile

SHELL := /bin/bash
PYTHON := python3
PIP := pip3
VENV_DIR := .venv
VENV_BIN := $(VENV_DIR)/bin
VENV_PYTHON := $(VENV_BIN)/python3
VENV_PIP := $(VENV_BIN)/pip
PROJECT_ROOT := ../../..
RESULTS_DIR := $(PROJECT_ROOT)/test-results/e2e
REPORTS_DIR := $(RESULTS_DIR)/reports
LOGS_DIR := $(RESULTS_DIR)/logs
COVERAGE_DIR := $(RESULTS_DIR)/coverage

# Default target
.PHONY: all
all: setup test

# Setup virtual environment and install dependencies
.PHONY: setup
setup: $(VENV_DIR)/pyvenv.cfg
	@echo "Setting up test framework environment..."
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	@echo "Setup complete!"

$(VENV_DIR)/pyvenv.cfg:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)

# Create necessary directories
.PHONY: directories
directories:
	@mkdir -p $(RESULTS_DIR) $(REPORTS_DIR) $(LOGS_DIR) $(COVERAGE_DIR)

# Install development dependencies
.PHONY: dev-setup
dev-setup: setup
	$(VENV_PIP) install -r requirements-dev.txt

# Run all tests
.PHONY: test
test: setup directories
	@echo "Running all end-to-end tests..."
	$(VENV_PYTHON) main.py --suite all --verbose \
		--results $(REPORTS_DIR)/test_results.json \
		--html-report $(REPORTS_DIR)/test_report.html \
		--junit-xml $(REPORTS_DIR)/junit_results.xml

# Run specific test suite
.PHONY: test-module
test-module: setup directories
	$(VENV_PYTHON) main.py --suite module_tests --verbose

.PHONY: test-basic
test-basic: setup directories
	$(VENV_PYTHON) main.py --suite basic_functionality --verbose

.PHONY: test-data
test-data: setup directories
	$(VENV_PYTHON) main.py --suite data_operations --verbose

.PHONY: test-performance
test-performance: setup directories
	$(VENV_PYTHON) main.py --suite performance_tests --verbose

.PHONY: test-stress
test-stress: setup directories
	$(VENV_PYTHON) main.py --suite stress_tests --verbose

# Run tests with pytest
.PHONY: pytest
pytest: setup directories
	cd $(VENV_BIN) && ./python -m pytest $(PWD)/.. -c $(PWD)/pytest.ini

# Run quick smoke tests
.PHONY: smoke
smoke: setup directories
	$(VENV_PYTHON) main.py --suite basic_functionality --timeout 60

# Dry run (show what would be executed)
.PHONY: dry-run
dry-run: setup
	$(VENV_PYTHON) main.py --dry-run --suite all

# Check test framework syntax and imports
.PHONY: check
check: setup
	@echo "Checking Python syntax..."
	$(VENV_PYTHON) -m py_compile *.py
	@echo "Checking imports..."
	$(VENV_PYTHON) -c "import test_framework, validators, performance, reports"
	@echo "Syntax and imports OK!"

# Run linting and style checks
.PHONY: lint
lint: setup
	@if $(VENV_PYTHON) -c "import flake8" 2>/dev/null; then \
		echo "Running flake8 linting..."; \
		$(VENV_PYTHON) -m flake8 *.py; \
	else \
		echo "flake8 not installed, skipping linting"; \
	fi

# Format code
.PHONY: format
format: setup
	@if $(VENV_PYTHON) -c "import black" 2>/dev/null; then \
		echo "Formatting code with black..."; \
		$(VENV_PYTHON) -m black *.py; \
	else \
		echo "black not installed, skipping formatting"; \
	fi

# Type checking
.PHONY: typecheck
typecheck: setup
	@if $(VENV_PYTHON) -c "import mypy" 2>/dev/null; then \
		echo "Running type checks with mypy..."; \
		$(VENV_PYTHON) -m mypy --ignore-missing-imports *.py; \
	else \
		echo "mypy not installed, skipping type checking"; \
	fi

# Generate test data
.PHONY: test-data-generate
test-data-generate: setup
	@echo "Generating test data..."
	$(VENV_PYTHON) -c "
import json
import time
data = {
    'timestamp': time.time(),
    'sample_data': [[1000, 0, 1000, 2500, 0, 0, 0] for _ in range(100)]
}
with open('sample_test_data.json', 'w') as f:
    json.dump(data, f, indent=2)
"
	@echo "Test data generated: sample_test_data.json"

# Clean generated files
.PHONY: clean
clean:
	@echo "Cleaning generated files..."
	rm -rf __pycache__/ *.pyc *.pyo
	rm -rf .pytest_cache/ .coverage
	rm -f *.log sample_test_data.json
	rm -rf $(RESULTS_DIR)/*
	@echo "Clean complete!"

# Clean everything including virtual environment
.PHONY: clean-all
clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf $(VENV_DIR)
	@echo "Full clean complete!"

# Install system dependencies (requires sudo)
.PHONY: install-system-deps
install-system-deps:
	@echo "Installing system dependencies..."
	@if command -v apt-get >/dev/null 2>&1; then \
		sudo apt-get update; \
		sudo apt-get install -y python3-dev python3-pip python3-venv; \
		sudo apt-get install -y build-essential linux-headers-$$(uname -r); \
		sudo apt-get install -y pkg-config libffi-dev; \
	elif command -v yum >/dev/null 2>&1; then \
		sudo yum install -y python3-devel python3-pip; \
		sudo yum groupinstall -y "Development Tools"; \
		sudo yum install -y kernel-devel-$$(uname -r); \
	else \
		echo "Unsupported package manager. Please install dependencies manually."; \
	fi

# Show help
.PHONY: help
help:
	@echo "MPU-6050 Test Framework Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  setup              - Setup virtual environment and dependencies"
	@echo "  test               - Run all tests"
	@echo "  test-module        - Run module loading tests"
	@echo "  test-basic         - Run basic functionality tests"  
	@echo "  test-data          - Run data operation tests"
	@echo "  test-performance   - Run performance tests"
	@echo "  test-stress        - Run stress tests"
	@echo "  pytest             - Run tests with pytest"
	@echo "  smoke              - Run quick smoke tests"
	@echo "  dry-run            - Show what would be executed"
	@echo "  check              - Check syntax and imports"
	@echo "  lint               - Run code linting"
	@echo "  format             - Format code"
	@echo "  typecheck          - Run type checking"
	@echo "  clean              - Clean generated files"
	@echo "  clean-all          - Clean everything including venv"
	@echo "  install-system-deps- Install system dependencies"
	@echo "  help               - Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make setup         # Setup environment"
	@echo "  make test          # Run all tests"
	@echo "  make smoke         # Quick test run"
	@echo "  make dry-run       # See what would run"

# Development workflow targets
.PHONY: dev
dev: dev-setup check lint

.PHONY: ci
ci: setup check test

.PHONY: release
release: clean setup check lint typecheck test

# Show current configuration
.PHONY: config
config:
	@echo "Current configuration:"
	@echo "  Python: $(shell $(PYTHON) --version)"
	@echo "  Virtual env: $(VENV_DIR)"
	@echo "  Project root: $(PROJECT_ROOT)"
	@echo "  Results dir: $(RESULTS_DIR)"
	@echo "  Reports dir: $(REPORTS_DIR)"
	@echo "  Test config: $(shell ls -la test_config.json 2>/dev/null || echo 'Not found')"

# List available test suites
.PHONY: list-suites
list-suites: setup
	$(VENV_PYTHON) main.py --list-suites

# Show version information
.PHONY: version
version: setup
	$(VENV_PYTHON) main.py --version