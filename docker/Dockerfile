# MPU-6050 Kernel Driver Build Environment
FROM ubuntu:22.04

LABEL maintainer="Murray Kopit <murr2k@gmail.com>"
LABEL description="Build environment for MPU-6050 kernel driver"
LABEL version="1.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV KERNEL_DIR=/lib/modules/5.15.0-generic/build

# Install system dependencies and kernel development tools
RUN apt-get update && apt-get install -y \
    # Build essentials
    build-essential \
    cmake \
    make \
    gcc \
    g++ \
    git \
    wget \
    curl \
    # Kernel development  
    linux-headers-generic \
    kmod \
    # Testing frameworks
    libcunit1-dev \
    libcunit1 \
    pkg-config \
    # Code coverage tools
    lcov \
    gcov \
    # Static analysis tools
    cppcheck \
    clang-format \
    flawfinder \
    sparse \
    # Security tools
    valgrind \
    # Utilities
    vim \
    tree \
    # Python for scripts
    python3 \
    python3-pip \
    # Additional tools
    perl \
    && rm -rf /var/lib/apt/lists/*

# Install Google Test from package manager
RUN apt-get update && apt-get install -y libgtest-dev && \
    if [ -d "/usr/src/gtest" ]; then \
        cd /usr/src/gtest && \
        cmake CMakeLists.txt && \
        make && \
        cp lib/*.a /usr/lib/ || cp *.a /usr/lib/; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Install additional Python packages for testing
RUN pip3 install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-xdist \
    xmlrunner

# Create working directories
RUN mkdir -p /workspace \
    /workspace/build \
    /workspace/tests \
    /workspace/coverage \
    /workspace/lint-results

# Set up kernel module development environment
ENV KBUILD_OUTPUT=/workspace/build
ENV INSTALL_MOD_PATH=/workspace/install

# Create non-root user for development
RUN useradd -m -s /bin/bash -G sudo developer && \
    echo "developer ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Copy build scripts and configuration when they exist
COPY scripts/ /opt/scripts/
COPY .clang-format /opt/.clang-format 2>/dev/null || echo "clang-format config not found"
RUN find /opt/scripts -name "*.sh" -type f -exec chmod +x {} \;

# Set up environment variables
ENV PATH="/opt/scripts:${PATH}"
ENV CC=gcc
ENV CXX=g++

# Create entrypoint script
RUN cat > /entrypoint.sh << 'EOF'
#!/bin/bash
set -e

# Initialize environment
if [ -d "/lib/modules" ]; then
    KERNEL_VERSION=$(ls /lib/modules | head -1)
    export KERNEL_DIR="/lib/modules/${KERNEL_VERSION}/build"
else
    export KERNEL_DIR="/lib/modules/5.15.0-generic/build"
fi
export KBUILD_OUTPUT=/workspace/build

# Create kernel directory if it doesn't exist (for testing)
if [ ! -d "$KERNEL_DIR" ]; then
    mkdir -p "$KERNEL_DIR"
    # Create minimal kernel build environment
    cat > "$KERNEL_DIR/Makefile" << 'KERNELEOF'
# Minimal Makefile for testing
KERNELRELEASE := 5.15.0-generic
obj-m := 
modules:
	@echo "Mock kernel build for $(obj-m)"
KERNELEOF
fi

# Ensure proper permissions
if [ "$(id -u)" = "0" ]; then
    chown -R developer:developer /workspace 2>/dev/null || true
fi

# Switch to developer user if running as root
if [ "$(id -u)" = "0" ] && [ "$1" != "root" ]; then
    exec su - developer -c "$*"
else
    exec "$@"
fi
EOF

RUN chmod +x /entrypoint.sh

# Set working directory
WORKDIR /workspace

# Set default user
USER developer

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD gcc --version && make --version && echo "Build environment ready" || exit 1

# Default command
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]

# Build information
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="mpu6050-build-env" \
      org.label-schema.description="Build environment for MPU-6050 kernel driver" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/murr2k/linux-exam" \
      org.label-schema.schema-version="1.0"