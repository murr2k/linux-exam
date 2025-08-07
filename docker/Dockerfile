# MPU-6050 Kernel Driver Build Environment
FROM ubuntu:22.04

LABEL maintainer="Murray Kopit <murr2k@gmail.com>"
LABEL description="Build environment for MPU-6050 kernel driver"
LABEL version="1.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

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
    linux-source \
    kmod \
    # Testing frameworks
    libcunit1-dev \
    libgtest-dev \
    googletest \
    # Code coverage tools
    lcov \
    gcov \
    gcovr \
    # Static analysis tools
    cppcheck \
    clang-format \
    clang-tidy \
    flawfinder \
    sparse \
    # Security tools
    valgrind \
    # Documentation tools
    doxygen \
    graphviz \
    # Utilities
    vim \
    nano \
    tree \
    htop \
    strace \
    ltrace \
    # Python for scripts
    python3 \
    python3-pip \
    # Additional kernel tools
    coccinelle \
    && rm -rf /var/lib/apt/lists/*

# Install Google Test from source (Ubuntu package may be outdated)
RUN cd /usr/src/googletest && \
    cmake . && \
    cmake --build . --target install

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
ENV KERNEL_DIR=/lib/modules/$(uname -r)/build
ENV KBUILD_OUTPUT=/workspace/build
ENV INSTALL_MOD_PATH=/workspace/install

# Create non-root user for development
RUN useradd -m -s /bin/bash -G sudo developer && \
    echo "developer ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Copy build scripts and configuration
COPY scripts/ /opt/scripts/
COPY .clang-format /opt/.clang-format
RUN chmod +x /opt/scripts/*.sh

# Set up environment variables
ENV PATH="/opt/scripts:${PATH}"
ENV CC=gcc
ENV CXX=g++

# Create entrypoint script
RUN cat > /entrypoint.sh << 'EOF'
#!/bin/bash
set -e

# Initialize environment
export KERNEL_DIR=/lib/modules/$(uname -r)/build
export KBUILD_OUTPUT=/workspace/build

# Ensure proper permissions
chown -R developer:developer /workspace

# Switch to developer user if not root
if [ "$(id -u)" = "0" ] && [ "$USER" != "root" ]; then
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
    CMD gcc --version && make --version || exit 1

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