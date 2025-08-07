#!/usr/bin/env python3
"""
MPU-6050 End-to-End Functional Test Suite (Python Implementation)

This Python script provides comprehensive testing of the MPU-6050 driver
with advanced features including statistical analysis, data visualization,
and long-duration stability testing.

Features:
- Statistical analysis of sensor noise and stability
- Data logging and CSV export
- Real-time data visualization (optional)
- Performance metrics collection
- Long-duration stress testing
- Automated report generation

Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import os
import sys
import time
import signal
import argparse
import csv
import json
import statistics
import struct
import fcntl
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any

# Try to import optional visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from matplotlib.dates import DateFormatter
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# MPU-6050 Constants (matching C header)
DEVICE_PATH = "/dev/mpu6050"

# IOCTL Commands
MPU6050_IOC_MAGIC = ord('M')
_IOC_READ = 2
_IOC_WRITE = 1
_IOC_NONE = 0

def _IOC(direction, type_char, nr, size):
    return (direction << 30) | (size << 16) | (type_char << 8) | nr

def _IOR(type_char, nr, size):
    return _IOC(_IOC_READ, type_char, nr, size)

def _IOW(type_char, nr, size):
    return _IOC(_IOC_WRITE, type_char, nr, size)

def _IO(type_char, nr):
    return _IOC(_IOC_NONE, type_char, nr, 0)

# IOCTL command definitions
MPU6050_IOC_READ_RAW = _IOR(MPU6050_IOC_MAGIC, 0, 14)  # struct mpu6050_raw_data
MPU6050_IOC_READ_SCALED = _IOR(MPU6050_IOC_MAGIC, 1, 28)  # struct mpu6050_scaled_data
MPU6050_IOC_SET_CONFIG = _IOW(MPU6050_IOC_MAGIC, 2, 4)  # struct mpu6050_config
MPU6050_IOC_GET_CONFIG = _IOR(MPU6050_IOC_MAGIC, 3, 4)  # struct mpu6050_config
MPU6050_IOC_RESET = _IO(MPU6050_IOC_MAGIC, 4)
MPU6050_IOC_WHO_AM_I = _IOR(MPU6050_IOC_MAGIC, 6, 1)

# Range definitions
ACCEL_RANGES = {0: 2, 1: 4, 2: 8, 3: 16}  # g
GYRO_RANGES = {0: 250, 1: 500, 2: 1000, 3: 2000}  # degrees/sec

@dataclass
class RawSensorData:
    """Raw sensor data structure"""
    accel_x: int
    accel_y: int
    accel_z: int
    temp: int
    gyro_x: int
    gyro_y: int
    gyro_z: int
    timestamp: float
    
    @classmethod
    def from_bytes(cls, data: bytes, timestamp: float = None) -> 'RawSensorData':
        """Create RawSensorData from bytes"""
        if timestamp is None:
            timestamp = time.time()
        
        # Unpack 7 signed 16-bit integers (big-endian)
        values = struct.unpack('>7h', data)
        return cls(*values, timestamp)

@dataclass
class ScaledSensorData:
    """Scaled sensor data structure"""
    accel_x: int  # mg
    accel_y: int  # mg
    accel_z: int  # mg
    temp: int     # degrees Celsius * 100
    gyro_x: int   # mdps (milli-degrees per second)
    gyro_y: int   # mdps
    gyro_z: int   # mdps
    timestamp: float
    
    @classmethod
    def from_bytes(cls, data: bytes, timestamp: float = None) -> 'ScaledSensorData':
        """Create ScaledSensorData from bytes"""
        if timestamp is None:
            timestamp = time.time()
        
        # Unpack 7 signed 32-bit integers (native endian)
        values = struct.unpack('7i', data)
        return cls(*values, timestamp)
    
    @property
    def temp_celsius(self) -> float:
        """Get temperature in degrees Celsius"""
        return self.temp / 100.0
    
    @property
    def accel_g(self) -> Tuple[float, float, float]:
        """Get acceleration in g units"""
        return (self.accel_x / 1000.0, self.accel_y / 1000.0, self.accel_z / 1000.0)
    
    @property
    def gyro_dps(self) -> Tuple[float, float, float]:
        """Get gyroscope data in degrees per second"""
        return (self.gyro_x / 1000.0, self.gyro_y / 1000.0, self.gyro_z / 1000.0)

@dataclass
class TestStatistics:
    """Test statistics and results"""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_samples: int = 0
    successful_samples: int = 0
    failed_samples: int = 0
    
    # Statistical data
    accel_stats: Optional[Dict] = None
    gyro_stats: Optional[Dict] = None
    temp_stats: Optional[Dict] = None
    
    # Performance data
    avg_read_time: float = 0.0
    min_read_time: float = float('inf')
    max_read_time: float = 0.0
    throughput: float = 0.0
    
    @property
    def duration(self) -> timedelta:
        """Get test duration"""
        end = self.end_time or datetime.now()
        return end - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Get success rate percentage"""
        if self.total_samples == 0:
            return 0.0
        return (self.successful_samples / self.total_samples) * 100.0

class MPU6050Tester:
    """MPU-6050 comprehensive test suite"""
    
    def __init__(self, device_path: str = DEVICE_PATH, verbose: bool = False):
        self.device_path = device_path
        self.verbose = verbose
        self.fd = None
        self.running = True
        self.stats = defaultdict(list)
        
        # Data collection buffers
        self.raw_data_buffer = deque(maxlen=1000)
        self.scaled_data_buffer = deque(maxlen=1000)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False
    
    def _log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        prefix = f"[{timestamp}] [{level}]"
        print(f"{prefix} {message}")
    
    def _verbose_log(self, message: str):
        """Log verbose message"""
        if self.verbose:
            self._log(message, "DEBUG")
    
    def open_device(self) -> bool:
        """Open the MPU-6050 device"""
        try:
            self.fd = os.open(self.device_path, os.O_RDWR)
            self._log(f"Successfully opened {self.device_path}")
            return True
        except Exception as e:
            self._log(f"Failed to open {self.device_path}: {e}", "ERROR")
            return False
    
    def close_device(self):
        """Close the device"""
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
            self._log("Device closed")
    
    def read_who_am_i(self) -> Optional[int]:
        """Read WHO_AM_I register"""
        try:
            result = fcntl.ioctl(self.fd, MPU6050_IOC_WHO_AM_I, b'\x00')
            who_am_i = struct.unpack('B', result)[0]
            self._verbose_log(f"WHO_AM_I: 0x{who_am_i:02X}")
            return who_am_i
        except Exception as e:
            self._log(f"Failed to read WHO_AM_I: {e}", "ERROR")
            return None
    
    def read_raw_data(self) -> Optional[RawSensorData]:
        """Read raw sensor data"""
        try:
            start_time = time.time()
            result = fcntl.ioctl(self.fd, MPU6050_IOC_READ_RAW, b'\x00' * 14)
            read_time = time.time() - start_time
            
            data = RawSensorData.from_bytes(result, start_time)
            
            # Update performance statistics
            self.stats['read_times'].append(read_time)
            
            self._verbose_log(f"Raw data: A=[{data.accel_x}, {data.accel_y}, {data.accel_z}], "
                            f"G=[{data.gyro_x}, {data.gyro_y}, {data.gyro_z}], T={data.temp}")
            
            return data
        except Exception as e:
            self._log(f"Failed to read raw data: {e}", "ERROR")
            return None
    
    def read_scaled_data(self) -> Optional[ScaledSensorData]:
        """Read scaled sensor data"""
        try:
            start_time = time.time()
            result = fcntl.ioctl(self.fd, MPU6050_IOC_READ_SCALED, b'\x00' * 28)
            read_time = time.time() - start_time
            
            data = ScaledSensorData.from_bytes(result, start_time)
            
            # Update performance statistics
            self.stats['read_times'].append(read_time)
            
            self._verbose_log(f"Scaled data: A=[{data.accel_x}, {data.accel_y}, {data.accel_z}] mg, "
                            f"G=[{data.gyro_x}, {data.gyro_y}, {data.gyro_z}] mdps, T={data.temp_celsius:.2f}°C")
            
            return data
        except Exception as e:
            self._log(f"Failed to read scaled data: {e}", "ERROR")
            return None
    
    def reset_device(self) -> bool:
        """Reset the device"""
        try:
            fcntl.ioctl(self.fd, MPU6050_IOC_RESET)
            self._log("Device reset successful")
            time.sleep(0.2)  # Wait for reset to complete
            return True
        except Exception as e:
            self._log(f"Device reset failed: {e}", "ERROR")
            return False
    
    def test_basic_functionality(self) -> TestStatistics:
        """Test basic device functionality"""
        stats = TestStatistics("Basic Functionality Test", datetime.now())
        
        self._log("Starting basic functionality test...")
        
        # Test WHO_AM_I
        who_am_i = self.read_who_am_i()
        stats.total_samples += 1
        if who_am_i == 0x68:
            stats.successful_samples += 1
            self._log("WHO_AM_I test: PASS (0x68)")
        else:
            stats.failed_samples += 1
            self._log(f"WHO_AM_I test: FAIL (expected 0x68, got 0x{who_am_i:02X})", "ERROR")
        
        # Test raw data reading
        raw_data = self.read_raw_data()
        stats.total_samples += 1
        if raw_data is not None:
            stats.successful_samples += 1
            self._log("Raw data read test: PASS")
        else:
            stats.failed_samples += 1
            self._log("Raw data read test: FAIL", "ERROR")
        
        # Test scaled data reading
        scaled_data = self.read_scaled_data()
        stats.total_samples += 1
        if scaled_data is not None:
            stats.successful_samples += 1
            self._log("Scaled data read test: PASS")
        else:
            stats.failed_samples += 1
            self._log("Scaled data read test: FAIL", "ERROR")
        
        # Test device reset
        reset_success = self.reset_device()
        stats.total_samples += 1
        if reset_success:
            stats.successful_samples += 1
            self._log("Device reset test: PASS")
        else:
            stats.failed_samples += 1
            self._log("Device reset test: FAIL", "ERROR")
        
        stats.end_time = datetime.now()
        self._log(f"Basic functionality test completed: {stats.successful_samples}/{stats.total_samples} passed")
        
        return stats
    
    def test_data_consistency(self, num_samples: int = 100) -> TestStatistics:
        """Test data consistency and calculate statistics"""
        stats = TestStatistics("Data Consistency Test", datetime.now())
        
        self._log(f"Starting data consistency test with {num_samples} samples...")
        
        accel_data = {'x': [], 'y': [], 'z': []}
        gyro_data = {'x': [], 'y': [], 'z': []}
        temp_data = []
        read_times = []
        
        for i in range(num_samples):
            if not self.running:
                break
            
            start_time = time.time()
            data = self.read_scaled_data()
            read_time = time.time() - start_time
            
            stats.total_samples += 1
            
            if data is not None:
                stats.successful_samples += 1
                
                # Collect accelerometer data
                accel_data['x'].append(data.accel_x)
                accel_data['y'].append(data.accel_y)
                accel_data['z'].append(data.accel_z)
                
                # Collect gyroscope data
                gyro_data['x'].append(data.gyro_x)
                gyro_data['y'].append(data.gyro_y)
                gyro_data['z'].append(data.gyro_z)
                
                # Collect temperature data
                temp_data.append(data.temp)
                
                # Collect timing data
                read_times.append(read_time)
                
                # Store in buffer for visualization
                self.scaled_data_buffer.append(data)
                
            else:
                stats.failed_samples += 1
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                self._verbose_log(f"Progress: {i + 1}/{num_samples} samples")
        
        # Calculate statistics
        if stats.successful_samples > 0:
            stats.accel_stats = {
                'x': self._calculate_axis_stats(accel_data['x'], 'mg'),
                'y': self._calculate_axis_stats(accel_data['y'], 'mg'),
                'z': self._calculate_axis_stats(accel_data['z'], 'mg')
            }
            
            stats.gyro_stats = {
                'x': self._calculate_axis_stats(gyro_data['x'], 'mdps'),
                'y': self._calculate_axis_stats(gyro_data['y'], 'mdps'),
                'z': self._calculate_axis_stats(gyro_data['z'], 'mdps')
            }
            
            stats.temp_stats = self._calculate_axis_stats(temp_data, '°C×100')
            
            # Performance statistics
            stats.avg_read_time = statistics.mean(read_times)
            stats.min_read_time = min(read_times)
            stats.max_read_time = max(read_times)
            stats.throughput = 1.0 / stats.avg_read_time
        
        stats.end_time = datetime.now()
        
        # Print summary
        self._print_consistency_summary(stats)
        
        return stats
    
    def _calculate_axis_stats(self, data: List[float], unit: str) -> Dict[str, Any]:
        """Calculate statistical metrics for an axis"""
        if not data:
            return {}
        
        return {
            'mean': statistics.mean(data),
            'median': statistics.median(data),
            'stdev': statistics.stdev(data) if len(data) > 1 else 0,
            'min': min(data),
            'max': max(data),
            'range': max(data) - min(data),
            'count': len(data),
            'unit': unit
        }
    
    def _print_consistency_summary(self, stats: TestStatistics):
        """Print data consistency test summary"""
        self._log("=" * 60)
        self._log("DATA CONSISTENCY TEST RESULTS")
        self._log("=" * 60)
        
        self._log(f"Test Duration: {stats.duration}")
        self._log(f"Total Samples: {stats.total_samples}")
        self._log(f"Successful Samples: {stats.successful_samples}")
        self._log(f"Success Rate: {stats.success_rate:.1f}%")
        
        if stats.accel_stats:
            self._log("\nACCELEROMETER STATISTICS:")
            for axis in ['x', 'y', 'z']:
                s = stats.accel_stats[axis]
                self._log(f"  {axis.upper()}: {s['mean']:.1f} ± {s['stdev']:.1f} mg "
                         f"(range: {s['min']:.1f} to {s['max']:.1f} mg)")
        
        if stats.gyro_stats:
            self._log("\nGYROSCOPE STATISTICS:")
            for axis in ['x', 'y', 'z']:
                s = stats.gyro_stats[axis]
                self._log(f"  {axis.upper()}: {s['mean']:.1f} ± {s['stdev']:.1f} mdps "
                         f"(range: {s['min']:.1f} to {s['max']:.1f} mdps)")
        
        if stats.temp_stats:
            s = stats.temp_stats
            temp_celsius_mean = s['mean'] / 100.0
            temp_celsius_stdev = s['stdev'] / 100.0
            self._log(f"\nTEMPERATURE STATISTICS:")
            self._log(f"  Temperature: {temp_celsius_mean:.2f} ± {temp_celsius_stdev:.2f} °C")
        
        self._log(f"\nPERFORMANCE STATISTICS:")
        self._log(f"  Average Read Time: {stats.avg_read_time*1000:.2f} ms")
        self._log(f"  Read Time Range: {stats.min_read_time*1000:.2f} - {stats.max_read_time*1000:.2f} ms")
        self._log(f"  Throughput: {stats.throughput:.1f} reads/sec")
        
        self._log("=" * 60)
    
    def test_stability(self, duration_minutes: int = 5) -> TestStatistics:
        """Test long-term stability"""
        stats = TestStatistics("Stability Test", datetime.now())
        duration_seconds = duration_minutes * 60
        end_time = time.time() + duration_seconds
        
        self._log(f"Starting {duration_minutes}-minute stability test...")
        
        sample_interval = 1.0  # 1 second between samples
        next_sample_time = time.time()
        
        while time.time() < end_time and self.running:
            if time.time() >= next_sample_time:
                data = self.read_scaled_data()
                stats.total_samples += 1
                
                if data is not None:
                    stats.successful_samples += 1
                    self.scaled_data_buffer.append(data)
                else:
                    stats.failed_samples += 1
                
                next_sample_time += sample_interval
                
                # Progress report every minute
                elapsed = time.time() - (end_time - duration_seconds)
                if stats.total_samples % 60 == 0:
                    remaining = int((end_time - time.time()) / 60)
                    self._log(f"Stability test progress: {elapsed/60:.1f}/{duration_minutes} minutes "
                             f"(remaining: {remaining} min)")
            
            time.sleep(0.1)  # Short sleep to prevent busy waiting
        
        stats.end_time = datetime.now()
        self._log(f"Stability test completed: {stats.successful_samples}/{stats.total_samples} samples "
                 f"({stats.success_rate:.1f}% success rate)")
        
        return stats
    
    def test_performance(self, num_samples: int = 1000) -> TestStatistics:
        """Test performance and throughput"""
        stats = TestStatistics("Performance Test", datetime.now())
        
        self._log(f"Starting performance test with {num_samples} samples...")
        
        read_times = []
        start_time = time.time()
        
        for i in range(num_samples):
            if not self.running:
                break
            
            sample_start = time.time()
            data = self.read_raw_data()  # Use raw data for faster reads
            read_time = time.time() - sample_start
            
            stats.total_samples += 1
            
            if data is not None:
                stats.successful_samples += 1
                read_times.append(read_time)
            else:
                stats.failed_samples += 1
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                self._verbose_log(f"Performance test progress: {i + 1}/{num_samples}")
        
        total_time = time.time() - start_time
        
        if read_times:
            stats.avg_read_time = statistics.mean(read_times)
            stats.min_read_time = min(read_times)
            stats.max_read_time = max(read_times)
            stats.throughput = len(read_times) / total_time
        
        stats.end_time = datetime.now()
        
        # Print performance summary
        self._log("=" * 60)
        self._log("PERFORMANCE TEST RESULTS")
        self._log("=" * 60)
        self._log(f"Total Samples: {stats.total_samples}")
        self._log(f"Successful Samples: {stats.successful_samples}")
        self._log(f"Success Rate: {stats.success_rate:.1f}%")
        self._log(f"Total Test Time: {total_time:.3f} seconds")
        self._log(f"Average Read Time: {stats.avg_read_time*1000:.2f} ms")
        self._log(f"Min Read Time: {stats.min_read_time*1000:.2f} ms")
        self._log(f"Max Read Time: {stats.max_read_time*1000:.2f} ms")
        self._log(f"Throughput: {stats.throughput:.1f} reads/sec")
        self._log("=" * 60)
        
        return stats
    
    def export_data_csv(self, filename: str):
        """Export collected data to CSV file"""
        if not self.scaled_data_buffer:
            self._log("No data to export", "WARNING")
            return
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'accel_x_mg', 'accel_y_mg', 'accel_z_mg',
                             'gyro_x_mdps', 'gyro_y_mdps', 'gyro_z_mdps', 'temp_celsius']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for data in self.scaled_data_buffer:
                    writer.writerow({
                        'timestamp': data.timestamp,
                        'accel_x_mg': data.accel_x,
                        'accel_y_mg': data.accel_y,
                        'accel_z_mg': data.accel_z,
                        'gyro_x_mdps': data.gyro_x,
                        'gyro_y_mdps': data.gyro_y,
                        'gyro_z_mdps': data.gyro_z,
                        'temp_celsius': data.temp_celsius
                    })
            
            self._log(f"Data exported to {filename} ({len(self.scaled_data_buffer)} samples)")
        except Exception as e:
            self._log(f"Failed to export data: {e}", "ERROR")
    
    def generate_report(self, test_results: List[TestStatistics], filename: str):
        """Generate comprehensive test report"""
        report = {
            'test_suite': 'MPU-6050 End-to-End Tests',
            'timestamp': datetime.now().isoformat(),
            'device_path': self.device_path,
            'total_tests': len(test_results),
            'test_results': []
        }
        
        total_samples = 0
        total_successful = 0
        
        for stats in test_results:
            test_data = asdict(stats)
            # Convert datetime objects to ISO strings
            test_data['start_time'] = stats.start_time.isoformat()
            if stats.end_time:
                test_data['end_time'] = stats.end_time.isoformat()
            test_data['duration_seconds'] = stats.duration.total_seconds()
            
            report['test_results'].append(test_data)
            total_samples += stats.total_samples
            total_successful += stats.successful_samples
        
        report['summary'] = {
            'total_samples': total_samples,
            'successful_samples': total_successful,
            'overall_success_rate': (total_successful / total_samples * 100) if total_samples > 0 else 0
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            self._log(f"Test report saved to {filename}")
        except Exception as e:
            self._log(f"Failed to save report: {e}", "ERROR")
    
    def visualize_data(self, duration_seconds: int = 30):
        """Real-time data visualization (requires matplotlib)"""
        if not MATPLOTLIB_AVAILABLE:
            self._log("Matplotlib not available, skipping visualization", "WARNING")
            return
        
        self._log(f"Starting {duration_seconds}-second real-time visualization...")
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('MPU-6050 Real-time Data Visualization')
        
        # Data storage for plotting
        times = deque(maxlen=100)
        accel_x, accel_y, accel_z = deque(maxlen=100), deque(maxlen=100), deque(maxlen=100)
        gyro_x, gyro_y, gyro_z = deque(maxlen=100), deque(maxlen=100), deque(maxlen=100)
        temps = deque(maxlen=100)
        
        # Initialize plots
        lines_accel = [ax1.plot([], [], label=f'Accel {axis}')[0] for axis in ['X', 'Y', 'Z']]
        lines_gyro = [ax2.plot([], [], label=f'Gyro {axis}')[0] for axis in ['X', 'Y', 'Z']]
        line_temp = ax3.plot([], [], 'r-', label='Temperature')[0]
        
        ax1.set_title('Accelerometer (mg)')
        ax1.legend()
        ax1.grid(True)
        
        ax2.set_title('Gyroscope (mdps)')
        ax2.legend()
        ax2.grid(True)
        
        ax3.set_title('Temperature (°C)')
        ax3.legend()
        ax3.grid(True)
        
        ax4.set_title('Data Statistics')
        ax4.axis('off')
        
        start_time = time.time()
        
        def update_plot(frame):
            if not self.running or time.time() - start_time > duration_seconds:
                return
            
            # Read new data
            data = self.read_scaled_data()
            if data is None:
                return
            
            # Add to buffers
            current_time = time.time() - start_time
            times.append(current_time)
            accel_x.append(data.accel_x)
            accel_y.append(data.accel_y)
            accel_z.append(data.accel_z)
            gyro_x.append(data.gyro_x)
            gyro_y.append(data.gyro_y)
            gyro_z.append(data.gyro_z)
            temps.append(data.temp_celsius)
            
            if len(times) > 1:
                # Update accelerometer plot
                for i, (line, data_series) in enumerate(zip(lines_accel, [accel_x, accel_y, accel_z])):
                    line.set_data(times, data_series)
                ax1.relim()
                ax1.autoscale_view()
                
                # Update gyroscope plot
                for i, (line, data_series) in enumerate(zip(lines_gyro, [gyro_x, gyro_y, gyro_z])):
                    line.set_data(times, data_series)
                ax2.relim()
                ax2.autoscale_view()
                
                # Update temperature plot
                line_temp.set_data(times, temps)
                ax3.relim()
                ax3.autoscale_view()
                
                # Update statistics
                ax4.clear()
                ax4.set_title('Data Statistics')
                ax4.axis('off')
                
                if len(accel_x) > 1:
                    stats_text = f"""
Samples: {len(times)}
Accel X: {statistics.mean(accel_x):.1f} ± {statistics.stdev(accel_x):.1f} mg
Accel Y: {statistics.mean(accel_y):.1f} ± {statistics.stdev(accel_y):.1f} mg  
Accel Z: {statistics.mean(accel_z):.1f} ± {statistics.stdev(accel_z):.1f} mg
Gyro X: {statistics.mean(gyro_x):.1f} ± {statistics.stdev(gyro_x):.1f} mdps
Gyro Y: {statistics.mean(gyro_y):.1f} ± {statistics.stdev(gyro_y):.1f} mdps
Gyro Z: {statistics.mean(gyro_z):.1f} ± {statistics.stdev(gyro_z):.1f} mdps
Temperature: {statistics.mean(temps):.2f} ± {statistics.stdev(temps):.2f} °C
                    """
                    ax4.text(0.1, 0.9, stats_text.strip(), transform=ax4.transAxes, 
                            verticalalignment='top', fontfamily='monospace')
        
        # Start animation
        ani = animation.FuncAnimation(fig, update_plot, interval=50, blit=False)
        plt.tight_layout()
        plt.show()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='MPU-6050 End-to-End Test Suite (Python)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-d', '--device', default=DEVICE_PATH, help='Device path (default: /dev/mpu6050)')
    parser.add_argument('--basic', action='store_true', help='Run basic functionality test only')
    parser.add_argument('--consistency', type=int, metavar='N', help='Run consistency test with N samples')
    parser.add_argument('--stability', type=int, metavar='MIN', help='Run stability test for MIN minutes')
    parser.add_argument('--performance', type=int, metavar='N', help='Run performance test with N samples')
    parser.add_argument('--visualize', type=int, metavar='SEC', help='Run real-time visualization for SEC seconds')
    parser.add_argument('--export-csv', metavar='FILE', help='Export collected data to CSV file')
    parser.add_argument('--report', metavar='FILE', help='Generate JSON report file')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = MPU6050Tester(device_path=args.device, verbose=args.verbose)
    
    # Open device
    if not tester.open_device():
        return 1
    
    try:
        test_results = []
        
        # Determine which tests to run
        run_all = args.all or not any([args.basic, args.consistency, args.stability, 
                                      args.performance, args.visualize])
        
        # Basic functionality test
        if args.basic or run_all:
            result = tester.test_basic_functionality()
            test_results.append(result)
        
        # Data consistency test
        if args.consistency or run_all:
            samples = args.consistency if args.consistency else 100
            result = tester.test_data_consistency(samples)
            test_results.append(result)
        
        # Stability test
        if args.stability or run_all:
            minutes = args.stability if args.stability else 5
            result = tester.test_stability(minutes)
            test_results.append(result)
        
        # Performance test
        if args.performance or run_all:
            samples = args.performance if args.performance else 1000
            result = tester.test_performance(samples)
            test_results.append(result)
        
        # Real-time visualization
        if args.visualize:
            tester.visualize_data(args.visualize)
        
        # Export data to CSV
        if args.export_csv:
            tester.export_data_csv(args.export_csv)
        
        # Generate report
        if args.report and test_results:
            tester.generate_report(test_results, args.report)
        
        # Print final summary
        if test_results:
            total_tests = len(test_results)
            passed_tests = sum(1 for r in test_results if r.success_rate > 90)
            
            print("\n" + "="*60)
            print("FINAL TEST SUMMARY")
            print("="*60)
            print(f"Total Test Suites: {total_tests}")
            print(f"Passed Test Suites: {passed_tests}")
            print(f"Overall Success Rate: {(passed_tests/total_tests)*100:.1f}%")
            print("="*60)
            
            return 0 if passed_tests == total_tests else 1
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        tester._log(f"Unexpected error: {e}", "ERROR")
        return 1
    finally:
        tester.close_device()

if __name__ == "__main__":
    sys.exit(main())