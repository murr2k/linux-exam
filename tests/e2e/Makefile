# MPU-6050 End-to-End Test Suite Makefile
#
# This Makefile builds the C-based end-to-end test programs for the MPU-6050 driver.
#
# Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

# Compiler and flags
CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -O2 -g
INCLUDES = -I../../include
LIBS = -lm

# Source files
SOURCES = test_mpu6050_e2e.c validate_ranges.c
TARGETS = test_mpu6050_e2e validate_ranges

# Build directory
BUILD_DIR = ../../build/tests/e2e

# Default target
all: $(TARGETS)

# Ensure build directory exists
$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

# Build main E2E test
test_mpu6050_e2e: test_mpu6050_e2e.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(INCLUDES) -o $(BUILD_DIR)/$@ $< $(LIBS)
	@ln -sf $(BUILD_DIR)/$@ $@
	@echo "Built: $@"

# Build range validation test  
validate_ranges: validate_ranges.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(INCLUDES) -o $(BUILD_DIR)/$@ $< $(LIBS)
	@ln -sf $(BUILD_DIR)/$@ $@
	@echo "Built: $@"

# Clean targets
clean:
	@rm -f $(TARGETS)
	@rm -rf $(BUILD_DIR)
	@echo "Cleaned E2E test binaries"

# Install targets (copy to system path - requires root)
install: all
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "Installation requires root privileges"; \
		echo "Please run: sudo make install"; \
		exit 1; \
	fi
	@cp $(BUILD_DIR)/test_mpu6050_e2e /usr/local/bin/
	@cp $(BUILD_DIR)/validate_ranges /usr/local/bin/
	@cp run_e2e_tests.sh /usr/local/bin/
	@cp test_mpu6050_e2e.py /usr/local/bin/
	@chmod +x /usr/local/bin/run_e2e_tests.sh
	@chmod +x /usr/local/bin/test_mpu6050_e2e.py
	@echo "Installed E2E test suite to /usr/local/bin/"

# Uninstall targets
uninstall:
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "Uninstallation requires root privileges"; \
		echo "Please run: sudo make uninstall"; \
		exit 1; \
	fi
	@rm -f /usr/local/bin/test_mpu6050_e2e
	@rm -f /usr/local/bin/validate_ranges
	@rm -f /usr/local/bin/run_e2e_tests.sh
	@rm -f /usr/local/bin/test_mpu6050_e2e.py
	@echo "Uninstalled E2E test suite from /usr/local/bin/"

# Test build (compile only, don't run)
test: all
	@echo "All E2E test programs compiled successfully"
	@echo "Available programs:"
	@echo "  ./test_mpu6050_e2e - Main E2E test suite"
	@echo "  ./validate_ranges  - Range validation tests"
	@echo "  ./run_e2e_tests.sh - Complete test runner (requires root)"
	@echo "  ./test_mpu6050_e2e.py - Python advanced test suite"

# Run tests (requires root and loaded driver)
run: all
	@echo "Running E2E test suite..."
	@echo "NOTE: This requires root privileges and a loaded MPU-6050 driver"
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "Please run: sudo make run"; \
		exit 1; \
	fi
	@./run_e2e_tests.sh

# Quick test (just C tests, no module operations)
quick-test: all
	@echo "Running quick E2E tests (device must already exist)..."
	@if [ -c /dev/mpu6050 ]; then \
		./test_mpu6050_e2e -v || true; \
		./validate_ranges -v || true; \
	else \
		echo "Device /dev/mpu6050 not found"; \
		echo "Load the driver first or run 'sudo make run'"; \
	fi

# Help target
help:
	@echo "MPU-6050 E2E Test Suite Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all          - Build all test programs (default)"
	@echo "  clean        - Remove built files"
	@echo "  test         - Build and verify compilation"
	@echo "  run          - Build and run complete test suite (requires root)"
	@echo "  quick-test   - Run tests on existing device (no module operations)"
	@echo "  install      - Install to system path (requires root)"
	@echo "  uninstall    - Remove from system path (requires root)"
	@echo "  help         - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make                    # Build all tests"
	@echo "  make test               # Verify build"
	@echo "  sudo make run          # Full test suite"
	@echo "  make quick-test        # Test existing device"
	@echo "  sudo make install      # Install system-wide"
	@echo ""
	@echo "Requirements:"
	@echo "  - gcc compiler"
	@echo "  - Linux kernel headers"
	@echo "  - Root privileges for driver operations"
	@echo "  - Python 3 (for advanced tests)"
	@echo "  - Optional: matplotlib, numpy (for visualization)"

# Phony targets
.PHONY: all clean install uninstall test run quick-test help

# Default target
.DEFAULT_GOAL := all