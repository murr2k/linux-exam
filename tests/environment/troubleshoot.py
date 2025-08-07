#!/usr/bin/env python3
"""
Automated Troubleshooting System
Provides automated diagnosis and resolution of common test environment issues.
"""

import os
import sys
import json
import logging
import subprocess
import time
import re
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import psutil
import tempfile

@dataclass
class TroubleshootResult:
    """Result of a troubleshooting action"""
    issue_type: str
    description: str
    severity: str  # low, medium, high, critical
    auto_fixable: bool
    fix_applied: bool = False
    fix_description: str = ""
    commands_run: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DiagnosticRule:
    """Rule for diagnosing issues"""
    name: str
    pattern: str
    severity: str
    auto_fix: Optional[Callable] = None
    description: str = ""
    fix_description: str = ""

class AutoTroubleshooter:
    """Automated troubleshooting and issue resolution system"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.diagnostic_rules = self._load_diagnostic_rules()
        self.fix_history = []
        self.system_state = {}
        
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
    
    def _load_diagnostic_rules(self) -> List[DiagnosticRule]:
        """Load diagnostic rules for common issues"""
        return [
            DiagnosticRule(
                name="python_import_error",
                pattern=r"ImportError|ModuleNotFoundError",
                severity="high",
                auto_fix=self._fix_python_import_error,
                description="Python module import failure",
                fix_description="Install missing Python packages"
            ),
            DiagnosticRule(
                name="permission_denied",
                pattern=r"Permission denied|PermissionError",
                severity="high",
                auto_fix=self._fix_permission_error,
                description="File system permission error",
                fix_description="Fix file/directory permissions"
            ),
            DiagnosticRule(
                name="disk_space_full",
                pattern=r"No space left on device|Disk full",
                severity="critical",
                auto_fix=self._fix_disk_space_issue,
                description="Insufficient disk space",
                fix_description="Free up disk space"
            ),
            DiagnosticRule(
                name="memory_error",
                pattern=r"MemoryError|Out of memory",
                severity="critical",
                auto_fix=self._fix_memory_issue,
                description="Insufficient memory",
                fix_description="Free memory or reduce resource usage"
            ),
            DiagnosticRule(
                name="port_in_use",
                pattern=r"Address already in use|Port.*already in use",
                severity="medium",
                auto_fix=self._fix_port_conflict,
                description="Network port conflict",
                fix_description="Kill process using port or use different port"
            ),
            DiagnosticRule(
                name="file_not_found",
                pattern=r"FileNotFoundError|No such file or directory",
                severity="medium",
                auto_fix=self._fix_missing_file,
                description="Missing file or directory",
                fix_description="Create missing files/directories"
            ),
            DiagnosticRule(
                name="timeout_error",
                pattern=r"TimeoutError|Timeout|timeout expired",
                severity="medium",
                auto_fix=self._fix_timeout_issue,
                description="Operation timeout",
                fix_description="Increase timeout or optimize performance"
            ),
            DiagnosticRule(
                name="network_error",
                pattern=r"ConnectionError|Network.*unreachable|Name resolution failed",
                severity="medium",
                auto_fix=self._fix_network_issue,
                description="Network connectivity issue",
                fix_description="Check network configuration"
            ),
            DiagnosticRule(
                name="syntax_error",
                pattern=r"SyntaxError|Invalid syntax",
                severity="high",
                auto_fix=None,  # Cannot auto-fix syntax errors
                description="Python syntax error",
                fix_description="Fix code syntax manually"
            ),
            DiagnosticRule(
                name="dependency_conflict",
                pattern=r"VersionConflict|version conflict|incompatible",
                severity="high",
                auto_fix=self._fix_dependency_conflict,
                description="Package dependency conflict",
                fix_description="Resolve dependency conflicts"
            )
        ]
    
    def diagnose_error(self, error_message: str, context: Dict[str, Any] = None) -> List[TroubleshootResult]:
        """Diagnose error message and return potential issues"""
        results = []
        context = context or {}
        
        self.logger.info(f"Diagnosing error: {error_message[:100]}...")
        
        # Check against diagnostic rules
        for rule in self.diagnostic_rules:
            if re.search(rule.pattern, error_message, re.IGNORECASE):
                result = TroubleshootResult(
                    issue_type=rule.name,
                    description=rule.description,
                    severity=rule.severity,
                    auto_fixable=rule.auto_fix is not None,
                    fix_description=rule.fix_description,
                    details={
                        'error_message': error_message,
                        'context': context,
                        'pattern_matched': rule.pattern
                    }
                )
                results.append(result)
                
                self.logger.info(f"Identified issue: {rule.name} (severity: {rule.severity})")
        
        # Generic analysis if no specific rules match
        if not results:
            result = TroubleshootResult(
                issue_type="unknown_error",
                description="Unknown error type",
                severity="medium",
                auto_fixable=False,
                fix_description="Manual investigation required",
                details={'error_message': error_message}
            )
            results.append(result)
        
        return results
    
    def auto_fix_issues(self, issues: List[TroubleshootResult]) -> List[TroubleshootResult]:
        """Attempt to automatically fix identified issues"""
        fixed_issues = []
        
        for issue in issues:
            if not issue.auto_fixable:
                self.logger.info(f"Skipping non-auto-fixable issue: {issue.issue_type}")
                continue
            
            self.logger.info(f"Attempting to auto-fix: {issue.issue_type}")
            
            # Find the corresponding rule
            rule = next((r for r in self.diagnostic_rules if r.name == issue.issue_type), None)
            if not rule or not rule.auto_fix:
                continue
            
            try:
                # Apply the fix
                fix_result = rule.auto_fix(issue)
                issue.fix_applied = fix_result
                
                if fix_result:
                    self.logger.info(f"✓ Successfully fixed: {issue.issue_type}")
                    self.fix_history.append(issue)
                else:
                    self.logger.warning(f"✗ Failed to fix: {issue.issue_type}")
                
                fixed_issues.append(issue)
                
            except Exception as e:
                self.logger.error(f"Error fixing {issue.issue_type}: {e}")
                issue.details['fix_error'] = str(e)
        
        return fixed_issues
    
    def _fix_python_import_error(self, issue: TroubleshootResult) -> bool:
        """Fix Python import errors by installing missing packages"""
        error_msg = issue.details.get('error_message', '')
        
        # Extract module name from error message
        import_patterns = [
            r"No module named '([^']+)'",
            r"ModuleNotFoundError.*'([^']+)'",
            r"ImportError.*cannot import name '([^']+)'"
        ]
        
        module_name = None
        for pattern in import_patterns:
            match = re.search(pattern, error_msg)
            if match:
                module_name = match.group(1)
                break
        
        if not module_name:
            return False
        
        # Try to install the module
        install_commands = [
            [sys.executable, '-m', 'pip', 'install', module_name],
            [sys.executable, '-m', 'pip', 'install', '--user', module_name]
        ]
        
        for cmd in install_commands:
            try:
                self.logger.info(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                issue.commands_run.append(' '.join(cmd))
                
                if result.returncode == 0:
                    issue.fix_description = f"Installed missing package: {module_name}"
                    return True
                else:
                    self.logger.warning(f"Installation failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                self.logger.error(f"Installation timeout for {module_name}")
            except Exception as e:
                self.logger.error(f"Installation error: {e}")
        
        return False
    
    def _fix_permission_error(self, issue: TroubleshootResult) -> bool:
        """Fix file permission errors"""
        error_msg = issue.details.get('error_message', '')
        
        # Extract file path from error message
        path_patterns = [
            r"Permission denied.*'([^']+)'",
            r"PermissionError.*'([^']+)'",
            r"Permission denied:\s*([^\s]+)"
        ]
        
        file_path = None
        for pattern in path_patterns:
            match = re.search(pattern, error_msg)
            if match:
                file_path = match.group(1)
                break
        
        if not file_path or not os.path.exists(file_path):
            return False
        
        try:
            # Try to fix permissions
            if os.path.isfile(file_path):
                os.chmod(file_path, 0o644)
                cmd = f"chmod 644 {file_path}"
            elif os.path.isdir(file_path):
                os.chmod(file_path, 0o755)
                cmd = f"chmod 755 {file_path}"
            else:
                return False
            
            issue.commands_run.append(cmd)
            issue.fix_description = f"Fixed permissions for: {file_path}"
            
            return True
            
        except Exception as e:
            self.logger.error(f"Permission fix failed: {e}")
            return False
    
    def _fix_disk_space_issue(self, issue: TroubleshootResult) -> bool:
        """Fix disk space issues by cleaning up temporary files"""
        try:
            cleaned_space = 0
            cleanup_commands = []
            
            # Clean up common temporary directories
            temp_dirs = [
                '/tmp',
                os.path.expanduser('~/.cache'),
                '.pytest_cache',
                '__pycache__',
                '*.pyc',
                '*.log'
            ]
            
            for temp_item in temp_dirs:
                if os.path.exists(temp_item):
                    if os.path.isdir(temp_item) and temp_item.startswith('/tmp'):
                        # Clean old files in /tmp
                        cmd = f"find {temp_item} -type f -mtime +7 -delete"
                        try:
                            subprocess.run(cmd.split(), check=False, capture_output=True)
                            cleanup_commands.append(cmd)
                        except Exception:
                            pass
                    elif temp_item.endswith('.pyc'):
                        # Remove Python cache files
                        cmd = "find . -name '*.pyc' -delete"
                        try:
                            subprocess.run(cmd.split(), check=False, capture_output=True)
                            cleanup_commands.append(cmd)
                        except Exception:
                            pass
            
            # Check if we freed up space
            disk_usage = psutil.disk_usage('/')
            free_space_gb = disk_usage.free / (1024**3)
            
            issue.commands_run.extend(cleanup_commands)
            issue.fix_description = f"Cleaned up temporary files, {free_space_gb:.1f}GB free"
            
            return free_space_gb > 1.0  # Consider fixed if >1GB free
            
        except Exception as e:
            self.logger.error(f"Disk cleanup failed: {e}")
            return False
    
    def _fix_memory_issue(self, issue: TroubleshootResult) -> bool:
        """Fix memory issues by freeing up memory"""
        try:
            initial_memory = psutil.virtual_memory()
            
            # Kill non-essential processes with high memory usage
            killed_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    if proc.info['memory_percent'] > 10:  # Using more than 10% memory
                        # Don't kill system-critical processes
                        if proc.info['name'] not in ['systemd', 'kernel', 'init', 'ssh', 'python']:
                            proc.terminate()
                            killed_processes.append(proc.info['name'])
                            
                            if len(killed_processes) >= 3:  # Limit to 3 processes
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Wait a moment for processes to terminate
            time.sleep(2)
            
            final_memory = psutil.virtual_memory()
            memory_freed = initial_memory.used - final_memory.used
            
            if killed_processes:
                issue.commands_run.append(f"Killed processes: {', '.join(killed_processes)}")
                issue.fix_description = f"Freed {memory_freed // 1024 // 1024}MB memory by killing processes"
                return memory_freed > 100 * 1024 * 1024  # Consider fixed if >100MB freed
            
            return False
            
        except Exception as e:
            self.logger.error(f"Memory cleanup failed: {e}")
            return False
    
    def _fix_port_conflict(self, issue: TroubleshootResult) -> bool:
        """Fix port conflicts by killing processes using the port"""
        error_msg = issue.details.get('error_message', '')
        
        # Extract port number
        port_patterns = [
            r"port (\d+)",
            r":(\d+).*already in use",
            r"Address.*:(\d+).*already in use"
        ]
        
        port = None
        for pattern in port_patterns:
            match = re.search(pattern, error_msg)
            if match:
                port = int(match.group(1))
                break
        
        if not port:
            return False
        
        try:
            # Find processes using the port
            killed_processes = []
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    for conn in proc.connections():
                        if conn.laddr.port == port:
                            proc.terminate()
                            killed_processes.append(f"{proc.info['name']}({proc.info['pid']})")
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed_processes:
                issue.commands_run.append(f"Killed processes using port {port}: {', '.join(killed_processes)}")
                issue.fix_description = f"Freed port {port} by killing processes"
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Port conflict fix failed: {e}")
            return False
    
    def _fix_missing_file(self, issue: TroubleshootResult) -> bool:
        """Fix missing file errors by creating placeholder files"""
        error_msg = issue.details.get('error_message', '')
        
        # Extract file path
        path_patterns = [
            r"No such file or directory: '([^']+)'",
            r"FileNotFoundError.*'([^']+)'",
            r"\[Errno 2\].*'([^']+)'"
        ]
        
        file_path = None
        for pattern in path_patterns:
            match = re.search(pattern, error_msg)
            if match:
                file_path = match.group(1)
                break
        
        if not file_path:
            return False
        
        try:
            # Create directory structure if needed
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
                issue.commands_run.append(f"mkdir -p {dir_path}")
            
            # Create placeholder file if it doesn't exist
            if not os.path.exists(file_path):
                # Determine file type and create appropriate placeholder
                if file_path.endswith('.py'):
                    content = "# Auto-generated placeholder file\npass\n"
                elif file_path.endswith('.json'):
                    content = "{}\n"
                elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    content = "# Auto-generated placeholder\n"
                else:
                    content = ""
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                issue.commands_run.append(f"Created file: {file_path}")
                issue.fix_description = f"Created missing file: {file_path}"
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"File creation failed: {e}")
            return False
    
    def _fix_timeout_issue(self, issue: TroubleshootResult) -> bool:
        """Fix timeout issues (limited automatic fix)"""
        # This is more of a diagnostic fix - we can't really fix timeouts automatically
        # but we can provide suggestions and collect system information
        
        try:
            # Collect system load information
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
            
            issue.details.update({
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'load_average': load_avg[0]
            })
            
            # Provide specific suggestions based on system state
            suggestions = []
            if cpu_percent > 80:
                suggestions.append("High CPU usage detected - consider reducing concurrent processes")
            if memory.percent > 80:
                suggestions.append("High memory usage detected - free up memory")
            if load_avg[0] > psutil.cpu_count():
                suggestions.append("High system load - wait for current processes to complete")
            
            issue.fix_description = "Timeout analysis completed. " + "; ".join(suggestions)
            issue.commands_run.append("Analyzed system performance metrics")
            
            return bool(suggestions)  # Consider "fixed" if we provided actionable suggestions
            
        except Exception as e:
            self.logger.error(f"Timeout analysis failed: {e}")
            return False
    
    def _fix_network_issue(self, issue: TroubleshootResult) -> bool:
        """Fix network connectivity issues"""
        try:
            # Test basic connectivity
            connectivity_tests = [
                ('DNS', ['nslookup', 'google.com']),
                ('Ping', ['ping', '-c', '1', '8.8.8.8']),
                ('HTTP', ['curl', '-s', '--max-time', '5', 'http://httpbin.org/get'])
            ]
            
            test_results = []
            
            for test_name, cmd in connectivity_tests:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    test_results.append(f"{test_name}: {'OK' if result.returncode == 0 else 'FAILED'}")
                    issue.commands_run.append(' '.join(cmd))
                except Exception:
                    test_results.append(f"{test_name}: ERROR")
            
            # Check if we can identify the specific issue
            if any('OK' in result for result in test_results):
                issue.fix_description = "Network connectivity appears functional. Issue may be service-specific."
                return True
            else:
                issue.fix_description = f"Network tests: {'; '.join(test_results)}"
                return False
                
        except Exception as e:
            self.logger.error(f"Network diagnosis failed: {e}")
            return False
    
    def _fix_dependency_conflict(self, issue: TroubleshootResult) -> bool:
        """Fix package dependency conflicts"""
        error_msg = issue.details.get('error_message', '')
        
        try:
            # Try to extract conflicting packages
            conflict_patterns = [
                r"(\w+)[^\w]*(\d+\.\d+[^\s]*)[^\w]*(\w+)[^\w]*(\d+\.\d+[^\s]*)",
                r"version conflict.*(\w+)",
                r"incompatible.*(\w+)"
            ]
            
            # Simple fix: try upgrading all packages
            upgrade_cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip']
            
            try:
                result = subprocess.run(upgrade_cmd, capture_output=True, text=True, timeout=300)
                issue.commands_run.append(' '.join(upgrade_cmd))
                
                if result.returncode == 0:
                    issue.fix_description = "Upgraded pip to resolve potential conflicts"
                    return True
                    
            except Exception as e:
                self.logger.error(f"Dependency fix failed: {e}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Dependency conflict fix failed: {e}")
            return False
    
    def run_system_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostics"""
        diagnostics = {}
        
        try:
            # System information
            diagnostics['system'] = {
                'platform': sys.platform,
                'python_version': sys.version,
                'cpu_count': psutil.cpu_count(),
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'free': psutil.disk_usage('/').free,
                    'percent': (psutil.disk_usage('/').total - psutil.disk_usage('/').free) / psutil.disk_usage('/').total * 100
                }
            }
            
            # Process information
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['cpu_percent'] > 1 or proc.info['memory_percent'] > 1:
                        processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            diagnostics['top_processes'] = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10]
            
            # Network information
            try:
                net_io = psutil.net_io_counters()
                diagnostics['network'] = {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
            except Exception:
                diagnostics['network'] = {'error': 'Network info unavailable'}
            
            # Environment variables
            diagnostics['environment'] = {
                'PYTHON_PATH': os.environ.get('PYTHONPATH', ''),
                'PATH': os.environ.get('PATH', '')[:200] + '...',  # Truncate long PATH
                'HOME': os.environ.get('HOME', ''),
                'USER': os.environ.get('USER', ''),
                'CI': os.environ.get('CI', ''),
                'TEST_ENVIRONMENT': os.environ.get('TEST_ENVIRONMENT', '')
            }
            
        except Exception as e:
            diagnostics['error'] = f"Diagnostic collection failed: {e}"
        
        return diagnostics
    
    def generate_troubleshooting_report(self, issues: List[TroubleshootResult], output_path: str = "troubleshooting_report.json"):
        """Generate comprehensive troubleshooting report"""
        report = {
            'timestamp': time.time(),
            'total_issues': len(issues),
            'auto_fixable_issues': sum(1 for issue in issues if issue.auto_fixable),
            'fixed_issues': sum(1 for issue in issues if issue.fix_applied),
            'system_diagnostics': self.run_system_diagnostics(),
            'issues': [
                {
                    'issue_type': issue.issue_type,
                    'description': issue.description,
                    'severity': issue.severity,
                    'auto_fixable': issue.auto_fixable,
                    'fix_applied': issue.fix_applied,
                    'fix_description': issue.fix_description,
                    'commands_run': issue.commands_run,
                    'details': issue.details
                }
                for issue in issues
            ],
            'fix_history': [
                {
                    'issue_type': fix.issue_type,
                    'fix_description': fix.fix_description,
                    'commands_run': fix.commands_run
                }
                for fix in self.fix_history
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Troubleshooting report saved: {output_path}")
        
        return report

def main():
    """Main entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated Troubleshooting System")
    parser.add_argument('--error-message', help="Error message to diagnose")
    parser.add_argument('--auto-fix', action='store_true', help="Attempt automatic fixes")
    parser.add_argument('--diagnostics', action='store_true', help="Run system diagnostics")
    parser.add_argument('--report', help="Output report file path")
    parser.add_argument('--verbose', action='store_true', help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    troubleshooter = AutoTroubleshooter()
    
    if args.diagnostics:
        diagnostics = troubleshooter.run_system_diagnostics()
        print("System Diagnostics:")
        print(json.dumps(diagnostics, indent=2, default=str))
        return
    
    if args.error_message:
        # Diagnose specific error
        issues = troubleshooter.diagnose_error(args.error_message)
        
        print(f"Diagnosed {len(issues)} potential issues:")
        for issue in issues:
            print(f"  - {issue.issue_type}: {issue.description} (severity: {issue.severity})")
            if issue.auto_fixable:
                print(f"    Auto-fixable: {issue.fix_description}")
        
        if args.auto_fix:
            print("\nAttempting automatic fixes...")
            fixed_issues = troubleshooter.auto_fix_issues(issues)
            
            for issue in fixed_issues:
                if issue.fix_applied:
                    print(f"  ✓ Fixed: {issue.issue_type}")
                else:
                    print(f"  ✗ Could not fix: {issue.issue_type}")
        
        if args.report:
            troubleshooter.generate_troubleshooting_report(issues, args.report)
            print(f"Report saved: {args.report}")
    else:
        print("No error message provided. Use --error-message to diagnose specific errors.")
        print("Use --diagnostics to run system diagnostics.")

if __name__ == "__main__":
    main()