#!/bin/bash

# Smart Test Runner for GitHub Actions
# Works with available tools, properly reports failures

set +e  # Don't exit immediately
set -o pipefail  # Catch pipe failures

# Initialize result tracking
TEST_RESULTS=0
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $*"; }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $*"; }

# Get test category from argument
TEST_CATEGORY="${1:-all}"

log_info "Running tests for category: $TEST_CATEGORY"
log_info "Environment: ${GITHUB_ACTIONS:+GitHub Actions}${GITHUB_ACTIONS:-Local}"

# Function to run a test
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    log_info "Running: $test_name"
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if eval "$test_cmd"; then
        log_pass "$test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "$test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        TEST_RESULTS=1
    fi
}

# Function to skip a test
skip_test() {
    local test_name="$1"
    local reason="$2"
    
    log_skip "$test_name - $reason"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
}

# Check for required tools
check_required_tools() {
    local missing=0
    
    for tool in gcc make; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_fail "Critical tool missing: $tool"
            ((missing++))
        fi
    done
    
    if [ $missing -gt 0 ]; then
        log_fail "Cannot run tests without critical tools"
        exit 1
    fi
}

# Run kernel module tests
run_kernel_tests() {
    log_info "=== Kernel Module Tests ==="
    
    if [ "$SKIP_KERNEL_BUILD" = "1" ] && [ "$KERNEL_BUILD_AVAILABLE" != "1" ]; then
        skip_test "Kernel module build" "No kernel headers available"
        return
    fi
    
    if [ -d "drivers" ] && [ -f "drivers/Makefile" ]; then
        run_test "Kernel module build" "make -C drivers clean && make -C drivers"
    else
        skip_test "Kernel module build" "No drivers directory found"
    fi
}

# Run unit tests
run_unit_tests() {
    log_info "=== Unit Tests ==="
    
    # Try to build and run C unit tests
    if [ -f "tests/unit/test_mpu6050.c" ]; then
        if command -v gcc >/dev/null 2>&1; then
            # Try with CUnit if available
            if pkg-config --exists cunit 2>/dev/null || [ -f "/usr/include/CUnit/CUnit.h" ]; then
                run_test "MPU6050 C unit tests" "gcc -o tests/unit/test_mpu6050 tests/unit/test_mpu6050.c -lcunit && ./tests/unit/test_mpu6050"
            else
                skip_test "MPU6050 C unit tests" "CUnit not available"
            fi
        fi
    fi
    
    # Try Google Test if available
    if [ -f "tests/unit/test_main.cpp" ]; then
        if command -v g++ >/dev/null 2>&1; then
            # Check for Google Test
            if [ -d "/usr/src/gtest" ] || [ -f "/usr/lib/libgtest.a" ] || pkg-config --exists gtest 2>/dev/null; then
                run_test "Google Test suite" "g++ -o tests/unit/test_main tests/unit/test_main.cpp tests/unit/test_mpu6050.cpp -lgtest -lgtest_main -pthread && ./tests/unit/test_main"
            else
                skip_test "Google Test suite" "Google Test not available"
            fi
        fi
    fi
    
    # Run make test if available
    if [ -f "Makefile" ] && grep -q "^test:" Makefile 2>/dev/null; then
        run_test "Make test target" "make test"
    fi
}

# Run integration tests
run_integration_tests() {
    log_info "=== Integration Tests ==="
    
    if [ -d "tests/integration" ]; then
        if [ -f "tests/integration/run_tests.sh" ]; then
            run_test "Integration test suite" "bash tests/integration/run_tests.sh"
        else
            skip_test "Integration tests" "No test runner found"
        fi
    else
        skip_test "Integration tests" "No integration test directory"
    fi
}

# Run E2E tests
run_e2e_tests() {
    log_info "=== End-to-End Tests ==="
    
    # Check for Docker if needed
    if [ "$SKIP_DOCKER_TESTS" = "1" ]; then
        skip_test "Docker E2E tests" "Docker not available"
    elif [ -f "tests/e2e/docker/docker-compose.yml" ]; then
        if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
            run_test "Docker E2E tests" "cd tests/e2e/docker && docker compose up --abort-on-container-exit"
        else
            skip_test "Docker E2E tests" "Docker daemon not running"
        fi
    fi
    
    # Python E2E tests
    if [ -f "tests/e2e/framework/test_e2e.py" ]; then
        if command -v python3 >/dev/null 2>&1; then
            # Check for pytest
            if python3 -m pytest --version >/dev/null 2>&1; then
                run_test "Python E2E tests" "python3 -m pytest tests/e2e/framework/test_e2e.py -v"
            else
                skip_test "Python E2E tests" "pytest not available"
            fi
        fi
    fi
    
    # Simulator tests
    if [ -f "tests/e2e/simulator/i2c_simulator.c" ]; then
        if command -v gcc >/dev/null 2>&1; then
            run_test "I2C Simulator" "gcc -o tests/e2e/simulator/i2c_simulator tests/e2e/simulator/i2c_simulator.c -pthread && ./tests/e2e/simulator/i2c_simulator --test"
        fi
    fi
}

# Run lint checks
run_lint_tests() {
    log_info "=== Linting ==="
    
    # cppcheck if available
    if command -v cppcheck >/dev/null 2>&1; then
        run_test "Cppcheck analysis" "cppcheck --error-exitcode=1 --enable=warning drivers/ include/ 2>/dev/null"
    else
        skip_test "Cppcheck" "Not installed"
    fi
    
    # clang-format check
    if command -v clang-format >/dev/null 2>&1; then
        # Just check, don't fail on format issues
        log_info "Checking code formatting..."
        find drivers/ include/ -name "*.c" -o -name "*.h" | xargs clang-format -n 2>&1 | tee format-check.log
        if [ -s format-check.log ]; then
            log_info "Code formatting issues found (not failing)"
        else
            log_pass "Code formatting check"
        fi
    else
        skip_test "Code formatting" "clang-format not available"
    fi
}

# Main execution
main() {
    check_required_tools
    
    case "$TEST_CATEGORY" in
        kernel)
            run_kernel_tests
            ;;
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        e2e)
            run_e2e_tests
            ;;
        lint)
            run_lint_tests
            ;;
        all)
            run_kernel_tests
            run_unit_tests
            run_integration_tests
            run_e2e_tests
            run_lint_tests
            ;;
        *)
            log_fail "Unknown test category: $TEST_CATEGORY"
            exit 1
            ;;
    esac
    
    # Summary
    echo ""
    log_info "========================================="
    log_info "Test Summary"
    log_info "========================================="
    echo "Tests Run:     $TESTS_RUN"
    echo -e "Tests Passed:  ${GREEN}$TESTS_PASSED${NC}"
    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "Tests Failed:  ${RED}$TESTS_FAILED${NC}"
    else
        echo -e "Tests Failed:  $TESTS_FAILED"
    fi
    echo -e "Tests Skipped: ${YELLOW}$TESTS_SKIPPED${NC}"
    log_info "========================================="
    
    # Determine exit status
    if [ $TESTS_FAILED -gt 0 ]; then
        log_fail "TESTS FAILED"
        exit 1
    elif [ $TESTS_RUN -eq 0 ]; then
        log_fail "No tests were run!"
        exit 1
    elif [ $TESTS_PASSED -eq 0 ] && [ $TESTS_SKIPPED -gt 0 ]; then
        log_info "All available tests were skipped"
        # Don't fail if we only have skipped tests in CI
        if [ "$GITHUB_ACTIONS" == "true" ]; then
            log_info "Allowing skipped tests in CI environment"
            exit 0
        else
            exit 1
        fi
    else
        log_pass "All tests passed!"
        exit 0
    fi
}

main "$@"