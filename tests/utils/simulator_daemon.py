#!/usr/bin/env python3
"""
MPU-6050 I2C Simulator Daemon
Author: Murray Kopit <murr2k@gmail.com>

This daemon simulates an MPU-6050 device on the I2C bus for testing purposes.
It provides realistic sensor data with configurable noise and error conditions.
"""

import argparse
import json
import logging
import math
import os
import random
import signal
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# MPU-6050 register definitions
MPU6050_REGISTERS = {
    'WHO_AM_I': 0x75,
    'PWR_MGMT_1': 0x6B,
    'PWR_MGMT_2': 0x6C,
    'GYRO_CONFIG': 0x1B,
    'ACCEL_CONFIG': 0x1C,
    'ACCEL_XOUT_H': 0x3B,
    'ACCEL_XOUT_L': 0x3C,
    'ACCEL_YOUT_H': 0x3D,
    'ACCEL_YOUT_L': 0x3E,
    'ACCEL_ZOUT_H': 0x3F,
    'ACCEL_ZOUT_L': 0x40,
    'TEMP_OUT_H': 0x41,
    'TEMP_OUT_L': 0x42,
    'GYRO_XOUT_H': 0x43,
    'GYRO_XOUT_L': 0x44,
    'GYRO_YOUT_H': 0x45,
    'GYRO_YOUT_L': 0x46,
    'GYRO_ZOUT_H': 0x47,
    'GYRO_ZOUT_L': 0x48,
}

MPU6050_WHO_AM_I_VALUE = 0x68
MPU6050_DEFAULT_ADDRESS = 0x68

class MPU6050Simulator:
    """MPU-6050 sensor simulator with realistic data generation."""
    
    def __init__(self, bus=1, address=MPU6050_DEFAULT_ADDRESS, noise_level=0.01):
        self.bus = bus
        self.address = address
        self.noise_level = noise_level
        self.running = False
        self.start_time = time.time()
        
        # Initialize register values
        self.registers = {}
        self.reset_registers()
        
        # Simulation parameters
        self.accel_range = 2  # ±2g
        self.gyro_range = 250  # ±250°/s
        
        # Motion simulation state
        self.motion_phase = 0.0
        self.motion_frequency = 0.1  # Hz
        
        # Statistics
        self.stats = {
            'reads': 0,
            'writes': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def reset_registers(self):
        """Reset all registers to default values."""
        self.registers = {}
        
        # Set default register values
        self.registers[MPU6050_REGISTERS['WHO_AM_I']] = MPU6050_WHO_AM_I_VALUE
        self.registers[MPU6050_REGISTERS['PWR_MGMT_1']] = 0x40  # Sleep mode
        self.registers[MPU6050_REGISTERS['PWR_MGMT_2']] = 0x00
        self.registers[MPU6050_REGISTERS['GYRO_CONFIG']] = 0x00  # ±250°/s
        self.registers[MPU6050_REGISTERS['ACCEL_CONFIG']] = 0x00  # ±2g
        
        # Initialize sensor data registers
        self.update_sensor_data()
    
    def update_sensor_data(self):
        """Generate realistic sensor data with motion simulation."""
        current_time = time.time() - self.start_time
        
        # Simulate gentle motion with sine waves
        self.motion_phase += self.motion_frequency * 2 * math.pi * 0.1
        
        # Generate accelerometer data (including gravity)
        accel_x = math.sin(self.motion_phase) * 0.2  # Small motion
        accel_y = math.cos(self.motion_phase * 1.3) * 0.1
        accel_z = 1.0 + math.sin(self.motion_phase * 0.7) * 0.05  # ~1g with small variation
        
        # Add noise
        accel_x += random.gauss(0, self.noise_level)
        accel_y += random.gauss(0, self.noise_level)
        accel_z += random.gauss(0, self.noise_level)
        
        # Convert to raw values (16-bit, ±2g range)
        accel_scale = 32768 / self.accel_range
        accel_x_raw = int(accel_x * accel_scale)
        accel_y_raw = int(accel_y * accel_scale)
        accel_z_raw = int(accel_z * accel_scale)
        
        # Generate gyroscope data (rotation rates)
        gyro_x = math.sin(self.motion_phase * 2) * 10  # deg/s
        gyro_y = math.cos(self.motion_phase * 1.7) * 5
        gyro_z = math.sin(self.motion_phase * 0.3) * 2
        
        # Add noise
        gyro_x += random.gauss(0, self.noise_level * 10)
        gyro_y += random.gauss(0, self.noise_level * 10)
        gyro_z += random.gauss(0, self.noise_level * 10)
        
        # Convert to raw values (16-bit, ±250°/s range)
        gyro_scale = 32768 / self.gyro_range
        gyro_x_raw = int(gyro_x * gyro_scale)
        gyro_y_raw = int(gyro_y * gyro_scale)
        gyro_z_raw = int(gyro_z * gyro_scale)
        
        # Generate temperature data (room temperature with small variation)
        temp_celsius = 22.0 + math.sin(current_time * 0.01) * 2.0
        temp_celsius += random.gauss(0, 0.1)  # Small noise
        
        # Convert to raw temperature value
        # MPU6050 temp formula: Temp = (TEMP_OUT / 340.0) + 36.53
        temp_raw = int((temp_celsius - 36.53) * 340.0)
        
        # Update registers with sensor data
        self._set_16bit_register(MPU6050_REGISTERS['ACCEL_XOUT_H'], accel_x_raw)
        self._set_16bit_register(MPU6050_REGISTERS['ACCEL_YOUT_H'], accel_y_raw)
        self._set_16bit_register(MPU6050_REGISTERS['ACCEL_ZOUT_H'], accel_z_raw)
        
        self._set_16bit_register(MPU6050_REGISTERS['GYRO_XOUT_H'], gyro_x_raw)
        self._set_16bit_register(MPU6050_REGISTERS['GYRO_YOUT_H'], gyro_y_raw)
        self._set_16bit_register(MPU6050_REGISTERS['GYRO_ZOUT_H'], gyro_z_raw)
        
        self._set_16bit_register(MPU6050_REGISTERS['TEMP_OUT_H'], temp_raw)
    
    def _set_16bit_register(self, high_reg, value):
        """Set a 16-bit value across high and low registers."""
        # Clamp to 16-bit signed range
        value = max(-32768, min(32767, value))
        
        # Split into high and low bytes
        high_byte = (value >> 8) & 0xFF
        low_byte = value & 0xFF
        
        self.registers[high_reg] = high_byte
        self.registers[high_reg + 1] = low_byte
    
    def read_register(self, reg_addr):
        """Read a register value."""
        self.stats['reads'] += 1
        
        if reg_addr in self.registers:
            value = self.registers[reg_addr]
            self.logger.debug(f"Read register 0x{reg_addr:02X}: 0x{value:02X}")
            return value
        else:
            self.stats['errors'] += 1
            self.logger.warning(f"Read from unknown register 0x{reg_addr:02X}")
            return 0x00
    
    def write_register(self, reg_addr, value):
        """Write a register value."""
        self.stats['writes'] += 1
        
        self.logger.debug(f"Write register 0x{reg_addr:02X}: 0x{value:02X}")
        
        # Handle special registers
        if reg_addr == MPU6050_REGISTERS['PWR_MGMT_1']:
            if value & 0x80:  # Reset bit
                self.logger.info("Device reset triggered")
                self.reset_registers()
                return
        
        elif reg_addr == MPU6050_REGISTERS['GYRO_CONFIG']:
            # Update gyro range based on FS_SEL bits
            fs_sel = (value >> 3) & 0x03
            self.gyro_range = [250, 500, 1000, 2000][fs_sel]
            self.logger.info(f"Gyro range set to ±{self.gyro_range}°/s")
        
        elif reg_addr == MPU6050_REGISTERS['ACCEL_CONFIG']:
            # Update accel range based on AFS_SEL bits
            afs_sel = (value >> 3) & 0x03
            self.accel_range = [2, 4, 8, 16][afs_sel]
            self.logger.info(f"Accel range set to ±{self.accel_range}g")
        
        # Store the value
        self.registers[reg_addr] = value & 0xFF
    
    def get_stats(self):
        """Get simulator statistics."""
        runtime = datetime.now() - self.stats['start_time']
        return {
            **self.stats,
            'runtime_seconds': runtime.total_seconds(),
            'reads_per_second': self.stats['reads'] / max(1, runtime.total_seconds()),
            'writes_per_second': self.stats['writes'] / max(1, runtime.total_seconds())
        }

class SimulatorDaemon:
    """Daemon wrapper for the MPU-6050 simulator."""
    
    def __init__(self, args):
        self.args = args
        self.simulator = None
        self.running = False
        self.update_thread = None
        
        # Set up logging
        self.setup_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def setup_logging(self):
        """Configure logging based on arguments."""
        log_level = getattr(logging, self.args.log_level.upper())
        
        # Configure logging format
        log_format = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
        
        # Configure logging handlers
        handlers = []
        
        if not self.args.daemon or self.args.log_file == '-':
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(console_handler)
        
        if self.args.log_file and self.args.log_file != '-':
            # File handler
            log_path = Path(self.args.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            handlers=handlers,
            format=log_format
        )
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def start(self):
        """Start the simulator daemon."""
        self.logger.info(f"Starting MPU-6050 simulator daemon")
        self.logger.info(f"Bus: {self.args.bus}, Address: 0x{self.args.address:02X}")
        self.logger.info(f"Noise level: {self.args.noise_level}")
        
        # Create simulator
        self.simulator = MPU6050Simulator(
            bus=self.args.bus,
            address=self.args.address,
            noise_level=self.args.noise_level
        )
        
        self.running = True
        
        # Start sensor data update thread
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        
        self.logger.info("Simulator daemon started successfully")
        
        # Main loop
        try:
            while self.running:
                if self.args.status_interval > 0:
                    self.log_status()
                
                time.sleep(self.args.status_interval if self.args.status_interval > 0 else 10)
        
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        
        finally:
            self.stop()
    
    def update_loop(self):
        """Continuous sensor data update loop."""
        while self.running:
            try:
                self.simulator.update_sensor_data()
                time.sleep(self.args.update_interval)
            except Exception as e:
                self.logger.error(f"Error updating sensor data: {e}")
                time.sleep(1)
    
    def log_status(self):
        """Log current simulator status."""
        stats = self.simulator.get_stats()
        self.logger.info(
            f"Status: {stats['reads']} reads, {stats['writes']} writes, "
            f"{stats['errors']} errors, {stats['runtime_seconds']:.1f}s runtime, "
            f"{stats['reads_per_second']:.1f} reads/s"
        )
    
    def stop(self):
        """Stop the simulator daemon."""
        if not self.running:
            return
        
        self.logger.info("Stopping simulator daemon...")
        self.running = False
        
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        
        if self.simulator:
            final_stats = self.simulator.get_stats()
            self.logger.info(f"Final statistics: {json.dumps(final_stats, indent=2)}")
        
        self.logger.info("Simulator daemon stopped")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MPU-6050 I2C Simulator Daemon",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--bus', type=int, default=1,
        help='I2C bus number'
    )
    parser.add_argument(
        '--address', type=lambda x: int(x, 0), default=MPU6050_DEFAULT_ADDRESS,
        help='I2C device address (hex or decimal)'
    )
    parser.add_argument(
        '--noise-level', type=float, default=0.01,
        help='Sensor noise level (0.0 to 1.0)'
    )
    parser.add_argument(
        '--update-interval', type=float, default=0.01,
        help='Sensor data update interval in seconds'
    )
    parser.add_argument(
        '--status-interval', type=int, default=30,
        help='Status logging interval in seconds (0 to disable)'
    )
    parser.add_argument(
        '--daemon', action='store_true',
        help='Run as daemon (background process)'
    )
    parser.add_argument(
        '--log-file', type=str,
        help='Log file path (use "-" for stdout only)'
    )
    parser.add_argument(
        '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
        help='Logging level'
    )
    parser.add_argument(
        '--pid-file', type=str,
        help='PID file path for daemon mode'
    )
    
    args = parser.parse_args()
    
    # Create and start daemon
    daemon = SimulatorDaemon(args)
    
    if args.daemon:
        # Simple daemonization
        if os.fork() > 0:
            sys.exit(0)  # Parent exits
        
        # Child continues
        os.setsid()
        os.chdir('/')
        
        # Write PID file
        if args.pid_file:
            with open(args.pid_file, 'w') as f:
                f.write(str(os.getpid()))
        
        # Redirect standard streams
        if not args.log_file or args.log_file == '-':
            # Only redirect if not logging to stdout
            sys.stdin.close()
            sys.stdout.close()
            sys.stderr.close()
    
    try:
        daemon.start()
    finally:
        # Cleanup PID file
        if args.daemon and args.pid_file and os.path.exists(args.pid_file):
            os.unlink(args.pid_file)

if __name__ == '__main__':
    main()