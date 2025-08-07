#!/usr/bin/env python3
"""
Environment Validation Framework
Validates test environment prerequisites and configuration before test execution.
"""

import os
import sys
import json
import subprocess
import platform
import socket
import importlib
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import time
import psutil

@dataclass
class ValidationResult:
    """Result of environment validation"""
    passed: bool
    message: str
    details: Dict[str, Any] = None
    fix_suggestion: str = ""

@dataclass
class EnvironmentConfig:
    """Environment configuration specification"""
    name: str
    python_version: Tuple[int, int]
    required_packages: List[str]
    system_deps: List[str]
    env_vars: Dict[str, str]
    ports: List[int]
    directories: List[str]
    min_memory_mb: int = 512
    min_disk_mb: int = 1024
    platform_requirements: List[str] = None

class EnvironmentValidator:
    """Comprehensive environment validation system"""
    
    def __init__(self, config_path: str = None):
        self.logger = self._setup_logging()
        self.config = self._load_config(config_path)
        self.validation_results = []
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_config(self, config_path: str) -> EnvironmentConfig:
        """Load environment configuration"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return EnvironmentConfig(**config_data)
        
        # Default configuration
        return EnvironmentConfig(
            name="default",
            python_version=(3, 8),
            required_packages=['pytest', 'coverage', 'numpy'],
            system_deps=['gcc', 'make', 'cmake'],
            env_vars={'PYTHONPATH': '.'},
            ports=[],
            directories=['tests', 'src', 'build'],
            min_memory_mb=512,
            min_disk_mb=1024,
            platform_requirements=['linux']
        )
    
    def validate_all(self) -> bool:
        """Run all validation checks"""
        self.logger.info(f"Starting environment validation for: {self.config.name}")
        
        # Core validations
        validations = [
            self._validate_python_version,
            self._validate_system_resources,
            self._validate_disk_space,
            self._validate_network_ports,
            self._validate_system_dependencies,
            self._validate_python_packages,
            self._validate_environment_variables,
            self._validate_directories,
            self._validate_platform,
            self._validate_permissions,
        ]
        
        all_passed = True
        
        for validation in validations:
            try:
                result = validation()
                self.validation_results.append(result)
                
                if result.passed:
                    self.logger.info(f"✓ {result.message}")
                else:
                    self.logger.error(f"✗ {result.message}")
                    if result.fix_suggestion:
                        self.logger.info(f"  Fix: {result.fix_suggestion}")
                    all_passed = False
                    
            except Exception as e:
                error_result = ValidationResult(
                    passed=False,
                    message=f"Validation error: {validation.__name__}",
                    details={"error": str(e)},
                    fix_suggestion="Check system configuration and try again"
                )
                self.validation_results.append(error_result)
                self.logger.error(f"✗ {error_result.message}: {e}")
                all_passed = False
        
        return all_passed
    
    def _validate_python_version(self) -> ValidationResult:
        """Validate Python version"""
        current = sys.version_info
        required = self.config.python_version
        
        if current >= required:
            return ValidationResult(
                passed=True,
                message=f"Python version {current.major}.{current.minor} meets requirement {required[0]}.{required[1]}"
            )
        
        return ValidationResult(
            passed=False,
            message=f"Python version {current.major}.{current.minor} below required {required[0]}.{required[1]}",
            fix_suggestion=f"Install Python {required[0]}.{required[1]} or higher"
        )
    
    def _validate_system_resources(self) -> ValidationResult:
        """Validate system memory and CPU"""
        memory = psutil.virtual_memory()
        available_mb = memory.available // (1024 * 1024)
        
        if available_mb < self.config.min_memory_mb:
            return ValidationResult(
                passed=False,
                message=f"Insufficient memory: {available_mb}MB available, {self.config.min_memory_mb}MB required",
                fix_suggestion="Free up memory or increase system RAM"
            )
        
        return ValidationResult(
            passed=True,
            message=f"Memory validation passed: {available_mb}MB available"
        )
    
    def _validate_disk_space(self) -> ValidationResult:
        """Validate disk space"""
        disk = psutil.disk_usage('.')
        free_mb = disk.free // (1024 * 1024)
        
        if free_mb < self.config.min_disk_mb:
            return ValidationResult(
                passed=False,
                message=f"Insufficient disk space: {free_mb}MB free, {self.config.min_disk_mb}MB required",
                fix_suggestion="Free up disk space"
            )
        
        return ValidationResult(
            passed=True,
            message=f"Disk space validation passed: {free_mb}MB free"
        )
    
    def _validate_network_ports(self) -> ValidationResult:
        """Validate required network ports are available"""
        if not self.config.ports:
            return ValidationResult(passed=True, message="No port validation required")
        
        blocked_ports = []
        
        for port in self.config.ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result == 0:  # Port is in use
                    blocked_ports.append(port)
        
        if blocked_ports:
            return ValidationResult(
                passed=False,
                message=f"Ports in use: {blocked_ports}",
                fix_suggestion=f"Stop processes using ports {blocked_ports}"
            )
        
        return ValidationResult(
            passed=True,
            message=f"All required ports available: {self.config.ports}"
        )
    
    def _validate_system_dependencies(self) -> ValidationResult:
        """Validate system dependencies"""
        missing_deps = []
        
        for dep in self.config.system_deps:
            try:
                subprocess.run(['which', dep], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                missing_deps.append(dep)
        
        if missing_deps:
            return ValidationResult(
                passed=False,
                message=f"Missing system dependencies: {missing_deps}",
                fix_suggestion=f"Install dependencies: {' '.join(missing_deps)}"
            )
        
        return ValidationResult(
            passed=True,
            message="All system dependencies available"
        )
    
    def _validate_python_packages(self) -> ValidationResult:
        """Validate Python packages"""
        missing_packages = []
        
        for package in self.config.required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            return ValidationResult(
                passed=False,
                message=f"Missing Python packages: {missing_packages}",
                fix_suggestion=f"Install packages: pip install {' '.join(missing_packages)}"
            )
        
        return ValidationResult(
            passed=True,
            message="All Python packages available"
        )
    
    def _validate_environment_variables(self) -> ValidationResult:
        """Validate environment variables"""
        missing_vars = []
        
        for var, expected_value in self.config.env_vars.items():
            actual_value = os.environ.get(var)
            if actual_value != expected_value:
                missing_vars.append(f"{var}={expected_value}")
        
        if missing_vars:
            return ValidationResult(
                passed=False,
                message=f"Environment variables not set: {missing_vars}",
                fix_suggestion=f"Set environment variables: {', '.join(missing_vars)}"
            )
        
        return ValidationResult(
            passed=True,
            message="All environment variables configured"
        )
    
    def _validate_directories(self) -> ValidationResult:
        """Validate required directories exist"""
        missing_dirs = []
        
        for directory in self.config.directories:
            if not os.path.exists(directory):
                missing_dirs.append(directory)
        
        if missing_dirs:
            return ValidationResult(
                passed=False,
                message=f"Missing directories: {missing_dirs}",
                fix_suggestion=f"Create directories: mkdir -p {' '.join(missing_dirs)}"
            )
        
        return ValidationResult(
            passed=True,
            message="All required directories exist"
        )
    
    def _validate_platform(self) -> ValidationResult:
        """Validate platform requirements"""
        if not self.config.platform_requirements:
            return ValidationResult(passed=True, message="No platform validation required")
        
        current_platform = platform.system().lower()
        
        if current_platform not in [p.lower() for p in self.config.platform_requirements]:
            return ValidationResult(
                passed=False,
                message=f"Platform {current_platform} not in required platforms: {self.config.platform_requirements}",
                fix_suggestion="Run tests on a supported platform"
            )
        
        return ValidationResult(
            passed=True,
            message=f"Platform validation passed: {current_platform}"
        )
    
    def _validate_permissions(self) -> ValidationResult:
        """Validate file system permissions"""
        test_file = "test_permissions.tmp"
        
        try:
            # Test write permissions
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Test read permissions
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Clean up
            os.remove(test_file)
            
            return ValidationResult(
                passed=True,
                message="File system permissions validated"
            )
            
        except Exception as e:
            return ValidationResult(
                passed=False,
                message=f"Permission validation failed: {e}",
                fix_suggestion="Check file system permissions"
            )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        passed_count = sum(1 for r in self.validation_results if r.passed)
        total_count = len(self.validation_results)
        
        return {
            'timestamp': time.time(),
            'environment': self.config.name,
            'summary': {
                'total_checks': total_count,
                'passed': passed_count,
                'failed': total_count - passed_count,
                'success_rate': passed_count / total_count if total_count > 0 else 0
            },
            'results': [
                {
                    'passed': r.passed,
                    'message': r.message,
                    'details': r.details,
                    'fix_suggestion': r.fix_suggestion
                }
                for r in self.validation_results
            ],
            'system_info': {
                'platform': platform.system(),
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
                'memory_mb': psutil.virtual_memory().total // (1024 * 1024),
                'cpu_count': psutil.cpu_count()
            }
        }
    
    def save_report(self, output_path: str = "validation_report.json"):
        """Save validation report to file"""
        report = self.generate_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Validation report saved to: {output_path}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Validation Framework")
    parser.add_argument('--config', help="Configuration file path")
    parser.add_argument('--report', help="Output report path", default="validation_report.json")
    parser.add_argument('--verbose', action='store_true', help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = EnvironmentValidator(args.config)
    success = validator.validate_all()
    validator.save_report(args.report)
    
    if success:
        print("✓ Environment validation passed")
        sys.exit(0)
    else:
        print("✗ Environment validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()