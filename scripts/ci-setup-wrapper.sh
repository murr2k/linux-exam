#!/bin/bash
# Robust CI Setup Wrapper - Handles missing dependencies gracefully
# Returns failure only if critical dependencies are missing

set +e  # Don't exit on error
CRITICAL_FAILURE=0

# Track what's available
CAPABILITIES_FILE="ci-capabilities.json"
echo '{"timestamp":"'$(date -Iseconds)'","capabilities":{' > "$CAPABILITIES_FILE"

# Function to check and install package
install_if_possible() {
    local pkg="$1"
    if dpkg -l | grep -q "^ii  $pkg "; then
        echo "\"$pkg\":\"installed\"," >> "$CAPABILITIES_FILE"
        return 0
    fi
    
    if sudo apt-get install -y "$pkg" 2>/dev/null; then
        echo "\"$pkg\":\"newly_installed\"," >> "$CAPABILITIES_FILE"
        return 0
    else
        echo "\"$pkg\":\"unavailable\"," >> "$CAPABILITIES_FILE"
        return 1
    fi
}

# Update package lists (best effort)
sudo apt-get update 2>/dev/null || echo "\"apt_update\":\"failed\"," >> "$CAPABILITIES_FILE"

# Essential packages (must have for build)
ESSENTIAL_PKGS="build-essential gcc g++ make git"
for pkg in $ESSENTIAL_PKGS; do
    if ! install_if_possible "$pkg"; then
        echo "ERROR: Failed to install critical dependency: $pkg"
        CRITICAL_FAILURE=1
    fi
done

# Optional packages
OPTIONAL_PKGS="linux-headers-generic cmake lcov gcovr cppcheck clang valgrind"
for pkg in $OPTIONAL_PKGS; do
    install_if_possible "$pkg" || true
done

# Python packages (best effort)
if command -v pip3 >/dev/null 2>&1; then
    pip3 install --user pytest coverage 2>/dev/null || true
    echo "\"python_tools\":\"available\"," >> "$CAPABILITIES_FILE"
else
    echo "\"python_tools\":\"unavailable\"," >> "$CAPABILITIES_FILE"
fi

# Kernel headers (special handling)
KERNEL_VERSION=$(uname -r)
if [ -d "/lib/modules/$KERNEL_VERSION/build" ]; then
    echo "\"kernel_headers\":\"available\"," >> "$CAPABILITIES_FILE"
else
    echo "\"kernel_headers\":\"unavailable\"," >> "$CAPABILITIES_FILE"
    echo "SKIP_KERNEL_BUILD=1" >> "$GITHUB_ENV"
fi

# Close JSON
echo "\"status\":\"complete\"}}' >> "$CAPABILITIES_FILE"

# Exit with appropriate status
if [ $CRITICAL_FAILURE -eq 1 ]; then
    echo "ERROR: Critical dependencies missing - cannot continue"
    exit 1
fi

echo "Setup completed successfully (some optional packages may be missing)"
exit 0
