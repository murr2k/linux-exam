#!/bin/bash

# validate-build.sh - Comprehensive build validation script
# Author: Murray Kopit <murr2k@gmail.com>

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
TESTS_DIR="${PROJECT_ROOT}/tests"
LOG_FILE="${BUILD_DIR}/build-validation.log"
VERBOSE=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_verbose() {
    if [[ $VERBOSE -eq 1 ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1" | tee -a "$LOG_FILE"
    else
        echo "$1" >> "$LOG_FILE"
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Comprehensive build validation for MPU-6050 kernel driver project.

OPTIONS:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    -c, --clean         Clean all build artifacts before validation
    -k, --kernel-only   Only validate kernel module build
    -t, --tests-only    Only validate test build
    --install-deps      Install missing dependencies (requires sudo)
    --docker           Use Docker for validation
    --report FILE       Generate detailed report to FILE

EXAMPLES:
    $0                  # Basic validation
    $0 -v -c            # Verbose validation with clean build
    $0 --kernel-only    # Only validate kernel module
    $0 --install-deps   # Install dependencies and validate
    $0 --docker         # Run validation in Docker container

EOF
}

# Parse command line arguments
CLEAN_BUILD=0
KERNEL_ONLY=0
TESTS_ONLY=0
INSTALL_DEPS=0
USE_DOCKER=0
REPORT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=1
            shift
            ;;
        -k|--kernel-only)
            KERNEL_ONLY=1
            shift
            ;;
        -t|--tests-only)
            TESTS_ONLY=1
            shift
            ;;
        --install-deps)
            INSTALL_DEPS=1
            shift
            ;;
        --docker)
            USE_DOCKER=1
            shift
            ;;
        --report)
            REPORT_FILE="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Initialize
mkdir -p "$BUILD_DIR"
echo "Build validation started at $(date)" > "$LOG_FILE"

log_info "Starting MPU-6050 build validation"
log_info "Project root: $PROJECT_ROOT"

# System information
log_info "Gathering system information..."
{
    echo "=== System Information ==="
    echo "Date: $(date)"
    echo "Hostname: $(hostname)"
    echo "Kernel: $(uname -r)"
    echo "Distribution: $(lsb_release -d 2>/dev/null | cut -f2- || echo 'Unknown')"
    echo "Architecture: $(uname -m)"
    echo "CPUs: $(nproc)"
    echo "Memory: $(free -h | grep '^Mem:' | awk '{print $2}')"
    echo ""
} >> "$LOG_FILE"

# Check basic tools
check_basic_tools() {
    log_info "Checking basic build tools..."
    local tools=("gcc" "make" "git" "pkg-config")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            local version=$(${tool} --version 2>/dev/null | head -n1 || echo "version unknown")
            log_verbose "$tool: $version"
        else
            missing_tools+=("$tool")
            log_error "$tool not found"
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing basic tools: ${missing_tools[*]}"
        if [[ $INSTALL_DEPS -eq 1 ]]; then
            log_info "Installing basic tools..."
            sudo apt-get update
            sudo apt-get install -y build-essential git pkg-config
        else
            log_error "Please install missing tools or use --install-deps"
            return 1
        fi
    fi
    
    log_success "Basic tools check passed"
    return 0
}

# Check kernel development environment
check_kernel_environment() {
    log_info "Checking kernel development environment..."
    
    local kernel_version=$(uname -r)
    local kernel_headers="/lib/modules/$kernel_version/build"
    
    log_verbose "Kernel version: $kernel_version"
    
    if [[ ! -d "$kernel_headers" ]]; then
        log_error "Kernel headers not found at $kernel_headers"
        if [[ $INSTALL_DEPS -eq 1 ]]; then
            log_info "Installing kernel headers..."
            sudo apt-get update
            sudo apt-get install -y "linux-headers-$kernel_version" || {
                log_warning "Specific kernel headers not available, trying generic..."
                sudo apt-get install -y linux-headers-generic
            }
        else
            log_error "Please install kernel headers or use --install-deps"
            return 1
        fi
    else
        log_success "Kernel headers found: $kernel_headers"
    fi
    
    # Check for essential kernel build files
    local required_files=(
        "$kernel_headers/Makefile"
        "$kernel_headers/Module.symvers"
        "/proc/version"
        "/proc/kallsyms"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_verbose "Found: $file"
        else
            log_warning "Missing: $file"
        fi
    done
    
    return 0
}

# Check test dependencies
check_test_dependencies() {
    log_info "Checking test dependencies..."
    
    # Check for Google Test
    if pkg-config --exists gtest >/dev/null 2>&1; then
        local gtest_version=$(pkg-config --modversion gtest)
        log_success "Google Test found: $gtest_version"
    else
        log_error "Google Test not found"
        if [[ $INSTALL_DEPS -eq 1 ]]; then
            log_info "Installing Google Test..."
            sudo apt-get update
            sudo apt-get install -y libgtest-dev libgmock-dev
            
            # Build Google Test if needed
            if [[ ! -f "/usr/lib/x86_64-linux-gnu/libgtest.a" ]] && [[ ! -f "/usr/lib/libgtest.a" ]]; then
                log_info "Building Google Test from source..."
                cd /usr/src/gtest
                sudo cmake CMakeLists.txt
                sudo make
                sudo cp lib/*.a /usr/lib/
                cd "$PROJECT_ROOT"
            fi
        else
            log_error "Please install Google Test or use --install-deps"
            return 1
        fi
    fi
    
    # Check for other test tools
    local test_tools=("lcov" "gcov" "valgrind" "cppcheck" "clang-format")
    
    for tool in "${test_tools[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            log_success "$tool found"
        else
            log_warning "$tool not found (optional)"
            if [[ $INSTALL_DEPS -eq 1 ]]; then
                log_info "Installing $tool..."
                sudo apt-get install -y "$tool" || log_warning "Failed to install $tool"
            fi
        fi
    done
    
    return 0
}

# Validate kernel module build
validate_kernel_build() {
    log_info "Validating kernel module build..."
    
    cd "$PROJECT_ROOT"
    
    if [[ $CLEAN_BUILD -eq 1 ]]; then
        log_info "Cleaning previous build..."
        make clean >/dev/null 2>&1 || true
    fi
    
    log_info "Building kernel module..."
    if make modules >>"$LOG_FILE" 2>&1; then
        log_success "Kernel module built successfully"
        
        # Check if module file was created
        if [[ -f "$BUILD_DIR/mpu6050.ko" ]]; then
            local module_size=$(stat -c%s "$BUILD_DIR/mpu6050.ko")
            log_success "Module file: $BUILD_DIR/mpu6050.ko (${module_size} bytes)"
            
            # Check module info
            if command -v modinfo >/dev/null 2>&1; then
                log_verbose "Module information:"
                modinfo "$BUILD_DIR/mpu6050.ko" >> "$LOG_FILE" 2>&1 || true
            fi
        else
            log_error "Module file not found after build"
            return 1
        fi
    else
        log_error "Kernel module build failed"
        return 1
    fi
    
    return 0
}

# Validate test builds
validate_test_builds() {
    log_info "Validating test builds..."
    
    cd "$TESTS_DIR"
    
    if [[ $CLEAN_BUILD -eq 1 ]]; then
        log_info "Cleaning test build..."
        make clean >/dev/null 2>&1 || true
    fi
    
    # Try to build tests
    log_info "Building tests..."
    if make all >>"$LOG_FILE" 2>&1; then
        log_success "Tests built successfully"
        
        # List built executables
        if [[ -d "build/bin" ]]; then
            local executables=(build/bin/*)
            for exe in "${executables[@]}"; do
                if [[ -x "$exe" ]]; then
                    local exe_size=$(stat -c%s "$exe")
                    log_success "Test executable: $exe (${exe_size} bytes)"
                fi
            done
        fi
    else
        log_error "Test build failed"
        return 1
    fi
    
    return 0
}

# Run quick smoke tests
run_smoke_tests() {
    log_info "Running smoke tests..."
    
    cd "$TESTS_DIR"
    
    # Try to run C++ tests
    if [[ -x "build/bin/mpu6050_tests" ]]; then
        log_info "Running C++ unit tests..."
        if timeout 30 ./build/bin/mpu6050_tests >>"$LOG_FILE" 2>&1; then
            log_success "C++ unit tests passed"
        else
            log_warning "C++ unit tests failed or timed out"
        fi
    fi
    
    # Try to run C tests  
    if [[ -x "build/bin/mpu6050_tests_c_tests" ]]; then
        log_info "Running C unit tests..."
        if timeout 30 ./build/bin/mpu6050_tests_c_tests >>"$LOG_FILE" 2>&1; then
            log_success "C unit tests passed"
        else
            log_warning "C unit tests failed or timed out"
        fi
    fi
    
    # Try to run E2E tests
    if [[ -x "build/bin/mpu6050_tests_e2e" ]]; then
        log_info "Running E2E tests..."
        if timeout 30 ./build/bin/mpu6050_tests_e2e >>"/dev/null" 2>&1; then
            log_success "E2E tests passed"
        else
            log_warning "E2E tests failed or timed out (expected without hardware)"
        fi
    fi
    
    return 0
}

# Docker-based validation
validate_with_docker() {
    log_info "Running validation with Docker..."
    
    cd "$PROJECT_ROOT"
    
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker not found"
        if [[ $INSTALL_DEPS -eq 1 ]]; then
            log_info "Installing Docker..."
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker "$USER"
            log_warning "Please log out and back in for Docker group membership to take effect"
        fi
        return 1
    fi
    
    # Build Docker image if Dockerfile exists
    if [[ -f "docker/Dockerfile.dev" ]]; then
        log_info "Building Docker development image..."
        docker build -f docker/Dockerfile.dev -t mpu6050-dev . >>$LOG_FILE 2>&1
        
        log_info "Running validation in Docker container..."
        docker run --rm -v "$PROJECT_ROOT:/workspace" mpu6050-dev \
            /workspace/scripts/validate-build.sh --kernel-only >>$LOG_FILE 2>&1
    else
        log_warning "Docker development file not found"
    fi
    
    return 0
}

# Generate comprehensive report
generate_report() {
    local report_file="$1"
    
    log_info "Generating comprehensive report: $report_file"
    
    {
        echo "MPU-6050 Kernel Driver Build Validation Report"
        echo "=============================================="
        echo "Generated: $(date)"
        echo ""
        
        echo "Build Environment:"
        echo "  Kernel: $(uname -r)"
        echo "  GCC: $(gcc --version | head -n1)"
        echo "  Make: $(make --version | head -n1)"
        echo ""
        
        echo "Project Structure:"
        find "$PROJECT_ROOT" -type f -name "*.c" -o -name "*.h" -o -name "Makefile" | \
            grep -v "build/" | sort
        echo ""
        
        echo "Build Artifacts:"
        find "$BUILD_DIR" -name "*.ko" -o -name "*.o" 2>/dev/null | sort || echo "None found"
        echo ""
        
        echo "Test Executables:"
        find "$TESTS_DIR/build" -type f -executable 2>/dev/null | sort || echo "None found"
        echo ""
        
        echo "Detailed Build Log:"
        echo "==================="
        cat "$LOG_FILE"
        
    } > "$report_file"
    
    log_success "Report generated: $report_file"
}

# Main validation function
main() {
    local exit_code=0
    
    # Basic tools check
    if ! check_basic_tools; then
        exit_code=1
    fi
    
    if [[ $USE_DOCKER -eq 1 ]]; then
        validate_with_docker
        if [[ -n "$REPORT_FILE" ]]; then
            generate_report "$REPORT_FILE"
        fi
        return $?
    fi
    
    # Kernel environment check
    if [[ $TESTS_ONLY -eq 0 ]]; then
        if ! check_kernel_environment; then
            exit_code=1
        fi
    fi
    
    # Test dependencies check
    if [[ $KERNEL_ONLY -eq 0 ]]; then
        if ! check_test_dependencies; then
            exit_code=1
        fi
    fi
    
    # Build validation
    if [[ $TESTS_ONLY -eq 0 ]]; then
        if ! validate_kernel_build; then
            exit_code=1
        fi
    fi
    
    if [[ $KERNEL_ONLY -eq 0 ]]; then
        if ! validate_test_builds; then
            exit_code=1
        fi
        
        run_smoke_tests || true  # Don't fail on smoke test failures
    fi
    
    # Generate report if requested
    if [[ -n "$REPORT_FILE" ]]; then
        generate_report "$REPORT_FILE"
    fi
    
    # Summary
    if [[ $exit_code -eq 0 ]]; then
        log_success "Build validation completed successfully!"
        log_info "Log file: $LOG_FILE"
    else
        log_error "Build validation failed with errors!"
        log_info "Check log file for details: $LOG_FILE"
    fi
    
    return $exit_code
}

# Run main function
main "$@"