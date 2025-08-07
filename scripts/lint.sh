#!/bin/bash

# MPU-6050 Kernel Driver Linting and Code Quality Script
# Author: Murray Kopit <murr2k@gmail.com>
# Description: Comprehensive code quality analysis for kernel drivers

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LINT_RESULTS_DIR="${PROJECT_ROOT}/lint-results"
CLANG_FORMAT_CONFIG="${PROJECT_ROOT}/.clang-format"

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
MPU-6050 Kernel Driver Linting Script

Usage: $0 [OPTIONS]

OPTIONS:
    --format-check      Run clang-format check
    --format-fix        Apply clang-format fixes
    --static-analysis   Run cppcheck static analysis
    --security-scan     Run security analysis tools
    --checkpatch        Run Linux kernel checkpatch.pl
    --sparse            Run sparse semantic checker
    --all               Run all checks
    --fix               Apply automatic fixes where possible
    --verbose           Enable verbose output
    --help              Show this help message

EXAMPLES:
    $0 --all                    # Run all linting checks
    $0 --format-check           # Check code formatting only
    $0 --format-fix             # Fix code formatting
    $0 --static-analysis        # Run static analysis only
    $0 --security-scan          # Security analysis only

RETURN CODES:
    0                           All checks passed
    1                           Format issues found
    2                           Static analysis warnings
    4                           Security issues found
    8                           Checkpatch violations
    (Combined for multiple issues)
EOF
}

# Setup results directory
setup_results_dir() {
    log "Setting up lint results directory..."
    mkdir -p "${LINT_RESULTS_DIR}"
    
    # Create timestamp for this run
    TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
    export TIMESTAMP
    
    success "Results will be saved to: ${LINT_RESULTS_DIR}"
}

# Find source files
find_source_files() {
    log "Finding source files..."
    
    # Find C source and header files, excluding build directories
    SOURCE_FILES=$(find "${PROJECT_ROOT}" \
        -type f \
        \( -name "*.c" -o -name "*.h" \) \
        -not -path "*/build/*" \
        -not -path "*/.*" \
        -not -path "*/node_modules/*" \
        2>/dev/null || true)
    
    if [[ -z "${SOURCE_FILES}" ]]; then
        warn "No source files found"
        return 1
    fi
    
    log "Found $(echo "${SOURCE_FILES}" | wc -l) source files"
    echo "${SOURCE_FILES}" > "${LINT_RESULTS_DIR}/source_files_${TIMESTAMP}.txt"
    
    export SOURCE_FILES
}

# Create sample source files if none exist
create_sample_files() {
    log "Creating sample source files for demonstration..."
    
    mkdir -p "${PROJECT_ROOT}/drivers" "${PROJECT_ROOT}/include"
    
    # Create sample header file
    if [[ ! -f "${PROJECT_ROOT}/include/mpu6050.h" ]]; then
        cat > "${PROJECT_ROOT}/include/mpu6050.h" << 'EOF'
/* SPDX-License-Identifier: GPL-2.0 */
/*
 * MPU-6050 6-axis gyroscope and accelerometer driver
 * 
 * Copyright (C) 2024 Murray Kopit <murr2k@gmail.com>
 */

#ifndef _MPU6050_H_
#define _MPU6050_H_

#include <linux/device.h>
#include <linux/i2c.h>
#include <linux/mutex.h>
#include <linux/types.h>

/* MPU-6050 I2C address */
#define MPU6050_I2C_ADDR		0x68

/* Register definitions */
#define MPU6050_REG_PWR_MGMT_1		0x6B
#define MPU6050_REG_GYRO_CONFIG		0x1B
#define MPU6050_REG_ACCEL_CONFIG	0x1C
#define MPU6050_REG_ACCEL_XOUT_H	0x3B
#define MPU6050_REG_GYRO_XOUT_H		0x43

/* Power management bits */
#define MPU6050_PWR_MGMT_1_SLEEP	BIT(6)
#define MPU6050_PWR_MGMT_1_RESET	BIT(7)

/**
 * struct mpu6050_data - MPU-6050 device data
 * @client: I2C client
 * @dev: Device structure
 * @lock: Mutex for device access
 * @gyro_range: Current gyroscope range setting
 * @accel_range: Current accelerometer range setting
 */
struct mpu6050_data {
	struct i2c_client *client;
	struct device *dev;
	struct mutex lock;
	u8 gyro_range;
	u8 accel_range;
};

/* Function prototypes */
int mpu6050_probe(struct i2c_client *client, const struct i2c_device_id *id);
void mpu6050_remove(struct i2c_client *client);
int mpu6050_read_raw(struct mpu6050_data *data, u8 reg, s16 *val);
int mpu6050_write_reg(struct mpu6050_data *data, u8 reg, u8 val);

#endif /* _MPU6050_H_ */
EOF
    fi
    
    # Create sample source file
    if [[ ! -f "${PROJECT_ROOT}/drivers/mpu6050_main.c" ]]; then
        cat > "${PROJECT_ROOT}/drivers/mpu6050_main.c" << 'EOF'
// SPDX-License-Identifier: GPL-2.0
/*
 * MPU-6050 6-axis gyroscope and accelerometer driver
 * 
 * Copyright (C) 2024 Murray Kopit <murr2k@gmail.com>
 */

#include <linux/delay.h>
#include <linux/device.h>
#include <linux/i2c.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/slab.h>

#include "../include/mpu6050.h"

static const struct i2c_device_id mpu6050_id[] = {
	{ "mpu6050", 0 },
	{ }
};
MODULE_DEVICE_TABLE(i2c, mpu6050_id);

static const struct of_device_id mpu6050_of_match[] = {
	{ .compatible = "invensense,mpu6050" },
	{ }
};
MODULE_DEVICE_TABLE(of, mpu6050_of_match);

/**
 * mpu6050_write_reg - Write to MPU-6050 register
 * @data: Device data structure
 * @reg: Register address
 * @val: Value to write
 *
 * Return: 0 on success, negative error code on failure
 */
int mpu6050_write_reg(struct mpu6050_data *data, u8 reg, u8 val)
{
	int ret;
	
	mutex_lock(&data->lock);
	ret = i2c_smbus_write_byte_data(data->client, reg, val);
	mutex_unlock(&data->lock);
	
	if (ret < 0)
		dev_err(data->dev, "Failed to write reg 0x%02x: %d\n", reg, ret);
	
	return ret;
}

/**
 * mpu6050_read_raw - Read raw data from MPU-6050
 * @data: Device data structure  
 * @reg: Starting register address
 * @val: Pointer to store the read value
 *
 * Return: 0 on success, negative error code on failure
 */
int mpu6050_read_raw(struct mpu6050_data *data, u8 reg, s16 *val)
{
	int ret;
	__be16 raw_val;
	
	mutex_lock(&data->lock);
	ret = i2c_smbus_read_i2c_block_data(data->client, reg, 
					    sizeof(raw_val), (u8 *)&raw_val);
	mutex_unlock(&data->lock);
	
	if (ret < 0) {
		dev_err(data->dev, "Failed to read reg 0x%02x: %d\n", reg, ret);
		return ret;
	}
	
	*val = be16_to_cpu(raw_val);
	return 0;
}

/**
 * mpu6050_init_device - Initialize MPU-6050 device
 * @data: Device data structure
 *
 * Return: 0 on success, negative error code on failure
 */
static int mpu6050_init_device(struct mpu6050_data *data)
{
	int ret;
	
	/* Reset device */
	ret = mpu6050_write_reg(data, MPU6050_REG_PWR_MGMT_1, 
				MPU6050_PWR_MGMT_1_RESET);
	if (ret < 0)
		return ret;
	
	msleep(100);
	
	/* Wake up device */
	ret = mpu6050_write_reg(data, MPU6050_REG_PWR_MGMT_1, 0);
	if (ret < 0)
		return ret;
	
	/* Set default ranges */
	data->gyro_range = 0;	/* ±250°/s */
	data->accel_range = 0;	/* ±2g */
	
	dev_info(data->dev, "MPU-6050 initialized successfully\n");
	return 0;
}

/**
 * mpu6050_probe - I2C probe function
 * @client: I2C client
 * @id: I2C device ID
 *
 * Return: 0 on success, negative error code on failure
 */
int mpu6050_probe(struct i2c_client *client, const struct i2c_device_id *id)
{
	struct mpu6050_data *data;
	int ret;
	
	if (!i2c_check_functionality(client->adapter, I2C_FUNC_SMBUS_I2C_BLOCK)) {
		dev_err(&client->dev, "I2C adapter doesn't support block transfers\n");
		return -ENODEV;
	}
	
	data = devm_kzalloc(&client->dev, sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;
	
	data->client = client;
	data->dev = &client->dev;
	mutex_init(&data->lock);
	
	i2c_set_clientdata(client, data);
	
	ret = mpu6050_init_device(data);
	if (ret < 0)
		return ret;
	
	dev_info(&client->dev, "MPU-6050 probe completed\n");
	return 0;
}

/**
 * mpu6050_remove - I2C remove function
 * @client: I2C client
 */
void mpu6050_remove(struct i2c_client *client)
{
	struct mpu6050_data *data = i2c_get_clientdata(client);
	
	mutex_destroy(&data->lock);
	dev_info(&client->dev, "MPU-6050 removed\n");
}

static struct i2c_driver mpu6050_driver = {
	.driver = {
		.name = "mpu6050",
		.of_match_table = mpu6050_of_match,
	},
	.probe = mpu6050_probe,
	.remove = mpu6050_remove,
	.id_table = mpu6050_id,
};

module_i2c_driver(mpu6050_driver);

MODULE_AUTHOR("Murray Kopit <murr2k@gmail.com>");
MODULE_DESCRIPTION("MPU-6050 6-axis gyroscope and accelerometer driver");
MODULE_LICENSE("GPL v2");
EOF
    fi
    
    success "Sample source files created"
}

# Run clang-format check
run_format_check() {
    local fix_mode=${1:-0}
    local exit_code=0
    
    if [[ $fix_mode -eq 1 ]]; then
        log "Running clang-format with automatic fixes..."
    else
        log "Running clang-format check..."
    fi
    
    if ! command -v clang-format >/dev/null 2>&1; then
        warn "clang-format not found, skipping format check"
        return 0
    fi
    
    local format_issues="${LINT_RESULTS_DIR}/format_issues_${TIMESTAMP}.txt"
    
    echo "# clang-format Results - $(date)" > "${format_issues}"
    echo "" >> "${format_issues}"
    
    while IFS= read -r file; do
        if [[ $fix_mode -eq 1 ]]; then
            log "Formatting: ${file}"
            if clang-format -i --style=file:"${CLANG_FORMAT_CONFIG}" "${file}"; then
                echo "FIXED: ${file}" >> "${format_issues}"
            else
                echo "ERROR: ${file}" >> "${format_issues}"
                exit_code=1
            fi
        else
            local diff_output
            diff_output=$(clang-format --style=file:"${CLANG_FORMAT_CONFIG}" "${file}" | diff -u "${file}" - || true)
            
            if [[ -n "${diff_output}" ]]; then
                echo "=== ${file} ===" >> "${format_issues}"
                echo "${diff_output}" >> "${format_issues}"
                echo "" >> "${format_issues}"
                exit_code=1
            fi
        fi
    done <<< "${SOURCE_FILES}"
    
    if [[ $exit_code -eq 0 ]]; then
        if [[ $fix_mode -eq 1 ]]; then
            success "Code formatting applied successfully"
        else
            success "Code formatting check passed"
        fi
    else
        if [[ $fix_mode -eq 1 ]]; then
            error "Some files could not be formatted"
        else
            error "Code formatting issues found (see ${format_issues})"
        fi
    fi
    
    return $exit_code
}

# Run static analysis with cppcheck
run_static_analysis() {
    log "Running static analysis with cppcheck..."
    local exit_code=0
    
    if ! command -v cppcheck >/dev/null 2>&1; then
        warn "cppcheck not found, skipping static analysis"
        return 0
    fi
    
    local analysis_results="${LINT_RESULTS_DIR}/static_analysis_${TIMESTAMP}.txt"
    local analysis_xml="${LINT_RESULTS_DIR}/static_analysis_${TIMESTAMP}.xml"
    
    # Run cppcheck with comprehensive checks
    cppcheck \
        --enable=all \
        --std=c99 \
        --platform=unix64 \
        --suppress=missingIncludeSystem \
        --suppress=unusedFunction \
        --suppress=unmatchedSuppression \
        --inline-suppr \
        --quiet \
        --template='{file}:{line}: {severity}: {message} [{id}]' \
        --xml \
        --xml-version=2 \
        --output-file="${analysis_xml}" \
        "${PROJECT_ROOT}/drivers" "${PROJECT_ROOT}/include" 2>"${analysis_results}"
    
    # Check results
    if [[ -s "${analysis_results}" ]]; then
        local warning_count
        warning_count=$(grep -c ": warning:" "${analysis_results}" 2>/dev/null || echo "0")
        local error_count  
        error_count=$(grep -c ": error:" "${analysis_results}" 2>/dev/null || echo "0")
        
        if [[ $error_count -gt 0 ]]; then
            error "Static analysis found ${error_count} errors and ${warning_count} warnings"
            exit_code=2
        elif [[ $warning_count -gt 0 ]]; then
            warn "Static analysis found ${warning_count} warnings"
            exit_code=2
        else
            success "Static analysis passed"
        fi
    else
        success "Static analysis completed with no issues"
    fi
    
    return $exit_code
}

# Run security analysis
run_security_scan() {
    log "Running security analysis..."
    local exit_code=0
    
    local security_results="${LINT_RESULTS_DIR}/security_scan_${TIMESTAMP}.txt"
    
    echo "# Security Analysis Results - $(date)" > "${security_results}"
    echo "" >> "${security_results}"
    
    # Run flawfinder if available
    if command -v flawfinder >/dev/null 2>&1; then
        echo "=== Flawfinder Results ===" >> "${security_results}"
        if ! flawfinder --quiet --dataonly "${PROJECT_ROOT}/drivers" "${PROJECT_ROOT}/include" >> "${security_results}" 2>&1; then
            exit_code=4
        fi
        echo "" >> "${security_results}"
    else
        warn "flawfinder not found, skipping security scan"
    fi
    
    # Check for common security issues manually
    echo "=== Manual Security Checks ===" >> "${security_results}"
    
    # Check for dangerous functions
    local dangerous_funcs="strcpy strcat sprintf gets"
    for func in $dangerous_funcs; do
        local matches
        matches=$(grep -rn "${func}(" "${PROJECT_ROOT}/drivers" "${PROJECT_ROOT}/include" 2>/dev/null || true)
        if [[ -n "${matches}" ]]; then
            echo "WARNING: Potentially unsafe function '${func}' found:" >> "${security_results}"
            echo "${matches}" >> "${security_results}"
            echo "" >> "${security_results}"
            exit_code=4
        fi
    done
    
    # Check for missing input validation patterns
    local validation_patterns="copy_from_user copy_to_user"
    for pattern in $validation_patterns; do
        local matches
        matches=$(grep -rn "${pattern}" "${PROJECT_ROOT}/drivers" 2>/dev/null || true)
        if [[ -n "${matches}" ]]; then
            echo "INFO: Found ${pattern} usage (verify bounds checking):" >> "${security_results}"
            echo "${matches}" >> "${security_results}"
            echo "" >> "${security_results}"
        fi
    done
    
    if [[ $exit_code -eq 0 ]]; then
        success "Security scan completed with no major issues"
    else
        error "Security issues found (see ${security_results})"
    fi
    
    return $exit_code
}

# Run Linux kernel checkpatch
run_checkpatch() {
    log "Running Linux kernel checkpatch..."
    local exit_code=0
    
    # Try to find checkpatch.pl
    local checkpatch_script=""
    local possible_locations=(
        "/usr/src/linux-headers-$(uname -r)/scripts/checkpatch.pl"
        "/lib/modules/$(uname -r)/build/scripts/checkpatch.pl"
        "${PROJECT_ROOT}/scripts/checkpatch.pl"
        "$(which checkpatch.pl 2>/dev/null || true)"
    )
    
    for location in "${possible_locations[@]}"; do
        if [[ -f "${location}" ]]; then
            checkpatch_script="${location}"
            break
        fi
    done
    
    if [[ -z "${checkpatch_script}" ]]; then
        warn "checkpatch.pl not found, skipping kernel style check"
        return 0
    fi
    
    local checkpatch_results="${LINT_RESULTS_DIR}/checkpatch_${TIMESTAMP}.txt"
    
    echo "# Linux Kernel Checkpatch Results - $(date)" > "${checkpatch_results}"
    echo "# Using: ${checkpatch_script}" >> "${checkpatch_results}"
    echo "" >> "${checkpatch_results}"
    
    while IFS= read -r file; do
        echo "=== Checking: ${file} ===" >> "${checkpatch_results}"
        
        if ! perl "${checkpatch_script}" --no-tree --terse --file "${file}" >> "${checkpatch_results}" 2>&1; then
            exit_code=8
        fi
        
        echo "" >> "${checkpatch_results}"
    done <<< "${SOURCE_FILES}"
    
    if [[ $exit_code -eq 0 ]]; then
        success "Kernel checkpatch passed"
    else
        error "Kernel style violations found (see ${checkpatch_results})"
    fi
    
    return $exit_code
}

# Run sparse semantic checker
run_sparse() {
    log "Running sparse semantic checker..."
    local exit_code=0
    
    if ! command -v sparse >/dev/null 2>&1; then
        warn "sparse not found, skipping semantic analysis"
        return 0
    fi
    
    local sparse_results="${LINT_RESULTS_DIR}/sparse_${TIMESTAMP}.txt"
    
    echo "# Sparse Results - $(date)" > "${sparse_results}"
    echo "" >> "${sparse_results}"
    
    # Set up sparse environment
    export SPARSE_FLAGS="-D__KERNEL__ -Dlinux -D__linux__ -D__STDC__ -Dunix -D__unix__ -Wbitwise -Wcast-to-as -Wdefault-bitfield-sign -Wparen-string -Wptr-subtraction-blows -Wreturn-void -Wshadow -Wtypesign -Wundef -Wuninitialized"
    
    while IFS= read -r file; do
        echo "=== Checking: ${file} ===" >> "${sparse_results}"
        
        if ! sparse ${SPARSE_FLAGS} "${file}" >> "${sparse_results}" 2>&1; then
            exit_code=2
        fi
        
        echo "" >> "${sparse_results}"
    done <<< "${SOURCE_FILES}"
    
    if [[ $exit_code -eq 0 ]]; then
        success "Sparse semantic check passed"
    else
        warn "Sparse found potential issues (see ${sparse_results})"
    fi
    
    return $exit_code
}

# Generate summary report
generate_summary() {
    local total_exit_code=$1
    
    log "Generating lint summary report..."
    
    local summary_file="${LINT_RESULTS_DIR}/summary_${TIMESTAMP}.txt"
    
    cat > "${summary_file}" << EOF
# MPU-6050 Kernel Driver Lint Summary
Generated: $(date)
Project: ${PROJECT_ROOT}

## Overall Status
Exit Code: ${total_exit_code}
$(if [[ $total_exit_code -eq 0 ]]; then echo "Status: ✅ ALL CHECKS PASSED"; else echo "Status: ❌ ISSUES FOUND"; fi)

## Checks Performed
EOF
    
    # List all result files
    for result_file in "${LINT_RESULTS_DIR}"/*_"${TIMESTAMP}".txt; do
        if [[ -f "${result_file}" ]]; then
            local check_name
            check_name=$(basename "${result_file}" | sed "s/_${TIMESTAMP}.txt//")
            local issue_count
            issue_count=$(grep -c "ERROR\|WARNING\|error\|warning" "${result_file}" 2>/dev/null || echo "0")
            
            echo "- ${check_name}: ${issue_count} issues" >> "${summary_file}"
        fi
    done
    
    cat >> "${summary_file}" << EOF

## Files Analyzed
Total files: $(echo "${SOURCE_FILES}" | wc -l)

$(echo "${SOURCE_FILES}" | sed 's/^/- /')

## Exit Code Meanings
- 0: All checks passed
- 1: Format issues
- 2: Static analysis warnings  
- 4: Security issues
- 8: Checkpatch violations
- Combined: Multiple issue types

## Next Steps
$(if [[ $total_exit_code -ne 0 ]]; then
    echo "1. Review individual result files in ${LINT_RESULTS_DIR}"
    echo "2. Fix identified issues"
    echo "3. Re-run linting with --fix for format issues"
    echo "4. Consider updating code style guidelines"
else
    echo "✅ All linting checks passed successfully!"
    echo "Code quality meets project standards."
fi)
EOF
    
    success "Summary report generated: ${summary_file}"
    
    # Show summary on console
    echo ""
    log "=== LINT SUMMARY ==="
    cat "${summary_file}" | grep -E "Status:|Exit Code:|Total files:" | sed 's/^/  /'
    echo ""
}

# Main execution logic
main() {
    local format_check=0
    local format_fix=0
    local static_analysis=0
    local security_scan=0
    local checkpatch=0
    local sparse=0
    local all=0
    local fix=0
    local verbose=0
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --format-check)
                format_check=1
                shift
                ;;
            --format-fix)
                format_fix=1
                shift
                ;;
            --static-analysis)
                static_analysis=1
                shift
                ;;
            --security-scan)
                security_scan=1
                shift
                ;;
            --checkpatch)
                checkpatch=1
                shift
                ;;
            --sparse)
                sparse=1
                shift
                ;;
            --all)
                all=1
                shift
                ;;
            --fix)
                fix=1
                shift
                ;;
            --verbose)
                verbose=1
                set -x
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
    
    # Default to --all if no specific checks requested
    if [[ $format_check -eq 0 && $format_fix -eq 0 && $static_analysis -eq 0 && $security_scan -eq 0 && $checkpatch -eq 0 && $sparse -eq 0 && $all -eq 0 ]]; then
        all=1
    fi
    
    log "Starting MPU-6050 code quality analysis..."
    
    setup_results_dir
    
    # Find source files or create samples
    if ! find_source_files; then
        create_sample_files
        find_source_files
    fi
    
    local total_exit_code=0
    
    # Run requested checks
    if [[ $all -eq 1 || $format_check -eq 1 || $format_fix -eq 1 ]]; then
        local format_mode=0
        if [[ $format_fix -eq 1 || $fix -eq 1 ]]; then
            format_mode=1
        fi
        
        if ! run_format_check $format_mode; then
            total_exit_code=$((total_exit_code | 1))
        fi
    fi
    
    if [[ $all -eq 1 || $static_analysis -eq 1 ]]; then
        if ! run_static_analysis; then
            total_exit_code=$((total_exit_code | 2))
        fi
    fi
    
    if [[ $all -eq 1 || $security_scan -eq 1 ]]; then
        if ! run_security_scan; then
            total_exit_code=$((total_exit_code | 4))
        fi
    fi
    
    if [[ $all -eq 1 || $checkpatch -eq 1 ]]; then
        if ! run_checkpatch; then
            total_exit_code=$((total_exit_code | 8))
        fi
    fi
    
    if [[ $all -eq 1 || $sparse -eq 1 ]]; then
        if ! run_sparse; then
            # Don't fail on sparse warnings, just inform
            log "Sparse analysis completed with warnings"
        fi
    fi
    
    # Generate summary
    generate_summary $total_exit_code
    
    if [[ $total_exit_code -eq 0 ]]; then
        success "All code quality checks completed successfully!"
    else
        error "Code quality issues found (exit code: ${total_exit_code})"
        log "Check ${LINT_RESULTS_DIR} for detailed results"
    fi
    
    exit $total_exit_code
}

# Run main function with all arguments
main "$@"