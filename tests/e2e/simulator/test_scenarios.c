#define _GNU_SOURCE
#include "simulator.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <math.h>
#include <assert.h>

// Global test scenarios
static test_scenario_t g_test_scenarios[] = {
    {
        .name = "normal_operation",
        .description = "Normal MPU-6050 operation with gravity-only data",
        .pattern = PATTERN_GRAVITY_ONLY,
        .error_mode = ERROR_NONE,
        .error_probability = 0.0,
        .duration_ms = 5000,
        .sample_rate_hz = 100,
        .enable_fifo = false,
        .enable_interrupts = false,
        .initial_power_state = POWER_ON
    },
    {
        .name = "fifo_operation",
        .description = "FIFO buffer operation with sine wave data",
        .pattern = PATTERN_SINE_WAVE,
        .error_mode = ERROR_NONE,
        .error_probability = 0.0,
        .duration_ms = 3000,
        .sample_rate_hz = 200,
        .enable_fifo = true,
        .enable_interrupts = true,
        .initial_power_state = POWER_ON
    },
    {
        .name = "high_frequency_sampling",
        .description = "High frequency sampling with vibration pattern",
        .pattern = PATTERN_VIBRATION,
        .error_mode = ERROR_NONE,
        .error_probability = 0.0,
        .duration_ms = 2000,
        .sample_rate_hz = 1000,
        .enable_fifo = true,
        .enable_interrupts = false,
        .initial_power_state = POWER_ON
    },
    {
        .name = "noisy_environment",
        .description = "Operation in noisy environment with random data",
        .pattern = PATTERN_NOISE,
        .error_mode = ERROR_NONE,
        .error_probability = 0.0,
        .duration_ms = 4000,
        .sample_rate_hz = 50,
        .enable_fifo = false,
        .enable_interrupts = false,
        .initial_power_state = POWER_ON
    },
    {
        .name = "rotation_simulation",
        .description = "Device rotation simulation",
        .pattern = PATTERN_ROTATION,
        .error_mode = ERROR_NONE,
        .error_probability = 0.0,
        .duration_ms = 6000,
        .sample_rate_hz = 100,
        .enable_fifo = true,
        .enable_interrupts = true,
        .initial_power_state = POWER_ON
    },
    {
        .name = "power_management",
        .description = "Power management state transitions",
        .pattern = PATTERN_STATIC,
        .error_mode = ERROR_NONE,
        .error_probability = 0.0,
        .duration_ms = 8000,
        .sample_rate_hz = 10,
        .enable_fifo = false,
        .enable_interrupts = false,
        .initial_power_state = POWER_SLEEP
    },
    {
        .name = "intermittent_errors",
        .description = "Intermittent communication errors",
        .pattern = PATTERN_GRAVITY_ONLY,
        .error_mode = ERROR_INTERMITTENT,
        .error_probability = 0.05, // 5% error rate
        .duration_ms = 3000,
        .sample_rate_hz = 100,
        .enable_fifo = false,
        .enable_interrupts = false,
        .initial_power_state = POWER_ON
    },
    {
        .name = "bus_errors",
        .description = "I2C bus error conditions",
        .pattern = PATTERN_SINE_WAVE,
        .error_mode = ERROR_BUS_ERROR,
        .error_probability = 0.02, // 2% error rate
        .duration_ms = 4000,
        .sample_rate_hz = 200,
        .enable_fifo = true,
        .enable_interrupts = false,
        .initial_power_state = POWER_ON
    },
    {
        .name = "timeout_conditions",
        .description = "Timeout error simulation",
        .pattern = PATTERN_STATIC,
        .error_mode = ERROR_TIMEOUT,
        .error_probability = 0.01, // 1% timeout rate
        .duration_ms = 5000,
        .sample_rate_hz = 50,
        .enable_fifo = false,
        .enable_interrupts = false,
        .initial_power_state = POWER_ON
    },
    {
        .name = "data_corruption",
        .description = "Data corruption simulation",
        .pattern = PATTERN_ROTATION,
        .error_mode = ERROR_CORRUPT_DATA,
        .error_probability = 0.03, // 3% corruption rate
        .duration_ms = 3000,
        .sample_rate_hz = 100,
        .enable_fifo = true,
        .enable_interrupts = true,
        .initial_power_state = POWER_ON
    },
    {
        .name = "device_not_found",
        .description = "Device not found error simulation",
        .pattern = PATTERN_STATIC,
        .error_mode = ERROR_DEVICE_NOT_FOUND,
        .error_probability = 0.1, // 10% device not found rate
        .duration_ms = 2000,
        .sample_rate_hz = 10,
        .enable_fifo = false,
        .enable_interrupts = false,
        .initial_power_state = POWER_OFF
    },
    {
        .name = "fifo_overflow",
        .description = "FIFO buffer overflow testing",
        .pattern = PATTERN_VIBRATION,
        .error_mode = ERROR_NONE,
        .error_probability = 0.0,
        .duration_ms = 1000,
        .sample_rate_hz = 2000, // Very high rate to cause overflow
        .enable_fifo = true,
        .enable_interrupts = true,
        .initial_power_state = POWER_ON
    },
    {
        .name = "concurrent_access",
        .description = "Concurrent access from multiple threads",
        .pattern = PATTERN_SINE_WAVE,
        .error_mode = ERROR_NONE,
        .error_probability = 0.0,
        .duration_ms = 5000,
        .sample_rate_hz = 100,
        .enable_fifo = true,
        .enable_interrupts = false,
        .initial_power_state = POWER_ON
    },
    {
        .name = "stress_test",
        .description = "Stress test with high error rates and fast sampling",
        .pattern = PATTERN_NOISE,
        .error_mode = ERROR_INTERMITTENT,
        .error_probability = 0.15, // 15% error rate
        .duration_ms = 10000,
        .sample_rate_hz = 500,
        .enable_fifo = true,
        .enable_interrupts = true,
        .initial_power_state = POWER_ON
    }
};

static const int g_scenario_count = sizeof(g_test_scenarios) / sizeof(test_scenario_t);

// Forward declarations for test functions
static int test_normal_operation(void);
static int test_fifo_operation(void);
static int test_error_injection(void);
static int test_power_management(void);
static int test_concurrent_access(void);
static int test_performance_limits(void);
static int validate_sensor_data_ranges(const sensor_data_t* data);
static int run_basic_i2c_tests(void);
static void* concurrent_read_thread(void* arg);
static void* concurrent_write_thread(void* arg);

// Thread parameters for concurrent testing
typedef struct {
    int thread_id;
    int iterations;
    int bus;
    uint8_t device_addr;
    volatile int* error_count;
    volatile int* success_count;
} thread_params_t;

int load_test_scenarios(const char* config_file) {
    (void)config_file; // Unused for now - using hardcoded scenarios
    
    printf("Loaded %d test scenarios:\n", g_scenario_count);
    for (int i = 0; i < g_scenario_count; i++) {
        printf("  %d. %s - %s\n", i + 1, g_test_scenarios[i].name, g_test_scenarios[i].description);
    }
    
    return g_scenario_count;
}

int run_test_scenario(const test_scenario_t* scenario) {
    if (!scenario) {
        printf("ERROR: NULL scenario pointer\n");
        return -1;
    }
    
    printf("\n=== Running Test Scenario: %s ===\n", scenario->name);
    printf("Description: %s\n", scenario->description);
    printf("Duration: %u ms, Sample Rate: %u Hz\n", scenario->duration_ms, scenario->sample_rate_hz);
    printf("Pattern: %s, Error: %s (%.1f%%)\n", 
           pattern_type_to_string(scenario->pattern),
           error_type_to_string(scenario->error_mode),
           scenario->error_probability * 100.0);
    printf("FIFO: %s, Interrupts: %s, Power: %s\n",
           scenario->enable_fifo ? "enabled" : "disabled",
           scenario->enable_interrupts ? "enabled" : "disabled",
           power_state_to_string(scenario->initial_power_state));
    
    // Initialize simulator if not already done
    if (i2c_simulator_init() != 0) {
        printf("ERROR: Failed to initialize simulator\n");
        return -1;
    }
    
    // Add MPU-6050 device to bus 0
    const uint8_t device_addr = MPU6050_ADDR;
    const int bus = 0;
    
    if (i2c_simulator_add_device(bus, device_addr, "mpu6050") != 0) {
        printf("ERROR: Failed to add MPU-6050 device\n");
        return -1;
    }
    
    // Configure device according to scenario
    mpu6050_simulator_set_pattern(device_addr, scenario->pattern);
    mpu6050_simulator_set_error_mode(device_addr, scenario->error_mode, scenario->error_probability);
    mpu6050_set_power_state(device_addr, scenario->initial_power_state);
    
    if (scenario->enable_fifo) {
        mpu6050_fifo_enable(device_addr, true);
    }
    
    // Reset performance metrics
    reset_performance_metrics();
    
    struct timespec start_time, current_time;
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    
    int total_samples = 0;
    int successful_reads = 0;
    int errors = 0;
    
    // Run the test scenario
    uint32_t sample_interval_us = 1000000 / scenario->sample_rate_hz;
    uint32_t elapsed_ms = 0;
    
    printf("Starting data collection...\n");
    
    while (elapsed_ms < scenario->duration_ms) {
        // Read sensor data
        uint8_t who_am_i;
        if (i2c_simulator_read_byte(bus, device_addr, MPU6050_WHO_AM_I, &who_am_i) == 0) {
            if (who_am_i == MPU6050_WHO_AM_I_VALUE) {
                // Read accelerometer data
                uint8_t accel_data[6];
                if (i2c_simulator_read_burst(bus, device_addr, MPU6050_ACCEL_XOUT_H, accel_data, 6) == 0) {
                    // Read gyroscope data
                    uint8_t gyro_data[6];
                    if (i2c_simulator_read_burst(bus, device_addr, MPU6050_GYRO_XOUT_H, gyro_data, 6) == 0) {
                        // Read temperature
                        uint8_t temp_data[2];
                        if (i2c_simulator_read_burst(bus, device_addr, MPU6050_TEMP_OUT_H, temp_data, 2) == 0) {
                            successful_reads++;
                            
                            // Validate data ranges
                            sensor_data_t data;
                            data.accel_x = (int16_t)((accel_data[0] << 8) | accel_data[1]);
                            data.accel_y = (int16_t)((accel_data[2] << 8) | accel_data[3]);
                            data.accel_z = (int16_t)((accel_data[4] << 8) | accel_data[5]);
                            data.gyro_x = (int16_t)((gyro_data[0] << 8) | gyro_data[1]);
                            data.gyro_y = (int16_t)((gyro_data[2] << 8) | gyro_data[3]);
                            data.gyro_z = (int16_t)((gyro_data[4] << 8) | gyro_data[5]);
                            data.temperature = (int16_t)((temp_data[0] << 8) | temp_data[1]);
                            
                            if (validate_sensor_data_ranges(&data) != 0) {
                                printf("WARNING: Sensor data out of expected ranges\n");
                            }
                        } else errors++;
                    } else errors++;
                } else errors++;
            } else {
                printf("ERROR: Invalid WHO_AM_I response: 0x%02X\n", who_am_i);
                errors++;
            }
        } else {
            errors++;
        }
        
        total_samples++;
        
        // Test FIFO if enabled
        if (scenario->enable_fifo && (total_samples % 10 == 0)) {
            uint16_t fifo_count;
            if (mpu6050_fifo_get_count(device_addr, &fifo_count) == 0) {
                if (fifo_count > 0) {
                    uint8_t fifo_data[64];
                    int bytes_read = mpu6050_fifo_read(device_addr, fifo_data, sizeof(fifo_data));
                    if (bytes_read > 0) {
                        printf("Read %d bytes from FIFO\n", bytes_read);
                    }
                }
            }
        }
        
        // Sleep until next sample
        usleep(sample_interval_us);
        
        clock_gettime(CLOCK_MONOTONIC, &current_time);
        elapsed_ms = (uint32_t)((current_time.tv_sec - start_time.tv_sec) * 1000 + 
                               (current_time.tv_nsec - start_time.tv_nsec) / 1000000);
    }
    
    printf("Test completed: %d total samples, %d successful reads, %d errors\n", 
           total_samples, successful_reads, errors);
    
    // Get final performance metrics
    performance_metrics_t metrics = get_performance_metrics();
    
    // Clean up
    i2c_simulator_remove_device(bus, device_addr);
    
    // Validate results
    int validation_result = validate_scenario_results(scenario, &metrics);
    
    printf("Scenario result: %s\n", validation_result == 0 ? "PASSED" : "FAILED");
    
    return validation_result;
}

int validate_scenario_results(const test_scenario_t* scenario, const performance_metrics_t* metrics) {
    if (!scenario || !metrics) return -1;
    
    printf("\nValidating scenario results...\n");
    
    // Basic validation checks
    bool passed = true;
    
    // Check that some operations occurred
    if (metrics->total_reads == 0 && metrics->total_writes == 0) {
        printf("FAIL: No I2C operations performed\n");
        passed = false;
    }
    
    // Check error rate is within acceptable bounds
    uint32_t total_ops = metrics->total_reads + metrics->total_writes;
    if (total_ops > 0) {
        double actual_error_rate = (double)metrics->errors_injected / total_ops;
        double expected_error_rate = scenario->error_probability;
        
        // Allow some tolerance (±50% of expected rate, minimum 5%)
        double tolerance = fmax(expected_error_rate * 0.5, 0.05);
        
        if (fabs(actual_error_rate - expected_error_rate) > tolerance) {
            printf("FAIL: Error rate %.2f%% outside expected range %.2f%% ± %.2f%%\n",
                   actual_error_rate * 100.0, expected_error_rate * 100.0, tolerance * 100.0);
            passed = false;
        } else {
            printf("PASS: Error rate %.2f%% within expected range\n", actual_error_rate * 100.0);
        }
    }
    
    // Check response times are reasonable
    if (metrics->avg_response_time_us > 10000) { // 10ms seems too slow
        printf("FAIL: Average response time %.2f µs is too high\n", metrics->avg_response_time_us);
        passed = false;
    } else if (metrics->avg_response_time_us > 1000) { // Warning for >1ms
        printf("WARN: Average response time %.2f µs is high\n", metrics->avg_response_time_us);
    } else {
        printf("PASS: Average response time %.2f µs is acceptable\n", metrics->avg_response_time_us);
    }
    
    // Scenario-specific validations
    if (scenario->error_mode == ERROR_NONE && metrics->errors_injected > total_ops * 0.01) {
        printf("FAIL: Too many errors for ERROR_NONE scenario\n");
        passed = false;
    }
    
    if (scenario->error_mode == ERROR_DEVICE_NOT_FOUND && metrics->errors_injected < total_ops * 0.05) {
        printf("FAIL: Too few errors for DEVICE_NOT_FOUND scenario\n");
        passed = false;
    }
    
    return passed ? 0 : -1;
}

// Test function implementations

static int test_normal_operation(void) {
    printf("\n=== Testing Normal Operation ===\n");
    
    const test_scenario_t* scenario = &g_test_scenarios[0]; // normal_operation
    return run_test_scenario(scenario);
}

static int test_fifo_operation(void) {
    printf("\n=== Testing FIFO Operation ===\n");
    
    const test_scenario_t* scenario = &g_test_scenarios[1]; // fifo_operation
    return run_test_scenario(scenario);
}

static int test_error_injection(void) {
    printf("\n=== Testing Error Injection ===\n");
    
    int failures = 0;
    
    // Test different error modes
    for (int i = 6; i <= 10; i++) { // Error scenarios
        if (run_test_scenario(&g_test_scenarios[i]) != 0) {
            failures++;
        }
    }
    
    printf("Error injection tests: %d failures\n", failures);
    return failures > 0 ? -1 : 0;
}

static int test_power_management(void) {
    printf("\n=== Testing Power Management ===\n");
    
    const test_scenario_t* scenario = &g_test_scenarios[5]; // power_management
    return run_test_scenario(scenario);
}

static int test_concurrent_access(void) {
    printf("\n=== Testing Concurrent Access ===\n");
    
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
    
    // Configure device for normal operation
    mpu6050_simulator_set_pattern(device_addr, PATTERN_SINE_WAVE);
    mpu6050_set_power_state(device_addr, POWER_ON);
    
    const int num_threads = 4;
    const int iterations_per_thread = 1000;
    
    pthread_t threads[num_threads];
    thread_params_t params[num_threads];
    volatile int total_errors = 0;
    volatile int total_success = 0;
    
    // Create threads for concurrent access
    for (int i = 0; i < num_threads; i++) {
        params[i].thread_id = i;
        params[i].iterations = iterations_per_thread;
        params[i].bus = bus;
        params[i].device_addr = device_addr;
        params[i].error_count = &total_errors;
        params[i].success_count = &total_success;
        
        if (i % 2 == 0) {
            pthread_create(&threads[i], NULL, concurrent_read_thread, &params[i]);
        } else {
            pthread_create(&threads[i], NULL, concurrent_write_thread, &params[i]);
        }
    }
    
    // Wait for all threads to complete
    for (int i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
    }
    
    printf("Concurrent access test: %d success, %d errors\n", 
           (int)total_success, (int)total_errors);
    
    i2c_simulator_remove_device(bus, device_addr);
    
    // Success if error rate is below 5%
    double error_rate = (double)total_errors / (total_success + total_errors);
    return (error_rate < 0.05) ? 0 : -1;
}

static int test_performance_limits(void) {
    printf("\n=== Testing Performance Limits ===\n");
    
    const test_scenario_t* scenario = &g_test_scenarios[13]; // stress_test
    return run_test_scenario(scenario);
}

static int validate_sensor_data_ranges(const sensor_data_t* data) {
    if (!data) return -1;
    
    // Check accelerometer ranges (±2g = ±32768 LSB)
    if (abs(data->accel_x) > 32768 || abs(data->accel_y) > 32768 || abs(data->accel_z) > 32768) {
        printf("WARNING: Accelerometer data out of range\n");
        return -1;
    }
    
    // Check gyroscope ranges (±250°/s = ±32768 LSB)
    if (abs(data->gyro_x) > 32768 || abs(data->gyro_y) > 32768 || abs(data->gyro_z) > 32768) {
        printf("WARNING: Gyroscope data out of range\n");
        return -1;
    }
    
    // Check temperature range (approximately -40°C to +85°C)
    // Temperature = (TEMP_OUT Register Value as a signed value)/340 + 36.53
    double temp_celsius = data->temperature / 340.0 - 36.53;
    if (temp_celsius < -50.0 || temp_celsius > 100.0) {
        printf("WARNING: Temperature data out of reasonable range: %.1f°C\n", temp_celsius);
        return -1;
    }
    
    return 0;
}

static int run_basic_i2c_tests(void) {
    printf("\n=== Running Basic I2C Tests ===\n");
    
    if (i2c_simulator_init() != 0) {
        printf("ERROR: Failed to initialize simulator\n");
        return -1;
    }
    
    const uint8_t device_addr = MPU6050_ADDR;
    const int bus = 0;
    
    // Test 1: Add device
    if (i2c_simulator_add_device(bus, device_addr, "mpu6050") != 0) {
        printf("ERROR: Failed to add device\n");
        return -1;
    }
    printf("PASS: Device added successfully\n");
    
    // Test 2: Read WHO_AM_I register
    uint8_t who_am_i;
    if (i2c_simulator_read_byte(bus, device_addr, MPU6050_WHO_AM_I, &who_am_i) != 0) {
        printf("ERROR: Failed to read WHO_AM_I register\n");
        return -1;
    }
    
    if (who_am_i != MPU6050_WHO_AM_I_VALUE) {
        printf("ERROR: Invalid WHO_AM_I value: 0x%02X (expected 0x%02X)\n", 
               who_am_i, MPU6050_WHO_AM_I_VALUE);
        return -1;
    }
    printf("PASS: WHO_AM_I register correct (0x%02X)\n", who_am_i);
    
    // Test 3: Write and read back power management register
    uint8_t pwr_mgmt_original, pwr_mgmt_readback;
    if (i2c_simulator_read_byte(bus, device_addr, MPU6050_PWR_MGMT_1, &pwr_mgmt_original) != 0) {
        printf("ERROR: Failed to read PWR_MGMT_1 register\n");
        return -1;
    }
    
    const uint8_t test_value = 0x00; // Wake up device
    if (i2c_simulator_write_byte(bus, device_addr, MPU6050_PWR_MGMT_1, test_value) != 0) {
        printf("ERROR: Failed to write PWR_MGMT_1 register\n");
        return -1;
    }
    
    if (i2c_simulator_read_byte(bus, device_addr, MPU6050_PWR_MGMT_1, &pwr_mgmt_readback) != 0) {
        printf("ERROR: Failed to read back PWR_MGMT_1 register\n");
        return -1;
    }
    
    if (pwr_mgmt_readback != test_value) {
        printf("ERROR: PWR_MGMT_1 readback failed: wrote 0x%02X, read 0x%02X\n", 
               test_value, pwr_mgmt_readback);
        return -1;
    }
    printf("PASS: PWR_MGMT_1 register write/read successful\n");
    
    // Test 4: Burst read sensor data
    uint8_t sensor_data[14];
    if (i2c_simulator_read_burst(bus, device_addr, MPU6050_ACCEL_XOUT_H, sensor_data, 14) != 0) {
        printf("ERROR: Failed to burst read sensor data\n");
        return -1;
    }
    printf("PASS: Burst read sensor data successful\n");
    
    // Test 5: Remove device
    if (i2c_simulator_remove_device(bus, device_addr) != 0) {
        printf("ERROR: Failed to remove device\n");
        return -1;
    }
    printf("PASS: Device removed successfully\n");
    
    printf("All basic I2C tests passed!\n");
    return 0;
}

static void* concurrent_read_thread(void* arg) {
    thread_params_t* params = (thread_params_t*)arg;
    
    for (int i = 0; i < params->iterations; i++) {
        uint8_t data;
        if (i2c_simulator_read_byte(params->bus, params->device_addr, MPU6050_WHO_AM_I, &data) == 0) {
            __sync_fetch_and_add((int*)params->success_count, 1);
        } else {
            __sync_fetch_and_add((int*)params->error_count, 1);
        }
        
        // Small delay to allow other threads to run
        usleep(100);
    }
    
    return NULL;
}

static void* concurrent_write_thread(void* arg) {
    thread_params_t* params = (thread_params_t*)arg;
    
    for (int i = 0; i < params->iterations; i++) {
        // Write to a safe register (ACCEL_CONFIG)
        uint8_t config_value = (i % 4) << 3; // Cycle through scale ranges
        if (i2c_simulator_write_byte(params->bus, params->device_addr, MPU6050_ACCEL_CONFIG, config_value) == 0) {
            __sync_fetch_and_add((int*)params->success_count, 1);
        } else {
            __sync_fetch_and_add((int*)params->error_count, 1);
        }
        
        // Small delay to allow other threads to run
        usleep(150);
    }
    
    return NULL;
}

// Main test runner function
int run_all_test_scenarios(void) {
    printf("\n======================================\n");
    printf("    MPU-6050 Simulator Test Suite\n");
    printf("======================================\n");
    
    int total_tests = 0;
    int passed_tests = 0;
    
    // Run basic I2C tests first
    printf("\n--- Phase 1: Basic I2C Tests ---\n");
    if (run_basic_i2c_tests() == 0) {
        passed_tests++;
    }
    total_tests++;
    
    // Run individual test categories
    printf("\n--- Phase 2: Functional Tests ---\n");
    
    struct {
        const char* name;
        int (*test_func)(void);
    } test_categories[] = {
        {"Normal Operation", test_normal_operation},
        {"FIFO Operation", test_fifo_operation},
        {"Error Injection", test_error_injection},
        {"Power Management", test_power_management},
        {"Concurrent Access", test_concurrent_access},
        {"Performance Limits", test_performance_limits}
    };
    
    for (size_t i = 0; i < sizeof(test_categories) / sizeof(test_categories[0]); i++) {
        printf("\nRunning %s tests...\n", test_categories[i].name);
        if (test_categories[i].test_func() == 0) {
            passed_tests++;
            printf("✓ %s tests PASSED\n", test_categories[i].name);
        } else {
            printf("✗ %s tests FAILED\n", test_categories[i].name);
        }
        total_tests++;
    }
    
    // Run all predefined scenarios
    printf("\n--- Phase 3: Scenario Tests ---\n");
    for (int i = 0; i < g_scenario_count; i++) {
        if (run_test_scenario(&g_test_scenarios[i]) == 0) {
            passed_tests++;
        }
        total_tests++;
    }
    
    // Final performance report
    print_performance_report();
    
    printf("\n======================================\n");
    printf("         Test Summary\n");
    printf("======================================\n");
    printf("Total tests: %d\n", total_tests);
    printf("Passed: %d\n", passed_tests);
    printf("Failed: %d\n", total_tests - passed_tests);
    printf("Success rate: %.1f%%\n", (double)passed_tests / total_tests * 100.0);
    
    if (passed_tests == total_tests) {
        printf("🎉 ALL TESTS PASSED! 🎉\n");
        return 0;
    } else {
        printf("❌ SOME TESTS FAILED ❌\n");
        return -1;
    }
}