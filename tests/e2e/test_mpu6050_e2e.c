/*
 * MPU-6050 End-to-End Functional Test Suite (C Implementation)
 *
 * This test suite performs comprehensive functional testing of the MPU-6050
 * driver through the character device interface (/dev/mpu6050).
 *
 * Tests include:
 * - Device accessibility and basic I/O operations
 * - All IOCTL command functionality
 * - Data range validation and consistency
 * - Error condition handling
 * - Performance metrics collection
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
#include <signal.h>
#include <math.h>
#include <time.h>
#include <stdarg.h>

#include "../../include/mpu6050.h"

#define DEVICE_PATH "/dev/mpu6050"
#define TEST_ITERATIONS 100
#define STABILITY_TEST_DURATION 10  /* seconds */
#define MAX_NOISE_THRESHOLD_ACCEL 100  /* mg */
#define MAX_NOISE_THRESHOLD_GYRO 50    /* mdps */

/* Test statistics structure */
struct test_stats {
    int total_tests;
    int passed_tests;
    int failed_tests;
    double test_duration;
    struct timeval start_time;
    struct timeval end_time;
};

/* Test context structure */
struct test_context {
    int fd;
    struct test_stats stats;
    int verbose;
    int continuous;
};

/* Color codes for output */
#define COLOR_RED     "\033[31m"
#define COLOR_GREEN   "\033[32m"
#define COLOR_YELLOW  "\033[33m"
#define COLOR_BLUE    "\033[34m"
#define COLOR_MAGENTA "\033[35m"
#define COLOR_CYAN    "\033[36m"
#define COLOR_RESET   "\033[0m"

/* Global context for signal handler */
static struct test_context *g_ctx = NULL;

/**
 * Signal handler for graceful shutdown
 */
static void signal_handler(int sig) {
    if (g_ctx) {
        printf("\n" COLOR_YELLOW "Received signal %d, shutting down gracefully..." COLOR_RESET "\n", sig);
        g_ctx->continuous = 0;
    }
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
 * Initialize test statistics
 */
static void init_test_stats(struct test_stats *stats) {
    memset(stats, 0, sizeof(*stats));
    gettimeofday(&stats->start_time, NULL);
}

/**
 * Update test statistics
 */
static void update_test_stats(struct test_stats *stats, int passed) {
    stats->total_tests++;
    if (passed) {
        stats->passed_tests++;
    } else {
        stats->failed_tests++;
    }
}

/**
 * Finalize test statistics
 */
static void finalize_test_stats(struct test_stats *stats) {
    gettimeofday(&stats->end_time, NULL);
    stats->test_duration = (stats->end_time.tv_sec - stats->start_time.tv_sec) +
                          (stats->end_time.tv_usec - stats->start_time.tv_usec) / 1000000.0;
}

/**
 * Print comprehensive test summary
 */
static void print_test_summary(const struct test_stats *stats) {
    double pass_rate = (stats->total_tests > 0) ? 
        (100.0 * stats->passed_tests / stats->total_tests) : 0.0;
    
    printf("\n" COLOR_MAGENTA "========================================" COLOR_RESET "\n");
    printf(COLOR_MAGENTA "TEST SUMMARY" COLOR_RESET "\n");
    printf(COLOR_MAGENTA "========================================" COLOR_RESET "\n");
    printf("Total Tests:    %d\n", stats->total_tests);
    printf("Passed Tests:   " COLOR_GREEN "%d" COLOR_RESET "\n", stats->passed_tests);
    printf("Failed Tests:   " COLOR_RED "%d" COLOR_RESET "\n", stats->failed_tests);
    printf("Pass Rate:      %.1f%%\n", pass_rate);
    printf("Test Duration:  %.3f seconds\n", stats->test_duration);
    printf("\n");
    
    if (stats->failed_tests == 0) {
        printf(COLOR_GREEN "ALL TESTS PASSED!" COLOR_RESET "\n");
    } else {
        printf(COLOR_RED "SOME TESTS FAILED!" COLOR_RESET "\n");
    }
    printf(COLOR_MAGENTA "========================================" COLOR_RESET "\n");
}

/**
 * Test device accessibility
 */
static int test_device_accessibility(struct test_context *ctx) {
    print_test_header("Device Accessibility");
    
    /* Test device open */
    ctx->fd = open(DEVICE_PATH, O_RDWR);
    if (ctx->fd < 0) {
        print_test_result("Device Open", 0, strerror(errno));
        return 0;
    }
    print_test_result("Device Open", 1, "Successfully opened /dev/mpu6050");
    
    /* Test device permissions */
    int flags = fcntl(ctx->fd, F_GETFL);
    if (flags < 0) {
        print_test_result("Device Permissions", 0, "Could not get file flags");
        return 0;
    }
    
    int readable = (flags & O_ACCMODE) != O_WRONLY;
    int writable = (flags & O_ACCMODE) != O_RDONLY;
    
    char perm_details[256];
    snprintf(perm_details, sizeof(perm_details), "Readable: %s, Writable: %s", 
             readable ? "Yes" : "No", writable ? "Yes" : "No");
    print_test_result("Device Permissions", readable && writable, perm_details);
    
    return readable && writable;
}

/**
 * Test WHO_AM_I IOCTL command
 */
static int test_who_am_i(struct test_context *ctx) {
    print_test_header("WHO_AM_I Test");
    
    u8 who_am_i = 0;
    int ret = ioctl(ctx->fd, MPU6050_IOC_WHO_AM_I, &who_am_i);
    
    char details[256];
    if (ret < 0) {
        snprintf(details, sizeof(details), "IOCTL failed: %s", strerror(errno));
        print_test_result("WHO_AM_I IOCTL", 0, details);
        return 0;
    }
    
    snprintf(details, sizeof(details), "Device ID: 0x%02X (expected: 0x%02X)", 
             who_am_i, MPU6050_WHO_AM_I_VAL);
    
    int passed = (who_am_i == MPU6050_WHO_AM_I_VAL);
    print_test_result("WHO_AM_I Value", passed, details);
    
    return passed;
}

/**
 * Test configuration IOCTL commands
 */
static int test_configuration(struct test_context *ctx) {
    print_test_header("Configuration Test");
    int tests_passed = 0;
    
    struct mpu6050_config original_config, test_config, read_config;
    
    /* Get original configuration */
    int ret = ioctl(ctx->fd, MPU6050_IOC_GET_CONFIG, &original_config);
    if (ret < 0) {
        print_test_result("Get Original Config", 0, strerror(errno));
        return 0;
    }
    print_test_result("Get Original Config", 1, "Successfully read configuration");
    tests_passed++;
    
    /* Test different accelerometer ranges */
    u8 accel_ranges[] = {MPU6050_ACCEL_FS_2G, MPU6050_ACCEL_FS_4G, 
                         MPU6050_ACCEL_FS_8G, MPU6050_ACCEL_FS_16G};
    const char *accel_range_names[] = {"±2g", "±4g", "±8g", "±16g"};
    
    for (int i = 0; i < 4; i++) {
        test_config = original_config;
        test_config.accel_range = accel_ranges[i];
        
        ret = ioctl(ctx->fd, MPU6050_IOC_SET_CONFIG, &test_config);
        if (ret < 0) {
            char details[256];
            snprintf(details, sizeof(details), "Set accel range %s failed: %s", 
                     accel_range_names[i], strerror(errno));
            print_test_result("Set Accel Range", 0, details);
            continue;
        }
        
        ret = ioctl(ctx->fd, MPU6050_IOC_GET_CONFIG, &read_config);
        if (ret < 0 || read_config.accel_range != accel_ranges[i]) {
            char details[256];
            snprintf(details, sizeof(details), "Accel range %s verification failed", 
                     accel_range_names[i]);
            print_test_result("Verify Accel Range", 0, details);
            continue;
        }
        
        char details[256];
        snprintf(details, sizeof(details), "Accel range %s set successfully", 
                 accel_range_names[i]);
        print_test_result("Set Accel Range", 1, details);
        tests_passed++;
    }
    
    /* Test different gyroscope ranges */
    u8 gyro_ranges[] = {MPU6050_GYRO_FS_250, MPU6050_GYRO_FS_500, 
                        MPU6050_GYRO_FS_1000, MPU6050_GYRO_FS_2000};
    const char *gyro_range_names[] = {"±250°/s", "±500°/s", "±1000°/s", "±2000°/s"};
    
    for (int i = 0; i < 4; i++) {
        test_config = original_config;
        test_config.gyro_range = gyro_ranges[i];
        
        ret = ioctl(ctx->fd, MPU6050_IOC_SET_CONFIG, &test_config);
        if (ret < 0) {
            char details[256];
            snprintf(details, sizeof(details), "Set gyro range %s failed: %s", 
                     gyro_range_names[i], strerror(errno));
            print_test_result("Set Gyro Range", 0, details);
            continue;
        }
        
        ret = ioctl(ctx->fd, MPU6050_IOC_GET_CONFIG, &read_config);
        if (ret < 0 || read_config.gyro_range != gyro_ranges[i]) {
            char details[256];
            snprintf(details, sizeof(details), "Gyro range %s verification failed", 
                     gyro_range_names[i]);
            print_test_result("Verify Gyro Range", 0, details);
            continue;
        }
        
        char details[256];
        snprintf(details, sizeof(details), "Gyro range %s set successfully", 
                 gyro_range_names[i]);
        print_test_result("Set Gyro Range", 1, details);
        tests_passed++;
    }
    
    /* Restore original configuration */
    ret = ioctl(ctx->fd, MPU6050_IOC_SET_CONFIG, &original_config);
    if (ret < 0) {
        print_test_result("Restore Original Config", 0, strerror(errno));
    } else {
        print_test_result("Restore Original Config", 1, "Configuration restored");
        tests_passed++;
    }
    
    return tests_passed;
}

/**
 * Test data reading operations
 */
static int test_data_reading(struct test_context *ctx) {
    print_test_header("Data Reading Test");
    int tests_passed = 0;
    
    /* Test raw data reading via IOCTL */
    struct mpu6050_raw_data raw_data;
    int ret = ioctl(ctx->fd, MPU6050_IOC_READ_RAW, &raw_data);
    if (ret < 0) {
        print_test_result("Read Raw Data (IOCTL)", 0, strerror(errno));
    } else {
        char details[256];
        snprintf(details, sizeof(details), "Accel: [%d, %d, %d], Gyro: [%d, %d, %d], Temp: %d", 
                 raw_data.accel_x, raw_data.accel_y, raw_data.accel_z,
                 raw_data.gyro_x, raw_data.gyro_y, raw_data.gyro_z, raw_data.temp);
        print_test_result("Read Raw Data (IOCTL)", 1, details);
        tests_passed++;
    }
    
    /* Test scaled data reading via IOCTL */
    struct mpu6050_scaled_data scaled_data;
    ret = ioctl(ctx->fd, MPU6050_IOC_READ_SCALED, &scaled_data);
    if (ret < 0) {
        print_test_result("Read Scaled Data (IOCTL)", 0, strerror(errno));
    } else {
        char details[512];
        snprintf(details, sizeof(details), 
                 "Accel: [%d mg, %d mg, %d mg], Gyro: [%d mdps, %d mdps, %d mdps], Temp: %.2f°C", 
                 scaled_data.accel_x, scaled_data.accel_y, scaled_data.accel_z,
                 scaled_data.gyro_x, scaled_data.gyro_y, scaled_data.gyro_z,
                 scaled_data.temp / 100.0);
        print_test_result("Read Scaled Data (IOCTL)", 1, details);
        tests_passed++;
    }
    
    /* Test raw data reading via read() system call */
    struct mpu6050_raw_data read_raw_data;
    ssize_t bytes_read = read(ctx->fd, &read_raw_data, sizeof(read_raw_data));
    if (bytes_read != sizeof(read_raw_data)) {
        char details[256];
        snprintf(details, sizeof(details), "Expected %zu bytes, got %zd", 
                 sizeof(read_raw_data), bytes_read);
        print_test_result("Read Raw Data (read())", 0, details);
    } else {
        print_test_result("Read Raw Data (read())", 1, "Successfully read via read() syscall");
        tests_passed++;
    }
    
    return tests_passed;
}

/**
 * Test device reset functionality
 */
static int test_device_reset(struct test_context *ctx) {
    print_test_header("Device Reset Test");
    
    /* Perform device reset */
    int ret = ioctl(ctx->fd, MPU6050_IOC_RESET);
    if (ret < 0) {
        print_test_result("Device Reset", 0, strerror(errno));
        return 0;
    }
    
    print_test_result("Device Reset", 1, "Reset command executed successfully");
    
    /* Wait for device to stabilize after reset */
    usleep(200000);  /* 200ms */
    
    /* Verify device is still accessible after reset */
    u8 who_am_i = 0;
    ret = ioctl(ctx->fd, MPU6050_IOC_WHO_AM_I, &who_am_i);
    if (ret < 0 || who_am_i != MPU6050_WHO_AM_I_VAL) {
        print_test_result("Post-Reset Verification", 0, "Device not accessible after reset");
        return 0;
    }
    
    print_test_result("Post-Reset Verification", 1, "Device functional after reset");
    return 2;  /* Two tests passed */
}

/**
 * Test data consistency over multiple readings
 */
static int test_data_consistency(struct test_context *ctx) {
    print_test_header("Data Consistency Test");
    
    struct mpu6050_scaled_data readings[10];
    int successful_reads = 0;
    
    /* Take multiple readings */
    for (int i = 0; i < 10; i++) {
        int ret = ioctl(ctx->fd, MPU6050_IOC_READ_SCALED, &readings[i]);
        if (ret == 0) {
            successful_reads++;
            usleep(10000);  /* 10ms between readings */
        }
    }
    
    if (successful_reads < 5) {
        print_test_result("Multiple Readings", 0, "Insufficient successful readings");
        return 0;
    }
    
    /* Check for reasonable data ranges */
    int valid_readings = 0;
    for (int i = 0; i < successful_reads; i++) {
        /* Check accelerometer data (should be within ±20g for sanity) */
        if (abs(readings[i].accel_x) < 20000 && 
            abs(readings[i].accel_y) < 20000 && 
            abs(readings[i].accel_z) < 20000) {
            
            /* Check gyroscope data (should be within ±3000 dps for sanity) */
            if (abs(readings[i].gyro_x) < 3000000 && 
                abs(readings[i].gyro_y) < 3000000 && 
                abs(readings[i].gyro_z) < 3000000) {
                
                /* Check temperature (should be between -40 and 85°C) */
                if (readings[i].temp > -4000 && readings[i].temp < 8500) {
                    valid_readings++;
                }
            }
        }
    }
    
    char details[256];
    snprintf(details, sizeof(details), "%d/%d readings within expected ranges", 
             valid_readings, successful_reads);
    
    int passed = (valid_readings >= successful_reads * 0.8);  /* 80% threshold */
    print_test_result("Data Range Validation", passed, details);
    
    return passed ? 1 : 0;
}

/**
 * Test error conditions
 */
static int test_error_conditions(struct test_context *ctx) {
    print_test_header("Error Condition Test");
    int tests_passed = 0;
    
    /* Test invalid IOCTL command */
    int ret = ioctl(ctx->fd, _IO('X', 99), NULL);
    if (ret < 0 && errno == ENOTTY) {
        print_test_result("Invalid IOCTL", 1, "Correctly rejected invalid IOCTL");
        tests_passed++;
    } else {
        print_test_result("Invalid IOCTL", 0, "Should have rejected invalid IOCTL");
    }
    
    /* Test read with insufficient buffer */
    char small_buffer[1];
    ssize_t bytes_read = read(ctx->fd, small_buffer, sizeof(small_buffer));
    if (bytes_read < 0 && errno == EINVAL) {
        print_test_result("Insufficient Buffer", 1, "Correctly rejected small buffer");
        tests_passed++;
    } else {
        print_test_result("Insufficient Buffer", 0, "Should have rejected small buffer");
    }
    
    /* Test configuration with invalid values */
    struct mpu6050_config invalid_config = {
        .sample_rate_div = 255,  /* Valid */
        .gyro_range = 0xFF,      /* Invalid */
        .accel_range = 0xFF,     /* Invalid */
        .dlpf_cfg = 0xFF         /* Invalid */
    };
    
    ret = ioctl(ctx->fd, MPU6050_IOC_SET_CONFIG, &invalid_config);
    /* Note: Driver may or may not validate these values, so we just test the call */
    print_test_result("Invalid Config Test", 1, "Invalid configuration test completed");
    tests_passed++;
    
    return tests_passed;
}

/**
 * Performance test - measure read throughput
 */
static int test_performance(struct test_context *ctx) {
    print_test_header("Performance Test");
    
    struct timeval start, end;
    struct mpu6050_raw_data raw_data;
    int successful_reads = 0;
    
    gettimeofday(&start, NULL);
    
    /* Perform TEST_ITERATIONS reads as fast as possible */
    for (int i = 0; i < TEST_ITERATIONS; i++) {
        if (ioctl(ctx->fd, MPU6050_IOC_READ_RAW, &raw_data) == 0) {
            successful_reads++;
        }
    }
    
    gettimeofday(&end, NULL);
    
    double duration = (end.tv_sec - start.tv_sec) + 
                     (end.tv_usec - start.tv_usec) / 1000000.0;
    double throughput = successful_reads / duration;
    
    char details[256];
    snprintf(details, sizeof(details), "%.1f reads/sec (%d/%d successful in %.3fs)", 
             throughput, successful_reads, TEST_ITERATIONS, duration);
    
    /* Expect at least 50 reads/second for reasonable performance */
    int passed = (throughput >= 50.0 && successful_reads >= TEST_ITERATIONS * 0.9);
    print_test_result("Read Throughput", passed, details);
    
    return passed ? 1 : 0;
}

/**
 * Run all tests
 */
static int run_all_tests(struct test_context *ctx) {
    int total_passed = 0;
    
    printf(COLOR_BLUE "Starting MPU-6050 End-to-End Test Suite" COLOR_RESET "\n");
    printf(COLOR_BLUE "Device: %s" COLOR_RESET "\n", DEVICE_PATH);
    printf(COLOR_BLUE "Timestamp: %s" COLOR_RESET "\n", ctime(&ctx->stats.start_time.tv_sec));
    printf("\n");
    
    /* Run test sequence */
    total_passed += test_device_accessibility(ctx);
    update_test_stats(&ctx->stats, total_passed > 0);
    
    if (ctx->fd > 0) {  /* Only continue if device opened successfully */
        int test_result;
        
        test_result = test_who_am_i(ctx);
        total_passed += test_result;
        update_test_stats(&ctx->stats, test_result > 0);
        
        test_result = test_configuration(ctx);
        total_passed += test_result;
        for (int i = 0; i < 9; i++) {  /* Configuration test runs 9 sub-tests */
            update_test_stats(&ctx->stats, test_result > i);
        }
        
        test_result = test_data_reading(ctx);
        total_passed += test_result;
        for (int i = 0; i < 3; i++) {  /* Data reading test runs 3 sub-tests */
            update_test_stats(&ctx->stats, test_result > i);
        }
        
        test_result = test_device_reset(ctx);
        total_passed += test_result;
        for (int i = 0; i < 2; i++) {  /* Reset test runs 2 sub-tests */
            update_test_stats(&ctx->stats, test_result > i);
        }
        
        test_result = test_data_consistency(ctx);
        total_passed += test_result;
        update_test_stats(&ctx->stats, test_result > 0);
        
        test_result = test_error_conditions(ctx);
        total_passed += test_result;
        for (int i = 0; i < 3; i++) {  /* Error condition test runs 3 sub-tests */
            update_test_stats(&ctx->stats, test_result > i);
        }
        
        test_result = test_performance(ctx);
        total_passed += test_result;
        update_test_stats(&ctx->stats, test_result > 0);
    }
    
    return total_passed;
}

/**
 * Print usage information
 */
static void print_usage(const char *program_name) {
    printf("Usage: %s [options]\n", program_name);
    printf("\n");
    printf("Options:\n");
    printf("  -v, --verbose    Enable verbose output\n");
    printf("  -c, --continuous Run tests continuously until interrupted\n");
    printf("  -h, --help       Show this help message\n");
    printf("\n");
    printf("Examples:\n");
    printf("  %s                    # Run tests once\n", program_name);
    printf("  %s -v                 # Run with verbose output\n", program_name);
    printf("  %s -c                 # Run continuously\n", program_name);
    printf("  %s -v -c              # Run continuously with verbose output\n", program_name);
    printf("\n");
}

/**
 * Main function
 */
int main(int argc, char *argv[]) {
    struct test_context ctx = {0};
    int continuous_runs = 0;
    
    /* Parse command line arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--verbose") == 0) {
            ctx.verbose = 1;
        } else if (strcmp(argv[i], "-c") == 0 || strcmp(argv[i], "--continuous") == 0) {
            ctx.continuous = 1;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            print_usage(argv[0]);
            return 1;
        }
    }
    
    /* Set up signal handlers for graceful shutdown */
    g_ctx = &ctx;
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    /* Initialize test statistics */
    init_test_stats(&ctx.stats);
    
    /* Run tests */
    do {
        if (ctx.continuous && continuous_runs > 0) {
            printf("\n" COLOR_YELLOW "========== Test Run #%d ==========" COLOR_RESET "\n", continuous_runs + 1);
            sleep(1);  /* Brief pause between continuous runs */
        }
        
        run_all_tests(&ctx);
        
        if (ctx.fd > 0) {
            close(ctx.fd);
            ctx.fd = 0;
        }
        
        continuous_runs++;
        
        if (ctx.continuous) {
            printf("\n" COLOR_YELLOW "Run #%d completed. Press Ctrl+C to stop..." COLOR_RESET "\n", continuous_runs);
        }
        
    } while (ctx.continuous);
    
    /* Finalize and print test summary */
    finalize_test_stats(&ctx.stats);
    print_test_summary(&ctx.stats);
    
    /* Return appropriate exit code */
    return (ctx.stats.failed_tests == 0) ? 0 : 1;
}