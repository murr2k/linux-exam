/**
 * @file test_helpers_c.h
 * @brief C-compatible utility functions for MPU-6050 driver testing
 * 
 * This file provides C-compatible versions of the test helper functions,
 * making them usable in both C and C++ test environments.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#ifndef TEST_HELPERS_C_H
#define TEST_HELPERS_C_H

#include <stdint.h>
#include <stdarg.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Data types */
typedef unsigned char u8;
typedef unsigned short u16;
typedef signed short s16;
typedef signed int s32;
typedef uint64_t u64;

/**
 * @struct sensor_reading
 * @brief Structure to hold sensor reading data
 */
struct sensor_reading {
    s16 accel_x, accel_y, accel_z;
    s16 gyro_x, gyro_y, gyro_z;
    s16 temperature;
    u64 timestamp;
};

/* Initialization and cleanup */
void test_helpers_init(void);
void test_helpers_cleanup(void);

/* Logging functions */
void test_helpers_enable_logging(void);
void test_helpers_disable_logging(void);
void test_helpers_log(const char *format, ...);

/* Data generation functions */
struct sensor_reading test_helpers_generate_stationary_reading(void);
struct sensor_reading test_helpers_generate_motion_reading(const char *motion_type);
struct sensor_reading test_helpers_generate_calibration_reading(void);
struct sensor_reading test_helpers_add_noise_to_reading(struct sensor_reading reading, double noise_level);

/* Validation functions */
int test_helpers_validate_accelerometer_range(s16 x, s16 y, s16 z, int range_g);
int test_helpers_validate_gyroscope_range(s16 x, s16 y, s16 z, int range_dps);
int test_helpers_validate_temperature_range(s16 temp);
int test_helpers_is_device_stationary(struct sensor_reading reading, double tolerance);
int test_helpers_is_device_in_freefall(struct sensor_reading reading, double tolerance);
double test_helpers_calculate_tilt_angle(s16 accel_x, s16 accel_y, s16 accel_z);

/* Utility functions */
void test_helpers_split_u16(u16 value, u8 *high, u8 *low);
u16 test_helpers_combine_bytes(u8 high, u8 low);
double test_helpers_raw_to_g_force(s16 raw_value, int range_g);
double test_helpers_raw_to_dps(s16 raw_value, int range_dps);
double test_helpers_raw_to_celsius(s16 raw_value);

/* Performance measurement */
void test_helpers_enable_performance_monitoring(void);
void test_helpers_disable_performance_monitoring(void);
void test_helpers_record_transaction(int is_read, int success, double time_ms);
void test_helpers_print_performance_stats(void);

/* Test timing functions */
double test_helpers_time_operation(void (*operation)(void));
void test_helpers_sleep_ms(int ms);

/* Random data generation */
void test_helpers_generate_random_bytes(u8 *buffer, int count);

/* String formatting for test output */
void test_helpers_format_test_description(char *output, size_t output_size, 
                                         const char *test_name, const char *description);

/* Mock verification helpers */
int test_helpers_verify_transaction_counts(int expected_reads, int expected_writes);

/* Test data file I/O */
int test_helpers_create_test_data_file(const char *filename, struct sensor_reading *readings, int count);
int test_helpers_load_test_data_file(const char *filename, struct sensor_reading *readings, int max_count);

/* Convenience macros for common operations */

#define EXPECT_VALID_ACCEL_DATA(x, y, z, range) \
    do { \
        if (!test_helpers_validate_accelerometer_range(x, y, z, range)) { \
            test_helpers_log("FAIL: Invalid accelerometer data [%d, %d, %d] for range ±%dg", x, y, z, range); \
        } else { \
            test_helpers_log("PASS: Valid accelerometer data"); \
        } \
    } while(0)

#define EXPECT_VALID_GYRO_DATA(x, y, z, range) \
    do { \
        if (!test_helpers_validate_gyroscope_range(x, y, z, range)) { \
            test_helpers_log("FAIL: Invalid gyroscope data [%d, %d, %d] for range ±%d°/s", x, y, z, range); \
        } else { \
            test_helpers_log("PASS: Valid gyroscope data"); \
        } \
    } while(0)

#define EXPECT_VALID_TEMPERATURE(temp) \
    do { \
        if (!test_helpers_validate_temperature_range(temp)) { \
            test_helpers_log("FAIL: Invalid temperature %d", temp); \
        } else { \
            test_helpers_log("PASS: Valid temperature %.2f°C", test_helpers_raw_to_celsius(temp)); \
        } \
    } while(0)

#define EXPECT_DEVICE_STATIONARY(reading) \
    do { \
        if (!test_helpers_is_device_stationary(reading, 0.1)) { \
            test_helpers_log("FAIL: Device not stationary"); \
        } else { \
            test_helpers_log("PASS: Device is stationary"); \
        } \
    } while(0)

#define TIME_OPERATION(operation) \
    do { \
        double elapsed = test_helpers_time_operation(operation); \
        test_helpers_log("Operation completed in %.3f ms", elapsed); \
    } while(0)

/* Assert-like macros for C tests */
#define TEST_ASSERT(condition, message) \
    do { \
        if (!(condition)) { \
            test_helpers_log("ASSERTION FAILED: %s", message); \
            return 0; \
        } \
    } while(0)

#define TEST_ASSERT_EQUAL(expected, actual, message) \
    do { \
        if ((expected) != (actual)) { \
            test_helpers_log("ASSERTION FAILED: %s (expected: %d, actual: %d)", message, expected, actual); \
            return 0; \
        } \
    } while(0)

#define TEST_ASSERT_NOT_NULL(pointer, message) \
    do { \
        if ((pointer) == NULL) { \
            test_helpers_log("ASSERTION FAILED: %s (pointer is NULL)", message); \
            return 0; \
        } \
    } while(0)

#define TEST_ASSERT_RANGE(value, min, max, message) \
    do { \
        if ((value) < (min) || (value) > (max)) { \
            test_helpers_log("ASSERTION FAILED: %s (value: %d, range: %d-%d)", message, value, min, max); \
            return 0; \
        } \
    } while(0)

/* Test result tracking */
struct test_result {
    int total_tests;
    int passed_tests;
    int failed_tests;
    double total_time_ms;
    char last_error[256];
};

/* Test result functions */
void test_result_init(struct test_result *result);
void test_result_record_pass(struct test_result *result, const char *test_name);
void test_result_record_fail(struct test_result *result, const char *test_name, const char *error);
void test_result_print_summary(const struct test_result *result);
int test_result_all_passed(const struct test_result *result);

#ifdef __cplusplus
}
#endif

#endif /* TEST_HELPERS_C_H */