/*
 * Buffer Overflow Security Tests
 *
 * Comprehensive buffer overflow detection tests for kernel drivers.
 * Tests include stack-based, heap-based, and integer overflow scenarios.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/random.h>
#include <linux/vmalloc.h>
#include <linux/hardirq.h>
#include "security_test_framework.h"
#include "../../include/mpu6050.h"

/* Test data structures */
struct stack_overflow_test {
	char buffer[64];
	u32 canary;
	char overflow_data[128];
};

static int sec_test_setup_buffer_test(struct sec_test_case *test, void *data)
{
	struct sec_buffer_test_data *test_data = (struct sec_buffer_test_data *)data;
	
	if (!test_data)
		return -EINVAL;
		
	/* Allocate test buffer */
	test_data->buffer = kzalloc(test_data->buffer_size, GFP_KERNEL);
	if (!test_data->buffer)
		return -ENOMEM;
		
	/* Initialize with pattern */
	memset(test_data->buffer, test_data->pattern, test_data->buffer_size);
	
	return 0;
}

static void sec_test_cleanup_buffer_test(struct sec_test_case *test, void *data)
{
	struct sec_buffer_test_data *test_data = (struct sec_buffer_test_data *)data;
	
	if (test_data && test_data->buffer) {
		kfree(test_data->buffer);
		test_data->buffer = NULL;
	}
}

/**
 * sec_test_buffer_overflow_basic - Basic buffer overflow detection
 * @test: Test case structure
 * @data: Test-specific data
 *
 * Tests basic buffer overflow scenarios with boundary checking.
 */
int sec_test_buffer_overflow_basic(struct sec_test_case *test, void *data)
{
	struct sec_buffer_test_data *test_data = (struct sec_buffer_test_data *)data;
	char test_buffer[32];
	u32 canary = SEC_BUFFER_CANARY_PATTERN;
	int i;
	
	/* Place canary after buffer */
	memcpy(&test_buffer[32], &canary, sizeof(canary));
	
	/* Simulate controlled overflow */
	for (i = 0; i < 40; i++) {
		test_buffer[i] = 'A';
	}
	
	/* Check if canary was corrupted */
	if (memcmp(&test_buffer[32], &canary, sizeof(canary)) != 0) {
		strcpy(test->details, "Buffer overflow detected - canary corrupted");
		test->vuln_found = true;
		return SEC_TEST_VULNERABLE;
	}
	
	return SEC_TEST_PASS;
}

/**
 * sec_test_buffer_overflow_stack - Stack-based buffer overflow test
 * @test: Test case structure
 * @data: Test-specific data
 */
int sec_test_buffer_overflow_stack(struct sec_test_case *test, void *data)
{
	struct stack_overflow_test stack_test;
	char input_data[100];
	int ret = SEC_TEST_PASS;
	
	/* Initialize stack structure */
	memset(&stack_test, 0, sizeof(stack_test));
	stack_test.canary = SEC_BUFFER_CANARY_PATTERN;
	
	/* Generate overflow pattern */
	memset(input_data, 'B', sizeof(input_data) - 1);
	input_data[sizeof(input_data) - 1] = '\0';
	
	/* Simulate unsafe copy operation */
	strncpy(stack_test.buffer, input_data, sizeof(stack_test.buffer) - 1);
	
	/* Verify canary integrity */
	if (stack_test.canary != SEC_BUFFER_CANARY_PATTERN) {
		snprintf(test->details, sizeof(test->details),
			"Stack overflow detected - canary: 0x%x, expected: 0x%x",
			stack_test.canary, SEC_BUFFER_CANARY_PATTERN);
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	return ret;
}

/**
 * sec_test_buffer_overflow_heap - Heap-based buffer overflow test
 * @test: Test case structure 
 * @data: Test-specific data
 */
int sec_test_buffer_overflow_heap(struct sec_test_case *test, void *data)
{
	struct sec_buffer_test_data *test_data = (struct sec_buffer_test_data *)data;
	void *heap_buffer;
	void *guard_buffer;
	u32 guard_pattern = SEC_BUFFER_CANARY_PATTERN;
	size_t test_size = 256;
	int ret = SEC_TEST_PASS;
	
	/* Allocate heap buffer with guard */
	heap_buffer = kzalloc(test_size, GFP_KERNEL);
	if (!heap_buffer)
		return SEC_TEST_SKIP;
	
	guard_buffer = kzalloc(sizeof(u32), GFP_KERNEL);
	if (!guard_buffer) {
		kfree(heap_buffer);
		return SEC_TEST_SKIP;
	}
	
	/* Set guard pattern */
	*(u32 *)guard_buffer = guard_pattern;
	
	/* Simulate heap overflow */
	memset(heap_buffer, 'C', test_size + 16); /* Intentional overflow */
	
	/* Check guard integrity (this is a simplified test) */
	if (*(u32 *)guard_buffer != guard_pattern) {
		strcpy(test->details, "Heap overflow detected - guard corrupted");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	kfree(heap_buffer);
	kfree(guard_buffer);
	
	return ret;
}

/**
 * sec_test_integer_overflow - Integer overflow vulnerability test
 * @test: Test case structure
 * @data: Test-specific data
 */
int sec_test_integer_overflow(struct sec_test_case *test, void *data)
{
	size_t size1 = SIZE_MAX - 100;
	size_t size2 = 200;
	size_t total_size;
	void *buffer;
	
	/* Test integer overflow in size calculation */
	total_size = size1 + size2;
	
	/* Check for overflow */
	if (total_size < size1 || total_size < size2) {
		strcpy(test->details, "Integer overflow detected in size calculation");
		test->vuln_found = true;
		return SEC_TEST_VULNERABLE;
	}
	
	/* Test allocation with potentially overflowed size */
	buffer = kzalloc(total_size, GFP_KERNEL);
	if (buffer) {
		/* If allocation succeeded with overflowed size, it's a vulnerability */
		kfree(buffer);
		strcpy(test->details, "Memory allocation succeeded with overflowed size");
		test->vuln_found = true;
		return SEC_TEST_VULNERABLE;
	}
	
	return SEC_TEST_PASS;
}

/**
 * sec_test_mpu6050_buffer_validation - MPU6050-specific buffer tests
 * @test: Test case structure
 * @data: Test-specific data
 */
static int sec_test_mpu6050_buffer_validation(struct sec_test_case *test, void *data)
{
	struct mpu6050_raw_data raw_data;
	struct mpu6050_config config;
	char buffer[256];
	int ret = SEC_TEST_PASS;
	
	/* Test structure size validation */
	if (sizeof(struct mpu6050_raw_data) > 64) {
		strcpy(test->details, "Raw data structure too large - potential overflow risk");
		ret = SEC_TEST_VULNERABLE;
	}
	
	/* Test config parameter bounds */
	config.sample_rate_div = 255; /* Maximum value */
	config.gyro_range = 4;        /* Out of bounds */
	config.accel_range = 4;       /* Out of bounds */
	config.dlpf_cfg = 7;          /* Out of bounds */
	
	if (config.gyro_range > 3 || config.accel_range > 3 || config.dlpf_cfg > 6) {
		strcpy(test->details, "Configuration parameter bounds checking failed");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	/* Test buffer initialization */
	memset(buffer, 0xAA, sizeof(buffer));
	memcpy(buffer, &raw_data, sizeof(raw_data));
	
	/* Verify no uninitialized data leakage */
	if (memchr(buffer + sizeof(raw_data), 0xAA, 
		   sizeof(buffer) - sizeof(raw_data)) != 
		   buffer + sizeof(raw_data)) {
		strcpy(test->details, "Potential information leakage detected");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	return ret;
}

/* Buffer overflow test suite definition */
static struct sec_buffer_test_data basic_buffer_data = {
	.buffer_size = 128,
	.overflow_size = 16,
	.canary_enabled = true,
	.pattern = 0x41414141
};

static struct sec_test_case buffer_overflow_tests[] = {
	{
		.name = "basic_buffer_overflow",
		.description = "Basic buffer overflow detection with canary",
		.category = SEC_CAT_BUFFER_OVERFLOW,
		.severity = SEC_SEVERITY_HIGH,
		.vuln_type = SEC_VULN_BUFFER_OVERFLOW,
		.test_func = sec_test_buffer_overflow_basic,
		.setup_func = sec_test_setup_buffer_test,
		.cleanup_func = sec_test_cleanup_buffer_test,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 5000,
		.data = &basic_buffer_data
	},
	{
		.name = "stack_buffer_overflow",
		.description = "Stack-based buffer overflow detection",
		.category = SEC_CAT_BUFFER_OVERFLOW,
		.severity = SEC_SEVERITY_CRITICAL,
		.vuln_type = SEC_VULN_BUFFER_OVERFLOW,
		.test_func = sec_test_buffer_overflow_stack,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 3000,
		.data = NULL
	},
	{
		.name = "heap_buffer_overflow", 
		.description = "Heap-based buffer overflow detection",
		.category = SEC_CAT_BUFFER_OVERFLOW,
		.severity = SEC_SEVERITY_HIGH,
		.vuln_type = SEC_VULN_BUFFER_OVERFLOW,
		.test_func = sec_test_buffer_overflow_heap,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 5000,
		.data = &basic_buffer_data
	},
	{
		.name = "integer_overflow",
		.description = "Integer overflow vulnerability test",
		.category = SEC_CAT_BUFFER_OVERFLOW,
		.severity = SEC_SEVERITY_HIGH,
		.vuln_type = SEC_VULN_INTEGER_OVERFLOW,
		.test_func = sec_test_integer_overflow,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 2000,
		.data = NULL
	},
	{
		.name = "mpu6050_buffer_validation",
		.description = "MPU6050-specific buffer overflow tests",
		.category = SEC_CAT_BUFFER_OVERFLOW | SEC_CAT_INPUT_VALIDATION,
		.severity = SEC_SEVERITY_MEDIUM,
		.vuln_type = SEC_VULN_BUFFER_OVERFLOW,
		.test_func = sec_test_mpu6050_buffer_validation,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 3000,
		.data = NULL
	}
};

/* Export test suite */
struct sec_test_suite buffer_overflow_suite = {
	.name = "buffer_overflow_tests",
	.description = "Buffer overflow and memory safety vulnerability tests",
	.test_count = ARRAY_SIZE(buffer_overflow_tests),
	.tests = buffer_overflow_tests,
	.results = NULL /* Will be allocated dynamically */
};

static int __init buffer_overflow_tests_init(void)
{
	int ret;
	
	pr_info("Initializing buffer overflow security tests\n");
	
	ret = sec_test_register_suite(&buffer_overflow_suite);
	if (ret) {
		pr_err("Failed to register buffer overflow test suite: %d\n", ret);
		return ret;
	}
	
	pr_info("Buffer overflow security tests registered successfully\n");
	return 0;
}

static void __exit buffer_overflow_tests_exit(void)
{
	pr_info("Unloading buffer overflow security tests\n");
	sec_test_unregister_suite(&buffer_overflow_suite);
}

module_init(buffer_overflow_tests_init);
module_exit(buffer_overflow_tests_exit);

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Murray Kopit <murr2k@gmail.com>");
MODULE_DESCRIPTION("Buffer overflow security tests for MPU6050 driver");
MODULE_VERSION("1.0");