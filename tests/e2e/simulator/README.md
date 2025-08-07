# MPU-6050 I2C Virtual Simulator

A comprehensive virtual I2C bus simulator specifically designed for the MPU-6050 6-axis motion sensor. This simulator enables testing of MPU-6050 drivers and applications without physical hardware, making it perfect for CI/CD pipelines, Docker containers, and development environments.

## Features

### Core Simulator Capabilities
- **Virtual I2C Bus**: Complete I2C protocol simulation with realistic timing
- **MPU-6050 Emulation**: Full register map and behavior simulation
- **Multi-device Support**: Support for up to 128 devices on 2 I2C buses
- **Thread-safe**: Concurrent access from multiple threads
- **No Root Required**: Runs entirely in user space
- **Docker Compatible**: Works in containerized environments

### MPU-6050 Specific Features
- **Complete Register Map**: All standard MPU-6050 registers implemented
- **Realistic Sensor Data**: Configurable data generation patterns
- **FIFO Buffer Simulation**: Full FIFO implementation with overflow detection
- **Power Management**: Sleep, cycle, and wake modes
- **Interrupt Generation**: Configurable interrupt sources
- **Self-test Mode**: Built-in self-test functionality

### Data Generation Patterns
- **Static**: Constant values (useful for basic testing)
- **Gravity Only**: Realistic gravity simulation (1g on Z-axis)
- **Sine Wave**: Smooth periodic motion simulation
- **Noise**: Random noise patterns for stress testing
- **Rotation**: Simulated device rotation with realistic angular rates
- **Vibration**: High-frequency vibration patterns

### Error Injection
- **Device Not Found**: Simulate disconnected or faulty devices
- **Timeout Errors**: I2C communication timeouts
- **Bus Errors**: General I2C bus error conditions
- **Data Corruption**: Corrupted data transmission
- **Intermittent Errors**: Random communication failures

## Architecture

```
┌─────────────────────────────────────────┐
│              Application                 │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│           I2C Simulator API             │
├─────────────────────────────────────────┤
│         Virtual I2C Bus Layer           │
├─────────────────────────────────────────┤
│        MPU-6050 Virtual Device          │
├─────────────────┬───────────────────────┤
│   Register Map  │  FIFO Buffer │ Data Gen│
└─────────────────┴───────────────────────┘
```

## Building

### Prerequisites
- GCC compiler with C99 support
- pthread library
- make utility

### Build Commands
```bash
# Build everything (library, tests, examples)
make all

# Build only the library
make libi2csim.a

# Build test program
make simulator_test

# Build example program  
make simulator_example
```

## Usage

### Basic Example
```c
#include "simulator.h"

int main(void) {
    // Initialize simulator
    i2c_simulator_init();
    
    // Add MPU-6050 device to bus 0 at address 0x68
    i2c_simulator_add_device(0, 0x68, "mpu6050");
    
    // Configure device behavior
    mpu6050_simulator_set_pattern(0x68, PATTERN_GRAVITY_ONLY);
    mpu6050_set_power_state(0x68, POWER_ON);
    
    // Read WHO_AM_I register
    uint8_t who_am_i;
    i2c_simulator_read_byte(0, 0x68, 0x75, &who_am_i);
    printf("WHO_AM_I: 0x%02X\n", who_am_i);
    
    // Read accelerometer data
    uint8_t accel_data[6];
    i2c_simulator_read_burst(0, 0x68, 0x3B, accel_data, 6);
    
    // Cleanup
    i2c_simulator_cleanup();
    return 0;
}
```

### Test Scenarios
The simulator includes predefined test scenarios:

```c
// Load and run test scenarios
load_test_scenarios(NULL); // Uses built-in scenarios

// Run specific scenario
const test_scenario_t scenario = {
    .name = "custom_test",
    .pattern = PATTERN_SINE_WAVE,
    .error_mode = ERROR_NONE,
    .duration_ms = 5000,
    .sample_rate_hz = 100,
    .enable_fifo = true
};
run_test_scenario(&scenario);
```

## API Reference

### Core Functions
```c
// Simulator lifecycle
int i2c_simulator_init(void);
void i2c_simulator_cleanup(void);

// Device management
int i2c_simulator_add_device(int bus, uint8_t address, const char* type);
int i2c_simulator_remove_device(int bus, uint8_t address);

// I2C operations
int i2c_simulator_read_byte(int bus, uint8_t addr, uint8_t reg, uint8_t* data);
int i2c_simulator_write_byte(int bus, uint8_t addr, uint8_t reg, uint8_t data);
int i2c_simulator_read_burst(int bus, uint8_t addr, uint8_t reg, uint8_t* data, size_t len);
```

### MPU-6050 Specific Functions
```c
// Device configuration
int mpu6050_simulator_set_pattern(uint8_t addr, data_pattern_t pattern);
int mpu6050_simulator_set_error_mode(uint8_t addr, error_type_t error, double prob);
int mpu6050_set_power_state(uint8_t addr, power_state_t state);

// FIFO operations
int mpu6050_fifo_enable(uint8_t addr, bool enable);
int mpu6050_fifo_get_count(uint8_t addr, uint16_t* count);
int mpu6050_fifo_read(uint8_t addr, uint8_t* data, size_t len);

// Data access
int mpu6050_simulator_get_data(uint8_t addr, sensor_data_t* data);
```

### Performance Monitoring
```c
// Performance metrics
void reset_performance_metrics(void);
performance_metrics_t get_performance_metrics(void);
void print_performance_report(void);

// Configuration
int set_bus_noise_level(int bus, double noise_level);
int set_global_latency(uint32_t latency_us);
int enable_debug_logging(bool enable);
```

## Test Scenarios

### Built-in Scenarios
1. **Normal Operation**: Basic sensor readings with gravity simulation
2. **FIFO Operation**: FIFO buffer testing with sine wave data
3. **High Frequency Sampling**: Stress test with 1kHz sampling rate
4. **Noisy Environment**: Random noise pattern testing
5. **Rotation Simulation**: Realistic device rotation patterns
6. **Power Management**: Power state transition testing
7. **Error Conditions**: Various error injection scenarios
8. **Concurrent Access**: Multi-threaded access testing
9. **Stress Test**: Combined high-rate sampling with error injection

### Running Tests
```bash
# Run all test scenarios
make test

# Run with verbose output
make test-verbose

# Run memory check (requires valgrind)
make memcheck

# Run performance benchmarks
make benchmark
```

## CI/CD Integration

### Docker Usage
```dockerfile
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y gcc make libc6-dev
COPY . /app
WORKDIR /app/tests/e2e/simulator
RUN make all
RUN make ci-test
```

### GitHub Actions Example
```yaml
name: MPU-6050 Simulator Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Build and test simulator
      run: |
        cd tests/e2e/simulator
        make all
        make ci-test
```

### Jenkins Pipeline
```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                dir('tests/e2e/simulator') {
                    sh 'make all'
                }
            }
        }
        stage('Test') {
            steps {
                dir('tests/e2e/simulator') {
                    sh 'make ci-test'
                }
            }
        }
    }
}
```

## Performance

### Benchmarks
- **Throughput**: Up to 10,000 operations/second
- **Latency**: 10-100µs per operation (configurable)
- **Memory Usage**: <1MB RAM footprint
- **Concurrency**: Supports 100+ concurrent threads

### Optimization Tips
- Use burst reads for multiple registers
- Enable FIFO buffering for high-rate sampling
- Adjust global latency based on test requirements
- Use appropriate data patterns for specific test cases

## Error Handling

### Error Types
- **-EINVAL**: Invalid parameter
- **-ENODEV**: Device not found or not responding
- **-ETIMEDOUT**: Communication timeout
- **-EIO**: I2C bus error
- **-EACCES**: Register access denied
- **-ENOMEM**: Insufficient memory
- **-EEXIST**: Device already exists

### Error Injection Examples
```c
// Inject intermittent errors (5% failure rate)
mpu6050_simulator_set_error_mode(0x68, ERROR_INTERMITTENT, 0.05);

// Simulate device disconnection
mpu6050_simulator_set_error_mode(0x68, ERROR_DEVICE_NOT_FOUND, 0.1);

// Test timeout handling
mpu6050_simulator_set_error_mode(0x68, ERROR_TIMEOUT, 0.02);
```

## Advanced Features

### Custom Data Patterns
```c
// Create custom data generation
int16_t generate_custom_accel(data_pattern_t pattern, int axis, uint32_t sample) {
    // Custom implementation
    return custom_value;
}
```

### Memory Management
- Automatic cleanup on simulator shutdown
- Thread-safe memory operations
- Minimal memory allocation during runtime
- Support for memory leak detection tools

### Debug Features
- Comprehensive debug logging
- Performance metrics collection
- Real-time monitoring capabilities
- Detailed error reporting

## Troubleshooting

### Common Issues
1. **Compilation errors**: Ensure gcc and pthread are installed
2. **Permission denied**: Simulator runs in user space - no root needed
3. **Thread safety**: Use proper locking when accessing from multiple threads
4. **Memory leaks**: Always call `i2c_simulator_cleanup()`

### Debug Mode
```c
// Enable detailed logging
enable_debug_logging(true);

// Monitor performance
print_performance_report();
```

## Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd tests/e2e/simulator

# Build and test
make all
make test

# Run static analysis
make analyze

# Generate coverage report
make coverage
```

### Adding New Features
1. Update `simulator.h` with new API declarations
2. Implement functionality in appropriate `.c` file
3. Add test scenarios in `test_scenarios.c`
4. Update documentation

### Code Style
- Follow C99 standard
- Use consistent naming conventions
- Add comprehensive comments
- Include error handling
- Maintain thread safety

## License

This simulator is designed for testing and development purposes. See project license for usage terms.

## Support

For issues, feature requests, or questions:
1. Check the troubleshooting section
2. Review test scenarios for usage examples
3. Submit issues through the project repository
4. Contribute improvements via pull requests