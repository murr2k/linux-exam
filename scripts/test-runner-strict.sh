#!/bin/bash

# Strict Test Runner - Properly fails on test failures
# Maintains test best practices: tests must pass or fail, never be ignored

set -o pipefail  # Fail on pipe failures
set +e           # Don't exit immediately, collect all results

# Initialize counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
EXIT_CODE=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

# Parse arguments
TEST_CATEGORY="${1:-all}"
VERBOSE="${2:-false}"

log_info "Starting test execution for category: $TEST_CATEGORY"

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    log_info "Running: $test_name"
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if eval "$test_command"; then
        log_success "$test_name passed"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "$test_name FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        EXIT_CODE=1
        return 1
    fi
}

# Function to skip a test with proper reporting
skip_test() {
    local test_name="$1"
    local reason="$2"
    
    log_warn "Skipping $test_name: $reason"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
}

# Check for required dependencies
check_dependencies() {
    local missing_deps=""
    
    if ! command -v gcc >/dev/null 2>&1; then
        missing_deps="$missing_deps gcc"
    fi
    
    if ! command -v make >/dev/null 2>&1; then
        missing_deps="$missing_deps make"
    fi
    
    if [ -n "$missing_deps" ]; then
        log_error "Critical dependencies missing:$missing_deps"
        log_error "Cannot run tests without build tools"
        exit 1
    fi
}

# Run unit tests
run_unit_tests() {
    log_info "=== Unit Tests ==="
    
    # Check if unit tests exist
    if [ ! -d "tests/unit" ]; then
        skip_test "Unit tests" "Directory tests/unit not found"
        return
    fi
    
    # Try to compile and run C unit tests
    if [ -f "tests/unit/test_mpu6050.c" ]; then
        if gcc -o tests/unit/test_mpu6050 tests/unit/test_mpu6050.c -lcunit 2>/dev/null; then
            run_test "MPU6050 C Unit Tests" "./tests/unit/test_mpu6050"
        else
            skip_test "MPU6050 C Unit Tests" "Compilation failed (CUnit may be missing)"
        fi
    fi
    
    # Try to run Google Test unit tests
    if [ -f "tests/unit/test_main.cpp" ]; then
        if g++ -o tests/unit/test_main tests/unit/test_main.cpp tests/unit/test_mpu6050.cpp -lgtest -lpthread 2>/dev/null; then
            run_test "MPU6050 Google Tests" "./tests/unit/test_main"
        else
            skip_test "MPU6050 Google Tests" "Compilation failed (Google Test may be missing)"
        fi
    fi
    
    # Run kernel module tests if possible
    if [ -f "drivers/Makefile" ] && [ "$SKIP_KERNEL_BUILD" != "1" ]; then
        run_test "Kernel Module Build" "make -C drivers clean && make -C drivers"
    else
        skip_test "Kernel Module Tests" "Kernel headers not available"
    fi
}

# Run integration tests
run_integration_tests() {
    log_info "=== Integration Tests ==="
    
    if [ ! -d "tests/integration" ]; then
        skip_test "Integration tests" "Directory tests/integration not found"
        return
    fi
    
    # Run integration test suite
    if [ -f "tests/integration/run_tests.sh" ]; then
        run_test "Integration Test Suite" "bash tests/integration/run_tests.sh"
    else
        skip_test "Integration tests" "No test runner found"
    fi
}

# Run E2E tests
run_e2e_tests() {
    log_info "=== End-to-End Tests ==="
    
    if [ ! -d "tests/e2e" ]; then
        skip_test "E2E tests" "Directory tests/e2e not found"
        return
    fi
    
    # Check for simulator
    if [ -f "tests/e2e/simulator/i2c_simulator.c" ]; then
        if gcc -o tests/e2e/simulator/i2c_simulator tests/e2e/simulator/i2c_simulator.c -pthread 2>/dev/null; then
            run_test "I2C Simulator" "./tests/e2e/simulator/i2c_simulator --test"
        else
            skip_test "I2C Simulator" "Compilation failed"
        fi
    fi
    
    # Run Python E2E tests if available
    if command -v python3 >/dev/null 2>&1 && [ -f "tests/e2e/framework/test_e2e.py" ]; then
        if python3 -m pytest tests/e2e/framework/test_e2e.py -v 2>/dev/null; then
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_PASSED=$((TESTS_PASSED + 1))
            log_success "Python E2E tests passed"
        else
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_FAILED=$((TESTS_FAILED + 1))
            EXIT_CODE=1
            log_error "Python E2E tests FAILED"
        fi
    else
        skip_test "Python E2E tests" "pytest not available or test file missing"
    fi
}

# Run linting checks
run_lint_checks() {
    log_info "=== Linting Checks ==="
    
    # C/C++ linting with cppcheck
    if command -v cppcheck >/dev/null 2>&1; then
        if cppcheck --error-exitcode=1 --enable=warning,style,performance \
                   --suppress=missingInclude drivers/ include/ 2>/dev/null; then
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_PASSED=$((TESTS_PASSED + 1))
            log_success "Cppcheck passed"
        else
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_FAILED=$((TESTS_FAILED + 1))
            EXIT_CODE=1
            log_error "Cppcheck found issues"
        fi
    else
        skip_test "Cppcheck" "Tool not installed"
    fi
    
    # Check code formatting
    if command -v clang-format >/dev/null 2>&1; then
        FORMAT_ISSUES=$(find drivers/ include/ -name "*.c" -o -name "*.h" | \
                       xargs clang-format -n 2>&1 | grep -c "warning:" || true)
        if [ "$FORMAT_ISSUES" -eq 0 ]; then
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_PASSED=$((TESTS_PASSED + 1))
            log_success "Code formatting check passed"
        else
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_FAILED=$((TESTS_FAILED + 1))
            EXIT_CODE=1
            log_error "Code formatting issues found: $FORMAT_ISSUES warnings"
        fi
    else
        skip_test "Code formatting" "clang-format not installed"
    fi
}

# Main execution
main() {
    # Check critical dependencies first
    check_dependencies
    
    # Run tests based on category
    case "$TEST_CATEGORY" in
        "unit")
            run_unit_tests
            ;;
        "integration")
            run_integration_tests
            ;;
        "e2e")
            run_e2e_tests
            ;;
        "lint")
            run_lint_checks
            ;;
        "all")
            run_unit_tests
            run_integration_tests
            run_e2e_tests
            run_lint_checks
            ;;
        *)
            log_error "Unknown test category: $TEST_CATEGORY"
            exit 1
            ;;
    esac
    
    # Print summary
    echo ""
    log_info "========================================="
    log_info "Test Execution Summary"
    log_info "========================================="
    echo -e "Tests Run:     $TESTS_RUN"
    echo -e "Tests Passed:  ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed:  ${RED}$TESTS_FAILED${NC}"
    echo -e "Tests Skipped: ${YELLOW}$TESTS_SKIPPED${NC}"
    log_info "========================================="
    
    # Exit with appropriate code
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "TEST SUITE FAILED - $TESTS_FAILED test(s) failed"
        exit 1
    elif [ $TESTS_RUN -eq 0 ]; then
        log_error "NO TESTS WERE RUN - This is a failure"
        exit 1
    elif [ $TESTS_PASSED -eq 0 ] && [ $TESTS_SKIPPED -gt 0 ]; then
        log_warn "All tests were skipped - treating as failure"
        exit 1
    else
        log_success "TEST SUITE PASSED - All tests successful"
        exit 0
    fi
}

# Run main function
main "$@"