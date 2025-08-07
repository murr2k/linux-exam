# MPU-6050 Linux Kernel Driver

[![Build Status](https://img.shields.io/github/actions/workflow/status/murr2k/linux-exam/ci.yml?branch=main)](https://github.com/murr2k/linux-exam/actions)
[![License](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)
[![Kernel](https://img.shields.io/badge/Kernel-5.4%2B-orange.svg)](https://kernel.org/)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](docs/TESTING.md)

A comprehensive Linux kernel driver for the MPU-6050 6-axis gyroscope and accelerometer sensor with I2C interface support, sysfs attributes, and robust error handling.

## 🚀 Features

- **Complete I2C Interface**: Full support for MPU-6050 I2C communication
- **Sysfs Integration**: Easy userspace access through standard sysfs attributes
- **Character Device**: Direct device access via `/dev/mpu6050`
- **IOCTL Commands**: Comprehensive control interface for advanced operations
- **Interrupt Support**: Hardware interrupt handling for data-ready signals
- **Configurable Ranges**: Adjustable gyroscope and accelerometer sensitivity
- **Power Management**: Sleep/wake functionality with proper power state handling
- **Self-Test**: Built-in hardware self-test capabilities
- **Robust Error Handling**: Comprehensive error detection and recovery
- **Device Tree Support**: Full device tree integration for modern kernels

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## 🚀 Quick Start

### Prerequisites

- Linux kernel 5.4 or later with headers installed
- Build tools: `make`, `gcc`
- I2C subsystem enabled in kernel
- MPU-6050 sensor connected via I2C

### Build and Install

```bash
# Clone the repository
git clone https://github.com/murr2k/linux-exam.git
cd linux-exam

# Build the kernel module
make

# Install the module
sudo make install

# Load the module
sudo modprobe mpu6050
```

### Quick Test

```bash
# Check if module loaded successfully
lsmod | grep mpu6050

# Read accelerometer data
cat /sys/class/mpu6050/mpu6050/accel_data

# Read gyroscope data  
cat /sys/class/mpu6050/mpu6050/gyro_data

# Check device status
cat /sys/class/mpu6050/mpu6050/status
```

## 📦 Installation

### System Requirements

| Component | Requirement |
|-----------|-------------|
| Kernel Version | 5.4+ |
| Architecture | x86_64, ARM, ARM64 |
| I2C Support | Required |
| Memory | Minimal (< 1MB) |

### Automated Installation

```bash
# Install dependencies and build
make setup

# Run full CI pipeline
make ci

# Install system-wide
sudo make install
```

### Manual Installation

```bash
# Install build dependencies
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    linux-headers-$(uname -r) \
    libcunit1-dev \
    lcov \
    clang-format \
    cppcheck

# Build the module
make modules

# Install module
sudo make modules_install
sudo depmod -A

# Load at boot (optional)
echo "mpu6050" | sudo tee -a /etc/modules
```

### Docker Installation

```bash
# Build development environment
./scripts/docker-build.sh --build

# Run tests in container
./scripts/docker-build.sh --test

# Interactive development
./scripts/docker-build.sh --run
```

## 🎯 Usage

### Device Tree Configuration

Add to your device tree:

```dts
&i2c1 {
    mpu6050@68 {
        compatible = "invensense,mpu6050";
        reg = <0x68>;
        interrupt-parent = <&gpio>;
        interrupts = <17 IRQ_TYPE_EDGE_RISING>;
        status = "okay";
    };
};
```

### Sysfs Interface

```bash
# Basic sensor readings
cat /sys/class/mpu6050/mpu6050/accel_data     # Raw accelerometer (x,y,z)
cat /sys/class/mpu6050/mpu6050/gyro_data      # Raw gyroscope (x,y,z)
cat /sys/class/mpu6050/mpu6050/temp_data      # Temperature

# Scaled readings (human-readable units)
cat /sys/class/mpu6050/mpu6050/accel_scale    # Accelerometer in mg
cat /sys/class/mpu6050/mpu6050/gyro_scale     # Gyroscope in mdps
cat /sys/class/mpu6050/mpu6050/temp_celsius   # Temperature in °C

# Configuration
echo "2" > /sys/class/mpu6050/mpu6050/accel_range  # ±4g
echo "1" > /sys/class/mpu6050/mpu6050/gyro_range   # ±500°/s
echo "7" > /sys/class/mpu6050/mpu6050/sample_rate  # 125 Hz

# Power management
echo "1" > /sys/class/mpu6050/mpu6050/power_state  # Wake up
echo "0" > /sys/class/mpu6050/mpu6050/power_state  # Sleep

# Self-test
cat /sys/class/mpu6050/mpu6050/self_test      # Run self-test
```

### Character Device Interface

```c
#include <sys/ioctl.h>
#include <fcntl.h>
#include "mpu6050.h"

int fd = open("/dev/mpu6050", O_RDWR);

// Read raw sensor data
struct mpu6050_raw_data raw_data;
ioctl(fd, MPU6050_IOC_READ_RAW, &raw_data);

// Read scaled data
struct mpu6050_scaled_data scaled_data;
ioctl(fd, MPU6050_IOC_READ_SCALED, &scaled_data);

// Configure sensor
struct mpu6050_config config = {
    .sample_rate_div = 7,    // 125 Hz
    .gyro_range = 1,         // ±500°/s
    .accel_range = 1,        // ±4g
    .dlpf_cfg = 3            // 44 Hz LPF
};
ioctl(fd, MPU6050_IOC_SET_CONFIG, &config);

close(fd);
```

### Python Example

```python
#!/usr/bin/env python3
import time

def read_mpu6050():
    """Read MPU-6050 sensor data via sysfs"""
    try:
        # Read accelerometer data
        with open('/sys/class/mpu6050/mpu6050/accel_scale', 'r') as f:
            accel_x, accel_y, accel_z = map(int, f.read().split())
            
        # Read gyroscope data  
        with open('/sys/class/mpu6050/mpu6050/gyro_scale', 'r') as f:
            gyro_x, gyro_y, gyro_z = map(int, f.read().split())
            
        # Read temperature
        with open('/sys/class/mpu6050/mpu6050/temp_celsius', 'r') as f:
            temp = int(f.read())
            
        return {
            'accel': {'x': accel_x, 'y': accel_y, 'z': accel_z},  # mg
            'gyro': {'x': gyro_x, 'y': gyro_y, 'z': gyro_z},      # mdps
            'temp': temp / 100.0  # °C
        }
    except Exception as e:
        print(f"Error reading sensor: {e}")
        return None

# Continuous reading
while True:
    data = read_mpu6050()
    if data:
        print(f"Accel: {data['accel']}, Gyro: {data['gyro']}, Temp: {data['temp']:.1f}°C")
    time.sleep(0.1)
```

## 🧪 Testing

### Unit Tests

```bash
# Run all unit tests
make test

# Run with coverage
make test COVERAGE=1

# View coverage report
open coverage/index.html
```

### Integration Tests

```bash
# Hardware-in-the-loop testing
make load           # Load module
make integration    # Run integration tests
make unload         # Unload module
```

### Manual Testing

```bash
# Load module and test basic functionality
sudo insmod build/mpu6050.ko
dmesg | tail -10

# Test sysfs interface
ls -la /sys/class/mpu6050/
cat /sys/class/mpu6050/mpu6050/accel_data

# Test character device
ls -la /dev/mpu6050*
cat /dev/mpu6050

# Stress test
./tests/stress_test.sh
```

For detailed testing procedures, see [docs/TESTING.md](docs/TESTING.md).

## 🔄 CI/CD Pipeline

Our automated pipeline ensures code quality and functionality:

```mermaid
graph LR
    A[Code Push] --> B[Lint Check]
    B --> C[Unit Tests]
    C --> D[Integration Tests]
    D --> E[Build Module]
    E --> F[Security Scan]
    F --> G[Deploy]
```

### Pipeline Stages

1. **Code Quality**: clang-format, cppcheck, checkpatch.pl
2. **Unit Testing**: CUnit framework with mocking
3. **Integration Testing**: Hardware simulation and real device tests
4. **Security Analysis**: Static analysis and vulnerability scanning
5. **Build Verification**: Multi-kernel version compatibility
6. **Documentation**: Automated doc generation and validation

### Running the Pipeline

```bash
# Local CI run
make ci

# Docker-based CI
./scripts/docker-build.sh --test

# Individual stages
make lint           # Code quality only
make test           # Tests only
make security       # Security scan only
```

## 🏗️ Architecture

### Driver Components

```
mpu6050/
├── drivers/
│   ├── mpu6050_main.c      # Core driver logic
│   ├── mpu6050_i2c.c       # I2C communication
│   ├── mpu6050_sysfs.c     # Sysfs interface
│   └── mpu6050_chardev.c   # Character device
├── include/
│   └── mpu6050.h           # Header definitions
├── tests/
│   ├── unit/               # Unit test suite
│   ├── integration/        # Integration tests
│   └── mocks/              # Hardware mocks
└── scripts/
    ├── build.sh            # Build automation
    ├── lint.sh             # Code quality
    └── docker-build.sh     # Container support
```

### Data Flow

```
Hardware → I2C → Driver → Character Device → Userspace Application
                     ↓
                Sysfs Attributes → Shell Scripts/Python
```

### Key Design Principles

- **Modularity**: Separate concerns (I2C, sysfs, chardev)
- **Robustness**: Comprehensive error handling and recovery
- **Performance**: Efficient register access and data caching
- **Standards Compliance**: Follows Linux kernel coding standards
- **Testability**: Mock-friendly architecture for unit testing

For detailed architecture information, see [docs/KERNEL_DRIVER.md](docs/KERNEL_DRIVER.md).

## 🤝 Contributing

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Development Environment

```bash
# Set up development environment
make setup

# Run development checks
make format          # Auto-format code
make lint           # Check code quality
make test           # Run test suite

# Docker development
./scripts/docker-build.sh --run
```

### Code Standards

- **Kernel Coding Style**: Strict adherence to Linux kernel standards
- **Documentation**: All functions must have kernel-doc comments
- **Testing**: New features require unit tests
- **Commit Messages**: Use conventional commit format
- **Error Handling**: All error paths must be tested

### Submitting Issues

When reporting bugs, please include:
- Kernel version and architecture
- Hardware configuration
- Steps to reproduce
- Expected vs actual behavior
- Relevant log messages (dmesg output)

## 📄 License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

### License Summary

- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ❌ Liability
- ❌ Warranty
- 📝 License and copyright notice required
- 📝 State changes

## 🆘 Support

### Documentation

- [Kernel Driver Details](docs/KERNEL_DRIVER.md)
- [Testing Guide](docs/TESTING.md)
- [API Reference](docs/API_REFERENCE.md)

### Community

- **Issues**: [GitHub Issues](https://github.com/murr2k/linux-exam/issues)
- **Discussions**: [GitHub Discussions](https://github.com/murr2k/linux-exam/discussions)
- **Email**: murr2k@gmail.com

### Professional Support

For commercial support, custom development, or consulting services, please contact:
- **Email**: murr2k@gmail.com
- **GitHub**: [@murr2k](https://github.com/murr2k)

---

## 📊 Project Status

| Component | Status | Coverage | Notes |
|-----------|--------|----------|---------|
| Core Driver | ✅ Stable | 95% | Production ready |
| I2C Interface | ✅ Stable | 90% | Fully tested |
| Sysfs Attributes | ✅ Stable | 85% | Complete API |
| Character Device | ✅ Stable | 88% | IOCTL interface |
| Power Management | ✅ Stable | 80% | Sleep/wake support |
| Device Tree | ✅ Stable | 75% | DT binding complete |
| Documentation | 🔄 WIP | 70% | Continuous improvement |

**Last Updated**: January 2025  
**Maintainer**: Murray Kopit <murr2k@gmail.com>  
**Repository**: https://github.com/murr2k/linux-exam

---

*Built with ❤️ for the Linux kernel community*