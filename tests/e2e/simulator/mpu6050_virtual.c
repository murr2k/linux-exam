#define _GNU_SOURCE
#include "simulator.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <math.h>
#include <errno.h>

// MPU-6050 specific constants
#define MPU6050_WHO_AM_I_VALUE         0x68
#define MPU6050_DEFAULT_TEMP           21.0  // 21°C in Celsius
#define TEMP_SENSITIVITY               340.0 // LSB/°C
#define TEMP_OFFSET                    36.53 // °C offset
#define ACCEL_SCALE_2G                 16384 // LSB/g
#define GYRO_SCALE_250DPS              131.0 // LSB/°/s

// Forward reference to global simulator - will be resolved at link time
i2c_simulator_t* get_global_simulator(void);
bool* get_debug_logging_flag(void);

// Forward declarations
int mpu6050_read_register(void* device, uint8_t reg, uint8_t* data);
int mpu6050_write_register(void* device, uint8_t reg, uint8_t data);
int mpu6050_read_burst(void* device, uint8_t reg, uint8_t* data, size_t len);
static void update_sensor_data(mpu6050_state_t* state);
static void update_fifo_buffer(mpu6050_state_t* state);
static bool is_register_readable(uint8_t reg);
static bool is_register_writable(uint8_t reg);
static void handle_power_management(mpu6050_state_t* state, uint8_t reg, uint8_t value);
static void handle_fifo_configuration(mpu6050_state_t* state, uint8_t reg, uint8_t value);

int mpu6050_simulator_create(uint8_t address) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    acquire_device_lock(address);
    
    // Initialize register map with default values
    memset(state->registers, 0, sizeof(state->registers));
    
    // Set default register values according to datasheet
    state->registers[MPU6050_WHO_AM_I] = MPU6050_WHO_AM_I_VALUE;
    state->registers[MPU6050_PWR_MGMT_1] = 0x40; // Sleep mode, internal 8MHz oscillator
    state->registers[MPU6050_PWR_MGMT_2] = 0x00; // All sensors enabled
    state->registers[MPU6050_ACCEL_CONFIG] = 0x00; // ±2g range
    state->registers[MPU6050_GYRO_CONFIG] = 0x00; // ±250°/s range
    
    // Initialize sensor data
    memset(&state->current_data, 0, sizeof(sensor_data_t));
    state->current_data.accel_z = ACCEL_SCALE_2G; // 1g downward (gravity)
    state->current_data.temperature = (int16_t)((MPU6050_DEFAULT_TEMP + TEMP_OFFSET) * TEMP_SENSITIVITY);
    
    // Initialize FIFO
    memset(&state->fifo, 0, sizeof(fifo_buffer_t));
    state->fifo.enabled = false;
    
    // Set default behavior
    state->power_state = POWER_SLEEP;
    state->pattern = PATTERN_GRAVITY_ONLY;
    state->error_mode = ERROR_NONE;
    state->error_probability = 0.0;
    state->initialized = true;
    state->self_test_mode = false;
    state->sample_count = 0;
    
    clock_gettime(CLOCK_MONOTONIC, &state->start_time);
    
    release_device_lock(address);
    
    if (*get_debug_logging_flag()) {
        printf("[MPU6050_SIM] Created virtual MPU-6050 at address 0x%02X\n", address);
    }
    
    return 0;
}

int mpu6050_simulator_destroy(uint8_t address) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    acquire_device_lock(address);
    state->initialized = false;
    release_device_lock(address);
    
    if (*get_debug_logging_flag()) {
        printf("[MPU6050_SIM] Destroyed virtual MPU-6050 at address 0x%02X\n", address);
    }
    
    return 0;
}

int mpu6050_simulator_reset(uint8_t address) {
    // Destroy and recreate to reset to default state
    mpu6050_simulator_destroy(address);
    return mpu6050_simulator_create(address);
}

int mpu6050_simulator_set_pattern(uint8_t address, data_pattern_t pattern) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized || pattern >= PATTERN_COUNT) {
        return -EINVAL;
    }
    
    acquire_device_lock(address);
    state->pattern = pattern;
    release_device_lock(address);
    
    if (*get_debug_logging_flag()) {
        printf("[MPU6050_SIM] Set data pattern to %s for device 0x%02X\n", 
               pattern_type_to_string(pattern), address);
    }
    
    return 0;
}

int mpu6050_simulator_set_error_mode(uint8_t address, error_type_t error, double probability) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized || error >= ERROR_COUNT || probability < 0.0 || probability > 1.0) {
        return -EINVAL;
    }
    
    acquire_device_lock(address);
    state->error_mode = error;
    state->error_probability = probability;
    release_device_lock(address);
    
    if (*get_debug_logging_flag()) {
        printf("[MPU6050_SIM] Set error mode to %s (%.2f%%) for device 0x%02X\n", 
               error_type_to_string(error), probability * 100.0, address);
    }
    
    return 0;
}

int mpu6050_simulator_get_data(uint8_t address, sensor_data_t* data) {
    if (data == NULL) return -EINVAL;
    
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized) {
        return -ENODEV;
    }
    
    acquire_device_lock(address);
    *data = state->current_data;
    release_device_lock(address);
    
    return 0;
}

int mpu6050_simulator_inject_error(uint8_t address) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized) {
        return -ENODEV;
    }
    
    acquire_device_lock(address);
    
    // Force an error on next operation by temporarily setting high error probability
    state->error_probability = 1.0;
    state->error_mode = ERROR_BUS_ERROR;
    
    // The error will be injected on the next I2C operation
    // Reset after a brief moment (in background thread)
    
    release_device_lock(address);
    
    if (*get_debug_logging_flag()) {
        printf("[MPU6050_SIM] Injected error for device 0x%02X\n", address);
    }
    
    return 0;
}

int mpu6050_fifo_enable(uint8_t address, bool enable) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized) {
        return -ENODEV;
    }
    
    acquire_device_lock(address);
    pthread_mutex_lock(&state->fifo.mutex);
    
    state->fifo.enabled = enable;
    if (enable) {
        // Reset FIFO when enabling
        state->fifo.head = 0;
        state->fifo.tail = 0;
        state->fifo.count = 0;
        state->fifo.overflow = false;
    }
    
    // Update register
    if (enable) {
        state->registers[MPU6050_USER_CTRL] |= 0x40; // FIFO_EN bit
    } else {
        state->registers[MPU6050_USER_CTRL] &= ~0x40;
    }
    
    pthread_mutex_unlock(&state->fifo.mutex);
    release_device_lock(address);
    
    if (*get_debug_logging_flag()) {
        printf("[MPU6050_SIM] FIFO %s for device 0x%02X\n", 
               enable ? "enabled" : "disabled", address);
    }
    
    return 0;
}

int mpu6050_fifo_reset(uint8_t address) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized) {
        return -ENODEV;
    }
    
    acquire_device_lock(address);
    pthread_mutex_lock(&state->fifo.mutex);
    
    state->fifo.head = 0;
    state->fifo.tail = 0;
    state->fifo.count = 0;
    state->fifo.overflow = false;
    
    pthread_mutex_unlock(&state->fifo.mutex);
    release_device_lock(address);
    
    return 0;
}

int mpu6050_fifo_get_count(uint8_t address, uint16_t* count) {
    if (count == NULL) return -EINVAL;
    
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized) {
        return -ENODEV;
    }
    
    acquire_device_lock(address);
    pthread_mutex_lock(&state->fifo.mutex);
    *count = state->fifo.count;
    pthread_mutex_unlock(&state->fifo.mutex);
    release_device_lock(address);
    
    return 0;
}

int mpu6050_fifo_read(uint8_t address, uint8_t* data, size_t len) {
    if (data == NULL || len == 0) return -EINVAL;
    
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized) {
        return -ENODEV;
    }
    
    acquire_device_lock(address);
    pthread_mutex_lock(&state->fifo.mutex);
    
    size_t bytes_read = 0;
    while (bytes_read < len && state->fifo.count > 0) {
        data[bytes_read] = state->fifo.buffer[state->fifo.tail];
        state->fifo.tail = (state->fifo.tail + 1) % FIFO_BUFFER_SIZE;
        state->fifo.count--;
        bytes_read++;
    }
    
    pthread_mutex_unlock(&state->fifo.mutex);
    release_device_lock(address);
    
    return (int)bytes_read;
}

int mpu6050_set_power_state(uint8_t address, power_state_t power_state) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized || power_state >= POWER_COUNT) {
        return -EINVAL;
    }
    
    acquire_device_lock(address);
    state->power_state = power_state;
    
    // Update power management register
    switch (power_state) {
        case POWER_OFF:
            state->registers[MPU6050_PWR_MGMT_1] |= 0x40; // SLEEP bit
            break;
        case POWER_SLEEP:
            state->registers[MPU6050_PWR_MGMT_1] |= 0x40; // SLEEP bit
            break;
        case POWER_ON:
            state->registers[MPU6050_PWR_MGMT_1] &= ~0x40; // Clear SLEEP bit
            break;
        case POWER_CYCLE:
            state->registers[MPU6050_PWR_MGMT_1] |= 0x20; // CYCLE bit
            break;
        case POWER_COUNT:
            // Invalid state, ignore
            break;
    }
    
    release_device_lock(address);
    
    if (*get_debug_logging_flag()) {
        printf("[MPU6050_SIM] Set power state to %s for device 0x%02X\n", 
               power_state_to_string(power_state), address);
    }
    
    return 0;
}

power_state_t mpu6050_get_power_state(uint8_t address) {
    int index = address % MAX_I2C_DEVICES;
    mpu6050_state_t* state = &get_global_simulator()->mpu6050_devices[index];
    
    if (!state->initialized) {
        return POWER_OFF;
    }
    
    acquire_device_lock(address);
    power_state_t power_state = state->power_state;
    release_device_lock(address);
    
    return power_state;
}

// Data generation helper functions
int16_t generate_accel_data(data_pattern_t pattern, int axis, uint32_t sample_num) {
    double time_sec = sample_num / 1000.0; // Assume 1kHz sampling
    int16_t base_value = 0;
    
    // Set gravity for Z-axis in most patterns
    if (axis == 2 && pattern != PATTERN_NOISE) { // Z-axis
        base_value = ACCEL_SCALE_2G; // 1g downward
    }
    
    switch (pattern) {
        case PATTERN_STATIC:
            return base_value;
            
        case PATTERN_SINE_WAVE: {
            double freq_hz = 1.0 + axis * 0.5; // Different freq per axis
            double amplitude = ACCEL_SCALE_2G * 0.1; // 0.1g amplitude
            return base_value + (int16_t)(amplitude * sin(2 * M_PI * freq_hz * time_sec));
        }
        
        case PATTERN_NOISE: {
            // Generate white noise ±0.05g
            double noise = (rand() / (double)RAND_MAX - 0.5) * 2.0;
            return base_value + (int16_t)(noise * ACCEL_SCALE_2G * 0.05);
        }
        
        case PATTERN_GRAVITY_ONLY:
            return base_value;
            
        case PATTERN_ROTATION: {
            // Simulate device rotation
            double angle = time_sec * 0.5; // 0.5 rad/s
            switch (axis) {
                case 0: return (int16_t)(ACCEL_SCALE_2G * sin(angle)); // X
                case 1: return (int16_t)(ACCEL_SCALE_2G * 0.1 * cos(angle * 2)); // Y
                case 2: return (int16_t)(ACCEL_SCALE_2G * cos(angle)); // Z
            }
            break;
        }
        
        case PATTERN_VIBRATION: {
            // High-frequency vibration
            double freq = 50.0 + axis * 10.0; // 50-70 Hz
            double amplitude = ACCEL_SCALE_2G * 0.02; // 0.02g amplitude
            return base_value + (int16_t)(amplitude * sin(2 * M_PI * freq * time_sec));
        }
        
        default:
            return base_value;
    }
    
    return base_value;
}

int16_t generate_gyro_data(data_pattern_t pattern, int axis, uint32_t sample_num) {
    double time_sec = sample_num / 1000.0;
    
    switch (pattern) {
        case PATTERN_STATIC:
        case PATTERN_GRAVITY_ONLY:
            return 0; // No rotation
            
        case PATTERN_SINE_WAVE: {
            double freq_hz = 0.5 + axis * 0.2; // Different freq per axis
            double amplitude = GYRO_SCALE_250DPS * 10.0; // 10°/s amplitude
            return (int16_t)(amplitude * sin(2 * M_PI * freq_hz * time_sec));
        }
        
        case PATTERN_NOISE: {
            // Generate gyro noise ±1°/s
            double noise = (rand() / (double)RAND_MAX - 0.5) * 2.0;
            return (int16_t)(noise * GYRO_SCALE_250DPS);
        }
        
        case PATTERN_ROTATION: {
            // Constant rotation rates
            switch (axis) {
                case 0: return (int16_t)(GYRO_SCALE_250DPS * 5.0); // 5°/s around X
                case 1: return (int16_t)(GYRO_SCALE_250DPS * -2.0); // -2°/s around Y
                case 2: return (int16_t)(GYRO_SCALE_250DPS * 10.0 * sin(time_sec)); // Variable Z
            }
            break;
        }
        
        case PATTERN_VIBRATION: {
            // High-frequency angular vibration
            double freq = 30.0 + axis * 5.0; // 30-40 Hz
            double amplitude = GYRO_SCALE_250DPS * 2.0; // 2°/s amplitude
            return (int16_t)(amplitude * sin(2 * M_PI * freq * time_sec));
        }
        
        case PATTERN_COUNT:
        default:
            return 0;
    }
}

int16_t generate_temp_data(data_pattern_t pattern, uint32_t sample_num) {
    double base_temp = MPU6050_DEFAULT_TEMP;
    double time_sec = sample_num / 1000.0;
    
    switch (pattern) {
        case PATTERN_STATIC:
        case PATTERN_GRAVITY_ONLY:
            break; // Use base temperature
            
        case PATTERN_SINE_WAVE:
            // Slow temperature variation ±2°C
            base_temp += 2.0 * sin(2 * M_PI * 0.01 * time_sec); // 0.01 Hz
            break;
            
        case PATTERN_NOISE:
            // Temperature noise ±0.5°C
            base_temp += (rand() / (double)RAND_MAX - 0.5) * 1.0;
            break;
            
        case PATTERN_ROTATION:
        case PATTERN_VIBRATION:
            // Slight heating from activity
            base_temp += 1.0;
            break;
            
        default:
            break;
    }
    
    // Convert to MPU-6050 temperature format
    return (int16_t)((base_temp + TEMP_OFFSET) * TEMP_SENSITIVITY);
}

// Private implementation functions

int mpu6050_read_register(void* device, uint8_t reg, uint8_t* data) {
    mpu6050_state_t* state = (mpu6050_state_t*)device;
    
    if (!state || !data) return -EINVAL;
    if (!state->initialized) return -ENODEV;
    
    // Check for error injection
    if (should_inject_error(state->error_probability)) {
        switch (state->error_mode) {
            case ERROR_DEVICE_NOT_FOUND:
                return -ENODEV;
            case ERROR_TIMEOUT:
                usleep(100000); // 100ms timeout
                return -ETIMEDOUT;
            case ERROR_BUS_ERROR:
                return -EIO;
            case ERROR_CORRUPT_DATA:
                *data = rand() % 256; // Random corrupted data
                return 0;
            case ERROR_INTERMITTENT:
                if (rand() % 10 < 3) { // 30% chance of intermittent error
                    return -EIO;
                }
                break;
            default:
                break;
        }
    }
    
    if (!is_register_readable(reg)) {
        return -EACCES;
    }
    
    // Handle special registers that need dynamic updates
    switch (reg) {
        case MPU6050_ACCEL_XOUT_H:
            update_sensor_data(state);
            *data = (state->current_data.accel_x >> 8) & 0xFF;
            break;
        case MPU6050_ACCEL_XOUT_L:
            *data = state->current_data.accel_x & 0xFF;
            break;
        case MPU6050_ACCEL_YOUT_H:
            *data = (state->current_data.accel_y >> 8) & 0xFF;
            break;
        case MPU6050_ACCEL_YOUT_L:
            *data = state->current_data.accel_y & 0xFF;
            break;
        case MPU6050_ACCEL_ZOUT_H:
            *data = (state->current_data.accel_z >> 8) & 0xFF;
            break;
        case MPU6050_ACCEL_ZOUT_L:
            *data = state->current_data.accel_z & 0xFF;
            break;
        case MPU6050_GYRO_XOUT_H:
            *data = (state->current_data.gyro_x >> 8) & 0xFF;
            break;
        case MPU6050_GYRO_XOUT_L:
            *data = state->current_data.gyro_x & 0xFF;
            break;
        case MPU6050_GYRO_YOUT_H:
            *data = (state->current_data.gyro_y >> 8) & 0xFF;
            break;
        case MPU6050_GYRO_YOUT_L:
            *data = state->current_data.gyro_y & 0xFF;
            break;
        case MPU6050_GYRO_ZOUT_H:
            *data = (state->current_data.gyro_z >> 8) & 0xFF;
            break;
        case MPU6050_GYRO_ZOUT_L:
            *data = state->current_data.gyro_z & 0xFF;
            break;
        case MPU6050_TEMP_OUT_H:
            *data = (state->current_data.temperature >> 8) & 0xFF;
            break;
        case MPU6050_TEMP_OUT_L:
            *data = state->current_data.temperature & 0xFF;
            break;
        case MPU6050_FIFO_COUNTH:
            *data = (state->fifo.count >> 8) & 0xFF;
            break;
        case MPU6050_FIFO_COUNTL:
            *data = state->fifo.count & 0xFF;
            break;
        case MPU6050_FIFO_R_W:
            // Read one byte from FIFO
            if (state->fifo.count > 0) {
                pthread_mutex_lock(&state->fifo.mutex);
                *data = state->fifo.buffer[state->fifo.tail];
                state->fifo.tail = (state->fifo.tail + 1) % FIFO_BUFFER_SIZE;
                state->fifo.count--;
                pthread_mutex_unlock(&state->fifo.mutex);
            } else {
                *data = 0;
            }
            break;
        default:
            *data = state->registers[reg];
            break;
    }
    
    return 0;
}

int mpu6050_write_register(void* device, uint8_t reg, uint8_t data) {
    mpu6050_state_t* state = (mpu6050_state_t*)device;
    
    if (!state) return -EINVAL;
    if (!state->initialized) return -ENODEV;
    
    // Check for error injection
    if (should_inject_error(state->error_probability)) {
        switch (state->error_mode) {
            case ERROR_DEVICE_NOT_FOUND:
                return -ENODEV;
            case ERROR_TIMEOUT:
                usleep(100000); // 100ms timeout
                return -ETIMEDOUT;
            case ERROR_BUS_ERROR:
                return -EIO;
            default:
                break;
        }
    }
    
    if (!is_register_writable(reg)) {
        return -EACCES;
    }
    
    // Handle special register writes
    switch (reg) {
        case MPU6050_PWR_MGMT_1:
            handle_power_management(state, reg, data);
            break;
        case MPU6050_USER_CTRL:
        case MPU6050_FIFO_EN:
            handle_fifo_configuration(state, reg, data);
            break;
        case MPU6050_FIFO_R_W:
            // Write to FIFO (usually not done, but supported)
            pthread_mutex_lock(&state->fifo.mutex);
            if (state->fifo.count < FIFO_BUFFER_SIZE) {
                state->fifo.buffer[state->fifo.head] = data;
                state->fifo.head = (state->fifo.head + 1) % FIFO_BUFFER_SIZE;
                state->fifo.count++;
            } else {
                state->fifo.overflow = true;
            }
            pthread_mutex_unlock(&state->fifo.mutex);
            break;
        default:
            state->registers[reg] = data;
            break;
    }
    
    return 0;
}

int mpu6050_read_burst(void* device, uint8_t reg, uint8_t* data, size_t len) {
    // For MPU-6050, burst reads are typically sequential register reads
    for (size_t i = 0; i < len; i++) {
        int result = mpu6050_read_register(device, reg + i, &data[i]);
        if (result < 0) {
            return result;
        }
    }
    return 0;
}

static void update_sensor_data(mpu6050_state_t* state) {
    if (state->power_state == POWER_OFF || state->power_state == POWER_SLEEP) {
        return; // No data updates in sleep/off mode
    }
    
    state->sample_count++;
    
    // Generate new sensor data based on pattern
    state->current_data.accel_x = generate_accel_data(state->pattern, 0, state->sample_count);
    state->current_data.accel_y = generate_accel_data(state->pattern, 1, state->sample_count);
    state->current_data.accel_z = generate_accel_data(state->pattern, 2, state->sample_count);
    
    state->current_data.gyro_x = generate_gyro_data(state->pattern, 0, state->sample_count);
    state->current_data.gyro_y = generate_gyro_data(state->pattern, 1, state->sample_count);
    state->current_data.gyro_z = generate_gyro_data(state->pattern, 2, state->sample_count);
    
    state->current_data.temperature = generate_temp_data(state->pattern, state->sample_count);
    state->current_data.timestamp = generate_realistic_timestamp();
    
    // Update FIFO if enabled
    if (state->fifo.enabled) {
        update_fifo_buffer(state);
    }
}

static void update_fifo_buffer(mpu6050_state_t* state) {
    // Add sensor data to FIFO buffer (14 bytes per sample)
    pthread_mutex_lock(&state->fifo.mutex);
    
    uint8_t fifo_data[14];
    fifo_data[0] = (state->current_data.accel_x >> 8) & 0xFF;
    fifo_data[1] = state->current_data.accel_x & 0xFF;
    fifo_data[2] = (state->current_data.accel_y >> 8) & 0xFF;
    fifo_data[3] = state->current_data.accel_y & 0xFF;
    fifo_data[4] = (state->current_data.accel_z >> 8) & 0xFF;
    fifo_data[5] = state->current_data.accel_z & 0xFF;
    fifo_data[6] = (state->current_data.temperature >> 8) & 0xFF;
    fifo_data[7] = state->current_data.temperature & 0xFF;
    fifo_data[8] = (state->current_data.gyro_x >> 8) & 0xFF;
    fifo_data[9] = state->current_data.gyro_x & 0xFF;
    fifo_data[10] = (state->current_data.gyro_y >> 8) & 0xFF;
    fifo_data[11] = state->current_data.gyro_y & 0xFF;
    fifo_data[12] = (state->current_data.gyro_z >> 8) & 0xFF;
    fifo_data[13] = state->current_data.gyro_z & 0xFF;
    
    for (int i = 0; i < 14; i++) {
        if (state->fifo.count < FIFO_BUFFER_SIZE) {
            state->fifo.buffer[state->fifo.head] = fifo_data[i];
            state->fifo.head = (state->fifo.head + 1) % FIFO_BUFFER_SIZE;
            state->fifo.count++;
        } else {
            state->fifo.overflow = true;
            break;
        }
    }
    
    pthread_mutex_unlock(&state->fifo.mutex);
}

static bool is_register_readable(uint8_t reg) {
    (void)reg; // Mark parameter as used to avoid warning
    // Most registers are readable, with few exceptions
    return true; // Simplified - in real implementation, check datasheet
}

static bool is_register_writable(uint8_t reg) {
    // Check if register is writable based on MPU-6050 datasheet
    switch (reg) {
        case MPU6050_WHO_AM_I:
        case MPU6050_ACCEL_XOUT_H:
        case MPU6050_ACCEL_XOUT_L:
        case MPU6050_ACCEL_YOUT_H:
        case MPU6050_ACCEL_YOUT_L:
        case MPU6050_ACCEL_ZOUT_H:
        case MPU6050_ACCEL_ZOUT_L:
        case MPU6050_TEMP_OUT_H:
        case MPU6050_TEMP_OUT_L:
        case MPU6050_GYRO_XOUT_H:
        case MPU6050_GYRO_XOUT_L:
        case MPU6050_GYRO_YOUT_H:
        case MPU6050_GYRO_YOUT_L:
        case MPU6050_GYRO_ZOUT_H:
        case MPU6050_GYRO_ZOUT_L:
        case MPU6050_FIFO_COUNTH:
        case MPU6050_FIFO_COUNTL:
            return false; // Read-only registers
        default:
            return true;
    }
}

static void handle_power_management(mpu6050_state_t* state, uint8_t reg, uint8_t value) {
    state->registers[reg] = value;
    
    // Update power state based on register value
    if (value & 0x40) { // SLEEP bit
        state->power_state = POWER_SLEEP;
    } else if (value & 0x20) { // CYCLE bit
        state->power_state = POWER_CYCLE;
    } else {
        state->power_state = POWER_ON;
    }
    
    // Device reset
    if (value & 0x80) { // DEVICE_RESET bit
        // Reset all registers to default values
        memset(state->registers, 0, sizeof(state->registers));
        state->registers[MPU6050_WHO_AM_I] = MPU6050_WHO_AM_I_VALUE;
        state->registers[MPU6050_PWR_MGMT_1] = 0x40; // Back to sleep mode
        state->power_state = POWER_SLEEP;
        
        // Reset FIFO
        mpu6050_fifo_reset(0); // Address doesn't matter for internal reset
    }
}

static void handle_fifo_configuration(mpu6050_state_t* state, uint8_t reg, uint8_t value) {
    state->registers[reg] = value;
    
    if (reg == MPU6050_USER_CTRL) {
        if (value & 0x40) { // FIFO_EN bit
            state->fifo.enabled = true;
        } else {
            state->fifo.enabled = false;
        }
        
        if (value & 0x04) { // FIFO_RESET bit
            pthread_mutex_lock(&state->fifo.mutex);
            state->fifo.head = 0;
            state->fifo.tail = 0;
            state->fifo.count = 0;
            state->fifo.overflow = false;
            pthread_mutex_unlock(&state->fifo.mutex);
        }
    }
}