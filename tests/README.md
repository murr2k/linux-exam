# MPU-6050 Kernel Driver Unit Tests

Comprehensive unit testing framework for the MPU-6050 Linux kernel driver. This test suite provides extensive coverage for all driver functionality without requiring actual hardware, using sophisticated mocks and simulations.

## Overview

This testing framework includes:

- **Comprehensive Unit Tests**: Full coverage of driver functionality
- **Mock I2C Interface**: Hardware-independent testing environment
- **Realistic Sensor Data**: Extensive test fixtures and motion patterns
- **Performance Testing**: Load and stress testing capabilities
- **Error Injection**: Systematic error condition testing
- **CI/CD Integration**: Automated testing with GitHub Actions
- **Multiple Build Systems**: CMake and Make support

## Directory Structure

```
tests/
├── unit/                    # Unit test implementations
│   ├── test_main.cpp       # Google Test main runner
│   └── test_mpu6050.cpp    # MPU-6050 driver tests
├── mocks/                  # Mock implementations
│   ├── mock_i2c.h         # I2C subsystem mock header
│   └── mock_i2c.cpp       # I2C subsystem mock implementation
├── utils/                  # Test utilities and helpers
│   ├── test_helpers.h     # Common test utilities header
│   └── test_helpers.cpp   # Test utilities implementation
├── fixtures/              # Test data and scenarios
│   ├── sensor_data.h      # Sensor data fixtures header
│   └── sensor_data.cpp    # Sensor data fixtures implementation
├── CMakeLists.txt         # CMake build configuration
├── Makefile               # Alternative Make build system
└── .github/workflows/     # CI/CD configuration
    └── test.yml          # GitHub Actions workflow
```

## Quick Start

### Prerequisites

Install required dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install -y \
    build-essential \
    cmake \
    libgtest-dev \
    libgmock-dev \
    pkg-config

# Build Google Test if not pre-built
cd /usr/src/gtest
sudo cmake CMakeLists.txt
sudo make
sudo cp lib/*.a /usr/lib
```

### Building and Running Tests

#### Using CMake (Recommended)

```bash
cd tests
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

#### Using Make

```bash
cd tests
make all
make test
```

#### Quick Test Commands

```bash
# Run all tests
./build/mpu6050_unit_tests

# Run with verbose output
./build/mpu6050_unit_tests --verbose

# Run specific test categories
make test-probe              # Device probe tests
make test-data-reading       # Sensor data reading tests
make test-error-handling     # Error handling tests

# Run performance tests
make test-performance
```

## Test Categories

### 1. Device Probe and Initialization

Tests covering device detection, identification, and initialization:

- Device presence detection
- WHO_AM_I register verification
- Initialization sequence validation
- Reset and power management
- Error handling during probe

### 2. Sensor Data Reading

Comprehensive testing of sensor data acquisition:

- Accelerometer data reading (X, Y, Z axes)
- Gyroscope data reading (X, Y, Z axes)
- Temperature sensor reading
- Block data transfer operations
- Data validation and range checking

### 3. Configuration Management

Testing of device configuration capabilities:

- Accelerometer range configuration (±2g, ±4g, ±8g, ±16g)
- Gyroscope range configuration (±250, ±500, ±1000, ±2000 °/s)
- Power mode management
- Register configuration validation

### 4. Calibration and Self-Test

Advanced testing of calibration and self-test features:

- Calibration procedure validation
- Self-test execution and verification
- Calibration convergence testing
- Self-test response validation

### 5. Error Handling and Recovery

Systematic testing of error conditions:

- I2C communication failures
- Device disconnection scenarios
- Invalid data handling
- Timeout and retry mechanisms
- Error recovery procedures

### 6. Performance and Stress Testing

Performance validation and stress testing:

- High-frequency data reading (1000+ samples/sec)
- Concurrent operation testing
- Memory usage validation
- Latency and throughput measurement

## Mock I2C Interface

The mock I2C interface provides sophisticated simulation capabilities:

### Features

- **Configurable Behavior**: Success/failure scenarios
- **Error Injection**: Programmable error rates and types
- **Noise Simulation**: Realistic sensor noise patterns
- **Transaction Recording**: Complete I2C transaction logging
- **Hardware Simulation**: Realistic MPU-6050 behavior

### Usage Examples

```cpp
// Set up successful operation
SETUP_I2C_SUCCESS();
MockI2CInterface::getInstance().simulateDevicePresent(true);

// Inject specific errors
SETUP_I2C_ERROR(ETIMEDOUT);

// Add realistic noise
MockI2CInterface::getInstance().simulateNoiseInReads(true, 0.1);

// Set register values
EXPECT_I2C_READ(MPU6050_Registers::WHO_AM_I, MPU6050_Registers::WHO_AM_I_VALUE);
```

## Test Data Fixtures

Extensive test data covering various scenarios:

### Motion Patterns

- **Stationary**: Device at rest
- **Slow Tilt**: Gradual orientation changes
- **Fast Rotation**: Rapid rotation around axes
- **Linear Acceleration**: Straight-line motion
- **Vibration**: High-frequency oscillation
- **Freefall**: Zero-gravity simulation
- **Tap Detection**: Impact events
- **Shake Gestures**: Multi-axis movement

### Calibration Data

- Six-orientation calibration positions
- Temperature compensation data
- Noise profiles (low, medium, high)
- Error condition simulations

### Usage Examples

```cpp
// Get predefined motion patterns
auto stationary = GET_MOTION_PATTERNS().stationary;
auto rotation = GET_MOTION_PATTERNS().fast_rotation;

// Access calibration data
auto cal_data = GET_CALIBRATION_DATA();
SensorSample flat = cal_data.flat_horizontal;

// Generate custom data
auto custom = SensorDataGenerator::generateReading("vibration");
auto sequence = SensorDataGenerator::generateSequence(100, "rotation", 0.1);
```

## Advanced Testing Features

### Code Coverage

Generate comprehensive code coverage reports:

```bash
# Using CMake
cmake -B build -DENABLE_COVERAGE=ON
make -C build coverage
# View: build/coverage/index.html

# Using Make
make coverage
```

### Memory Testing

Detect memory leaks and errors:

```bash
# Valgrind memory checking
make memcheck

# Address sanitizer (CMake)
cmake -B build -DCMAKE_CXX_FLAGS="-fsanitize=address"
```

### Static Analysis

Comprehensive static code analysis:

```bash
# cppcheck analysis
make static-analysis

# clang-tidy (automatic with CMake)
cmake -B build -DCMAKE_CXX_CLANG_TIDY=clang-tidy
```

### Performance Profiling

Profile test execution:

```bash
# Generate profiling data
make profile
# View: build/profile_report.txt
```

## CI/CD Integration

Automated testing with GitHub Actions:

### Workflow Features

- **Multi-Platform Testing**: Ubuntu 20.04, 22.04, latest
- **Multiple Compilers**: GCC and Clang versions
- **Comprehensive Checks**: Tests, static analysis, memory checking
- **Coverage Reporting**: Codecov integration
- **Performance Benchmarks**: Automated performance tracking
- **Documentation Generation**: Doxygen documentation

### Triggers

- Push to main/develop branches
- Pull requests
- Daily scheduled runs
- Manual workflow dispatch

## Writing New Tests

### Basic Test Structure

```cpp
TEST_F(MPU6050DriverTest, YourTestName) {
    // Arrange: Set up test conditions
    setupSuccessfulProbe();
    setupValidSensorData();
    
    // Act: Execute the code under test
    int result = mpu6050_your_function(&test_client_);
    
    // Assert: Verify the results
    EXPECT_EQ(result, 0);
    EXPECT_GT(MockI2CInterface::getInstance().getReadCount(), 0);
}
```

### Using Test Fixtures

```cpp
TEST_F(MPU6050DriverTest, TestWithFixtures) {
    // Use predefined sensor data
    auto motion_data = GET_FIXTURE_MANAGER().getMotionPatterns().vibration;
    
    // Set up mock with fixture data
    for (const auto& sample : motion_data) {
        MockI2CInterface::getInstance().simulateSensorData(
            sample.accel_x, sample.accel_y, sample.accel_z,
            sample.gyro_x, sample.gyro_y, sample.gyro_z,
            sample.temperature
        );
        
        // Test with this data point
        // ... your test code ...
    }
}
```

### Error Injection Testing

```cpp
TEST_F(MPU6050DriverTest, TestErrorRecovery) {
    // Set up error injection
    MockI2CInterface::getInstance().enableErrorInjection(true);
    MockI2CInterface::getInstance().setErrorInjectionRate(0.3); // 30% error rate
    MockI2CInterface::getInstance().simulateI2CError(EIO);
    
    // Test error handling
    int success_count = 0;
    for (int i = 0; i < 100; i++) {
        int result = mpu6050_read_sensor_data(&test_client_, ...);
        if (result == 0) success_count++;
    }
    
    // Verify error handling behavior
    EXPECT_GT(success_count, 60); // Should succeed ~70% of the time
    EXPECT_LT(success_count, 80);
}
```

## Best Practices

### Test Design

1. **One Thing Per Test**: Each test should verify one specific behavior
2. **Clear Test Names**: Use descriptive names that explain what is being tested
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
4. **Independent Tests**: Tests should not depend on each other
5. **Realistic Data**: Use realistic sensor values and motion patterns

### Mock Usage

1. **Verify Interactions**: Use EXPECT_CALL to verify I2C interactions
2. **Simulate Realistic Conditions**: Add noise, delays, and error conditions
3. **Test Edge Cases**: Test boundary conditions and error scenarios
4. **Reset Mock State**: Clear mock state between tests

### Performance Considerations

1. **Efficient Tests**: Keep individual tests fast (< 100ms)
2. **Batch Operations**: Group related operations in single tests
3. **Resource Cleanup**: Properly clean up resources after tests
4. **Parallel Execution**: Design tests to run in parallel safely

## Troubleshooting

### Common Issues

#### Build Errors

```bash
# Missing Google Test
sudo apt-get install libgtest-dev libgmock-dev

# CMake version too old
sudo apt-get install cmake
# Or install newer version from CMake website

# Missing pkg-config
sudo apt-get install pkg-config
```

#### Runtime Issues

```bash
# Test executable crashes
# Run with GDB for debugging
gdb ./build/mpu6050_unit_tests
(gdb) run
(gdb) bt

# Memory issues
# Use Valgrind for memory debugging
valgrind --tool=memcheck ./build/mpu6050_unit_tests
```

#### Test Failures

```bash
# Run specific failing test
./build/mpu6050_unit_tests --gtest_filter="*FailingTestName*"

# Run with verbose output
./build/mpu6050_unit_tests --verbose --gtest_filter="*FailingTestName*"

# Generate XML output for analysis
./build/mpu6050_unit_tests --gtest_output=xml:results.xml
```

### Debug Mode

Enable detailed debugging output:

```cpp
// In test code
MPU6050TestConfig::getInstance().enableVerboseLogging();

// Or via command line
./build/mpu6050_unit_tests --verbose
```

## Contributing

### Adding New Tests

1. Follow existing test patterns and naming conventions
2. Add comprehensive documentation for new test functions
3. Include both positive and negative test cases
4. Test edge cases and error conditions
5. Update this README if adding new test categories

### Improving Mocks

1. Keep mock behavior realistic
2. Add new mock capabilities as needed
3. Maintain backwards compatibility
4. Document new mock features

### Performance Improvements

1. Profile tests to identify bottlenecks
2. Optimize slow-running tests
3. Maintain test accuracy while improving speed
4. Consider parallel execution for independent tests

## License

This test framework is part of the MPU-6050 Linux kernel driver project and follows the same licensing terms as the main driver code.

## Support

For issues, questions, or contributions:

1. Check existing test cases for examples
2. Review mock interface documentation
3. Run tests with verbose output for debugging
4. Submit issues with detailed error information

---

*This testing framework provides comprehensive validation of the MPU-6050 kernel driver without requiring physical hardware, enabling rapid development, debugging, and validation of driver functionality.*