#!/usr/bin/env python3
"""
Chaos Engineering Framework for Linux Kernel Driver Testing
Implements fault injection, resource exhaustion, and race condition testing.
"""

import os
import sys
import time
import random
import threading
import subprocess
import psutil
import signal
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import tempfile
import contextlib
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import struct

class FaultType(Enum):
    """Types of faults that can be injected."""
    MEMORY_ALLOCATION_FAILURE = "memory_allocation_failure"
    I2C_BUS_ERROR = "i2c_bus_error" 
    INTERRUPT_STORM = "interrupt_storm"
    TIMING_VIOLATION = "timing_violation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_FAULT = "network_fault"
    POWER_FLUCTUATION = "power_fluctuation"
    THERMAL_STRESS = "thermal_stress"
    CPU_THROTTLING = "cpu_throttling"
    MEMORY_CORRUPTION = "memory_corruption"

class ChaosIntensity(Enum):
    """Intensity levels for chaos experiments."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    EXTREME = 4

@dataclass
class ChaosExperiment:
    """Definition of a chaos experiment."""
    name: str
    fault_type: FaultType
    intensity: ChaosIntensity
    duration: float  # seconds
    target_function: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[Callable] = field(default_factory=list)
    postconditions: List[Callable] = field(default_factory=list)

@dataclass
class ChaosResult:
    """Result of a chaos experiment."""
    experiment_name: str
    fault_type: FaultType
    success: bool
    execution_time: float
    system_impact: Dict[str, Any]
    recovery_time: Optional[float] = None
    error_message: Optional[str] = None
    metrics_before: Dict[str, float] = field(default_factory=dict)
    metrics_after: Dict[str, float] = field(default_factory=dict)
    
class SystemMonitor:
    """Monitor system resources during chaos experiments."""
    
    def __init__(self, sampling_interval: float = 0.1):
        self.sampling_interval = sampling_interval
        self.monitoring = False
        self.metrics_history = []
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start system monitoring."""
        self.monitoring = True
        self.metrics_history = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
        
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return collected metrics."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
            
        if not self.metrics_history:
            return {}
            
        # Calculate aggregate metrics
        cpu_usage = [m['cpu_percent'] for m in self.metrics_history]
        memory_usage = [m['memory_percent'] for m in self.metrics_history]
        io_read = [m['io_read_bytes'] for m in self.metrics_history]
        io_write = [m['io_write_bytes'] for m in self.metrics_history]
        
        return {
            'cpu_avg': sum(cpu_usage) / len(cpu_usage),
            'cpu_max': max(cpu_usage),
            'memory_avg': sum(memory_usage) / len(memory_usage),
            'memory_max': max(memory_usage),
            'io_read_total': max(io_read) - min(io_read) if io_read else 0,
            'io_write_total': max(io_write) - min(io_write) if io_write else 0,
            'sample_count': len(self.metrics_history)
        }
        
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                
                metrics = {
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': memory.available,
                    'io_read_bytes': disk_io.read_bytes if disk_io else 0,
                    'io_write_bytes': disk_io.write_bytes if disk_io else 0,
                }
                
                self.metrics_history.append(metrics)
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                print(f"Monitor error: {e}")
                continue

class MemoryFaultInjector:
    """Inject memory allocation failures."""
    
    def __init__(self):
        self.original_malloc_fail_rate = 0
        
    @contextlib.contextmanager
    def inject_fault(self, fail_rate: float = 0.1, duration: float = 10.0):
        """Inject memory allocation failures."""
        try:
            # Enable memory allocation failure injection via sysctl
            # This requires proper kernel support (CONFIG_FAULT_INJECTION)
            subprocess.run([
                'echo', str(int(fail_rate * 100)), '>', 
                '/sys/kernel/debug/failslab/probability'
            ], shell=True, check=False)
            
            subprocess.run([
                'echo', '1', '>', '/sys/kernel/debug/failslab/ignore-gfp-wait'
            ], shell=True, check=False)
            
            print(f"Memory fault injection active (rate: {fail_rate})")
            yield
            
        finally:
            # Restore normal operation
            subprocess.run([
                'echo', '0', '>', '/sys/kernel/debug/failslab/probability'
            ], shell=True, check=False)
            print("Memory fault injection disabled")

class I2CFaultInjector:
    """Inject I2C bus errors and timing violations."""
    
    def __init__(self, i2c_bus: int = 1):
        self.i2c_bus = i2c_bus
        self.fault_thread = None
        self.fault_active = False
        
    @contextlib.contextmanager 
    def inject_fault(self, fault_type: str = "bus_error", intensity: ChaosIntensity = ChaosIntensity.MEDIUM):
        """Inject I2C faults."""
        try:
            self.fault_active = True
            
            if fault_type == "bus_error":
                self.fault_thread = threading.Thread(target=self._inject_bus_errors, args=(intensity,))
            elif fault_type == "timing_violation":
                self.fault_thread = threading.Thread(target=self._inject_timing_violations, args=(intensity,))
            elif fault_type == "address_collision":
                self.fault_thread = threading.Thread(target=self._inject_address_collisions, args=(intensity,))
                
            self.fault_thread.start()
            print(f"I2C fault injection active: {fault_type}")
            yield
            
        finally:
            self.fault_active = False
            if self.fault_thread:
                self.fault_thread.join(timeout=5.0)
            print("I2C fault injection disabled")
            
    def _inject_bus_errors(self, intensity: ChaosIntensity):
        """Inject random bus errors."""
        error_rate = {
            ChaosIntensity.LOW: 0.01,
            ChaosIntensity.MEDIUM: 0.05, 
            ChaosIntensity.HIGH: 0.15,
            ChaosIntensity.EXTREME: 0.3
        }[intensity]
        
        while self.fault_active:
            if random.random() < error_rate:
                # Simulate bus error by sending invalid data
                try:
                    with open(f'/dev/i2c-{self.i2c_bus}', 'wb') as f:
                        # Send corrupted data
                        f.write(b'\xFF\xFF\xFF\xFF')
                except:
                    pass  # Expected to fail
                    
            time.sleep(0.1)
            
    def _inject_timing_violations(self, intensity: ChaosIntensity):
        """Inject timing violations."""
        delay_ms = {
            ChaosIntensity.LOW: 1,
            ChaosIntensity.MEDIUM: 5,
            ChaosIntensity.HIGH: 20,
            ChaosIntensity.EXTREME: 100
        }[intensity]
        
        while self.fault_active:
            # Add artificial delays to I2C operations
            time.sleep(delay_ms / 1000.0)
            
    def _inject_address_collisions(self, intensity: ChaosIntensity):
        """Inject address collisions."""
        collision_rate = {
            ChaosIntensity.LOW: 0.005,
            ChaosIntensity.MEDIUM: 0.02,
            ChaosIntensity.HIGH: 0.08, 
            ChaosIntensity.EXTREME: 0.2
        }[intensity]
        
        while self.fault_active:
            if random.random() < collision_rate:
                # Simulate address collision by rapid access attempts
                try:
                    for _ in range(5):
                        with open(f'/dev/i2c-{self.i2c_bus}', 'rb') as f:
                            f.read(1)
                except:
                    pass
                    
            time.sleep(0.05)

class ResourceExhaustionInjector:
    """Exhaust system resources to test driver behavior."""
    
    def __init__(self):
        self.exhaustion_processes = []
        
    @contextlib.contextmanager
    def exhaust_memory(self, percentage: float = 80.0):
        """Exhaust available memory."""
        try:
            total_memory = psutil.virtual_memory().total
            target_allocation = int(total_memory * percentage / 100)
            
            print(f"Exhausting {percentage}% of memory ({target_allocation // (1024**2)} MB)")
            
            # Allocate memory in separate process to avoid affecting test runner
            process = mp.Process(target=self._allocate_memory, args=(target_allocation,))
            process.start()
            self.exhaustion_processes.append(process)
            
            # Wait for allocation to take effect
            time.sleep(2.0)
            yield
            
        finally:
            for process in self.exhaustion_processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5.0)
            self.exhaustion_processes.clear()
            print("Memory exhaustion ended")
            
    @contextlib.contextmanager
    def exhaust_cpu(self, percentage: float = 90.0, duration: float = 30.0):
        """Exhaust CPU resources."""
        try:
            cpu_count = psutil.cpu_count()
            target_processes = max(1, int(cpu_count * percentage / 100))
            
            print(f"Exhausting CPU with {target_processes} processes")
            
            for _ in range(target_processes):
                process = mp.Process(target=self._consume_cpu, args=(duration,))
                process.start()
                self.exhaustion_processes.append(process)
                
            yield
            
        finally:
            for process in self.exhaustion_processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5.0)
            self.exhaustion_processes.clear()
            print("CPU exhaustion ended")
            
    @contextlib.contextmanager
    def exhaust_file_descriptors(self, percentage: float = 90.0):
        """Exhaust available file descriptors."""
        opened_files = []
        try:
            # Get current limits
            soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
            target_fds = int(soft_limit * percentage / 100)
            
            print(f"Exhausting file descriptors (target: {target_fds})")
            
            # Open files until we reach the target
            for i in range(target_fds):
                try:
                    fd = os.open('/dev/null', os.O_RDONLY)
                    opened_files.append(fd)
                except OSError:
                    break  # Hit the limit
                    
            yield
            
        finally:
            for fd in opened_files:
                try:
                    os.close(fd)
                except OSError:
                    pass
            print("File descriptor exhaustion ended")
            
    def _allocate_memory(self, target_bytes: int):
        """Allocate large amount of memory."""
        chunk_size = 1024 * 1024  # 1MB chunks
        allocated_chunks = []
        
        try:
            while len(allocated_chunks) * chunk_size < target_bytes:
                chunk = bytearray(chunk_size)
                # Touch the memory to ensure it's actually allocated
                chunk[0] = 1
                chunk[-1] = 1
                allocated_chunks.append(chunk)
                
            # Keep memory allocated
            while True:
                time.sleep(1.0)
                
        except MemoryError:
            pass  # Expected when we hit limits
            
    def _consume_cpu(self, duration: float):
        """Consume CPU cycles."""
        end_time = time.time() + duration
        while time.time() < end_time:
            # Busy loop to consume CPU
            for _ in range(10000):
                pass

class RaceConditionTester:
    """Test for race conditions in driver code."""
    
    def __init__(self, num_threads: int = 10):
        self.num_threads = num_threads
        
    def test_concurrent_access(self, test_function: Callable, 
                             iterations: int = 1000) -> Dict[str, Any]:
        """Test concurrent access patterns."""
        results = {'success': 0, 'errors': [], 'race_detected': False}
        barrier = threading.Barrier(self.num_threads)
        
        def worker():
            nonlocal results
            barrier.wait()  # Synchronize start
            
            for _ in range(iterations // self.num_threads):
                try:
                    result = test_function()
                    with threading.Lock():
                        results['success'] += 1
                except Exception as e:
                    with threading.Lock():
                        results['errors'].append(str(e))
                        # Detect potential race conditions
                        if any(keyword in str(e).lower() for keyword in 
                              ['race', 'concurrent', 'deadlock', 'timeout']):
                            results['race_detected'] = True
        
        threads = []
        start_time = time.time()
        
        for _ in range(self.num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        results['execution_time'] = time.time() - start_time
        results['error_rate'] = len(results['errors']) / (results['success'] + len(results['errors']))
        
        return results
        
    def test_producer_consumer_race(self, producer_func: Callable, 
                                  consumer_func: Callable,
                                  buffer_size: int = 10) -> Dict[str, Any]:
        """Test producer-consumer race conditions."""
        import queue
        
        buffer = queue.Queue(maxsize=buffer_size)
        results = {'produced': 0, 'consumed': 0, 'errors': []}
        
        def producer():
            for i in range(100):
                try:
                    item = producer_func(i)
                    buffer.put(item, timeout=1.0)
                    with threading.Lock():
                        results['produced'] += 1
                except Exception as e:
                    with threading.Lock():
                        results['errors'].append(f"Producer: {e}")
                        
        def consumer():
            while results['consumed'] < 100:
                try:
                    item = buffer.get(timeout=2.0)
                    consumer_func(item)
                    buffer.task_done()
                    with threading.Lock():
                        results['consumed'] += 1
                except queue.Empty:
                    break
                except Exception as e:
                    with threading.Lock():
                        results['errors'].append(f"Consumer: {e}")
        
        start_time = time.time()
        
        # Start threads
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        producer_thread.start()
        consumer_thread.start()
        
        producer_thread.join()
        consumer_thread.join()
        
        results['execution_time'] = time.time() - start_time
        results['balance'] = results['produced'] - results['consumed']
        
        return results

class ChaosEngine:
    """Main chaos engineering engine."""
    
    def __init__(self):
        self.monitor = SystemMonitor()
        self.memory_injector = MemoryFaultInjector()
        self.i2c_injector = I2CFaultInjector()
        self.resource_injector = ResourceExhaustionInjector()
        self.race_tester = RaceConditionTester()
        
    def run_experiment(self, experiment: ChaosExperiment, 
                      test_function: Callable) -> ChaosResult:
        """Run a chaos experiment."""
        print(f"Starting chaos experiment: {experiment.name}")
        
        # Get baseline metrics
        baseline_metrics = self._get_system_metrics()
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        start_time = time.time()
        success = True
        error_message = None
        recovery_time = None
        
        try:
            # Apply chaos based on fault type
            if experiment.fault_type == FaultType.MEMORY_ALLOCATION_FAILURE:
                with self.memory_injector.inject_fault(
                    fail_rate=experiment.intensity.value * 0.05,
                    duration=experiment.duration
                ):
                    test_function()
                    
            elif experiment.fault_type == FaultType.I2C_BUS_ERROR:
                with self.i2c_injector.inject_fault(
                    fault_type="bus_error",
                    intensity=experiment.intensity
                ):
                    time.sleep(experiment.duration)
                    test_function()
                    
            elif experiment.fault_type == FaultType.RESOURCE_EXHAUSTION:
                exhaustion_type = experiment.parameters.get('type', 'memory')
                if exhaustion_type == 'memory':
                    with self.resource_injector.exhaust_memory(
                        percentage=experiment.intensity.value * 20
                    ):
                        test_function()
                elif exhaustion_type == 'cpu':
                    with self.resource_injector.exhaust_cpu(
                        percentage=experiment.intensity.value * 25
                    ):
                        test_function()
                        
            elif experiment.fault_type == FaultType.TIMING_VIOLATION:
                # Test race conditions
                result = self.race_tester.test_concurrent_access(
                    test_function,
                    iterations=experiment.parameters.get('iterations', 1000)
                )
                if result['race_detected'] or result['error_rate'] > 0.1:
                    success = False
                    error_message = f"Race condition detected: {result['error_rate']} error rate"
                    
            else:
                # Default: just run the test
                test_function()
                
        except Exception as e:
            success = False
            error_message = str(e)
            
        execution_time = time.time() - start_time
        
        # Measure recovery time
        recovery_start = time.time()
        try:
            # Simple recovery test
            test_function()
            recovery_time = time.time() - recovery_start
        except:
            recovery_time = None
            
        # Stop monitoring and get metrics
        final_metrics = self.monitor.stop_monitoring()
        
        return ChaosResult(
            experiment_name=experiment.name,
            fault_type=experiment.fault_type,
            success=success,
            execution_time=execution_time,
            system_impact=final_metrics,
            recovery_time=recovery_time,
            error_message=error_message,
            metrics_before=baseline_metrics,
            metrics_after=self._get_system_metrics()
        )
        
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get current system metrics."""
        try:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            
            return {
                'cpu_percent': cpu,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'io_read_mb': (disk_io.read_bytes / (1024**2)) if disk_io else 0,
                'io_write_mb': (disk_io.write_bytes / (1024**2)) if disk_io else 0
            }
        except:
            return {}

# Example chaos experiments for I2C driver testing

def create_i2c_chaos_experiments() -> List[ChaosExperiment]:
    """Create chaos experiments for I2C driver testing."""
    return [
        ChaosExperiment(
            name="Memory Allocation Failure During I2C Transaction",
            fault_type=FaultType.MEMORY_ALLOCATION_FAILURE,
            intensity=ChaosIntensity.MEDIUM,
            duration=10.0
        ),
        ChaosExperiment(
            name="I2C Bus Error Storm",
            fault_type=FaultType.I2C_BUS_ERROR,
            intensity=ChaosIntensity.HIGH,
            duration=15.0
        ),
        ChaosExperiment(
            name="System Memory Exhaustion",
            fault_type=FaultType.RESOURCE_EXHAUSTION,
            intensity=ChaosIntensity.MEDIUM,
            duration=20.0,
            parameters={'type': 'memory'}
        ),
        ChaosExperiment(
            name="CPU Exhaustion During Driver Load",
            fault_type=FaultType.RESOURCE_EXHAUSTION,
            intensity=ChaosIntensity.HIGH,
            duration=30.0,
            parameters={'type': 'cpu'}
        ),
        ChaosExperiment(
            name="Concurrent I2C Access Race Condition",
            fault_type=FaultType.TIMING_VIOLATION,
            intensity=ChaosIntensity.MEDIUM,
            duration=10.0,
            parameters={'iterations': 2000}
        )
    ]

def generate_chaos_report(results: List[ChaosResult], output_path: Path):
    """Generate chaos engineering report."""
    successful_experiments = sum(1 for r in results if r.success)
    total_experiments = len(results)
    success_rate = (successful_experiments / total_experiments * 100) if total_experiments > 0 else 0
    
    report_data = {
        'summary': {
            'total_experiments': total_experiments,
            'successful_experiments': successful_experiments,
            'failed_experiments': total_experiments - successful_experiments,
            'success_rate': round(success_rate, 2),
            'average_execution_time': round(
                sum(r.execution_time for r in results) / len(results), 2
            ) if results else 0
        },
        'experiments': [
            {
                'name': result.experiment_name,
                'fault_type': result.fault_type.value,
                'success': result.success,
                'execution_time': round(result.execution_time, 2),
                'recovery_time': round(result.recovery_time, 2) if result.recovery_time else None,
                'error_message': result.error_message,
                'system_impact': result.system_impact
            }
            for result in results
        ],
        'fault_type_analysis': {}
    }
    
    # Analyze by fault type
    fault_types = {}
    for result in results:
        fault_type = result.fault_type.value
        if fault_type not in fault_types:
            fault_types[fault_type] = {'total': 0, 'successful': 0}
        fault_types[fault_type]['total'] += 1
        if result.success:
            fault_types[fault_type]['successful'] += 1
            
    for fault_type, stats in fault_types.items():
        success_rate = (stats['successful'] / stats['total'] * 100)
        report_data['fault_type_analysis'][fault_type] = {
            'success_rate': round(success_rate, 2),
            'total_tests': stats['total']
        }
    
    with open(output_path, 'w') as f:
        json.dump(report_data, f, indent=2)
        
    print(f"\nChaos Engineering Report")
    print(f"=" * 50)
    print(f"Total Experiments: {total_experiments}")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"System Resilience Score: {success_rate:.1f}/100")
    
    print(f"\nFault Type Analysis:")
    for fault_type, analysis in report_data['fault_type_analysis'].items():
        print(f"  {fault_type}: {analysis['success_rate']:.1f}% success")
    
    print(f"\nReport saved to: {output_path}")

if __name__ == "__main__":
    import resource
    
    # Example I2C driver test function
    def mock_i2c_test():
        """Mock I2C driver test function."""
        time.sleep(0.1)  # Simulate I2C operation
        if random.random() < 0.05:  # 5% chance of failure
            raise Exception("I2C communication failed")
        return True
    
    # Run chaos experiments
    chaos_engine = ChaosEngine()
    experiments = create_i2c_chaos_experiments()
    
    results = []
    for experiment in experiments:
        result = chaos_engine.run_experiment(experiment, mock_i2c_test)
        results.append(result)
        
    generate_chaos_report(results, Path("chaos_report.json"))