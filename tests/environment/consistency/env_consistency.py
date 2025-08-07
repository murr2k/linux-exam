#!/usr/bin/env python3
"""
Environment Consistency Manager
Ensures reproducible and consistent test environments across different systems and runs.
"""

import os
import sys
import json
import hashlib
import shutil
import subprocess
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime
import yaml

@dataclass
class EnvironmentSnapshot:
    """Snapshot of environment state"""
    timestamp: float
    python_version: str
    system_info: Dict[str, str]
    environment_variables: Dict[str, str]
    installed_packages: Dict[str, str]
    file_checksums: Dict[str, str]
    configuration_hash: str
    git_commit: Optional[str] = None

@dataclass
class ConsistencyConfig:
    """Configuration for environment consistency"""
    name: str
    snapshot_file: str = "env_snapshot.json"
    track_env_vars: List[str] = field(default_factory=lambda: [
        'PATH', 'PYTHONPATH', 'HOME', 'USER', 'SHELL'
    ])
    track_packages: bool = True
    track_files: List[str] = field(default_factory=list)
    ignore_patterns: List[str] = field(default_factory=lambda: [
        '*.pyc', '__pycache__', '.git', '.pytest_cache'
    ])
    auto_fix: bool = False
    strict_mode: bool = False

class EnvironmentConsistencyManager:
    """Manages environment consistency and reproducibility"""
    
    def __init__(self, config: ConsistencyConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.baseline_snapshot = None
        self.current_snapshot = None
        self.inconsistencies = []
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def create_baseline_snapshot(self, save_path: str = None) -> EnvironmentSnapshot:
        """Create baseline environment snapshot"""
        self.logger.info("Creating baseline environment snapshot")
        
        snapshot = self._capture_current_state()
        self.baseline_snapshot = snapshot
        
        # Save snapshot
        save_path = save_path or self.config.snapshot_file
        self._save_snapshot(snapshot, save_path)
        
        self.logger.info(f"Baseline snapshot saved to: {save_path}")
        return snapshot
    
    def load_baseline_snapshot(self, snapshot_path: str) -> EnvironmentSnapshot:
        """Load baseline snapshot from file"""
        if not os.path.exists(snapshot_path):
            raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")
        
        with open(snapshot_path, 'r') as f:
            data = json.load(f)
        
        self.baseline_snapshot = EnvironmentSnapshot(**data)
        self.logger.info(f"Baseline snapshot loaded from: {snapshot_path}")
        
        return self.baseline_snapshot
    
    def validate_consistency(self) -> bool:
        """Validate current environment against baseline"""
        if not self.baseline_snapshot:
            raise RuntimeError("No baseline snapshot available. Create or load one first.")
        
        self.logger.info("Validating environment consistency")
        
        # Capture current state
        self.current_snapshot = self._capture_current_state()
        
        # Compare snapshots
        self.inconsistencies = self._compare_snapshots(
            self.baseline_snapshot,
            self.current_snapshot
        )
        
        if self.inconsistencies:
            self.logger.warning(f"Found {len(self.inconsistencies)} inconsistencies")
            
            for inconsistency in self.inconsistencies:
                level = logging.ERROR if self.config.strict_mode else logging.WARNING
                self.logger.log(level, f"Inconsistency: {inconsistency}")
            
            return False
        else:
            self.logger.info("Environment consistency validated successfully")
            return True
    
    def _capture_current_state(self) -> EnvironmentSnapshot:
        """Capture current environment state"""
        timestamp = time.time()
        
        # System information
        import platform
        system_info = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        }
        
        # Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # Environment variables
        env_vars = {}
        for var in self.config.track_env_vars:
            env_vars[var] = os.environ.get(var, '')
        
        # Installed packages
        installed_packages = {}
        if self.config.track_packages:
            installed_packages = self._get_installed_packages()
        
        # File checksums
        file_checksums = {}
        for file_path in self.config.track_files:
            if os.path.exists(file_path):
                file_checksums[file_path] = self._calculate_file_hash(file_path)
        
        # Configuration hash
        config_hash = self._calculate_config_hash()
        
        # Git commit (if available)
        git_commit = self._get_git_commit()
        
        return EnvironmentSnapshot(
            timestamp=timestamp,
            python_version=python_version,
            system_info=system_info,
            environment_variables=env_vars,
            installed_packages=installed_packages,
            file_checksums=file_checksums,
            configuration_hash=config_hash,
            git_commit=git_commit
        )
    
    def _get_installed_packages(self) -> Dict[str, str]:
        """Get list of installed Python packages"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'freeze'],
                capture_output=True,
                text=True,
                check=True
            )
            
            packages = {}
            for line in result.stdout.strip().split('\n'):
                if '==' in line:
                    name, version = line.split('==', 1)
                    packages[name.strip()] = version.strip()
            
            return packages
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to get installed packages: {e}")
            return {}
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to hash file {file_path}: {e}")
            return ""
    
    def _calculate_config_hash(self) -> str:
        """Calculate hash of current configuration"""
        config_str = json.dumps(asdict(self.config), sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def _compare_snapshots(self, baseline: EnvironmentSnapshot, current: EnvironmentSnapshot) -> List[str]:
        """Compare two snapshots and find inconsistencies"""
        inconsistencies = []
        
        # Python version
        if baseline.python_version != current.python_version:
            inconsistencies.append(
                f"Python version mismatch: {baseline.python_version} -> {current.python_version}"
            )
        
        # System info (only check if strict mode)
        if self.config.strict_mode:
            for key, value in baseline.system_info.items():
                if current.system_info.get(key) != value:
                    inconsistencies.append(
                        f"System {key} changed: {value} -> {current.system_info.get(key)}"
                    )
        
        # Environment variables
        for var, baseline_value in baseline.environment_variables.items():
            current_value = current.environment_variables.get(var, '')
            if baseline_value != current_value:
                inconsistencies.append(
                    f"Environment variable {var} changed: '{baseline_value}' -> '{current_value}'"
                )
        
        # Installed packages
        for package, baseline_version in baseline.installed_packages.items():
            current_version = current.installed_packages.get(package)
            if current_version != baseline_version:
                if current_version is None:
                    inconsistencies.append(f"Package {package} removed (was {baseline_version})")
                else:
                    inconsistencies.append(
                        f"Package {package} version changed: {baseline_version} -> {current_version}"
                    )
        
        # New packages
        for package, version in current.installed_packages.items():
            if package not in baseline.installed_packages:
                inconsistencies.append(f"New package installed: {package}=={version}")
        
        # File checksums
        for file_path, baseline_hash in baseline.file_checksums.items():
            current_hash = current.file_checksums.get(file_path)
            if current_hash != baseline_hash:
                if current_hash is None:
                    inconsistencies.append(f"Tracked file removed: {file_path}")
                else:
                    inconsistencies.append(f"File modified: {file_path}")
        
        # Configuration hash
        if baseline.configuration_hash != current.configuration_hash:
            inconsistencies.append("Configuration changed")
        
        return inconsistencies
    
    def fix_inconsistencies(self) -> bool:
        """Attempt to fix inconsistencies automatically"""
        if not self.config.auto_fix:
            self.logger.warning("Auto-fix not enabled")
            return False
        
        if not self.inconsistencies:
            self.logger.info("No inconsistencies to fix")
            return True
        
        self.logger.info("Attempting to fix inconsistencies")
        
        fixed_count = 0
        
        for inconsistency in self.inconsistencies:
            if self._fix_single_inconsistency(inconsistency):
                fixed_count += 1
        
        self.logger.info(f"Fixed {fixed_count}/{len(self.inconsistencies)} inconsistencies")
        
        # Re-validate
        return self.validate_consistency()
    
    def _fix_single_inconsistency(self, inconsistency: str) -> bool:
        """Fix a single inconsistency"""
        try:
            if "Package" in inconsistency and "version changed" in inconsistency:
                # Try to fix package version
                return self._fix_package_version(inconsistency)
            
            elif "Environment variable" in inconsistency:
                # Try to fix environment variable
                return self._fix_environment_variable(inconsistency)
            
            else:
                self.logger.warning(f"Cannot auto-fix: {inconsistency}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to fix inconsistency '{inconsistency}': {e}")
            return False
    
    def _fix_package_version(self, inconsistency: str) -> bool:
        """Fix package version inconsistency"""
        # Parse package name and target version from inconsistency message
        # This is a simplified implementation
        self.logger.info(f"Would attempt to fix package version: {inconsistency}")
        return False  # Placeholder - actual implementation would install correct version
    
    def _fix_environment_variable(self, inconsistency: str) -> bool:
        """Fix environment variable inconsistency"""
        # Parse variable and value from inconsistency message
        # This is a simplified implementation
        self.logger.info(f"Would attempt to fix environment variable: {inconsistency}")
        return False  # Placeholder - actual implementation would set correct value
    
    def _save_snapshot(self, snapshot: EnvironmentSnapshot, path: str):
        """Save snapshot to file"""
        with open(path, 'w') as f:
            json.dump(asdict(snapshot), f, indent=2, default=str)
    
    def generate_consistency_report(self) -> Dict[str, Any]:
        """Generate consistency report"""
        if not self.baseline_snapshot or not self.current_snapshot:
            raise RuntimeError("Both baseline and current snapshots required")
        
        return {
            'timestamp': time.time(),
            'environment_name': self.config.name,
            'baseline_timestamp': self.baseline_snapshot.timestamp,
            'current_timestamp': self.current_snapshot.timestamp,
            'consistency_check_passed': len(self.inconsistencies) == 0,
            'inconsistency_count': len(self.inconsistencies),
            'inconsistencies': self.inconsistencies,
            'baseline_snapshot': asdict(self.baseline_snapshot),
            'current_snapshot': asdict(self.current_snapshot),
            'config': asdict(self.config)
        }
    
    def reset_environment(self) -> bool:
        """Reset environment to baseline state (limited implementation)"""
        if not self.baseline_snapshot:
            raise RuntimeError("No baseline snapshot available")
        
        self.logger.info("Resetting environment to baseline state")
        
        # This is a simplified implementation
        # Full reset would require containerization or virtual environments
        
        reset_success = True
        
        # Reset environment variables
        for var, value in self.baseline_snapshot.environment_variables.items():
            if value:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
        
        self.logger.info("Environment reset completed (partial)")
        
        return reset_success

def create_environment_template(name: str, template_path: str = None) -> str:
    """Create environment template configuration"""
    template = {
        'name': name,
        'snapshot_file': f"{name}_snapshot.json",
        'track_env_vars': [
            'PATH', 'PYTHONPATH', 'HOME', 'USER', 'SHELL',
            'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV'
        ],
        'track_packages': True,
        'track_files': [
            'requirements.txt',
            'setup.py',
            'pyproject.toml',
            'Pipfile'
        ],
        'ignore_patterns': [
            '*.pyc', '__pycache__', '.git', '.pytest_cache',
            '*.log', '*.tmp'
        ],
        'auto_fix': False,
        'strict_mode': False
    }
    
    template_path = template_path or f"{name}_env_config.json"
    
    with open(template_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    return template_path

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Consistency Manager")
    parser.add_argument('command', choices=['create-baseline', 'validate', 'reset', 'create-template'])
    parser.add_argument('--config', help="Configuration file path")
    parser.add_argument('--name', default="test", help="Environment name")
    parser.add_argument('--snapshot', help="Snapshot file path")
    parser.add_argument('--strict', action='store_true', help="Strict mode")
    parser.add_argument('--auto-fix', action='store_true', help="Attempt auto-fix")
    parser.add_argument('--report', help="Generate report file")
    
    args = parser.parse_args()
    
    if args.command == 'create-template':
        template_path = create_environment_template(args.name)
        print(f"Environment template created: {template_path}")
        return
    
    # Load configuration
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        config = ConsistencyConfig(**config_data)
    else:
        config = ConsistencyConfig(
            name=args.name,
            strict_mode=args.strict,
            auto_fix=args.auto_fix
        )
    
    manager = EnvironmentConsistencyManager(config)
    
    try:
        if args.command == 'create-baseline':
            snapshot_path = args.snapshot or config.snapshot_file
            manager.create_baseline_snapshot(snapshot_path)
            print(f"✓ Baseline snapshot created: {snapshot_path}")
        
        elif args.command == 'validate':
            snapshot_path = args.snapshot or config.snapshot_file
            manager.load_baseline_snapshot(snapshot_path)
            
            if manager.validate_consistency():
                print("✓ Environment consistency validated")
                sys.exit(0)
            else:
                print("✗ Environment inconsistencies found")
                
                if args.auto_fix:
                    if manager.fix_inconsistencies():
                        print("✓ Inconsistencies fixed")
                        sys.exit(0)
                    else:
                        print("✗ Could not fix all inconsistencies")
                
                sys.exit(1)
        
        elif args.command == 'reset':
            snapshot_path = args.snapshot or config.snapshot_file
            manager.load_baseline_snapshot(snapshot_path)
            
            if manager.reset_environment():
                print("✓ Environment reset to baseline")
            else:
                print("✗ Environment reset failed")
                sys.exit(1)
        
        # Generate report if requested
        if args.report and manager.current_snapshot:
            report = manager.generate_consistency_report()
            with open(args.report, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Report generated: {args.report}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()