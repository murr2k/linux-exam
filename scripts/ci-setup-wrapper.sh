#!/bin/bash
# Robust CI Setup Wrapper - Always succeeds but reports issues

set +e  # Don't exit on error

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

# Essential packages (try to install but don't fail)
ESSENTIAL_PKGS="build-essential gcc g++ make git"
for pkg in $ESSENTIAL_PKGS; do
    install_if_possible "$pkg"
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

# Always succeed
exit 0
