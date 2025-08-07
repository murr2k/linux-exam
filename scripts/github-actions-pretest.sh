#!/bin/bash

# GitHub Actions Environment Discovery Script
# This script checks what tools and packages are available in GitHub Actions Ubuntu runners
# without any installation attempts

echo "================================================"
echo "GitHub Actions Environment Discovery"
echo "================================================"
echo ""
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "User: $(whoami)"
echo "PWD: $(pwd)"
echo ""

# Check if running in GitHub Actions
if [ "$GITHUB_ACTIONS" == "true" ]; then
    echo "✅ Running in GitHub Actions"
    echo "Runner OS: $RUNNER_OS"
    echo "Runner Name: $RUNNER_NAME"
    echo "Runner Tool Cache: $RUNNER_TOOL_CACHE"
    echo "GitHub Workspace: $GITHUB_WORKSPACE"
else
    echo "⚠️  NOT running in GitHub Actions (local environment)"
fi

echo ""
echo "================================================"
echo "System Information"
echo "================================================"
echo "OS Release:"
cat /etc/os-release | grep -E "^(NAME|VERSION|ID)" || echo "Could not read OS release"
echo ""
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "CPU Info: $(nproc) cores"
echo "Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Disk Space: $(df -h / | awk 'NR==2 {print $4 " available"}')"

echo ""
echo "================================================"
echo "Build Tools Required by Our Tests"
echo "================================================"

# Function to check if a command exists
check_tool() {
    local tool=$1
    local category=$2
    local required=$3
    
    if command -v "$tool" >/dev/null 2>&1; then
        local version=$(get_version "$tool")
        echo "✅ [$category] $tool: AVAILABLE - $version"
        return 0
    else
        if [ "$required" == "REQUIRED" ]; then
            echo "❌ [$category] $tool: NOT FOUND (REQUIRED)"
        else
            echo "⚠️  [$category] $tool: NOT FOUND (optional)"
        fi
        return 1
    fi
}

# Function to get version
get_version() {
    local tool=$1
    case $tool in
        gcc|g++)
            $tool --version 2>/dev/null | head -n1 || echo "version unknown"
            ;;
        clang|clang++)
            $tool --version 2>/dev/null | head -n1 || echo "version unknown"
            ;;
        make)
            $tool --version 2>/dev/null | head -n1 || echo "version unknown"
            ;;
        cmake)
            $tool --version 2>/dev/null | head -n1 || echo "version unknown"
            ;;
        python3)
            $tool --version 2>/dev/null || echo "version unknown"
            ;;
        pip3)
            $tool --version 2>/dev/null || echo "version unknown"
            ;;
        docker)
            $tool --version 2>/dev/null || echo "version unknown"
            ;;
        git)
            $tool --version 2>/dev/null || echo "version unknown"
            ;;
        *)
            echo "version check not implemented"
            ;;
    esac
}

# Check for package availability without installing
check_package() {
    local pkg=$1
    local category=$2
    
    if dpkg -l | grep -q "^ii  $pkg "; then
        local version=$(dpkg -l | grep "^ii  $pkg " | awk '{print $3}')
        echo "✅ [$category] Package $pkg: INSTALLED - version $version"
        return 0
    else
        echo "⚠️  [$category] Package $pkg: NOT INSTALLED"
        return 1
    fi
}

echo ""
echo "=== Core Build Tools (CRITICAL) ==="
check_tool "gcc" "BUILD" "REQUIRED"
check_tool "g++" "BUILD" "REQUIRED"
check_tool "make" "BUILD" "REQUIRED"
check_tool "git" "BUILD" "REQUIRED"
check_tool "bash" "BUILD" "REQUIRED"
check_tool "sh" "BUILD" "REQUIRED"

echo ""
echo "=== Additional Compilers ==="
check_tool "clang" "BUILD" "optional"
check_tool "clang++" "BUILD" "optional"

echo ""
echo "=== Build Systems ==="
check_tool "cmake" "BUILD" "optional"
check_tool "automake" "BUILD" "optional"
check_tool "autoconf" "BUILD" "optional"
check_tool "pkg-config" "BUILD" "optional"

echo ""
echo "=== Python Tools (Required for E2E tests) ==="
check_tool "python3" "PYTHON" "REQUIRED"
check_tool "pip3" "PYTHON" "REQUIRED"
check_tool "pytest" "PYTHON" "optional"
check_tool "coverage" "PYTHON" "optional"

echo ""
echo "=== Testing Tools ==="
check_tool "cppcheck" "TEST" "optional"
check_tool "valgrind" "TEST" "optional"
check_tool "lcov" "TEST" "optional"
check_tool "gcov" "TEST" "optional"
check_tool "gcovr" "TEST" "optional"

echo ""
echo "=== Linting/Formatting Tools ==="
check_tool "clang-format" "LINT" "optional"
check_tool "clang-tidy" "LINT" "optional"
check_tool "flawfinder" "LINT" "optional"
check_tool "sparse" "LINT" "optional"
check_tool "coccinelle" "LINT" "optional"

echo ""
echo "=== Security Scanning Tools ==="
check_tool "bandit" "SECURITY" "optional"
check_tool "safety" "SECURITY" "optional"
check_tool "trivy" "SECURITY" "optional"

echo ""
echo "=== Container Tools ==="
check_tool "docker" "CONTAINER" "optional"
check_tool "docker-compose" "CONTAINER" "optional"
check_tool "podman" "CONTAINER" "optional"

echo ""
echo "=== Other Utilities ==="
check_tool "wget" "UTIL" "optional"
check_tool "curl" "UTIL" "optional"
check_tool "jq" "UTIL" "optional"
check_tool "tar" "UTIL" "optional"
check_tool "gzip" "UTIL" "optional"
check_tool "zip" "UTIL" "optional"
check_tool "unzip" "UTIL" "optional"
check_tool "sed" "UTIL" "optional"
check_tool "awk" "UTIL" "optional"
check_tool "grep" "UTIL" "optional"
check_tool "find" "UTIL" "optional"
check_tool "sudo" "UTIL" "optional"

echo ""
echo "================================================"
echo "Package Status (via dpkg)"
echo "================================================"

echo ""
echo "=== Development Packages ==="
check_package "build-essential" "DEV"
check_package "linux-headers-generic" "DEV"
check_package "linux-libc-dev" "DEV"
check_package "libc6-dev" "DEV"

echo ""
echo "=== Testing Libraries ==="
check_package "libgtest-dev" "TEST"
check_package "libcunit1-dev" "TEST"
check_package "libcunit1" "TEST"

echo ""
echo "=== Python Packages ==="
check_package "python3-pip" "PYTHON"
check_package "python3-dev" "PYTHON"
check_package "python3-venv" "PYTHON"
check_package "python3-pytest" "PYTHON"

echo ""
echo "================================================"
echo "Kernel Headers Check"
echo "================================================"
KERNEL_VERSION=$(uname -r)
echo "Current kernel: $KERNEL_VERSION"

if [ -d "/lib/modules/$KERNEL_VERSION/build" ]; then
    echo "✅ Kernel headers directory exists: /lib/modules/$KERNEL_VERSION/build"
else
    echo "❌ Kernel headers directory NOT FOUND: /lib/modules/$KERNEL_VERSION/build"
fi

if [ -f "/lib/modules/$KERNEL_VERSION/build/Makefile" ]; then
    echo "✅ Kernel Makefile exists"
else
    echo "❌ Kernel Makefile NOT FOUND"
fi

# Check for generic headers
if [ -d "/usr/src/linux-headers-$KERNEL_VERSION" ]; then
    echo "✅ Headers in /usr/src/linux-headers-$KERNEL_VERSION"
else
    echo "⚠️  No headers in /usr/src/linux-headers-$KERNEL_VERSION"
fi

echo ""
echo "================================================"
echo "Python Environment"
echo "================================================"

if command -v python3 >/dev/null 2>&1; then
    echo "Python3 version: $(python3 --version)"
    echo "Python3 path: $(which python3)"
    
    # Check pip packages
    if command -v pip3 >/dev/null 2>&1; then
        echo ""
        echo "=== Installed Python Packages (relevant) ==="
        pip3 list 2>/dev/null | grep -E "(pytest|coverage|mock|unittest|nose|tox|flake8|pylint|black|mypy)" || echo "No testing packages found"
    fi
fi

echo ""
echo "================================================"
echo "Environment Variables"
echo "================================================"
echo "PATH=$PATH"
echo ""
echo "CC=${CC:-not set}"
echo "CXX=${CXX:-not set}"
echo "CFLAGS=${CFLAGS:-not set}"
echo "LDFLAGS=${LDFLAGS:-not set}"

echo ""
echo "================================================"
echo "Sudo Permissions Check"
echo "================================================"
if [ "$GITHUB_ACTIONS" == "true" ]; then
    echo "Checking sudo capabilities..."
    
    # Test if sudo works without password
    if sudo -n true 2>/dev/null; then
        echo "✅ Sudo available without password"
        
        # Test if we can update package lists
        if sudo apt-get update -qq 2>/dev/null; then
            echo "✅ Can run apt-get update"
        else
            echo "❌ Cannot run apt-get update"
        fi
    else
        echo "❌ Sudo requires password or not available"
    fi
else
    echo "⚠️  Not in GitHub Actions, skipping sudo check"
fi

echo ""
echo "================================================"
echo "Summary"
echo "================================================"

# Count available tools
REQUIRED_FOUND=0
REQUIRED_MISSING=0
OPTIONAL_FOUND=0
OPTIONAL_MISSING=0

# Re-check critical tools for summary
for tool in gcc g++ make git python3; do
    if command -v "$tool" >/dev/null 2>&1; then
        ((REQUIRED_FOUND++))
    else
        ((REQUIRED_MISSING++))
        echo "❌ CRITICAL: $tool is missing"
    fi
done

echo ""
echo "Required tools found: $REQUIRED_FOUND"
echo "Required tools missing: $REQUIRED_MISSING"
echo ""

if [ $REQUIRED_MISSING -eq 0 ]; then
    echo "✅ All critical tools are available!"
    echo "The environment can run basic builds and tests."
else
    echo "❌ Some critical tools are missing!"
    echo "The environment cannot run all tests without installation."
fi

echo ""
echo "================================================"
echo "Recommendations"
echo "================================================"

if [ "$GITHUB_ACTIONS" == "true" ]; then
    echo "For GitHub Actions Ubuntu runners:"
    echo "1. Use pre-installed tools when possible (gcc, g++, make, git, python3)"
    echo "2. Only install truly missing dependencies"
    echo "3. Skip kernel module tests (no kernel headers in containers)"
    echo "4. Use apt-get for additional packages only when needed"
    echo "5. Consider using setup-python action for Python packages"
else
    echo "For local development:"
    echo "1. Install development packages as needed"
    echo "2. Ensure kernel headers match your kernel version"
    echo "3. Use virtual environments for Python packages"
fi

echo ""
echo "================================================"
echo "End of Environment Discovery"
echo "================================================"