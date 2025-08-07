/**
 * @file performance_monitor.h
 * @brief Performance measurement utilities for MPU-6050 driver testing
 * 
 * This file provides comprehensive performance monitoring and benchmarking
 * capabilities for the MPU-6050 kernel driver testing suite.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#ifndef PERFORMANCE_MONITOR_H
#define PERFORMANCE_MONITOR_H

#include <stdint.h>
#include <sys/time.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MAX_MEASUREMENTS 1000
#define MAX_OPERATION_NAME 64

/* Performance timer structure */
struct performance_timer {
    char operation_name[MAX_OPERATION_NAME];
    uint64_t start_time;
    int is_running;
};

/* Performance measurement record */
struct performance_measurement {
    char operation_name[MAX_OPERATION_NAME];
    uint64_t start_time;
    uint64_t end_time;
    uint64_t duration_us;
    int success;
    int error_code;
};

/* Cumulative performance statistics */
struct performance_stats {
    uint64_t total_operations;
    uint64_t successful_operations;
    uint64_t failed_operations;
    uint64_t total_time_us;
    uint64_t min_duration_us;
    uint64_t max_duration_us;
    uint64_t average_duration_us;
    uint64_t session_duration_us;
    double success_rate;
    double operations_per_second;
};

/* Memory usage information */
struct memory_usage {
    unsigned long rss_kb;        /* Resident Set Size */
    unsigned long vsize_kb;      /* Virtual Memory Size */
    unsigned long peak_rss_kb;   /* Peak RSS */
    unsigned long peak_vsize_kb; /* Peak Virtual Memory */
};

/* Benchmark operation types */
enum benchmark_operation {
    BENCHMARK_READ = 0,
    BENCHMARK_WRITE = 1,
    BENCHMARK_IOCTL = 2
};

/* I/O benchmark result */
struct io_benchmark_result {
    char device_path[256];
    enum benchmark_operation operation;
    int num_iterations;
    int successful_operations;
    int failed_operations;
    uint64_t total_duration_us;
    uint64_t average_duration_us;
    unsigned long bytes_transferred;
    double success_rate;
    double operations_per_second;
    double bytes_per_second;
    int error_code;
    char error_message[256];
};

/* Core monitoring functions */
void perf_monitor_init(void);
void perf_monitor_cleanup(void);
void perf_monitor_enable(void);
void perf_monitor_disable(void);

/* Timer functions */
struct performance_timer perf_timer_start(const char *operation_name);
struct performance_measurement perf_timer_stop(struct performance_timer *timer);

/* Measurement recording and retrieval */
void perf_monitor_record_measurement(const struct performance_measurement *measurement);
struct performance_stats perf_monitor_get_stats(void);
void perf_monitor_reset_stats(void);

/* Reporting functions */
void perf_monitor_print_stats(void);
void perf_monitor_print_history(int max_entries);
void perf_monitor_generate_report(const char *filename);

/* Benchmarking functions */
struct io_benchmark_result perf_monitor_benchmark_io(const char *device_path, 
                                                   int num_iterations,
                                                   enum benchmark_operation operation);
void perf_monitor_print_io_benchmark(const struct io_benchmark_result *result);

/* Memory monitoring */
struct memory_usage perf_monitor_get_memory_usage(void);
void perf_monitor_print_memory_usage(void);

/* Convenience macros */

/**
 * Time a code block and record the measurement
 */
#define PERF_TIME_BLOCK(name, block) \
    do { \
        struct performance_timer timer = perf_timer_start(name); \
        { block; } \
        struct performance_measurement m = perf_timer_stop(&timer); \
        printf("Operation '%s' took %.3f ms\n", name, m.duration_us / 1000.0); \
    } while(0)

/**
 * Time a function call and record the measurement
 */
#define PERF_TIME_CALL(name, call) \
    do { \
        struct performance_timer timer = perf_timer_start(name); \
        call; \
        struct performance_measurement m = perf_timer_stop(&timer); \
        printf("Call '%s' took %.3f ms\n", name, m.duration_us / 1000.0); \
    } while(0)

/**
 * Assert that an operation completes within a specified time
 */
#define PERF_ASSERT_TIME_UNDER(name, max_ms, call) \
    do { \
        struct performance_timer timer = perf_timer_start(name); \
        call; \
        struct performance_measurement m = perf_timer_stop(&timer); \
        double actual_ms = m.duration_us / 1000.0; \
        if (actual_ms > max_ms) { \
            printf("PERFORMANCE FAIL: '%s' took %.3f ms (limit: %.3f ms)\n", \
                   name, actual_ms, max_ms); \
        } else { \
            printf("PERFORMANCE PASS: '%s' took %.3f ms\n", name, actual_ms); \
        } \
    } while(0)

/**
 * Start a performance session for a test
 */
#define PERF_SESSION_START() \
    do { \
        perf_monitor_init(); \
        printf("Performance monitoring started\n"); \
    } while(0)

/**
 * End a performance session and print summary
 */
#define PERF_SESSION_END() \
    do { \
        perf_monitor_print_stats(); \
        perf_monitor_cleanup(); \
        printf("Performance monitoring ended\n"); \
    } while(0)

/**
 * Simple performance benchmark macro
 */
#define PERF_BENCHMARK(name, iterations, operation) \
    do { \
        printf("Running benchmark: %s (%d iterations)\n", name, iterations); \
        struct performance_timer timer = perf_timer_start(name); \
        int success_count = 0; \
        for (int i = 0; i < iterations; i++) { \
            if (operation) success_count++; \
        } \
        struct performance_measurement m = perf_timer_stop(&timer); \
        double ops_per_sec = (double)success_count * 1000000.0 / m.duration_us; \
        printf("Benchmark '%s': %.2f ops/sec (%.2f%% success)\n", \
               name, ops_per_sec, (double)success_count * 100.0 / iterations); \
    } while(0)

/* Statistical analysis functions */

/**
 * Calculate standard deviation of measurement durations
 */
double perf_monitor_calculate_stddev(void);

/**
 * Calculate percentile of measurement durations
 */
uint64_t perf_monitor_calculate_percentile(double percentile);

/**
 * Detect performance anomalies (measurements outside normal range)
 */
int perf_monitor_detect_anomalies(double threshold_factor);

#ifdef __cplusplus
}
#endif

#endif /* PERFORMANCE_MONITOR_H */