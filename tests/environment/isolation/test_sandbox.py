#!/usr/bin/env python3
"""
Test Sandbox and Isolation System
Provides comprehensive test isolation, resource management, and cleanup mechanisms.
"""

import os
import sys
import shutil
import tempfile
import subprocess
import threading
import time
import signal
import psutil
import logging
from typing import Dict, List, Optional, Callable, Any
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class SandboxConfig:
    """Configuration for test sandbox"""
    name: str
    temp_dir: str = None
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0
    timeout_seconds: int = 300
    network_isolation: bool = False
    filesystem_isolation: bool = True
    process_isolation: bool = True
    cleanup_on_exit: bool = True
    preserve_on_error: bool = True

@dataclass
class ResourceLimits:
    """Resource limits for sandboxed execution"""
    memory_limit: int = 512 * 1024 * 1024  # 512MB in bytes
    cpu_limit: float = 50.0  # CPU percentage
    file_limit: int = 1000  # Max open files
    process_limit: int = 100  # Max processes
    time_limit: int = 300  # Max execution time in seconds

class TestSandbox:
    """Comprehensive test isolation and sandboxing system"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.temp_dir = None
        self.original_cwd = os.getcwd()
        self.created_files = set()
        self.spawned_processes = []
        self.resource_monitor = None
        self.cleanup_callbacks = []
        self.active = False
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for sandbox"""
        logger = logging.getLogger(f"sandbox.{self.config.name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def __enter__(self):
        """Enter sandbox context"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sandbox context"""
        self.cleanup(preserve_on_error=(exc_type is not None and self.config.preserve_on_error))
    
    def start(self):
        """Start sandbox environment"""
        if self.active:
            self.logger.warning("Sandbox already active")
            return
        
        self.logger.info(f"Starting sandbox: {self.config.name}")
        
        # Create isolated temporary directory
        if self.config.filesystem_isolation:
            self._setup_filesystem_isolation()
        
        # Setup resource monitoring
        if self.config.max_memory_mb or self.config.max_cpu_percent:
            self._start_resource_monitoring()
        
        # Setup process isolation
        if self.config.process_isolation:
            self._setup_process_isolation()
        
        # Setup network isolation (if supported)
        if self.config.network_isolation:
            self._setup_network_isolation()
        
        self.active = True
        self.logger.info(f"Sandbox {self.config.name} started successfully")
    
    def _setup_filesystem_isolation(self):
        """Setup filesystem isolation"""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{self.config.name}_")
        self.logger.info(f"Created sandbox directory: {self.temp_dir}")
        
        # Change to sandbox directory
        os.chdir(self.temp_dir)
        
        # Create common directories
        common_dirs = ['tmp', 'work', 'data', 'logs']
        for dir_name in common_dirs:
            os.makedirs(dir_name, exist_ok=True)
        
        # Set environment variables for isolation
        os.environ['TMPDIR'] = os.path.join(self.temp_dir, 'tmp')
        os.environ['HOME'] = self.temp_dir
        os.environ['SANDBOX_DIR'] = self.temp_dir
    
    def _setup_process_isolation(self):
        """Setup process isolation (where supported)"""
        # Set process limits
        try:
            import resource
            
            # Set memory limit
            if self.config.max_memory_mb:
                memory_limit = self.config.max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # Set CPU time limit
            if self.config.timeout_seconds:
                resource.setrlimit(resource.RLIMIT_CPU, (self.config.timeout_seconds, self.config.timeout_seconds))
            
            self.logger.info("Process limits configured")
            
        except ImportError:
            self.logger.warning("Resource limits not available on this platform")
        except Exception as e:
            self.logger.warning(f"Failed to set process limits: {e}")
    
    def _setup_network_isolation(self):
        """Setup network isolation (basic implementation)"""
        # This is a simplified version - full network isolation requires containerization
        self.logger.warning("Network isolation requested but not fully implemented")
        
        # Set proxy variables to disable network access
        network_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
        for var in network_vars:
            os.environ[var] = 'http://127.0.0.1:9999'  # Non-existent proxy
    
    def _start_resource_monitoring(self):
        """Start resource monitoring thread"""
        self.resource_monitor = ResourceMonitor(
            max_memory_mb=self.config.max_memory_mb,
            max_cpu_percent=self.config.max_cpu_percent,
            logger=self.logger
        )
        self.resource_monitor.start()
    
    def run_isolated(self, func: Callable, *args, **kwargs) -> Any:
        """Run function in isolated environment"""
        if not self.active:
            raise RuntimeError("Sandbox not active")
        
        self.logger.info(f"Running function {func.__name__} in sandbox")
        
        try:
            # Track resource usage before
            initial_memory = psutil.virtual_memory().used
            initial_cpu = psutil.cpu_percent()
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Track resource usage after
            final_memory = psutil.virtual_memory().used
            final_cpu = psutil.cpu_percent()
            
            self.logger.info(f"Function completed. Memory delta: {(final_memory - initial_memory) // 1024 // 1024}MB")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Function execution failed: {e}")
            raise
    
    def run_command(self, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run command in sandboxed environment"""
        if not self.active:
            raise RuntimeError("Sandbox not active")
        
        self.logger.info(f"Running command: {' '.join(cmd)}")
        
        # Set sandbox environment
        env = os.environ.copy()
        if self.temp_dir:
            env['SANDBOX_DIR'] = self.temp_dir
        
        try:
            # Run with timeout and resource limits
            result = subprocess.run(
                cmd,
                env=env,
                timeout=self.config.timeout_seconds,
                **kwargs
            )
            
            self.logger.info(f"Command completed with return code: {result.returncode}")
            return result
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {self.config.timeout_seconds} seconds")
            raise
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise
    
    def create_file(self, filepath: str, content: str = "") -> str:
        """Create file in sandbox and track for cleanup"""
        if not self.active:
            raise RuntimeError("Sandbox not active")
        
        full_path = os.path.abspath(filepath)
        
        # Ensure file is within sandbox
        if self.temp_dir and not full_path.startswith(self.temp_dir):
            full_path = os.path.join(self.temp_dir, filepath)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write file
        with open(full_path, 'w') as f:
            f.write(content)
        
        self.created_files.add(full_path)
        self.logger.debug(f"Created file: {full_path}")
        
        return full_path
    
    def add_cleanup_callback(self, callback: Callable):
        """Add cleanup callback"""
        self.cleanup_callbacks.append(callback)
    
    def cleanup(self, preserve_on_error: bool = False):
        """Cleanup sandbox environment"""
        if not self.active:
            return
        
        self.logger.info(f"Cleaning up sandbox: {self.config.name}")
        
        # Stop resource monitoring
        if self.resource_monitor:
            self.resource_monitor.stop()
            self.resource_monitor = None
        
        # Kill spawned processes
        self._cleanup_processes()
        
        # Run custom cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Cleanup callback failed: {e}")
        
        # Restore working directory
        try:
            os.chdir(self.original_cwd)
        except Exception as e:
            self.logger.error(f"Failed to restore working directory: {e}")
        
        # Clean up filesystem
        if self.temp_dir and not preserve_on_error:
            self._cleanup_filesystem()
        elif preserve_on_error:
            self.logger.info(f"Preserving sandbox directory: {self.temp_dir}")
        
        self.active = False
        self.logger.info("Sandbox cleanup completed")
    
    def _cleanup_processes(self):
        """Kill all spawned processes"""
        for proc in self.spawned_processes:
            try:
                if proc.is_running():
                    proc.terminate()
                    proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
            except Exception as e:
                self.logger.error(f"Error cleaning up process {proc.pid}: {e}")
    
    def _cleanup_filesystem(self):
        """Clean up temporary files and directories"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Removed sandbox directory: {self.temp_dir}")
            except Exception as e:
                self.logger.error(f"Failed to remove sandbox directory: {e}")

class ResourceMonitor:
    """Monitor resource usage in sandbox"""
    
    def __init__(self, max_memory_mb: int, max_cpu_percent: float, logger: logging.Logger):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.logger = logger
        self.monitoring = False
        self.thread = None
        self.violations = []
    
    def start(self):
        """Start monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info("Resource monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=1)
        self.logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Check memory usage
                if self.max_memory_mb:
                    current_process = psutil.Process()
                    memory_mb = current_process.memory_info().rss / 1024 / 1024
                    
                    if memory_mb > self.max_memory_mb:
                        violation = f"Memory limit exceeded: {memory_mb:.1f}MB > {self.max_memory_mb}MB"
                        self.violations.append(violation)
                        self.logger.warning(violation)
                
                # Check CPU usage
                if self.max_cpu_percent:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    
                    if cpu_percent > self.max_cpu_percent:
                        violation = f"CPU limit exceeded: {cpu_percent:.1f}% > {self.max_cpu_percent}%"
                        self.violations.append(violation)
                        self.logger.warning(violation)
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Resource monitoring error: {e}")
                break

@contextmanager
def test_sandbox(name: str, **config_kwargs):
    """Context manager for test sandbox"""
    config = SandboxConfig(name=name, **config_kwargs)
    sandbox = TestSandbox(config)
    
    try:
        sandbox.start()
        yield sandbox
    finally:
        sandbox.cleanup()

def main():
    """Main entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Sandbox System")
    parser.add_argument('--name', default="test", help="Sandbox name")
    parser.add_argument('--memory-limit', type=int, default=512, help="Memory limit in MB")
    parser.add_argument('--cpu-limit', type=float, default=50.0, help="CPU limit percentage")
    parser.add_argument('--timeout', type=int, default=60, help="Timeout in seconds")
    parser.add_argument('--command', nargs='+', help="Command to run in sandbox")
    
    args = parser.parse_args()
    
    config = SandboxConfig(
        name=args.name,
        max_memory_mb=args.memory_limit,
        max_cpu_percent=args.cpu_limit,
        timeout_seconds=args.timeout
    )
    
    with test_sandbox(args.name, **config.__dict__) as sandbox:
        if args.command:
            result = sandbox.run_command(args.command, capture_output=True, text=True)
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
        else:
            print(f"Sandbox {args.name} created successfully")
            print(f"Sandbox directory: {sandbox.temp_dir}")
            input("Press Enter to cleanup...")

if __name__ == "__main__":
    main()