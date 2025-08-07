#!/usr/bin/env python3
"""
Environment Manager
Central management system for multi-environment test execution and configuration.
"""

import os
import sys
import json
import yaml
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import subprocess
import importlib.util

# Import our environment management modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from validation.env_validator import EnvironmentValidator, EnvironmentConfig
from validation.dependency_checker import DependencyChecker, DependencySet, Dependency
from isolation.test_sandbox import TestSandbox, SandboxConfig, test_sandbox
from consistency.env_consistency import EnvironmentConsistencyManager, ConsistencyConfig
from monitoring.env_monitor import EnvironmentMonitor, MonitoringConfig

@dataclass
class EnvironmentProfile:
    """Complete environment profile configuration"""
    name: str
    description: str
    platform: str
    dependencies: DependencySet
    environment_variables: Dict[str, str]
    resource_limits: Dict[str, Any]
    isolation: Dict[str, Any]
    monitoring: Dict[str, Any]
    validation_config: Dict[str, Any] = field(default_factory=dict)
    consistency_config: Dict[str, Any] = field(default_factory=dict)

class EnvironmentManager:
    """Central environment management system"""
    
    def __init__(self, config_path: str = None):
        self.logger = self._setup_logging()
        self.config_path = config_path or self._find_config_file()
        self.environments = {}
        self.current_environment = None
        self.active_sandbox = None
        self.active_monitor = None
        
        if self.config_path:
            self.load_configuration()
        
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
    
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in common locations"""
        search_paths = [
            'multi_env_config.yaml',
            'tests/environment/config/multi_env_config.yaml',
            'environment_config.yaml',
            '.env_config.yaml'
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def load_configuration(self):
        """Load environment configuration from file"""
        if not self.config_path or not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        self.logger.info(f"Loading configuration from: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            if self.config_path.endswith('.json'):
                config = json.load(f)
            else:
                config = yaml.safe_load(f)
        
        # Parse environments
        self.environments = {}
        for env_name, env_data in config.get('environments', {}).items():
            profile = self._parse_environment_profile(env_name, env_data)
            self.environments[env_name] = profile
        
        self.defaults = config.get('defaults', {})
        self.selection_rules = config.get('selection_rules', [])
        self.compatibility = config.get('compatibility', {})
        self.test_configurations = config.get('test_configurations', {})
        
        self.logger.info(f"Loaded {len(self.environments)} environment profiles")
    
    def _parse_environment_profile(self, name: str, data: Dict[str, Any]) -> EnvironmentProfile:
        """Parse environment profile from configuration data"""
        # Parse dependencies
        deps_data = data.get('dependencies', {})
        dependencies = DependencySet(
            python_packages=[
                Dependency(**pkg) for pkg in deps_data.get('python_packages', [])
            ],
            system_packages=[
                Dependency(**pkg) for pkg in deps_data.get('system_packages', [])
            ],
            npm_packages=[
                Dependency(**pkg) for pkg in deps_data.get('npm_packages', [])
            ],
            binary_tools=[
                Dependency(**pkg) for pkg in deps_data.get('binary_tools', [])
            ]
        )
        
        return EnvironmentProfile(
            name=name,
            description=data.get('description', ''),
            platform=data.get('platform', 'any'),
            dependencies=dependencies,
            environment_variables=data.get('environment_variables', {}),
            resource_limits=data.get('resource_limits', {}),
            isolation=data.get('isolation', {}),
            monitoring=data.get('monitoring', {}),
            validation_config=data.get('validation', {}),
            consistency_config=data.get('consistency', {})
        )
    
    def detect_environment(self) -> str:
        """Auto-detect appropriate environment based on rules"""
        for rule in self.selection_rules:
            condition = rule.get('condition', '')
            
            if condition == 'default':
                return rule['environment']
            
            # Simple condition evaluation
            if self._evaluate_condition(condition):
                env_name = rule['environment']
                self.logger.info(f"Auto-detected environment: {env_name} (condition: {condition})")
                return env_name
        
        # Fallback to first available environment
        if self.environments:
            return list(self.environments.keys())[0]
        
        raise RuntimeError("No environments configured")
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate environment selection condition"""
        try:
            # Simple environment variable checks
            if '==' in condition:
                var, value = condition.split('==', 1)
                var = var.strip().strip('"\'')
                value = value.strip().strip('"\'')
                return os.environ.get(var) == value
            
            # Environment variable existence check
            if condition in os.environ:
                return bool(os.environ[condition])
            
            return False
        except Exception:
            return False
    
    def setup_environment(self, env_name: str = None) -> bool:
        """Setup specified environment"""
        if not env_name:
            env_name = self.detect_environment()
        
        if env_name not in self.environments:
            raise ValueError(f"Environment not found: {env_name}")
        
        profile = self.environments[env_name]
        self.current_environment = env_name
        
        self.logger.info(f"Setting up environment: {env_name}")
        
        # Step 1: Validate environment
        if not self._validate_environment(profile):
            return False
        
        # Step 2: Check dependencies
        if not self._check_dependencies(profile):
            return False
        
        # Step 3: Setup environment variables
        self._setup_environment_variables(profile)
        
        # Step 4: Create sandbox if needed
        if profile.isolation.get('filesystem_isolation') or profile.isolation.get('process_isolation'):
            self._setup_sandbox(profile)
        
        # Step 5: Start monitoring if enabled
        if profile.monitoring.get('enable_monitoring'):
            self._start_monitoring(profile)
        
        self.logger.info(f"Environment setup completed: {env_name}")
        return True
    
    def _validate_environment(self, profile: EnvironmentProfile) -> bool:
        """Validate environment prerequisites"""
        try:
            # Create validation configuration
            validation_config = EnvironmentConfig(
                name=profile.name,
                python_version=(3, 8),  # Default minimum
                required_packages=[dep.name for dep in profile.dependencies.python_packages if not dep.optional],
                system_deps=[dep.name for dep in profile.dependencies.system_packages if not dep.optional],
                env_vars=profile.environment_variables,
                ports=[],
                directories=['tests', 'src'],
                min_memory_mb=profile.resource_limits.get('max_memory_mb', 512),
                min_disk_mb=1024,
                platform_requirements=[profile.platform] if profile.platform != 'any' else []
            )
            
            validator = EnvironmentValidator()
            validator.config = validation_config
            
            if validator.validate_all():
                self.logger.info("Environment validation passed")
                return True
            else:
                self.logger.error("Environment validation failed")
                for result in validator.validation_results:
                    if not result.passed:
                        self.logger.error(f"  {result.message}")
                        if result.fix_suggestion:
                            self.logger.info(f"  Fix: {result.fix_suggestion}")
                return False
                
        except Exception as e:
            self.logger.error(f"Environment validation error: {e}")
            return False
    
    def _check_dependencies(self, profile: EnvironmentProfile) -> bool:
        """Check and optionally install dependencies"""
        try:
            checker = DependencyChecker()
            results = checker.check_all_dependencies(profile.dependencies)
            
            if results['has_missing']:
                self.logger.warning("Missing dependencies found:")
                for dep_type, missing in results.items():
                    if dep_type.endswith('_missing') and missing:
                        self.logger.warning(f"  {dep_type.replace('_missing', '')}: {missing}")
                
                # Generate installation script
                install_script = checker.generate_install_script(
                    {
                        'python': results['python_missing'],
                        'system': results['system_missing'],
                        'npm': results['npm_missing']
                    }
                )
                
                self.logger.info("Dependency installation script generated: install_dependencies.sh")
                return False
            else:
                self.logger.info("All dependencies satisfied")
                return True
                
        except Exception as e:
            self.logger.error(f"Dependency check error: {e}")
            return False
    
    def _setup_environment_variables(self, profile: EnvironmentProfile):
        """Setup environment variables"""
        for var, value in profile.environment_variables.items():
            os.environ[var] = value
            self.logger.debug(f"Set environment variable: {var}={value}")
    
    def _setup_sandbox(self, profile: EnvironmentProfile):
        """Setup test sandbox"""
        try:
            sandbox_config = SandboxConfig(
                name=profile.name,
                max_memory_mb=profile.resource_limits.get('max_memory_mb', 512),
                max_cpu_percent=profile.resource_limits.get('max_cpu_percent', 50.0),
                timeout_seconds=profile.resource_limits.get('timeout_seconds', 300),
                filesystem_isolation=profile.isolation.get('filesystem_isolation', False),
                process_isolation=profile.isolation.get('process_isolation', False),
                network_isolation=profile.isolation.get('network_isolation', False),
                cleanup_on_exit=profile.isolation.get('cleanup_on_exit', True),
                preserve_on_error=profile.isolation.get('preserve_on_error', False)
            )
            
            self.active_sandbox = TestSandbox(sandbox_config)
            self.active_sandbox.start()
            
            self.logger.info(f"Sandbox started for environment: {profile.name}")
            
        except Exception as e:
            self.logger.error(f"Sandbox setup error: {e}")
    
    def _start_monitoring(self, profile: EnvironmentProfile):
        """Start environment monitoring"""
        try:
            monitor_config = MonitoringConfig(
                name=profile.name,
                monitoring_interval=profile.monitoring.get('monitoring_interval', 5.0),
                health_check_interval=profile.monitoring.get('health_check_interval', 30.0),
                diagnostic_interval=profile.monitoring.get('diagnostic_interval', 300.0),
                enable_alerts=profile.monitoring.get('enable_alerts', True)
            )
            
            self.active_monitor = EnvironmentMonitor(monitor_config)
            self.active_monitor.start()
            
            self.logger.info(f"Monitoring started for environment: {profile.name}")
            
        except Exception as e:
            self.logger.error(f"Monitoring setup error: {e}")
    
    def run_tests_in_environment(self, test_command: List[str], env_name: str = None) -> subprocess.CompletedProcess:
        """Run tests in specified environment"""
        if env_name and env_name != self.current_environment:
            if not self.setup_environment(env_name):
                raise RuntimeError(f"Failed to setup environment: {env_name}")
        
        if not self.current_environment:
            raise RuntimeError("No environment is currently active")
        
        profile = self.environments[self.current_environment]
        
        self.logger.info(f"Running tests in environment: {self.current_environment}")
        self.logger.info(f"Test command: {' '.join(test_command)}")
        
        # Set environment variables for the test run
        env = os.environ.copy()
        env.update(profile.environment_variables)
        env['TEST_ENVIRONMENT'] = self.current_environment
        
        try:
            if self.active_sandbox:
                # Run in sandbox
                result = self.active_sandbox.run_command(
                    test_command,
                    env=env,
                    capture_output=True,
                    text=True
                )
            else:
                # Run directly
                result = subprocess.run(
                    test_command,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=profile.resource_limits.get('timeout_seconds', 300)
                )
            
            self.logger.info(f"Tests completed with return code: {result.returncode}")
            return result
            
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Tests timed out after {e.timeout} seconds")
            raise
        except Exception as e:
            self.logger.error(f"Test execution error: {e}")
            raise
    
    def validate_environment_consistency(self, baseline_snapshot: str = None) -> bool:
        """Validate environment consistency against baseline"""
        if not self.current_environment:
            raise RuntimeError("No environment is currently active")
        
        profile = self.environments[self.current_environment]
        
        try:
            consistency_config = ConsistencyConfig(
                name=profile.name,
                **profile.consistency_config
            )
            
            manager = EnvironmentConsistencyManager(consistency_config)
            
            if baseline_snapshot and os.path.exists(baseline_snapshot):
                manager.load_baseline_snapshot(baseline_snapshot)
            else:
                # Create new baseline
                baseline_path = f"{profile.name}_baseline.json"
                manager.create_baseline_snapshot(baseline_path)
                self.logger.info(f"Created baseline snapshot: {baseline_path}")
                return True
            
            return manager.validate_consistency()
            
        except Exception as e:
            self.logger.error(f"Consistency validation error: {e}")
            return False
    
    def get_environment_status(self) -> Dict[str, Any]:
        """Get current environment status and metrics"""
        if not self.current_environment:
            return {'error': 'No environment is currently active'}
        
        status = {
            'environment': self.current_environment,
            'profile': asdict(self.environments[self.current_environment]),
            'sandbox_active': self.active_sandbox is not None,
            'monitoring_active': self.active_monitor is not None,
        }
        
        if self.active_monitor:
            try:
                status['system_summary'] = self.active_monitor.get_system_summary()
            except Exception as e:
                status['monitoring_error'] = str(e)
        
        return status
    
    def cleanup_environment(self):
        """Cleanup current environment"""
        if self.active_monitor:
            self.active_monitor.stop()
            self.active_monitor = None
        
        if self.active_sandbox:
            self.active_sandbox.cleanup()
            self.active_sandbox = None
        
        if self.current_environment:
            self.logger.info(f"Cleaned up environment: {self.current_environment}")
            self.current_environment = None
    
    def list_environments(self) -> Dict[str, Dict[str, Any]]:
        """List available environments"""
        return {
            name: {
                'name': profile.name,
                'description': profile.description,
                'platform': profile.platform,
                'python_packages': len(profile.dependencies.python_packages),
                'system_packages': len(profile.dependencies.system_packages)
            }
            for name, profile in self.environments.items()
        }
    
    def get_compatibility_matrix(self) -> Dict[str, Any]:
        """Get environment compatibility information"""
        return self.compatibility
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup_environment()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Manager")
    parser.add_argument('command', choices=[
        'list', 'setup', 'validate', 'status', 'cleanup', 'run-tests'
    ])
    parser.add_argument('--config', help="Configuration file path")
    parser.add_argument('--environment', help="Environment name")
    parser.add_argument('--test-command', nargs='+', help="Test command to run")
    parser.add_argument('--baseline', help="Baseline snapshot for consistency check")
    parser.add_argument('--verbose', action='store_true', help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    manager = EnvironmentManager(args.config)
    
    try:
        if args.command == 'list':
            environments = manager.list_environments()
            print("Available environments:")
            for name, info in environments.items():
                print(f"  {name}: {info['description']}")
                print(f"    Platform: {info['platform']}")
                print(f"    Dependencies: {info['python_packages']} Python, {info['system_packages']} system")
        
        elif args.command == 'setup':
            env_name = args.environment or manager.detect_environment()
            if manager.setup_environment(env_name):
                print(f"✓ Environment setup successful: {env_name}")
            else:
                print(f"✗ Environment setup failed: {env_name}")
                sys.exit(1)
        
        elif args.command == 'validate':
            env_name = args.environment or manager.current_environment
            if not env_name:
                env_name = manager.detect_environment()
                manager.setup_environment(env_name)
            
            if manager.validate_environment_consistency(args.baseline):
                print("✓ Environment consistency validated")
            else:
                print("✗ Environment consistency check failed")
                sys.exit(1)
        
        elif args.command == 'status':
            status = manager.get_environment_status()
            print(json.dumps(status, indent=2, default=str))
        
        elif args.command == 'cleanup':
            manager.cleanup_environment()
            print("✓ Environment cleaned up")
        
        elif args.command == 'run-tests':
            if not args.test_command:
                print("Error: --test-command required for run-tests")
                sys.exit(1)
            
            result = manager.run_tests_in_environment(args.test_command, args.environment)
            print(f"Test result: {result.returncode}")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            sys.exit(result.returncode)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()