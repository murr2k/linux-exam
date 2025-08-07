#!/usr/bin/env python3
"""
MPU-6050 End-to-End Test Framework

This package provides a comprehensive end-to-end test framework for the MPU-6050
Linux kernel driver, including test orchestration, data validation, performance
testing, and comprehensive reporting.

Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__version__ = "1.0.0"
__author__ = "Murray Kopit"
__email__ = "murr2k@gmail.com"
__license__ = "GPL-2.0"

# Import main framework components
from .test_framework import (
    TestFramework,
    TestConfig,
    TestResult,
    TestSuite
)

from .validators import (
    DataValidator,
    StatisticalAnalyzer,
    NoiseAnalyzer,
    DriftDetector,
    AnomalyDetector,
    SensorLimits,
    ValidationResult,
    StatisticalMetrics,
    NoiseAnalysis,
    DriftAnalysis,
    AnomalyResult
)

from .performance import (
    PerformanceTracker,
    StressTestRunner,
    ResourceMonitor,
    PerformanceMetrics,
    ResourceMetrics,
    StressTestConfig
)

from .reports import (
    ReportGenerator,
    MetricsCollector,
    TestSummary,
    TestCase
)

__all__ = [
    # Core framework
    'TestFramework',
    'TestConfig', 
    'TestResult',
    'TestSuite',
    
    # Validators
    'DataValidator',
    'StatisticalAnalyzer',
    'NoiseAnalyzer',
    'DriftDetector',
    'AnomalyDetector',
    'SensorLimits',
    'ValidationResult',
    'StatisticalMetrics',
    'NoiseAnalysis',
    'DriftAnalysis',
    'AnomalyResult',
    
    # Performance testing
    'PerformanceTracker',
    'StressTestRunner', 
    'ResourceMonitor',
    'PerformanceMetrics',
    'ResourceMetrics',
    'StressTestConfig',
    
    # Reporting
    'ReportGenerator',
    'MetricsCollector',
    'TestSummary',
    'TestCase'
]

# Package metadata
FRAMEWORK_INFO = {
    'name': 'mpu6050-test-framework',
    'version': __version__,
    'description': 'Comprehensive end-to-end test framework for MPU-6050 Linux kernel driver',
    'author': __author__,
    'author_email': __email__,
    'license': __license__,
    'url': 'https://github.com/murr2k/linux-exam',
    'python_requires': '>=3.7',
    'keywords': ['mpu6050', 'testing', 'kernel', 'driver', 'imu', 'sensors'],
    'classifiers': [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Testing',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Topic :: System :: Operating System Kernels :: Linux'
    ]
}