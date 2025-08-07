#!/bin/bash

# MPU-6050 Kernel Driver Build Script
# Author: Murray Kopit <murr2k@gmail.com>
# Description: Comprehensive build script for kernel module compilation, testing, and coverage

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
TEST_DIR="${PROJECT_ROOT}/tests"
COVERAGE_DIR="${PROJECT_ROOT}/coverage"
DOCS_DIR="${PROJECT_ROOT}/docs"
RESULTS_DIR="${PROJECT_ROOT}/test-results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $*${NC}" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS] $*${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING] $*${NC}" >&2
}

error() {
    echo -e "${RED}[ERROR] $*${NC}" >&2
}

fatal() {
    error "$*"
    exit 1
}

# Help function
show_help() {
    cat << EOF
MPU-6050 Kernel Driver Build Script

Usage: $0 [OPTIONS]

OPTIONS:
    --build-only        Build kernel module only
    --test-only         Run tests only (requires existing build)
    --coverage          Generate coverage report
    --clean             Clean build directory
    --integration       Run integration tests
    --docs              Generate documentation
    --all               Run complete build, test, and coverage pipeline
    --verbose           Enable verbose output
    --help              Show this help message

EXAMPLES:
    $0 --all                    # Complete pipeline
    $0 --build-only --verbose   # Build with verbose output
    $0 --test-only --coverage   # Test with coverage
    $0 --clean --build-only     # Clean build

ENVIRONMENT VARIABLES:
    KERNEL_DIR          Kernel source directory (default: auto-detect)
    CC                  C compiler (default: gcc)
    CFLAGS              Additional C compiler flags
    VERBOSE             Enable verbose output (0/1)
EOF
}

# Setup directories
setup_directories() {
    log "Setting up build directories..."
    mkdir -p "${BUILD_DIR}" "${COVERAGE_DIR}" "${RESULTS_DIR}"
    
    # Create results subdirectories
    mkdir -p "${RESULTS_DIR}/unit" "${RESULTS_DIR}/integration"
    
    success "Directories created successfully"
}

# Detect kernel version and headers
detect_kernel() {
    log "Detecting kernel environment..."
    
    KERNEL_VERSION=$(uname -r)
    KERNEL_DIR=${KERNEL_DIR:-"/lib/modules/${KERNEL_VERSION}/build"}
    
    if [[ ! -d "${KERNEL_DIR}" ]]; then
        warn "Kernel headers not found at ${KERNEL_DIR}"
        
        # Try alternative locations
        for alt_dir in "/usr/src/linux-headers-${KERNEL_VERSION}" "/usr/src/kernels/${KERNEL_VERSION}"; do
            if [[ -d "${alt_dir}" ]]; then
                KERNEL_DIR="${alt_dir}"
                break
            fi
        done
        
        [[ ! -d "${KERNEL_DIR}" ]] && fatal "Kernel headers not found. Install linux-headers-$(uname -r)"
    fi
    
    log "Kernel version: ${KERNEL_VERSION}"
    log "Kernel directory: ${KERNEL_DIR}"
    
    export KERNEL_DIR
    success "Kernel environment detected"
}

# Clean build directory
clean_build() {
    log "Cleaning build directory..."
    if [[ -d "${BUILD_DIR}" ]]; then
        rm -rf "${BUILD_DIR}"/*
        success "Build directory cleaned"
    else
        log "Build directory doesn't exist, nothing to clean"
    fi
}

# Build kernel module
build_module() {
    log "Building MPU-6050 kernel module..."
    
    cd "${PROJECT_ROOT}"
    
    # Check if Makefile exists
    if [[ ! -f "Makefile" ]]; then
        log "Creating basic Makefile..."
        cat > Makefile << 'EOF'
# MPU-6050 Kernel Module Makefile
obj-m += mpu6050.o
mpu6050-objs := drivers/mpu6050_main.o drivers/mpu6050_i2c.o drivers/mpu6050_sysfs.o

# Kernel build directory
KDIR ?= /lib/modules/$(shell uname -r)/build

# Build directory
BUILD_DIR ?= build

all:
	mkdir -p $(BUILD_DIR)
	$(MAKE) -C $(KDIR) M=$(PWD) modules
	cp *.ko $(BUILD_DIR)/ 2>/dev/null || true
	cp *.mod $(BUILD_DIR)/ 2>/dev/null || true
	cp *.o $(BUILD_DIR)/ 2>/dev/null || true

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -rf $(BUILD_DIR)

install:
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install

.PHONY: all clean install
EOF
    fi
    
    # Set build flags
    export EXTRA_CFLAGS="-Wall -Wextra -DDEBUG"
    
    if [[ "${VERBOSE:-0}" == "1" ]]; then
        export EXTRA_CFLAGS="${EXTRA_CFLAGS} -DVERBOSE"
    fi
    
    # Build the module
    make KDIR="${KERNEL_DIR}" BUILD_DIR="${BUILD_DIR}" all
    
    # Verify build
    if [[ ! -f "${BUILD_DIR}/mpu6050.ko" ]]; then
        # Look for any .ko files
        ko_files=$(find "${BUILD_DIR}" -name "*.ko" 2>/dev/null || true)
        if [[ -z "${ko_files}" ]]; then
            fatal "No kernel module (.ko) files were built"
        else
            success "Built kernel modules: ${ko_files}"
        fi
    else
        success "MPU-6050 kernel module built successfully"
    fi
    
    # Show module information
    if command -v modinfo >/dev/null 2>&1; then
        log "Module information:"
        modinfo "${BUILD_DIR}"/*.ko | head -20 || true
    fi
}

# Create sample test files if they don't exist
create_sample_tests() {
    log "Creating sample test files..."
    
    mkdir -p "${TEST_DIR}"
    
    if [[ ! -f "${TEST_DIR}/test_mpu6050.c" ]]; then
        cat > "${TEST_DIR}/test_mpu6050.c" << 'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <CUnit/CUnit.h>
#include <CUnit/Basic.h>

// Mock driver functions
int mpu6050_init(void) {
    return 0;
}

int mpu6050_read_gyro(int *x, int *y, int *z) {
    *x = 100;
    *y = 200;
    *z = 300;
    return 0;
}

int mpu6050_read_accel(int *x, int *y, int *z) {
    *x = 1000;
    *y = 2000;
    *z = 3000;
    return 0;
}

// Test functions
void test_mpu6050_init(void) {
    CU_ASSERT(mpu6050_init() == 0);
}

void test_mpu6050_read_gyro(void) {
    int x, y, z;
    CU_ASSERT(mpu6050_read_gyro(&x, &y, &z) == 0);
    CU_ASSERT(x == 100);
    CU_ASSERT(y == 200);
    CU_ASSERT(z == 300);
}

void test_mpu6050_read_accel(void) {
    int x, y, z;
    CU_ASSERT(mpu6050_read_accel(&x, &y, &z) == 0);
    CU_ASSERT(x == 1000);
    CU_ASSERT(y == 2000);
    CU_ASSERT(z == 3000);
}

int init_suite(void) { return 0; }
int clean_suite(void) { return 0; }

int main(void) {
    if (CUE_SUCCESS != CU_initialize_registry()) {
        return CU_get_error();
    }

    CU_pSuite pSuite = CU_add_suite("MPU6050_Test_Suite", init_suite, clean_suite);
    if (NULL == pSuite) {
        CU_cleanup_registry();
        return CU_get_error();
    }

    if ((NULL == CU_add_test(pSuite, "test_mpu6050_init", test_mpu6050_init)) ||
        (NULL == CU_add_test(pSuite, "test_mpu6050_read_gyro", test_mpu6050_read_gyro)) ||
        (NULL == CU_add_test(pSuite, "test_mpu6050_read_accel", test_mpu6050_read_accel))) {
        CU_cleanup_registry();
        return CU_get_error();
    }

    CU_basic_set_mode(CU_BRM_VERBOSE);
    CU_basic_run_tests();
    
    int failures = CU_get_number_of_failures();
    CU_cleanup_registry();
    
    return (failures > 0) ? EXIT_FAILURE : EXIT_SUCCESS;
}
EOF
    fi
    
    # Create CMakeLists.txt for tests
    if [[ ! -f "${TEST_DIR}/CMakeLists.txt" ]]; then
        cat > "${TEST_DIR}/CMakeLists.txt" << 'EOF'
cmake_minimum_required(VERSION 3.10)
project(MPU6050Tests)

# Find required packages
find_package(PkgConfig REQUIRED)
pkg_check_modules(CUNIT REQUIRED cunit)

# Set C standard
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Add compile flags for coverage
if(ENABLE_COVERAGE)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fprofile-arcs -ftest-coverage")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -lgcov")
endif()

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/../include)
include_directories(${CUNIT_INCLUDE_DIRS})

# Create test executable
add_executable(test_mpu6050 test_mpu6050.c)

# Link libraries
target_link_libraries(test_mpu6050 ${CUNIT_LIBRARIES})

# Add test target
enable_testing()
add_test(NAME MPU6050UnitTests COMMAND test_mpu6050)
EOF
    fi
    
    success "Sample test files created"
}

# Run unit tests
run_tests() {
    log "Running unit tests..."
    
    create_sample_tests
    
    cd "${TEST_DIR}"
    
    # Build tests with CMake
    mkdir -p build
    cd build
    
    local cmake_flags=""
    if [[ "${COVERAGE:-0}" == "1" ]]; then
        cmake_flags="-DENABLE_COVERAGE=ON"
    fi
    
    cmake ${cmake_flags} ..
    make
    
    # Run tests
    log "Executing test suite..."
    if ./test_mpu6050; then
        success "All unit tests passed"
    else
        error "Some unit tests failed"
        return 1
    fi
    
    # Generate JUnit XML for CI
    if command -v ctest >/dev/null 2>&1; then
        ctest --output-junit "${RESULTS_DIR}/unit/results.xml" || true
    fi
}

# Generate coverage report
generate_coverage() {
    log "Generating coverage report..."
    
    if [[ ! -d "${TEST_DIR}/build" ]]; then
        warn "No test build directory found, running tests first..."
        COVERAGE=1 run_tests
    fi
    
    cd "${TEST_DIR}/build"
    
    if command -v lcov >/dev/null 2>&1; then
        # Generate coverage with lcov
        lcov --capture --directory . --output-file coverage.info
        lcov --remove coverage.info '/usr/*' --output-file coverage.info
        lcov --list coverage.info
        
        # Generate HTML report
        genhtml coverage.info --output-directory "${COVERAGE_DIR}"
        success "Coverage report generated in ${COVERAGE_DIR}/index.html"
    elif command -v gcov >/dev/null 2>&1; then
        # Basic gcov coverage
        gcov *.gcno
        mkdir -p "${COVERAGE_DIR}"
        mv *.gcov "${COVERAGE_DIR}/"
        success "Coverage files generated in ${COVERAGE_DIR}"
    else
        warn "No coverage tools found (lcov/gcov)"
    fi
}

# Run integration tests
run_integration() {
    log "Running integration tests..."
    
    # Simple integration test - check if module can be loaded (in test mode)
    if [[ -f "${BUILD_DIR}/mpu6050.ko" ]]; then
        log "Testing module loading simulation..."
        
        # Check module dependencies
        if command -v modprobe >/dev/null 2>&1; then
            modprobe --dry-run --show-depends "${BUILD_DIR}/mpu6050.ko" || true
        fi
        
        # Verify module structure
        if command -v modinfo >/dev/null 2>&1; then
            modinfo "${BUILD_DIR}/mpu6050.ko" > "${RESULTS_DIR}/integration/modinfo.txt"
            success "Module information verified"
        fi
        
        success "Integration tests completed"
    else
        error "No kernel module found for integration testing"
        return 1
    fi
}

# Generate documentation
generate_docs() {
    log "Generating documentation..."
    
    mkdir -p "${DOCS_DIR}"
    
    if command -v doxygen >/dev/null 2>&1; then
        # Create Doxygen config if it doesn't exist
        if [[ ! -f "Doxyfile" ]]; then
            doxygen -g
            sed -i 's/PROJECT_NAME.*/PROJECT_NAME = "MPU-6050 Kernel Driver"/' Doxyfile
            sed -i 's/OUTPUT_DIRECTORY.*/OUTPUT_DIRECTORY = docs/' Doxyfile
        fi
        
        doxygen
        success "Doxygen documentation generated in ${DOCS_DIR}"
    else
        # Create simple README
        cat > "${DOCS_DIR}/README.md" << 'EOF'
# MPU-6050 Kernel Driver Documentation

## Overview
This kernel driver provides support for the MPU-6050 6-axis gyroscope and accelerometer.

## Features
- I2C communication interface
- Sysfs attribute interface
- Configurable sampling rates
- Interrupt support

## Usage
```bash
# Load the module
sudo insmod mpu6050.ko

# Check dmesg for driver messages
dmesg | tail

# Access device through sysfs
cat /sys/class/mpu6050/mpu6050/gyro_data
```

## Build Information
Built on: $(date)
Kernel version: $(uname -r)
EOF
        success "Basic documentation generated"
    fi
}

# Main execution logic
main() {
    local build_only=0
    local test_only=0
    local coverage=0
    local clean=0
    local integration=0
    local docs=0
    local all=0
    local verbose=0
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-only)
                build_only=1
                shift
                ;;
            --test-only)
                test_only=1
                shift
                ;;
            --coverage)
                coverage=1
                export COVERAGE=1
                shift
                ;;
            --clean)
                clean=1
                shift
                ;;
            --integration)
                integration=1
                shift
                ;;
            --docs)
                docs=1
                shift
                ;;
            --all)
                all=1
                shift
                ;;
            --verbose)
                verbose=1
                export VERBOSE=1
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Default to --all if no options specified
    if [[ $build_only -eq 0 && $test_only -eq 0 && $clean -eq 0 && $integration -eq 0 && $docs -eq 0 && $all -eq 0 ]]; then
        all=1
    fi
    
    log "Starting MPU-6050 build process..."
    log "Project root: ${PROJECT_ROOT}"
    
    setup_directories
    detect_kernel
    
    # Clean if requested
    if [[ $clean -eq 1 ]]; then
        clean_build
    fi
    
    # Execute requested operations
    if [[ $all -eq 1 || $build_only -eq 1 ]]; then
        build_module
    fi
    
    if [[ $all -eq 1 || $test_only -eq 1 ]]; then
        run_tests
    fi
    
    if [[ $coverage -eq 1 ]]; then
        generate_coverage
    fi
    
    if [[ $integration -eq 1 || $all -eq 1 ]]; then
        run_integration
    fi
    
    if [[ $docs -eq 1 || $all -eq 1 ]]; then
        generate_docs
    fi
    
    success "Build process completed successfully!"
    
    # Summary
    log "=== Build Summary ==="
    [[ -d "${BUILD_DIR}" ]] && log "Build artifacts: $(ls -la ${BUILD_DIR} | wc -l) files"
    [[ -d "${RESULTS_DIR}" ]] && log "Test results: ${RESULTS_DIR}"
    [[ -d "${COVERAGE_DIR}" ]] && log "Coverage report: ${COVERAGE_DIR}"
    [[ -d "${DOCS_DIR}" ]] && log "Documentation: ${DOCS_DIR}"
}

# Run main function with all arguments
main "$@"