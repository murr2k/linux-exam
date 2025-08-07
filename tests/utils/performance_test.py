#!/usr/bin/env python3
"""
MPU-6050 Performance Testing Suite
Author: Murray Kopit <murr2k@gmail.com>

This module provides comprehensive performance testing capabilities for the
MPU-6050 kernel driver, measuring throughput, latency, and resource usage.
"""

import argparse
import json
import logging
import os
import psutil
import statistics
import sys
import time
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Performance test configuration
DEFAULT_TEST_DURATION = 60  # seconds
DEFAULT_MIN_THROUGHPUT = 50  # operations per second
DEFAULT_DEVICE_PATH = "/dev/mpu6050"
DEFAULT_IOCTL_TIMEOUT = 1.0  # seconds

@dataclass
class PerformanceMetrics:
    """Container for performance test results."""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    throughput_ops_per_sec: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    cpu_usage_percent: float
    memory_usage_mb: float
    error_rate_percent: float
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        return data

class PerformanceMonitor:
    """System resource monitoring during tests."""
    
    def __init__(self, interval=0.1):
        self.interval = interval
        self.monitoring = False
        self.cpu_samples = []
        self.memory_samples = []
        self.monitor_thread = None
        self.process = psutil.Process()
    
    def start(self):
        """Start monitoring system resources."""
        self.monitoring = True
        self.cpu_samples.clear()
        self.memory_samples.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self) -> Tuple[float, float]:
        """Stop monitoring and return average CPU and memory usage."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        avg_cpu = statistics.mean(self.cpu_samples) if self.cpu_samples else 0.0
        avg_memory = statistics.mean(self.memory_samples) if self.memory_samples else 0.0
        
        return avg_cpu, avg_memory
    
    def _monitor_loop(self):
        """Monitoring loop running in separate thread."""
        while self.monitoring:
            try:
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
                
                self.cpu_samples.append(cpu_percent)
                self.memory_samples.append(memory_mb)
                
                time.sleep(self.interval)
            except Exception as e:
                logging.warning(f"Error monitoring resources: {e}")
                break

class MPU6050PerformanceTester:
    """MPU-6050 device performance tester."""
    
    def __init__(self, device_path=DEFAULT_DEVICE_PATH):
        self.device_path = device_path
        self.logger = logging.getLogger(self.__class__.__name__)
        self.monitor = PerformanceMonitor()
        
        # Test results storage
        self.test_results = []
    
    def test_read_throughput(self, duration=DEFAULT_TEST_DURATION) -> PerformanceMetrics:
        """Test raw read operation throughput."""
        self.logger.info(f"Starting read throughput test for {duration}s")
        
        start_time = datetime.now()
        end_time_target = time.time() + duration
        
        operation_count = 0
        successful_ops = 0
        failed_ops = 0
        latencies = []
        
        # Start monitoring
        self.monitor.start()
        
        try:
            with open(self.device_path, 'rb') as device:
                while time.time() < end_time_target:
                    operation_start = time.time()
                    
                    try:
                        # Read raw sensor data (14 bytes)
                        data = device.read(14)
                        
                        operation_end = time.time()
                        latency_ms = (operation_end - operation_start) * 1000
                        latencies.append(latency_ms)
                        
                        if len(data) == 14:
                            successful_ops += 1
                        else:
                            failed_ops += 1
                            self.logger.warning(f"Short read: {len(data)} bytes")
                        
                    except Exception as e:
                        failed_ops += 1
                        operation_end = time.time()
                        latency_ms = (operation_end - operation_start) * 1000
                        latencies.append(latency_ms)
                        self.logger.debug(f"Read operation failed: {e}")
                    
                    operation_count += 1
                    
                    # Brief pause to prevent overwhelming the system
                    time.sleep(0.001)
        
        except Exception as e:
            self.logger.error(f"Device access failed: {e}")
            raise
        
        finally:
            # Stop monitoring
            avg_cpu, avg_memory = self.monitor.stop()
        
        end_time = datetime.now()
        actual_duration = (end_time - start_time).total_seconds()
        
        # Calculate metrics
        throughput = successful_ops / actual_duration if actual_duration > 0 else 0
        error_rate = (failed_ops / operation_count * 100) if operation_count > 0 else 0
        
        # Calculate latency percentiles
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            sorted_latencies = sorted(latencies)
            p50_latency = statistics.median(sorted_latencies)
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]
        else:
            avg_latency = min_latency = max_latency = 0
            p50_latency = p95_latency = p99_latency = 0
        
        metrics = PerformanceMetrics(
            test_name="read_throughput",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=actual_duration,
            total_operations=operation_count,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            throughput_ops_per_sec=throughput,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            cpu_usage_percent=avg_cpu,
            memory_usage_mb=avg_memory,
            error_rate_percent=error_rate,
            metadata={
                'device_path': self.device_path,
                'read_size_bytes': 14,
                'test_type': 'throughput'
            }
        )
        
        self.test_results.append(metrics)
        self.logger.info(f"Read throughput test completed: {throughput:.1f} ops/s")
        
        return metrics
    
    def test_ioctl_throughput(self, duration=DEFAULT_TEST_DURATION) -> PerformanceMetrics:
        """Test IOCTL operation throughput."""
        import fcntl
        
        self.logger.info(f"Starting IOCTL throughput test for {duration}s")
        
        start_time = datetime.now()
        end_time_target = time.time() + duration
        
        operation_count = 0
        successful_ops = 0
        failed_ops = 0
        latencies = []
        
        # IOCTL commands to test (example values - adjust based on your driver)
        ioctl_commands = [
            0x8001,  # Example: GET_WHO_AM_I
            0x8002,  # Example: READ_RAW
            0x8003,  # Example: READ_SCALED
        ]
        
        # Start monitoring
        self.monitor.start()
        
        try:
            with open(self.device_path, 'rw') as device:
                fd = device.fileno()
                
                while time.time() < end_time_target:
                    # Cycle through IOCTL commands
                    cmd = ioctl_commands[operation_count % len(ioctl_commands)]
                    
                    operation_start = time.time()
                    
                    try:
                        # Execute IOCTL (this is a simplified example)
                        result = fcntl.ioctl(fd, cmd, 0)
                        
                        operation_end = time.time()
                        latency_ms = (operation_end - operation_start) * 1000
                        latencies.append(latency_ms)
                        
                        successful_ops += 1
                        
                    except Exception as e:
                        failed_ops += 1
                        operation_end = time.time()
                        latency_ms = (operation_end - operation_start) * 1000
                        latencies.append(latency_ms)
                        self.logger.debug(f"IOCTL operation failed: {e}")
                    
                    operation_count += 1
                    
                    # Brief pause
                    time.sleep(0.001)
        
        except Exception as e:
            self.logger.warning(f"IOCTL test limited due to device access: {e}")
            # Continue with synthetic results for demonstration
            
        finally:
            avg_cpu, avg_memory = self.monitor.stop()
        
        end_time = datetime.now()
        actual_duration = (end_time - start_time).total_seconds()
        
        # Calculate metrics (similar to read test)
        throughput = successful_ops / actual_duration if actual_duration > 0 else 0
        error_rate = (failed_ops / operation_count * 100) if operation_count > 0 else 0
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            sorted_latencies = sorted(latencies)
            p50_latency = statistics.median(sorted_latencies)
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 1 else avg_latency
            p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 1 else avg_latency
        else:
            avg_latency = min_latency = max_latency = 0
            p50_latency = p95_latency = p99_latency = 0
        
        metrics = PerformanceMetrics(
            test_name="ioctl_throughput",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=actual_duration,
            total_operations=operation_count,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            throughput_ops_per_sec=throughput,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            cpu_usage_percent=avg_cpu,
            memory_usage_mb=avg_memory,
            error_rate_percent=error_rate,
            metadata={
                'device_path': self.device_path,
                'ioctl_commands_tested': len(ioctl_commands),
                'test_type': 'ioctl_throughput'
            }
        )
        
        self.test_results.append(metrics)
        self.logger.info(f"IOCTL throughput test completed: {throughput:.1f} ops/s")
        
        return metrics
    
    def test_concurrent_access(self, duration=DEFAULT_TEST_DURATION, num_threads=4) -> PerformanceMetrics:
        """Test concurrent access performance."""
        self.logger.info(f"Starting concurrent access test with {num_threads} threads for {duration}s")
        
        start_time = datetime.now()
        end_time_target = time.time() + duration
        
        # Shared counters (thread-safe)
        results = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'latencies': []
        }
        results_lock = threading.Lock()
        
        # Worker thread function
        def worker():
            thread_ops = 0
            thread_success = 0
            thread_failed = 0
            thread_latencies = []
            
            try:
                with open(self.device_path, 'rb') as device:
                    while time.time() < end_time_target:
                        operation_start = time.time()
                        
                        try:
                            data = device.read(14)
                            operation_end = time.time()
                            latency_ms = (operation_end - operation_start) * 1000
                            thread_latencies.append(latency_ms)
                            
                            if len(data) == 14:
                                thread_success += 1
                            else:
                                thread_failed += 1
                        
                        except Exception:
                            thread_failed += 1
                            operation_end = time.time()
                            latency_ms = (operation_end - operation_start) * 1000
                            thread_latencies.append(latency_ms)
                        
                        thread_ops += 1
                        time.sleep(0.001)  # Small delay
            
            except Exception as e:
                self.logger.debug(f"Worker thread error: {e}")
            
            # Update shared results
            with results_lock:
                results['total_operations'] += thread_ops
                results['successful_operations'] += thread_success
                results['failed_operations'] += thread_failed
                results['latencies'].extend(thread_latencies)
        
        # Start monitoring
        self.monitor.start()
        
        # Start worker threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Stop monitoring
        avg_cpu, avg_memory = self.monitor.stop()
        
        end_time = datetime.now()
        actual_duration = (end_time - start_time).total_seconds()
        
        # Calculate metrics
        total_ops = results['total_operations']
        successful_ops = results['successful_operations']
        failed_ops = results['failed_operations']
        latencies = results['latencies']
        
        throughput = successful_ops / actual_duration if actual_duration > 0 else 0
        error_rate = (failed_ops / total_ops * 100) if total_ops > 0 else 0
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            sorted_latencies = sorted(latencies)
            p50_latency = statistics.median(sorted_latencies)
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 1 else avg_latency
            p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 1 else avg_latency
        else:
            avg_latency = min_latency = max_latency = 0
            p50_latency = p95_latency = p99_latency = 0
        
        metrics = PerformanceMetrics(
            test_name="concurrent_access",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=actual_duration,
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            throughput_ops_per_sec=throughput,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            cpu_usage_percent=avg_cpu,
            memory_usage_mb=avg_memory,
            error_rate_percent=error_rate,
            metadata={
                'device_path': self.device_path,
                'num_threads': num_threads,
                'test_type': 'concurrent_access'
            }
        )
        
        self.test_results.append(metrics)
        self.logger.info(f"Concurrent access test completed: {throughput:.1f} ops/s with {num_threads} threads")
        
        return metrics
    
    def run_all_tests(self, duration=DEFAULT_TEST_DURATION, min_throughput=DEFAULT_MIN_THROUGHPUT) -> Dict[str, bool]:
        """Run all performance tests and return pass/fail results."""
        self.logger.info("Starting comprehensive performance test suite")
        
        test_results = {}
        
        try:
            # Test 1: Read throughput
            read_metrics = self.test_read_throughput(duration)
            test_results['read_throughput'] = read_metrics.throughput_ops_per_sec >= min_throughput
            
            # Test 2: IOCTL throughput
            ioctl_metrics = self.test_ioctl_throughput(duration)
            test_results['ioctl_throughput'] = ioctl_metrics.throughput_ops_per_sec >= min_throughput * 0.5  # Lower threshold
            
            # Test 3: Concurrent access
            concurrent_metrics = self.test_concurrent_access(duration, num_threads=4)
            test_results['concurrent_access'] = concurrent_metrics.throughput_ops_per_sec >= min_throughput * 0.8
            
        except Exception as e:
            self.logger.error(f"Performance test suite failed: {e}")
            test_results['error'] = str(e)
        
        # Overall result
        all_passed = all(result for result in test_results.values() if isinstance(result, bool))
        test_results['overall_pass'] = all_passed
        
        self.logger.info(f"Performance test suite completed. Overall: {'PASS' if all_passed else 'FAIL'}")
        
        return test_results
    
    def save_results(self, output_file: str):
        """Save test results to JSON file."""
        results_data = {
            'test_suite': 'MPU6050_Performance',
            'timestamp': datetime.now().isoformat(),
            'device_path': self.device_path,
            'results': [result.to_dict() for result in self.test_results]
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        self.logger.info(f"Performance test results saved to {output_file}")

def run_performance_suite(duration=DEFAULT_TEST_DURATION, 
                         min_throughput=DEFAULT_MIN_THROUGHPUT,
                         device_path=DEFAULT_DEVICE_PATH,
                         log_file=None) -> bool:
    """Convenience function to run the full performance test suite."""
    # Set up logging
    log_level = logging.INFO
    if log_file:
        logging.basicConfig(
            level=log_level,
            format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    else:
        logging.basicConfig(
            level=log_level,
            format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
        )
    
    logger = logging.getLogger('PerformanceTestSuite')
    
    try:
        # Check device availability
        if not os.path.exists(device_path):
            logger.error(f"Device not found: {device_path}")
            return False
        
        # Run tests
        tester = MPU6050PerformanceTester(device_path)
        results = tester.run_all_tests(duration, min_throughput)
        
        # Save results if log file is specified
        if log_file:
            results_file = log_file.replace('.log', '_results.json')
            tester.save_results(results_file)
        
        return results.get('overall_pass', False)
        
    except Exception as e:
        logger.error(f"Performance test suite failed: {e}")
        return False

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MPU-6050 Performance Test Suite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--device', default=DEFAULT_DEVICE_PATH,
        help='Device path to test'
    )
    parser.add_argument(
        '--duration', type=int, default=DEFAULT_TEST_DURATION,
        help='Test duration in seconds'
    )
    parser.add_argument(
        '--min-throughput', type=float, default=DEFAULT_MIN_THROUGHPUT,
        help='Minimum required throughput (ops/sec)'
    )
    parser.add_argument(
        '--output', type=str,
        help='Output file for test results (JSON)'
    )
    parser.add_argument(
        '--log-file', type=str,
        help='Log file path'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    handlers = []
    
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file))
    
    handlers.append(logging.StreamHandler(sys.stdout))
    
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        handlers=handlers
    )
    
    # Run tests
    success = run_performance_suite(
        duration=args.duration,
        min_throughput=args.min_throughput,
        device_path=args.device,
        log_file=args.log_file
    )
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()