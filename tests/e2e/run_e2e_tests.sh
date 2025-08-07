#!/bin/bash
#
# MPU-6050 End-to-End Test Suite Runner
#
# This script orchestrates comprehensive end-to-end testing of the MPU-6050
# driver including module loading/unloading, test execution, and result reporting.
#
# Features:
# - Automatic module loading and unloading
# - Multiple test execution strategies
# - Comprehensive result reporting
# - CI/CD integration support
# - Cleanup and error handling
#
# Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DRIVER_DIR="${PROJECT_ROOT}/drivers"
BUILD_DIR="${PROJECT_ROOT}/build"
RESULTS_DIR="${PROJECT_ROOT}/test-results/e2e"

# Test configuration
DEVICE_PATH="/dev/mpu6050"
MODULE_NAME="mpu6050_driver"
I2C_BUS="1"
I2C_ADDR="0x68"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_header() {
    echo -e "${CYAN}${1}${NC}"
    echo -e "${CYAN}$(printf '=%.0s' $(seq 1 ${#1}))${NC}"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    
    log_info "Performing cleanup..."
    
    # Remove I2C device if it exists
    if [ -f "/sys/bus/i2c/devices/i2c-${I2C_BUS}/${I2C_BUS}-$(printf "%04x" "${I2C_ADDR}")/delete_device" ]; then
        echo "${I2C_ADDR}" > "/sys/bus/i2c/devices/i2c-${I2C_BUS}/delete_device" 2>/dev/null || true
        log_info "I2C device removed"
    fi
    
    # Unload module if loaded
    if lsmod | grep -q "${MODULE_NAME}"; then
        rmmod "${MODULE_NAME}" 2>/dev/null || true
        log_info "Module ${MODULE_NAME} unloaded"
    fi
    
    # Remove device node if it exists
    if [ -c "${DEVICE_PATH}" ]; then
        rm -f "${DEVICE_PATH}" 2>/dev/null || true
        log_info "Device node ${DEVICE_PATH} removed"
    fi
    
    if [ $exit_code -eq 0 ]; then
        log_success "Cleanup completed successfully"
    else
        log_error "Cleanup completed with errors (exit code: $exit_code)"
    fi
    
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root for module loading/unloading"
        log_info "Please run: sudo $0 $*"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"
    
    local missing_deps=0
    
    # Check for required commands
    local commands=("modprobe" "lsmod" "insmod" "rmmod" "gcc" "make")
    for cmd in "${commands[@]}"; do
        if ! command -v "${cmd}" >/dev/null 2>&1; then
            log_error "Required command not found: ${cmd}"
            missing_deps=1
        fi
    done
    
    # Check for I2C tools (optional but helpful)
    if ! command -v i2cdetect >/dev/null 2>&1; then
        log_warning "i2c-tools not found - I2C bus scanning not available"
        log_info "Install with: apt-get install i2c-tools (Debian/Ubuntu) or yum install i2c-tools (RHEL/CentOS)"
    fi
    
    # Check for Python3 and required modules
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python3 not found"
        missing_deps=1
    else
        log_info "Python3 found: $(python3 --version)"
        
        # Check for optional Python modules
        python3 -c "import matplotlib" 2>/dev/null && log_info "Matplotlib available for visualization" || log_warning "Matplotlib not available - visualization disabled"
        python3 -c "import numpy" 2>/dev/null && log_info "NumPy available for advanced statistics" || log_warning "NumPy not available - advanced statistics disabled"
    fi
    
    # Check kernel version and module support
    local kernel_version=$(uname -r)
    log_info "Kernel version: ${kernel_version}"
    
    if [ ! -d "/lib/modules/${kernel_version}" ]; then
        log_error "Kernel modules directory not found: /lib/modules/${kernel_version}"
        missing_deps=1
    fi
    
    # Check for I2C support
    if [ ! -d "/sys/bus/i2c" ]; then
        log_error "I2C subsystem not available - check kernel configuration"
        missing_deps=1
    fi
    
    # Check I2C bus
    if [ ! -d "/sys/bus/i2c/devices/i2c-${I2C_BUS}" ]; then
        log_warning "I2C bus ${I2C_BUS} not found - will attempt to use anyway"
    else
        log_info "I2C bus ${I2C_BUS} found"
    fi
    
    if [ $missing_deps -eq 1 ]; then
        log_error "Missing required dependencies"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# Build the driver module
build_driver() {
    log_header "Building MPU-6050 Driver"
    
    cd "${PROJECT_ROOT}"
    
    # Clean previous build
    if [ -d "${BUILD_DIR}" ]; then
        log_info "Cleaning previous build..."
        make clean || true
    fi
    
    # Build driver
    log_info "Building driver module..."
    if make > "${RESULTS_DIR}/build.log" 2>&1; then
        log_success "Driver module built successfully"
    else
        log_error "Driver build failed - check ${RESULTS_DIR}/build.log"
        cat "${RESULTS_DIR}/build.log"
        exit 1
    fi
    
    # Verify module file exists
    local module_file="${BUILD_DIR}/${MODULE_NAME}.ko"
    if [ ! -f "${module_file}" ]; then
        log_error "Module file not found: ${module_file}"
        exit 1
    fi
    
    log_info "Module file: ${module_file} ($(stat -c%s "${module_file}" | numfmt --to=iec))"
}

# Load the driver module
load_driver() {
    log_header "Loading MPU-6050 Driver"
    
    local module_file="${BUILD_DIR}/${MODULE_NAME}.ko"
    
    # Unload if already loaded
    if lsmod | grep -q "${MODULE_NAME}"; then
        log_info "Module already loaded, unloading first..."
        rmmod "${MODULE_NAME}"
    fi
    
    # Load the module
    log_info "Loading module: ${module_file}"
    if insmod "${module_file}"; then
        log_success "Module loaded successfully"
    else
        log_error "Failed to load module"
        exit 1
    fi
    
    # Verify module is loaded
    if lsmod | grep -q "${MODULE_NAME}"; then
        local module_info=$(lsmod | grep "${MODULE_NAME}")
        log_info "Module info: ${module_info}"
    else
        log_error "Module not found in lsmod output"
        exit 1
    fi
    
    # Check kernel messages
    log_info "Recent kernel messages:"
    dmesg | tail -10 | grep -i mpu6050 || log_warning "No MPU-6050 messages in dmesg"
}

# Create I2C device
create_i2c_device() {
    log_header "Creating I2C Device"
    
    # Create the I2C device
    local device_path="/sys/bus/i2c/devices/i2c-${I2C_BUS}/new_device"
    
    if [ -f "${device_path}" ]; then
        log_info "Creating I2C device on bus ${I2C_BUS} at address ${I2C_ADDR}"
        echo "mpu6050 ${I2C_ADDR}" > "${device_path}"
        
        # Wait for device creation
        sleep 2
        
        # Verify device was created
        local device_dir="/sys/bus/i2c/devices/i2c-${I2C_BUS}/${I2C_BUS}-$(printf "%04x" "${I2C_ADDR}")"
        if [ -d "${device_dir}" ]; then
            log_success "I2C device created: ${device_dir}"
        else
            log_warning "I2C device directory not found, but continuing with tests"
        fi
        
        # Check if character device was created
        sleep 2
        if [ -c "${DEVICE_PATH}" ]; then
            log_success "Character device created: ${DEVICE_PATH}"
            ls -l "${DEVICE_PATH}"
        else
            log_error "Character device not created: ${DEVICE_PATH}"
            exit 1
        fi
    else
        log_error "Cannot create I2C device - path not found: ${device_path}"
        exit 1
    fi
}

# Scan I2C bus (if i2c-tools available)
scan_i2c_bus() {
    if command -v i2cdetect >/dev/null 2>&1; then
        log_info "Scanning I2C bus ${I2C_BUS}:"
        i2cdetect -y "${I2C_BUS}" || log_warning "I2C bus scan failed"
    fi
}

# Run C test suite
run_c_tests() {
    log_header "Running C Test Suite"
    
    local test_binary="${SCRIPT_DIR}/test_mpu6050_e2e"
    local test_source="${SCRIPT_DIR}/test_mpu6050_e2e.c"
    
    # Compile test if needed
    if [ ! -x "${test_binary}" ] || [ "${test_source}" -nt "${test_binary}" ]; then
        log_info "Compiling C test suite..."
        gcc -Wall -Wextra -std=c99 -O2 \
            -I"${PROJECT_ROOT}/include" \
            -o "${test_binary}" \
            "${test_source}"
        
        if [ $? -eq 0 ]; then
            log_success "C test suite compiled successfully"
        else
            log_error "Failed to compile C test suite"
            return 1
        fi
    fi
    
    # Run tests
    log_info "Running C test suite..."
    local c_test_log="${RESULTS_DIR}/c_tests.log"
    
    if "${test_binary}" -v > "${c_test_log}" 2>&1; then
        log_success "C test suite completed successfully"
        
        # Show summary
        local summary=$(tail -20 "${c_test_log}" | grep -A 10 "TEST SUMMARY")
        if [ -n "${summary}" ]; then
            echo "${summary}"
        fi
    else
        log_error "C test suite failed - check ${c_test_log}"
        tail -50 "${c_test_log}"
        return 1
    fi
    
    return 0
}

# Run Python test suite
run_python_tests() {
    log_header "Running Python Test Suite"
    
    local python_script="${SCRIPT_DIR}/test_mpu6050_e2e.py"
    local python_test_log="${RESULTS_DIR}/python_tests.log"
    local csv_export="${RESULTS_DIR}/sensor_data.csv"
    local json_report="${RESULTS_DIR}/python_test_report.json"
    
    # Make sure the script is executable
    chmod +x "${python_script}"
    
    # Run Python tests
    log_info "Running Python test suite with comprehensive testing..."
    
    if python3 "${python_script}" \
        --verbose \
        --all \
        --export-csv "${csv_export}" \
        --report "${json_report}" \
        > "${python_test_log}" 2>&1; then
        
        log_success "Python test suite completed successfully"
        
        # Show final summary
        local summary=$(tail -30 "${python_test_log}" | grep -A 15 "FINAL TEST SUMMARY")
        if [ -n "${summary}" ]; then
            echo "${summary}"
        fi
        
        # Report generated files
        if [ -f "${csv_export}" ]; then
            log_info "Data exported to: ${csv_export} ($(wc -l < "${csv_export}") lines)"
        fi
        
        if [ -f "${json_report}" ]; then
            log_info "Test report generated: ${json_report}"
        fi
        
    else
        log_error "Python test suite failed - check ${python_test_log}"
        tail -50 "${python_test_log}"
        return 1
    fi
    
    return 0
}

# Run validation tests
run_validation_tests() {
    log_header "Running Range Validation Tests"
    
    local validation_binary="${SCRIPT_DIR}/validate_ranges"
    local validation_source="${SCRIPT_DIR}/validate_ranges.c"
    
    # Compile validation test if needed
    if [ ! -x "${validation_binary}" ] || [ "${validation_source}" -nt "${validation_binary}" ]; then
        log_info "Compiling range validation test..."
        gcc -Wall -Wextra -std=c99 -O2 -lm \
            -I"${PROJECT_ROOT}/include" \
            -o "${validation_binary}" \
            "${validation_source}"
        
        if [ $? -eq 0 ]; then
            log_success "Range validation test compiled successfully"
        else
            log_error "Failed to compile range validation test"
            return 1
        fi
    fi
    
    # Run validation tests
    log_info "Running range validation tests..."
    local validation_log="${RESULTS_DIR}/validation_tests.log"
    
    if "${validation_binary}" -v > "${validation_log}" 2>&1; then
        log_success "Range validation tests completed successfully"
        
        # Show summary
        tail -20 "${validation_log}" | grep -E "(PASS|FAIL|Summary)"
    else
        log_error "Range validation tests failed - check ${validation_log}"
        tail -30 "${validation_log}"
        return 1
    fi
    
    return 0
}

# Generate comprehensive test report
generate_report() {
    log_header "Generating Comprehensive Test Report"
    
    local report_file="${RESULTS_DIR}/comprehensive_report.html"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat > "${report_file}" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPU-6050 E2E Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f4f4f4; padding: 20px; border-radius: 5px; }
        .success { color: #008000; }
        .error { color: #ff0000; }
        .warning { color: #ff8000; }
        .section { margin: 20px 0; }
        .log-content { background-color: #f9f9f9; padding: 10px; border-left: 3px solid #ccc; font-family: monospace; white-space: pre-wrap; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>MPU-6050 End-to-End Test Report</h1>
        <p><strong>Generated:</strong> ${timestamp}</p>
        <p><strong>Device:</strong> ${DEVICE_PATH}</p>
        <p><strong>Kernel:</strong> $(uname -r)</p>
        <p><strong>Test Directory:</strong> ${RESULTS_DIR}</p>
    </div>

    <div class="section">
        <h2>Test Summary</h2>
        <table>
            <tr><th>Test Suite</th><th>Status</th><th>Details</th></tr>
EOF

    # Add test results to report
    local overall_status="PASS"
    
    # C Tests
    if [ -f "${RESULTS_DIR}/c_tests.log" ]; then
        local c_status="PASS"
        if ! grep -q "ALL TESTS PASSED" "${RESULTS_DIR}/c_tests.log"; then
            c_status="FAIL"
            overall_status="FAIL"
        fi
        echo "<tr><td>C Test Suite</td><td class=\"${c_status,,}\">${c_status}</td><td><a href=\"c_tests.log\">View Log</a></td></tr>" >> "${report_file}"
    fi
    
    # Python Tests
    if [ -f "${RESULTS_DIR}/python_tests.log" ]; then
        local py_status="PASS"
        if ! grep -q "Overall Success Rate: 100.0%" "${RESULTS_DIR}/python_tests.log"; then
            py_status="FAIL"
            overall_status="FAIL"
        fi
        echo "<tr><td>Python Test Suite</td><td class=\"${py_status,,}\">${py_status}</td><td><a href=\"python_tests.log\">View Log</a> | <a href=\"sensor_data.csv\">Data CSV</a> | <a href=\"python_test_report.json\">JSON Report</a></td></tr>" >> "${report_file}"
    fi
    
    # Validation Tests
    if [ -f "${RESULTS_DIR}/validation_tests.log" ]; then
        local val_status="PASS"
        if grep -q "FAIL" "${RESULTS_DIR}/validation_tests.log"; then
            val_status="FAIL"
            overall_status="FAIL"
        fi
        echo "<tr><td>Range Validation Tests</td><td class=\"${val_status,,}\">${val_status}</td><td><a href=\"validation_tests.log\">View Log</a></td></tr>" >> "${report_file}"
    fi
    
    cat >> "${report_file}" << EOF
        </table>
        
        <h3>Overall Status: <span class="${overall_status,,}">${overall_status}</span></h3>
    </div>

    <div class="section">
        <h2>System Information</h2>
        <div class="log-content">
Kernel: $(uname -a)
I2C Bus: ${I2C_BUS}
I2C Address: ${I2C_ADDR}
Module: ${MODULE_NAME}
Device Path: ${DEVICE_PATH}

Loaded Modules:
$(lsmod | grep -E "(i2c|mpu)" || echo "No relevant modules found")

Recent Kernel Messages:
$(dmesg | grep -i mpu6050 | tail -10 || echo "No MPU-6050 messages found")
        </div>
    </div>

    <div class="section">
        <h2>Build Information</h2>
        <div class="log-content">
$(cat "${RESULTS_DIR}/build.log" 2>/dev/null || echo "Build log not available")
        </div>
    </div>

</body>
</html>
EOF

    log_success "Comprehensive test report generated: ${report_file}"
    log_info "Open in browser: file://${report_file}"
}

# Print usage information
print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

MPU-6050 End-to-End Test Suite Runner

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -b, --build-only        Build driver module only
    -l, --load-only         Load driver module only (assumes built)
    -t, --test-only         Run tests only (assumes loaded)
    -c, --c-tests           Run C tests only
    -p, --python-tests      Run Python tests only
    -r, --validation-tests  Run validation tests only
    --no-cleanup            Skip cleanup on exit
    --i2c-bus BUS          I2C bus number (default: ${I2C_BUS})
    --i2c-addr ADDR        I2C address (default: ${I2C_ADDR})
    --device-path PATH     Device path (default: ${DEVICE_PATH})

EXAMPLES:
    $0                      # Run full test suite
    $0 -v                   # Run with verbose output
    $0 --c-tests            # Run C tests only
    $0 --python-tests       # Run Python tests only
    $0 --build-only         # Build module only
    $0 --no-cleanup         # Don't unload module after tests

NOTES:
    - This script must be run as root for module operations
    - Results are saved to: ${RESULTS_DIR}
    - Comprehensive HTML report is generated after completion
    - Use Ctrl+C to interrupt tests gracefully

EOF
}

# Parse command line arguments
parse_arguments() {
    local build_only=false
    local load_only=false
    local test_only=false
    local c_tests_only=false
    local python_tests_only=false
    local validation_tests_only=false
    local no_cleanup=false
    local verbose=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                set -x
                shift
                ;;
            -b|--build-only)
                build_only=true
                shift
                ;;
            -l|--load-only)
                load_only=true
                shift
                ;;
            -t|--test-only)
                test_only=true
                shift
                ;;
            -c|--c-tests)
                c_tests_only=true
                shift
                ;;
            -p|--python-tests)
                python_tests_only=true
                shift
                ;;
            -r|--validation-tests)
                validation_tests_only=true
                shift
                ;;
            --no-cleanup)
                no_cleanup=true
                trap - EXIT INT TERM  # Remove cleanup trap
                shift
                ;;
            --i2c-bus)
                I2C_BUS="$2"
                shift 2
                ;;
            --i2c-addr)
                I2C_ADDR="$2"
                shift 2
                ;;
            --device-path)
                DEVICE_PATH="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    # Set operation flags
    BUILD_ONLY=$build_only
    LOAD_ONLY=$load_only
    TEST_ONLY=$test_only
    C_TESTS_ONLY=$c_tests_only
    PYTHON_TESTS_ONLY=$python_tests_only
    VALIDATION_TESTS_ONLY=$validation_tests_only
    NO_CLEANUP=$no_cleanup
    VERBOSE=$verbose
}

# Main execution function
main() {
    # Parse arguments
    parse_arguments "$@"
    
    # Check if running as root
    check_root
    
    # Create results directory
    mkdir -p "${RESULTS_DIR}"
    
    # Start logging
    local main_log="${RESULTS_DIR}/main.log"
    exec 1> >(tee "${main_log}")
    exec 2>&1
    
    log_header "MPU-6050 End-to-End Test Suite"
    log_info "Started at: $(date)"
    log_info "Results directory: ${RESULTS_DIR}"
    log_info "Script directory: ${SCRIPT_DIR}"
    log_info "Project root: ${PROJECT_ROOT}"
    
    # Check prerequisites
    check_prerequisites
    
    # Execute based on options
    local exit_code=0
    
    if [ "$BUILD_ONLY" = true ]; then
        build_driver
    elif [ "$LOAD_ONLY" = true ]; then
        load_driver
        create_i2c_device
        scan_i2c_bus
    elif [ "$TEST_ONLY" = true ]; then
        # Run specific tests
        if [ "$C_TESTS_ONLY" = true ]; then
            run_c_tests || exit_code=1
        elif [ "$PYTHON_TESTS_ONLY" = true ]; then
            run_python_tests || exit_code=1
        elif [ "$VALIDATION_TESTS_ONLY" = true ]; then
            run_validation_tests || exit_code=1
        else
            # Run all tests
            run_c_tests || exit_code=1
            run_python_tests || exit_code=1
            run_validation_tests || exit_code=1
        fi
    else
        # Full test suite
        build_driver
        load_driver
        create_i2c_device
        scan_i2c_bus
        
        # Run all tests
        run_c_tests || exit_code=1
        run_python_tests || exit_code=1
        run_validation_tests || exit_code=1
    fi
    
    # Generate comprehensive report (unless build/load only)
    if [ "$BUILD_ONLY" = false ] && [ "$LOAD_ONLY" = false ]; then
        generate_report
    fi
    
    # Final status
    log_header "Test Suite Completed"
    if [ $exit_code -eq 0 ]; then
        log_success "All tests completed successfully!"
    else
        log_error "Some tests failed - check logs in ${RESULTS_DIR}"
    fi
    
    log_info "Completed at: $(date)"
    log_info "Check comprehensive report: ${RESULTS_DIR}/comprehensive_report.html"
    
    exit $exit_code
}

# Run main function with all arguments
main "$@"