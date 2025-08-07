#!/bin/bash
#
# MPU-6050 E2E Test Docker Entrypoint Script
# Author: Murray Kopit <murr2k@gmail.com>
#
# This script handles the initialization, execution, and cleanup of E2E tests
# within the Docker container environment.

set -euo pipefail

# Script configuration
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
PID=$$

# Default configuration
TEST_HOME="${TEST_HOME:-/opt/mpu6050-test}"
TEST_RESULTS_DIR="${TEST_RESULTS_DIR:-/opt/mpu6050-test/results}"
TEST_LOGS_DIR="${TEST_LOGS_DIR:-/var/log/mpu6050-test}"
SOURCE_DIR="${SOURCE_DIR:-/opt/mpu6050-test/src}"
BUILD_DIR="${BUILD_DIR:-/opt/mpu6050-test/build}"

# Test configuration
TEST_ENV="${TEST_ENV:-docker}"
TEST_MODE="${TEST_MODE:-e2e}"
TEST_VERBOSE="${TEST_VERBOSE:-false}"
TEST_CONTINUOUS="${TEST_CONTINUOUS:-false}"
TEST_TIMEOUT="${TEST_TIMEOUT:-300}"
TEST_RETRIES="${TEST_RETRIES:-3}"
TEST_PARALLEL="${TEST_PARALLEL:-true}"

# Hardware simulation
SIMULATE_HARDWARE="${SIMULATE_HARDWARE:-true}"
SIMULATOR_ENABLED="${SIMULATOR_ENABLED:-true}"
I2C_SIMULATOR_BUS="${I2C_SIMULATOR_BUS:-1}"
MPU6050_I2C_ADDR="${MPU6050_I2C_ADDR:-0x68}"

# Coverage and profiling
COVERAGE_ENABLED="${COVERAGE_ENABLED:-true}"
COVERAGE_MIN_THRESHOLD="${COVERAGE_MIN_THRESHOLD:-80}"
PROFILING_ENABLED="${PROFILING_ENABLED:-false}"

# Logging configuration
LOG_LEVEL="${LOG_LEVEL:-INFO}"
LOG_FORMAT="${LOG_FORMAT:-detailed}"
COLORIZED_OUTPUT="${COLORIZED_OUTPUT:-true}"

# Performance testing
PERF_TEST_ENABLED="${PERF_TEST_ENABLED:-true}"
PERF_MIN_THROUGHPUT="${PERF_MIN_THROUGHPUT:-50}"
PERF_TEST_DURATION="${PERF_TEST_DURATION:-60}"

# CI/CD integration
CI="${CI:-false}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}"

# Color codes for output
if [ "${COLORIZED_OUTPUT}" = "true" ] && [ -t 1 ]; then
    export COLOR_RED="\033[31m"
    export COLOR_GREEN="\033[32m"
    export COLOR_YELLOW="\033[33m"
    export COLOR_BLUE="\033[34m"
    export COLOR_MAGENTA="\033[35m"
    export COLOR_CYAN="\033[36m"
    export COLOR_RESET="\033[0m"
else
    export COLOR_RED=""
    export COLOR_GREEN=""
    export COLOR_YELLOW=""
    export COLOR_BLUE=""
    export COLOR_MAGENTA=""
    export COLOR_CYAN=""
    export COLOR_RESET=""
fi

# Logging functions
log() {
    local level="$1"
    shift
    local timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    echo -e "[${timestamp}] [${level}] [${SCRIPT_NAME}:${PID}] $*" | tee -a "${TEST_LOGS_DIR}/entrypoint.log"
}

log_info() {
    log "INFO" "${COLOR_BLUE}$*${COLOR_RESET}"
}

log_warn() {
    log "WARN" "${COLOR_YELLOW}$*${COLOR_RESET}"
}

log_error() {
    log "ERROR" "${COLOR_RED}$*${COLOR_RESET}"
}

log_success() {
    log "SUCCESS" "${COLOR_GREEN}$*${COLOR_RESET}"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    log_info "Starting cleanup process..."
    
    # Stop any running simulators
    if [ "${SIMULATOR_ENABLED}" = "true" ]; then
        stop_simulator
    fi
    
    # Unload test modules
    cleanup_modules
    
    # Collect final logs
    collect_logs
    
    # Generate test report
    generate_final_report "${exit_code}"
    
    log_info "Cleanup completed with exit code: ${exit_code}"
    exit "${exit_code}"
}

# Set up trap for cleanup
trap cleanup EXIT
trap 'log_error "Received SIGTERM, initiating graceful shutdown..."; exit 143' TERM
trap 'log_error "Received SIGINT, initiating graceful shutdown..."; exit 130' INT

# Environment validation
validate_environment() {
    log_info "Validating test environment..."
    
    # Check required directories
    for dir in "${TEST_HOME}" "${TEST_RESULTS_DIR}" "${TEST_LOGS_DIR}" "${SOURCE_DIR}"; do
        if [ ! -d "${dir}" ]; then
            log_error "Required directory not found: ${dir}"
            return 1
        fi
    done
    
    # Check build tools
    for tool in gcc make python3; do
        if ! command -v "${tool}" >/dev/null 2>&1; then
            log_error "Required tool not found: ${tool}"
            return 1
        fi
    done
    
    # Check kernel headers
    if [ ! -d "/lib/modules/$(uname -r)/build" ]; then
        log_error "Kernel headers not found for $(uname -r)"
        return 1
    fi
    
    # Create necessary files
    touch "${TEST_LOGS_DIR}/entrypoint.log"
    touch "${TEST_LOGS_DIR}/test-execution.log"
    touch "${TEST_LOGS_DIR}/simulator.log"
    
    log_success "Environment validation completed successfully"
    return 0
}

# Module building function
build_modules() {
    log_info "Building MPU-6050 kernel modules..."
    
    cd "${SOURCE_DIR}"
    
    # Clean previous builds
    make clean > "${TEST_LOGS_DIR}/build.log" 2>&1 || true
    
    # Build main module
    if make modules >> "${TEST_LOGS_DIR}/build.log" 2>&1; then
        log_success "Main module built successfully"
    else
        log_error "Failed to build main module"
        cat "${TEST_LOGS_DIR}/build.log"
        return 1
    fi
    
    # Build test modules
    cd "${SOURCE_DIR}/tests/e2e"
    if make >> "${TEST_LOGS_DIR}/build.log" 2>&1; then
        log_success "Test modules built successfully"
    else
        log_error "Failed to build test modules"
        cat "${TEST_LOGS_DIR}/build.log"
        return 1
    fi
    
    return 0
}

# Simulator initialization
start_simulator() {
    if [ "${SIMULATOR_ENABLED}" = "true" ]; then
        log_info "Starting I2C simulator..."
        
        # Load simulator module if available
        if [ -f "/opt/simulator/src/i2c_simulator.ko" ]; then
            if insmod "/opt/simulator/src/i2c_simulator.ko" >> "${TEST_LOGS_DIR}/simulator.log" 2>&1; then
                log_success "Simulator module loaded"
            else
                log_warn "Failed to load simulator module, using software simulation"
            fi
        fi
        
        # Create device node for simulation
        if [ "${SIMULATE_HARDWARE}" = "true" ] && [ ! -c /dev/mpu6050 ]; then
            log_info "Creating simulated device node..."
            mknod /dev/mpu6050 c 242 0 2>/dev/null || true
            chmod 666 /dev/mpu6050 2>/dev/null || true
        fi
        
        # Start Python simulation daemon if needed
        if [ "${SIMULATE_HARDWARE}" = "true" ]; then
            python3 "${SOURCE_DIR}/tests/utils/simulator_daemon.py" \
                --bus "${I2C_SIMULATOR_BUS}" \
                --address "${MPU6050_I2C_ADDR}" \
                --daemon \
                --log "${TEST_LOGS_DIR}/simulator.log" &
            
            SIMULATOR_PID=$!
            echo "${SIMULATOR_PID}" > "${TEST_LOGS_DIR}/simulator.pid"
            log_info "Simulator daemon started with PID: ${SIMULATOR_PID}"
            
            # Wait for simulator to initialize
            sleep 2
        fi
    fi
}

# Simulator cleanup
stop_simulator() {
    if [ "${SIMULATOR_ENABLED}" = "true" ]; then
        log_info "Stopping simulator..."
        
        # Stop daemon
        if [ -f "${TEST_LOGS_DIR}/simulator.pid" ]; then
            local pid
            pid=$(cat "${TEST_LOGS_DIR}/simulator.pid")
            if kill -0 "${pid}" 2>/dev/null; then
                kill "${pid}" 2>/dev/null || true
                sleep 1
                kill -9 "${pid}" 2>/dev/null || true
            fi
            rm -f "${TEST_LOGS_DIR}/simulator.pid"
        fi
        
        # Unload simulator module
        rmmod i2c_simulator 2>/dev/null || true
        
        log_info "Simulator stopped"
    fi
}

# Module cleanup
cleanup_modules() {
    log_info "Cleaning up kernel modules..."
    
    # Unload main module
    rmmod mpu6050 2>/dev/null || true
    
    # Clean build artifacts
    cd "${SOURCE_DIR}" && make clean >/dev/null 2>&1 || true
    
    log_info "Module cleanup completed"
}

# Test execution functions
run_c_tests() {
    log_info "Running C-based E2E tests..."
    
    cd "${SOURCE_DIR}/tests/e2e"
    
    local test_args=()
    [ "${TEST_VERBOSE}" = "true" ] && test_args+=("-v")
    [ "${TEST_CONTINUOUS}" = "true" ] && test_args+=("-c")
    
    # Run main E2E test
    timeout "${TEST_TIMEOUT}" ./test_mpu6050_e2e "${test_args[@]}" \
        >> "${TEST_LOGS_DIR}/test-execution.log" 2>&1
    local c_exit_code=$?
    
    # Run validation tests
    timeout "${TEST_TIMEOUT}" ./validate_ranges "${test_args[@]}" \
        >> "${TEST_LOGS_DIR}/test-execution.log" 2>&1
    local val_exit_code=$?
    
    if [ ${c_exit_code} -eq 0 ] && [ ${val_exit_code} -eq 0 ]; then
        log_success "C tests completed successfully"
        return 0
    else
        log_error "C tests failed (exit codes: ${c_exit_code}, ${val_exit_code})"
        return 1
    fi
}

run_python_tests() {
    log_info "Running Python-based E2E tests..."
    
    cd "${SOURCE_DIR}/tests/e2e"
    
    local pytest_args=()
    [ "${TEST_VERBOSE}" = "true" ] && pytest_args+=("-v")
    [ "${TEST_PARALLEL}" = "true" ] && pytest_args+=("-n" "auto")
    [ "${COVERAGE_ENABLED}" = "true" ] && pytest_args+=("--cov" "--cov-report=xml" "--cov-report=html")
    
    pytest_args+=("--timeout=${TEST_TIMEOUT}")
    pytest_args+=("--junit-xml=${TEST_RESULTS_DIR}/pytest-results.xml")
    
    python3 -m pytest "${pytest_args[@]}" test_mpu6050_e2e.py \
        >> "${TEST_LOGS_DIR}/test-execution.log" 2>&1
    local py_exit_code=$?
    
    if [ ${py_exit_code} -eq 0 ]; then
        log_success "Python tests completed successfully"
        return 0
    else
        log_error "Python tests failed (exit code: ${py_exit_code})"
        return 1
    fi
}

run_performance_tests() {
    if [ "${PERF_TEST_ENABLED}" = "true" ]; then
        log_info "Running performance tests..."
        
        cd "${SOURCE_DIR}/tests/e2e"
        
        # Run performance benchmark
        python3 -c "
import sys
sys.path.append('${SOURCE_DIR}')
from tests.utils.performance_test import run_performance_suite
result = run_performance_suite(
    duration=${PERF_TEST_DURATION},
    min_throughput=${PERF_MIN_THROUGHPUT},
    log_file='${TEST_LOGS_DIR}/performance.log'
)
sys.exit(0 if result else 1)
" >> "${TEST_LOGS_DIR}/test-execution.log" 2>&1
        
        local perf_exit_code=$?
        
        if [ ${perf_exit_code} -eq 0 ]; then
            log_success "Performance tests completed successfully"
            return 0
        else
            log_error "Performance tests failed (exit code: ${perf_exit_code})"
            return 1
        fi
    else
        log_info "Performance tests disabled"
        return 0
    fi
}

# Log collection
collect_logs() {
    log_info "Collecting test logs and artifacts..."
    
    # Copy kernel logs
    dmesg > "${TEST_LOGS_DIR}/kernel.log" 2>/dev/null || true
    
    # Copy coverage reports if enabled
    if [ "${COVERAGE_ENABLED}" = "true" ]; then
        find "${SOURCE_DIR}" -name "*.gcov" -exec cp {} "${TEST_RESULTS_DIR}/" \; 2>/dev/null || true
        find "${SOURCE_DIR}" -name "coverage.xml" -exec cp {} "${TEST_RESULTS_DIR}/" \; 2>/dev/null || true
        find "${SOURCE_DIR}" -name "htmlcov" -type d -exec cp -r {} "${TEST_RESULTS_DIR}/" \; 2>/dev/null || true
    fi
    
    # Collect system information
    {
        echo "=== System Information ==="
        uname -a
        echo "\n=== CPU Information ==="
        cat /proc/cpuinfo | head -20
        echo "\n=== Memory Information ==="
        cat /proc/meminfo | head -10
        echo "\n=== Kernel Modules ==="
        lsmod
        echo "\n=== Test Environment Variables ==="
        env | grep -E '^(TEST_|MPU6050_|SIMULATOR_|COVERAGE_|PERF_)' | sort
    } > "${TEST_LOGS_DIR}/system-info.log"
    
    # Create archive of all logs
    cd "${TEST_LOGS_DIR}"
    tar -czf "${TEST_RESULTS_DIR}/test-logs-${TIMESTAMP}.tar.gz" *.log 2>/dev/null || true
    
    log_success "Log collection completed"
}

# Final report generation
generate_final_report() {
    local exit_code=$1
    log_info "Generating final test report..."
    
    local report_file="${TEST_RESULTS_DIR}/final-report-${TIMESTAMP}.md"
    
    {
        echo "# MPU-6050 E2E Test Report"
        echo ""
        echo "**Test Execution Date:** $(date -u)"
        echo "**Environment:** ${TEST_ENV}"
        echo "**Mode:** ${TEST_MODE}"
        echo "**Exit Code:** ${exit_code}"
        echo ""
        echo "## Configuration"
        echo ""
        echo "- Hardware Simulation: ${SIMULATE_HARDWARE}"
        echo "- Simulator Enabled: ${SIMULATOR_ENABLED}"
        echo "- Coverage Enabled: ${COVERAGE_ENABLED}"
        echo "- Performance Tests: ${PERF_TEST_ENABLED}"
        echo "- Test Timeout: ${TEST_TIMEOUT}s"
        echo "- Test Retries: ${TEST_RETRIES}"
        echo ""
        echo "## Results Summary"
        echo ""
        if [ ${exit_code} -eq 0 ]; then
            echo "✅ **Overall Result: PASSED**"
        else
            echo "❌ **Overall Result: FAILED**"
        fi
        echo ""
        echo "## Log Files"
        echo ""
        find "${TEST_LOGS_DIR}" -name "*.log" -type f -exec basename {} \; | sort | sed 's/^/- /'
        echo ""
        echo "## Artifacts"
        echo ""
        find "${TEST_RESULTS_DIR}" -type f -exec basename {} \; | sort | sed 's/^/- /'
        echo ""
        echo "---"
        echo "*Generated by MPU-6050 E2E Test Suite*"
    } > "${report_file}"
    
    log_info "Final report generated: $(basename "${report_file}")"
}

# Main execution function
main() {
    log_info "Starting MPU-6050 E2E Test Suite"
    log_info "Environment: ${TEST_ENV}, Mode: ${TEST_MODE}"
    log_info "Process ID: ${PID}, Timestamp: ${TIMESTAMP}"
    
    # Parse command line arguments
    local run_all=false
    local run_c_only=false
    local run_python_only=false
    local run_perf_only=false
    local skip_build=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --run-all)
                run_all=true
                shift
                ;;
            --c-tests-only)
                run_c_only=true
                shift
                ;;
            --python-tests-only)
                run_python_only=true
                shift
                ;;
            --performance-only)
                run_perf_only=true
                shift
                ;;
            --skip-build)
                skip_build=true
                shift
                ;;
            --help|-h)
                cat << EOF
Usage: $0 [OPTIONS]

Options:
    --run-all              Run all test suites (default)
    --c-tests-only         Run only C-based tests
    --python-tests-only    Run only Python-based tests
    --performance-only     Run only performance tests
    --skip-build           Skip module building phase
    --help, -h             Show this help message

Environment Variables:
    TEST_VERBOSE           Enable verbose output (true/false)
    TEST_CONTINUOUS        Run tests continuously (true/false)
    TEST_TIMEOUT           Test timeout in seconds
    SIMULATE_HARDWARE      Enable hardware simulation (true/false)
    COVERAGE_ENABLED       Enable coverage collection (true/false)
    PERF_TEST_ENABLED      Enable performance tests (true/false)

Examples:
    $0 --run-all                    # Run complete test suite
    $0 --c-tests-only               # Run only C tests
    TEST_VERBOSE=true $0            # Run with verbose output
    SIMULATE_HARDWARE=false $0      # Run with real hardware
EOF
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Default to run all if no specific option
    if [ "$run_all" = false ] && [ "$run_c_only" = false ] && [ "$run_python_only" = false ] && [ "$run_perf_only" = false ]; then
        run_all=true
    fi
    
    # Step 1: Validate environment
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi
    
    # Step 2: Build modules (unless skipped)
    if [ "$skip_build" = false ]; then
        if ! build_modules; then
            log_error "Module building failed"
            exit 1
        fi
    fi
    
    # Step 3: Start simulator
    start_simulator
    
    # Step 4: Execute tests
    local overall_result=0
    
    if [ "$run_all" = true ] || [ "$run_c_only" = true ]; then
        if ! run_c_tests; then
            overall_result=1
        fi
    fi
    
    if [ "$run_all" = true ] || [ "$run_python_only" = true ]; then
        if ! run_python_tests; then
            overall_result=1
        fi
    fi
    
    if [ "$run_all" = true ] || [ "$run_perf_only" = true ]; then
        if ! run_performance_tests; then
            overall_result=1
        fi
    fi
    
    # Test execution completed - cleanup will be handled by trap
    if [ ${overall_result} -eq 0 ]; then
        log_success "All tests completed successfully!"
    else
        log_error "Some tests failed!"
    fi
    
    exit ${overall_result}
}

# Run main function with all arguments
main "$@"