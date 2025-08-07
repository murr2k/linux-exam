#!/bin/bash

# Smart CI Setup Script for GitHub Actions
# Based on pretest findings - only installs what's actually missing
# Never fails for pre-installed tools

set +e  # Don't exit on error - handle gracefully

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }

# Track capabilities
CAPABILITIES_FILE="ci-capabilities.json"
echo '{"timestamp":"'$(date -Iseconds)'","environment":{' > "$CAPABILITIES_FILE"

# Detect environment
if [ "$GITHUB_ACTIONS" == "true" ]; then
    log_info "Running in GitHub Actions"
    echo '"ci":"github_actions",' >> "$CAPABILITIES_FILE"
    echo '"runner_os":"'$RUNNER_OS'",' >> "$CAPABILITIES_FILE"
else
    log_info "Running in local environment"
    echo '"ci":"local",' >> "$CAPABILITIES_FILE"
fi

# Function to check if a tool exists
tool_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to verify critical tools (must exist, won't install)
verify_critical_tool() {
    local tool=$1
    if tool_exists "$tool"; then
        log_success "$tool is available"
        echo '"'$tool'":"available",' >> "$CAPABILITIES_FILE"
        return 0
    else
        log_error "$tool is MISSING (critical)"
        echo '"'$tool'":"missing",' >> "$CAPABILITIES_FILE"
        return 1
    fi
}

# Function to install optional tool if missing
install_if_missing() {
    local tool=$1
    local package=${2:-$1}  # Use tool name as package name if not specified
    
    if tool_exists "$tool"; then
        log_success "$tool already available"
        echo '"'$tool'":"pre_installed",' >> "$CAPABILITIES_FILE"
        return 0
    fi
    
    log_info "Installing $package..."
    if sudo apt-get install -y "$package" 2>/dev/null; then
        log_success "$package installed successfully"
        echo '"'$tool'":"newly_installed",' >> "$CAPABILITIES_FILE"
        return 0
    else
        log_warn "$package could not be installed (optional)"
        echo '"'$tool'":"unavailable",' >> "$CAPABILITIES_FILE"
        return 1
    fi
}

echo ""
log_info "=== Verifying Critical Tools (Pre-installed in GitHub Actions) ==="

# These MUST exist - GitHub Actions always has them
# We do NOT try to install these
CRITICAL_MISSING=0

verify_critical_tool "gcc" || ((CRITICAL_MISSING++))
verify_critical_tool "g++" || ((CRITICAL_MISSING++))
verify_critical_tool "make" || ((CRITICAL_MISSING++))
verify_critical_tool "git" || ((CRITICAL_MISSING++))
verify_critical_tool "python3" || ((CRITICAL_MISSING++))

echo ""
log_info "=== Installing Optional Testing Tools ==="

# Update package lists (best effort)
log_info "Updating package lists..."
sudo apt-get update -qq 2>/dev/null || log_warn "Could not update package lists"

# Optional testing tools - install only if missing
install_if_missing "cppcheck"
install_if_missing "valgrind"
install_if_missing "lcov"
install_if_missing "gcovr"

# Testing libraries
install_if_missing "cunit" "libcunit1-dev"

# For Google Test, we need to check differently
if [ ! -d "/usr/src/gtest" ] && [ ! -f "/usr/lib/libgtest.a" ]; then
    log_info "Installing Google Test..."
    sudo apt-get install -y libgtest-dev 2>/dev/null || log_warn "Google Test not available"
else
    log_success "Google Test already available"
fi

echo ""
log_info "=== Setting up Python Testing Tools ==="

# Install Python testing packages via pip (more reliable than apt)
if tool_exists "pip3"; then
    log_info "Installing Python test packages..."
    pip3 install --user pytest coverage 2>/dev/null && log_success "Python test tools installed" || log_warn "Some Python packages unavailable"
    echo '"python_test_tools":"installed",' >> "$CAPABILITIES_FILE"
else
    log_warn "pip3 not available, skipping Python packages"
    echo '"python_test_tools":"skipped",' >> "$CAPABILITIES_FILE"
fi

echo ""
log_info "=== Checking Kernel Build Capability ==="

KERNEL_VERSION=$(uname -r)
if [ -d "/lib/modules/$KERNEL_VERSION/build" ]; then
    log_success "Kernel headers available for $KERNEL_VERSION"
    echo '"kernel_headers":"available",' >> "$CAPABILITIES_FILE"
    # Don't skip kernel builds - headers are available!
    echo "KERNEL_BUILD_AVAILABLE=1" >> "$GITHUB_ENV"
else
    log_warn "Kernel headers not found for $KERNEL_VERSION"
    echo '"kernel_headers":"missing",' >> "$CAPABILITIES_FILE"
    echo "SKIP_KERNEL_BUILD=1" >> "$GITHUB_ENV"
fi

echo ""
log_info "=== Checking Docker Availability ==="

if tool_exists "docker"; then
    log_success "Docker is available"
    echo '"docker":"available",' >> "$CAPABILITIES_FILE"
    
    # Check if Docker daemon is running
    if docker info >/dev/null 2>&1; then
        log_success "Docker daemon is running"
        echo '"docker_daemon":"running",' >> "$CAPABILITIES_FILE"
    else
        log_warn "Docker daemon not running"
        echo '"docker_daemon":"not_running",' >> "$CAPABILITIES_FILE"
        echo "SKIP_DOCKER_TESTS=1" >> "$GITHUB_ENV"
    fi
else
    log_warn "Docker not available"
    echo '"docker":"missing",' >> "$CAPABILITIES_FILE"
    echo "SKIP_DOCKER_TESTS=1" >> "$GITHUB_ENV"
fi

# Close JSON
echo '"status":"complete"}}' >> "$CAPABILITIES_FILE"

echo ""
log_info "=== Setup Summary ==="

if [ $CRITICAL_MISSING -gt 0 ]; then
    log_error "Critical tools missing: $CRITICAL_MISSING"
    log_error "This should not happen in GitHub Actions!"
    log_error "Are you running in a non-standard environment?"
    
    # Only fail if we're missing critical tools AND we're in CI
    if [ "$GITHUB_ACTIONS" == "true" ]; then
        exit 1
    fi
else
    log_success "All critical tools available"
fi

log_info "Optional tools installed where possible"
log_info "Setup complete - see ci-capabilities.json for details"

# Always succeed if critical tools are present
exit 0