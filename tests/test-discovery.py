#!/usr/bin/env python3
"""
Automatic Test Discovery and Execution Planning
Discovers available test files, checks dependencies, and generates execution plans
Author: Murray Kopit <murr2k@gmail.com>
"""

import os
import sys
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse
import logging


@dataclass
class TestFile:
    """Represents a single test file"""
    path: str
    category: str
    language: str
    dependencies: List[str]
    can_run: bool
    skip_reason: str = ""


@dataclass
class TestCategory:
    """Represents a test category"""
    name: str
    files: List[TestFile]
    dependencies: List[str]
    can_run: bool
    skip_reason: str = ""


@dataclass
class TestPlan:
    """Represents the complete test execution plan"""
    categories: List[TestCategory]
    total_files: int
    runnable_files: int
    skipped_files: int
    missing_dependencies: Set[str]
    timestamp: str


class TestDiscovery:
    """Main test discovery and planning engine"""
    
    # Test file patterns by language
    TEST_PATTERNS = {
        'c': ['*.c'],
        'cpp': ['*.cpp', '*.cc', '*.cxx'],
        'python': ['*.py', 'test_*.py', '*_test.py'],
    }
    
    # Dependencies required for each test category
    CATEGORY_DEPENDENCIES = {
        'unit': ['gcc', 'g++', 'cunit'],
        'integration': ['gcc', 'g++', 'cunit'],
        'e2e': ['python3', 'pytest'],
        'performance': ['gcc', 'g++', 'cunit'],
        'property': ['gcc', 'g++', 'cunit'],
        'mutation': ['gcc', 'g++', 'cunit'],
        'coverage': ['gcc', 'g++', 'lcov', 'gcov'],
    }
    
    # Language-specific dependencies
    LANGUAGE_DEPENDENCIES = {
        'c': ['gcc'],
        'cpp': ['g++'],
        'python': ['python3'],
    }
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.test_dir = self.project_root / 'tests'
        self.results_dir = self.project_root / 'test-results'
        self.fixtures_dir = self.test_dir / 'fixtures'
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def command_exists(self, command: str) -> bool:
        """Check if a command exists in the system PATH"""
        try:
            subprocess.run(['which', command], 
                         capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def check_dependencies(self, deps: List[str]) -> Tuple[bool, List[str]]:
        """Check if all dependencies are available"""
        missing = [dep for dep in deps if not self.command_exists(dep)]
        return len(missing) == 0, missing
    
    def detect_language(self, file_path: Path) -> str:
        """Detect the programming language of a test file"""
        suffix = file_path.suffix.lower()
        if suffix == '.c':
            return 'c'
        elif suffix in ['.cpp', '.cc', '.cxx']:
            return 'cpp'
        elif suffix == '.py':
            return 'python'
        else:
            return 'unknown'
    
    def find_test_files(self, category_dir: Path) -> List[Path]:
        """Find all test files in a category directory"""
        if not category_dir.exists():
            return []
        
        test_files = []
        for pattern_list in self.TEST_PATTERNS.values():
            for pattern in pattern_list:
                test_files.extend(category_dir.glob(pattern))
        
        # Also check subdirectories
        for subdir in category_dir.iterdir():
            if subdir.is_dir():
                for pattern_list in self.TEST_PATTERNS.values():
                    for pattern in pattern_list:
                        test_files.extend(subdir.glob(pattern))
        
        return list(set(test_files))  # Remove duplicates
    
    def analyze_test_file(self, file_path: Path, category: str) -> TestFile:
        """Analyze a single test file and determine if it can run"""
        language = self.detect_language(file_path)
        
        # Determine dependencies
        deps = []
        deps.extend(self.CATEGORY_DEPENDENCIES.get(category, []))
        deps.extend(self.LANGUAGE_DEPENDENCIES.get(language, []))
        
        # Check if file can run
        can_run, missing = self.check_dependencies(deps)
        skip_reason = ""
        
        if not can_run:
            skip_reason = f"Missing dependencies: {', '.join(missing)}"
        elif language == 'unknown':
            can_run = False
            skip_reason = f"Unknown file type: {file_path.suffix}"
        
        return TestFile(
            path=str(file_path.relative_to(self.project_root)),
            category=category,
            language=language,
            dependencies=deps,
            can_run=can_run,
            skip_reason=skip_reason
        )
    
    def discover_category(self, category_name: str) -> TestCategory:
        """Discover all tests in a specific category"""
        category_dir = self.test_dir / category_name
        
        # Find all test files
        test_files_paths = self.find_test_files(category_dir)
        test_files = [
            self.analyze_test_file(path, category_name) 
            for path in test_files_paths
        ]
        
        # Check category-level dependencies
        category_deps = self.CATEGORY_DEPENDENCIES.get(category_name, [])
        can_run_category, missing_category = self.check_dependencies(category_deps)
        
        skip_reason = ""
        if not category_dir.exists():
            can_run_category = False
            skip_reason = f"Category directory not found: {category_dir}"
        elif not test_files:
            can_run_category = False
            skip_reason = "No test files found"
        elif not can_run_category:
            skip_reason = f"Missing category dependencies: {', '.join(missing_category)}"
        
        return TestCategory(
            name=category_name,
            files=test_files,
            dependencies=category_deps,
            can_run=can_run_category,
            skip_reason=skip_reason
        )
    
    def discover_all_tests(self) -> TestPlan:
        """Discover all tests in the project"""
        self.logger.info(f"Discovering tests in {self.test_dir}")
        
        # Get all category directories
        categories = []
        for category_name in self.CATEGORY_DEPENDENCIES.keys():
            category = self.discover_category(category_name)
            categories.append(category)
        
        # Also discover any additional categories
        if self.test_dir.exists():
            for item in self.test_dir.iterdir():
                if item.is_dir() and item.name not in self.CATEGORY_DEPENDENCIES:
                    category = self.discover_category(item.name)
                    if category.files:  # Only add if it has test files
                        categories.append(category)
        
        # Calculate statistics
        total_files = sum(len(cat.files) for cat in categories)
        runnable_files = sum(len([f for f in cat.files if f.can_run]) for cat in categories)
        skipped_files = total_files - runnable_files
        
        # Collect all missing dependencies
        missing_deps = set()
        for category in categories:
            for file in category.files:
                if not file.can_run and file.dependencies:
                    _, missing = self.check_dependencies(file.dependencies)
                    missing_deps.update(missing)
        
        return TestPlan(
            categories=categories,
            total_files=total_files,
            runnable_files=runnable_files,
            skipped_files=skipped_files,
            missing_dependencies=missing_deps,
            timestamp=datetime.now().isoformat()
        )
    
    def generate_junit_xml_for_skipped(self, test_file: TestFile) -> str:
        """Generate JUnit XML for a skipped test"""
        root = ET.Element('testsuite')
        root.set('name', f"{test_file.category}.{Path(test_file.path).stem}")
        root.set('tests', '1')
        root.set('failures', '0')
        root.set('errors', '0')
        root.set('skipped', '1')
        root.set('time', '0')
        
        testcase = ET.SubElement(root, 'testcase')
        testcase.set('classname', test_file.category)
        testcase.set('name', Path(test_file.path).stem)
        testcase.set('time', '0')
        
        skipped = ET.SubElement(testcase, 'skipped')
        skipped.set('message', test_file.skip_reason)
        
        return ET.tostring(root, encoding='unicode')
    
    def generate_execution_plan_xml(self, plan: TestPlan) -> None:
        """Generate JUnit XML files for all tests, including skipped ones"""
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        for category in plan.categories:
            category_dir = self.results_dir / category.name
            category_dir.mkdir(parents=True, exist_ok=True)
            
            for test_file in category.files:
                if not test_file.can_run:
                    # Generate XML for skipped test
                    xml_content = self.generate_junit_xml_for_skipped(test_file)
                    xml_file = category_dir / f"{Path(test_file.path).stem}.xml"
                    xml_file.write_text(xml_content)
    
    def save_test_plan(self, plan: TestPlan, output_file: Optional[str] = None) -> str:
        """Save the test plan to a JSON file"""
        if output_file is None:
            output_file = str(self.results_dir / 'test-plan.json')
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for JSON serialization
        plan_dict = asdict(plan)
        plan_dict['missing_dependencies'] = list(plan.missing_dependencies)
        
        with open(output_file, 'w') as f:
            json.dump(plan_dict, f, indent=2)
        
        return output_file
    
    def print_summary(self, plan: TestPlan) -> None:
        """Print a human-readable summary of the test plan"""
        print("\n" + "="*50)
        print("         TEST DISCOVERY SUMMARY")
        print("="*50)
        print(f"Total test files found: {plan.total_files}")
        print(f"Runnable test files:    {plan.runnable_files}")
        print(f"Skipped test files:     {plan.skipped_files}")
        print(f"Success rate:           {(plan.runnable_files/plan.total_files*100 if plan.total_files > 0 else 0):.1f}%")
        
        if plan.missing_dependencies:
            print(f"\nMissing dependencies: {', '.join(sorted(plan.missing_dependencies))}")
        
        print(f"\nTest Categories:")
        for category in plan.categories:
            status = "✓" if category.can_run else "✗"
            runnable = len([f for f in category.files if f.can_run])
            total = len(category.files)
            print(f"  {status} {category.name:<12} ({runnable}/{total} runnable)")
            
            if not category.can_run and category.skip_reason:
                print(f"     Reason: {category.skip_reason}")
        
        print(f"\nDetailed breakdown:")
        for category in plan.categories:
            if not category.files:
                continue
                
            print(f"\n{category.name.upper()} Tests:")
            for test_file in category.files:
                status = "✓" if test_file.can_run else "✗"
                print(f"  {status} {test_file.path}")
                if not test_file.can_run:
                    print(f"     Reason: {test_file.skip_reason}")
    
    def generate_test_data(self) -> None:
        """Generate missing test data and fixtures"""
        self.logger.info("Generating test data and fixtures...")
        
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock sensor data
        sensor_data_c = self.fixtures_dir / 'mock_sensor_data.h'
        if not sensor_data_c.exists():
            sensor_data_c.write_text('''
#ifndef MOCK_SENSOR_DATA_H
#define MOCK_SENSOR_DATA_H

// Mock MPU-6050 sensor data for testing
static const struct {
    int16_t accel_x;
    int16_t accel_y;
    int16_t accel_z;
    int16_t temp;
    int16_t gyro_x;
    int16_t gyro_y;
    int16_t gyro_z;
} mock_sensor_readings[] = {
    {1000, 2000, 15000, 23000, 100, 200, 300},
    {-500, 1500, 14000, 22500, -50, 150, 250},
    {800, -300, 16000, 24000, 75, -25, 175},
    // Add more test data as needed
};

#define MOCK_SENSOR_DATA_COUNT (sizeof(mock_sensor_readings) / sizeof(mock_sensor_readings[0]))

#endif // MOCK_SENSOR_DATA_H
''')
            self.logger.info(f"Created mock sensor data: {sensor_data_c}")
        
        # Create test configuration
        test_config = self.fixtures_dir / 'test_config.json'
        if not test_config.exists():
            config = {
                "test_timeout": 30,
                "mock_i2c_address": 0x68,
                "expected_ranges": {
                    "accel_x": [-32768, 32767],
                    "accel_y": [-32768, 32767], 
                    "accel_z": [-32768, 32767],
                    "gyro_x": [-32768, 32767],
                    "gyro_y": [-32768, 32767],
                    "gyro_z": [-32768, 32767],
                    "temperature": [-40000, 85000]
                },
                "test_i2c_bus": "/dev/i2c-1"
            }
            
            with open(test_config, 'w') as f:
                json.dump(config, f, indent=2)
            self.logger.info(f"Created test configuration: {test_config}")
        
        self.logger.info("Test data generation completed")


def main():
    parser = argparse.ArgumentParser(description='Test Discovery and Planning Tool')
    parser.add_argument('--project-root', default='.', 
                       help='Project root directory (default: current directory)')
    parser.add_argument('--output', '-o', 
                       help='Output file for test plan JSON')
    parser.add_argument('--generate-data', action='store_true',
                       help='Generate missing test data files')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--xml-only', action='store_true',
                       help='Only generate XML files for skipped tests')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize discovery
    discovery = TestDiscovery(args.project_root)
    
    # Generate test data if requested
    if args.generate_data:
        discovery.generate_test_data()
    
    # Discover tests
    plan = discovery.discover_all_tests()
    
    # Generate XML files for skipped tests
    discovery.generate_execution_plan_xml(plan)
    
    if not args.xml_only:
        # Save test plan
        output_file = discovery.save_test_plan(plan, args.output)
        print(f"Test plan saved to: {output_file}")
        
        # Print summary
        discovery.print_summary(plan)
    
    # Exit with appropriate code
    if plan.runnable_files == 0:
        sys.exit(1)  # No tests can run
    else:
        sys.exit(0)  # Some tests can run


if __name__ == '__main__':
    main()