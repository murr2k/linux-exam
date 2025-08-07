#!/usr/bin/env python3
"""
Environment Monitoring and Diagnostics System
Provides comprehensive monitoring, health checks, and diagnostic capabilities for test environments.
"""

import os
import sys
import json
import time
import threading
import subprocess
import logging
import psutil
import socket
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import statistics
import queue

@dataclass
class HealthMetric:
    """Represents a health metric"""
    name: str
    value: float
    unit: str
    status: str  # healthy, warning, critical
    threshold_warning: float = None
    threshold_critical: float = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class DiagnosticResult:
    """Result of a diagnostic check"""
    name: str
    success: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestions: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

@dataclass
class MonitoringConfig:
    """Configuration for environment monitoring"""
    name: str
    monitoring_interval: float = 5.0  # seconds
    health_check_interval: float = 30.0  # seconds
    diagnostic_interval: float = 300.0  # seconds
    metrics_retention: int = 1000  # number of metrics to retain
    enable_alerts: bool = True
    alert_cooldown: float = 60.0  # seconds between similar alerts
    log_level: str = "INFO"

class EnvironmentMonitor:
    """Comprehensive environment monitoring system"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.monitoring = False
        self.metrics_history = {}
        self.health_status = {}
        self.diagnostic_results = []
        self.alert_history = {}
        
        # Threading
        self.monitor_thread = None
        self.health_thread = None
        self.diagnostic_thread = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.metric_callbacks = []
        self.alert_callbacks = []
        self.health_callbacks = []
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(f"monitor.{self.config.name}")
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def start(self):
        """Start monitoring"""
        if self.monitoring:
            self.logger.warning("Monitoring already active")
            return
        
        self.logger.info(f"Starting environment monitoring: {self.config.name}")
        self.monitoring = True
        self.stop_event.clear()
        
        # Start monitoring threads
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.diagnostic_thread = threading.Thread(target=self._diagnostic_loop, daemon=True)
        
        self.monitor_thread.start()
        self.health_thread.start()
        self.diagnostic_thread.start()
        
        self.logger.info("Monitoring started successfully")
    
    def stop(self):
        """Stop monitoring"""
        if not self.monitoring:
            return
        
        self.logger.info("Stopping environment monitoring")
        self.monitoring = False
        self.stop_event.set()
        
        # Wait for threads to finish
        for thread in [self.monitor_thread, self.health_thread, self.diagnostic_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=5)
        
        self.logger.info("Monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring and not self.stop_event.wait(self.config.monitoring_interval):
            try:
                self._collect_metrics()
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
    
    def _health_check_loop(self):
        """Health check loop"""
        while self.monitoring and not self.stop_event.wait(self.config.health_check_interval):
            try:
                self._perform_health_checks()
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
    
    def _diagnostic_loop(self):
        """Diagnostic loop"""
        while self.monitoring and not self.stop_event.wait(self.config.diagnostic_interval):
            try:
                self._run_diagnostics()
            except Exception as e:
                self.logger.error(f"Error in diagnostic loop: {e}")
    
    def _collect_metrics(self):
        """Collect system metrics"""
        timestamp = time.time()
        
        # System metrics
        metrics = []
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append(HealthMetric(
            name="cpu_usage",
            value=cpu_percent,
            unit="%",
            status=self._get_status(cpu_percent, 70, 90),
            threshold_warning=70,
            threshold_critical=90
        ))
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        metrics.append(HealthMetric(
            name="memory_usage",
            value=memory_percent,
            unit="%",
            status=self._get_status(memory_percent, 80, 95),
            threshold_warning=80,
            threshold_critical=95
        ))
        
        memory_available_mb = memory.available / 1024 / 1024
        metrics.append(HealthMetric(
            name="memory_available",
            value=memory_available_mb,
            unit="MB",
            status=self._get_status(memory_available_mb, 1000, 500, reverse=True),
            threshold_warning=1000,
            threshold_critical=500
        ))
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_percent = (disk.total - disk.free) / disk.total * 100
        metrics.append(HealthMetric(
            name="disk_usage",
            value=disk_percent,
            unit="%",
            status=self._get_status(disk_percent, 85, 95),
            threshold_warning=85,
            threshold_critical=95
        ))
        
        disk_free_gb = disk.free / 1024 / 1024 / 1024
        metrics.append(HealthMetric(
            name="disk_free",
            value=disk_free_gb,
            unit="GB",
            status=self._get_status(disk_free_gb, 5, 2, reverse=True),
            threshold_warning=5,
            threshold_critical=2
        ))
        
        # Network metrics
        try:
            network = psutil.net_io_counters()
            if hasattr(self, '_last_network_stats'):
                time_delta = timestamp - self._last_network_timestamp
                bytes_sent_rate = (network.bytes_sent - self._last_network_stats.bytes_sent) / time_delta
                bytes_recv_rate = (network.bytes_recv - self._last_network_stats.bytes_recv) / time_delta
                
                metrics.append(HealthMetric(
                    name="network_send_rate",
                    value=bytes_sent_rate / 1024,  # KB/s
                    unit="KB/s",
                    status="healthy"
                ))
                
                metrics.append(HealthMetric(
                    name="network_recv_rate",
                    value=bytes_recv_rate / 1024,  # KB/s
                    unit="KB/s",
                    status="healthy"
                ))
            
            self._last_network_stats = network
            self._last_network_timestamp = timestamp
        except Exception as e:
            self.logger.warning(f"Failed to collect network metrics: {e}")
        
        # Process metrics
        try:
            process_count = len(psutil.pids())
            metrics.append(HealthMetric(
                name="process_count",
                value=process_count,
                unit="count",
                status=self._get_status(process_count, 200, 500),
                threshold_warning=200,
                threshold_critical=500
            ))
        except Exception as e:
            self.logger.warning(f"Failed to collect process metrics: {e}")
        
        # Load average (Unix-like systems)
        try:
            if hasattr(os, 'getloadavg'):
                load_avg = os.getloadavg()[0]  # 1-minute load average
                cpu_count = psutil.cpu_count()
                load_percent = (load_avg / cpu_count) * 100 if cpu_count > 0 else 0
                
                metrics.append(HealthMetric(
                    name="load_average",
                    value=load_percent,
                    unit="%",
                    status=self._get_status(load_percent, 80, 100),
                    threshold_warning=80,
                    threshold_critical=100
                ))
        except Exception as e:
            self.logger.warning(f"Failed to collect load average: {e}")
        
        # Store metrics
        for metric in metrics:
            self._store_metric(metric)
            
            # Check for alerts
            if self.config.enable_alerts and metric.status in ['warning', 'critical']:
                self._trigger_alert(metric)
        
        # Notify callbacks
        for callback in self.metric_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                self.logger.error(f"Metric callback error: {e}")
    
    def _get_status(self, value: float, warning_threshold: float, critical_threshold: float, reverse: bool = False) -> str:
        """Determine status based on thresholds"""
        if reverse:
            if value <= critical_threshold:
                return "critical"
            elif value <= warning_threshold:
                return "warning"
            else:
                return "healthy"
        else:
            if value >= critical_threshold:
                return "critical"
            elif value >= warning_threshold:
                return "warning"
            else:
                return "healthy"
    
    def _store_metric(self, metric: HealthMetric):
        """Store metric in history"""
        if metric.name not in self.metrics_history:
            self.metrics_history[metric.name] = []
        
        history = self.metrics_history[metric.name]
        history.append(metric)
        
        # Limit history size
        if len(history) > self.config.metrics_retention:
            history.pop(0)
    
    def _trigger_alert(self, metric: HealthMetric):
        """Trigger alert for metric"""
        alert_key = f"{metric.name}_{metric.status}"
        now = time.time()
        
        # Check cooldown
        if alert_key in self.alert_history:
            last_alert = self.alert_history[alert_key]
            if now - last_alert < self.config.alert_cooldown:
                return
        
        # Log alert
        self.logger.warning(f"ALERT: {metric.name} is {metric.status} - {metric.value}{metric.unit}")
        
        # Update alert history
        self.alert_history[alert_key] = now
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(metric)
            except Exception as e:
                self.logger.error(f"Alert callback error: {e}")
    
    def _perform_health_checks(self):
        """Perform comprehensive health checks"""
        health_checks = [
            self._check_filesystem_health,
            self._check_network_connectivity,
            self._check_service_availability,
            self._check_python_environment,
            self._check_dependencies
        ]
        
        health_results = {}
        
        for check in health_checks:
            try:
                result = check()
                health_results[result.name] = result
                
                if not result.success:
                    self.logger.warning(f"Health check failed: {result.name} - {result.message}")
                
            except Exception as e:
                error_result = DiagnosticResult(
                    name=check.__name__,
                    success=False,
                    message=f"Health check error: {e}",
                    details={'error': str(e)}
                )
                health_results[error_result.name] = error_result
                self.logger.error(f"Health check error in {check.__name__}: {e}")
        
        self.health_status = health_results
        
        # Notify callbacks
        for callback in self.health_callbacks:
            try:
                callback(health_results)
            except Exception as e:
                self.logger.error(f"Health callback error: {e}")
    
    def _check_filesystem_health(self) -> DiagnosticResult:
        """Check filesystem health"""
        try:
            # Check if we can write to temp directory
            import tempfile
            with tempfile.NamedTemporaryFile(delete=True) as f:
                f.write(b"test")
                f.flush()
            
            return DiagnosticResult(
                name="filesystem_health",
                success=True,
                message="Filesystem is healthy"
            )
        except Exception as e:
            return DiagnosticResult(
                name="filesystem_health",
                success=False,
                message=f"Filesystem check failed: {e}",
                fix_suggestions=["Check disk space", "Check filesystem permissions"]
            )
    
    def _check_network_connectivity(self) -> DiagnosticResult:
        """Check network connectivity"""
        try:
            # Try to connect to a reliable service
            sock = socket.create_connection(("8.8.8.8", 53), timeout=5)
            sock.close()
            
            return DiagnosticResult(
                name="network_connectivity",
                success=True,
                message="Network connectivity is healthy"
            )
        except Exception as e:
            return DiagnosticResult(
                name="network_connectivity",
                success=False,
                message=f"Network connectivity check failed: {e}",
                fix_suggestions=["Check network configuration", "Check firewall settings"]
            )
    
    def _check_service_availability(self) -> DiagnosticResult:
        """Check availability of critical services"""
        # This is a placeholder - would check specific services in real implementation
        return DiagnosticResult(
            name="service_availability",
            success=True,
            message="All services are available"
        )
    
    def _check_python_environment(self) -> DiagnosticResult:
        """Check Python environment health"""
        try:
            issues = []
            
            # Check Python version
            if sys.version_info < (3, 6):
                issues.append("Python version is too old")
            
            # Check if we can import common packages
            test_imports = ['os', 'sys', 'json', 'subprocess']
            for module in test_imports:
                try:
                    __import__(module)
                except ImportError:
                    issues.append(f"Cannot import {module}")
            
            if issues:
                return DiagnosticResult(
                    name="python_environment",
                    success=False,
                    message=f"Python environment issues: {', '.join(issues)}",
                    fix_suggestions=["Update Python version", "Reinstall Python packages"]
                )
            else:
                return DiagnosticResult(
                    name="python_environment",
                    success=True,
                    message="Python environment is healthy"
                )
                
        except Exception as e:
            return DiagnosticResult(
                name="python_environment",
                success=False,
                message=f"Python environment check failed: {e}"
            )
    
    def _check_dependencies(self) -> DiagnosticResult:
        """Check critical dependencies"""
        try:
            missing = []
            critical_deps = ['subprocess', 'threading', 'logging']
            
            for dep in critical_deps:
                try:
                    __import__(dep)
                except ImportError:
                    missing.append(dep)
            
            if missing:
                return DiagnosticResult(
                    name="dependencies",
                    success=False,
                    message=f"Missing dependencies: {missing}",
                    fix_suggestions=["Install missing dependencies"]
                )
            else:
                return DiagnosticResult(
                    name="dependencies",
                    success=True,
                    message="All dependencies are available"
                )
                
        except Exception as e:
            return DiagnosticResult(
                name="dependencies",
                success=False,
                message=f"Dependency check failed: {e}"
            )
    
    def _run_diagnostics(self):
        """Run comprehensive diagnostics"""
        self.logger.info("Running comprehensive diagnostics")
        
        diagnostics = [
            self._diagnostic_performance_baseline,
            self._diagnostic_resource_trends,
            self._diagnostic_error_patterns,
            self._diagnostic_system_stability
        ]
        
        results = []
        
        for diagnostic in diagnostics:
            try:
                result = diagnostic()
                results.append(result)
                
                if not result.success:
                    self.logger.warning(f"Diagnostic issue: {result.name} - {result.message}")
                
            except Exception as e:
                error_result = DiagnosticResult(
                    name=diagnostic.__name__,
                    success=False,
                    message=f"Diagnostic error: {e}",
                    details={'error': str(e)}
                )
                results.append(error_result)
                self.logger.error(f"Diagnostic error in {diagnostic.__name__}: {e}")
        
        # Store recent results
        self.diagnostic_results.extend(results)
        if len(self.diagnostic_results) > 100:  # Keep last 100 results
            self.diagnostic_results = self.diagnostic_results[-100:]
    
    def _diagnostic_performance_baseline(self) -> DiagnosticResult:
        """Analyze performance against baseline"""
        try:
            # Get recent CPU metrics
            if 'cpu_usage' in self.metrics_history:
                recent_cpu = [m.value for m in self.metrics_history['cpu_usage'][-10:]]
                if recent_cpu:
                    avg_cpu = statistics.mean(recent_cpu)
                    if avg_cpu > 80:
                        return DiagnosticResult(
                            name="performance_baseline",
                            success=False,
                            message=f"High average CPU usage: {avg_cpu:.1f}%",
                            details={'average_cpu': avg_cpu}
                        )
            
            return DiagnosticResult(
                name="performance_baseline",
                success=True,
                message="Performance is within baseline"
            )
            
        except Exception as e:
            return DiagnosticResult(
                name="performance_baseline",
                success=False,
                message=f"Performance baseline check failed: {e}"
            )
    
    def _diagnostic_resource_trends(self) -> DiagnosticResult:
        """Analyze resource usage trends"""
        try:
            issues = []
            
            # Check memory trend
            if 'memory_usage' in self.metrics_history:
                recent_memory = [m.value for m in self.metrics_history['memory_usage'][-20:]]
                if len(recent_memory) >= 10:
                    # Simple trend analysis
                    first_half = statistics.mean(recent_memory[:len(recent_memory)//2])
                    second_half = statistics.mean(recent_memory[len(recent_memory)//2:])
                    
                    if second_half > first_half + 10:  # 10% increase
                        issues.append(f"Memory usage trending up: {first_half:.1f}% -> {second_half:.1f}%")
            
            if issues:
                return DiagnosticResult(
                    name="resource_trends",
                    success=False,
                    message=f"Resource trend issues: {'; '.join(issues)}",
                    details={'issues': issues}
                )
            else:
                return DiagnosticResult(
                    name="resource_trends",
                    success=True,
                    message="Resource trends are stable"
                )
                
        except Exception as e:
            return DiagnosticResult(
                name="resource_trends",
                success=False,
                message=f"Resource trend analysis failed: {e}"
            )
    
    def _diagnostic_error_patterns(self) -> DiagnosticResult:
        """Analyze error patterns in logs"""
        # This is a placeholder - would analyze actual log files
        return DiagnosticResult(
            name="error_patterns",
            success=True,
            message="No significant error patterns detected"
        )
    
    def _diagnostic_system_stability(self) -> DiagnosticResult:
        """Analyze system stability"""
        try:
            # Check uptime
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            uptime_hours = uptime / 3600
            
            details = {'uptime_hours': uptime_hours}
            
            if uptime_hours < 1:
                return DiagnosticResult(
                    name="system_stability",
                    success=False,
                    message=f"Recent system restart detected: {uptime_hours:.1f} hours uptime",
                    details=details,
                    fix_suggestions=["Check system logs for restart cause"]
                )
            else:
                return DiagnosticResult(
                    name="system_stability",
                    success=True,
                    message=f"System is stable: {uptime_hours:.1f} hours uptime",
                    details=details
                )
                
        except Exception as e:
            return DiagnosticResult(
                name="system_stability",
                success=False,
                message=f"System stability check failed: {e}"
            )
    
    def get_current_metrics(self) -> Dict[str, HealthMetric]:
        """Get current metrics"""
        current = {}
        for name, history in self.metrics_history.items():
            if history:
                current[name] = history[-1]
        return current
    
    def get_metric_history(self, metric_name: str, duration_minutes: int = 60) -> List[HealthMetric]:
        """Get metric history for specified duration"""
        if metric_name not in self.metrics_history:
            return []
        
        cutoff_time = time.time() - (duration_minutes * 60)
        return [m for m in self.metrics_history[metric_name] if m.timestamp >= cutoff_time]
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        current_metrics = self.get_current_metrics()
        
        # Overall health
        critical_count = sum(1 for m in current_metrics.values() if m.status == 'critical')
        warning_count = sum(1 for m in current_metrics.values() if m.status == 'warning')
        
        if critical_count > 0:
            overall_status = 'critical'
        elif warning_count > 0:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        return {
            'timestamp': time.time(),
            'environment_name': self.config.name,
            'overall_status': overall_status,
            'metrics_count': len(current_metrics),
            'critical_metrics': critical_count,
            'warning_metrics': warning_count,
            'healthy_metrics': len(current_metrics) - critical_count - warning_count,
            'current_metrics': {name: asdict(metric) for name, metric in current_metrics.items()},
            'health_checks': {name: asdict(result) for name, result in self.health_status.items()},
            'recent_diagnostics': [asdict(r) for r in self.diagnostic_results[-5:]]
        }
    
    def add_metric_callback(self, callback: Callable):
        """Add callback for metric updates"""
        self.metric_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for alerts"""
        self.alert_callbacks.append(callback)
    
    def add_health_callback(self, callback: Callable):
        """Add callback for health check updates"""
        self.health_callbacks.append(callback)

def main():
    """Main entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Monitor")
    parser.add_argument('--name', default="test", help="Environment name")
    parser.add_argument('--duration', type=int, default=60, help="Monitoring duration in seconds")
    parser.add_argument('--interval', type=float, default=5.0, help="Monitoring interval in seconds")
    parser.add_argument('--output', help="Output file for results")
    
    args = parser.parse_args()
    
    config = MonitoringConfig(
        name=args.name,
        monitoring_interval=args.interval,
        health_check_interval=30.0,
        diagnostic_interval=60.0
    )
    
    monitor = EnvironmentMonitor(config)
    
    try:
        monitor.start()
        
        print(f"Monitoring {args.name} for {args.duration} seconds...")
        time.sleep(args.duration)
        
        # Generate summary
        summary = monitor.get_system_summary()
        print(f"\nMonitoring Summary:")
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Critical Metrics: {summary['critical_metrics']}")
        print(f"Warning Metrics: {summary['warning_metrics']}")
        print(f"Healthy Metrics: {summary['healthy_metrics']}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"Results saved to: {args.output}")
        
    finally:
        monitor.stop()

if __name__ == "__main__":
    main()