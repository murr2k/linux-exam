#!/bin/bash
"""
MPU-6050 End-to-End Test Runner Script

This script orchestrates the complete test execution process including:
- Environment setup and validation
- Module compilation and loading
- Test execution with proper isolation
- Result collection and analysis
- Comprehensive cleanup

Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DRIVERS_DIR="$PROJECT_ROOT/drivers"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results/e2e"
LOG_DIR="$TEST_RESULTS_DIR/logs"
REPORT_DIR="$TEST_RESULTS_DIR/reports"

# Test configuration
MODULE_NAME="mpu6050_driver"
MODULE_PATH="$DRIVERS_DIR/${MODULE_NAME}.ko"
DEVICE_NODE="/dev/mpu6050"
TEST_CONFIG_FILE="$SCRIPT_DIR/test_config.json"
PYTHON_VENV="$SCRIPT_DIR/.venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Global variables
VERBOSE=false
DRY_RUN=false
CLEANUP_ON_EXIT=true
KEEP_LOGS=true
TEST_SUITE=""
PARALLEL_JOBS=1
TIMEOUT=3600  # 1 hour default timeout
EXIT_CODE=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

log_debug() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $*" >&2
    fi
}

# Print usage information
usage() {
    cat << EOF
MPU-6050 End-to-End Test Runner

Usage: $0 [OPTIONS] [TEST_SUITE]

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -n, --dry-run           Show what would be done without executing
    -c, --no-cleanup        Don't cleanup on exit
    -k, --keep-logs         Keep log files after test completion
    -j, --jobs NUM          Number of parallel test jobs (default: 1)
    -t, --timeout SECONDS   Test timeout in seconds (default: 3600)
    -s, --suite SUITE       Run specific test suite only
    -l, --list-suites       List available test suites
    -r, --report-only       Generate reports from existing results
    -f, --force             Force execution even if environment checks fail

TEST_SUITES:
    module_tests           Module loading and initialization tests
    basic_functionality    Basic device functionality tests
    data_operations        Data reading and validation tests
    performance_tests      Performance and stress tests
    stress_tests           Long-duration stress and stability tests
    all                    Run all test suites (default)

EXAMPLES:
    $0                              # Run all tests
    $0 -v basic_functionality       # Run basic tests with verbose output
    $0 -j 4 performance_tests       # Run performance tests with 4 parallel jobs
    $0 --dry-run                    # Show what would be executed
    $0 --report-only                # Generate reports from existing results

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -c|--no-cleanup)
                CLEANUP_ON_EXIT=false
                shift
                ;;
            -k|--keep-logs)
                KEEP_LOGS=true
                shift
                ;;
            -j|--jobs)
                PARALLEL_JOBS="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -s|--suite)
                TEST_SUITE="$2"
                shift 2
                ;;
            -l|--list-suites)
                list_test_suites
                exit 0
                ;;
            -r|--report-only)
                generate_reports_only
                exit 0
                ;;
            -f|--force)
                FORCE_EXECUTION=true
                shift
                ;;
            *)
                if [[ -z "$TEST_SUITE" && ! "$1" =~ ^- ]]; then
                    TEST_SUITE="$1"
                else
                    log_error "Unknown option: $1"
                    usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Default to all tests if no suite specified
    if [[ -z "$TEST_SUITE" ]]; then
        TEST_SUITE="all"
    fi
}

# List available test suites
list_test_suites() {
    log_info "Available test suites:"
    echo "  module_tests          - Module loading and initialization tests"
    echo "  basic_functionality   - Basic device functionality tests"
    echo "  data_operations       - Data reading and validation tests"
    echo "  performance_tests     - Performance and stress tests"
    echo "  stress_tests          - Long-duration stress and stability tests"
    echo "  all                   - Run all test suites"
}

# Setup exit trap for cleanup
setup_exit_trap() {
    trap cleanup_and_exit EXIT
    trap 'cleanup_and_exit 130' INT
    trap 'cleanup_and_exit 143' TERM
}

# Cleanup function called on exit
cleanup_and_exit() {
    local exit_code=${1:-$EXIT_CODE}
    
    log_info "Cleaning up test environment..."
    
    if [[ "$CLEANUP_ON_EXIT" == true ]]; then
        # Unload kernel module if loaded
        if lsmod | grep -q "$MODULE_NAME"; then
            log_debug "Unloading module: $MODULE_NAME"
            if [[ "$DRY_RUN" == false ]]; then
                sudo rmmod "$MODULE_NAME" 2>/dev/null || true
            fi
        fi
        
        # Remove device node if it exists
        if [[ -e "$DEVICE_NODE" && "$DRY_RUN" == false ]]; then
            log_debug "Removing device node: $DEVICE_NODE"
            sudo rm -f "$DEVICE_NODE" 2>/dev/null || true
        fi
        
        # Kill any remaining test processes
        pkill -f "test_framework.py" 2>/dev/null || true
        
        # Clean up temporary files
        find "$TEST_RESULTS_DIR" -name "*.tmp" -delete 2>/dev/null || true
        
        # Compress logs if keeping them
        if [[ "$KEEP_LOGS" == true && -d "$LOG_DIR" ]]; then
            local timestamp=$(date +"%Y%m%d_%H%M%S")
            local archive_name="test_logs_${timestamp}.tar.gz"
            tar -czf "$TEST_RESULTS_DIR/$archive_name" -C "$LOG_DIR" . 2>/dev/null || true
            log_info "Logs archived to: $TEST_RESULTS_DIR/$archive_name"
        fi
    fi
    
    log_info "Cleanup completed"
    exit $exit_code
}

# Check system requirements and environment
check_environment() {
    log_info "Checking test environment..."
    
    local errors=0
    
    # Check if running as root or with sudo access
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        log_error "Root privileges required for module operations"
        ((errors++))
    fi
    
    # Check required directories exist
    for dir in "$DRIVERS_DIR" "$PROJECT_ROOT/include"; do
        if [[ ! -d "$dir" ]]; then
            log_error "Required directory not found: $dir"
            ((errors++))
        fi
    done
    
    # Check Python environment
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        ((errors++))
    fi
    
    # Check required Python packages
    local required_packages=("pytest" "numpy" "matplotlib" "psutil")
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            log_warn "Python package '$package' not available - some features may be limited"
        fi
    done
    
    # Check kernel development headers
    local kernel_version=$(uname -r)
    if [[ ! -d "/lib/modules/$kernel_version/build" ]]; then
        log_error "Kernel development headers not found for version $kernel_version"
        ((errors++))
    fi
    
    # Check required tools
    local required_tools=("make" "gcc" "insmod" "rmmod" "lsmod")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            ((errors++))
        fi
    done
    
    # Check I2C subsystem
    if [[ ! -e "/sys/bus/i2c" ]]; then
        log_warn "I2C subsystem not available - hardware tests may fail"
    fi
    
    # Check memory and disk space
    local available_memory=$(free -m | awk '/^Mem:/{print $7}')
    if [[ $available_memory -lt 512 ]]; then
        log_warn "Low available memory: ${available_memory}MB (recommended: 512MB+)"
    fi
    
    local available_disk=$(df "$TEST_RESULTS_DIR" | awk 'NR==2{print $4}')
    if [[ $available_disk -lt 1048576 ]]; then  # 1GB in KB
        log_warn "Low disk space: $(($available_disk/1024))MB (recommended: 1GB+)"
    fi
    
    if [[ $errors -gt 0 ]]; then
        log_error "Environment check failed with $errors errors"
        if [[ "${FORCE_EXECUTION:-false}" != true ]]; then
            return 1
        else
            log_warn "Continuing with --force flag despite errors"
        fi
    fi
    
    log_success "Environment check passed"
    return 0
}

# Setup test directories and files
setup_test_environment() {
    log_info "Setting up test environment..."
    
    if [[ "$DRY_RUN" == false ]]; then
        # Create required directories
        mkdir -p "$TEST_RESULTS_DIR" "$LOG_DIR" "$REPORT_DIR"
        
        # Create Python virtual environment if it doesn't exist
        if [[ ! -d "$PYTHON_VENV" ]]; then
            log_debug "Creating Python virtual environment"
            python3 -m venv "$PYTHON_VENV"
            source "$PYTHON_VENV/bin/activate"
            pip install -r "$SCRIPT_DIR/requirements.txt" || true
        fi
        
        # Generate test configuration
        generate_test_config
        
        # Set up log rotation
        setup_log_rotation
    fi
    
    log_success "Test environment setup completed"
}

# Generate test configuration file
generate_test_config() {
    local config_file="$TEST_CONFIG_FILE"
    
    cat > "$config_file" << EOF
{
    "device_path": "$DEVICE_NODE",
    "module_name": "$MODULE_NAME",
    "module_path": "$MODULE_PATH",
    "test_duration": 300,
    "sample_rate": 100.0,
    "stress_test_duration": 600,
    "concurrent_clients": $PARALLEL_JOBS,
    "memory_limit_mb": 64,
    "cpu_limit_percent": 25,
    "validate_ranges": true,
    "generate_reports": true,
    "verbose": $VERBOSE
}
EOF
    
    log_debug "Test configuration written to: $config_file"
}

# Setup log rotation
setup_log_rotation() {
    local max_logs=10
    local log_pattern="$LOG_DIR/test_*.log"
    
    # Remove old logs if we have too many
    local log_count=$(find "$LOG_DIR" -name "test_*.log" | wc -l)
    if [[ $log_count -gt $max_logs ]]; then
        find "$LOG_DIR" -name "test_*.log" -type f -printf '%T@ %p\n' | \
            sort -n | head -n $((log_count - max_logs)) | \
            cut -d' ' -f2- | xargs rm -f
    fi
}

# Compile kernel module
compile_module() {
    log_info "Compiling kernel module..."
    
    local build_dir="$DRIVERS_DIR"
    local makefile="$PROJECT_ROOT/Makefile"
    
    if [[ ! -f "$makefile" ]]; then
        log_error "Makefile not found: $makefile"
        return 1
    fi
    
    if [[ "$DRY_RUN" == false ]]; then
        log_debug "Building module with: make -C $PROJECT_ROOT drivers"
        
        if ! make -C "$PROJECT_ROOT" drivers 2>&1 | tee "$LOG_DIR/module_build.log"; then
            log_error "Module compilation failed"
            return 1
        fi
        
        if [[ ! -f "$MODULE_PATH" ]]; then
            log_error "Module file not found after compilation: $MODULE_PATH"
            return 1
        fi
        
        # Verify module
        if ! modinfo "$MODULE_PATH" &> /dev/null; then
            log_error "Invalid module file: $MODULE_PATH"
            return 1
        fi
    fi
    
    log_success "Module compilation completed"
    return 0
}

# Load kernel module
load_module() {
    log_info "Loading kernel module..."
    
    # Check if module is already loaded
    if lsmod | grep -q "$MODULE_NAME"; then
        log_info "Module already loaded, unloading first..."
        if [[ "$DRY_RUN" == false ]]; then
            sudo rmmod "$MODULE_NAME" || true
        fi
    fi
    
    if [[ "$DRY_RUN" == false ]]; then
        # Load the module
        if ! sudo insmod "$MODULE_PATH"; then
            log_error "Failed to load module: $MODULE_PATH"
            return 1
        fi
        
        # Wait for device node creation
        local timeout=10
        local count=0
        while [[ ! -e "$DEVICE_NODE" && $count -lt $timeout ]]; do
            sleep 1
            ((count++))
        done
        
        if [[ ! -e "$DEVICE_NODE" ]]; then
            log_error "Device node not created: $DEVICE_NODE"
            return 1
        fi
        
        # Set appropriate permissions
        sudo chmod 666 "$DEVICE_NODE" 2>/dev/null || true
    fi
    
    log_success "Module loaded successfully"
    return 0
}

# Execute test framework
run_tests() {
    log_info "Executing test framework..."
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local log_file="$LOG_DIR/test_execution_${timestamp}.log"
    local results_file="$REPORT_DIR/test_results_${timestamp}.json"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would execute test framework with suite: $TEST_SUITE"
        return 0
    fi
    
    # Activate Python virtual environment
    if [[ -d "$PYTHON_VENV" ]]; then
        source "$PYTHON_VENV/bin/activate"
    fi
    
    # Prepare test command
    local test_cmd=(
        python3 "$SCRIPT_DIR/test_framework.py"
        --config "$TEST_CONFIG_FILE"
        --suite "$TEST_SUITE"
        --results "$results_file"
        --timeout "$TIMEOUT"
    )
    
    if [[ "$VERBOSE" == true ]]; then
        test_cmd+=(--verbose)
    fi
    
    if [[ $PARALLEL_JOBS -gt 1 ]]; then
        test_cmd+=(--parallel-jobs "$PARALLEL_JOBS")
    fi
    
    log_debug "Test command: ${test_cmd[*]}"
    
    # Execute tests with timeout
    local test_exit_code=0
    if ! timeout "$TIMEOUT" "${test_cmd[@]}" 2>&1 | tee "$log_file"; then
        test_exit_code=$?
        if [[ $test_exit_code -eq 124 ]]; then
            log_error "Test execution timed out after $TIMEOUT seconds"
        else
            log_error "Test execution failed with exit code: $test_exit_code"
        fi
    fi
    
    # Check if results file was generated
    if [[ -f "$results_file" ]]; then
        log_success "Test results saved to: $results_file"
    else
        log_error "Test results file not generated"
        test_exit_code=1
    fi
    
    return $test_exit_code
}

# Generate comprehensive reports
generate_reports() {
    log_info "Generating test reports..."
    
    local latest_results=$(find "$REPORT_DIR" -name "test_results_*.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [[ -z "$latest_results" || ! -f "$latest_results" ]]; then
        log_error "No test results found for report generation"
        return 1
    fi
    
    if [[ "$DRY_RUN" == false ]]; then
        # Generate HTML report
        python3 "$SCRIPT_DIR/reports.py" --input "$latest_results" --format html --output "$REPORT_DIR/test_report.html"
        
        # Generate JUnit XML report
        python3 "$SCRIPT_DIR/reports.py" --input "$latest_results" --format junit --output "$REPORT_DIR/junit_results.xml"
        
        # Generate metrics JSON
        python3 "$SCRIPT_DIR/reports.py" --input "$latest_results" --format metrics --output "$REPORT_DIR/test_metrics.json"
        
        # Generate coverage report if available
        if command -v gcov &> /dev/null && [[ -d "$DRIVERS_DIR" ]]; then
            generate_coverage_report
        fi
    fi
    
    log_success "Reports generated in: $REPORT_DIR"
    return 0
}

# Generate coverage report
generate_coverage_report() {
    log_info "Generating code coverage report..."
    
    local coverage_dir="$REPORT_DIR/coverage"
    mkdir -p "$coverage_dir"
    
    # Run gcov on driver source files
    find "$DRIVERS_DIR" -name "*.gcda" -exec gcov {} \; 2>/dev/null || true
    
    # Move coverage files to report directory
    find . -name "*.gcov" -exec mv {} "$coverage_dir/" \; 2>/dev/null || true
    
    # Generate HTML coverage report if lcov is available
    if command -v lcov &> /dev/null && command -v genhtml &> /dev/null; then
        lcov --capture --directory "$DRIVERS_DIR" --output-file "$coverage_dir/coverage.info" 2>/dev/null || true
        genhtml "$coverage_dir/coverage.info" --output-directory "$coverage_dir/html" 2>/dev/null || true
        log_info "HTML coverage report: $coverage_dir/html/index.html"
    fi
}

# Generate reports from existing results
generate_reports_only() {
    log_info "Generating reports from existing results..."
    
    setup_test_environment
    generate_reports
    
    log_success "Report generation completed"
}

# Validate test results and determine exit code
validate_results() {
    local results_file="$1"
    
    if [[ ! -f "$results_file" ]]; then
        log_error "Results file not found: $results_file"
        return 1
    fi
    
    # Parse JSON results to determine success
    local total_tests=$(jq '.test_run_info.total_tests' "$results_file" 2>/dev/null || echo 0)
    local passed_tests=$(jq '.test_run_info.passed_tests' "$results_file" 2>/dev/null || echo 0)
    local failed_tests=$(jq '.test_run_info.failed_tests' "$results_file" 2>/dev/null || echo 0)
    
    log_info "Test Results Summary:"
    log_info "  Total Tests:  $total_tests"
    log_info "  Passed Tests: $passed_tests"
    log_info "  Failed Tests: $failed_tests"
    
    if [[ $failed_tests -gt 0 ]]; then
        log_error "Some tests failed"
        return 1
    elif [[ $total_tests -eq 0 ]]; then
        log_error "No tests were executed"
        return 1
    else
        log_success "All tests passed"
        return 0
    fi
}

# Main execution function
main() {
    log_info "MPU-6050 End-to-End Test Runner Starting..."
    log_info "Timestamp: $(date)"
    log_info "Working Directory: $(pwd)"
    log_info "Test Suite: $TEST_SUITE"
    
    # Setup
    setup_exit_trap
    
    # Environment validation
    if ! check_environment; then
        EXIT_CODE=1
        return
    fi
    
    # Test environment setup
    setup_test_environment
    
    # Module compilation
    if ! compile_module; then
        EXIT_CODE=1
        return
    fi
    
    # Module loading
    if ! load_module; then
        EXIT_CODE=1
        return
    fi
    
    # Test execution
    if ! run_tests; then
        EXIT_CODE=1
        # Continue to generate reports even if tests failed
    fi
    
    # Report generation
    generate_reports || true  # Don't fail on report generation errors
    
    # Validate results and set final exit code
    local latest_results=$(find "$REPORT_DIR" -name "test_results_*.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    if [[ -n "$latest_results" ]]; then
        if ! validate_results "$latest_results"; then
            EXIT_CODE=1
        fi
    fi
    
    if [[ $EXIT_CODE -eq 0 ]]; then
        log_success "Test execution completed successfully"
    else
        log_error "Test execution completed with errors"
    fi
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    parse_arguments "$@"
    main
fi