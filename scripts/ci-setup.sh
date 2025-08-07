#!/bin/bash

# CI/CD Setup Script for MPU-6050 Kernel Driver
# Ensures all dependencies and configurations are ready

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[CI-SETUP] $*${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $*${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $*${NC}"
}

error() {
    echo -e "${RED}[ERROR] $*${NC}"
}

# Detect environment
detect_environment() {
    log "Detecting CI/CD environment..."
    
    if [[ "${GITHUB_ACTIONS}" == "true" ]]; then
        export CI_ENVIRONMENT="github-actions"
        log "Running in GitHub Actions"
    elif [[ "${GITLAB_CI}" == "true" ]]; then
        export CI_ENVIRONMENT="gitlab-ci"
        log "Running in GitLab CI"
    elif [[ "${CIRCLECI}" == "true" ]]; then
        export CI_ENVIRONMENT="circle-ci"
        log "Running in CircleCI"
    else
        export CI_ENVIRONMENT="local"
        log "Running in local environment"
    fi
}

# Check and install dependencies
install_dependencies() {
    log "Installing required dependencies..."
    
    # Update package list
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        
        # Core build dependencies
        sudo apt-get install -y \
            build-essential \
            linux-headers-$(uname -r) \
            linux-headers-generic \
            kmod \
            git \
            make \
            gcc \
            g++ \
            libc6-dev \
            pkg-config
            
        # Testing dependencies
        sudo apt-get install -y \
            libcunit1-dev \
            libcunit1 \
            cmake \
            lcov \
            gcov \
            valgrind
            
        # Linting dependencies
        sudo apt-get install -y \
            clang-format \
            cppcheck \
            flawfinder \
            sparse \
            coccinelle \
            perl \
            wget \
            curl
            
        success "Dependencies installed successfully"
    else
        error "apt-get not found. Manual dependency installation required."
        return 1
    fi
}

# Setup kernel development environment
setup_kernel_env() {
    log "Setting up kernel development environment..."
    
    KERNEL_VERSION=$(uname -r)
    KERNEL_DIR="/lib/modules/${KERNEL_VERSION}/build"
    
    if [[ ! -d "${KERNEL_DIR}" ]]; then
        error "Kernel headers not found at ${KERNEL_DIR}"
        log "Installing kernel headers..."
        
        sudo apt-get install -y linux-headers-${KERNEL_VERSION} || \
        sudo apt-get install -y linux-headers-generic
    fi
    
    if [[ -d "${KERNEL_DIR}" ]]; then
        success "Kernel headers found at ${KERNEL_DIR}"
        export KERNEL_DIR
        return 0
    else
        error "Failed to install kernel headers"
        return 1
    fi
}

# Create required directories
setup_directories() {
    log "Setting up project directories..."
    
    local dirs=(
        "build"
        "test-results"
        "test-results/unit"
        "test-results/integration"
        "coverage"
        "lint-results"
        "docs"
        "drivers"
        "include"
        "tests"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "${dir}"
        log "Created directory: ${dir}"
    done
    
    success "All directories created"
}

# Setup Google Test if needed
setup_gtest() {
    log "Setting up Google Test..."
    
    if pkg-config --exists gtest; then
        success "Google Test already available via pkg-config"
        return 0
    fi
    
    if [[ -f "/usr/lib/libgtest.a" ]]; then
        success "Google Test libraries found"
        return 0
    fi
    
    # Install from package manager first
    if sudo apt-get install -y libgtest-dev; then
        # Build from source if needed
        if [[ -d "/usr/src/gtest" ]]; then
            log "Building Google Test from source..."
            pushd /usr/src/gtest
            sudo cmake CMakeLists.txt
            sudo make
            sudo cp lib/*.a /usr/lib/ 2>/dev/null || \
            sudo cp *.a /usr/lib/ 2>/dev/null || \
            log "Google Test libraries already in place"
            popd
        fi
        success "Google Test setup complete"
    else
        warn "Could not install Google Test - tests may fail"
    fi
}

# Download checkpatch.pl if needed
download_checkpatch() {
    log "Setting up checkpatch.pl..."
    
    if [[ -f "scripts/checkpatch.pl" ]]; then
        success "checkpatch.pl already exists"
        return 0
    fi
    
    mkdir -p scripts
    
    log "Downloading checkpatch.pl from Linux kernel repository..."
    if wget -O scripts/checkpatch.pl https://raw.githubusercontent.com/torvalds/linux/master/scripts/checkpatch.pl; then
        chmod +x scripts/checkpatch.pl
        success "checkpatch.pl downloaded and made executable"
    else
        warn "Failed to download checkpatch.pl - kernel style checks will be skipped"
    fi
}

# Ensure script permissions
fix_permissions() {
    log "Fixing script permissions..."
    
    find scripts -name "*.sh" -type f -exec chmod +x {} \;
    
    if [[ -f "scripts/checkpatch.pl" ]]; then
        chmod +x scripts/checkpatch.pl
    fi
    
    success "Script permissions fixed"
}

# Create minimal source files if they don't exist
ensure_source_files() {
    log "Ensuring source files exist for testing..."
    
    # This will be handled by the build and lint scripts
    # which create sample files if none exist
    success "Source file check delegated to build scripts"
}

# Verify environment
verify_environment() {
    log "Verifying CI/CD environment setup..."
    
    local checks=0
    local failed=0
    
    # Check kernel headers
    checks=$((checks + 1))
    if [[ -d "/lib/modules/$(uname -r)/build" ]]; then
        success "✓ Kernel headers available"
    else
        error "✗ Kernel headers missing"
        failed=$((failed + 1))
    fi
    
    # Check build tools
    checks=$((checks + 1))
    if command -v gcc >/dev/null 2>&1 && command -v make >/dev/null 2>&1; then
        success "✓ Build tools available"
    else
        error "✗ Build tools missing"
        failed=$((failed + 1))
    fi
    
    # Check test tools
    checks=$((checks + 1))
    if pkg-config --exists cunit || [[ -f "/usr/lib/libcunit.a" ]]; then
        success "✓ Test framework available"
    else
        warn "⚠ Test framework may be missing"
    fi
    
    # Check linting tools
    checks=$((checks + 1))
    if command -v clang-format >/dev/null 2>&1 && command -v cppcheck >/dev/null 2>&1; then
        success "✓ Linting tools available"
    else
        warn "⚠ Some linting tools may be missing"
    fi
    
    log "Environment verification: $((checks - failed))/${checks} checks passed"
    
    if [[ $failed -eq 0 ]]; then
        success "Environment setup complete and verified!"
        return 0
    else
        error "Environment setup has ${failed} critical issues"
        return 1
    fi
}

# Main execution
main() {
    log "Starting CI/CD environment setup..."
    
    detect_environment
    install_dependencies
    setup_kernel_env
    setup_directories
    setup_gtest
    download_checkpatch
    fix_permissions
    ensure_source_files
    verify_environment
    
    success "CI/CD environment setup completed successfully!"
}

# Run main function
main "$@"