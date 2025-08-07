# MPU-6050 End-to-End Test Framework

A comprehensive, production-grade test framework for the MPU-6050 Linux kernel driver that provides automated testing, performance validation, stress testing, and detailed reporting.

## Overview

This test framework provides:

- **Complete Test Coverage**: Module loading, device functionality, data operations, performance, and stress testing
- **Advanced Data Validation**: Statistical analysis, noise characterization, drift detection, and anomaly detection
- **Performance Testing**: Throughput measurement, latency analysis, resource monitoring, and concurrent access testing
- **Stress Testing**: Long-duration stability tests, memory leak detection, and error recovery testing
- **Comprehensive Reporting**: HTML reports, JUnit XML for CI, performance graphs, and coverage analysis
- **Python & Bash Integration**: Python-based test orchestration with Bash script automation

## Quick Start

1. **Setup the framework:**
   ```bash
   cd tests/e2e/framework
   make setup
   ```

2. **Run all tests:**
   ```bash
   make test
   ```

3. **Run specific test suite:**
   ```bash
   make test-basic          # Basic functionality tests
   make test-performance    # Performance tests
   make test-stress         # Stress tests
   ```

4. **Generate reports:**
   ```bash
   # Tests automatically generate reports in test-results/e2e/reports/
   firefox ../../../test-results/e2e/reports/test_report.html
   ```

## Framework Architecture

### Core Components

```
tests/e2e/framework/
├── main.py              # Main entry point and CLI
├── test_framework.py    # Core test orchestration
├── test_runner.sh       # Bash automation script
├── validators.py        # Data validation and analysis
├── performance.py       # Performance and stress testing
├── reports.py          # Report generation
├── requirements.txt    # Python dependencies
├── pytest.ini         # Pytest configuration
├── test_config.json    # Test configuration
├── Makefile           # Build automation
└── README.md          # This file
```

### Test Suites

1. **Module Tests** (`module_tests`)
   - Kernel module loading/unloading
   - Device node creation
   - Module parameter validation
   - Permission testing

2. **Basic Functionality** (`basic_functionality`) 
   - Device open/close operations
   - WHO_AM_I register validation
   - Basic register access
   - Configuration commands

3. **Data Operations** (`data_operations`)
   - Raw data reading
   - Scaled data reading  
   - Continuous data streaming
   - Data consistency validation

4. **Performance Tests** (`performance_tests`)
   - Throughput measurement
   - Latency analysis
   - Concurrent access testing
   - Resource usage monitoring

5. **Stress Tests** (`stress_tests`)
   - Long-duration stability testing
   - Memory leak detection
   - Error recovery scenarios
   - Power cycle recovery

## Usage

### Command Line Interface

```bash
# Run all tests with verbose output
python3 main.py --verbose

# Run specific test suite
python3 main.py --suite basic_functionality

# Run with custom configuration
python3 main.py --config my_config.json

# Generate additional reports
python3 main.py --html-report report.html --junit-xml junit.xml

# Dry run (show what would be executed)
python3 main.py --dry-run

# List available test suites
python3 main.py --list-suites
```

### Bash Script Interface

```bash
# Complete test execution with environment setup
./test_runner.sh

# Run specific suite
./test_runner.sh basic_functionality

# Verbose execution
./test_runner.sh -v performance_tests

# Continuous testing until interrupted
./test_runner.sh -c

# Generate reports only
./test_runner.sh --report-only
```

### Make Targets

```bash
make setup              # Setup environment and dependencies
make test               # Run all tests
make test-basic         # Run basic functionality tests
make test-performance   # Run performance tests
make smoke              # Quick smoke tests
make clean              # Clean generated files
make help               # Show all available targets
```

## Configuration

### Test Configuration (`test_config.json`)

```json
{
    "device_path": "/dev/mpu6050",
    "module_path": "../drivers/mpu6050_driver.ko",
    "test_duration": 300,
    "stress_test_duration": 600,
    "concurrent_clients": 4,
    "memory_limit_mb": 64,
    "cpu_limit_percent": 25,
    "validate_ranges": true,
    "generate_reports": true,
    "verbose": false
}
```

### Sensor Limits Configuration

The framework validates sensor data against configurable physical limits:

- **Accelerometer**: ±2g, ±4g, ±8g, ±16g ranges
- **Gyroscope**: ±250°/s, ±500°/s, ±1000°/s, ±2000°/s ranges  
- **Temperature**: -40°C to +85°C operating range
- **Noise Thresholds**: Configurable noise level validation

### Test Suite Configuration

Each test suite can be individually configured:

```json
{
    "test_suites": {
        "basic_functionality": {
            "enabled": true,
            "timeout": 120,
            "retry_count": 1
        },
        "performance_tests": {
            "enabled": true,
            "throughput_threshold": 100,
            "latency_threshold_ms": 10
        }
    }
}
```

## Data Validation

### Statistical Analysis

- **Descriptive Statistics**: Mean, median, standard deviation, variance
- **Distribution Analysis**: Skewness, kurtosis, percentiles
- **Quality Metrics**: Signal-to-noise ratio, effective resolution

### Noise Analysis

- **Noise Level Measurement**: RMS noise calculation
- **Frequency Analysis**: Power spectral density analysis
- **Noise Classification**: White, pink, brown noise detection
- **Periodicity Detection**: Autocorrelation-based period detection

### Drift Detection

- **Trend Analysis**: Linear, polynomial, exponential drift models
- **Model Fitting**: R-squared goodness of fit analysis
- **Time Constants**: Exponential drift time constant estimation

### Anomaly Detection  

- **Statistical Outliers**: Z-score based outlier detection
- **Change Point Detection**: Step change identification
- **Pattern Recognition**: Spike, dropout, drift anomaly types

## Performance Testing

### Throughput Testing

- **Operations per Second**: Raw and scaled data read throughput
- **Sustainable Performance**: Long-duration throughput measurement
- **Performance Degradation**: Throughput stability over time

### Latency Analysis

- **Response Time**: Individual operation latency measurement
- **Statistical Analysis**: Average, median, P95, P99 latencies
- **Latency Distribution**: Histogram analysis and outlier detection

### Resource Monitoring

- **CPU Usage**: Process CPU utilization tracking
- **Memory Usage**: Memory consumption and leak detection
- **File Descriptors**: Open file handle monitoring
- **System Resources**: Overall system impact assessment

### Concurrent Access Testing

- **Multi-Client Testing**: Simultaneous device access validation
- **Race Condition Detection**: Concurrent operation integrity
- **Contention Analysis**: Resource contention measurement

## Stress Testing

### Stability Testing

- **Long-Duration Testing**: Extended operation validation (10+ minutes)
- **Continuous Operation**: Sustained high-frequency testing
- **Error Rate Monitoring**: Failure rate tracking and analysis

### Memory Leak Detection

- **Memory Growth Analysis**: Memory usage trend analysis
- **Leak Pattern Recognition**: Different leak signature detection
- **Resource Cleanup Validation**: Proper resource deallocation testing

### Error Recovery

- **Invalid Input Handling**: Malformed request recovery testing
- **Device Error Recovery**: Hardware error condition handling
- **Module Recovery**: Post-error state recovery validation

## Reporting

### HTML Reports

Comprehensive HTML reports include:

- **Executive Summary**: Test results overview with pass/fail statistics
- **Detailed Results**: Individual test case results with error details
- **Performance Charts**: Throughput, latency, and resource usage graphs
- **Data Analysis**: Statistical analysis and trend visualization
- **Recommendations**: Automated analysis and improvement suggestions

### JUnit XML Reports

Standard JUnit XML format for CI/CD integration:

- **Test Case Results**: Pass/fail status with timing information
- **Error Details**: Failure messages and stack traces  
- **Test Properties**: Test metadata and configuration information
- **Suite Organization**: Hierarchical test organization

### JSON Metrics Export

Machine-readable metrics for automated analysis:

- **Performance Metrics**: Detailed performance measurements
- **Resource Metrics**: Resource usage statistics
- **Quality Metrics**: Data quality and validation results
- **System Information**: Test environment and configuration

### Performance Graphs

Automated graph generation includes:

- **Throughput Charts**: Operations per second over time
- **Latency Histograms**: Latency distribution analysis
- **Resource Usage**: CPU and memory usage trends
- **Data Quality**: Noise and drift analysis visualization

## Integration

### CI/CD Integration

The framework integrates with continuous integration systems:

```yaml
# GitHub Actions example
- name: Run MPU-6050 Tests
  run: |
    cd tests/e2e/framework
    make setup
    make test
    
- name: Publish Test Results
  uses: mikepenz/action-junit-report@v3
  with:
    report_paths: 'test-results/e2e/reports/junit_results.xml'
```

### Coverage Integration

Integrates with code coverage tools:

```bash
# Generate coverage report
make test  # Automatically generates coverage data

# View HTML coverage report
firefox test-results/e2e/coverage/html/index.html
```

## Requirements

### System Requirements

- **Operating System**: Linux (Ubuntu 18.04+, CentOS 7+, or similar)
- **Python**: 3.7 or higher
- **Kernel**: Linux kernel headers for module compilation
- **Hardware**: MPU-6050 sensor (optional for simulation testing)

### Python Dependencies

Core dependencies (automatically installed):

- `pytest>=7.0.0` - Testing framework
- `numpy>=1.21.0` - Numerical analysis
- `matplotlib>=3.5.0` - Graph generation
- `psutil>=5.8.0` - System monitoring
- `jinja2>=3.0.0` - HTML templating

Optional dependencies for enhanced features:

- `scipy>=1.7.0` - Advanced statistical analysis
- `pandas>=1.3.0` - Data manipulation
- `seaborn>=0.11.0` - Statistical plotting

### System Dependencies

Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev python3-pip build-essential linux-headers-$(uname -r)

# CentOS/RHEL  
sudo yum install python3-devel python3-pip gcc kernel-devel-$(uname -r)

# Or use the Makefile
make install-system-deps
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
cd tests/e2e/framework

# Setup development environment
make dev-setup

# Run code quality checks
make lint
make typecheck
make format
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-basic
make test-performance
make test-stress

# Run with coverage
make pytest

# Quick smoke test
make smoke
```

### Adding New Tests

1. **Create test function** in appropriate suite:
   ```python
   def test_new_functionality(self) -> bool:
       """Test new functionality"""
       # Test implementation
       return success
   ```

2. **Register test** in test suite:
   ```python
   self.register_test_suite(TestSuite(
       name="my_suite",
       tests=[self.test_new_functionality]
   ))
   ```

3. **Add configuration** in `test_config.json`:
   ```json
   {
       "my_suite": {
           "enabled": true,
           "timeout": 60
       }
   }
   ```

## Troubleshooting

### Common Issues

**Module Loading Fails**
```bash
# Check module path
ls -la ../drivers/mpu6050_driver.ko

# Compile module if missing
make -C ../../../ drivers

# Check kernel compatibility
modinfo ../drivers/mpu6050_driver.ko
```

**Permission Denied**
```bash
# Ensure proper permissions
sudo chmod 666 /dev/mpu6050

# Or run with sudo
sudo python3 main.py --suite basic_functionality
```

**Python Dependencies**
```bash
# Recreate virtual environment
make clean-all
make setup

# Manual dependency installation
pip3 install -r requirements.txt
```

**Device Not Found**
```bash
# Check device node
ls -la /dev/mpu*

# Load module manually
sudo insmod ../drivers/mpu6050_driver.ko

# Check kernel logs
dmesg | tail -20
```

### Debug Mode

Enable verbose debugging:

```bash
# Verbose output
python3 main.py --verbose --suite basic_functionality

# Debug logging
python3 main.py --config debug_config.json

# Dry run to check configuration
python3 main.py --dry-run
```

### Log Analysis

Framework generates detailed logs:

```bash
# View test execution log
tail -f test_framework.log

# View test runner log  
tail -f test-results/e2e/logs/test_execution_*.log

# View module build log
cat test-results/e2e/logs/module_build.log
```

## Contributing

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/new-test`
3. **Add tests** for new functionality
4. **Run** test suite: `make test`
5. **Submit** pull request with detailed description

### Code Style

- **Python**: Follow PEP 8 style guidelines
- **Documentation**: Include comprehensive docstrings
- **Testing**: Add tests for new functionality
- **Type Hints**: Use type annotations for better code clarity

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

## Support

- **Documentation**: See inline code documentation and comments
- **Issues**: Report bugs and feature requests via GitHub issues  
- **Community**: Join discussions in project forums

---

**MPU-6050 Test Framework v1.0.0**  
Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>