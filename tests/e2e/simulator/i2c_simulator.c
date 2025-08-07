#define _GNU_SOURCE
#include "simulator.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <math.h>
#include <sys/time.h>

// Global simulator instance
static i2c_simulator_t g_simulator = {0};
static bool g_simulator_initialized = false;
static uint32_t g_global_latency_us = 100; // Default 100us latency
static bool g_debug_logging = false;

// Global access functions
i2c_simulator_t* get_global_simulator(void) {
    return &g_simulator;
}

bool* get_debug_logging_flag(void) {
    return &g_debug_logging;
}

// Private function declarations
static void* background_simulation_thread(void* arg);
static void update_performance_metrics(struct timespec* start, struct timespec* end, bool error);
static i2c_device_t* find_device(int bus, uint8_t address);
static void simulate_bus_conditions(int bus);

int i2c_simulator_init(void) {
    if (g_simulator_initialized) {
        return 0; // Already initialized
    }

    memset(&g_simulator, 0, sizeof(g_simulator));
    
    // Initialize buses
    for (int i = 0; i < I2C_BUS_COUNT; i++) {
        pthread_mutex_init(&g_simulator.buses[i].bus_mutex, NULL);
        g_simulator.buses[i].device_count = 0;
        g_simulator.buses[i].bus_error = false;
        g_simulator.buses[i].noise_level = 0.01; // 1% noise by default
    }

    // Initialize MPU-6050 device states
    for (int i = 0; i < MAX_I2C_DEVICES; i++) {
        pthread_mutex_init(&g_simulator.mpu6050_devices[i].mutex, NULL);
        pthread_mutex_init(&g_simulator.mpu6050_devices[i].fifo.mutex, NULL);
        g_simulator.mpu6050_devices[i].initialized = false;
    }

    // Record simulation start time
    clock_gettime(CLOCK_MONOTONIC, &g_simulator.simulation_start);

    // Start background simulation thread
    g_simulator.running = true;
    if (pthread_create(&g_simulator.background_thread, NULL, background_simulation_thread, NULL) != 0) {
        fprintf(stderr, "Failed to create background simulation thread\n");
        return -1;
    }

    g_simulator_initialized = true;
    
    if (g_debug_logging) {
        printf("[I2C_SIM] Simulator initialized successfully\n");
    }

    return 0;
}

void i2c_simulator_cleanup(void) {
    if (!g_simulator_initialized) {
        return;
    }

    // Stop background thread
    g_simulator.running = false;
    pthread_join(g_simulator.background_thread, NULL);

    // Cleanup mutexes
    for (int i = 0; i < I2C_BUS_COUNT; i++) {
        pthread_mutex_destroy(&g_simulator.buses[i].bus_mutex);
    }

    for (int i = 0; i < MAX_I2C_DEVICES; i++) {
        pthread_mutex_destroy(&g_simulator.mpu6050_devices[i].mutex);
        pthread_mutex_destroy(&g_simulator.mpu6050_devices[i].fifo.mutex);
    }

    g_simulator_initialized = false;

    if (g_debug_logging) {
        printf("[I2C_SIM] Simulator cleanup completed\n");
    }
}

int i2c_simulator_add_device(int bus, uint8_t address, const char* device_type) {
    if (!g_simulator_initialized || bus < 0 || bus >= I2C_BUS_COUNT) {
        return -EINVAL;
    }

    acquire_bus_lock(bus);

    // Check if device already exists
    if (find_device(bus, address) != NULL) {
        release_bus_lock(bus);
        return -EEXIST;
    }

    // Find free slot
    i2c_bus_t* i2c_bus = &g_simulator.buses[bus];
    if (i2c_bus->device_count >= MAX_I2C_DEVICES) {
        release_bus_lock(bus);
        return -ENOMEM;
    }

    // Add device
    int slot = i2c_bus->device_count++;
    i2c_device_t* device = &i2c_bus->devices[slot];
    device->address = address;
    device->present = true;

    // Initialize device based on type
    if (strcmp(device_type, "mpu6050") == 0) {
        int result = mpu6050_simulator_create(address);
        if (result < 0) {
            i2c_bus->device_count--;
            release_bus_lock(bus);
            return result;
        }
        device->device_data = &g_simulator.mpu6050_devices[address % MAX_I2C_DEVICES];
        device->read_register = mpu6050_read_register;
        device->write_register = mpu6050_write_register;
        device->read_burst = mpu6050_read_burst;
    } else {
        i2c_bus->device_count--;
        release_bus_lock(bus);
        return -ENOTSUP;
    }

    release_bus_lock(bus);

    if (g_debug_logging) {
        printf("[I2C_SIM] Added %s device at address 0x%02X on bus %d\n", 
               device_type, address, bus);
    }

    return 0;
}

int i2c_simulator_remove_device(int bus, uint8_t address) {
    if (!g_simulator_initialized || bus < 0 || bus >= I2C_BUS_COUNT) {
        return -EINVAL;
    }

    acquire_bus_lock(bus);

    i2c_device_t* device = find_device(bus, address);
    if (device == NULL) {
        release_bus_lock(bus);
        return -ENODEV;
    }

    // Mark device as not present
    device->present = false;
    device->device_data = NULL;

    // Cleanup MPU-6050 state if applicable
    mpu6050_simulator_destroy(address);

    release_bus_lock(bus);

    if (g_debug_logging) {
        printf("[I2C_SIM] Removed device at address 0x%02X from bus %d\n", address, bus);
    }

    return 0;
}

int i2c_simulator_read_byte(int bus, uint8_t device_addr, uint8_t reg_addr, uint8_t* data) {
    if (!g_simulator_initialized || data == NULL) {
        return -EINVAL;
    }

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    simulate_processing_delay();
    simulate_bus_conditions(bus);

    acquire_bus_lock(bus);

    i2c_device_t* device = find_device(bus, device_addr);
    if (device == NULL || !device->present) {
        release_bus_lock(bus);
        clock_gettime(CLOCK_MONOTONIC, &end);
        update_performance_metrics(&start, &end, true);
        g_simulator.metrics.errors_injected++;
        return -ENODEV;
    }

    int result = -EIO;
    if (device->read_register && device->device_data) {
        result = device->read_register(device->device_data, reg_addr, data);
    }

    g_simulator.metrics.total_reads++;
    release_bus_lock(bus);

    clock_gettime(CLOCK_MONOTONIC, &end);
    update_performance_metrics(&start, &end, result < 0);

    if (g_debug_logging && result >= 0) {
        printf("[I2C_SIM] Read: bus=%d, addr=0x%02X, reg=0x%02X, data=0x%02X\n", 
               bus, device_addr, reg_addr, *data);
    }

    return result;
}

int i2c_simulator_write_byte(int bus, uint8_t device_addr, uint8_t reg_addr, uint8_t data) {
    if (!g_simulator_initialized) {
        return -EINVAL;
    }

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    simulate_processing_delay();
    simulate_bus_conditions(bus);

    acquire_bus_lock(bus);

    i2c_device_t* device = find_device(bus, device_addr);
    if (device == NULL || !device->present) {
        release_bus_lock(bus);
        clock_gettime(CLOCK_MONOTONIC, &end);
        update_performance_metrics(&start, &end, true);
        g_simulator.metrics.errors_injected++;
        return -ENODEV;
    }

    int result = -EIO;
    if (device->write_register && device->device_data) {
        result = device->write_register(device->device_data, reg_addr, data);
    }

    g_simulator.metrics.total_writes++;
    release_bus_lock(bus);

    clock_gettime(CLOCK_MONOTONIC, &end);
    update_performance_metrics(&start, &end, result < 0);

    if (g_debug_logging && result >= 0) {
        printf("[I2C_SIM] Write: bus=%d, addr=0x%02X, reg=0x%02X, data=0x%02X\n", 
               bus, device_addr, reg_addr, data);
    }

    return result;
}

int i2c_simulator_read_burst(int bus, uint8_t device_addr, uint8_t reg_addr, uint8_t* data, size_t len) {
    if (!g_simulator_initialized || data == NULL || len == 0) {
        return -EINVAL;
    }

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    simulate_processing_delay();
    simulate_bus_conditions(bus);

    acquire_bus_lock(bus);

    i2c_device_t* device = find_device(bus, device_addr);
    if (device == NULL || !device->present) {
        release_bus_lock(bus);
        clock_gettime(CLOCK_MONOTONIC, &end);
        update_performance_metrics(&start, &end, true);
        g_simulator.metrics.errors_injected++;
        return -ENODEV;
    }

    int result = -EIO;
    if (device->read_burst && device->device_data) {
        result = device->read_burst(device->device_data, reg_addr, data, len);
    } else if (device->read_register && device->device_data) {
        // Fallback to individual reads
        result = 0;
        for (size_t i = 0; i < len; i++) {
            int byte_result = device->read_register(device->device_data, reg_addr + i, &data[i]);
            if (byte_result < 0) {
                result = byte_result;
                break;
            }
        }
    }

    g_simulator.metrics.total_reads += len;
    release_bus_lock(bus);

    clock_gettime(CLOCK_MONOTONIC, &end);
    update_performance_metrics(&start, &end, result < 0);

    if (g_debug_logging && result >= 0) {
        printf("[I2C_SIM] Burst read: bus=%d, addr=0x%02X, reg=0x%02X, len=%zu\n", 
               bus, device_addr, reg_addr, len);
    }

    return result;
}

int i2c_simulator_write_burst(int bus, uint8_t device_addr, uint8_t reg_addr, const uint8_t* data, size_t len) {
    if (!g_simulator_initialized || data == NULL || len == 0) {
        return -EINVAL;
    }

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    simulate_processing_delay();
    simulate_bus_conditions(bus);

    acquire_bus_lock(bus);

    i2c_device_t* device = find_device(bus, device_addr);
    if (device == NULL || !device->present) {
        release_bus_lock(bus);
        clock_gettime(CLOCK_MONOTONIC, &end);
        update_performance_metrics(&start, &end, true);
        g_simulator.metrics.errors_injected++;
        return -ENODEV;
    }

    int result = -EIO;
    if (device->write_register && device->device_data) {
        // Use individual writes (most devices don't support burst write)
        result = 0;
        for (size_t i = 0; i < len; i++) {
            int byte_result = device->write_register(device->device_data, reg_addr + i, data[i]);
            if (byte_result < 0) {
                result = byte_result;
                break;
            }
        }
    }

    g_simulator.metrics.total_writes += len;
    release_bus_lock(bus);

    clock_gettime(CLOCK_MONOTONIC, &end);
    update_performance_metrics(&start, &end, result < 0);

    if (g_debug_logging && result >= 0) {
        printf("[I2C_SIM] Burst write: bus=%d, addr=0x%02X, reg=0x%02X, len=%zu\n", 
               bus, device_addr, reg_addr, len);
    }

    return result;
}

void reset_performance_metrics(void) {
    memset(&g_simulator.metrics, 0, sizeof(performance_metrics_t));
    g_simulator.metrics.min_response_time_us = UINT32_MAX;
    clock_gettime(CLOCK_MONOTONIC, &g_simulator.simulation_start);
}

performance_metrics_t get_performance_metrics(void) {
    return g_simulator.metrics;
}

void print_performance_report(void) {
    performance_metrics_t* m = &g_simulator.metrics;
    double sim_time = get_simulation_time_ms();
    
    printf("\n=== I2C Simulator Performance Report ===\n");
    printf("Simulation time: %.2f ms\n", sim_time);
    printf("Total reads: %u\n", m->total_reads);
    printf("Total writes: %u\n", m->total_writes);
    printf("Errors injected: %u\n", m->errors_injected);
    printf("Timeouts: %u\n", m->timeouts);
    printf("Average response time: %.2f µs\n", m->avg_response_time_us);
    printf("Min response time: %u µs\n", m->min_response_time_us);
    printf("Max response time: %u µs\n", m->max_response_time_us);
    
    if (m->total_reads + m->total_writes > 0) {
        double error_rate = (double)m->errors_injected / (m->total_reads + m->total_writes) * 100.0;
        double throughput = (m->total_reads + m->total_writes) / (sim_time / 1000.0);
        printf("Error rate: %.2f%%\n", error_rate);
        printf("Throughput: %.2f ops/sec\n", throughput);
    }
    printf("=====================================\n\n");
}

int set_bus_noise_level(int bus, double noise_level) {
    if (bus < 0 || bus >= I2C_BUS_COUNT || noise_level < 0.0 || noise_level > 1.0) {
        return -EINVAL;
    }
    
    g_simulator.buses[bus].noise_level = noise_level;
    return 0;
}

int set_global_latency(uint32_t latency_us) {
    g_global_latency_us = latency_us;
    return 0;
}

int enable_debug_logging(bool enable) {
    g_debug_logging = enable;
    return 0;
}

double get_simulation_time_ms(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    
    double elapsed_sec = (now.tv_sec - g_simulator.simulation_start.tv_sec) + 
                        (now.tv_nsec - g_simulator.simulation_start.tv_nsec) / 1e9;
    return elapsed_sec * 1000.0;
}

uint32_t generate_realistic_timestamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

void simulate_processing_delay(void) {
    if (g_global_latency_us > 0) {
        usleep(g_global_latency_us);
    }
}

bool should_inject_error(double probability) {
    if (probability <= 0.0) return false;
    if (probability >= 1.0) return true;
    
    return (rand() / (double)RAND_MAX) < probability;
}

int acquire_device_lock(uint8_t address) {
    int index = address % MAX_I2C_DEVICES;
    return pthread_mutex_lock(&g_simulator.mpu6050_devices[index].mutex);
}

int release_device_lock(uint8_t address) {
    int index = address % MAX_I2C_DEVICES;
    return pthread_mutex_unlock(&g_simulator.mpu6050_devices[index].mutex);
}

int acquire_bus_lock(int bus) {
    if (bus < 0 || bus >= I2C_BUS_COUNT) return -EINVAL;
    return pthread_mutex_lock(&g_simulator.buses[bus].bus_mutex);
}

int release_bus_lock(int bus) {
    if (bus < 0 || bus >= I2C_BUS_COUNT) return -EINVAL;
    return pthread_mutex_unlock(&g_simulator.buses[bus].bus_mutex);
}

const char* error_type_to_string(error_type_t error) {
    static const char* error_names[] = {
        "NONE", "DEVICE_NOT_FOUND", "TIMEOUT", "BUS_ERROR", 
        "CORRUPT_DATA", "INTERMITTENT"
    };
    if (error < ERROR_COUNT) {
        return error_names[error];
    }
    return "UNKNOWN";
}

const char* pattern_type_to_string(data_pattern_t pattern) {
    static const char* pattern_names[] = {
        "STATIC", "SINE_WAVE", "NOISE", "GRAVITY_ONLY", 
        "ROTATION", "VIBRATION"
    };
    if (pattern < PATTERN_COUNT) {
        return pattern_names[pattern];
    }
    return "UNKNOWN";
}

const char* power_state_to_string(power_state_t state) {
    static const char* state_names[] = {
        "OFF", "SLEEP", "CYCLE", "ON"
    };
    if (state < POWER_COUNT) {
        return state_names[state];
    }
    return "UNKNOWN";
}

// Private helper functions

static void* background_simulation_thread(void* arg) {
    (void)arg; // Unused parameter
    
    while (g_simulator.running) {
        // Update all active MPU-6050 devices
        for (int i = 0; i < MAX_I2C_DEVICES; i++) {
            if (g_simulator.mpu6050_devices[i].initialized) {
                // This will be implemented in mpu6050_virtual.c
                // mpu6050_update_background(&g_simulator.mpu6050_devices[i]);
            }
        }
        
        // Sleep for 10ms (100Hz update rate)
        usleep(10000);
    }
    
    return NULL;
}

static void update_performance_metrics(struct timespec* start, struct timespec* end, bool error) {
    uint32_t elapsed_us = (uint32_t)((end->tv_sec - start->tv_sec) * 1000000 + 
                                    (end->tv_nsec - start->tv_nsec) / 1000);
    
    // Update average response time
    uint32_t total_ops = g_simulator.metrics.total_reads + g_simulator.metrics.total_writes;
    if (total_ops == 0) {
        g_simulator.metrics.avg_response_time_us = elapsed_us;
    } else {
        g_simulator.metrics.avg_response_time_us = 
            (g_simulator.metrics.avg_response_time_us * total_ops + elapsed_us) / (total_ops + 1);
    }
    
    // Update min/max
    if (elapsed_us < g_simulator.metrics.min_response_time_us) {
        g_simulator.metrics.min_response_time_us = elapsed_us;
    }
    if (elapsed_us > g_simulator.metrics.max_response_time_us) {
        g_simulator.metrics.max_response_time_us = elapsed_us;
    }
    
    if (error) {
        g_simulator.metrics.errors_injected++;
    }
}

static i2c_device_t* find_device(int bus, uint8_t address) {
    if (bus < 0 || bus >= I2C_BUS_COUNT) return NULL;
    
    i2c_bus_t* i2c_bus = &g_simulator.buses[bus];
    for (int i = 0; i < i2c_bus->device_count; i++) {
        if (i2c_bus->devices[i].address == address && i2c_bus->devices[i].present) {
            return &i2c_bus->devices[i];
        }
    }
    return NULL;
}

static void simulate_bus_conditions(int bus) {
    if (bus < 0 || bus >= I2C_BUS_COUNT) return;
    
    i2c_bus_t* i2c_bus = &g_simulator.buses[bus];
    
    // Simulate bus noise by occasionally injecting small delays
    if (i2c_bus->noise_level > 0.0) {
        if (should_inject_error(i2c_bus->noise_level)) {
            usleep(rand() % 50); // 0-50µs random noise delay
        }
    }
    
    i2c_bus->transaction_count++;
}