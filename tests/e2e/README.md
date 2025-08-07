# MPU-6050 End-to-End Test Suite

This directory contains comprehensive end-to-end functional tests for the MPU-6050 driver. The test suite validates all aspects of the driver functionality through the character device interface (`/dev/mpu6050`).

## Test Components

### 1. C Test Suite (`test_mpu6050_e2e.c`)

A comprehensive C-based test program that validates core driver functionality:

**Features:**
- Device accessibility testing
- WHO_AM_I register validation
- Configuration IOCTL commands
- Raw and scaled data reading
- Device reset functionality
- Data consistency validation
- Error condition handling
- Performance testing (throughput measurement)

**Usage:**
```bash
# Compile and run
gcc -Wall -Wextra -std=c99 -O2 -I../../include -o test_mpu6050_e2e test_mpu6050_e2e.c
./test_mpu6050_e2e [options]

# Options
./test_mpu6050_e2e -v              # Verbose output
./test_mpu6050_e2e -c              # Continuous testing
./test_mpu6050_e2e -v -c           # Verbose continuous testing
```

**Output:**
- Colored test results (PASS/FAIL)
- Detailed test statistics
- Performance metrics (reads/second)
- Comprehensive summary report

### 2. Python Test Suite (`test_mpu6050_e2e.py`)

Advanced Python-based test suite with statistical analysis and visualization:

**Features:**
- Statistical noise analysis
- Long-duration stability testing
- Data logging and CSV export
- Real-time visualization (requires matplotlib)
- JSON test reports
- Performance benchmarking
- Advanced error analysis

**Dependencies:**
```bash
# Required
python3

# Optional (for advanced features)
pip3 install matplotlib numpy
```

**Usage:**
```bash
# Basic functionality test
./test_mpu6050_e2e.py --basic

# Comprehensive testing
./test_mpu6050_e2e.py --all --verbose

# Specific tests
./test_mpu6050_e2e.py --consistency 200
./test_mpu6050_e2e.py --stability 10
./test_mpu6050_e2e.py --performance 1000

# Data export and reporting
./test_mpu6050_e2e.py --all --export-csv data.csv --report report.json

# Real-time visualization
./test_mpu6050_e2e.py --visualize 30
```

### 3. Range Validation (`validate_ranges.c`)

Specialized test for validating sensor range configurations:

**Features:**
- Accelerometer range testing (±2g to ±16g)
- Gyroscope range testing (±250°/s to ±2000°/s)
- Temperature range validation
- Range switching consistency
- Statistical noise analysis
- Data integrity verification

**Usage:**
```bash
# Compile and run
gcc -Wall -Wextra -std=c99 -O2 -lm -I../../include -o validate_ranges validate_ranges.c
./validate_ranges [options]

# Options
./validate_ranges -v              # Verbose output
```

### 4. Test Runner (`run_e2e_tests.sh`)

Comprehensive test orchestration script:

**Features:**
- Automatic module building and loading
- I2C device creation
- Sequential test execution
- Result aggregation
- HTML report generation
- Cleanup management
- CI/CD integration support

**Usage:**
```bash
# Full test suite (requires root)
sudo ./run_e2e_tests.sh

# Specific operations
sudo ./run_e2e_tests.sh --build-only
sudo ./run_e2e_tests.sh --c-tests
sudo ./run_e2e_tests.sh --python-tests
sudo ./run_e2e_tests.sh --validation-tests

# Options
sudo ./run_e2e_tests.sh --verbose
sudo ./run_e2e_tests.sh --no-cleanup
sudo ./run_e2e_tests.sh --i2c-bus 1 --i2c-addr 0x68
```

## Test Coverage

### Functional Tests
- [x] Device node creation and accessibility
- [x] Character device file operations
- [x] IOCTL command validation
- [x] Configuration parameter validation
- [x] Raw data reading
- [x] Scaled data conversion
- [x] Device reset functionality
- [x] WHO_AM_I register verification

### Range Testing
- [x] Accelerometer ranges: ±2g, ±4g, ±8g, ±16g
- [x] Gyroscope ranges: ±250°/s, ±500°/s, ±1000°/s, ±2000°/s
- [x] Temperature measurement (-40°C to +85°C)
- [x] Range switching consistency
- [x] Data scaling accuracy

### Performance Testing
- [x] Read throughput measurement
- [x] Latency analysis
- [x] Long-duration stability
- [x] Memory usage validation
- [x] Error recovery testing

### Statistical Analysis
- [x] Sensor noise characterization
- [x] Data consistency validation
- [x] Drift analysis
- [x] Outlier detection
- [x] Signal-to-noise ratio

## Expected Results

### Performance Benchmarks
- **Read Throughput:** >50 reads/second
- **Read Latency:** <20ms per operation
- **Success Rate:** >95% for stable operation
- **Temperature Drift:** <1°C over 5 minutes
- **Noise Levels:** 
  - Accelerometer: <100mg RMS
  - Gyroscope: <50mdps RMS

### Range Accuracy
- **Accelerometer:** Within ±5% of full scale
- **Gyroscope:** Within ±3% of full scale  
- **Temperature:** Within ±2°C of ambient
- **Range Switching:** <0.1g difference for accelerometer, <2°/s for gyroscope

## Results and Reports

Test results are saved in `../../test-results/e2e/`:

```
test-results/e2e/
├── build.log              # Driver compilation log
├── c_tests.log            # C test suite output
├── python_tests.log       # Python test suite output
├── validation_tests.log   # Range validation output
├── sensor_data.csv        # Exported sensor data
├── python_test_report.json # Detailed JSON report
├── comprehensive_report.html # HTML summary report
└── main.log               # Overall test execution log
```

### HTML Report Features
- Test summary with pass/fail status
- System information
- Build logs
- Clickable links to detailed logs
- Performance metrics
- Recommendations

## Troubleshooting

### Common Issues

**Device not found (`/dev/mpu6050`):**
```bash
# Check if module is loaded
lsmod | grep mpu6050

# Check I2C device
ls /sys/bus/i2c/devices/

# Check dmesg for errors
dmesg | grep -i mpu6050
```

**Permission denied:**
```bash
# Run as root or add user to appropriate group
sudo ./test_program
# or
sudo usermod -a -G i2c $USER
```

**I2C communication errors:**
```bash
# Check I2C bus
i2cdetect -y 1

# Verify I2C address
i2cget -y 1 0x68 0x75  # Should return 0x68
```

**Python dependencies:**
```bash
# Install required packages
sudo apt-get install python3-pip
pip3 install matplotlib numpy
```

### Debug Mode

Enable debug output for troubleshooting:

```bash
# C tests
./test_mpu6050_e2e -v

# Python tests  
./test_mpu6050_e2e.py --verbose

# Range validation
./validate_ranges -v

# Test runner
sudo ./run_e2e_tests.sh --verbose
```

## Integration with CI/CD

The test runner supports automated testing:

```yaml
# Example GitHub Actions workflow
- name: Run MPU-6050 E2E Tests
  run: |
    cd tests/e2e
    sudo ./run_e2e_tests.sh --verbose
    
- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: e2e-test-results
    path: test-results/e2e/
```

## Contributing

When adding new tests:

1. Follow existing code style and patterns
2. Include comprehensive error handling
3. Add verbose logging for debugging
4. Update this README with new test descriptions
5. Ensure tests are deterministic and repeatable
6. Add appropriate cleanup procedures

## License

These tests are part of the MPU-6050 driver project and are licensed under the GNU General Public License v2.