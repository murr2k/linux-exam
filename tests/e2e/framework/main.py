#!/usr/bin/env python3
"""
MPU-6050 Test Framework Main Entry Point

This is the main executable for the MPU-6050 end-to-end test framework.
It provides command-line interface for running comprehensive tests.

Usage:
    python3 main.py [options] [test_suite]
    python3 main.py --config config.json --suite all --verbose

Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path

# Add framework directory to Python path
framework_dir = Path(__file__).parent
sys.path.insert(0, str(framework_dir))

from test_framework import TestFramework, TestConfig


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('test_framework.log')
        ]
    )


def load_config(config_path: str) -> TestConfig:
    """Load test configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return TestConfig(**config_data)
        
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        print("Using default configuration...")
        return TestConfig()
    
    except json.JSONDecodeError as e:
        print(f"Error parsing configuration file: {e}")
        print("Using default configuration...")
        return TestConfig()
    
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Using default configuration...")
        return TestConfig()


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='MPU-6050 End-to-End Test Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Suites:
  module_tests          Module loading and initialization tests
  basic_functionality   Basic device functionality tests  
  data_operations       Data reading and validation tests
  performance_tests     Performance and stress tests
  stress_tests          Long-duration stress and stability tests
  all                   Run all test suites (default)

Examples:
  %(prog)s                              # Run all tests with defaults
  %(prog)s --verbose basic_functionality # Run basic tests with verbose output
  %(prog)s --config my_config.json      # Use custom configuration
  %(prog)s --suite performance_tests    # Run only performance tests
  %(prog)s --dry-run                    # Show what would be executed
  %(prog)s --list-suites                # List available test suites

For more information, see the project documentation.
        """
    )
    
    # Configuration options
    parser.add_argument(
        '--config', '-c',
        default='test_config.json',
        help='Configuration file path (default: test_config.json)'
    )
    
    # Test selection
    parser.add_argument(
        '--suite', '-s',
        default='all',
        choices=['module_tests', 'basic_functionality', 'data_operations', 
                'performance_tests', 'stress_tests', 'all'],
        help='Test suite to run (default: all)'
    )
    
    parser.add_argument(
        '--test', '-t',
        help='Run specific test by name (e.g., module_tests::test_module_loading)'
    )
    
    # Output options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-essential output'
    )
    
    # Execution options
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be executed without running tests'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=3600,
        help='Test timeout in seconds (default: 3600)'
    )
    
    parser.add_argument(
        '--parallel-jobs', '-j',
        type=int,
        default=1,
        help='Number of parallel test jobs (default: 1)'
    )
    
    # Output files
    parser.add_argument(
        '--results',
        default='test_results.json',
        help='Results output file (default: test_results.json)'
    )
    
    parser.add_argument(
        '--html-report',
        help='Generate HTML report at specified path'
    )
    
    parser.add_argument(
        '--junit-xml',
        help='Generate JUnit XML report at specified path'
    )
    
    # Device configuration
    parser.add_argument(
        '--device',
        default='/dev/mpu6050',
        help='Device path (default: /dev/mpu6050)'
    )
    
    parser.add_argument(
        '--module-path',
        default='../drivers/mpu6050_driver.ko',
        help='Kernel module path (default: ../drivers/mpu6050_driver.ko)'
    )
    
    # Information options
    parser.add_argument(
        '--list-suites',
        action='store_true',
        help='List available test suites and exit'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='MPU-6050 Test Framework 1.0.0'
    )
    
    return parser


def list_test_suites():
    """List available test suites"""
    suites = {
        'module_tests': 'Module loading and initialization tests',
        'basic_functionality': 'Basic device functionality tests',
        'data_operations': 'Data reading and validation tests',
        'performance_tests': 'Performance and stress tests',
        'stress_tests': 'Long-duration stress and stability tests',
        'all': 'Run all test suites'
    }
    
    print("Available test suites:")
    for suite_name, description in suites.items():
        print(f"  {suite_name:20} - {description}")


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle information requests
    if args.list_suites:
        list_test_suites()
        return 0
    
    # Setup logging
    if args.quiet:
        verbose = False
    else:
        verbose = args.verbose
    
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override configuration with command line arguments
    if args.device:
        config.device_path = args.device
    
    if args.module_path:
        config.module_path = args.module_path
    
    config.verbose = verbose
    
    # Validate configuration
    if not os.path.exists(config.module_path):
        logger.error(f"Module file not found: {config.module_path}")
        logger.info("Please compile the module first with: make -C drivers/")
        return 1
    
    # Show dry-run information
    if args.dry_run:
        print("DRY RUN MODE - No tests will be executed")
        print(f"Configuration:")
        print(f"  Device path: {config.device_path}")
        print(f"  Module path: {config.module_path}")
        print(f"  Test suite: {args.suite}")
        print(f"  Timeout: {args.timeout}s")
        print(f"  Parallel jobs: {args.parallel_jobs}")
        print(f"  Verbose: {verbose}")
        
        if args.test:
            print(f"  Specific test: {args.test}")
        
        return 0
    
    # Create test framework
    try:
        framework = TestFramework(config)
        logger.info("Test framework initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize test framework: {e}")
        return 1
    
    # Run tests
    try:
        if args.test:
            # Run specific test
            logger.info(f"Running specific test: {args.test}")
            # Parse test name
            if '::' in args.test:
                suite_name, test_name = args.test.split('::', 1)
                results = framework.run_test_suite(suite_name)
            else:
                logger.error("Invalid test name format. Use: suite_name::test_name")
                return 1
        
        elif args.suite == 'all':
            # Run all tests
            logger.info("Running all test suites...")
            results = framework.run_all_tests()
        
        else:
            # Run specific suite
            logger.info(f"Running test suite: {args.suite}")
            results = framework.run_test_suite(args.suite)
        
    except KeyboardInterrupt:
        logger.info("Test execution interrupted by user")
        return 130  # Standard exit code for SIGINT
    
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return 1
    
    # Save results
    try:
        if args.results:
            framework.save_results(args.results)
            logger.info(f"Results saved to: {args.results}")
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
    
    # Generate additional reports
    try:
        if args.html_report:
            report_data = framework.generate_final_report()
            framework.report_generator.generate_html_report(report_data, args.html_report)
            logger.info(f"HTML report generated: {args.html_report}")
        
        if args.junit_xml:
            report_data = framework.generate_final_report()
            framework.report_generator.generate_junit_xml(report_data, args.junit_xml)
            logger.info(f"JUnit XML report generated: {args.junit_xml}")
    
    except Exception as e:
        logger.error(f"Failed to generate additional reports: {e}")
    
    # Print summary
    framework.print_summary()
    
    # Determine exit code
    if results:
        failed_tests = [r for r in results if not r.passed]
        return 1 if failed_tests else 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())