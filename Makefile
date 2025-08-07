# MPU-6050 Kernel Driver Makefile
# Author: Murray Kopit <murr2k@gmail.com>

# Module name
MODULE_NAME := mpu6050

# Source files
obj-m += $(MODULE_NAME).o
$(MODULE_NAME)-objs := drivers/mpu6050_driver.o

# Kernel build directory
KERNEL_VERSION := $(shell uname -r)
KDIR ?= /lib/modules/$(KERNEL_VERSION)/build

# Build directory
BUILD_DIR ?= build

# Current directory
PWD := $(shell pwd)

# Compiler flags
ccflags-y := -Wall -Wextra -DDEBUG -I$(PWD)/include

# Additional flags for kernel module
EXTRA_CFLAGS += -I$(PWD)/include -DCONFIG_MPU6050_DEBUG=1

# Coverage directories
COVERAGE_DIR := build/coverage

# Build targets
.PHONY: all clean install uninstall test lint docker help coverage-badges coverage-gate coverage-dashboard

# Default target
all: modules

# Build kernel modules
modules:
	@echo "Building MPU-6050 kernel module..."
	@mkdir -p $(BUILD_DIR)
	$(MAKE) -C $(KDIR) M=$(PWD) modules
	@if [ -f $(MODULE_NAME).ko ]; then \
		cp $(MODULE_NAME).ko $(BUILD_DIR)/; \
		cp $(MODULE_NAME).mod $(BUILD_DIR)/ 2>/dev/null || true; \
		cp $(MODULE_NAME).o $(BUILD_DIR)/ 2>/dev/null || true; \
		echo "Module built successfully: $(BUILD_DIR)/$(MODULE_NAME).ko"; \
	fi

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	@rm -rf $(BUILD_DIR)
	@rm -rf test-results coverage lint-results
	@echo "Clean completed"

# Install module
install: modules
	@echo "Installing MPU-6050 kernel module..."
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install
	@depmod -A
	@echo "Module installed successfully"

# Uninstall module
uninstall:
	@echo "Uninstalling MPU-6050 kernel module..."
	@rmmod $(MODULE_NAME) 2>/dev/null || true
	@rm -f /lib/modules/$(KERNEL_VERSION)/extra/$(MODULE_NAME).ko
	@depmod -A
	@echo "Module uninstalled"

# Load module (for testing)
load: modules
	@echo "Loading MPU-6050 kernel module..."
	@if lsmod | grep -q $(MODULE_NAME); then \
		echo "Module already loaded"; \
	else \
		insmod $(BUILD_DIR)/$(MODULE_NAME).ko; \
		echo "Module loaded successfully"; \
	fi
	@dmesg | tail -10

# Unload module
unload:
	@echo "Unloading MPU-6050 kernel module..."
	@rmmod $(MODULE_NAME) 2>/dev/null || echo "Module not loaded"
	@echo "Module unloaded"

# Reload module (unload + load)
reload: unload load

# Run tests
test:
	@echo "Running tests..."
	@./scripts/build.sh --all

# Run linting
lint:
	@echo "Running code quality checks..."
	@./scripts/lint.sh --all

# Format code
format:
	@echo "Formatting code..."
	@./scripts/lint.sh --format-fix

# Docker build
docker:
	@echo "Building Docker development environment..."
	@./scripts/docker-build.sh --build

# Run in Docker
docker-run:
	@echo "Starting Docker development environment..."
	@./scripts/docker-build.sh --run

# Docker test
docker-test:
	@echo "Running tests in Docker..."
	@./scripts/docker-build.sh --test

# Show module info
info: modules
	@echo "=== Module Information ==="
	@if [ -f $(BUILD_DIR)/$(MODULE_NAME).ko ]; then \
		modinfo $(BUILD_DIR)/$(MODULE_NAME).ko; \
	else \
		echo "Module not built yet. Run 'make' first."; \
	fi

# Check dependencies
check-deps:
	@echo "Checking build dependencies..."
	@echo -n "Kernel headers: "
	@if [ -d $(KDIR) ]; then echo "✓ Found at $(KDIR)"; else echo "✗ Not found"; fi
	@echo -n "Build tools: "
	@if command -v make >/dev/null 2>&1; then echo -n "make ✓ "; fi
	@if command -v gcc >/dev/null 2>&1; then echo -n "gcc ✓ "; fi
	@echo ""
	@echo -n "Test tools: "
	@if command -v cunit-config >/dev/null 2>&1; then echo -n "cunit ✓ "; fi
	@if command -v lcov >/dev/null 2>&1; then echo -n "lcov ✓ "; fi
	@echo ""
	@echo -n "Lint tools: "
	@if command -v clang-format >/dev/null 2>&1; then echo -n "clang-format ✓ "; fi
	@if command -v cppcheck >/dev/null 2>&1; then echo -n "cppcheck ✓ "; fi
	@echo ""

# Coverage Badge Generation
coverage-badges:
	@echo "Generating coverage badges..."
	@chmod +x scripts/generate-coverage-badge.py
	@python3 scripts/generate-coverage-badge.py --input $(COVERAGE_DIR)/coverage.info --update-readme
	@echo "Coverage badges updated in README.md"

# Coverage Quality Gate
coverage-gate:
	@echo "Running coverage quality gate..."
	@chmod +x scripts/coverage-gate.py
	@python3 scripts/coverage-gate.py --input $(COVERAGE_DIR)/coverage.info --save-history

# Coverage Dashboard Update
coverage-dashboard: coverage-badges
	@echo "Coverage dashboard updated"
	@echo "View at: docs/TEST_COVERAGE_DASHBOARD.md"

# Coverage Report Generation
coverage-report:
	@echo "Generating comprehensive coverage report..."
	@mkdir -p $(COVERAGE_DIR)
	@if [ -f $(COVERAGE_DIR)/coverage.info ]; then \
		python3 scripts/generate-coverage-badge.py --input $(COVERAGE_DIR)/coverage.info --format both --output docs/badges; \
		python3 scripts/coverage-gate.py --input $(COVERAGE_DIR)/coverage.info --format json --output $(COVERAGE_DIR)/quality_gate_report.json --save-history; \
		echo "Coverage reports generated in docs/badges/ and $(COVERAGE_DIR)/"; \
	else \
		echo "No coverage data found. Run 'make test COVERAGE=1' first."; \
	fi

# CI/CD pipeline
ci: clean test lint modules coverage-report
	@echo "=== CI Pipeline Completed ==="
	@echo "✓ Tests passed"
	@echo "✓ Linting passed"  
	@echo "✓ Module built successfully"
	@echo "✓ Coverage reports generated"

# Development setup
setup:
	@echo "Setting up development environment..."
	@sudo apt-get update
	@sudo apt-get install -y \
		build-essential \
		linux-headers-$(KERNEL_VERSION) \
		libcunit1-dev \
		lcov \
		clang-format \
		cppcheck \
		docker.io
	@echo "Development environment setup completed"

# Show status
status:
	@echo "=== MPU-6050 Driver Status ==="
	@echo "Kernel version: $(KERNEL_VERSION)"
	@echo "Build directory: $(BUILD_DIR)"
	@echo "Module file: $(BUILD_DIR)/$(MODULE_NAME).ko"
	@echo -n "Module loaded: "
	@if lsmod | grep -q $(MODULE_NAME); then echo "Yes"; else echo "No"; fi
	@echo -n "Module built: "
	@if [ -f $(BUILD_DIR)/$(MODULE_NAME).ko ]; then echo "Yes"; else echo "No"; fi
	@echo "Project directory: $(PWD)"

# Help target
help:
	@echo "MPU-6050 Kernel Driver Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  all         - Build kernel module (default)"
	@echo "  modules     - Build kernel module"
	@echo "  clean       - Clean build artifacts"
	@echo "  install     - Install module system-wide"
	@echo "  uninstall   - Remove installed module"
	@echo "  load        - Load module for testing"
	@echo "  unload      - Unload module"
	@echo "  reload      - Reload module (unload + load)"
	@echo "  test        - Run test suite"
	@echo "  lint        - Run code quality checks"
	@echo "  format      - Format source code"
	@echo "  docker      - Build Docker environment"
	@echo "  docker-run  - Run Docker environment"
	@echo "  docker-test - Test in Docker"
	@echo "  info        - Show module information"
	@echo "  check-deps  - Check build dependencies"
	@echo "  setup       - Install development dependencies"
	@echo "  status      - Show current status"
	@echo "  ci          - Run CI/CD pipeline"
	@echo "  coverage-badges    - Generate coverage badges for README"
	@echo "  coverage-gate      - Run coverage quality gate"
	@echo "  coverage-dashboard - Update coverage dashboard"
	@echo "  coverage-report    - Generate comprehensive coverage reports"
	@echo "  help        - Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make                # Build module"
	@echo "  make test          # Run tests"
	@echo "  make ci            # Full CI pipeline"
	@echo "  make load          # Load for testing"
	@echo "  make docker-test   # Test in container"

# Kernel module build rules (auto-generated)
modules_install:
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install