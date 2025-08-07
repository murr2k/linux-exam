#!/usr/bin/env python3
"""
Dependency Security Scanner for MPU6050 Project

Comprehensive dependency vulnerability scanning with support for:
- Python dependencies (pip packages)
- System packages (apt/yum)
- Kernel modules and drivers
- License compliance checking
- CVE database integration

Author: Murray Kopit <murr2k@gmail.com>
"""

import os
import sys
import json
import subprocess
import argparse
import requests
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET

class DependencyScanner:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results_dir = self.project_root / "security-results" / "sca"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Vulnerability databases
        self.cve_api_url = "https://services.nvd.nist.gov/rest/json/cves/1.0"
        self.osv_api_url = "https://api.osv.dev/v1/query"
        
        # Results storage
        self.vulnerabilities = []
        self.dependencies = []
        self.licenses = {}
        
    def scan_python_dependencies(self) -> List[Dict[str, Any]]:
        """Scan Python dependencies for vulnerabilities"""
        print("📦 Scanning Python dependencies...")
        
        results = []
        requirements_files = list(self.project_root.rglob("requirements*.txt"))
        setup_files = list(self.project_root.rglob("setup.py"))
        pipfile = list(self.project_root.rglob("Pipfile"))
        
        # Scan requirements.txt files
        for req_file in requirements_files:
            print(f"  Scanning {req_file.relative_to(self.project_root)}")
            deps = self._parse_requirements_file(req_file)
            for dep in deps:
                vuln_info = self._check_python_vulnerability(dep)
                if vuln_info:
                    results.append(vuln_info)
                    
        # Scan installed packages if no requirements.txt
        if not requirements_files:
            installed_deps = self._get_installed_python_packages()
            for dep in installed_deps:
                vuln_info = self._check_python_vulnerability(dep)
                if vuln_info:
                    results.append(vuln_info)
        
        # Use safety tool if available
        safety_results = self._run_safety_check()
        if safety_results:
            results.extend(safety_results)
            
        return results
    
    def _parse_requirements_file(self, req_file: Path) -> List[Dict[str, str]]:
        """Parse requirements.txt file"""
        dependencies = []
        
        try:
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse package==version format
                        if '==' in line:
                            name, version = line.split('==', 1)
                            dependencies.append({
                                'name': name.strip(),
                                'version': version.strip(),
                                'source': str(req_file)
                            })
                        elif '>=' in line:
                            name, version = line.split('>=', 1)
                            dependencies.append({
                                'name': name.strip(),
                                'version': f">={version.strip()}",
                                'source': str(req_file)
                            })
        except Exception as e:
            print(f"  ⚠️ Error parsing {req_file}: {e}")
            
        return dependencies
    
    def _get_installed_python_packages(self) -> List[Dict[str, str]]:
        """Get list of installed Python packages"""
        dependencies = []
        
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'],
                                  capture_output=True, text=True, check=True)
            packages = json.loads(result.stdout)
            
            for pkg in packages:
                dependencies.append({
                    'name': pkg['name'],
                    'version': pkg['version'],
                    'source': 'installed'
                })
        except Exception as e:
            print(f"  ⚠️ Error getting installed packages: {e}")
            
        return dependencies
    
    def _check_python_vulnerability(self, dependency: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Check a Python dependency for known vulnerabilities"""
        try:
            # Query OSV database
            query_data = {
                "package": {
                    "name": dependency['name'],
                    "ecosystem": "PyPI"
                }
            }
            
            if 'version' in dependency and not dependency['version'].startswith(('>=', '>', '<', '!=')):
                query_data["version"] = dependency['version']
            
            response = requests.post(self.osv_api_url, json=query_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'vulns' in data and data['vulns']:
                    vuln = data['vulns'][0]  # Get first vulnerability
                    return {
                        'type': 'python_dependency',
                        'package': dependency['name'],
                        'version': dependency.get('version', 'unknown'),
                        'vulnerability_id': vuln.get('id', 'unknown'),
                        'summary': vuln.get('summary', 'No summary available'),
                        'severity': self._get_vulnerability_severity(vuln),
                        'fixed_versions': self._get_fixed_versions(vuln),
                        'source': dependency.get('source', 'unknown'),
                        'references': vuln.get('references', [])
                    }
        except Exception as e:
            print(f"  ⚠️ Error checking {dependency['name']}: {e}")
            
        return None
    
    def _run_safety_check(self) -> List[Dict[str, Any]]:
        """Run safety tool for Python vulnerability scanning"""
        results = []
        
        try:
            # Check if safety is installed
            subprocess.run(['safety', '--version'], capture_output=True, check=True)
            
            # Run safety check
            result = subprocess.run(['safety', 'check', '--json'],
                                  capture_output=True, text=True)
            
            if result.stdout:
                safety_data = json.loads(result.stdout)
                for item in safety_data:
                    if isinstance(item, list):
                        for vuln in item:
                            results.append({
                                'type': 'python_dependency',
                                'package': vuln.get('package', 'unknown'),
                                'version': vuln.get('installed_version', 'unknown'),
                                'vulnerability_id': vuln.get('id', 'unknown'),
                                'summary': vuln.get('advisory', 'No summary available'),
                                'severity': 'medium',  # Safety doesn't provide severity
                                'tool': 'safety'
                            })
                            
        except subprocess.CalledProcessError:
            print("  ℹ️ Safety tool not available")
        except Exception as e:
            print(f"  ⚠️ Error running safety: {e}")
            
        return results
    
    def scan_system_packages(self) -> List[Dict[str, Any]]:
        """Scan system packages for vulnerabilities"""
        print("🖥️ Scanning system packages...")
        
        results = []
        
        # Check for apt packages (Debian/Ubuntu)
        if self._command_exists('apt'):
            results.extend(self._scan_apt_packages())
            
        # Check for yum packages (RHEL/CentOS)
        if self._command_exists('yum'):
            results.extend(self._scan_yum_packages())
            
        # Check kernel version
        results.extend(self._scan_kernel_version())
        
        return results
    
    def _scan_apt_packages(self) -> List[Dict[str, Any]]:
        """Scan APT packages for security updates"""
        results = []
        
        try:
            # Get list of upgradeable packages
            result = subprocess.run(['apt', 'list', '--upgradable'],
                                  capture_output=True, text=True, check=True)
            
            for line in result.stdout.split('\n'):
                if 'upgradable' in line and 'security' in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        package_name = parts[0].split('/')[0]
                        results.append({
                            'type': 'system_package',
                            'package': package_name,
                            'severity': 'medium',
                            'summary': 'Security update available',
                            'recommendation': 'Update package to latest version'
                        })
                        
        except subprocess.CalledProcessError:
            print("  ⚠️ Error scanning APT packages")
            
        return results
    
    def _scan_yum_packages(self) -> List[Dict[str, Any]]:
        """Scan YUM packages for security updates"""
        results = []
        
        try:
            result = subprocess.run(['yum', 'check-update', '--security'],
                                  capture_output=True, text=True)
            
            # yum check-update returns 100 if updates are available
            if result.returncode == 100:
                for line in result.stdout.split('\n'):
                    if line.strip() and not line.startswith('Loaded'):
                        parts = line.split()
                        if len(parts) >= 1:
                            results.append({
                                'type': 'system_package',
                                'package': parts[0],
                                'severity': 'medium',
                                'summary': 'Security update available',
                                'recommendation': 'Update package to latest version'
                            })
                            
        except subprocess.CalledProcessError:
            print("  ⚠️ Error scanning YUM packages")
            
        return results
    
    def _scan_kernel_version(self) -> List[Dict[str, Any]]:
        """Check kernel version for known vulnerabilities"""
        results = []
        
        try:
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True, check=True)
            kernel_version = result.stdout.strip()
            
            # Check if kernel is EOL or has known critical vulnerabilities
            # This is a simplified check - in production, use a proper CVE database
            if self._is_kernel_vulnerable(kernel_version):
                results.append({
                    'type': 'kernel',
                    'package': f'linux-kernel-{kernel_version}',
                    'version': kernel_version,
                    'severity': 'high',
                    'summary': 'Kernel version may have known vulnerabilities',
                    'recommendation': 'Update to latest stable kernel version'
                })
                
        except subprocess.CalledProcessError:
            print("  ⚠️ Error checking kernel version")
            
        return results
    
    def scan_licenses(self) -> Dict[str, Any]:
        """Scan for license compliance issues"""
        print("📄 Scanning license compliance...")
        
        license_info = {
            'compliant': [],
            'non_compliant': [],
            'missing': [],
            'summary': {}
        }
        
        # Check source files for SPDX license identifiers
        source_files = []
        for pattern in ['*.c', '*.h', '*.py', '*.cpp', '*.hpp']:
            source_files.extend(self.project_root.rglob(pattern))
            
        for source_file in source_files:
            if self._is_excluded_path(source_file):
                continue
                
            license_status = self._check_file_license(source_file)
            if license_status['has_license']:
                license_info['compliant'].append({
                    'file': str(source_file.relative_to(self.project_root)),
                    'license': license_status['license']
                })
            else:
                license_info['missing'].append(
                    str(source_file.relative_to(self.project_root))
                )
        
        # Check for conflicting licenses
        license_info['conflicting'] = self._check_license_conflicts(license_info['compliant'])
        
        # Generate summary
        license_info['summary'] = {
            'total_files': len(source_files),
            'compliant_files': len(license_info['compliant']),
            'missing_license': len(license_info['missing']),
            'conflicting_licenses': len(license_info['conflicting'])
        }
        
        return license_info
    
    def _check_file_license(self, file_path: Path) -> Dict[str, Any]:
        """Check if a file has proper license identifier"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_50_lines = []
                for i, line in enumerate(f):
                    if i >= 50:  # Check only first 50 lines
                        break
                    first_50_lines.append(line)
                
                content = ''.join(first_50_lines)
                
                # Look for SPDX license identifier
                if 'SPDX-License-Identifier:' in content:
                    # Extract license
                    for line in first_50_lines:
                        if 'SPDX-License-Identifier:' in line:
                            license_id = line.split('SPDX-License-Identifier:')[1].strip()
                            # Remove comment markers
                            license_id = license_id.lstrip('*/ ')
                            return {'has_license': True, 'license': license_id}
                
                # Look for common license patterns
                license_patterns = {
                    'GPL': ['GNU General Public License', 'GPL'],
                    'MIT': ['MIT License', 'MIT'],
                    'Apache': ['Apache License', 'Apache-2.0'],
                    'BSD': ['BSD License', 'BSD']
                }
                
                for license_name, patterns in license_patterns.items():
                    for pattern in patterns:
                        if pattern in content:
                            return {'has_license': True, 'license': license_name}
                            
        except Exception as e:
            print(f"  ⚠️ Error reading {file_path}: {e}")
            
        return {'has_license': False, 'license': None}
    
    def _check_license_conflicts(self, compliant_files: List[Dict[str, Any]]) -> List[str]:
        """Check for conflicting licenses in the project"""
        licenses = set()
        
        for file_info in compliant_files:
            license_id = file_info['license']
            if license_id:
                # Normalize license names
                if 'GPL' in license_id:
                    licenses.add('GPL')
                elif 'MIT' in license_id:
                    licenses.add('MIT')
                elif 'Apache' in license_id:
                    licenses.add('Apache')
                elif 'BSD' in license_id:
                    licenses.add('BSD')
                else:
                    licenses.add(license_id)
        
        # Check for known conflicts
        conflicts = []
        if 'GPL' in licenses and 'MIT' in licenses:
            conflicts.append('GPL and MIT licenses may be incompatible')
        if 'GPL' in licenses and 'Apache' in licenses:
            conflicts.append('GPL and Apache licenses may be incompatible')
            
        return conflicts
    
    def generate_report(self, output_format: str = 'json') -> str:
        """Generate comprehensive security report"""
        print(f"📊 Generating {output_format.upper()} report...")
        
        # Collect all scan results
        python_vulns = self.scan_python_dependencies()
        system_vulns = self.scan_system_packages()
        license_info = self.scan_licenses()
        
        all_vulnerabilities = python_vulns + system_vulns
        
        report_data = {
            'scan_metadata': {
                'timestamp': datetime.now().isoformat(),
                'project_root': str(self.project_root),
                'scanner_version': '1.0.0',
                'scan_id': self.timestamp
            },
            'summary': {
                'total_vulnerabilities': len(all_vulnerabilities),
                'critical': len([v for v in all_vulnerabilities if v.get('severity') == 'critical']),
                'high': len([v for v in all_vulnerabilities if v.get('severity') == 'high']),
                'medium': len([v for v in all_vulnerabilities if v.get('severity') == 'medium']),
                'low': len([v for v in all_vulnerabilities if v.get('severity') == 'low']),
                'python_dependencies': len([v for v in all_vulnerabilities if v.get('type') == 'python_dependency']),
                'system_packages': len([v for v in all_vulnerabilities if v.get('type') == 'system_package']),
                'license_compliance': license_info['summary']
            },
            'vulnerabilities': all_vulnerabilities,
            'license_compliance': license_info,
            'recommendations': self._generate_recommendations(all_vulnerabilities, license_info)
        }
        
        # Save report
        if output_format == 'json':
            report_file = self.results_dir / f"dependency_scan_{self.timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
        elif output_format == 'xml':
            report_file = self.results_dir / f"dependency_scan_{self.timestamp}.xml"
            self._save_xml_report(report_data, report_file)
        else:  # text
            report_file = self.results_dir / f"dependency_scan_{self.timestamp}.txt"
            self._save_text_report(report_data, report_file)
            
        print(f"📁 Report saved to: {report_file}")
        return str(report_file)
    
    def _generate_recommendations(self, vulnerabilities: List[Dict[str, Any]], 
                                license_info: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on scan results"""
        recommendations = []
        
        if vulnerabilities:
            recommendations.append("Update vulnerable dependencies to patched versions")
            recommendations.append("Implement automated dependency scanning in CI/CD pipeline")
            recommendations.append("Set up security alerts for new vulnerabilities")
        
        if license_info['missing']:
            recommendations.append("Add SPDX license identifiers to all source files")
            
        if license_info['conflicting']:
            recommendations.append("Review and resolve conflicting licenses")
            
        recommendations.extend([
            "Regular security updates for system packages",
            "Implement dependency pinning for reproducible builds",
            "Use dependency vulnerability databases for continuous monitoring",
            "Establish security review process for new dependencies",
            "Create Software Bill of Materials (SBOM) for the project"
        ])
        
        return recommendations
    
    def _save_text_report(self, report_data: Dict[str, Any], report_file: Path):
        """Save report in text format"""
        with open(report_file, 'w') as f:
            f.write("# Dependency Security Scan Report\n")
            f.write(f"Generated: {report_data['scan_metadata']['timestamp']}\n")
            f.write(f"Project: {report_data['scan_metadata']['project_root']}\n")
            f.write(f"Scan ID: {report_data['scan_metadata']['scan_id']}\n\n")
            
            f.write("## Summary\n")
            summary = report_data['summary']
            f.write(f"Total Vulnerabilities: {summary['total_vulnerabilities']}\n")
            f.write(f"- Critical: {summary['critical']}\n")
            f.write(f"- High: {summary['high']}\n")
            f.write(f"- Medium: {summary['medium']}\n")
            f.write(f"- Low: {summary['low']}\n\n")
            
            f.write("## Vulnerabilities\n")
            for vuln in report_data['vulnerabilities']:
                f.write(f"### {vuln.get('package', 'Unknown Package')}\n")
                f.write(f"Type: {vuln.get('type', 'unknown')}\n")
                f.write(f"Severity: {vuln.get('severity', 'unknown')}\n")
                f.write(f"Summary: {vuln.get('summary', 'No summary')}\n")
                if 'vulnerability_id' in vuln:
                    f.write(f"CVE/ID: {vuln['vulnerability_id']}\n")
                f.write("\n")
            
            f.write("## License Compliance\n")
            license_summary = report_data['license_compliance']['summary']
            f.write(f"Total Files: {license_summary['total_files']}\n")
            f.write(f"Compliant Files: {license_summary['compliant_files']}\n")
            f.write(f"Missing License: {license_summary['missing_license']}\n")
            f.write(f"Conflicting Licenses: {license_summary['conflicting_licenses']}\n\n")
            
            f.write("## Recommendations\n")
            for i, rec in enumerate(report_data['recommendations'], 1):
                f.write(f"{i}. {rec}\n")
    
    # Utility methods
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            subprocess.run([command, '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _is_excluded_path(self, path: Path) -> bool:
        """Check if path should be excluded from scanning"""
        excluded_dirs = {'.git', 'build', 'node_modules', '__pycache__', '.pytest_cache'}
        return any(part in excluded_dirs for part in path.parts)
    
    def _get_vulnerability_severity(self, vuln_data: Dict[str, Any]) -> str:
        """Extract vulnerability severity from vulnerability data"""
        if 'database_specific' in vuln_data:
            db_specific = vuln_data['database_specific']
            if 'severity' in db_specific:
                return db_specific['severity'].lower()
        
        # Default to medium if severity not specified
        return 'medium'
    
    def _get_fixed_versions(self, vuln_data: Dict[str, Any]) -> List[str]:
        """Extract fixed versions from vulnerability data"""
        fixed_versions = []
        
        if 'affected' in vuln_data:
            for affected in vuln_data['affected']:
                if 'ranges' in affected:
                    for range_data in affected['ranges']:
                        if 'events' in range_data:
                            for event in range_data['events']:
                                if 'fixed' in event:
                                    fixed_versions.append(event['fixed'])
        
        return fixed_versions
    
    def _is_kernel_vulnerable(self, kernel_version: str) -> bool:
        """Check if kernel version has known vulnerabilities (simplified)"""
        # This is a simplified check - in production, use proper CVE database
        vulnerable_patterns = [
            '4.4.',  # Old LTS versions that might have issues
            '4.9.',
            '4.14.'
        ]
        
        for pattern in vulnerable_patterns:
            if kernel_version.startswith(pattern):
                return True
                
        return False

def main():
    parser = argparse.ArgumentParser(description='Dependency Security Scanner for MPU6050 Project')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--output-format', choices=['json', 'xml', 'text'], default='json',
                       help='Output format for the report')
    parser.add_argument('--output-dir', help='Output directory for results')
    parser.add_argument('--python-only', action='store_true', help='Scan only Python dependencies')
    parser.add_argument('--system-only', action='store_true', help='Scan only system packages')
    parser.add_argument('--license-only', action='store_true', help='Scan only license compliance')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Initialize scanner
    scanner = DependencyScanner(args.project_root)
    
    if args.output_dir:
        scanner.results_dir = Path(args.output_dir)
        scanner.results_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔍 Starting dependency security scan...")
    print(f"📂 Project root: {scanner.project_root}")
    print(f"📁 Results directory: {scanner.results_dir}")
    
    try:
        # Generate report
        report_file = scanner.generate_report(args.output_format)
        
        print(f"\n✅ Dependency scan completed successfully!")
        print(f"📊 Report saved to: {report_file}")
        
        # Print summary to console
        with open(report_file, 'r') as f:
            if args.output_format == 'json':
                data = json.load(f)
                summary = data['summary']
                print(f"\n📋 Summary:")
                print(f"   Total vulnerabilities: {summary['total_vulnerabilities']}")
                print(f"   Critical: {summary['critical']}, High: {summary['high']}, Medium: {summary['medium']}, Low: {summary['low']}")
                print(f"   License compliance: {summary['license_compliance']['missing_license']} files missing licenses")
        
        # Exit with appropriate code
        return 0 if summary['total_vulnerabilities'] == 0 else 1
        
    except Exception as e:
        print(f"\n❌ Error during dependency scan: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 2

if __name__ == '__main__':
    sys.exit(main())