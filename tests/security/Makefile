# Security Testing Framework Makefile
# Author: Murray Kopit <murr2k@gmail.com>

# Module names
SECURITY_MODULES := buffer_overflow_tests privilege_escalation_tests memory_safety_tests race_condition_tests

# Kernel build directory
KERNEL_VERSION := $(shell uname -r)
KDIR ?= /lib/modules/$(KERNEL_VERSION)/build

# Build directory
BUILD_DIR ?= ../../build/security

# Current directory
PWD := $(shell pwd)

# Compiler flags for security testing
ccflags-y := -Wall -Wextra -DDEBUG -I$(PWD)/../../include
ccflags-y += -DCONFIG_SECURITY_TESTING=1
ccflags-y += -DCONFIG_KASAN_ENABLE=1 -DCONFIG_SLUB_DEBUG=1

# Enable security-related compiler flags
EXTRA_CFLAGS += -I$(PWD)/../../include
EXTRA_CFLAGS += -Wformat-security -Wstack-protector
EXTRA_CFLAGS += -fstack-protector-strong

# Module object files
obj-m += buffer_overflow_tests.o
obj-m += privilege_escalation_tests.o  
obj-m += memory_safety_tests.o
obj-m += race_condition_tests.o

# Additional objects for framework
obj-m += security_test_framework.o

# Build targets
.PHONY: all clean install uninstall load unload test help

# Default target
all: modules

# Build kernel modules
modules:
	@echo "Building security test modules..."
	@mkdir -p $(BUILD_DIR)
	$(MAKE) -C $(KDIR) M=$(PWD) modules
	@for module in $(SECURITY_MODULES); do \
		if [ -f $${module}.ko ]; then \
			cp $${module}.ko $(BUILD_DIR)/; \
			echo "Built: $${module}.ko"; \
		fi; \
	done
	@echo "Security test modules built successfully"

# Clean build artifacts
clean:
	@echo "Cleaning security test modules..."
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	@rm -rf $(BUILD_DIR)
	@echo "Clean completed"

# Install modules
install: modules
	@echo "Installing security test modules..."
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install
	@depmod -A
	@echo "Security test modules installed"

# Uninstall modules
uninstall:
	@echo "Uninstalling security test modules..."
	@for module in $(SECURITY_MODULES); do \
		rmmod $${module} 2>/dev/null || true; \
		rm -f /lib/modules/$(KERNEL_VERSION)/extra/$${module}.ko; \
	done
	@depmod -A
	@echo "Security test modules uninstalled"

# Load security test modules
load: modules
	@echo "Loading security test modules..."
	@for module in $(SECURITY_MODULES); do \
		if [ -f $(BUILD_DIR)/$${module}.ko ]; then \
			echo "Loading $${module}..."; \
			insmod $(BUILD_DIR)/$${module}.ko || true; \
		fi; \
	done
	@echo "Security test modules loaded"
	@lsmod | grep -E "(buffer_overflow|privilege_escalation|memory_safety|race_condition)" || true

# Unload security test modules
unload:
	@echo "Unloading security test modules..."
	@for module in $(SECURITY_MODULES); do \
		rmmod $${module} 2>/dev/null || true; \
	done
	@echo "Security test modules unloaded"

# Run security tests
test: load
	@echo "Running security tests..."
	@echo "=== Buffer Overflow Tests ==="
	@dmesg | tail -20 | grep -i "buffer_overflow" || echo "No buffer overflow test output"
	@echo "=== Privilege Escalation Tests ==="
	@dmesg | tail -20 | grep -i "privilege_escalation" || echo "No privilege escalation test output"
	@echo "=== Memory Safety Tests ==="
	@dmesg | tail -20 | grep -i "memory_safety" || echo "No memory safety test output"
	@echo "=== Race Condition Tests ==="
	@dmesg | tail -20 | grep -i "race_condition" || echo "No race condition test output"
	@echo "Security tests completed. Check dmesg for detailed results."

# Show module information
info: modules
	@echo "=== Security Test Modules Information ==="
	@for module in $(SECURITY_MODULES); do \
		if [ -f $(BUILD_DIR)/$${module}.ko ]; then \
			echo "--- $${module}.ko ---"; \
			modinfo $(BUILD_DIR)/$${module}.ko; \
			echo ""; \
		fi; \
	done

# Check dependencies
check-deps:
	@echo "Checking security test dependencies..."
	@echo -n "Kernel headers: "
	@if [ -d $(KDIR) ]; then echo "✓ Found at $(KDIR)"; else echo "✗ Not found"; fi
	@echo -n "Security features: "
	@if grep -q CONFIG_KASAN /boot/config-$(KERNEL_VERSION) 2>/dev/null; then echo -n "KASAN ✓ "; fi
	@if grep -q CONFIG_SLUB_DEBUG /boot/config-$(KERNEL_VERSION) 2>/dev/null; then echo -n "SLUB_DEBUG ✓ "; fi
	@if grep -q CONFIG_STACKPROTECTOR /boot/config-$(KERNEL_VERSION) 2>/dev/null; then echo -n "STACKPROTECTOR ✓ "; fi
	@echo ""

# Security test configuration
config:
	@echo "Configuring security test environment..."
	@echo "# Security Test Configuration" > security_test.conf
	@echo "KASAN_ENABLED=1" >> security_test.conf
	@echo "SLUB_DEBUG_ENABLED=1" >> security_test.conf
	@echo "STACK_PROTECTOR_ENABLED=1" >> security_test.conf
	@echo "SECURITY_TEST_VERBOSE=1" >> security_test.conf
	@echo "Security test configuration written to security_test.conf"

# Run specific test category
test-buffer-overflow:
	@echo "Running buffer overflow tests..."
	@if lsmod | grep -q buffer_overflow_tests; then \
		echo "Buffer overflow test module loaded"; \
		dmesg | grep -i "buffer_overflow" | tail -10; \
	else \
		echo "Loading buffer overflow test module..."; \
		make load-buffer-overflow; \
	fi

test-privilege-escalation:
	@echo "Running privilege escalation tests..."
	@if lsmod | grep -q privilege_escalation_tests; then \
		echo "Privilege escalation test module loaded"; \
		dmesg | grep -i "privilege_escalation" | tail -10; \
	else \
		echo "Loading privilege escalation test module..."; \
		make load-privilege-escalation; \
	fi

test-memory-safety:
	@echo "Running memory safety tests..."
	@if lsmod | grep -q memory_safety_tests; then \
		echo "Memory safety test module loaded"; \
		dmesg | grep -i "memory_safety" | tail -10; \
	else \
		echo "Loading memory safety test module..."; \
		make load-memory-safety; \
	fi

# Load individual modules
load-buffer-overflow:
	@if [ -f $(BUILD_DIR)/buffer_overflow_tests.ko ]; then \
		insmod $(BUILD_DIR)/buffer_overflow_tests.ko; \
		echo "Buffer overflow test module loaded"; \
	fi

load-privilege-escalation:
	@if [ -f $(BUILD_DIR)/privilege_escalation_tests.ko ]; then \
		insmod $(BUILD_DIR)/privilege_escalation_tests.ko; \
		echo "Privilege escalation test module loaded"; \
	fi

load-memory-safety:
	@if [ -f $(BUILD_DIR)/memory_safety_tests.ko ]; then \
		insmod $(BUILD_DIR)/memory_safety_tests.ko; \
		echo "Memory safety test module loaded"; \
	fi

# Generate test report
report:
	@echo "Generating security test report..."
	@mkdir -p $(BUILD_DIR)/reports
	@echo "# Security Test Report - $(shell date)" > $(BUILD_DIR)/reports/security_test_report.md
	@echo "" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "## Test Results" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "### Buffer Overflow Tests" >> $(BUILD_DIR)/reports/security_test_report.md
	@dmesg | grep -i "buffer_overflow" | tail -5 >> $(BUILD_DIR)/reports/security_test_report.md || echo "No results" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "### Privilege Escalation Tests" >> $(BUILD_DIR)/reports/security_test_report.md
	@dmesg | grep -i "privilege_escalation" | tail -5 >> $(BUILD_DIR)/reports/security_test_report.md || echo "No results" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "### Memory Safety Tests" >> $(BUILD_DIR)/reports/security_test_report.md
	@dmesg | grep -i "memory_safety" | tail -5 >> $(BUILD_DIR)/reports/security_test_report.md || echo "No results" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "" >> $(BUILD_DIR)/reports/security_test_report.md
	@echo "Report generated: $(BUILD_DIR)/reports/security_test_report.md"

# Show status
status:
	@echo "=== Security Test Module Status ==="
	@echo "Kernel version: $(KERNEL_VERSION)"
	@echo "Build directory: $(BUILD_DIR)"
	@echo ""
	@echo "Module Status:"
	@for module in $(SECURITY_MODULES); do \
		echo -n "  $${module}: "; \
		if lsmod | grep -q $${module}; then \
			echo "LOADED ✓"; \
		else \
			echo "NOT LOADED"; \
		fi; \
	done
	@echo ""
	@echo "Built Modules:"
	@for module in $(SECURITY_MODULES); do \
		if [ -f $(BUILD_DIR)/$${module}.ko ]; then \
			echo "  ✓ $(BUILD_DIR)/$${module}.ko"; \
		else \
			echo "  ✗ $(BUILD_DIR)/$${module}.ko"; \
		fi; \
	done

# Help target
help:
	@echo "Security Testing Framework Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  all                      - Build all security test modules (default)"
	@echo "  modules                  - Build security test modules"
	@echo "  clean                    - Clean build artifacts"
	@echo "  install                  - Install modules system-wide"
	@echo "  uninstall                - Remove installed modules"
	@echo "  load                     - Load all security test modules"
	@echo "  unload                   - Unload all security test modules"
	@echo "  test                     - Run all security tests"
	@echo "  test-buffer-overflow     - Run buffer overflow tests only"
	@echo "  test-privilege-escalation- Run privilege escalation tests only"
	@echo "  test-memory-safety       - Run memory safety tests only"
	@echo "  info                     - Show module information"
	@echo "  check-deps               - Check build dependencies"
	@echo "  config                   - Configure security test environment"
	@echo "  report                   - Generate security test report"
	@echo "  status                   - Show current status"
	@echo "  help                     - Show this help message"
	@echo ""
	@echo "Security Test Modules:"
	@for module in $(SECURITY_MODULES); do \
		echo "  - $${module}"; \
	done
	@echo ""
	@echo "Examples:"
	@echo "  make                     # Build all modules"
	@echo "  make test                # Run all security tests"
	@echo "  make test-buffer-overflow# Run buffer overflow tests"
	@echo "  make load                # Load all test modules"
	@echo "  make report              # Generate test report"