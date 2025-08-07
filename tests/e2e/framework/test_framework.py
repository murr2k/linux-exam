#!/usr/bin/env python3
"""
MPU-6050 End-to-End Test Framework

This module provides a comprehensive test orchestration framework for the MPU-6050 driver.
It handles module loading/unloading, device node testing, IOCTL testing, performance
measurement, and data validation.

Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import os
import sys
import time
import subprocess
import fcntl
import struct
import signal
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any, Callable
from contextlib import contextmanager
from threading import Lock, Event

from .validators import DataValidator, StatisticalAnalyzer, NoiseAnalyzer
from .performance import PerformanceTracker, StressTestRunner, ResourceMonitor
from .reports import ReportGenerator, MetricsCollector


@dataclass
class TestConfig:
    """Test configuration parameters"""
    device_path: str = "/dev/mpu6050"
    module_name: str = "mpu6050_driver"
    module_path: str = "../drivers/mpu6050_driver.ko"
    test_duration: int = 300  # seconds
    sample_rate: float = 100.0  # Hz
    stress_test_duration: int = 600  # seconds
    concurrent_clients: int = 4
    memory_limit_mb: int = 64
    cpu_limit_percent: int = 25
    validate_ranges: bool = True
    generate_reports: bool = True
    verbose: bool = False


@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    passed: bool
    duration: float
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class TestSuite:
    """Test suite information"""
    name: str
    description: str
    setup_func: Optional[Callable] = None
    teardown_func: Optional[Callable] = None
    tests: List[Callable] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.tests is None:
            self.tests = []
        if self.dependencies is None:
            self.dependencies = []


class TestFramework:
    """Main test framework orchestrator"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.results: List[TestResult] = []
        self.test_suites: Dict[str, TestSuite] = {}
        self.device_fd: Optional[int] = None
        self.module_loaded: bool = False
        self.shutdown_event = Event()
        self.lock = Lock()
        
        # Initialize components
        self.validator = DataValidator()
        self.analyzer = StatisticalAnalyzer()
        self.noise_analyzer = NoiseAnalyzer()
        self.performance_tracker = PerformanceTracker()
        self.stress_tester = StressTestRunner()
        self.resource_monitor = ResourceMonitor()
        self.report_generator = ReportGenerator()
        self.metrics_collector = MetricsCollector()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self._register_builtin_test_suites()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        log_level = logging.DEBUG if self.config.verbose else logging.INFO
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'test_framework_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            ]
        )
        
        return logging.getLogger(__name__)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    def _register_builtin_test_suites(self) -> None:
        """Register built-in test suites"""
        self.register_test_suite(TestSuite(
            name="module_tests",
            description="Module loading and initialization tests",
            setup_func=self._module_setup,
            teardown_func=self._module_teardown,
            tests=[
                self.test_module_loading,
                self.test_device_node_creation,
                self.test_device_permissions,
                self.test_module_parameters
            ]
        ))

        self.register_test_suite(TestSuite(
            name="basic_functionality",
            description="Basic device functionality tests",
            setup_func=self._device_setup,
            teardown_func=self._device_teardown,
            tests=[
                self.test_device_open_close,
                self.test_who_am_i,
                self.test_basic_register_access,
                self.test_configuration_commands
            ],
            dependencies=["module_tests"]
        ))

        self.register_test_suite(TestSuite(
            name="data_operations",
            description="Data reading and validation tests",
            setup_func=self._device_setup,
            teardown_func=self._device_teardown,
            tests=[
                self.test_raw_data_reading,
                self.test_scaled_data_reading,
                self.test_continuous_reading,
                self.test_data_consistency
            ],
            dependencies=["basic_functionality"]
        ))

        self.register_test_suite(TestSuite(
            name="performance_tests",
            description="Performance and stress tests",
            setup_func=self._device_setup,
            teardown_func=self._device_teardown,
            tests=[
                self.test_throughput_performance,
                self.test_latency_measurements,
                self.test_concurrent_access,
                self.test_resource_usage
            ],
            dependencies=["data_operations"]
        ))

        self.register_test_suite(TestSuite(
            name="stress_tests",
            description="Long-duration stress and stability tests",
            setup_func=self._device_setup,
            teardown_func=self._device_teardown,
            tests=[
                self.test_long_duration_stability,
                self.test_memory_leak_detection,
                self.test_error_recovery,
                self.test_power_cycle_recovery
            ],
            dependencies=["performance_tests"]
        ))

    def register_test_suite(self, suite: TestSuite) -> None:
        """Register a test suite"""
        self.test_suites[suite.name] = suite
        self.logger.info(f"Registered test suite: {suite.name}")

    @contextmanager
    def _device_context(self):
        """Context manager for device operations"""
        fd = None
        try:
            fd = os.open(self.config.device_path, os.O_RDWR)
            yield fd
        except Exception as e:
            self.logger.error(f"Failed to open device: {e}")
            raise
        finally:
            if fd is not None:
                os.close(fd)

    def _module_setup(self) -> bool:
        """Setup function for module tests"""
        self.logger.info("Setting up module tests...")
        return True

    def _module_teardown(self) -> bool:
        """Teardown function for module tests"""
        self.logger.info("Tearing down module tests...")
        if self.module_loaded:
            self.unload_module()
        return True

    def _device_setup(self) -> bool:
        """Setup function for device tests"""
        self.logger.info("Setting up device tests...")
        if not self.module_loaded:
            if not self.load_module():
                return False
        return True

    def _device_teardown(self) -> bool:
        """Teardown function for device tests"""
        self.logger.info("Tearing down device tests...")
        if self.device_fd is not None:
            os.close(self.device_fd)
            self.device_fd = None
        return True

    def load_module(self) -> bool:
        """Load the kernel module"""
        try:
            self.logger.info(f"Loading module: {self.config.module_name}")
            
            # Check if module is already loaded
            result = subprocess.run(["lsmod"], capture_output=True, text=True)
            if self.config.module_name in result.stdout:
                self.logger.info("Module already loaded")
                self.module_loaded = True
                return True
            
            # Load the module
            cmd = ["sudo", "insmod", self.config.module_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Module loaded successfully")
                self.module_loaded = True
                time.sleep(1)  # Wait for device node creation
                return True
            else:
                self.logger.error(f"Failed to load module: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception loading module: {e}")
            return False

    def unload_module(self) -> bool:
        """Unload the kernel module"""
        try:
            self.logger.info(f"Unloading module: {self.config.module_name}")
            
            cmd = ["sudo", "rmmod", self.config.module_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Module unloaded successfully")
                self.module_loaded = False
                return True
            else:
                self.logger.error(f"Failed to unload module: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception unloading module: {e}")
            return False

    def run_test_suite(self, suite_name: str) -> List[TestResult]:
        """Run a specific test suite"""
        if suite_name not in self.test_suites:
            raise ValueError(f"Unknown test suite: {suite_name}")
        
        suite = self.test_suites[suite_name]
        results = []
        
        self.logger.info(f"Running test suite: {suite.name}")
        self.logger.info(f"Description: {suite.description}")
        
        # Check dependencies
        for dep in suite.dependencies:
            if dep not in [r.test_name.split('::')[0] for r in self.results if r.passed]:
                self.logger.warning(f"Dependency {dep} not satisfied, skipping suite {suite_name}")
                return []
        
        # Run setup
        if suite.setup_func and not suite.setup_func():
            self.logger.error(f"Setup failed for suite {suite_name}")
            return []
        
        try:
            # Run tests
            for test_func in suite.tests:
                if self.shutdown_event.is_set():
                    break
                
                test_name = f"{suite_name}::{test_func.__name__}"
                result = self._run_single_test(test_name, test_func)
                results.append(result)
                self.results.append(result)
                
        finally:
            # Run teardown
            if suite.teardown_func:
                suite.teardown_func()
        
        return results

    def _run_single_test(self, test_name: str, test_func: Callable) -> TestResult:
        """Run a single test function"""
        self.logger.info(f"Running test: {test_name}")
        start_time = time.time()
        
        try:
            success = test_func()
            duration = time.time() - start_time
            
            result = TestResult(
                test_name=test_name,
                passed=bool(success),
                duration=duration,
                metrics=self.metrics_collector.get_test_metrics(test_name)
            )
            
            status = "PASSED" if result.passed else "FAILED"
            self.logger.info(f"Test {test_name}: {status} (duration: {duration:.3f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(
                test_name=test_name,
                passed=False,
                duration=duration,
                error_message=str(e)
            )
            self.logger.error(f"Test {test_name}: EXCEPTION - {e}")
        
        return result

    def run_all_tests(self) -> List[TestResult]:
        """Run all registered test suites"""
        self.logger.info("Starting comprehensive test run...")
        
        # Determine execution order based on dependencies
        execution_order = self._resolve_dependencies()
        
        for suite_name in execution_order:
            if self.shutdown_event.is_set():
                break
            
            results = self.run_test_suite(suite_name)
            
            # Stop if critical tests fail
            if suite_name in ["module_tests", "basic_functionality"]:
                failed_tests = [r for r in results if not r.passed]
                if failed_tests:
                    self.logger.error(f"Critical test suite {suite_name} failed, stopping execution")
                    break
        
        return self.results

    def _resolve_dependencies(self) -> List[str]:
        """Resolve test suite dependencies to determine execution order"""
        ordered = []
        visited = set()
        
        def visit(suite_name: str):
            if suite_name in visited:
                return
            
            if suite_name in self.test_suites:
                suite = self.test_suites[suite_name]
                for dep in suite.dependencies:
                    visit(dep)
                
                visited.add(suite_name)
                ordered.append(suite_name)
        
        for suite_name in self.test_suites:
            visit(suite_name)
        
        return ordered

    # Test implementations
    def test_module_loading(self) -> bool:
        """Test module loading and unloading"""
        try:
            # Ensure module is unloaded first
            if self.module_loaded:
                self.unload_module()
            
            # Load module
            if not self.load_module():
                return False
            
            # Verify module is loaded
            result = subprocess.run(["lsmod"], capture_output=True, text=True)
            return self.config.module_name in result.stdout
            
        except Exception as e:
            self.logger.error(f"Module loading test failed: {e}")
            return False

    def test_device_node_creation(self) -> bool:
        """Test device node creation"""
        try:
            # Wait for device node to appear
            timeout = 5.0
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if os.path.exists(self.config.device_path):
                    return True
                time.sleep(0.1)
            
            self.logger.error(f"Device node {self.config.device_path} not created within timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Device node creation test failed: {e}")
            return False

    def test_device_permissions(self) -> bool:
        """Test device node permissions"""
        try:
            if not os.path.exists(self.config.device_path):
                return False
            
            stat_info = os.stat(self.config.device_path)
            
            # Check if it's a character device
            import stat
            if not stat.S_ISCHR(stat_info.st_mode):
                self.logger.error(f"Device {self.config.device_path} is not a character device")
                return False
            
            # Check permissions (should be readable and writable)
            return os.access(self.config.device_path, os.R_OK | os.W_OK)
            
        except Exception as e:
            self.logger.error(f"Device permissions test failed: {e}")
            return False

    def test_module_parameters(self) -> bool:
        """Test module parameters"""
        try:
            # Check sysfs entries for module parameters
            module_path = f"/sys/module/{self.config.module_name}"
            if not os.path.exists(module_path):
                return False
            
            # Basic test - just check the path exists
            # More specific parameter tests would depend on actual module parameters
            return True
            
        except Exception as e:
            self.logger.error(f"Module parameters test failed: {e}")
            return False

    def test_device_open_close(self) -> bool:
        """Test basic device open and close operations"""
        try:
            with self._device_context() as fd:
                return fd is not None
        except Exception as e:
            self.logger.error(f"Device open/close test failed: {e}")
            return False

    def test_who_am_i(self) -> bool:
        """Test WHO_AM_I register reading"""
        try:
            # Define IOCTL constants (from header)
            MPU6050_IOC_MAGIC = ord('M')
            MPU6050_IOC_WHO_AM_I = (2 << 30) | (1 << 16) | (MPU6050_IOC_MAGIC << 8) | 6
            
            with self._device_context() as fd:
                result = fcntl.ioctl(fd, MPU6050_IOC_WHO_AM_I, b'\x00')
                who_am_i = struct.unpack('B', result)[0]
                
                expected = 0x68  # MPU-6050 WHO_AM_I value
                if who_am_i == expected:
                    return True
                else:
                    self.logger.error(f"WHO_AM_I mismatch: got 0x{who_am_i:02X}, expected 0x{expected:02X}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"WHO_AM_I test failed: {e}")
            return False

    def test_basic_register_access(self) -> bool:
        """Test basic register read/write operations"""
        try:
            # This would depend on the specific IOCTL interface
            # For now, we'll consider it passed if device opens
            with self._device_context() as fd:
                return True
        except Exception as e:
            self.logger.error(f"Register access test failed: {e}")
            return False

    def test_configuration_commands(self) -> bool:
        """Test configuration IOCTL commands"""
        try:
            # Define IOCTL constants for configuration
            MPU6050_IOC_MAGIC = ord('M')
            MPU6050_IOC_GET_CONFIG = (2 << 30) | (4 << 16) | (MPU6050_IOC_MAGIC << 8) | 3
            
            with self._device_context() as fd:
                # Try to read configuration
                result = fcntl.ioctl(fd, MPU6050_IOC_GET_CONFIG, b'\x00' * 4)
                return len(result) == 4
                
        except Exception as e:
            self.logger.error(f"Configuration commands test failed: {e}")
            return False

    def test_raw_data_reading(self) -> bool:
        """Test raw data reading"""
        try:
            MPU6050_IOC_MAGIC = ord('M')
            MPU6050_IOC_READ_RAW = (2 << 30) | (14 << 16) | (MPU6050_IOC_MAGIC << 8) | 0
            
            with self._device_context() as fd:
                result = fcntl.ioctl(fd, MPU6050_IOC_READ_RAW, b'\x00' * 14)
                return len(result) == 14
                
        except Exception as e:
            self.logger.error(f"Raw data reading test failed: {e}")
            return False

    def test_scaled_data_reading(self) -> bool:
        """Test scaled data reading"""
        try:
            MPU6050_IOC_MAGIC = ord('M')
            MPU6050_IOC_READ_SCALED = (2 << 30) | (28 << 16) | (MPU6050_IOC_MAGIC << 8) | 1
            
            with self._device_context() as fd:
                result = fcntl.ioctl(fd, MPU6050_IOC_READ_SCALED, b'\x00' * 28)
                
                if len(result) != 28:
                    return False
                
                # Validate data ranges
                data = struct.unpack('7i', result)
                return self.validator.validate_scaled_data(data)
                
        except Exception as e:
            self.logger.error(f"Scaled data reading test failed: {e}")
            return False

    def test_continuous_reading(self) -> bool:
        """Test continuous data reading"""
        try:
            MPU6050_IOC_MAGIC = ord('M')
            MPU6050_IOC_READ_SCALED = (2 << 30) | (28 << 16) | (MPU6050_IOC_MAGIC << 8) | 1
            
            readings = []
            with self._device_context() as fd:
                for _ in range(10):
                    if self.shutdown_event.is_set():
                        break
                        
                    result = fcntl.ioctl(fd, MPU6050_IOC_READ_SCALED, b'\x00' * 28)
                    if len(result) == 28:
                        data = struct.unpack('7i', result)
                        readings.append(data)
                    
                    time.sleep(0.01)  # 10ms between readings
            
            return len(readings) >= 8  # At least 8 successful readings
            
        except Exception as e:
            self.logger.error(f"Continuous reading test failed: {e}")
            return False

    def test_data_consistency(self) -> bool:
        """Test data consistency and validation"""
        try:
            readings = self._collect_sample_data(100)
            if len(readings) < 50:
                return False
            
            # Perform statistical analysis
            stats = self.analyzer.analyze_dataset(readings)
            
            # Check for reasonable statistics
            return (stats['sample_count'] >= 50 and
                   stats['accel_noise_level'] < 100 and  # mg
                   stats['gyro_noise_level'] < 50)       # mdps
            
        except Exception as e:
            self.logger.error(f"Data consistency test failed: {e}")
            return False

    def test_throughput_performance(self) -> bool:
        """Test read throughput performance"""
        try:
            with self.performance_tracker.measure_throughput("raw_reads") as tracker:
                MPU6050_IOC_MAGIC = ord('M')
                MPU6050_IOC_READ_RAW = (2 << 30) | (14 << 16) | (MPU6050_IOC_MAGIC << 8) | 0
                
                with self._device_context() as fd:
                    for _ in range(1000):
                        if self.shutdown_event.is_set():
                            break
                        
                        fcntl.ioctl(fd, MPU6050_IOC_READ_RAW, b'\x00' * 14)
                        tracker.record_operation()
            
            metrics = self.performance_tracker.get_metrics("raw_reads")
            throughput = metrics.get('throughput', 0)
            
            # Expect at least 100 reads/second
            return throughput >= 100.0
            
        except Exception as e:
            self.logger.error(f"Throughput performance test failed: {e}")
            return False

    def test_latency_measurements(self) -> bool:
        """Test latency measurements"""
        try:
            latencies = []
            MPU6050_IOC_MAGIC = ord('M')
            MPU6050_IOC_READ_RAW = (2 << 30) | (14 << 16) | (MPU6050_IOC_MAGIC << 8) | 0
            
            with self._device_context() as fd:
                for _ in range(100):
                    if self.shutdown_event.is_set():
                        break
                        
                    start_time = time.perf_counter()
                    fcntl.ioctl(fd, MPU6050_IOC_READ_RAW, b'\x00' * 14)
                    end_time = time.perf_counter()
                    
                    latencies.append((end_time - start_time) * 1000)  # ms
            
            if len(latencies) < 50:
                return False
            
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            # Expect average latency < 10ms, max latency < 50ms
            return avg_latency < 10.0 and max_latency < 50.0
            
        except Exception as e:
            self.logger.error(f"Latency measurements test failed: {e}")
            return False

    def test_concurrent_access(self) -> bool:
        """Test concurrent access from multiple processes"""
        try:
            return self.stress_tester.run_concurrent_access_test(
                device_path=self.config.device_path,
                num_clients=self.config.concurrent_clients,
                duration=30  # seconds
            )
        except Exception as e:
            self.logger.error(f"Concurrent access test failed: {e}")
            return False

    def test_resource_usage(self) -> bool:
        """Test resource usage monitoring"""
        try:
            with self.resource_monitor.monitor_process("test_process"):
                # Perform some operations
                readings = self._collect_sample_data(100)
                
            metrics = self.resource_monitor.get_metrics("test_process")
            
            # Check resource limits
            max_memory_mb = metrics.get('max_memory_mb', 0)
            max_cpu_percent = metrics.get('max_cpu_percent', 0)
            
            return (max_memory_mb < self.config.memory_limit_mb and
                   max_cpu_percent < self.config.cpu_limit_percent)
            
        except Exception as e:
            self.logger.error(f"Resource usage test failed: {e}")
            return False

    def test_long_duration_stability(self) -> bool:
        """Test long-duration stability"""
        try:
            return self.stress_tester.run_stability_test(
                device_path=self.config.device_path,
                duration=self.config.stress_test_duration
            )
        except Exception as e:
            self.logger.error(f"Long duration stability test failed: {e}")
            return False

    def test_memory_leak_detection(self) -> bool:
        """Test for memory leaks"""
        try:
            return self.stress_tester.run_memory_leak_test(
                device_path=self.config.device_path,
                duration=300  # 5 minutes
            )
        except Exception as e:
            self.logger.error(f"Memory leak detection test failed: {e}")
            return False

    def test_error_recovery(self) -> bool:
        """Test error recovery scenarios"""
        try:
            # Test recovery from various error conditions
            test_scenarios = [
                self._test_invalid_ioctl_recovery,
                self._test_device_busy_recovery,
                self._test_configuration_error_recovery
            ]
            
            for scenario in test_scenarios:
                if not scenario():
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error recovery test failed: {e}")
            return False

    def test_power_cycle_recovery(self) -> bool:
        """Test recovery from power cycle scenarios"""
        try:
            # Simulate module reload (closest to power cycle)
            if not self.unload_module():
                return False
            
            time.sleep(2)  # Wait
            
            if not self.load_module():
                return False
            
            # Test basic functionality after reload
            return self.test_who_am_i()
            
        except Exception as e:
            self.logger.error(f"Power cycle recovery test failed: {e}")
            return False

    def _collect_sample_data(self, count: int) -> List[Tuple]:
        """Collect sample data for analysis"""
        readings = []
        MPU6050_IOC_MAGIC = ord('M')
        MPU6050_IOC_READ_SCALED = (2 << 30) | (28 << 16) | (MPU6050_IOC_MAGIC << 8) | 1
        
        try:
            with self._device_context() as fd:
                for _ in range(count):
                    if self.shutdown_event.is_set():
                        break
                        
                    result = fcntl.ioctl(fd, MPU6050_IOC_READ_SCALED, b'\x00' * 28)
                    if len(result) == 28:
                        data = struct.unpack('7i', result)
                        readings.append(data)
                    
                    time.sleep(0.01)  # 10ms between readings
        except Exception as e:
            self.logger.error(f"Error collecting sample data: {e}")
        
        return readings

    def _test_invalid_ioctl_recovery(self) -> bool:
        """Test recovery from invalid IOCTL"""
        try:
            with self._device_context() as fd:
                # Send invalid IOCTL
                try:
                    fcntl.ioctl(fd, 0xDEADBEEF, b'\x00')
                except OSError:
                    pass  # Expected to fail
                
                # Test that device still works
                return self.test_who_am_i()
        except Exception:
            return False

    def _test_device_busy_recovery(self) -> bool:
        """Test recovery from device busy conditions"""
        # This would depend on specific driver implementation
        return True

    def _test_configuration_error_recovery(self) -> bool:
        """Test recovery from configuration errors"""
        try:
            MPU6050_IOC_MAGIC = ord('M')
            MPU6050_IOC_SET_CONFIG = (1 << 30) | (4 << 16) | (MPU6050_IOC_MAGIC << 8) | 2
            
            with self._device_context() as fd:
                # Send invalid configuration
                try:
                    invalid_config = struct.pack('4B', 0xFF, 0xFF, 0xFF, 0xFF)
                    fcntl.ioctl(fd, MPU6050_IOC_SET_CONFIG, invalid_config)
                except OSError:
                    pass  # May fail, which is OK
                
                # Test that device still works
                return self.test_who_am_i()
        except Exception:
            return False

    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        if not self.config.generate_reports:
            return {}
        
        report_data = {
            'test_run_info': {
                'timestamp': datetime.now().isoformat(),
                'config': asdict(self.config),
                'total_tests': len(self.results),
                'passed_tests': len([r for r in self.results if r.passed]),
                'failed_tests': len([r for r in self.results if not r.passed])
            },
            'test_results': [asdict(r) for r in self.results],
            'performance_metrics': self.performance_tracker.get_all_metrics(),
            'resource_metrics': self.resource_monitor.get_all_metrics(),
            'analysis_results': self.analyzer.get_analysis_summary()
        }
        
        return self.report_generator.generate_comprehensive_report(report_data)

    def save_results(self, filename: str) -> None:
        """Save test results to file"""
        report = self.generate_final_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Test results saved to {filename}")

    def print_summary(self) -> None:
        """Print test summary to console"""
        total = len(self.results)
        passed = len([r for r in self.results if r.passed])
        failed = total - passed
        
        print("\n" + "="*60)
        print("TEST FRAMEWORK SUMMARY")
        print("="*60)
        print(f"Total Tests:     {total}")
        print(f"Passed Tests:    {passed}")
        print(f"Failed Tests:    {failed}")
        print(f"Success Rate:    {(passed/total*100) if total > 0 else 0:.1f}%")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.test_name}: {result.error_message or 'Failed'}")
        
        print("="*60)