# MPU-6050 End-to-End Testing Suite

## 🎯 Overview

Comprehensive end-to-end testing suite for the MPU-6050 Linux kernel driver, featuring hardware simulation, automated testing, and CI/CD integration.

## 🏗️ Architecture

```
tests/e2e/
├── simulator/          # Virtual I2C bus and MPU-6050 simulator
├── framework/          # Python-based test framework
├── docker/            # Docker containerization
├── scenarios/         # Test scenarios and data
└── reports/           # Generated test reports
```

## 🚀 Quick Start

### Local Testing

```bash
# Build and run all tests
cd tests/e2e
make all

# Run simulator tests only
./simulator/simulator_test -q

# Run Python framework tests
python3 framework/main.py --suite all

# Run Docker-based tests
./docker/run_e2e_docker.sh
```

### CI/CD Integration

The E2E tests are automatically run in GitHub Actions:
- On every push to main/develop branches
- On pull requests
- Nightly scheduled runs
- Manual workflow dispatch

## 🧪 Test Components

### 1. I2C Bus Simulator
- **Purpose**: Simulates I2C hardware without physical devices
- **Features**:
  - Virtual I2C bus with multiple devices
  - MPU-6050 register emulation
  - Realistic sensor data generation
  - Error injection capabilities
  - Performance benchmarking

### 2. Test Framework
- **Purpose**: Comprehensive test orchestration and validation
- **Components**:
  - Module loading/unloading tests
  - Device node operation tests
  - IOCTL functionality tests
  - Data validation and analysis
  - Performance benchmarking
  - Stress testing

### 3. Docker Environment
- **Purpose**: Isolated, reproducible test environment
- **Features**:
  - Multi-stage builds for efficiency
  - Non-root execution for security
  - CI/CD compatible
  - Result persistence with PostgreSQL
  - Monitoring with Grafana (optional)

## 📊 Test Scenarios

### Basic Functionality
- Device detection and initialization
- Register read/write operations
- Power management states
- Configuration changes

### Data Operations
- Continuous data reading
- Data rate verification
- Range switching
- FIFO buffer operations

### Performance Tests
- Throughput measurement (>1000 reads/sec)
- Latency analysis (<10ms P99)
- Concurrent access testing
- Resource usage monitoring

### Stress Testing
- Long-duration stability (24+ hours)
- Memory leak detection
- Error recovery
- High-load scenarios

## 📈 Metrics and Reporting

### Available Reports
- **HTML Dashboard**: Executive summary with charts
- **JUnit XML**: CI/CD integration
- **JSON Metrics**: Machine-readable performance data
- **Coverage Reports**: Code coverage analysis

### Key Metrics
- Test pass rate
- Performance benchmarks
- Resource utilization
- Error rates
- Coverage percentage

## 🔧 Configuration

### Test Configuration
Edit `framework/test_config.json`:
```json
{
  "sensor_limits": {
    "accel_range": 16.0,
    "gyro_range": 2000.0,
    "temp_range": [-40, 85]
  },
  "test_suites": {
    "smoke": ["module", "basic"],
    "full": ["module", "basic", "data", "performance", "stress"]
  }
}
```

### Docker Configuration
Environment variables in `docker/.env`:
```bash
TEST_VERBOSE=false
TEST_SUITE=smoke
ENABLE_MONITORING=false
```

## 🐛 Troubleshooting

### Common Issues

1. **Module Load Failure**
   ```bash
   # Check kernel headers
   ls /lib/modules/$(uname -r)/build
   
   # Install if missing
   sudo apt-get install linux-headers-$(uname -r)
   ```

2. **Permission Denied**
   ```bash
   # Add user to required groups
   sudo usermod -a -G i2c,gpio $USER
   
   # Or run with sudo (not recommended)
   sudo ./test_runner.sh
   ```

3. **Docker Build Failure**
   ```bash
   # Clean Docker cache
   docker system prune -a
   
   # Rebuild with no cache
   docker build --no-cache -f docker/Dockerfile.e2e -t mpu6050-e2e .
   ```

## 📚 Documentation

- [Simulator Documentation](simulator/README.md)
- [Framework Documentation](framework/README.md)
- [Docker Documentation](docker/README.md)
- [CI/CD Integration](.github/workflows/README.md)

## 🤝 Contributing

1. Add new test scenarios in `framework/test_scenarios.py`
2. Extend validators in `framework/validators.py`
3. Add performance benchmarks in `framework/performance.py`
4. Update documentation

## 📝 License

Same as parent project - see [LICENSE](../../LICENSE)

## 🔗 Resources

- [MPU-6050 Datasheet](https://invensense.tdk.com/products/motion-tracking/6-axis/mpu-6050/)
- [Linux I2C Documentation](https://www.kernel.org/doc/html/latest/i2c/index.html)
- [Kernel Testing Guide](https://www.kernel.org/doc/html/latest/dev-tools/testing-overview.html)