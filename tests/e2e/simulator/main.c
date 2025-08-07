#define _GNU_SOURCE
#include "simulator.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <signal.h>

// External function from test_scenarios.c
extern int run_all_test_scenarios(void);

// Global flag for clean shutdown
static volatile sig_atomic_t running = 1;

static void signal_handler(int sig) {
    (void)sig; // Unused parameter
    printf("\nReceived interrupt signal, shutting down...\n");
    running = 0;
}

static void print_usage(const char* program_name) {
    printf("Usage: %s [OPTIONS]\n", program_name);
    printf("\nMPU-6050 I2C Virtual Simulator Test Suite\n\n");
    printf("Options:\n");
    printf("  -h, --help          Show this help message\n");
    printf("  -v, --verbose       Enable verbose debug logging\n");
    printf("  -b, --benchmark     Run performance benchmarks\n");
    printf("  -s, --scenario NAME Run specific test scenario\n");
    printf("  -l, --list          List available test scenarios\n");
    printf("  -q, --quick         Run quick test suite (basic tests only)\n");
    printf("  -c, --continuous    Run continuous testing until interrupted\n");
    printf("  -n, --noise LEVEL   Set bus noise level (0.0-1.0)\n");
    printf("  -d, --delay US      Set global I2C delay in microseconds\n");
    printf("\nTest Scenarios:\n");
    printf("  normal_operation    - Basic MPU-6050 functionality\n");
    printf("  fifo_operation      - FIFO buffer testing\n");
    printf("  error_injection     - Error condition testing\n");
    printf("  power_management    - Power state transitions\n");
    printf("  concurrent_access   - Multi-threaded access\n");
    printf("  stress_test         - High-load stress testing\n");
    printf("\nExamples:\n");
    printf("  %s                      # Run all tests\n", program_name);
    printf("  %s -v                   # Run with verbose output\n", program_name);
    printf("  %s -s stress_test       # Run specific scenario\n", program_name);
    printf("  %s -b                   # Run benchmarks\n", program_name);
    printf("  %s -c                   # Continuous testing\n", program_name);
}

static void list_scenarios(void) {
    printf("Available Test Scenarios:\n");
    printf("========================\n");
    printf("1. normal_operation    - Standard MPU-6050 operation with gravity simulation\n");
    printf("2. fifo_operation      - FIFO buffer functionality with sine wave data\n");
    printf("3. high_frequency      - High-rate sampling (1kHz) with vibration pattern\n");
    printf("4. noisy_environment   - Random noise pattern for robustness testing\n");
    printf("5. rotation_simulation - Device rotation with realistic motion patterns\n");
    printf("6. power_management    - Power state transitions and wake/sleep cycles\n");
    printf("7. intermittent_errors - Communication errors with 5%% failure rate\n");
    printf("8. bus_errors          - I2C bus error conditions (2%% error rate)\n");
    printf("9. timeout_conditions  - Timeout simulation (1%% timeout rate)\n");
    printf("10. data_corruption    - Data corruption scenarios (3%% corruption rate)\n");
    printf("11. device_not_found   - Device disconnection simulation\n");
    printf("12. fifo_overflow      - FIFO buffer overflow testing\n");
    printf("13. concurrent_access  - Multi-threaded concurrent access\n");
    printf("14. stress_test        - Combined high-load with error injection\n");
}

static int run_benchmark(void) {
    printf("\n=== Performance Benchmarks ===\n");
    
    if (i2c_simulator_init() != 0) {
        printf("ERROR: Failed to initialize simulator\n");
        return -1;
    }
    
    const uint8_t device_addr = MPU6050_ADDR;
    const int bus = 0;
    
    if (i2c_simulator_add_device(bus, device_addr, "mpu6050") != 0) {
        printf("ERROR: Failed to add MPU-6050 device\n");
        return -1;
    }
    
    // Configure for optimal performance
    mpu6050_simulator_set_pattern(device_addr, PATTERN_STATIC);
    mpu6050_set_power_state(device_addr, POWER_ON);
    set_global_latency(0); // Minimal latency
    
    // Benchmark 1: Single byte reads
    printf("\nBenchmark 1: Single Byte Reads\n");
    reset_performance_metrics();
    
    const int read_iterations = 10000;
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int i = 0; i < read_iterations; i++) {
        uint8_t data;
        i2c_simulator_read_byte(bus, device_addr, MPU6050_WHO_AM_I, &data);
    }
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("  %d reads in %.3f seconds\n", read_iterations, elapsed);
    printf("  Throughput: %.0f reads/second\n", read_iterations / elapsed);
    
    // Benchmark 2: Burst reads
    printf("\nBenchmark 2: Burst Reads (14 bytes)\n");
    reset_performance_metrics();
    
    const int burst_iterations = 5000;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int i = 0; i < burst_iterations; i++) {
        uint8_t data[14];
        i2c_simulator_read_burst(bus, device_addr, MPU6050_ACCEL_XOUT_H, data, 14);
    }
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("  %d burst reads in %.3f seconds\n", burst_iterations, elapsed);
    printf("  Throughput: %.0f burst reads/second\n", burst_iterations / elapsed);
    printf("  Data rate: %.0f bytes/second\n", (burst_iterations * 14) / elapsed);
    
    // Benchmark 3: Mixed operations
    printf("\nBenchmark 3: Mixed Read/Write Operations\n");
    reset_performance_metrics();
    
    const int mixed_iterations = 2000;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int i = 0; i < mixed_iterations; i++) {
        uint8_t data;
        // Read WHO_AM_I
        i2c_simulator_read_byte(bus, device_addr, MPU6050_WHO_AM_I, &data);
        // Write to config register
        i2c_simulator_write_byte(bus, device_addr, MPU6050_ACCEL_CONFIG, i % 4);
        // Read sensor data burst
        uint8_t sensor_data[14];
        i2c_simulator_read_burst(bus, device_addr, MPU6050_ACCEL_XOUT_H, sensor_data, 14);
    }
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("  %d mixed operations in %.3f seconds\n", mixed_iterations, elapsed);
    printf("  Throughput: %.0f operations/second\n", (mixed_iterations * 3) / elapsed);
    
    // Benchmark 4: FIFO operations
    printf("\nBenchmark 4: FIFO Operations\n");
    mpu6050_fifo_enable(device_addr, true);
    mpu6050_simulator_set_pattern(device_addr, PATTERN_SINE_WAVE);
    
    reset_performance_metrics();
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    // Let FIFO fill up
    usleep(100000); // 100ms
    
    const int fifo_reads = 1000;
    for (int i = 0; i < fifo_reads; i++) {
        uint16_t count;
        mpu6050_fifo_get_count(device_addr, &count);
        if (count > 0) {
            uint8_t fifo_data[64];
            mpu6050_fifo_read(device_addr, fifo_data, sizeof(fifo_data));
        }
    }
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("  %d FIFO operations in %.3f seconds\n", fifo_reads, elapsed);
    printf("  Throughput: %.0f FIFO ops/second\n", fifo_reads / elapsed);
    
    print_performance_report();
    
    i2c_simulator_remove_device(bus, device_addr);
    i2c_simulator_cleanup();
    
    return 0;
}

static int run_quick_test(void) {
    printf("\n=== Quick Test Suite ===\n");
    
    if (i2c_simulator_init() != 0) {
        printf("ERROR: Failed to initialize simulator\n");
        return -1;
    }
    
    const uint8_t device_addr = MPU6050_ADDR;
    const int bus = 0;
    
    printf("Test 1: Device Creation and Identification\n");
    if (i2c_simulator_add_device(bus, device_addr, "mpu6050") != 0) {
        printf("FAIL: Could not add device\n");
        return -1;
    }
    
    uint8_t who_am_i;
    if (i2c_simulator_read_byte(bus, device_addr, MPU6050_WHO_AM_I, &who_am_i) != 0) {
        printf("FAIL: Could not read WHO_AM_I\n");
        return -1;
    }
    
    if (who_am_i != MPU6050_WHO_AM_I_VALUE) {
        printf("FAIL: Invalid WHO_AM_I value: 0x%02X\n", who_am_i);
        return -1;
    }
    printf("PASS: WHO_AM_I = 0x%02X\n", who_am_i);
    
    printf("\nTest 2: Power Management\n");
    mpu6050_set_power_state(device_addr, POWER_ON);
    if (mpu6050_get_power_state(device_addr) != POWER_ON) {
        printf("FAIL: Power state not set correctly\n");
        return -1;
    }
    printf("PASS: Power state management working\n");
    
    printf("\nTest 3: Sensor Data Reading\n");
    mpu6050_simulator_set_pattern(device_addr, PATTERN_GRAVITY_ONLY);
    uint8_t accel_data[6];
    if (i2c_simulator_read_burst(bus, device_addr, MPU6050_ACCEL_XOUT_H, accel_data, 6) != 0) {
        printf("FAIL: Could not read accelerometer data\n");
        return -1;
    }
    
    int16_t az = (int16_t)((accel_data[4] << 8) | accel_data[5]);
    if (abs(az - 16384) > 1000) { // Should be close to 1g (16384 LSB)
        printf("FAIL: Gravity simulation not working, Z-axis = %d\n", az);
        return -1;
    }
    printf("PASS: Sensor data reading working (Z-axis = %d)\n", az);
    
    printf("\nTest 4: FIFO Functionality\n");
    mpu6050_fifo_enable(device_addr, true);
    usleep(50000); // Let some data accumulate
    
    uint16_t fifo_count;
    if (mpu6050_fifo_get_count(device_addr, &fifo_count) != 0) {
        printf("FAIL: Could not read FIFO count\n");
        return -1;
    }
    
    if (fifo_count == 0) {
        printf("FAIL: FIFO not accumulating data\n");
        return -1;
    }
    printf("PASS: FIFO functionality working (%d bytes)\n", fifo_count);
    
    i2c_simulator_remove_device(bus, device_addr);
    i2c_simulator_cleanup();
    
    printf("\n✓ Quick test suite completed successfully!\n");
    return 0;
}

static int run_continuous_test(void) {
    printf("\n=== Continuous Testing Mode ===\n");
    printf("Press Ctrl+C to stop...\n");
    
    // Set up signal handler
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    if (i2c_simulator_init() != 0) {
        printf("ERROR: Failed to initialize simulator\n");
        return -1;
    }
    
    const uint8_t device_addr = MPU6050_ADDR;
    const int bus = 0;
    
    if (i2c_simulator_add_device(bus, device_addr, "mpu6050") != 0) {
        printf("ERROR: Failed to add device\n");
        return -1;
    }
    
    // Configure for continuous operation
    mpu6050_simulator_set_pattern(device_addr, PATTERN_ROTATION);
    mpu6050_set_power_state(device_addr, POWER_ON);
    mpu6050_fifo_enable(device_addr, true);
    
    uint32_t iteration = 0;
    reset_performance_metrics();
    
    while (running) {
        // Read sensor data
        uint8_t sensor_data[14];
        if (i2c_simulator_read_burst(bus, device_addr, MPU6050_ACCEL_XOUT_H, sensor_data, 14) == 0) {
            int16_t ax = (int16_t)((sensor_data[0] << 8) | sensor_data[1]);
            int16_t ay = (int16_t)((sensor_data[2] << 8) | sensor_data[3]);
            int16_t az = (int16_t)((sensor_data[4] << 8) | sensor_data[5]);
            int16_t gx = (int16_t)((sensor_data[8] << 8) | sensor_data[9]);
            int16_t gy = (int16_t)((sensor_data[10] << 8) | sensor_data[11]);
            int16_t gz = (int16_t)((sensor_data[12] << 8) | sensor_data[13]);
            
            if (iteration % 1000 == 0) {
                printf("Iteration %u: Accel(%d,%d,%d) Gyro(%d,%d,%d)\n",
                       iteration, ax, ay, az, gx, gy, gz);
            }
        }
        
        // Check FIFO occasionally
        if (iteration % 100 == 0) {
            uint16_t fifo_count;
            if (mpu6050_fifo_get_count(device_addr, &fifo_count) == 0 && fifo_count > 50) {
                uint8_t fifo_data[64];
                mpu6050_fifo_read(device_addr, fifo_data, sizeof(fifo_data));
            }
        }
        
        // Print status every 10 seconds
        if (iteration % 10000 == 0 && iteration > 0) {
            performance_metrics_t metrics = get_performance_metrics();
            printf("\nStatus: %u iterations, %u reads, %u writes, %.2f ops/sec\n",
                   iteration, metrics.total_reads, metrics.total_writes,
                   (double)(metrics.total_reads + metrics.total_writes) / 
                   (iteration / 1000.0));
        }
        
        iteration++;
        usleep(1000); // 1ms delay = ~1kHz sampling
    }
    
    printf("\nStopping continuous test...\n");
    print_performance_report();
    
    i2c_simulator_remove_device(bus, device_addr);
    i2c_simulator_cleanup();
    
    return 0;
}

int main(int argc, char* argv[]) {
    int opt;
    bool verbose = false;
    bool benchmark = false;
    bool list_only = false;
    bool quick_test = false;
    bool continuous = false;
    char* scenario_name = NULL;
    double noise_level = -1.0;
    int delay_us = -1;
    
    static struct option long_options[] = {
        {"help", no_argument, 0, 'h'},
        {"verbose", no_argument, 0, 'v'},
        {"benchmark", no_argument, 0, 'b'},
        {"scenario", required_argument, 0, 's'},
        {"list", no_argument, 0, 'l'},
        {"quick", no_argument, 0, 'q'},
        {"continuous", no_argument, 0, 'c'},
        {"noise", required_argument, 0, 'n'},
        {"delay", required_argument, 0, 'd'},
        {0, 0, 0, 0}
    };
    
    while ((opt = getopt_long(argc, argv, "hvbs:lqcn:d:", long_options, NULL)) != -1) {
        switch (opt) {
            case 'h':
                print_usage(argv[0]);
                return 0;
            case 'v':
                verbose = true;
                break;
            case 'b':
                benchmark = true;
                break;
            case 's':
                scenario_name = optarg;
                break;
            case 'l':
                list_only = true;
                break;
            case 'q':
                quick_test = true;
                break;
            case 'c':
                continuous = true;
                break;
            case 'n':
                noise_level = atof(optarg);
                if (noise_level < 0.0 || noise_level > 1.0) {
                    fprintf(stderr, "Error: Noise level must be between 0.0 and 1.0\n");
                    return 1;
                }
                break;
            case 'd':
                delay_us = atoi(optarg);
                if (delay_us < 0) {
                    fprintf(stderr, "Error: Delay must be non-negative\n");
                    return 1;
                }
                break;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }
    
    // Print banner
    printf("MPU-6050 I2C Virtual Simulator\n");
    printf("===============================\n");
    printf("Version: 1.0.0\n");
    printf("Built: %s %s\n", __DATE__, __TIME__);
    printf("Features: Thread-safe, Docker-compatible, No root required\n\n");
    
    // Configure simulator
    if (verbose) {
        enable_debug_logging(true);
        printf("Debug logging enabled\n");
    }
    
    if (noise_level >= 0.0) {
        set_bus_noise_level(0, noise_level);
        printf("Bus noise level set to %.2f\n", noise_level);
    }
    
    if (delay_us >= 0) {
        set_global_latency(delay_us);
        printf("Global I2C delay set to %d µs\n", delay_us);
    }
    
    // Handle different modes
    if (list_only) {
        list_scenarios();
        return 0;
    }
    
    if (benchmark) {
        return run_benchmark();
    }
    
    if (quick_test) {
        return run_quick_test();
    }
    
    if (continuous) {
        return run_continuous_test();
    }
    
    if (scenario_name) {
        printf("Running specific scenario: %s\n", scenario_name);
        // TODO: Implement specific scenario selection
        printf("Specific scenario selection not yet implemented\n");
        printf("Running all test scenarios instead...\n");
    }
    
    // Default: run all test scenarios
    printf("Running complete test suite...\n");
    int result = run_all_test_scenarios();
    
    if (result == 0) {
        printf("\n🎉 All tests completed successfully! 🎉\n");
    } else {
        printf("\n❌ Some tests failed. Check output above for details. ❌\n");
    }
    
    return result;
}