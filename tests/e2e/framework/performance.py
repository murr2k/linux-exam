#!/usr/bin/env python3
"""
MPU-6050 Performance Testing Module

This module provides comprehensive performance testing capabilities including
throughput testing, latency measurement, resource usage monitoring,
concurrent access testing, and stress testing.

Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import os
import sys
import time
import psutil
import threading
import multiprocessing
import subprocess
import fcntl
import struct
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import deque
from contextlib import contextmanager
import statistics
import json


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    operation_name: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_time: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    avg_latency: float = 0.0
    median_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    throughput: float = 0.0  # operations per second
    error_rate: float = 0.0
    latency_samples: List[float] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)


@dataclass
class ResourceMetrics:
    """Resource usage metrics"""
    process_name: str
    pid: int = 0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    open_files: int = 0
    threads: int = 0
    max_cpu_percent: float = 0.0
    max_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    avg_memory_mb: float = 0.0
    monitoring_duration: float = 0.0


@dataclass
class StressTestConfig:
    """Stress test configuration"""
    duration: int = 600  # seconds
    num_clients: int = 4
    operations_per_second: int = 100
    ramp_up_time: int = 30
    cool_down_time: int = 30
    failure_threshold: float = 0.05  # 5% failure rate
    memory_limit_mb: int = 64
    cpu_limit_percent: int = 50


class PerformanceTracker:
    """Track performance metrics for various operations"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.lock = threading.Lock()
    
    @contextmanager
    def measure_operation(self, operation_name: str):
        """Context manager for measuring single operations"""
        start_time = time.perf_counter()
        success = False
        
        try:
            yield
            success = True
        finally:
            end_time = time.perf_counter()
            latency = end_time - start_time
            
            with self.lock:
                if operation_name not in self.metrics:
                    self.metrics[operation_name] = PerformanceMetrics(operation_name)
                
                metric = self.metrics[operation_name]
                metric.total_operations += 1
                if success:
                    metric.successful_operations += 1
                    metric.latency_samples.append(latency)
                    metric.timestamps.append(start_time)
                else:
                    metric.failed_operations += 1
                
                # Update running statistics
                self._update_statistics(metric)
    
    @contextmanager
    def measure_throughput(self, operation_name: str):
        """Context manager for measuring throughput"""
        tracker = ThroughputTracker(operation_name, self)
        
        try:
            yield tracker
        finally:
            tracker.finalize()
    
    def _update_statistics(self, metric: PerformanceMetrics):
        """Update statistical measures"""
        if not metric.latency_samples:
            return
        
        latencies = metric.latency_samples
        metric.min_latency = min(latencies)
        metric.max_latency = max(latencies)
        metric.avg_latency = statistics.mean(latencies)
        metric.median_latency = statistics.median(latencies)
        
        if len(latencies) >= 20:
            sorted_latencies = sorted(latencies)
            metric.p95_latency = sorted_latencies[int(0.95 * len(sorted_latencies))]
            metric.p99_latency = sorted_latencies[int(0.99 * len(sorted_latencies))]
        
        if metric.timestamps:
            time_span = max(metric.timestamps) - min(metric.timestamps)
            if time_span > 0:
                metric.throughput = metric.successful_operations / time_span
        
        if metric.total_operations > 0:
            metric.error_rate = metric.failed_operations / metric.total_operations
    
    def get_metrics(self, operation_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for specific operation"""
        with self.lock:
            if operation_name not in self.metrics:
                return None
            
            metric = self.metrics[operation_name]
            return {
                'operation_name': metric.operation_name,
                'total_operations': metric.total_operations,
                'successful_operations': metric.successful_operations,
                'failed_operations': metric.failed_operations,
                'throughput': metric.throughput,
                'avg_latency': metric.avg_latency,
                'median_latency': metric.median_latency,
                'p95_latency': metric.p95_latency,
                'p99_latency': metric.p99_latency,
                'min_latency': metric.min_latency,
                'max_latency': metric.max_latency,
                'error_rate': metric.error_rate
            }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all tracked metrics"""
        result = {}
        with self.lock:
            for name, metric in self.metrics.items():
                result[name] = self.get_metrics(name)
        return result
    
    def reset_metrics(self, operation_name: Optional[str] = None):
        """Reset metrics for specific operation or all operations"""
        with self.lock:
            if operation_name:
                if operation_name in self.metrics:
                    self.metrics[operation_name] = PerformanceMetrics(operation_name)
            else:
                self.metrics.clear()


class ThroughputTracker:
    """Helper class for throughput measurement"""
    
    def __init__(self, operation_name: str, parent_tracker: PerformanceTracker):
        self.operation_name = operation_name
        self.parent_tracker = parent_tracker
        self.start_time = time.perf_counter()
        self.operation_count = 0
    
    def record_operation(self, success: bool = True):
        """Record an operation"""
        with self.parent_tracker.lock:
            if self.operation_name not in self.parent_tracker.metrics:
                self.parent_tracker.metrics[self.operation_name] = PerformanceMetrics(self.operation_name)
            
            metric = self.parent_tracker.metrics[self.operation_name]
            metric.total_operations += 1
            
            if success:
                metric.successful_operations += 1
            else:
                metric.failed_operations += 1
            
            self.operation_count += 1
    
    def finalize(self):
        """Finalize throughput measurement"""
        end_time = time.perf_counter()
        duration = end_time - self.start_time
        
        with self.parent_tracker.lock:
            if self.operation_name in self.parent_tracker.metrics:
                metric = self.parent_tracker.metrics[self.operation_name]
                if duration > 0:
                    metric.throughput = self.operation_count / duration
                    metric.total_time = duration


class ResourceMonitor:
    """Monitor system resource usage"""
    
    def __init__(self):
        self.monitored_processes: Dict[str, ResourceMetrics] = {}
        self.monitoring_threads: Dict[str, threading.Thread] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        self.lock = threading.Lock()
    
    @contextmanager
    def monitor_process(self, process_name: str, pid: Optional[int] = None):
        """Context manager for monitoring a process"""
        if pid is None:
            pid = os.getpid()
        
        self.start_monitoring(process_name, pid)
        
        try:
            yield
        finally:
            self.stop_monitoring(process_name)
    
    def start_monitoring(self, process_name: str, pid: int):
        """Start monitoring a process"""
        with self.lock:
            if process_name in self.monitoring_threads:
                return  # Already monitoring
            
            self.monitored_processes[process_name] = ResourceMetrics(process_name, pid)
            self.stop_events[process_name] = threading.Event()
            
            thread = threading.Thread(
                target=self._monitor_loop,
                args=(process_name, pid),
                daemon=True
            )
            self.monitoring_threads[process_name] = thread
            thread.start()
    
    def stop_monitoring(self, process_name: str):
        """Stop monitoring a process"""
        with self.lock:
            if process_name in self.stop_events:
                self.stop_events[process_name].set()
            
            if process_name in self.monitoring_threads:
                thread = self.monitoring_threads[process_name]
                thread.join(timeout=5.0)
                del self.monitoring_threads[process_name]
            
            if process_name in self.stop_events:
                del self.stop_events[process_name]
    
    def _monitor_loop(self, process_name: str, pid: int):
        """Main monitoring loop"""
        try:
            process = psutil.Process(pid)
            metrics = self.monitored_processes[process_name]
            
            start_time = time.time()
            cpu_samples = []
            memory_samples = []
            
            while not self.stop_events[process_name].wait(1.0):  # Sample every second
                try:
                    # CPU usage
                    cpu_percent = process.cpu_percent()
                    cpu_samples.append(cpu_percent)
                    metrics.cpu_percent = cpu_percent
                    metrics.max_cpu_percent = max(metrics.max_cpu_percent, cpu_percent)
                    
                    # Memory usage
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
                    memory_samples.append(memory_mb)
                    metrics.memory_mb = memory_mb
                    metrics.max_memory_mb = max(metrics.max_memory_mb, memory_mb)
                    
                    # Memory percentage
                    try:
                        metrics.memory_percent = process.memory_percent()
                    except:
                        pass
                    
                    # Open files and threads
                    try:
                        metrics.open_files = process.num_fds()  # Linux/Unix
                    except (AttributeError, psutil.AccessDenied):
                        try:
                            metrics.open_files = len(process.open_files())
                        except:
                            pass
                    
                    try:
                        metrics.threads = process.num_threads()
                    except:
                        pass
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
            
            # Calculate averages
            end_time = time.time()
            metrics.monitoring_duration = end_time - start_time
            
            if cpu_samples:
                metrics.avg_cpu_percent = statistics.mean(cpu_samples)
            if memory_samples:
                metrics.avg_memory_mb = statistics.mean(memory_samples)
            
        except Exception as e:
            print(f"Error in resource monitoring for {process_name}: {e}")
    
    def get_metrics(self, process_name: str) -> Optional[Dict[str, Any]]:
        """Get resource metrics for a process"""
        with self.lock:
            if process_name not in self.monitored_processes:
                return None
            
            metrics = self.monitored_processes[process_name]
            return {
                'process_name': metrics.process_name,
                'pid': metrics.pid,
                'current_cpu_percent': metrics.cpu_percent,
                'current_memory_mb': metrics.memory_mb,
                'memory_percent': metrics.memory_percent,
                'open_files': metrics.open_files,
                'threads': metrics.threads,
                'max_cpu_percent': metrics.max_cpu_percent,
                'max_memory_mb': metrics.max_memory_mb,
                'avg_cpu_percent': metrics.avg_cpu_percent,
                'avg_memory_mb': metrics.avg_memory_mb,
                'monitoring_duration': metrics.monitoring_duration
            }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all monitored process metrics"""
        result = {}
        with self.lock:
            for name in self.monitored_processes:
                result[name] = self.get_metrics(name)
        return result


class StressTestRunner:
    """Run various stress tests on the MPU-6050 driver"""
    
    def __init__(self):
        self.performance_tracker = PerformanceTracker()
        self.resource_monitor = ResourceMonitor()
        self.active_processes: List[multiprocessing.Process] = []
    
    def run_concurrent_access_test(self, device_path: str, num_clients: int = 4, 
                                 duration: int = 60) -> bool:
        """Test concurrent access to the device"""
        print(f"Running concurrent access test: {num_clients} clients for {duration}s")
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring("stress_test", os.getpid())
        
        try:
            # Create client processes
            processes = []
            results_queue = multiprocessing.Queue()
            
            for i in range(num_clients):
                process = multiprocessing.Process(
                    target=self._concurrent_client_worker,
                    args=(device_path, duration, i, results_queue)
                )
                processes.append(process)
                process.start()
            
            # Wait for all processes to complete
            for process in processes:
                process.join()
            
            # Collect results
            total_operations = 0
            successful_operations = 0
            errors = []
            
            while not results_queue.empty():
                result = results_queue.get()
                total_operations += result['total_operations']
                successful_operations += result['successful_operations']
                if result['errors']:
                    errors.extend(result['errors'])
            
            success_rate = successful_operations / total_operations if total_operations > 0 else 0
            
            print(f"Concurrent access test results:")
            print(f"  Total operations: {total_operations}")
            print(f"  Successful operations: {successful_operations}")
            print(f"  Success rate: {success_rate:.1%}")
            print(f"  Errors: {len(errors)}")
            
            return success_rate >= 0.95  # 95% success rate threshold
            
        finally:
            self.resource_monitor.stop_monitoring("stress_test")
    
    def _concurrent_client_worker(self, device_path: str, duration: int, 
                                client_id: int, results_queue: multiprocessing.Queue):
        """Worker function for concurrent access testing"""
        # IOCTL constants
        MPU6050_IOC_MAGIC = ord('M')
        MPU6050_IOC_READ_SCALED = (2 << 30) | (28 << 16) | (MPU6050_IOC_MAGIC << 8) | 1
        
        total_operations = 0
        successful_operations = 0
        errors = []
        
        end_time = time.time() + duration
        
        try:
            while time.time() < end_time:
                try:
                    with open(device_path, 'rb') as device:
                        fd = device.fileno()
                        result = fcntl.ioctl(fd, MPU6050_IOC_READ_SCALED, b'\x00' * 28)
                        
                        if len(result) == 28:
                            successful_operations += 1
                        else:
                            errors.append(f"Client {client_id}: Invalid data length")
                        
                        total_operations += 1
                        
                except Exception as e:
                    errors.append(f"Client {client_id}: {str(e)}")
                    total_operations += 1
                
                # Small delay to avoid overwhelming the system
                time.sleep(0.01)
        
        except Exception as e:
            errors.append(f"Client {client_id} fatal error: {str(e)}")
        
        results_queue.put({
            'client_id': client_id,
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'errors': errors
        })
    
    def run_stability_test(self, device_path: str, duration: int = 600) -> bool:
        """Run long-duration stability test"""
        print(f"Running stability test for {duration} seconds...")
        
        # IOCTL constants
        MPU6050_IOC_MAGIC = ord('M')
        MPU6050_IOC_READ_SCALED = (2 << 30) | (28 << 16) | (MPU6050_IOC_MAGIC << 8) | 1
        
        end_time = time.time() + duration
        total_operations = 0
        successful_operations = 0
        error_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 0
        
        # Track performance over time
        performance_window = deque(maxlen=100)  # Last 100 operations
        
        self.resource_monitor.start_monitoring("stability_test", os.getpid())
        
        try:
            while time.time() < end_time:
                start_time = time.perf_counter()
                success = False
                
                try:
                    with open(device_path, 'rb') as device:
                        fd = device.fileno()
                        result = fcntl.ioctl(fd, MPU6050_IOC_READ_SCALED, b'\x00' * 28)
                        
                        if len(result) == 28:
                            # Validate data
                            data = struct.unpack('7i', result)
                            if self._validate_sensor_data(data):
                                successful_operations += 1
                                consecutive_errors = 0
                                success = True
                            else:
                                error_count += 1
                                consecutive_errors += 1
                        else:
                            error_count += 1
                            consecutive_errors += 1
                        
                        total_operations += 1
                        
                except Exception:
                    error_count += 1
                    consecutive_errors += 1
                    total_operations += 1
                
                # Track timing
                operation_time = time.perf_counter() - start_time
                performance_window.append({
                    'time': operation_time,
                    'success': success,
                    'timestamp': time.time()
                })
                
                max_consecutive_errors = max(max_consecutive_errors, consecutive_errors)
                
                # Check for stability issues
                if consecutive_errors > 50:  # Too many consecutive errors
                    print("Stability test failed: Too many consecutive errors")
                    return False
                
                # Adaptive delay based on performance
                if len(performance_window) >= 10:
                    recent_times = [p['time'] for p in list(performance_window)[-10:]]
                    avg_time = statistics.mean(recent_times)
                    
                    if avg_time > 0.1:  # If operations are taking too long
                        time.sleep(0.05)  # Longer delay
                    else:
                        time.sleep(0.01)  # Normal delay
                else:
                    time.sleep(0.01)
                
                # Progress update
                if total_operations % 1000 == 0:
                    elapsed = duration - (end_time - time.time())
                    success_rate = successful_operations / total_operations if total_operations > 0 else 0
                    print(f"Stability test progress: {elapsed:.0f}s, {total_operations} ops, "
                          f"{success_rate:.1%} success rate")
        
        finally:
            self.resource_monitor.stop_monitoring("stability_test")
        
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        
        print(f"Stability test results:")
        print(f"  Duration: {duration}s")
        print(f"  Total operations: {total_operations}")
        print(f"  Successful operations: {successful_operations}")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Max consecutive errors: {max_consecutive_errors}")
        
        # Consider test passed if success rate > 95% and max consecutive errors < 20
        return success_rate >= 0.95 and max_consecutive_errors < 20
    
    def run_memory_leak_test(self, device_path: str, duration: int = 300) -> bool:
        """Test for memory leaks during continuous operation"""
        print(f"Running memory leak test for {duration} seconds...")
        
        # IOCTL constants
        MPU6050_IOC_MAGIC = ord('M')
        MPU6050_IOC_READ_SCALED = (2 << 30) | (28 << 16) | (MPU6050_IOC_MAGIC << 8) | 1
        
        # Monitor memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        memory_samples = [initial_memory]
        sample_times = [0]
        
        end_time = time.time() + duration
        start_time = time.time()
        operations = 0
        
        try:
            while time.time() < end_time:
                try:
                    # Perform operations
                    for _ in range(10):  # Batch operations for efficiency
                        with open(device_path, 'rb') as device:
                            fd = device.fileno()
                            fcntl.ioctl(fd, MPU6050_IOC_READ_SCALED, b'\x00' * 28)
                        operations += 1
                    
                    # Sample memory every 5 seconds
                    current_time = time.time() - start_time
                    if current_time - sample_times[-1] >= 5:
                        current_memory = process.memory_info().rss / (1024 * 1024)
                        memory_samples.append(current_memory)
                        sample_times.append(current_time)
                    
                except Exception:
                    pass  # Continue testing even with errors
        
        except Exception as e:
            print(f"Memory leak test error: {e}")
            return False
        
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_growth = final_memory - initial_memory
        
        # Analyze memory trend
        leak_detected = False
        if len(memory_samples) >= 5:
            # Simple linear regression to detect trend
            x = list(range(len(memory_samples)))
            y = memory_samples
            
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            sum_x2 = sum(xi * xi for xi in x)
            
            # Calculate slope
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # Consider leak if memory grows more than 0.1 MB per minute
            growth_rate_per_minute = slope * 60 / duration  # MB per minute
            leak_detected = growth_rate_per_minute > 0.1
        
        print(f"Memory leak test results:")
        print(f"  Initial memory: {initial_memory:.1f} MB")
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Memory growth: {memory_growth:.1f} MB")
        print(f"  Operations performed: {operations}")
        print(f"  Leak detected: {'Yes' if leak_detected else 'No'}")
        
        return not leak_detected and memory_growth < 10  # Less than 10MB growth
    
    def run_performance_benchmark(self, device_path: str, duration: int = 60) -> Dict[str, Any]:
        """Run performance benchmark test"""
        print(f"Running performance benchmark for {duration} seconds...")
        
        # IOCTL constants
        MPU6050_IOC_MAGIC = ord('M')
        MPU6050_IOC_READ_RAW = (2 << 30) | (14 << 16) | (MPU6050_IOC_MAGIC << 8) | 0
        MPU6050_IOC_READ_SCALED = (2 << 30) | (28 << 16) | (MPU6050_IOC_MAGIC << 8) | 1
        
        benchmark_results = {
            'raw_reads': {'count': 0, 'total_time': 0, 'latencies': []},
            'scaled_reads': {'count': 0, 'total_time': 0, 'latencies': []}
        }
        
        # Test raw reads
        print("Benchmarking raw reads...")
        end_time = time.time() + duration / 2  # Half the time for raw reads
        
        try:
            while time.time() < end_time:
                start = time.perf_counter()
                try:
                    with open(device_path, 'rb') as device:
                        fd = device.fileno()
                        fcntl.ioctl(fd, MPU6050_IOC_READ_RAW, b'\x00' * 14)
                    
                    latency = time.perf_counter() - start
                    benchmark_results['raw_reads']['latencies'].append(latency)
                    benchmark_results['raw_reads']['count'] += 1
                    benchmark_results['raw_reads']['total_time'] += latency
                    
                except Exception:
                    pass
        
        except Exception as e:
            print(f"Raw read benchmark error: {e}")
        
        # Test scaled reads
        print("Benchmarking scaled reads...")
        end_time = time.time() + duration / 2  # Half the time for scaled reads
        
        try:
            while time.time() < end_time:
                start = time.perf_counter()
                try:
                    with open(device_path, 'rb') as device:
                        fd = device.fileno()
                        fcntl.ioctl(fd, MPU6050_IOC_READ_SCALED, b'\x00' * 28)
                    
                    latency = time.perf_counter() - start
                    benchmark_results['scaled_reads']['latencies'].append(latency)
                    benchmark_results['scaled_reads']['count'] += 1
                    benchmark_results['scaled_reads']['total_time'] += latency
                    
                except Exception:
                    pass
        
        except Exception as e:
            print(f"Scaled read benchmark error: {e}")
        
        # Calculate statistics
        results = {}
        for operation, data in benchmark_results.items():
            if data['count'] > 0 and data['latencies']:
                latencies = data['latencies']
                results[operation] = {
                    'operations': data['count'],
                    'total_time': data['total_time'],
                    'throughput': data['count'] / (duration / 2),
                    'avg_latency': statistics.mean(latencies),
                    'median_latency': statistics.median(latencies),
                    'min_latency': min(latencies),
                    'max_latency': max(latencies),
                    'p95_latency': sorted(latencies)[int(0.95 * len(latencies))] if len(latencies) >= 20 else max(latencies),
                    'p99_latency': sorted(latencies)[int(0.99 * len(latencies))] if len(latencies) >= 100 else max(latencies)
                }
            else:
                results[operation] = {'error': 'No successful operations'}
        
        print("Performance benchmark results:")
        for operation, metrics in results.items():
            if 'error' not in metrics:
                print(f"  {operation}:")
                print(f"    Throughput: {metrics['throughput']:.1f} ops/sec")
                print(f"    Avg latency: {metrics['avg_latency']*1000:.2f} ms")
                print(f"    P95 latency: {metrics['p95_latency']*1000:.2f} ms")
        
        return results
    
    def _validate_sensor_data(self, data: tuple) -> bool:
        """Basic validation of sensor data"""
        if len(data) != 7:
            return False
        
        accel_x, accel_y, accel_z, temp, gyro_x, gyro_y, gyro_z = data
        
        # Basic range checks (scaled data)
        if not (-20000 <= accel_x <= 20000):  # ±20g max
            return False
        if not (-20000 <= accel_y <= 20000):
            return False
        if not (-20000 <= accel_z <= 20000):
            return False
        
        if not (-4000 <= temp <= 8500):  # -40°C to 85°C
            return False
        
        if not (-2000000 <= gyro_x <= 2000000):  # ±2000°/s max in mdps
            return False
        if not (-2000000 <= gyro_y <= 2000000):
            return False
        if not (-2000000 <= gyro_z <= 2000000):
            return False
        
        return True
    
    def cleanup(self):
        """Cleanup any running processes"""
        for process in self.active_processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
        
        self.active_processes.clear()