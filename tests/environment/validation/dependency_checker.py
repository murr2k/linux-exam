#!/usr/bin/env python3
"""
Dependency Checker
Comprehensive dependency validation and management for test environments.
"""

import os
import sys
import json
import subprocess
import importlib
import pkg_resources
import logging
import re
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml

@dataclass
class Dependency:
    """Represents a single dependency"""
    name: str
    version: str = None
    type: str = "python"  # python, system, npm, etc.
    optional: bool = False
    description: str = ""

@dataclass
class DependencySet:
    """Set of dependencies for a specific environment"""
    python_packages: List[Dependency]
    system_packages: List[Dependency]
    npm_packages: List[Dependency]
    binary_tools: List[Dependency]

class DependencyChecker:
    """Comprehensive dependency checking and management"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.missing_deps = []
        self.version_conflicts = []
        self.optional_missing = []
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def check_python_dependencies(self, requirements: List[Dependency]) -> Tuple[List[str], List[str]]:
        """Check Python package dependencies"""
        missing = []
        conflicts = []
        
        for dep in requirements:
            try:
                if dep.version:
                    # Check specific version requirement
                    pkg_resources.require(f"{dep.name}{dep.version}")
                else:
                    # Check if package exists
                    importlib.import_module(dep.name)
                
                self.logger.debug(f"✓ {dep.name} available")
                
            except (ImportError, pkg_resources.DistributionNotFound):
                if dep.optional:
                    self.optional_missing.append(dep.name)
                    self.logger.warning(f"Optional dependency missing: {dep.name}")
                else:
                    missing.append(dep.name)
                    self.logger.error(f"✗ Missing required dependency: {dep.name}")
                    
            except pkg_resources.VersionConflict as e:
                conflicts.append(f"{dep.name}: {str(e)}")
                self.logger.error(f"✗ Version conflict: {dep.name}")
        
        return missing, conflicts
    
    def check_system_dependencies(self, requirements: List[Dependency]) -> List[str]:
        """Check system package dependencies"""
        missing = []
        
        for dep in requirements:
            if not self._is_system_package_available(dep.name):
                if dep.optional:
                    self.optional_missing.append(dep.name)
                    self.logger.warning(f"Optional system package missing: {dep.name}")
                else:
                    missing.append(dep.name)
                    self.logger.error(f"✗ Missing system package: {dep.name}")
            else:
                self.logger.debug(f"✓ System package {dep.name} available")
        
        return missing
    
    def check_binary_tools(self, requirements: List[Dependency]) -> List[str]:
        """Check binary tool dependencies"""
        missing = []
        
        for dep in requirements:
            if not self._is_binary_available(dep.name):
                if dep.optional:
                    self.optional_missing.append(dep.name)
                    self.logger.warning(f"Optional binary missing: {dep.name}")
                else:
                    missing.append(dep.name)
                    self.logger.error(f"✗ Missing binary: {dep.name}")
            else:
                # Check version if specified
                if dep.version:
                    actual_version = self._get_binary_version(dep.name)
                    if actual_version and not self._version_matches(actual_version, dep.version):
                        self.logger.warning(f"Version mismatch for {dep.name}: got {actual_version}, expected {dep.version}")
                
                self.logger.debug(f"✓ Binary {dep.name} available")
        
        return missing
    
    def check_npm_dependencies(self, requirements: List[Dependency]) -> List[str]:
        """Check npm package dependencies"""
        if not self._is_binary_available("npm"):
            self.logger.error("npm not available, skipping npm dependency check")
            return [dep.name for dep in requirements if not dep.optional]
        
        missing = []
        
        try:
            result = subprocess.run(
                ["npm", "list", "--depth=0", "--json"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                installed = json.loads(result.stdout).get("dependencies", {})
            else:
                installed = {}
            
            for dep in requirements:
                if dep.name not in installed:
                    if dep.optional:
                        self.optional_missing.append(dep.name)
                        self.logger.warning(f"Optional npm package missing: {dep.name}")
                    else:
                        missing.append(dep.name)
                        self.logger.error(f"✗ Missing npm package: {dep.name}")
                else:
                    self.logger.debug(f"✓ npm package {dep.name} available")
                    
        except Exception as e:
            self.logger.error(f"Error checking npm dependencies: {e}")
            return [dep.name for dep in requirements if not dep.optional]
        
        return missing
    
    def _is_system_package_available(self, package: str) -> bool:
        """Check if system package is available"""
        # Try different package managers
        managers = [
            ["dpkg", "-l", package],  # Debian/Ubuntu
            ["rpm", "-q", package],   # Red Hat/CentOS
            ["pacman", "-Q", package], # Arch
            ["brew", "list", package]  # macOS
        ]
        
        for cmd in managers:
            try:
                result = subprocess.run(cmd, capture_output=True, check=False)
                if result.returncode == 0:
                    return True
            except FileNotFoundError:
                continue
        
        return False
    
    def _is_binary_available(self, binary: str) -> bool:
        """Check if binary tool is available"""
        try:
            subprocess.run(["which", binary], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _get_binary_version(self, binary: str) -> Optional[str]:
        """Get version of binary tool"""
        version_flags = ["--version", "-V", "-version", "version"]
        
        for flag in version_flags:
            try:
                result = subprocess.run(
                    [binary, flag],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5
                )
                
                # Extract version using common patterns
                version_patterns = [
                    r"(\d+\.\d+\.\d+)",
                    r"version\s+(\d+\.\d+)",
                    r"v(\d+\.\d+\.\d+)",
                ]
                
                for pattern in version_patterns:
                    match = re.search(pattern, result.stdout, re.IGNORECASE)
                    if match:
                        return match.group(1)
                
                return result.stdout.strip().split('\n')[0]
                
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return None
    
    def _version_matches(self, actual: str, expected: str) -> bool:
        """Check if version matches requirement"""
        # Simple version comparison - can be extended for semver
        if expected.startswith(">="):
            return actual >= expected[2:]
        elif expected.startswith("<="):
            return actual <= expected[2:]
        elif expected.startswith(">"):
            return actual > expected[1:]
        elif expected.startswith("<"):
            return actual < expected[1:]
        else:
            return actual == expected
    
    def auto_install_dependencies(self, missing_python: List[str], missing_system: List[str]) -> bool:
        """Attempt to auto-install missing dependencies"""
        success = True
        
        # Install Python packages
        if missing_python:
            self.logger.info(f"Installing Python packages: {missing_python}")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install"] + missing_python,
                    check=True
                )
                self.logger.info("✓ Python packages installed successfully")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"✗ Failed to install Python packages: {e}")
                success = False
        
        # Install system packages (if running with sudo)
        if missing_system and os.geteuid() == 0:
            self.logger.info(f"Installing system packages: {missing_system}")
            
            # Try different package managers
            if self._is_binary_available("apt-get"):
                try:
                    subprocess.run(
                        ["apt-get", "update", "-qq"],
                        check=True
                    )
                    subprocess.run(
                        ["apt-get", "install", "-y"] + missing_system,
                        check=True
                    )
                    self.logger.info("✓ System packages installed successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"✗ Failed to install system packages: {e}")
                    success = False
        elif missing_system:
            self.logger.warning("Cannot auto-install system packages without sudo privileges")
            success = False
        
        return success
    
    def generate_install_script(self, missing_deps: Dict[str, List[str]], output_path: str = "install_dependencies.sh") -> str:
        """Generate shell script to install missing dependencies"""
        script_lines = [
            "#!/bin/bash",
            "# Auto-generated dependency installation script",
            "set -e",
            "",
            "echo 'Installing missing dependencies...'",
            ""
        ]
        
        # Python packages
        if missing_deps.get('python'):
            script_lines.extend([
                "# Python packages",
                f"pip install {' '.join(missing_deps['python'])}",
                ""
            ])
        
        # System packages
        if missing_deps.get('system'):
            script_lines.extend([
                "# System packages (Debian/Ubuntu)",
                "if command -v apt-get &> /dev/null; then",
                "    sudo apt-get update",
                f"    sudo apt-get install -y {' '.join(missing_deps['system'])}",
                "fi",
                "",
                "# System packages (Red Hat/CentOS)",
                "if command -v yum &> /dev/null; then",
                f"    sudo yum install -y {' '.join(missing_deps['system'])}",
                "fi",
                "",
                "# System packages (macOS)",
                "if command -v brew &> /dev/null; then",
                f"    brew install {' '.join(missing_deps['system'])}",
                "fi",
                ""
            ])
        
        # npm packages
        if missing_deps.get('npm'):
            script_lines.extend([
                "# npm packages",
                f"npm install {' '.join(missing_deps['npm'])}",
                ""
            ])
        
        script_lines.append("echo 'Dependencies installation completed!'")
        
        script_content = "\n".join(script_lines)
        
        with open(output_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(output_path, 0o755)
        self.logger.info(f"Installation script generated: {output_path}")
        
        return script_content
    
    def load_dependencies_from_file(self, file_path: str) -> DependencySet:
        """Load dependencies from configuration file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dependencies file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            if file_path.endswith('.json'):
                config = json.load(f)
            elif file_path.endswith('.yml') or file_path.endswith('.yaml'):
                config = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
        
        return DependencySet(
            python_packages=[Dependency(**dep) for dep in config.get('python_packages', [])],
            system_packages=[Dependency(**dep) for dep in config.get('system_packages', [])],
            npm_packages=[Dependency(**dep) for dep in config.get('npm_packages', [])],
            binary_tools=[Dependency(**dep) for dep in config.get('binary_tools', [])]
        )
    
    def check_all_dependencies(self, deps: DependencySet) -> Dict[str, List[str]]:
        """Check all dependency types"""
        results = {}
        
        # Check Python dependencies
        python_missing, python_conflicts = self.check_python_dependencies(deps.python_packages)
        results['python_missing'] = python_missing
        results['python_conflicts'] = python_conflicts
        
        # Check system dependencies
        results['system_missing'] = self.check_system_dependencies(deps.system_packages)
        
        # Check npm dependencies
        results['npm_missing'] = self.check_npm_dependencies(deps.npm_packages)
        
        # Check binary tools
        results['binary_missing'] = self.check_binary_tools(deps.binary_tools)
        
        # Summary
        all_missing = (
            python_missing + 
            results['system_missing'] + 
            results['npm_missing'] + 
            results['binary_missing']
        )
        
        results['all_missing'] = all_missing
        results['has_missing'] = len(all_missing) > 0
        results['optional_missing'] = self.optional_missing
        
        return results

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dependency Checker")
    parser.add_argument('--config', required=True, help="Dependencies configuration file")
    parser.add_argument('--auto-install', action='store_true', help="Attempt to auto-install missing dependencies")
    parser.add_argument('--generate-script', help="Generate installation script")
    parser.add_argument('--verbose', action='store_true', help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    checker = DependencyChecker()
    
    try:
        deps = checker.load_dependencies_from_file(args.config)
        results = checker.check_all_dependencies(deps)
        
        if results['has_missing']:
            print("✗ Missing dependencies found:")
            for dep_type, missing in results.items():
                if dep_type.endswith('_missing') and missing:
                    print(f"  {dep_type.replace('_missing', '')}: {missing}")
            
            if args.auto_install:
                success = checker.auto_install_dependencies(
                    results['python_missing'],
                    results['system_missing']
                )
                if not success:
                    sys.exit(1)
            
            if args.generate_script:
                checker.generate_install_script(
                    {
                        'python': results['python_missing'],
                        'system': results['system_missing'],
                        'npm': results['npm_missing']
                    },
                    args.generate_script
                )
            
            if not args.auto_install:
                sys.exit(1)
        else:
            print("✓ All dependencies satisfied")
        
        if results['optional_missing']:
            print(f"ℹ Optional dependencies missing: {results['optional_missing']}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()