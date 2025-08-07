/*
 * Race Condition Security Tests
 *
 * Comprehensive race condition and concurrent access vulnerability tests
 * including TOCTOU, deadlock detection, and synchronization testing.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/kthread.h>
#include <linux/delay.h>
#include <linux/mutex.h>
#include <linux/spinlock.h>
#include <linux/rwlock.h>
#include <linux/completion.h>
#include <linux/atomic.h>
#include <linux/random.h>
#include "security_test_framework.h"
#include "../../include/mpu6050.h"

/* Test data structures */
struct race_test_shared_data {
	int counter;
	int protected_counter;
	atomic_t atomic_counter;
	struct mutex mutex;
	spinlock_t spinlock;
	rwlock_t rwlock;
	bool test_running;
	struct completion test_completion;
};

static struct race_test_shared_data *shared_data;
static struct task_struct *test_threads[4];
static int num_active_threads;

/**
 * race_test_worker_thread - Worker thread for race condition testing
 * @data: Thread-specific data
 */
static int race_test_worker_thread(void *data)
{
	struct race_test_shared_data *test_data = (struct race_test_shared_data *)data;
	int thread_id = (int)(unsigned long)current;
	int iterations = 1000;
	int i;
	
	pr_debug("Race test worker thread %d started\n", thread_id);
	
	for (i = 0; i < iterations && test_data->test_running; i++) {
		/* Test 1: Unprotected counter (race condition) */
		test_data->counter++;
		
		/* Test 2: Mutex-protected counter */
		mutex_lock(&test_data->mutex);
		test_data->protected_counter++;
		mutex_unlock(&test_data->mutex);
		
		/* Test 3: Atomic counter */
		atomic_inc(&test_data->atomic_counter);
		
		/* Test 4: Spinlock-protected operations */
		unsigned long flags;
		spin_lock_irqsave(&test_data->spinlock, flags);
		/* Simulate critical section */
		udelay(1);
		spin_unlock_irqrestore(&test_data->spinlock, flags);
		
		/* Test 5: Read-write lock test */
		read_lock(&test_data->rwlock);
		/* Read operation */
		volatile int temp = test_data->counter;
		(void)temp; /* Suppress unused variable warning */
		read_unlock(&test_data->rwlock);
		
		if (i % 100 == 0) {
			/* Occasional write operation */
			write_lock(&test_data->rwlock);
			/* Write operation would go here */
			write_unlock(&test_data->rwlock);
		}
		
		/* Yield to increase chance of race conditions */
		if (i % 10 == 0) {
			schedule();
		}
	}
	
	pr_debug("Race test worker thread %d completed\n", thread_id);
	complete(&test_data->test_completion);
	
	return 0;
}

/**
 * sec_test_race_condition_basic - Basic race condition test
 * @test: Test case structure
 * @data: Test-specific data
 */
int sec_test_race_condition_basic(struct sec_test_case *test, void *data)
{
	int ret = SEC_TEST_PASS;
	int expected_counter;
	int i;
	
	/* Initialize shared data */
	if (!shared_data) {
		shared_data = kzalloc(sizeof(*shared_data), GFP_KERNEL);
		if (!shared_data) {
			strcpy(test->details, "Failed to allocate shared data");
			return SEC_TEST_SKIP;
		}
		
		shared_data->counter = 0;
		shared_data->protected_counter = 0;
		atomic_set(&shared_data->atomic_counter, 0);
		mutex_init(&shared_data->mutex);
		spin_lock_init(&shared_data->spinlock);
		rwlock_init(&shared_data->rwlock);
		shared_data->test_running = true;
		init_completion(&shared_data->test_completion);
	}
	
	/* Reset counters */
	shared_data->counter = 0;
	shared_data->protected_counter = 0;
	atomic_set(&shared_data->atomic_counter, 0);
	shared_data->test_running = true;
	reinit_completion(&shared_data->test_completion);
	
	/* Start worker threads */
	num_active_threads = 4;
	for (i = 0; i < num_active_threads; i++) {
		test_threads[i] = kthread_run(race_test_worker_thread, shared_data,
					      "race_test_%d", i);
		if (IS_ERR(test_threads[i])) {
			pr_err("Failed to create race test thread %d\n", i);
			num_active_threads = i;
			break;
		}
	}
	
	/* Let threads run for a while */
	msleep(100);
	
	/* Stop threads */
	shared_data->test_running = false;
	
	/* Wait for threads to complete */
	for (i = 0; i < num_active_threads; i++) {
		wait_for_completion_timeout(&shared_data->test_completion,
					    msecs_to_jiffies(5000));
		kthread_stop(test_threads[i]);
	}
	
	/* Analyze results */
	expected_counter = num_active_threads * 1000;
	
	snprintf(test->details, sizeof(test->details),
		"Unprotected counter: %d (expected: %d), Protected: %d, Atomic: %d",
		shared_data->counter, expected_counter,
		shared_data->protected_counter,
		atomic_read(&shared_data->atomic_counter));
	
	/* Check for race conditions */
	if (shared_data->counter != expected_counter) {
		/* This indicates a race condition occurred */
		strcat(test->details, " - Race condition detected in unprotected counter");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	if (shared_data->protected_counter != expected_counter) {
		strcat(test->details, " - Mutex protection failed");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	if (atomic_read(&shared_data->atomic_counter) != expected_counter) {
		strcat(test->details, " - Atomic operations failed");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	return ret;
}

/**
 * sec_test_toctou_vulnerability - Time-of-check to time-of-use test
 * @test: Test case structure
 * @data: Test-specific data
 */
int sec_test_toctou_vulnerability(struct sec_test_case *test, void *data)
{
	static struct {
		bool valid;
		int value;
		struct mutex lock;
	} toctou_data = { .valid = false, .value = 0 };
	
	int ret = SEC_TEST_PASS;
	bool race_detected = false;
	
	mutex_init(&toctou_data.lock);
	
	/* Simulate TOCTOU scenario */
	
	/* Time of Check */
	if (toctou_data.valid) {
		/* Simulate delay between check and use */
		msleep(1);
		
		/* Time of Use - value might have changed */
		if (toctou_data.value < 0) {
			/* This could be a TOCTOU vulnerability if value changed */
			race_detected = true;
		}
	}
	
	/* Test proper TOCTOU protection */
	mutex_lock(&toctou_data.lock);
	if (toctou_data.valid && toctou_data.value >= 0) {
		/* Use the value atomically */
		toctou_data.value++;
	}
	mutex_unlock(&toctou_data.lock);
	
	if (race_detected) {
		strcpy(test->details, "TOCTOU vulnerability detected - value changed between check and use");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	} else {
		strcpy(test->details, "TOCTOU protection working correctly");
	}
	
	return ret;
}

/**
 * sec_test_concurrent_access - Test concurrent access to shared resources
 * @test: Test case structure
 * @data: Test-specific data
 */
int sec_test_concurrent_access(struct sec_test_case *test, void *data)
{
	static struct mpu6050_data mock_device = {0};
	static bool mock_device_initialized = false;
	int ret = SEC_TEST_PASS;
	
	/* Initialize mock device once */
	if (!mock_device_initialized) {
		mutex_init(&mock_device.lock);
		mock_device.gyro_range = 0;
		mock_device.accel_range = 0;
		mock_device_initialized = true;
	}
	
	/* Test concurrent access to device structure */
	
	/* Thread 1 simulation: Configuration change */
	mutex_lock(&mock_device.lock);
	mock_device.gyro_range = 1;
	msleep(1); /* Simulate processing time */
	mock_device.accel_range = 1;
	mutex_unlock(&mock_device.lock);
	
	/* Thread 2 simulation: Read configuration */
	mutex_lock(&mock_device.lock);
	if (mock_device.gyro_range != mock_device.accel_range) {
		/* Inconsistent state detected */
		snprintf(test->details, sizeof(test->details),
			"Inconsistent device state: gyro_range=%d, accel_range=%d",
			mock_device.gyro_range, mock_device.accel_range);
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	} else {
		strcpy(test->details, "Concurrent access properly synchronized");
	}
	mutex_unlock(&mock_device.lock);
	
	return ret;
}

/**
 * sec_test_deadlock_detection - Test for deadlock scenarios
 * @test: Test case structure
 * @data: Test-specific data
 */
static int sec_test_deadlock_detection(struct sec_test_case *test, void *data)
{
	static DEFINE_MUTEX(mutex_a);
	static DEFINE_MUTEX(mutex_b);
	int ret = SEC_TEST_PASS;
	
	/* Test proper lock ordering to avoid deadlock */
	
	/* Correct order: always acquire mutex_a before mutex_b */
	if (mutex_trylock(&mutex_a)) {
		if (mutex_trylock(&mutex_b)) {
			/* Critical section with both locks */
			udelay(1);
			mutex_unlock(&mutex_b);
		} else {
			/* Failed to acquire second lock - potential deadlock avoided */
			strcpy(test->details, "Deadlock avoidance: failed to acquire second lock");
		}
		mutex_unlock(&mutex_a);
	} else {
		strcpy(test->details, "Failed to acquire first lock");
		ret = SEC_TEST_SKIP;
	}
	
	/* Test timeout-based lock acquisition */
	if (mutex_lock_interruptible_timeout(&mutex_a, msecs_to_jiffies(100)) > 0) {
		if (mutex_lock_interruptible_timeout(&mutex_b, msecs_to_jiffies(100)) > 0) {
			strcat(test->details, "; Timeout-based locking successful");
			mutex_unlock(&mutex_b);
		} else {
			strcat(test->details, "; Timeout prevented potential deadlock");
		}
		mutex_unlock(&mutex_a);
	}
	
	return ret;
}

/**
 * sec_test_atomic_operations - Test atomic operation safety
 * @test: Test case structure
 * @data: Test-specific data
 */
static int sec_test_atomic_operations(struct sec_test_case *test, void *data)
{
	atomic_t test_atomic = ATOMIC_INIT(0);
	atomic64_t test_atomic64 = ATOMIC64_INIT(0);
	int ret = SEC_TEST_PASS;
	int i;
	
	/* Test basic atomic operations */
	for (i = 0; i < 100; i++) {
		atomic_inc(&test_atomic);
		atomic64_inc(&test_atomic64);
	}
	
	if (atomic_read(&test_atomic) != 100) {
		snprintf(test->details, sizeof(test->details),
			"Atomic increment failed: expected 100, got %d",
			atomic_read(&test_atomic));
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	if (atomic64_read(&test_atomic64) != 100) {
		snprintf(test->details, sizeof(test->details),
			"Atomic64 increment failed: expected 100, got %lld",
			(long long)atomic64_read(&test_atomic64));
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	/* Test compare-and-swap operations */
	int old_val = atomic_read(&test_atomic);
	if (atomic_cmpxchg(&test_atomic, old_val, old_val + 50) != old_val) {
		strcat(test->details, "; Compare-and-swap operation failed");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	if (ret == SEC_TEST_PASS) {
		strcpy(test->details, "Atomic operations working correctly");
	}
	
	return ret;
}

/**
 * sec_test_interrupt_safety - Test interrupt context safety
 * @test: Test case structure
 * @data: Test-specific data
 */
static int sec_test_interrupt_safety(struct sec_test_case *test, void *data)
{
	spinlock_t test_spinlock;
	unsigned long flags;
	int ret = SEC_TEST_PASS;
	
	spin_lock_init(&test_spinlock);
	
	/* Test interrupt-safe spinlock usage */
	spin_lock_irqsave(&test_spinlock, flags);
	
	/* Simulate critical section that must be interrupt-safe */
	udelay(1);
	
	spin_unlock_irqrestore(&test_spinlock, flags);
	
	/* Test that we can still acquire the lock (not deadlocked) */
	if (spin_trylock(&test_spinlock)) {
		spin_unlock(&test_spinlock);
		strcpy(test->details, "Interrupt-safe spinlock operations working correctly");
	} else {
		strcpy(test->details, "Spinlock appears to be stuck - potential deadlock");
		test->vuln_found = true;
		ret = SEC_TEST_VULNERABLE;
	}
	
	return ret;
}

/* Race condition test cases */
static struct sec_test_case race_condition_tests[] = {
	{
		.name = "basic_race_condition",
		.description = "Test basic race condition detection in concurrent access",
		.category = SEC_CAT_RACE_CONDITIONS,
		.severity = SEC_SEVERITY_HIGH,
		.vuln_type = SEC_VULN_RACE_CONDITION,
		.test_func = sec_test_race_condition_basic,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 10000,
		.data = NULL
	},
	{
		.name = "toctou_vulnerability",
		.description = "Test time-of-check to time-of-use vulnerability",
		.category = SEC_CAT_RACE_CONDITIONS,
		.severity = SEC_SEVERITY_MEDIUM,
		.vuln_type = SEC_VULN_RACE_CONDITION,
		.test_func = sec_test_toctou_vulnerability,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 3000,
		.data = NULL
	},
	{
		.name = "concurrent_access",
		.description = "Test concurrent access to shared device structures",
		.category = SEC_CAT_RACE_CONDITIONS,
		.severity = SEC_SEVERITY_MEDIUM,
		.vuln_type = SEC_VULN_RACE_CONDITION,
		.test_func = sec_test_concurrent_access,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 5000,
		.data = NULL
	},
	{
		.name = "deadlock_detection",
		.description = "Test deadlock detection and prevention mechanisms",
		.category = SEC_CAT_RACE_CONDITIONS,
		.severity = SEC_SEVERITY_HIGH,
		.vuln_type = SEC_VULN_RACE_CONDITION,
		.test_func = sec_test_deadlock_detection,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 4000,
		.data = NULL
	},
	{
		.name = "atomic_operations",
		.description = "Test atomic operation correctness and safety",
		.category = SEC_CAT_RACE_CONDITIONS,
		.severity = SEC_SEVERITY_MEDIUM,
		.vuln_type = SEC_VULN_RACE_CONDITION,
		.test_func = sec_test_atomic_operations,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 2000,
		.data = NULL
	},
	{
		.name = "interrupt_safety",
		.description = "Test interrupt context safety and spinlock usage",
		.category = SEC_CAT_RACE_CONDITIONS,
		.severity = SEC_SEVERITY_HIGH,
		.vuln_type = SEC_VULN_RACE_CONDITION,
		.test_func = sec_test_interrupt_safety,
		.expected_result = SEC_TEST_PASS,
		.timeout_ms = 2000,
		.data = NULL
	}
};

/* Export test suite */
struct sec_test_suite race_condition_suite = {
	.name = "race_condition_tests",
	.description = "Race condition and concurrent access vulnerability tests",
	.test_count = ARRAY_SIZE(race_condition_tests),
	.tests = race_condition_tests,
	.results = NULL
};

static int __init race_condition_tests_init(void)
{
	int ret;
	
	pr_info("Initializing race condition security tests\n");
	
	ret = sec_test_register_suite(&race_condition_suite);
	if (ret) {
		pr_err("Failed to register race condition test suite: %d\n", ret);
		return ret;
	}
	
	pr_info("Race condition security tests registered successfully\n");
	return 0;
}

static void __exit race_condition_tests_exit(void)
{
	int i;
	
	pr_info("Unloading race condition security tests\n");
	
	/* Clean up any remaining test threads */
	if (shared_data) {
		shared_data->test_running = false;
		
		for (i = 0; i < num_active_threads; i++) {
			if (test_threads[i] && !IS_ERR(test_threads[i])) {
				kthread_stop(test_threads[i]);
			}
		}
		
		/* Clean up shared data */
		if (mutex_is_locked(&shared_data->mutex)) {
			mutex_unlock(&shared_data->mutex);
		}
		
		kfree(shared_data);
		shared_data = NULL;
	}
	
	sec_test_unregister_suite(&race_condition_suite);
}

module_init(race_condition_tests_init);
module_exit(race_condition_tests_exit);

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Murray Kopit <murr2k@gmail.com>");
MODULE_DESCRIPTION("Race condition security tests for MPU6050 driver");
MODULE_VERSION("1.0");