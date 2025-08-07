/*
 * MPU-6050 Range Validation Test
 *
 * This test validates that the MPU-6050 driver correctly handles different
 * measurement ranges for both accelerometer and gyroscope sensors.
 *
 * Tests include:
 * - Accelerometer range validation (±2g to ±16g)
 * - Gyroscope range validation (±250 to ±2000 °/s)
 * - Temperature range validation
 * - Data integrity and consistency checks
 * - Range switching verification
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#define _GNU_SOURCE
#define _DEFAULT_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <sys/time.h>
#include <math.h>
#include <time.h>
#include <signal.h>
#include <stdarg.h>

#include "../../include/mpu6050.h"

#define DEVICE_PATH "/dev/mpu6050"
#define NUM_SAMPLES_PER_RANGE 50
#define STABILITY_THRESHOLD_ACCEL 0.1  /* 100mg stability threshold */
#define STABILITY_THRESHOLD_GYRO 0.05  /* 50mdps stability threshold */

/* Color codes for output */
#define COLOR_RED     "\033[31m"
#define COLOR_GREEN   "\033[32m"
#define COLOR_YELLOW  "\033[33m"
#define COLOR_BLUE    "\033[34m"
#define COLOR_MAGENTA "\033[35m"
#define COLOR_CYAN    "\033[36m"
#define COLOR_RESET   "\033[0m"

/* Range configuration structures */
struct range_config {
    u8 value;
    const char *name;
    double max_value;  /* Maximum expected value in standard units */
    const char *unit;
};

/* Accelerometer ranges */
static const struct range_config accel_ranges[] = {
    {MPU6050_ACCEL_FS_2G,  "±2g",   2000.0, "mg"},
    {MPU6050_ACCEL_FS_4G,  "±4g",   4000.0, "mg"},
    {MPU6050_ACCEL_FS_8G,  "±8g",   8000.0, "mg"},
    {MPU6050_ACCEL_FS_16G, "±16g", 16000.0, "mg"},
};

/* Gyroscope ranges */
static const struct range_config gyro_ranges[] = {
    {MPU6050_GYRO_FS_250,  "±250°/s",  250000.0, "mdps"},
    {MPU6050_GYRO_FS_500,  "±500°/s",  500000.0, "mdps"},
    {MPU6050_GYRO_FS_1000, "±1000°/s", 1000000.0, "mdps"},
    {MPU6050_GYRO_FS_2000, "±2000°/s", 2000000.0, "mdps"},
};

#define NUM_ACCEL_RANGES (sizeof(accel_ranges) / sizeof(accel_ranges[0]))
#define NUM_GYRO_RANGES (sizeof(gyro_ranges) / sizeof(gyro_ranges[0]))

/* Test statistics structure */
struct test_stats {
    int total_tests;
    int passed_tests;
    int failed_tests;
    double test_duration;
    struct timeval start_time;
    struct timeval end_time;
};

/* Range test results */
struct range_test_result {
    const struct range_config *range;
    int samples_collected;
    double mean_x, mean_y, mean_z;
    double stdev_x, stdev_y, stdev_z;
    double max_x, max_y, max_z;
    double min_x, min_y, min_z;
    int range_violations;
    int stability_violations;
    int passed;
};

/* Global variables */
static int g_verbose = 0;
static int g_running = 1;

/**
 * Signal handler for graceful shutdown
 */
static void signal_handler(int sig) {
    printf("\n" COLOR_YELLOW "Received signal %d, shutting down gracefully..." COLOR_RESET "\n", sig);
    g_running = 0;
}

/**
 * Print test header with formatting
 */
static void print_test_header(const char *test_name) {
    printf(COLOR_CYAN "========================================" COLOR_RESET "\n");
    printf(COLOR_CYAN "TEST: %s" COLOR_RESET "\n", test_name);
    printf(COLOR_CYAN "========================================" COLOR_RESET "\n");
}

/**
 * Print test result with color coding
 */
static void print_test_result(const char *test_name, int passed, const char *details) {
    const char *status = passed ? COLOR_GREEN "PASS" COLOR_RESET : COLOR_RED "FAIL" COLOR_RESET;
    printf("[%s] %s", status, test_name);
    if (details && strlen(details) > 0) {
        printf(" - %s", details);
    }
    printf("\n");
}

/**
 * Verbose logging function
 */
static void verbose_log(const char *format, ...) {
    if (g_verbose) {
        va_list args;
        va_start(args, format);
        printf(COLOR_BLUE "[VERBOSE] " COLOR_RESET);
        vprintf(format, args);
        printf("\n");
        va_end(args);
    }
}

/**
 * Calculate mean of an array
 */
static double calculate_mean(double *values, int count) {
    if (count == 0) return 0.0;
    
    double sum = 0.0;
    for (int i = 0; i < count; i++) {
        sum += values[i];
    }
    return sum / count;
}

/**
 * Calculate standard deviation of an array
 */
static double calculate_stdev(double *values, int count, double mean) {
    if (count <= 1) return 0.0;
    
    double sum_sq = 0.0;
    for (int i = 0; i < count; i++) {
        double diff = values[i] - mean;
        sum_sq += diff * diff;
    }
    return sqrt(sum_sq / (count - 1));
}

/**
 * Find minimum value in array
 */
static double find_min(double *values, int count) {
    if (count == 0) return 0.0;
    
    double min = values[0];
    for (int i = 1; i < count; i++) {
        if (values[i] < min) {
            min = values[i];
        }
    }
    return min;
}

/**
 * Find maximum value in array
 */
static double find_max(double *values, int count) {
    if (count == 0) return 0.0;
    
    double max = values[0];
    for (int i = 1; i < count; i++) {
        if (values[i] > max) {
            max = values[i];
        }
    }
    return max;
}

/**
 * Test accelerometer range configuration
 */
static int test_accelerometer_range(int fd, const struct range_config *range, 
                                   struct range_test_result *result) {
    printf(COLOR_YELLOW "Testing accelerometer range: %s" COLOR_RESET "\n", range->name);
    
    memset(result, 0, sizeof(*result));
    result->range = range;
    
    /* Set configuration for this range */
    struct mpu6050_config config = {
        .sample_rate_div = 7,  /* 125Hz */
        .gyro_range = MPU6050_GYRO_FS_250,  /* Keep gyro at minimum range */
        .accel_range = range->value,
        .dlpf_cfg = 0x03  /* 44Hz low-pass filter */
    };
    
    int ret = ioctl(fd, MPU6050_IOC_SET_CONFIG, &config);
    if (ret < 0) {
        verbose_log("Failed to set accelerometer range %s: %s", range->name, strerror(errno));
        return 0;
    }
    
    /* Wait for configuration to settle */
    usleep(100000);  /* 100ms */
    
    /* Collect samples */
    double accel_x[NUM_SAMPLES_PER_RANGE];
    double accel_y[NUM_SAMPLES_PER_RANGE];
    double accel_z[NUM_SAMPLES_PER_RANGE];
    int samples_collected = 0;
    
    for (int i = 0; i < NUM_SAMPLES_PER_RANGE && g_running; i++) {
        struct mpu6050_scaled_data data;
        ret = ioctl(fd, MPU6050_IOC_READ_SCALED, &data);
        
        if (ret == 0) {
            accel_x[samples_collected] = (double)data.accel_x;
            accel_y[samples_collected] = (double)data.accel_y;
            accel_z[samples_collected] = (double)data.accel_z;
            samples_collected++;
            
            verbose_log("Sample %d: X=%d mg, Y=%d mg, Z=%d mg", 
                       i, data.accel_x, data.accel_y, data.accel_z);
        } else {
            verbose_log("Failed to read sample %d: %s", i, strerror(errno));
        }
        
        usleep(10000);  /* 10ms between samples */
    }
    
    result->samples_collected = samples_collected;
    
    if (samples_collected < NUM_SAMPLES_PER_RANGE / 2) {
        verbose_log("Insufficient samples collected: %d/%d", samples_collected, NUM_SAMPLES_PER_RANGE);
        return 0;
    }
    
    /* Calculate statistics */
    result->mean_x = calculate_mean(accel_x, samples_collected);
    result->mean_y = calculate_mean(accel_y, samples_collected);
    result->mean_z = calculate_mean(accel_z, samples_collected);
    
    result->stdev_x = calculate_stdev(accel_x, samples_collected, result->mean_x);
    result->stdev_y = calculate_stdev(accel_y, samples_collected, result->mean_y);
    result->stdev_z = calculate_stdev(accel_z, samples_collected, result->mean_z);
    
    result->min_x = find_min(accel_x, samples_collected);
    result->min_y = find_min(accel_y, samples_collected);
    result->min_z = find_min(accel_z, samples_collected);
    
    result->max_x = find_max(accel_x, samples_collected);
    result->max_y = find_max(accel_y, samples_collected);
    result->max_z = find_max(accel_z, samples_collected);
    
    /* Check for range violations */
    double max_expected = range->max_value;
    double values[] = {result->max_x, result->max_y, result->max_z,
                       -result->min_x, -result->min_y, -result->min_z};
    
    for (int i = 0; i < 6; i++) {
        if (fabs(values[i]) > max_expected) {
            result->range_violations++;
        }
    }
    
    /* Check for stability (noise should be reasonable) */
    double noise_threshold = range->max_value * STABILITY_THRESHOLD_ACCEL;
    if (result->stdev_x > noise_threshold || 
        result->stdev_y > noise_threshold || 
        result->stdev_z > noise_threshold) {
        result->stability_violations++;
    }
    
    /* Test passes if no range violations and reasonable stability */
    result->passed = (result->range_violations == 0 && result->stability_violations == 0);
    
    /* Print results */
    printf("  Samples collected: %d/%d\n", samples_collected, NUM_SAMPLES_PER_RANGE);
    printf("  Mean: X=%.1f, Y=%.1f, Z=%.1f %s\n", 
           result->mean_x, result->mean_y, result->mean_z, range->unit);
    printf("  Std Dev: X=%.2f, Y=%.2f, Z=%.2f %s\n", 
           result->stdev_x, result->stdev_y, result->stdev_z, range->unit);
    printf("  Range: X=[%.1f,%.1f], Y=[%.1f,%.1f], Z=[%.1f,%.1f] %s\n",
           result->min_x, result->max_x, result->min_y, result->max_y, 
           result->min_z, result->max_z, range->unit);
    printf("  Range violations: %d\n", result->range_violations);
    printf("  Stability violations: %d\n", result->stability_violations);
    
    return result->passed;
}

/**
 * Test gyroscope range configuration
 */
static int test_gyroscope_range(int fd, const struct range_config *range, 
                               struct range_test_result *result) {
    printf(COLOR_YELLOW "Testing gyroscope range: %s" COLOR_RESET "\n", range->name);
    
    memset(result, 0, sizeof(*result));
    result->range = range;
    
    /* Set configuration for this range */
    struct mpu6050_config config = {
        .sample_rate_div = 7,  /* 125Hz */
        .gyro_range = range->value,
        .accel_range = MPU6050_ACCEL_FS_2G,  /* Keep accel at minimum range */
        .dlpf_cfg = 0x03  /* 44Hz low-pass filter */
    };
    
    int ret = ioctl(fd, MPU6050_IOC_SET_CONFIG, &config);
    if (ret < 0) {
        verbose_log("Failed to set gyroscope range %s: %s", range->name, strerror(errno));
        return 0;
    }
    
    /* Wait for configuration to settle */
    usleep(100000);  /* 100ms */
    
    /* Collect samples */
    double gyro_x[NUM_SAMPLES_PER_RANGE];
    double gyro_y[NUM_SAMPLES_PER_RANGE];
    double gyro_z[NUM_SAMPLES_PER_RANGE];
    int samples_collected = 0;
    
    for (int i = 0; i < NUM_SAMPLES_PER_RANGE && g_running; i++) {
        struct mpu6050_scaled_data data;
        ret = ioctl(fd, MPU6050_IOC_READ_SCALED, &data);
        
        if (ret == 0) {
            gyro_x[samples_collected] = (double)data.gyro_x;
            gyro_y[samples_collected] = (double)data.gyro_y;
            gyro_z[samples_collected] = (double)data.gyro_z;
            samples_collected++;
            
            verbose_log("Sample %d: X=%d mdps, Y=%d mdps, Z=%d mdps", 
                       i, data.gyro_x, data.gyro_y, data.gyro_z);
        } else {
            verbose_log("Failed to read sample %d: %s", i, strerror(errno));
        }
        
        usleep(10000);  /* 10ms between samples */
    }
    
    result->samples_collected = samples_collected;
    
    if (samples_collected < NUM_SAMPLES_PER_RANGE / 2) {
        verbose_log("Insufficient samples collected: %d/%d", samples_collected, NUM_SAMPLES_PER_RANGE);
        return 0;
    }
    
    /* Calculate statistics */
    result->mean_x = calculate_mean(gyro_x, samples_collected);
    result->mean_y = calculate_mean(gyro_y, samples_collected);
    result->mean_z = calculate_mean(gyro_z, samples_collected);
    
    result->stdev_x = calculate_stdev(gyro_x, samples_collected, result->mean_x);
    result->stdev_y = calculate_stdev(gyro_y, samples_collected, result->mean_y);
    result->stdev_z = calculate_stdev(gyro_z, samples_collected, result->mean_z);
    
    result->min_x = find_min(gyro_x, samples_collected);
    result->min_y = find_min(gyro_y, samples_collected);
    result->min_z = find_min(gyro_z, samples_collected);
    
    result->max_x = find_max(gyro_x, samples_collected);
    result->max_y = find_max(gyro_y, samples_collected);
    result->max_z = find_max(gyro_z, samples_collected);
    
    /* Check for range violations */
    double max_expected = range->max_value;
    double values[] = {result->max_x, result->max_y, result->max_z,
                       -result->min_x, -result->min_y, -result->min_z};
    
    for (int i = 0; i < 6; i++) {
        if (fabs(values[i]) > max_expected) {
            result->range_violations++;
        }
    }
    
    /* Check for stability (noise should be reasonable) */
    double noise_threshold = range->max_value * STABILITY_THRESHOLD_GYRO;
    if (result->stdev_x > noise_threshold || 
        result->stdev_y > noise_threshold || 
        result->stdev_z > noise_threshold) {
        result->stability_violations++;
    }
    
    /* Test passes if no range violations and reasonable stability */
    result->passed = (result->range_violations == 0 && result->stability_violations == 0);
    
    /* Print results */
    printf("  Samples collected: %d/%d\n", samples_collected, NUM_SAMPLES_PER_RANGE);
    printf("  Mean: X=%.1f, Y=%.1f, Z=%.1f %s\n", 
           result->mean_x, result->mean_y, result->mean_z, range->unit);
    printf("  Std Dev: X=%.2f, Y=%.2f, Z=%.2f %s\n", 
           result->stdev_x, result->stdev_y, result->stdev_z, range->unit);
    printf("  Range: X=[%.1f,%.1f], Y=[%.1f,%.1f], Z=[%.1f,%.1f] %s\n",
           result->min_x, result->max_x, result->min_y, result->max_y, 
           result->min_z, result->max_z, range->unit);
    printf("  Range violations: %d\n", result->range_violations);
    printf("  Stability violations: %d\n", result->stability_violations);
    
    return result->passed;
}

/**
 * Test temperature range validation
 */
static int test_temperature_range(int fd) {
    print_test_header("Temperature Range Validation");
    
    /* Collect temperature samples */
    double temps[NUM_SAMPLES_PER_RANGE];
    int samples_collected = 0;
    
    for (int i = 0; i < NUM_SAMPLES_PER_RANGE && g_running; i++) {
        struct mpu6050_scaled_data data;
        int ret = ioctl(fd, MPU6050_IOC_READ_SCALED, &data);
        
        if (ret == 0) {
            temps[samples_collected] = (double)data.temp / 100.0;  /* Convert to Celsius */
            samples_collected++;
            
            verbose_log("Sample %d: Temperature = %.2f°C", i, temps[samples_collected-1]);
        } else {
            verbose_log("Failed to read temperature sample %d: %s", i, strerror(errno));
        }
        
        usleep(10000);  /* 10ms between samples */
    }
    
    if (samples_collected == 0) {
        print_test_result("Temperature Range", 0, "No samples collected");
        return 0;
    }
    
    /* Calculate statistics */
    double mean_temp = calculate_mean(temps, samples_collected);
    double stdev_temp = calculate_stdev(temps, samples_collected, mean_temp);
    double min_temp = find_min(temps, samples_collected);
    double max_temp = find_max(temps, samples_collected);
    
    /* Validate temperature range (MPU-6050 operates from -40°C to +85°C) */
    int range_violations = 0;
    if (min_temp < -45.0 || max_temp > 90.0) {
        range_violations++;
    }
    
    /* Check for reasonable stability (temperature shouldn't vary too much quickly) */
    int stability_violations = 0;
    if (stdev_temp > 5.0) {  /* 5°C standard deviation seems excessive for quick readings */
        stability_violations++;
    }
    
    /* Print results */
    printf("Temperature Statistics:\n");
    printf("  Samples collected: %d/%d\n", samples_collected, NUM_SAMPLES_PER_RANGE);
    printf("  Mean: %.2f°C\n", mean_temp);
    printf("  Std Dev: %.3f°C\n", stdev_temp);
    printf("  Range: [%.2f, %.2f]°C\n", min_temp, max_temp);
    printf("  Range violations: %d\n", range_violations);
    printf("  Stability violations: %d\n", stability_violations);
    
    int passed = (range_violations == 0 && stability_violations == 0);
    
    char details[256];
    snprintf(details, sizeof(details), "Mean: %.2f°C, Range: [%.2f, %.2f]°C", 
             mean_temp, min_temp, max_temp);
    print_test_result("Temperature Range", passed, details);
    
    return passed;
}

/**
 * Test range switching consistency
 */
static int test_range_switching(int fd) {
    print_test_header("Range Switching Consistency");
    
    int tests_passed = 0;
    int total_tests = 0;
    
    /* Test accelerometer range switching */
    for (int i = 0; i < NUM_ACCEL_RANGES - 1; i++) {
        const struct range_config *range1 = &accel_ranges[i];
        const struct range_config *range2 = &accel_ranges[i + 1];
        
        printf(COLOR_YELLOW "Testing accel range switch: %s -> %s" COLOR_RESET "\n", 
               range1->name, range2->name);
        
        /* Set first range and take reading */
        struct mpu6050_config config1 = {
            .sample_rate_div = 7,
            .gyro_range = MPU6050_GYRO_FS_250,
            .accel_range = range1->value,
            .dlpf_cfg = 0x03
        };
        
        int ret = ioctl(fd, MPU6050_IOC_SET_CONFIG, &config1);
        if (ret < 0) continue;
        
        usleep(100000);  /* Wait for settling */
        
        struct mpu6050_scaled_data data1;
        ret = ioctl(fd, MPU6050_IOC_READ_SCALED, &data1);
        if (ret < 0) continue;
        
        /* Set second range and take reading */
        struct mpu6050_config config2 = {
            .sample_rate_div = 7,
            .gyro_range = MPU6050_GYRO_FS_250,
            .accel_range = range2->value,
            .dlpf_cfg = 0x03
        };
        
        ret = ioctl(fd, MPU6050_IOC_SET_CONFIG, &config2);
        if (ret < 0) continue;
        
        usleep(100000);  /* Wait for settling */
        
        struct mpu6050_scaled_data data2;
        ret = ioctl(fd, MPU6050_IOC_READ_SCALED, &data2);
        if (ret < 0) continue;
        
        /* Compare readings - they should be reasonably close when converted to g */
        double g1_x = (double)data1.accel_x / 1000.0;
        double g1_y = (double)data1.accel_y / 1000.0;
        double g1_z = (double)data1.accel_z / 1000.0;
        
        double g2_x = (double)data2.accel_x / 1000.0;
        double g2_y = (double)data2.accel_y / 1000.0;
        double g2_z = (double)data2.accel_z / 1000.0;
        
        double diff_x = fabs(g1_x - g2_x);
        double diff_y = fabs(g1_y - g2_y);
        double diff_z = fabs(g1_z - g2_z);
        
        /* Allow 0.1g difference for range switching consistency */
        double tolerance = 0.1;
        int consistent = (diff_x < tolerance && diff_y < tolerance && diff_z < tolerance);
        
        verbose_log("Range1 (%s): X=%.3fg, Y=%.3fg, Z=%.3fg", range1->name, g1_x, g1_y, g1_z);
        verbose_log("Range2 (%s): X=%.3fg, Y=%.3fg, Z=%.3fg", range2->name, g2_x, g2_y, g2_z);
        verbose_log("Differences: X=%.3fg, Y=%.3fg, Z=%.3fg", diff_x, diff_y, diff_z);
        
        char test_name[128];
        char details[256];
        snprintf(test_name, sizeof(test_name), "Accel %s -> %s", range1->name, range2->name);
        snprintf(details, sizeof(details), "Max diff: %.3fg (tolerance: %.3fg)", 
                 fmax(fmax(diff_x, diff_y), diff_z), tolerance);
        
        print_test_result(test_name, consistent, details);
        
        if (consistent) tests_passed++;
        total_tests++;
    }
    
    /* Test gyroscope range switching */
    for (int i = 0; i < NUM_GYRO_RANGES - 1; i++) {
        const struct range_config *range1 = &gyro_ranges[i];
        const struct range_config *range2 = &gyro_ranges[i + 1];
        
        printf(COLOR_YELLOW "Testing gyro range switch: %s -> %s" COLOR_RESET "\n", 
               range1->name, range2->name);
        
        /* Set first range and take reading */
        struct mpu6050_config config1 = {
            .sample_rate_div = 7,
            .gyro_range = range1->value,
            .accel_range = MPU6050_ACCEL_FS_2G,
            .dlpf_cfg = 0x03
        };
        
        int ret = ioctl(fd, MPU6050_IOC_SET_CONFIG, &config1);
        if (ret < 0) continue;
        
        usleep(100000);  /* Wait for settling */
        
        struct mpu6050_scaled_data data1;
        ret = ioctl(fd, MPU6050_IOC_READ_SCALED, &data1);
        if (ret < 0) continue;
        
        /* Set second range and take reading */
        struct mpu6050_config config2 = {
            .sample_rate_div = 7,
            .gyro_range = range2->value,
            .accel_range = MPU6050_ACCEL_FS_2G,
            .dlpf_cfg = 0x03
        };
        
        ret = ioctl(fd, MPU6050_IOC_SET_CONFIG, &config2);
        if (ret < 0) continue;
        
        usleep(100000);  /* Wait for settling */
        
        struct mpu6050_scaled_data data2;
        ret = ioctl(fd, MPU6050_IOC_READ_SCALED, &data2);
        if (ret < 0) continue;
        
        /* Compare readings - they should be reasonably close when converted to dps */
        double dps1_x = (double)data1.gyro_x / 1000.0;
        double dps1_y = (double)data1.gyro_y / 1000.0;
        double dps1_z = (double)data1.gyro_z / 1000.0;
        
        double dps2_x = (double)data2.gyro_x / 1000.0;
        double dps2_y = (double)data2.gyro_y / 1000.0;
        double dps2_z = (double)data2.gyro_z / 1000.0;
        
        double diff_x = fabs(dps1_x - dps2_x);
        double diff_y = fabs(dps1_y - dps2_y);
        double diff_z = fabs(dps1_z - dps2_z);
        
        /* Allow 2°/s difference for range switching consistency */
        double tolerance = 2.0;
        int consistent = (diff_x < tolerance && diff_y < tolerance && diff_z < tolerance);
        
        verbose_log("Range1 (%s): X=%.2f°/s, Y=%.2f°/s, Z=%.2f°/s", range1->name, dps1_x, dps1_y, dps1_z);
        verbose_log("Range2 (%s): X=%.2f°/s, Y=%.2f°/s, Z=%.2f°/s", range2->name, dps2_x, dps2_y, dps2_z);
        verbose_log("Differences: X=%.2f°/s, Y=%.2f°/s, Z=%.2f°/s", diff_x, diff_y, diff_z);
        
        char test_name[128];
        char details[256];
        snprintf(test_name, sizeof(test_name), "Gyro %s -> %s", range1->name, range2->name);
        snprintf(details, sizeof(details), "Max diff: %.2f°/s (tolerance: %.2f°/s)", 
                 fmax(fmax(diff_x, diff_y), diff_z), tolerance);
        
        print_test_result(test_name, consistent, details);
        
        if (consistent) tests_passed++;
        total_tests++;
    }
    
    char summary[256];
    snprintf(summary, sizeof(summary), "%d/%d range switches passed", tests_passed, total_tests);
    print_test_result("Range Switching Summary", tests_passed == total_tests, summary);
    
    return tests_passed;
}

/**
 * Print comprehensive test summary
 */
static void print_test_summary(struct test_stats *stats) {
    double pass_rate = (stats->total_tests > 0) ? 
        (100.0 * stats->passed_tests / stats->total_tests) : 0.0;
    
    printf("\n" COLOR_MAGENTA "========================================" COLOR_RESET "\n");
    printf(COLOR_MAGENTA "RANGE VALIDATION TEST SUMMARY" COLOR_RESET "\n");
    printf(COLOR_MAGENTA "========================================" COLOR_RESET "\n");
    printf("Total Tests:    %d\n", stats->total_tests);
    printf("Passed Tests:   " COLOR_GREEN "%d" COLOR_RESET "\n", stats->passed_tests);
    printf("Failed Tests:   " COLOR_RED "%d" COLOR_RESET "\n", stats->failed_tests);
    printf("Pass Rate:      %.1f%%\n", pass_rate);
    printf("Test Duration:  %.3f seconds\n", stats->test_duration);
    printf("\n");
    
    if (stats->failed_tests == 0) {
        printf(COLOR_GREEN "ALL RANGE VALIDATION TESTS PASSED!" COLOR_RESET "\n");
    } else {
        printf(COLOR_RED "SOME RANGE VALIDATION TESTS FAILED!" COLOR_RESET "\n");
    }
    printf(COLOR_MAGENTA "========================================" COLOR_RESET "\n");
}

/**
 * Print usage information
 */
static void print_usage(const char *program_name) {
    printf("Usage: %s [options]\n", program_name);
    printf("\n");
    printf("Options:\n");
    printf("  -v, --verbose    Enable verbose output\n");
    printf("  -h, --help       Show this help message\n");
    printf("\n");
    printf("Description:\n");
    printf("  This program validates the range configuration capabilities of the\n");
    printf("  MPU-6050 driver by testing all supported accelerometer and gyroscope\n");
    printf("  ranges, verifying data integrity, and checking range switching\n");
    printf("  consistency.\n");
    printf("\n");
    printf("Tests performed:\n");
    printf("  - Accelerometer ranges: ±2g, ±4g, ±8g, ±16g\n");
    printf("  - Gyroscope ranges: ±250°/s, ±500°/s, ±1000°/s, ±2000°/s\n");
    printf("  - Temperature range validation\n");
    printf("  - Range switching consistency\n");
    printf("  - Data integrity and noise analysis\n");
    printf("\n");
}

/**
 * Main function
 */
int main(int argc, char *argv[]) {
    /* Parse command line arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--verbose") == 0) {
            g_verbose = 1;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            print_usage(argv[0]);
            return 1;
        }
    }
    
    /* Set up signal handlers */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    /* Initialize test statistics */
    struct test_stats stats = {0};
    gettimeofday(&stats.start_time, NULL);
    
    printf(COLOR_BLUE "MPU-6050 Range Validation Test Suite" COLOR_RESET "\n");
    printf(COLOR_BLUE "Device: %s" COLOR_RESET "\n", DEVICE_PATH);
    printf(COLOR_BLUE "Started: %s" COLOR_RESET, ctime(&stats.start_time.tv_sec));
    printf("\n");
    
    /* Open device */
    int fd = open(DEVICE_PATH, O_RDWR);
    if (fd < 0) {
        printf(COLOR_RED "Failed to open device %s: %s" COLOR_RESET "\n", 
               DEVICE_PATH, strerror(errno));
        return 1;
    }
    
    verbose_log("Device opened successfully");
    
    /* Test all accelerometer ranges */
    print_test_header("Accelerometer Range Validation");
    for (int i = 0; i < NUM_ACCEL_RANGES && g_running; i++) {
        struct range_test_result result;
        int passed = test_accelerometer_range(fd, &accel_ranges[i], &result);
        
        char details[256];
        snprintf(details, sizeof(details), 
                 "Samples: %d, Violations: %d range + %d stability", 
                 result.samples_collected, result.range_violations, result.stability_violations);
        
        print_test_result(accel_ranges[i].name, passed, details);
        
        stats.total_tests++;
        if (passed) {
            stats.passed_tests++;
        } else {
            stats.failed_tests++;
        }
    }
    
    /* Test all gyroscope ranges */
    print_test_header("Gyroscope Range Validation");
    for (int i = 0; i < NUM_GYRO_RANGES && g_running; i++) {
        struct range_test_result result;
        int passed = test_gyroscope_range(fd, &gyro_ranges[i], &result);
        
        char details[256];
        snprintf(details, sizeof(details), 
                 "Samples: %d, Violations: %d range + %d stability", 
                 result.samples_collected, result.range_violations, result.stability_violations);
        
        print_test_result(gyro_ranges[i].name, passed, details);
        
        stats.total_tests++;
        if (passed) {
            stats.passed_tests++;
        } else {
            stats.failed_tests++;
        }
    }
    
    /* Test temperature range */
    if (g_running) {
        int temp_passed = test_temperature_range(fd);
        stats.total_tests++;
        if (temp_passed) {
            stats.passed_tests++;
        } else {
            stats.failed_tests++;
        }
    }
    
    /* Test range switching consistency */
    if (g_running) {
        int switch_tests_passed = test_range_switching(fd);
        int expected_switch_tests = (NUM_ACCEL_RANGES - 1) + (NUM_GYRO_RANGES - 1);
        
        stats.total_tests += expected_switch_tests;
        stats.passed_tests += switch_tests_passed;
        stats.failed_tests += (expected_switch_tests - switch_tests_passed);
    }
    
    /* Close device */
    close(fd);
    verbose_log("Device closed");
    
    /* Finalize statistics */
    gettimeofday(&stats.end_time, NULL);
    stats.test_duration = (stats.end_time.tv_sec - stats.start_time.tv_sec) +
                         (stats.end_time.tv_usec - stats.start_time.tv_usec) / 1000000.0;
    
    /* Print comprehensive summary */
    print_test_summary(&stats);
    
    /* Return appropriate exit code */
    return (stats.failed_tests == 0) ? 0 : 1;
}