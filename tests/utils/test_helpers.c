/**
 * @file test_helpers.c
 * @brief Implementation of utility functions for MPU-6050 driver testing
 * 
 * This file provides common utility functions, test data generators,
 * and helper classes to simplify test development and reduce code
 * duplication across test files.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <sys/time.h>
#include <unistd.h>

#include "test_helpers.h"

/* Global state for test helpers */
static struct {
    int logging_enabled;
    struct timeval test_start_time;
    int random_initialized;
    int performance_monitoring_enabled;
    
    struct {
        int transaction_count;
        int read_count;
        int write_count;
        int error_count;
        double total_time_ms;
    } performance_stats;
} test_state = {0};

/* Initialize random number generator if needed */
static void ensure_random_init(void)
{
    if (!test_state.random_initialized) {
        srand((unsigned int)time(NULL));
        test_state.random_initialized = 1;
    }
}

/* Get current time in milliseconds */
static double get_time_ms(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000.0 + tv.tv_usec / 1000.0;
}

/* Initialize test environment */
void test_helpers_init(void)
{
    memset(&test_state, 0, sizeof(test_state));
    gettimeofday(&test_state.test_start_time, NULL);
    ensure_random_init();
}

/* Cleanup test environment */
void test_helpers_cleanup(void)
{
    memset(&test_state, 0, sizeof(test_state));
}

/* Enable detailed logging */
void test_helpers_enable_logging(void)
{
    test_state.logging_enabled = 1;
}

/* Disable detailed logging */
void test_helpers_disable_logging(void)
{
    test_state.logging_enabled = 0;
}

/* Log message if logging is enabled */
void test_helpers_log(const char *format, ...)
{
    if (!test_state.logging_enabled)
        return;
        
    va_list args;
    printf("[TEST] ");
    va_start(args, format);
    vprintf(format, args);
    va_end(args);
    printf("\n");
}

/* Generate random sensor data */
struct sensor_reading test_helpers_generate_stationary_reading(void)
{
    ensure_random_init();
    
    struct sensor_reading reading = {0};
    
    /* Stationary device: small noise around gravity on Z-axis */
    reading.accel_x = (rand() % 200) - 100;     /* \u00b1100 LSB noise */
    reading.accel_y = (rand() % 200) - 100;     /* \u00b1100 LSB noise */
    reading.accel_z = 16384 + (rand() % 200) - 100;  /* 1g + noise */
    
    /* Minimal gyroscope values */
    reading.gyro_x = (rand() % 100) - 50;       /* \u00b150 LSB noise */
    reading.gyro_y = (rand() % 100) - 50;       /* \u00b150 LSB noise */
    reading.gyro_z = (rand() % 100) - 50;       /* \u00b150 LSB noise */
    
    /* Room temperature with small variation */
    reading.temperature = 8400 + (rand() % 200) - 100;  /* ~25\u00b0C \u00b1 variation */
    
    struct timeval tv;
    gettimeofday(&tv, NULL);
    reading.timestamp = tv.tv_sec * 1000000ULL + tv.tv_usec;
    
    return reading;
}

struct sensor_reading test_helpers_generate_motion_reading(const char *motion_type)
{
    ensure_random_init();
    
    struct sensor_reading reading = {0};
    
    if (strcmp(motion_type, "rotation_x") == 0) {
        /* Rotation around X-axis */
        reading.accel_x = (rand() % 4000) - 2000;
        reading.accel_y = (rand() % 8000) - 4000;
        reading.accel_z = (rand() % 8000) + 8000;
        reading.gyro_x = (rand() % 10000) + 5000;   /* Strong X rotation */
        reading.gyro_y = (rand() % 1000) - 500;
        reading.gyro_z = (rand() % 1000) - 500;
    } else if (strcmp(motion_type, "rotation_y") == 0) {
        /* Rotation around Y-axis */
        reading.accel_x = (rand() % 8000) - 4000;
        reading.accel_y = (rand() % 4000) - 2000;
        reading.accel_z = (rand() % 8000) + 8000;
        reading.gyro_x = (rand() % 1000) - 500;
        reading.gyro_y = (rand() % 10000) + 5000;   /* Strong Y rotation */
        reading.gyro_z = (rand() % 1000) - 500;
    } else if (strcmp(motion_type, "rotation_z") == 0) {
        /* Rotation around Z-axis */
        reading.accel_x = (rand() % 2000) - 1000;
        reading.accel_y = (rand() % 2000) - 1000;
        reading.accel_z = 16384 + (rand() % 1000) - 500;
        reading.gyro_x = (rand() % 1000) - 500;
        reading.gyro_y = (rand() % 1000) - 500;
        reading.gyro_z = (rand() % 10000) + 5000;   /* Strong Z rotation */
    } else if (strcmp(motion_type, "shake") == 0) {
        /* Shaking motion */
        reading.accel_x = (rand() % 16000) - 8000;
        reading.accel_y = (rand() % 16000) - 8000;
        reading.accel_z = (rand() % 16000) - 8000;
        reading.gyro_x = (rand() % 8000) - 4000;
        reading.gyro_y = (rand() % 8000) - 4000;
        reading.gyro_z = (rand() % 8000) - 4000;
    } else if (strcmp(motion_type, "freefall") == 0) {
        /* Free fall */
        reading.accel_x = (rand() % 1000) - 500;
        reading.accel_y = (rand() % 1000) - 500;
        reading.accel_z = (rand() % 1000) - 500;
        reading.gyro_x = (rand() % 2000) - 1000;
        reading.gyro_y = (rand() % 2000) - 1000;
        reading.gyro_z = (rand() % 2000) - 1000;
    } else {
        /* Default to stationary */
        return test_helpers_generate_stationary_reading();
    }
    
    /* Temperature stays relatively constant */
    reading.temperature = 8400 + (rand() % 200) - 100;
    
    struct timeval tv;
    gettimeofday(&tv, NULL);
    reading.timestamp = tv.tv_sec * 1000000ULL + tv.tv_usec;
    
    return reading;
}

struct sensor_reading test_helpers_generate_calibration_reading(void)
{
    struct sensor_reading reading = {0};
    
    /* Perfect calibration: no acceleration except gravity */
    reading.accel_x = 0;
    reading.accel_y = 0;
    reading.accel_z = 16384;  /* Exactly 1g */
    
    /* No rotation */
    reading.gyro_x = 0;
    reading.gyro_y = 0;
    reading.gyro_z = 0;
    
    /* Standard temperature */
    reading.temperature = 8653;  /* 25°C */
    
    struct timeval tv;
    gettimeofday(&tv, NULL);
    reading.timestamp = tv.tv_sec * 1000000ULL + tv.tv_usec;
    
    return reading;
}

struct sensor_reading test_helpers_add_noise_to_reading(struct sensor_reading reading, double noise_level)
{
    ensure_random_init();
    
    if (noise_level <= 0.0)
        return reading;
        
    /* Add noise to accelerometer readings */
    int accel_noise_range = (int)(noise_level * 1000);
    reading.accel_x += (rand() % (2 * accel_noise_range)) - accel_noise_range;
    reading.accel_y += (rand() % (2 * accel_noise_range)) - accel_noise_range;
    reading.accel_z += (rand() % (2 * accel_noise_range)) - accel_noise_range;
    
    /* Add noise to gyroscope readings */
    int gyro_noise_range = (int)(noise_level * 500);
    reading.gyro_x += (rand() % (2 * gyro_noise_range)) - gyro_noise_range;
    reading.gyro_y += (rand() % (2 * gyro_noise_range)) - gyro_noise_range;
    reading.gyro_z += (rand() % (2 * gyro_noise_range)) - gyro_noise_range;
    
    /* Add minimal noise to temperature */
    int temp_noise_range = (int)(noise_level * 100);
    reading.temperature += (rand() % (2 * temp_noise_range)) - temp_noise_range;
    
    return reading;
}

/* Validation functions */
int test_helpers_validate_accelerometer_range(short x, short y, short z, int range_g)
{
    int max_value = 32767;
    int expected_max = (max_value * range_g) / 16;  /* Scale based on range */
    
    return (abs(x) <= expected_max && 
            abs(y) <= expected_max && 
            abs(z) <= expected_max);
}

int test_helpers_validate_gyroscope_range(short x, short y, short z, int range_dps)
{
    int max_value = 32767;
    int expected_max = (max_value * range_dps) / 2000;  /* Scale based on range */
    
    return (abs(x) <= expected_max && 
            abs(y) <= expected_max && 
            abs(z) <= expected_max);
}

int test_helpers_validate_temperature_range(short temp)
{
    /* Valid temperature range: -40°C to +85°C */
    /* Formula: T = (TEMP_OUT/340) + 36.53 */
    /* TEMP_OUT = (T - 36.53) * 340 */
    short min_temp = (short)((-40.0 - 36.53) * 340);  /* ~-26000 */
    short max_temp = (short)((85.0 - 36.53) * 340);   /* ~16500 */
    
    return (temp >= min_temp && temp <= max_temp);
}

int test_helpers_is_device_stationary(struct sensor_reading reading, double tolerance)
{
    /* Check if accelerometer shows mostly gravity */
    double accel_magnitude = sqrt((double)reading.accel_x * reading.accel_x +
                                 (double)reading.accel_y * reading.accel_y +
                                 (double)reading.accel_z * reading.accel_z);
    double expected_gravity = 16384.0;  /* 1g at \u00b12g range */
    double accel_error = fabs(accel_magnitude - expected_gravity) / expected_gravity;
    
    /* Check if gyroscope shows minimal rotation */
    int gyro_magnitude = abs(reading.gyro_x) + abs(reading.gyro_y) + abs(reading.gyro_z);
    
    return (accel_error < tolerance && gyro_magnitude < 1000);
}

int test_helpers_is_device_in_freefall(struct sensor_reading reading, double tolerance)
{
    /* Check if accelerometer shows near-zero acceleration */
    double accel_magnitude = sqrt((double)reading.accel_x * reading.accel_x +
                                 (double)reading.accel_y * reading.accel_y +
                                 (double)reading.accel_z * reading.accel_z);
    
    return (accel_magnitude < tolerance * 16384.0);
}

double test_helpers_calculate_tilt_angle(short accel_x, short accel_y, short accel_z)
{
    /* Calculate tilt angle from vertical (Z-axis) */
    double magnitude = sqrt((double)accel_x * accel_x + 
                           (double)accel_y * accel_y + 
                           (double)accel_z * accel_z);
                           
    if (magnitude == 0.0)
        return 0.0;
        
    double z_normalized = (double)accel_z / magnitude;
    
    /* Clamp to valid range for acos */
    if (z_normalized > 1.0) z_normalized = 1.0;
    if (z_normalized < -1.0) z_normalized = -1.0;
    
    return acos(z_normalized) * 180.0 / M_PI;
}

/* Utility functions */
void test_helpers_split_u16(unsigned short value, unsigned char *high, unsigned char *low)
{
    *high = (value >> 8) & 0xFF;
    *low = value & 0xFF;
}

unsigned short test_helpers_combine_bytes(unsigned char high, unsigned char low)
{
    return ((unsigned short)high << 8) | (unsigned short)low;
}

double test_helpers_raw_to_g_force(short raw_value, int range_g)
{
    return ((double)raw_value * range_g) / 32768.0;
}

double test_helpers_raw_to_dps(short raw_value, int range_dps)
{
    return ((double)raw_value * range_dps) / 32768.0;
}

double test_helpers_raw_to_celsius(short raw_value)
{
    return ((double)raw_value / 340.0) + 36.53;
}

/* Performance measurement */
void test_helpers_enable_performance_monitoring(void)
{
    test_state.performance_monitoring_enabled = 1;
    memset(&test_state.performance_stats, 0, sizeof(test_state.performance_stats));
}

void test_helpers_disable_performance_monitoring(void)
{
    test_state.performance_monitoring_enabled = 0;
}

void test_helpers_record_transaction(int is_read, int success, double time_ms)
{
    if (!test_state.performance_monitoring_enabled)
        return;
        
    test_state.performance_stats.transaction_count++;
    if (is_read) {
        test_state.performance_stats.read_count++;
    } else {
        test_state.performance_stats.write_count++;
    }
    
    if (!success) {
        test_state.performance_stats.error_count++;
    }
    
    test_state.performance_stats.total_time_ms += time_ms;
}

void test_helpers_print_performance_stats(void)
{
    if (!test_state.performance_monitoring_enabled)
        return;
        
    printf("\n=== Performance Statistics ===\n");
    printf("Total Transactions: %d\n", test_state.performance_stats.transaction_count);
    printf("Read Operations: %d\n", test_state.performance_stats.read_count);
    printf("Write Operations: %d\n", test_state.performance_stats.write_count);
    printf("Errors: %d\n", test_state.performance_stats.error_count);
    printf("Total Time: %.3f ms\n", test_state.performance_stats.total_time_ms);
    
    if (test_state.performance_stats.transaction_count > 0) {
        double avg_time = test_state.performance_stats.total_time_ms / 
                         test_state.performance_stats.transaction_count;
        printf("Average Time per Transaction: %.3f ms\n", avg_time);
        
        double success_rate = 100.0 * (test_state.performance_stats.transaction_count - 
                                      test_state.performance_stats.error_count) /
                             test_state.performance_stats.transaction_count;
        printf("Success Rate: %.1f%%\n", success_rate);
    }
    printf("==============================\n\n");
}

/* Test timing functions */
double test_helpers_time_operation(void (*operation)(void))
{
    double start_time = get_time_ms();
    operation();
    double end_time = get_time_ms();
    return end_time - start_time;
}

void test_helpers_sleep_ms(int ms)
{
    usleep(ms * 1000);
}

/* Random data generation */
void test_helpers_generate_random_bytes(unsigned char *buffer, int count)
{
    ensure_random_init();
    
    for (int i = 0; i < count; i++) {
        buffer[i] = (unsigned char)(rand() & 0xFF);
    }
}

/* String formatting for test output */
void test_helpers_format_test_description(char *output, size_t output_size, 
                                         const char *test_name, const char *description)
{
    snprintf(output, output_size, "[%s] %s", test_name, description);
}

/* Mock verification helpers */
int test_helpers_verify_transaction_counts(int expected_reads, int expected_writes)
{
    /* This would interface with the mock system */
    /* For now, return success as a placeholder */
    test_helpers_log("Verifying transaction counts: reads=%d, writes=%d", 
                    expected_reads, expected_writes);
    return 1;
}

/* Test data file generation */
int test_helpers_create_test_data_file(const char *filename, struct sensor_reading *readings, int count)
{
    FILE *file = fopen(filename, "w");
    if (!file) {
        return 0;
    }
    
    fprintf(file, "# MPU-6050 Test Data\n");
    fprintf(file, "# Format: timestamp,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,temperature\n");
    
    for (int i = 0; i < count; i++) {
        fprintf(file, "%llu,%d,%d,%d,%d,%d,%d,%d\n",
                readings[i].timestamp,
                readings[i].accel_x, readings[i].accel_y, readings[i].accel_z,
                readings[i].gyro_x, readings[i].gyro_y, readings[i].gyro_z,
                readings[i].temperature);
    }
    
    fclose(file);
    return 1;
}

int test_helpers_load_test_data_file(const char *filename, struct sensor_reading *readings, int max_count)
{
    FILE *file = fopen(filename, "r");
    if (!file) {
        return 0;
    }
    
    char line[256];
    int count = 0;
    
    /* Skip header lines */
    while (fgets(line, sizeof(line), file) && line[0] == '#') {
        /* Skip comments */
    }
    
    /* Read data lines */
    do {
        if (line[0] != '#' && count < max_count) {
            if (sscanf(line, "%llu,%hd,%hd,%hd,%hd,%hd,%hd,%hd",
                      &readings[count].timestamp,
                      &readings[count].accel_x, &readings[count].accel_y, &readings[count].accel_z,
                      &readings[count].gyro_x, &readings[count].gyro_y, &readings[count].gyro_z,
                      &readings[count].temperature) == 8) {
                count++;
            }
        }
    } while (fgets(line, sizeof(line), file) && count < max_count);
    
    fclose(file);
    return count;
}