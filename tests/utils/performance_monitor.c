/**
 * @file performance_monitor.c
 * @brief Performance measurement utilities for MPU-6050 driver testing
 * 
 * This file provides comprehensive performance monitoring and benchmarking
 * capabilities for the MPU-6050 kernel driver testing suite.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <math.h>

#include "performance_monitor.h"

/* Global performance monitoring state */
static struct {
    int monitoring_enabled;
    struct timeval session_start;
    struct performance_stats cumulative_stats;
    struct performance_measurement measurements[MAX_MEASUREMENTS];
    int measurement_count;
    int current_measurement_index;
} perf_state = {0};

/* Initialize performance monitoring */
void perf_monitor_init(void)
{
    memset(&perf_state, 0, sizeof(perf_state));
    gettimeofday(&perf_state.session_start, NULL);
    perf_state.monitoring_enabled = 1;
}

/* Cleanup performance monitoring */
void perf_monitor_cleanup(void)
{
    perf_state.monitoring_enabled = 0;
    memset(&perf_state, 0, sizeof(perf_state));
}

/* Enable/disable monitoring */
void perf_monitor_enable(void)
{
    perf_state.monitoring_enabled = 1;
}

void perf_monitor_disable(void)
{
    perf_state.monitoring_enabled = 0;
}

/* Get current time in microseconds */
static uint64_t get_time_us(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000000ULL + (uint64_t)tv.tv_usec;
}

/* Start a performance measurement */
struct performance_timer perf_timer_start(const char *operation_name)
{
    struct performance_timer timer = {0};
    
    if (operation_name) {
        strncpy(timer.operation_name, operation_name, sizeof(timer.operation_name) - 1);
        timer.operation_name[sizeof(timer.operation_name) - 1] = '\0';
    }
    
    timer.start_time = get_time_us();
    timer.is_running = 1;
    
    return timer;
}

/* Stop a performance measurement and record results */
struct performance_measurement perf_timer_stop(struct performance_timer *timer)
{
    struct performance_measurement measurement = {0};
    
    if (!timer || !timer->is_running) {
        return measurement;
    }
    
    uint64_t end_time = get_time_us();
    
    strncpy(measurement.operation_name, timer->operation_name, 
            sizeof(measurement.operation_name) - 1);
    measurement.operation_name[sizeof(measurement.operation_name) - 1] = '\0';
    
    measurement.start_time = timer->start_time;
    measurement.end_time = end_time;
    measurement.duration_us = end_time - timer->start_time;
    measurement.success = 1;  /* Default to success, can be overridden */
    
    timer->is_running = 0;
    
    /* Record the measurement if monitoring is enabled */
    if (perf_state.monitoring_enabled) {
        perf_monitor_record_measurement(&measurement);
    }
    
    return measurement;
}

/* Record a performance measurement */
void perf_monitor_record_measurement(const struct performance_measurement *measurement)
{
    if (!perf_state.monitoring_enabled || !measurement) {
        return;
    }
    
    /* Store measurement in circular buffer */
    if (perf_state.measurement_count < MAX_MEASUREMENTS) {
        perf_state.measurements[perf_state.measurement_count] = *measurement;
        perf_state.measurement_count++;
    } else {
        /* Circular buffer - overwrite oldest measurement */
        perf_state.measurements[perf_state.current_measurement_index] = *measurement;
        perf_state.current_measurement_index = 
            (perf_state.current_measurement_index + 1) % MAX_MEASUREMENTS;
    }
    
    /* Update cumulative statistics */
    perf_state.cumulative_stats.total_operations++;
    perf_state.cumulative_stats.total_time_us += measurement->duration_us;
    
    if (measurement->success) {
        perf_state.cumulative_stats.successful_operations++;
    } else {
        perf_state.cumulative_stats.failed_operations++;
    }
    
    /* Update min/max durations */
    if (perf_state.cumulative_stats.min_duration_us == 0 || 
        measurement->duration_us < perf_state.cumulative_stats.min_duration_us) {
        perf_state.cumulative_stats.min_duration_us = measurement->duration_us;
    }
    
    if (measurement->duration_us > perf_state.cumulative_stats.max_duration_us) {
        perf_state.cumulative_stats.max_duration_us = measurement->duration_us;
    }
}

/* Get current performance statistics */
struct performance_stats perf_monitor_get_stats(void)
{
    struct performance_stats stats = perf_state.cumulative_stats;
    
    /* Calculate derived statistics */
    if (stats.total_operations > 0) {
        stats.average_duration_us = stats.total_time_us / stats.total_operations;
        stats.success_rate = (double)stats.successful_operations / stats.total_operations;
    }
    
    /* Calculate total session time */
    struct timeval now;
    gettimeofday(&now, NULL);
    stats.session_duration_us = (now.tv_sec - perf_state.session_start.tv_sec) * 1000000ULL +
                               (now.tv_usec - perf_state.session_start.tv_usec);
    
    /* Calculate throughput */
    if (stats.session_duration_us > 0) {
        stats.operations_per_second = (double)stats.total_operations * 1000000.0 / stats.session_duration_us;
    }
    
    return stats;
}

/* Reset performance statistics */
void perf_monitor_reset_stats(void)
{
    memset(&perf_state.cumulative_stats, 0, sizeof(perf_state.cumulative_stats));
    perf_state.measurement_count = 0;
    perf_state.current_measurement_index = 0;
    gettimeofday(&perf_state.session_start, NULL);
}

/* Print performance statistics */
void perf_monitor_print_stats(void)
{
    struct performance_stats stats = perf_monitor_get_stats();
    
    printf("\n=== Performance Statistics ===\n");
    printf("Session Duration: %.3f seconds\n", stats.session_duration_us / 1000000.0);
    printf("Total Operations: %lu\n", stats.total_operations);
    printf("Successful Operations: %lu\n", stats.successful_operations);
    printf("Failed Operations: %lu\n", stats.failed_operations);
    printf("Success Rate: %.2f%%\n", stats.success_rate * 100.0);
    printf("Operations per Second: %.2f\n", stats.operations_per_second);
    printf("\nTiming Statistics:\n");
    printf("  Total Time: %.3f seconds\n", stats.total_time_us / 1000000.0);
    printf("  Average Duration: %.3f ms\n", stats.average_duration_us / 1000.0);
    printf("  Min Duration: %.3f ms\n", stats.min_duration_us / 1000.0);
    printf("  Max Duration: %.3f ms\n", stats.max_duration_us / 1000.0);
    printf("==============================\n\n");
}

/* Print detailed measurement history */
void perf_monitor_print_history(int max_entries)
{
    int entries_to_print = (max_entries > 0) ? 
                          (max_entries < perf_state.measurement_count ? max_entries : perf_state.measurement_count) :
                          perf_state.measurement_count;
    
    printf("\n=== Performance Measurement History ===\n");
    printf("Operation Name                    Duration (ms)  Success  Timestamp\n");
    printf("----------------------------------------------------------------------\n");
    
    int start_index = (perf_state.measurement_count >= MAX_MEASUREMENTS) ?
                     perf_state.current_measurement_index : 0;
    
    for (int i = 0; i < entries_to_print; i++) {
        int index = (start_index + i) % MAX_MEASUREMENTS;
        if (index >= perf_state.measurement_count && perf_state.measurement_count < MAX_MEASUREMENTS) {
            break;
        }
        
        struct performance_measurement *m = &perf_state.measurements[index];
        double duration_ms = m->duration_us / 1000.0;
        uint64_t timestamp_ms = m->start_time / 1000;
        
        printf("%-30s %12.3f     %s  %llu\n", 
               m->operation_name, 
               duration_ms,
               m->success ? "Yes" : "No",
               timestamp_ms);
    }
    
    printf("======================================\n\n");
}

/* Benchmark I/O operations */
struct io_benchmark_result perf_monitor_benchmark_io(const char *device_path, 
                                                   int num_iterations,
                                                   enum benchmark_operation operation)
{
    struct io_benchmark_result result = {0};
    strncpy(result.device_path, device_path, sizeof(result.device_path) - 1);
    result.operation = operation;
    result.num_iterations = num_iterations;
    
    int fd = open(device_path, O_RDWR);
    if (fd < 0) {
        result.error_code = errno;
        snprintf(result.error_message, sizeof(result.error_message), 
                "Failed to open device: %s", strerror(errno));
        return result;
    }
    
    struct performance_timer timer = perf_timer_start("IO Benchmark");
    
    for (int i = 0; i < num_iterations; i++) {
        int success = 0;
        
        switch (operation) {
        case BENCHMARK_READ: {
            char buffer[256];
            ssize_t bytes_read = read(fd, buffer, sizeof(buffer));
            success = (bytes_read >= 0);
            if (success) {
                result.bytes_transferred += bytes_read;
            }
            break;
        }
        case BENCHMARK_WRITE: {
            const char test_data[] = "test data";
            ssize_t bytes_written = write(fd, test_data, sizeof(test_data));
            success = (bytes_written >= 0);
            if (success) {
                result.bytes_transferred += bytes_written;
            }
            break;
        }
        case BENCHMARK_IOCTL: {
            /* Example IOCTL operation - adjust based on actual driver */
            int ioctl_result = fcntl(fd, F_GETFL);  /* Use a safe IOCTL */
            success = (ioctl_result >= 0);
            break;
        }
        }
        
        if (success) {
            result.successful_operations++;
        } else {
            result.failed_operations++;
            if (result.error_code == 0) {
                result.error_code = errno;
                snprintf(result.error_message, sizeof(result.error_message), 
                        "Operation failed: %s", strerror(errno));
            }
        }
    }
    
    struct performance_measurement measurement = perf_timer_stop(&timer);
    result.total_duration_us = measurement.duration_us;
    
    close(fd);
    
    /* Calculate derived metrics */
    if (result.total_duration_us > 0) {
        result.operations_per_second = (double)result.successful_operations * 1000000.0 / 
                                     result.total_duration_us;
        result.bytes_per_second = (double)result.bytes_transferred * 1000000.0 / 
                                result.total_duration_us;
    }
    
    if (num_iterations > 0) {
        result.success_rate = (double)result.successful_operations / num_iterations;
        result.average_duration_us = result.total_duration_us / num_iterations;
    }
    
    return result;
}

/* Print I/O benchmark results */
void perf_monitor_print_io_benchmark(const struct io_benchmark_result *result)
{
    const char *operation_names[] = {"READ", "WRITE", "IOCTL"};
    
    printf("\n=== I/O Benchmark Results ===\n");
    printf("Device: %s\n", result->device_path);
    printf("Operation: %s\n", operation_names[result->operation]);
    printf("Iterations: %d\n", result->num_iterations);
    printf("Successful Operations: %d\n", result->successful_operations);
    printf("Failed Operations: %d\n", result->failed_operations);
    printf("Success Rate: %.2f%%\n", result->success_rate * 100.0);
    printf("Total Duration: %.3f seconds\n", result->total_duration_us / 1000000.0);
    printf("Average Duration: %.3f ms\n", result->average_duration_us / 1000.0);
    printf("Operations per Second: %.2f\n", result->operations_per_second);
    
    if (result->bytes_transferred > 0) {
        printf("Bytes Transferred: %lu\n", result->bytes_transferred);
        printf("Bytes per Second: %.2f\n", result->bytes_per_second);
    }
    
    if (result->error_code != 0) {
        printf("Error Code: %d\n", result->error_code);
        printf("Error Message: %s\n", result->error_message);
    }
    
    printf("============================\n\n");
}

/* Memory usage monitoring */
struct memory_usage perf_monitor_get_memory_usage(void)
{
    struct memory_usage usage = {0};
    
    FILE *status_file = fopen("/proc/self/status", "r");
    if (!status_file) {
        return usage;
    }
    
    char line[256];
    while (fgets(line, sizeof(line), status_file)) {
        if (strncmp(line, "VmRSS:", 6) == 0) {
            sscanf(line + 6, "%lu", &usage.rss_kb);
        } else if (strncmp(line, "VmSize:", 7) == 0) {
            sscanf(line + 7, "%lu", &usage.vsize_kb);
        } else if (strncmp(line, "VmPeak:", 7) == 0) {
            sscanf(line + 7, "%lu", &usage.peak_vsize_kb);
        } else if (strncmp(line, "VmHWM:", 6) == 0) {
            sscanf(line + 6, "%lu", &usage.peak_rss_kb);
        }
    }
    
    fclose(status_file);
    return usage;
}

/* Print memory usage */
void perf_monitor_print_memory_usage(void)
{
    struct memory_usage usage = perf_monitor_get_memory_usage();
    
    printf("\n=== Memory Usage ===\n");
    printf("Current RSS: %lu KB (%.2f MB)\n", usage.rss_kb, usage.rss_kb / 1024.0);
    printf("Current VSize: %lu KB (%.2f MB)\n", usage.vsize_kb, usage.vsize_kb / 1024.0);
    printf("Peak RSS: %lu KB (%.2f MB)\n", usage.peak_rss_kb, usage.peak_rss_kb / 1024.0);
    printf("Peak VSize: %lu KB (%.2f MB)\n", usage.peak_vsize_kb, usage.peak_vsize_kb / 1024.0);
    printf("==================\n\n");
}

/* Generate performance report */
void perf_monitor_generate_report(const char *filename)
{
    FILE *report_file = filename ? fopen(filename, "w") : stdout;
    if (!report_file && filename) {
        printf("Error: Could not open report file '%s': %s\n", filename, strerror(errno));
        return;
    }
    
    struct performance_stats stats = perf_monitor_get_stats();
    struct memory_usage memory = perf_monitor_get_memory_usage();
    
    fprintf(report_file, "MPU-6050 Driver Performance Report\n");
    fprintf(report_file, "====================================\n\n");
    
    time_t now = time(NULL);
    fprintf(report_file, "Generated: %s\n", ctime(&now));
    
    fprintf(report_file, "Performance Summary:\n");
    fprintf(report_file, "  Session Duration: %.3f seconds\n", stats.session_duration_us / 1000000.0);
    fprintf(report_file, "  Total Operations: %lu\n", stats.total_operations);
    fprintf(report_file, "  Success Rate: %.2f%%\n", stats.success_rate * 100.0);
    fprintf(report_file, "  Throughput: %.2f ops/sec\n", stats.operations_per_second);
    fprintf(report_file, "  Average Latency: %.3f ms\n", stats.average_duration_us / 1000.0);
    fprintf(report_file, "  Min Latency: %.3f ms\n", stats.min_duration_us / 1000.0);
    fprintf(report_file, "  Max Latency: %.3f ms\n", stats.max_duration_us / 1000.0);
    
    fprintf(report_file, "\nMemory Usage:\n");
    fprintf(report_file, "  Current RSS: %.2f MB\n", memory.rss_kb / 1024.0);
    fprintf(report_file, "  Peak RSS: %.2f MB\n", memory.peak_rss_kb / 1024.0);
    
    if (filename) {
        fclose(report_file);
        printf("Performance report written to: %s\n", filename);
    }
}