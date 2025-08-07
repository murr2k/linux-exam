#!/usr/bin/env python3
"""
Test Data Generator
Generates mock sensor data, configuration files, and test databases
Author: Murray Kopit <murr2k@gmail.com>
"""

import os
import json
import sqlite3
import struct
import random
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import argparse
import logging


class TestDataGenerator:
    """Generator for various types of test data"""
    
    def __init__(self, fixtures_dir: str):
        self.fixtures_dir = Path(fixtures_dir)
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def generate_sensor_data_c(self) -> str:
        """Generate C header file with mock sensor data"""
        output_file = self.fixtures_dir / 'sensor_data.h'
        
        # Generate realistic sensor data
        data_points = []
        for i in range(100):
            # Simulate accelerometer data (±2g range, 16-bit)
            accel_x = random.randint(-16384, 16384)  # ±1g in LSB
            accel_y = random.randint(-16384, 16384)
            accel_z = random.randint(8192, 24576)    # 0.5g to 1.5g (gravity + movement)
            
            # Simulate temperature (typical range: -40°C to +85°C)
            # MPU-6050 temp formula: Temp = (TEMP_OUT/340) + 36.53
            temp_celsius = random.uniform(-40, 85)
            temp_raw = int((temp_celsius - 36.53) * 340)
            
            # Simulate gyroscope data (±250°/s range)
            gyro_x = random.randint(-8192, 8192)   # ±250°/s in LSB
            gyro_y = random.randint(-8192, 8192)
            gyro_z = random.randint(-8192, 8192)
            
            data_points.append({
                'accel_x': accel_x,
                'accel_y': accel_y, 
                'accel_z': accel_z,
                'temp': temp_raw,
                'gyro_x': gyro_x,
                'gyro_y': gyro_y,
                'gyro_z': gyro_z
            })
        
        # Generate C header content
        header_content = f'''
#ifndef SENSOR_DATA_H
#define SENSOR_DATA_H

#include <stdint.h>

/**
 * Mock MPU-6050 sensor data for testing
 * Generated on: {datetime.now().isoformat()}
 */

typedef struct {{
    int16_t accel_x;    // Accelerometer X-axis (±2g range)
    int16_t accel_y;    // Accelerometer Y-axis (±2g range)
    int16_t accel_z;    // Accelerometer Z-axis (±2g range)
    int16_t temp;       // Temperature sensor
    int16_t gyro_x;     // Gyroscope X-axis (±250°/s range)
    int16_t gyro_y;     // Gyroscope Y-axis (±250°/s range)  
    int16_t gyro_z;     // Gyroscope Z-axis (±250°/s range)
}} mpu6050_data_t;

// Test data array
static const mpu6050_data_t test_sensor_data[] = {{
'''
        
        # Add data points
        for i, point in enumerate(data_points):
            header_content += f'''    {{ {point['accel_x']:6d}, {point['accel_y']:6d}, {point['accel_z']:6d}, '''
            header_content += f'''{point['temp']:6d}, {point['gyro_x']:6d}, {point['gyro_y']:6d}, {point['gyro_z']:6d} }}'''
            if i < len(data_points) - 1:
                header_content += ','
            header_content += '\n'
        
        header_content += '''};

#define TEST_SENSOR_DATA_COUNT (sizeof(test_sensor_data) / sizeof(test_sensor_data[0]))

// Predefined test scenarios
typedef enum {
    TEST_SCENARIO_NORMAL = 0,
    TEST_SCENARIO_HIGH_ACCEL,
    TEST_SCENARIO_HIGH_GYRO,
    TEST_SCENARIO_TEMPERATURE_EXTREME,
    TEST_SCENARIO_ALL_ZEROS,
    TEST_SCENARIO_MAX_VALUES,
    TEST_SCENARIO_COUNT
} test_scenario_t;

// Scenario-specific data
static const mpu6050_data_t scenario_data[TEST_SCENARIO_COUNT] = {
    // Normal operation
    { 1000, 2000, 16384, 23000, 100, 200, 300 },
    // High acceleration
    { 30000, -25000, 20000, 23000, 100, 200, 300 },  
    // High gyroscope readings
    { 1000, 2000, 16384, 23000, 30000, -25000, 28000 },
    // Extreme temperature
    { 1000, 2000, 16384, -13000, 100, 200, 300 },  // ~-75°C
    // All zeros (potential error condition)
    { 0, 0, 0, 0, 0, 0, 0 },
    // Maximum values (saturation test)
    { 32767, 32767, 32767, 32767, 32767, 32767, 32767 }
};

// Helper functions for converting raw values
static inline float accel_raw_to_g(int16_t raw) {
    return (float)raw / 16384.0f;  // ±2g range, 16-bit
}

static inline float gyro_raw_to_dps(int16_t raw) {
    return (float)raw / 131.0f;  // ±250°/s range
}

static inline float temp_raw_to_celsius(int16_t raw) {
    return (float)raw / 340.0f + 36.53f;
}

#endif // SENSOR_DATA_H
'''
        
        with open(output_file, 'w') as f:
            f.write(header_content)
        
        self.logger.info(f"Generated C sensor data: {output_file}")
        return str(output_file)
    
    def generate_sensor_data_cpp(self) -> str:
        """Generate C++ class with mock sensor data"""
        output_file = self.fixtures_dir / 'MockSensorData.hpp'
        
        cpp_content = '''
#ifndef MOCK_SENSOR_DATA_HPP
#define MOCK_SENSOR_DATA_HPP

#include <vector>
#include <random>
#include <cmath>

/**
 * Mock sensor data generator for C++ tests
 * Provides various sensor data patterns for comprehensive testing
 */
class MockSensorData {
public:
    struct SensorReading {
        int16_t accel_x, accel_y, accel_z;
        int16_t temp;
        int16_t gyro_x, gyro_y, gyro_z;
        
        SensorReading(int16_t ax=0, int16_t ay=0, int16_t az=0, int16_t t=0,
                     int16_t gx=0, int16_t gy=0, int16_t gz=0) 
            : accel_x(ax), accel_y(ay), accel_z(az), temp(t),
              gyro_x(gx), gyro_y(gy), gyro_z(gz) {}
    };
    
    enum class Pattern {
        NORMAL,
        SINE_WAVE,
        RANDOM_WALK,
        STEP_FUNCTION,
        NOISY_CONSTANT,
        EXTREME_VALUES
    };
    
private:
    std::mt19937 rng_;
    std::vector<SensorReading> data_;
    
public:
    MockSensorData(unsigned seed = 42) : rng_(seed) {}
    
    // Generate data with specific pattern
    std::vector<SensorReading> generate(Pattern pattern, size_t count = 100) {
        data_.clear();
        data_.reserve(count);
        
        switch (pattern) {
            case Pattern::NORMAL:
                generateNormal(count);
                break;
            case Pattern::SINE_WAVE:
                generateSineWave(count);
                break;
            case Pattern::RANDOM_WALK:
                generateRandomWalk(count);
                break;
            case Pattern::STEP_FUNCTION:
                generateStepFunction(count);
                break;
            case Pattern::NOISY_CONSTANT:
                generateNoisyConstant(count);
                break;
            case Pattern::EXTREME_VALUES:
                generateExtremeValues(count);
                break;
        }
        
        return data_;
    }
    
    // Get predefined test scenarios
    static SensorReading getScenario(const std::string& name) {
        if (name == "rest") {
            return SensorReading(0, 0, 16384, 23000, 0, 0, 0);  // At rest, gravity on Z
        } else if (name == "movement") {
            return SensorReading(5000, 3000, 14000, 23000, 1000, 500, 200);
        } else if (name == "high_g") {
            return SensorReading(30000, -20000, 25000, 23000, 100, 200, 300);
        } else if (name == "rotation") {
            return SensorReading(1000, 2000, 16000, 23000, 15000, -12000, 8000);
        } else if (name == "hot") {
            return SensorReading(1000, 2000, 16000, 35000, 100, 200, 300);  // ~67°C
        } else if (name == "cold") {
            return SensorReading(1000, 2000, 16000, -10000, 100, 200, 300);  // ~-66°C
        }
        return SensorReading();  // Default: all zeros
    }
    
private:
    void generateNormal(size_t count) {
        std::normal_distribution<float> accel_dist(0, 2000);
        std::normal_distribution<float> gyro_dist(0, 500);
        std::normal_distribution<float> temp_dist(23000, 1000);
        
        for (size_t i = 0; i < count; ++i) {
            data_.emplace_back(
                static_cast<int16_t>(accel_dist(rng_)),
                static_cast<int16_t>(accel_dist(rng_)),
                static_cast<int16_t>(16384 + accel_dist(rng_) * 0.1),  // Gravity + noise
                static_cast<int16_t>(temp_dist(rng_)),
                static_cast<int16_t>(gyro_dist(rng_)),
                static_cast<int16_t>(gyro_dist(rng_)),
                static_cast<int16_t>(gyro_dist(rng_))
            );
        }
    }
    
    void generateSineWave(size_t count) {
        for (size_t i = 0; i < count; ++i) {
            float t = static_cast<float>(i) / 10.0f;  // Time scaling
            data_.emplace_back(
                static_cast<int16_t>(8000 * std::sin(t)),
                static_cast<int16_t>(8000 * std::cos(t)),
                static_cast<int16_t>(16384 + 2000 * std::sin(t * 0.5)),
                23000,  // Constant temperature
                static_cast<int16_t>(2000 * std::sin(t * 2)),
                static_cast<int16_t>(2000 * std::cos(t * 2)), 
                static_cast<int16_t>(1000 * std::sin(t * 3))
            );
        }
    }
    
    void generateRandomWalk(size_t count) {
        SensorReading current(1000, 2000, 16384, 23000, 100, 200, 300);
        std::normal_distribution<float> step(-100, 100);
        
        for (size_t i = 0; i < count; ++i) {
            current.accel_x += static_cast<int16_t>(step(rng_));
            current.accel_y += static_cast<int16_t>(step(rng_));
            current.accel_z += static_cast<int16_t>(step(rng_) * 0.1);
            current.temp += static_cast<int16_t>(step(rng_) * 0.01);
            current.gyro_x += static_cast<int16_t>(step(rng_) * 0.5);
            current.gyro_y += static_cast<int16_t>(step(rng_) * 0.5);
            current.gyro_z += static_cast<int16_t>(step(rng_) * 0.5);
            
            // Clamp to reasonable ranges
            current.accel_x = std::clamp(current.accel_x, static_cast<int16_t>(-32000), static_cast<int16_t>(32000));
            current.accel_y = std::clamp(current.accel_y, static_cast<int16_t>(-32000), static_cast<int16_t>(32000));
            current.accel_z = std::clamp(current.accel_z, static_cast<int16_t>(0), static_cast<int16_t>(32000));
            
            data_.push_back(current);
        }
    }
    
    void generateStepFunction(size_t count) {
        size_t step_size = count / 4;
        std::vector<SensorReading> steps = {
            SensorReading(0, 0, 16384, 23000, 0, 0, 0),        // Rest
            SensorReading(8000, 0, 16384, 25000, 2000, 0, 0),  // X acceleration
            SensorReading(0, 8000, 16384, 25000, 0, 2000, 0),  // Y acceleration  
            SensorReading(0, 0, 24000, 27000, 0, 0, 2000)      // Z acceleration
        };
        
        for (size_t i = 0; i < count; ++i) {
            size_t step_idx = i / step_size;
            if (step_idx >= steps.size()) step_idx = steps.size() - 1;
            data_.push_back(steps[step_idx]);
        }
    }
    
    void generateNoisyConstant(size_t count) {
        std::normal_distribution<float> noise(0, 50);
        SensorReading base(2000, 1000, 15000, 24000, 300, 200, 100);
        
        for (size_t i = 0; i < count; ++i) {
            data_.emplace_back(
                base.accel_x + static_cast<int16_t>(noise(rng_)),
                base.accel_y + static_cast<int16_t>(noise(rng_)),
                base.accel_z + static_cast<int16_t>(noise(rng_)),
                base.temp + static_cast<int16_t>(noise(rng_) * 0.1),
                base.gyro_x + static_cast<int16_t>(noise(rng_)),
                base.gyro_y + static_cast<int16_t>(noise(rng_)),
                base.gyro_z + static_cast<int16_t>(noise(rng_))
            );
        }
    }
    
    void generateExtremeValues(size_t count) {
        std::vector<SensorReading> extremes = {
            SensorReading(32767, 32767, 32767, 32767, 32767, 32767, 32767),   // Max
            SensorReading(-32768, -32768, -32768, -32768, -32768, -32768, -32768), // Min
            SensorReading(0, 0, 0, 0, 0, 0, 0),                              // Zero
            SensorReading(16384, 0, 0, 23000, 0, 0, 0),                      // 1g X only
            SensorReading(0, 16384, 0, 23000, 0, 0, 0),                      // 1g Y only
            SensorReading(0, 0, 16384, 23000, 0, 0, 0),                      // 1g Z only
        };
        
        for (size_t i = 0; i < count; ++i) {
            data_.push_back(extremes[i % extremes.size()]);
        }
    }
};

#endif // MOCK_SENSOR_DATA_HPP
'''
        
        with open(output_file, 'w') as f:
            f.write(cpp_content)
        
        self.logger.info(f"Generated C++ sensor data: {output_file}")
        return str(output_file)
    
    def generate_binary_data(self) -> str:
        """Generate binary sensor data file"""
        output_file = self.fixtures_dir / 'sensor_data.bin'
        
        # Generate 1000 sensor readings in binary format
        with open(output_file, 'wb') as f:
            for i in range(1000):
                # Each reading: 7 int16_t values (14 bytes total)
                accel_x = random.randint(-16384, 16384)
                accel_y = random.randint(-16384, 16384)  
                accel_z = random.randint(8192, 24576)
                temp = random.randint(-13000, 32767)
                gyro_x = random.randint(-8192, 8192)
                gyro_y = random.randint(-8192, 8192)
                gyro_z = random.randint(-8192, 8192)
                
                # Pack as little-endian signed 16-bit integers
                data = struct.pack('<7h', accel_x, accel_y, accel_z, temp, gyro_x, gyro_y, gyro_z)
                f.write(data)
        
        self.logger.info(f"Generated binary sensor data: {output_file} (14KB)")
        return str(output_file)
    
    def generate_config_files(self) -> List[str]:
        """Generate various configuration files for testing"""
        files_created = []
        
        # Main test configuration
        test_config = {
            "test_settings": {
                "timeout": 30,
                "max_retries": 3,
                "verbose": True
            },
            "mpu6050": {
                "i2c_address": "0x68",
                "i2c_bus": "/dev/i2c-1", 
                "sample_rate": 1000,
                "accel_range": 2,  # ±2g
                "gyro_range": 250  # ±250°/s
            },
            "test_scenarios": {
                "basic": {
                    "description": "Basic functionality test",
                    "duration": 5,
                    "expected_samples": 5000
                },
                "stress": {
                    "description": "Stress test with high sample rate",
                    "duration": 30,
                    "expected_samples": 30000
                },
                "precision": {
                    "description": "Precision and accuracy test", 
                    "duration": 10,
                    "tolerance": 0.01
                }
            },
            "validation": {
                "accel_range": [-32768, 32767],
                "gyro_range": [-32768, 32767],
                "temp_range": [-13000, 35000],
                "noise_threshold": 100
            }
        }
        
        config_file = self.fixtures_dir / 'test_config.json'
        with open(config_file, 'w') as f:
            json.dump(test_config, f, indent=2)
        files_created.append(str(config_file))
        
        # Docker test configuration
        docker_config = {
            "image": "ubuntu:22.04",
            "volumes": [
                "./:/workspace"
            ],
            "environment": {
                "DEBIAN_FRONTEND": "noninteractive",
                "TEST_MODE": "docker"
            },
            "commands": [
                "apt-get update",
                "apt-get install -y build-essential linux-headers-generic",
                "make clean",
                "make test"
            ]
        }
        
        docker_config_file = self.fixtures_dir / 'docker_test_config.json'
        with open(docker_config_file, 'w') as f:
            json.dump(docker_config, f, indent=2)
        files_created.append(str(docker_config_file))
        
        # CI/CD configuration
        ci_config = {
            "stages": ["build", "test", "coverage"],
            "build": {
                "dependencies": ["gcc", "g++", "make", "linux-headers-generic"],
                "commands": ["make clean", "make modules"]
            },
            "test": {
                "dependencies": ["cunit", "lcov", "python3", "pytest"],
                "commands": ["./scripts/test-wrapper.sh", "python3 tests/test-discovery.py"],
                "artifacts": ["test-results/", "coverage/"]
            },
            "coverage": {
                "min_threshold": 80,
                "format": "lcov",
                "exclude": ["tests/", "build/"]
            }
        }
        
        ci_config_file = self.fixtures_dir / 'ci_config.json'  
        with open(ci_config_file, 'w') as f:
            json.dump(ci_config, f, indent=2)
        files_created.append(str(ci_config_file))
        
        self.logger.info(f"Generated {len(files_created)} configuration files")
        return files_created
    
    def create_test_database(self) -> str:
        """Create SQLite database with test data"""
        db_file = self.fixtures_dir / 'test_data.db'
        
        # Remove existing database
        if db_file.exists():
            db_file.unlink()
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                accel_x INTEGER,
                accel_y INTEGER,
                accel_z INTEGER,
                temp INTEGER,
                gyro_x INTEGER,
                gyro_y INTEGER,
                gyro_z INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE test_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                status TEXT DEFAULT 'running',
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE calibration_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                accel_offset_x REAL DEFAULT 0.0,
                accel_offset_y REAL DEFAULT 0.0,
                accel_offset_z REAL DEFAULT 0.0,
                gyro_offset_x REAL DEFAULT 0.0,
                gyro_offset_y REAL DEFAULT 0.0,
                gyro_offset_z REAL DEFAULT 0.0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Insert sample data
        base_time = datetime.now()
        for i in range(1000):
            timestamp = base_time + timedelta(milliseconds=i)
            cursor.execute('''
                INSERT INTO sensor_readings 
                (timestamp, accel_x, accel_y, accel_z, temp, gyro_x, gyro_y, gyro_z)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                random.randint(-16384, 16384),
                random.randint(-16384, 16384),
                random.randint(8192, 24576), 
                random.randint(20000, 26000),
                random.randint(-8192, 8192),
                random.randint(-8192, 8192),
                random.randint(-8192, 8192)
            ))
        
        # Insert test sessions
        test_sessions = [
            ("basic_functionality", "completed", "All basic tests passed"),
            ("stress_test", "completed", "Handled 30000 samples successfully"),
            ("calibration_test", "completed", "Calibration within tolerance"),
            ("error_handling", "failed", "Simulated I2C error not handled properly"),
            ("performance_test", "running", "Long-running performance evaluation")
        ]
        
        for name, status, notes in test_sessions:
            cursor.execute('''
                INSERT INTO test_sessions (name, status, notes)
                VALUES (?, ?, ?)
            ''', (name, status, notes))
        
        # Insert calibration data
        cursor.execute('''
            INSERT INTO calibration_data 
            (accel_offset_x, accel_offset_y, accel_offset_z, gyro_offset_x, gyro_offset_y, gyro_offset_z)
            VALUES (0.02, -0.01, 0.98, 0.5, -0.3, 0.1)
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Created test database: {db_file}")
        return str(db_file)
    
    def generate_all(self) -> Dict[str, List[str]]:
        """Generate all test data and return file paths"""
        generated_files = {
            'c_headers': [],
            'cpp_files': [],
            'binary_data': [],
            'config_files': [],
            'databases': []
        }
        
        self.logger.info("Generating comprehensive test data suite...")
        
        # Generate C/C++ source files
        generated_files['c_headers'].append(self.generate_sensor_data_c())
        generated_files['cpp_files'].append(self.generate_sensor_data_cpp())
        
        # Generate binary data
        generated_files['binary_data'].append(self.generate_binary_data())
        
        # Generate configuration files
        generated_files['config_files'].extend(self.generate_config_files())
        
        # Generate database
        generated_files['databases'].append(self.create_test_database())
        
        total_files = sum(len(files) for files in generated_files.values())
        self.logger.info(f"Generated {total_files} test data files in {self.fixtures_dir}")
        
        return generated_files


def main():
    parser = argparse.ArgumentParser(description='Generate test data and fixtures')
    parser.add_argument('--fixtures-dir', 
                       default='./tests/fixtures',
                       help='Directory to store generated fixtures')
    parser.add_argument('--type', 
                       choices=['c', 'cpp', 'binary', 'config', 'database', 'all'],
                       default='all',
                       help='Type of test data to generate')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    generator = TestDataGenerator(args.fixtures_dir)
    
    if args.type == 'all':
        generated = generator.generate_all()
        print(f"\nGenerated test data files:")
        for category, files in generated.items():
            if files:
                print(f"\n{category.replace('_', ' ').title()}:")
                for file_path in files:
                    print(f"  - {file_path}")
    else:
        # Generate specific type
        if args.type == 'c':
            file_path = generator.generate_sensor_data_c()
            print(f"Generated C header: {file_path}")
        elif args.type == 'cpp':
            file_path = generator.generate_sensor_data_cpp()
            print(f"Generated C++ file: {file_path}")
        elif args.type == 'binary':
            file_path = generator.generate_binary_data()
            print(f"Generated binary data: {file_path}")
        elif args.type == 'config':
            file_paths = generator.generate_config_files()
            print(f"Generated {len(file_paths)} config files:")
            for path in file_paths:
                print(f"  - {path}")
        elif args.type == 'database':
            file_path = generator.create_test_database()
            print(f"Generated test database: {file_path}")


if __name__ == '__main__':
    main()