# MPU-6050 Docker-based E2E Testing Environment

This directory contains a comprehensive Docker-based end-to-end testing environment for the MPU-6050 Linux kernel driver. The environment supports both local development and CI/CD pipelines.

## 📁 Directory Structure

```
tests/e2e/docker/
├── Dockerfile.e2e              # Multi-stage Docker build
├── docker-compose.yml          # Complete testing stack
├── entrypoint.sh              # Container entrypoint script
├── run_e2e_docker.sh          # Docker orchestration script
├── init-db.sql                # PostgreSQL schema
├── .dockerignore              # Docker build exclusions
├── grafana-dashboards/        # Dashboard configurations
│   └── dashboard.yml
├── grafana-datasources/       # Data source configurations
│   └── datasources.yml
├── test-results/              # Test output directory
├── test-logs/                 # Log output directory
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+ (or docker-compose 1.29+)
- 4GB+ available RAM
- 10GB+ available disk space

### Run All Tests

```bash
# From the project root
cd tests/e2e/docker

# Build and run all tests
./run_e2e_docker.sh

# Run with verbose output
TEST_VERBOSE=true ./run_e2e_docker.sh

# Run only C tests
./run_e2e_docker.sh --c-tests-only

# Run with Docker Compose (includes database and dashboard)
./run_e2e_docker.sh --use-compose
```

### Run Individual Components

```bash
# Build Docker image only
./run_e2e_docker.sh --build-only

# Run tests with existing image
./run_e2e_docker.sh --run-only

# Clean up and rebuild
./run_e2e_docker.sh --clean-first
```

## 🐳 Docker Components

### Main Test Container

The primary test container (`mpu6050-e2e-tests`) includes:

- **Base System**: Ubuntu 22.04 with kernel headers
- **Build Tools**: GCC, Make, CMake, kernel development tools
- **Testing Frameworks**: CUnit, pytest, coverage tools
- **Python Environment**: Python 3 with testing and analysis libraries
- **I2C Simulator**: Custom MPU-6050 device simulator
- **Monitoring Tools**: System monitoring and profiling utilities

### Supporting Services (Docker Compose)

- **PostgreSQL Database** (`test-database`): Stores test results and metrics
- **Grafana Dashboard** (`test-dashboard`): Visualizes test results and trends
- **Elasticsearch** (`log-aggregator`): Centralized logging (optional)

## 🔧 Configuration

### Environment Variables

Configure the test environment using these variables:

#### Test Configuration
```bash
TEST_VERBOSE=true              # Enable verbose output
TEST_CONTINUOUS=false          # Run tests continuously
TEST_TIMEOUT=300               # Test timeout in seconds
TEST_RETRIES=3                 # Number of test retries
TEST_PARALLEL=true             # Enable parallel execution
```

#### Hardware Simulation
```bash
SIMULATE_HARDWARE=true         # Enable hardware simulation
SIMULATOR_ENABLED=true         # Enable I2C simulator
I2C_SIMULATOR_BUS=1           # Simulated I2C bus number
MPU6050_I2C_ADDR=0x68         # Device I2C address
```

#### Coverage and Performance
```bash
COVERAGE_ENABLED=true          # Enable code coverage collection
COVERAGE_MIN_THRESHOLD=80      # Minimum coverage threshold
PERF_TEST_ENABLED=true         # Enable performance tests
PERF_MIN_THROUGHPUT=50         # Minimum required throughput
PERF_TEST_DURATION=60          # Performance test duration
```

#### Logging
```bash
LOG_LEVEL=INFO                 # Log level (DEBUG/INFO/WARN/ERROR)
LOG_FORMAT=detailed            # Log format style
COLORIZED_OUTPUT=true          # Enable colored output
```

#### CI/CD Integration
```bash
CI=false                       # Enable CI mode
GITHUB_ACTIONS=false          # GitHub Actions integration
BUILD_NUMBER=0                 # Build number
GIT_COMMIT=HEAD               # Git commit hash
GIT_BRANCH=main               # Git branch name
```

### Docker Compose Profiles

Control which services to start:

```bash
# Start with dashboard
docker-compose --profile dashboard up

# Start with logging
docker-compose --profile logging up

# Start everything
docker-compose --profile dashboard --profile logging up
```

## 📊 Test Types

The environment supports multiple test categories:

### 1. C-based Tests
- **Device Accessibility**: Basic device open/close operations
- **WHO_AM_I Test**: Device identification verification
- **Configuration Tests**: Register read/write operations
- **Data Reading**: Raw and scaled sensor data tests
- **Reset Functionality**: Device reset and recovery tests
- **Error Conditions**: Error handling and edge cases
- **Performance**: Throughput and latency measurements

### 2. Python-based Tests
- **Advanced Scenarios**: Complex test sequences
- **Data Validation**: Comprehensive range and consistency checks
- **Stress Testing**: High-load and endurance tests
- **Regression Tests**: Automated regression detection

### 3. Performance Tests
- **Throughput Measurement**: Operations per second
- **Latency Analysis**: Response time distribution
- **Concurrent Access**: Multi-threaded performance
- **Resource Usage**: CPU and memory monitoring

## 📈 Results and Reporting

### Test Results

Results are stored in multiple formats:

- **Console Output**: Real-time test progress
- **Log Files**: Detailed execution logs in `test-logs/`
- **JSON Results**: Structured results in `test-results/`
- **Coverage Reports**: HTML and XML coverage reports
- **Performance Data**: Detailed performance metrics

### Database Storage

When using Docker Compose, results are stored in PostgreSQL:

- **test_executions**: Overall test run information
- **test_results**: Individual test outcomes
- **performance_metrics**: Performance measurements
- **coverage_data**: Code coverage information
- **error_logs**: Detailed error information

### Dashboard Visualization

Grafana dashboard provides:

- **Test Trends**: Pass/fail rates over time
- **Performance Metrics**: Throughput and latency trends
- **Coverage Trends**: Code coverage evolution
- **Error Analysis**: Failure pattern analysis

## 🛠️ Development Workflow

### Local Development

1. **Make Changes**: Modify driver or test code
2. **Quick Test**: Run specific tests
   ```bash
   ./run_e2e_docker.sh --c-tests-only
   ```
3. **Full Validation**: Run complete test suite
   ```bash
   ./run_e2e_docker.sh
   ```
4. **Check Coverage**: Review coverage reports
   ```bash
   open test-results/htmlcov/index.html
   ```

### CI/CD Integration

```bash
# In CI pipeline
CI=true GITHUB_ACTIONS=true ./run_e2e_docker.sh
```

The environment automatically:
- Adjusts resource limits for CI
- Generates machine-readable reports
- Handles cleanup and error codes properly

## 🔍 Troubleshooting

### Common Issues

#### Docker Build Fails
```bash
# Clean Docker cache
docker system prune -f

# Rebuild without cache
./run_e2e_docker.sh --clean-first
```

#### Tests Fail to Access Device
```bash
# Enable hardware simulation
SIMULATE_HARDWARE=true ./run_e2e_docker.sh
```

#### Permission Issues
```bash
# Fix directory permissions
sudo chown -R $(id -u):$(id -g) test-results test-logs
```

#### Out of Memory
```bash
# Reduce parallel jobs
TEST_PARALLEL=false ./run_e2e_docker.sh
```

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG TEST_VERBOSE=true ./run_e2e_docker.sh

# Keep container running after tests
docker run -it --rm mpu6050-e2e-test:latest /bin/bash
```

### Log Analysis

```bash
# View real-time logs
tail -f test-logs/test-execution.log

# Search for errors
grep -i error test-logs/*.log

# Check kernel messages
grep -i mpu6050 test-logs/kernel.log
```

## 📋 Test Execution Flow

1. **Environment Validation**: Check prerequisites and setup
2. **Module Building**: Compile kernel modules and test programs
3. **Simulator Initialization**: Start I2C device simulator
4. **Test Execution**: Run test suites in sequence
5. **Results Collection**: Gather logs, coverage, and metrics
6. **Report Generation**: Create comprehensive test reports
7. **Cleanup**: Remove containers and temporary files

## 🚦 Exit Codes

- **0**: All tests passed successfully
- **1**: Some tests failed
- **2**: Environment setup failed
- **3**: Build failures
- **130**: Interrupted by user (Ctrl+C)
- **143**: Terminated by system signal

## 🤝 Contributing

To extend the testing environment:

1. **Add Tests**: Place new tests in appropriate directories
2. **Update Configuration**: Modify environment variables as needed
3. **Extend Dockerfile**: Add new tools or dependencies
4. **Update Documentation**: Keep this README current

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Linux Kernel Testing](https://www.kernel.org/doc/html/latest/dev-tools/testing-overview.html)
- [MPU-6050 Datasheet](https://invensense.tdk.com/products/motion-tracking/6-axis/mpu-6050/)

---

**Author**: Murray Kopit <murr2k@gmail.com>  
**Project**: MPU-6050 Linux Kernel Driver  
**License**: GPL-2.0