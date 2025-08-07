#ifndef SIMULATOR_H
#define SIMULATOR_H

#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>
#include <time.h>

// MPU-6050 register addresses
#define MPU6050_ADDR                0x68
#define MPU6050_WHO_AM_I           0x75
#define MPU6050_PWR_MGMT_1         0x6B
#define MPU6050_PWR_MGMT_2         0x6C
#define MPU6050_ACCEL_CONFIG       0x1C
#define MPU6050_GYRO_CONFIG        0x1B
#define MPU6050_ACCEL_XOUT_H       0x3B
#define MPU6050_ACCEL_XOUT_L       0x3C
#define MPU6050_ACCEL_YOUT_H       0x3D
#define MPU6050_ACCEL_YOUT_L       0x3E
#define MPU6050_ACCEL_ZOUT_H       0x3F
#define MPU6050_ACCEL_ZOUT_L       0x40
#define MPU6050_TEMP_OUT_H         0x41
#define MPU6050_TEMP_OUT_L         0x42
#define MPU6050_GYRO_XOUT_H        0x43
#define MPU6050_GYRO_XOUT_L        0x44
#define MPU6050_GYRO_YOUT_H        0x45
#define MPU6050_GYRO_YOUT_L        0x46
#define MPU6050_GYRO_ZOUT_H        0x47
#define MPU6050_GYRO_ZOUT_L        0x48
#define MPU6050_FIFO_COUNTH        0x72
#define MPU6050_FIFO_COUNTL        0x73
#define MPU6050_FIFO_R_W           0x74
#define MPU6050_USER_CTRL          0x6A
#define MPU6050_FIFO_EN            0x23
#define MPU6050_INT_PIN_CFG        0x37
#define MPU6050_INT_ENABLE         0x38
#define MPU6050_INT_STATUS         0x3A

// MPU-6050 specific values
#define MPU6050_WHO_AM_I_VALUE     0x68

// I2C simulator constants
#define MAX_I2C_DEVICES            128
#define I2C_BUS_COUNT              2
#define FIFO_BUFFER_SIZE           1024

// Error injection types
typedef enum {
    ERROR_NONE = 0,
    ERROR_DEVICE_NOT_FOUND,
    ERROR_TIMEOUT,
    ERROR_BUS_ERROR,
    ERROR_CORRUPT_DATA,
    ERROR_INTERMITTENT,
    ERROR_COUNT
} error_type_t;

// Sensor data patterns
typedef enum {
    PATTERN_STATIC = 0,
    PATTERN_SINE_WAVE,
    PATTERN_NOISE,
    PATTERN_GRAVITY_ONLY,
    PATTERN_ROTATION,
    PATTERN_VIBRATION,
    PATTERN_COUNT
} data_pattern_t;

// Power management states
typedef enum {
    POWER_OFF = 0,
    POWER_SLEEP,
    POWER_CYCLE,
    POWER_ON,
    POWER_COUNT
} power_state_t;

// Virtual sensor data
typedef struct {
    int16_t accel_x, accel_y, accel_z;
    int16_t gyro_x, gyro_y, gyro_z;
    int16_t temperature;
    uint32_t timestamp;
} sensor_data_t;

// FIFO buffer
typedef struct {
    uint8_t buffer[FIFO_BUFFER_SIZE];
    uint16_t head;
    uint16_t tail;
    uint16_t count;
    bool enabled;
    bool overflow;
    pthread_mutex_t mutex;
} fifo_buffer_t;

// MPU-6050 device state
typedef struct {
    uint8_t registers[256];        // Register map
    sensor_data_t current_data;    // Current sensor readings
    fifo_buffer_t fifo;           // FIFO buffer
    power_state_t power_state;    // Power management state
    data_pattern_t pattern;       // Data generation pattern
    error_type_t error_mode;      // Current error mode
    double error_probability;     // Probability of error occurrence
    bool initialized;             // Device initialization state
    bool self_test_mode;          // Self-test mode flag
    uint32_t sample_count;        // Total samples generated
    struct timespec start_time;   // Simulation start time
    pthread_mutex_t mutex;        // Thread safety
} mpu6050_state_t;

// I2C device interface
typedef struct {
    uint8_t address;
    bool present;
    void* device_data;
    int (*read_register)(void* device, uint8_t reg, uint8_t* data);
    int (*write_register)(void* device, uint8_t reg, uint8_t data);
    int (*read_burst)(void* device, uint8_t reg, uint8_t* data, size_t len);
} i2c_device_t;

// I2C bus simulator
typedef struct {
    i2c_device_t devices[MAX_I2C_DEVICES];
    int device_count;
    bool bus_error;
    double noise_level;           // Bus noise simulation (0.0-1.0)
    uint32_t transaction_count;   // Total transactions
    pthread_mutex_t bus_mutex;    // Bus access synchronization
} i2c_bus_t;

// Test scenario configuration
typedef struct {
    const char* name;
    const char* description;
    data_pattern_t pattern;
    error_type_t error_mode;
    double error_probability;
    uint32_t duration_ms;
    uint32_t sample_rate_hz;
    bool enable_fifo;
    bool enable_interrupts;
    power_state_t initial_power_state;
} test_scenario_t;

// Performance metrics
typedef struct {
    uint32_t total_reads;
    uint32_t total_writes;
    uint32_t errors_injected;
    uint32_t timeouts;
    double avg_response_time_us;
    uint32_t max_response_time_us;
    uint32_t min_response_time_us;
} performance_metrics_t;

// Global simulator state
typedef struct {
    i2c_bus_t buses[I2C_BUS_COUNT];
    mpu6050_state_t mpu6050_devices[MAX_I2C_DEVICES];
    performance_metrics_t metrics;
    bool running;
    pthread_t background_thread;
    struct timespec simulation_start;
} i2c_simulator_t;

// Core simulator functions
int i2c_simulator_init(void);
void i2c_simulator_cleanup(void);
int i2c_simulator_add_device(int bus, uint8_t address, const char* device_type);
int i2c_simulator_remove_device(int bus, uint8_t address);

// I2C bus operations
int i2c_simulator_read_byte(int bus, uint8_t device_addr, uint8_t reg_addr, uint8_t* data);
int i2c_simulator_write_byte(int bus, uint8_t device_addr, uint8_t reg_addr, uint8_t data);
int i2c_simulator_read_burst(int bus, uint8_t device_addr, uint8_t reg_addr, uint8_t* data, size_t len);
int i2c_simulator_write_burst(int bus, uint8_t device_addr, uint8_t reg_addr, const uint8_t* data, size_t len);

// MPU-6050 specific functions
int mpu6050_simulator_create(uint8_t address);
int mpu6050_simulator_destroy(uint8_t address);
int mpu6050_simulator_reset(uint8_t address);
int mpu6050_simulator_set_pattern(uint8_t address, data_pattern_t pattern);
int mpu6050_simulator_set_error_mode(uint8_t address, error_type_t error, double probability);
int mpu6050_simulator_get_data(uint8_t address, sensor_data_t* data);
int mpu6050_simulator_inject_error(uint8_t address);

// FIFO operations
int mpu6050_fifo_enable(uint8_t address, bool enable);
int mpu6050_fifo_reset(uint8_t address);
int mpu6050_fifo_get_count(uint8_t address, uint16_t* count);
int mpu6050_fifo_read(uint8_t address, uint8_t* data, size_t len);

// Power management
int mpu6050_set_power_state(uint8_t address, power_state_t state);
power_state_t mpu6050_get_power_state(uint8_t address);

// Test scenario support
int load_test_scenarios(const char* config_file);
int run_test_scenario(const test_scenario_t* scenario);
int validate_scenario_results(const test_scenario_t* scenario, const performance_metrics_t* metrics);

// Performance monitoring
void reset_performance_metrics(void);
performance_metrics_t get_performance_metrics(void);
void print_performance_report(void);

// Configuration
int set_bus_noise_level(int bus, double noise_level);
int set_global_latency(uint32_t latency_us);
int enable_debug_logging(bool enable);

// Utility functions
double get_simulation_time_ms(void);
uint32_t generate_realistic_timestamp(void);
void simulate_processing_delay(void);
bool should_inject_error(double probability);

// Device function declarations
int mpu6050_read_register(void* device, uint8_t reg, uint8_t* data);
int mpu6050_write_register(void* device, uint8_t reg, uint8_t data);
int mpu6050_read_burst(void* device, uint8_t reg, uint8_t* data, size_t len);

// Data generation helpers
int16_t generate_accel_data(data_pattern_t pattern, int axis, uint32_t sample_num);
int16_t generate_gyro_data(data_pattern_t pattern, int axis, uint32_t sample_num);
int16_t generate_temp_data(data_pattern_t pattern, uint32_t sample_num);

// Thread safety
int acquire_device_lock(uint8_t address);
int release_device_lock(uint8_t address);
int acquire_bus_lock(int bus);
int release_bus_lock(int bus);

// Error injection
const char* error_type_to_string(error_type_t error);
const char* pattern_type_to_string(data_pattern_t pattern);
const char* power_state_to_string(power_state_t state);

#endif // SIMULATOR_H