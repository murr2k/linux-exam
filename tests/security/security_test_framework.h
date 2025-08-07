/* SPDX-License-Identifier: GPL-2.0 */
/*
 * MPU-6050 Security Testing Framework
 *
 * Comprehensive security testing framework for kernel drivers with focus on:
 * - Buffer overflow detection
 * - Privilege escalation detection  
 * - Memory safety validation
 * - Input sanitization verification
 * - Race condition security testing
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#ifndef _SECURITY_TEST_FRAMEWORK_H_
#define _SECURITY_TEST_FRAMEWORK_H_

#include <linux/types.h>
#include <linux/kernel.h>
#include <linux/mutex.h>
#include <linux/security.h>

/* Security test result codes */
#define SEC_TEST_PASS           0
#define SEC_TEST_FAIL           1
#define SEC_TEST_VULNERABLE     2
#define SEC_TEST_SKIP           3

/* Security test categories */
#define SEC_CAT_BUFFER_OVERFLOW    BIT(0)
#define SEC_CAT_PRIVILEGE_ESC      BIT(1)
#define SEC_CAT_MEMORY_SAFETY      BIT(2)
#define SEC_CAT_INPUT_VALIDATION   BIT(3)
#define SEC_CAT_RACE_CONDITIONS    BIT(4)
#define SEC_CAT_CAPABILITY_CHECK   BIT(5)
#define SEC_CAT_ALL               0x3F

/* Security test severities */
enum sec_test_severity {
	SEC_SEVERITY_LOW = 0,
	SEC_SEVERITY_MEDIUM,
	SEC_SEVERITY_HIGH,
	SEC_SEVERITY_CRITICAL
};

/* Security vulnerability types */
enum sec_vuln_type {
	SEC_VULN_BUFFER_OVERFLOW,
	SEC_VULN_INTEGER_OVERFLOW,
	SEC_VULN_USE_AFTER_FREE,
	SEC_VULN_DOUBLE_FREE,
	SEC_VULN_NULL_DEREF,
	SEC_VULN_PRIVILEGE_ESC,
	SEC_VULN_RACE_CONDITION,
	SEC_VULN_INFO_LEAK,
	SEC_VULN_INJECTION,
	SEC_VULN_MAX
};

/**
 * struct sec_test_case - Security test case definition
 * @name: Test case name
 * @description: Detailed test description
 * @category: Security category bitmask
 * @severity: Test severity level
 * @vuln_type: Type of vulnerability being tested
 * @test_func: Test function pointer
 * @setup_func: Optional setup function
 * @cleanup_func: Optional cleanup function
 * @expected_result: Expected test result
 * @timeout_ms: Test timeout in milliseconds
 * @data: Test-specific data pointer
 */
struct sec_test_case {
	const char *name;
	const char *description;
	u32 category;
	enum sec_test_severity severity;
	enum sec_vuln_type vuln_type;
	int (*test_func)(struct sec_test_case *test, void *data);
	int (*setup_func)(struct sec_test_case *test, void *data);
	void (*cleanup_func)(struct sec_test_case *test, void *data);
	int expected_result;
	u32 timeout_ms;
	void *data;
};

/**
 * struct sec_test_result - Security test result
 * @test_name: Name of the test case
 * @result: Test result code
 * @severity: Detected severity level
 * @vuln_found: Vulnerability detected flag
 * @execution_time_us: Test execution time in microseconds
 * @details: Additional details about the result
 * @recommendations: Security recommendations
 */
struct sec_test_result {
	char test_name[64];
	int result;
	enum sec_test_severity severity;
	bool vuln_found;
	u64 execution_time_us;
	char details[256];
	char recommendations[512];
};

/**
 * struct sec_test_suite - Security test suite
 * @name: Test suite name
 * @description: Suite description
 * @test_count: Number of test cases
 * @tests: Array of test cases
 * @results: Array of test results
 * @lock: Synchronization mutex
 * @stats: Test statistics
 */
struct sec_test_suite {
	const char *name;
	const char *description;
	u32 test_count;
	struct sec_test_case *tests;
	struct sec_test_result *results;
	struct mutex lock;
	struct {
		u32 passed;
		u32 failed;
		u32 vulnerabilities;
		u32 skipped;
		u64 total_time_us;
	} stats;
};

/* Buffer overflow test data */
struct sec_buffer_test_data {
	void *buffer;
	size_t buffer_size;
	size_t overflow_size;
	bool canary_enabled;
	u32 pattern;
};

/* Privilege escalation test data */
struct sec_privilege_test_data {
	kuid_t original_uid;
	kgid_t original_gid;
	cap_t original_caps;
	bool should_escalate;
};

/* Memory safety test data */
struct sec_memory_test_data {
	void *alloc_ptr;
	size_t alloc_size;
	bool use_after_free;
	bool double_free;
	u32 poison_pattern;
};

/* Function prototypes */
int sec_test_init_framework(void);
void sec_test_cleanup_framework(void);
int sec_test_register_suite(struct sec_test_suite *suite);
void sec_test_unregister_suite(struct sec_test_suite *suite);
int sec_test_run_suite(struct sec_test_suite *suite, u32 category_mask);
int sec_test_run_all_suites(u32 category_mask);

/* Buffer overflow testing */
int sec_test_buffer_overflow_basic(struct sec_test_case *test, void *data);
int sec_test_buffer_overflow_stack(struct sec_test_case *test, void *data);
int sec_test_buffer_overflow_heap(struct sec_test_case *test, void *data);
int sec_test_integer_overflow(struct sec_test_case *test, void *data);

/* Privilege escalation testing */
int sec_test_privilege_escalation(struct sec_test_case *test, void *data);
int sec_test_capability_bypass(struct sec_test_case *test, void *data);
int sec_test_uid_manipulation(struct sec_test_case *test, void *data);

/* Memory safety testing */
int sec_test_use_after_free(struct sec_test_case *test, void *data);
int sec_test_double_free(struct sec_test_case *test, void *data);
int sec_test_null_pointer_deref(struct sec_test_case *test, void *data);
int sec_test_memory_leak_detection(struct sec_test_case *test, void *data);

/* Input validation testing */
int sec_test_input_sanitization(struct sec_test_case *test, void *data);
int sec_test_boundary_conditions(struct sec_test_case *test, void *data);
int sec_test_format_string_vuln(struct sec_test_case *test, void *data);

/* Race condition testing */
int sec_test_race_condition_basic(struct sec_test_case *test, void *data);
int sec_test_toctou_vulnerability(struct sec_test_case *test, void *data);
int sec_test_concurrent_access(struct sec_test_case *test, void *data);

/* Hardware-specific security tests */
int sec_test_hardware_interface_validation(struct sec_test_case *test, void *data);
int sec_test_i2c_security(struct sec_test_case *test, void *data);
int sec_test_register_protection(struct sec_test_case *test, void *data);

/* Kernel-specific security tests */
int sec_test_kernel_module_security(struct sec_test_case *test, void *data);
int sec_test_device_node_permissions(struct sec_test_case *test, void *data);
int sec_test_sysfs_security(struct sec_test_case *test, void *data);

/* Utility functions */
const char *sec_test_severity_to_string(enum sec_test_severity severity);
const char *sec_test_vuln_type_to_string(enum sec_vuln_type vuln_type);
int sec_test_generate_report(struct sec_test_suite *suite, char *buffer, size_t size);
void sec_test_print_statistics(struct sec_test_suite *suite);

/* Security test macros */
#define SEC_TEST_ASSERT(condition, test, message) \
	do { \
		if (!(condition)) { \
			snprintf((test)->details, sizeof((test)->details), \
				"Assertion failed: %s", message); \
			return SEC_TEST_FAIL; \
		} \
	} while (0)

#define SEC_TEST_ASSERT_VULN(condition, test, vuln_type, message) \
	do { \
		if (condition) { \
			snprintf((test)->details, sizeof((test)->details), \
				"Vulnerability detected: %s", message); \
			(test)->vuln_found = true; \
			return SEC_TEST_VULNERABLE; \
		} \
	} while (0)

#define SEC_TEST_SKIP_IF(condition, test, message) \
	do { \
		if (condition) { \
			snprintf((test)->details, sizeof((test)->details), \
				"Test skipped: %s", message); \
			return SEC_TEST_SKIP; \
		} \
	} while (0)

/* Memory protection utilities */
#define SEC_MEMORY_POISON_PATTERN   0xDEADBEEF
#define SEC_BUFFER_CANARY_PATTERN   0xCAFEBABE

/* Stack canary detection */
static inline bool sec_test_stack_canary_intact(u32 *canary_ptr, u32 expected)
{
	return (*canary_ptr == expected);
}

/* Buffer pattern verification */
static inline bool sec_test_buffer_pattern_intact(u32 *buffer, size_t size, u32 pattern)
{
	size_t i;
	for (i = 0; i < size / sizeof(u32); i++) {
		if (buffer[i] != pattern)
			return false;
	}
	return true;
}

#endif /* _SECURITY_TEST_FRAMEWORK_H_ */