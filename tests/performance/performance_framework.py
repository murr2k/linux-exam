#!/usr/bin/env python3
"""
Performance Regression Testing Framework for Linux Kernel Drivers
Implements automated baselines, statistical analysis, and trend detection.
"""

import time
import statistics
import json
import subprocess
import psutil
import threading
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import sqlite3
import hashlib

class PerformanceMetric(Enum):
    """Types of performance metrics to track."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    I2C_TRANSACTION_RATE = "i2c_transaction_rate"
    INTERRUPT_LATENCY = "interrupt_latency"
    POWER_CONSUMPTION = "power_consumption"
    ERROR_RATE = "error_rate"

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PerformanceBenchmark:
    """Definition of a performance benchmark."""
    name: str
    test_function: Callable
    metric_type: PerformanceMetric
    iterations: int = 100
    warmup_iterations: int = 10
    timeout: float = 60.0
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceResult:
    """Result of a single performance test."""
    benchmark_name: str
    metric_type: PerformanceMetric
    values: List[float]
    timestamp: datetime
    system_info: Dict[str, Any]
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    percentile_95: float = 0.0
    percentile_99: float = 0.0
    
    def __post_init__(self):
        """Calculate statistics after initialization."""
        if self.values:
            self.mean = statistics.mean(self.values)
            self.median = statistics.median(self.values)
            self.std_dev = statistics.stdev(self.values) if len(self.values) > 1 else 0.0
            self.min_value = min(self.values)
            self.max_value = max(self.values)
            self.percentile_95 = np.percentile(self.values, 95)
            self.percentile_99 = np.percentile(self.values, 99)

@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison."""
    benchmark_name: str
    metric_type: PerformanceMetric
    baseline_mean: float
    baseline_std: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    created_at: datetime
    git_commit: Optional[str] = None
    
@dataclass
class RegressionAlert:
    """Performance regression alert."""
    benchmark_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    baseline_value: float
    regression_percentage: float
    timestamp: datetime
    statistical_significance: float

class PerformanceDatabase:
    """SQLite database for storing performance data."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_name TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                mean_value REAL NOT NULL,
                median_value REAL NOT NULL,
                std_dev REAL NOT NULL,
                min_value REAL NOT NULL,
                max_value REAL NOT NULL,
                percentile_95 REAL NOT NULL,
                percentile_99 REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                git_commit TEXT,
                system_info TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_name TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                baseline_mean REAL NOT NULL,
                baseline_std REAL NOT NULL,
                confidence_low REAL NOT NULL,
                confidence_high REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                git_commit TEXT,
                UNIQUE(benchmark_name, metric_type)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regression_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                current_value REAL NOT NULL,
                baseline_value REAL NOT NULL,
                regression_percentage REAL NOT NULL,
                statistical_significance REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def store_result(self, result: PerformanceResult):
        """Store performance result in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_results 
            (benchmark_name, metric_type, mean_value, median_value, std_dev,
             min_value, max_value, percentile_95, percentile_99, sample_size,
             timestamp, git_commit, system_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.benchmark_name,
            result.metric_type.value,
            result.mean,
            result.median,
            result.std_dev,
            result.min_value,
            result.max_value,
            result.percentile_95,
            result.percentile_99,
            len(result.values),
            result.timestamp.isoformat(),
            self._get_git_commit(),
            json.dumps(result.system_info)
        ))
        
        conn.commit()
        conn.close()
        
    def store_baseline(self, baseline: PerformanceBaseline):
        """Store performance baseline."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO performance_baselines
            (benchmark_name, metric_type, baseline_mean, baseline_std,
             confidence_low, confidence_high, sample_size, created_at, git_commit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            baseline.benchmark_name,
            baseline.metric_type.value,
            baseline.baseline_mean,
            baseline.baseline_std,
            baseline.confidence_interval[0],
            baseline.confidence_interval[1],
            baseline.sample_size,
            baseline.created_at.isoformat(),
            baseline.git_commit
        ))
        
        conn.commit()
        conn.close()
        
    def get_baseline(self, benchmark_name: str, metric_type: PerformanceMetric) -> Optional[PerformanceBaseline]:
        """Get performance baseline."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM performance_baselines 
            WHERE benchmark_name = ? AND metric_type = ?
        ''', (benchmark_name, metric_type.value))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return PerformanceBaseline(
                benchmark_name=row[1],
                metric_type=PerformanceMetric(row[2]),
                baseline_mean=row[3],
                baseline_std=row[4],
                confidence_interval=(row[5], row[6]),
                sample_size=row[7],
                created_at=datetime.fromisoformat(row[8]),
                git_commit=row[9]
            )
        return None
        
    def get_historical_results(self, benchmark_name: str, 
                             days: int = 30) -> List[Tuple[datetime, float]]:
        """Get historical performance results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT timestamp, mean_value FROM performance_results
            WHERE benchmark_name = ? AND timestamp > ?
            ORDER BY timestamp
        ''', (benchmark_name, cutoff_date.isoformat()))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [(datetime.fromisoformat(row[0]), row[1]) for row in rows]
        
    def store_alert(self, alert: RegressionAlert):
        """Store regression alert."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO regression_alerts
            (benchmark_name, severity, message, current_value, baseline_value,
             regression_percentage, statistical_significance, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.benchmark_name,
            alert.severity.value,
            alert.message,
            alert.current_value,
            alert.baseline_value,
            alert.regression_percentage,
            alert.statistical_significance,
            alert.timestamp.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            return None

class StatisticalAnalyzer:
    """Statistical analysis for performance data."""
    
    @staticmethod
    def calculate_baseline(results: List[PerformanceResult], 
                          confidence_level: float = 0.95) -> PerformanceBaseline:
        """Calculate performance baseline from historical results."""
        if not results:
            raise ValueError("No results provided for baseline calculation")
            
        all_values = []
        for result in results:
            all_values.extend(result.values)
            
        mean_val = statistics.mean(all_values)
        std_val = statistics.stdev(all_values) if len(all_values) > 1 else 0.0
        
        # Calculate confidence interval
        alpha = 1 - confidence_level
        t_critical = stats.t.ppf(1 - alpha/2, len(all_values) - 1)
        margin_of_error = t_critical * (std_val / np.sqrt(len(all_values)))
        
        confidence_interval = (mean_val - margin_of_error, mean_val + margin_of_error)
        
        return PerformanceBaseline(
            benchmark_name=results[0].benchmark_name,
            metric_type=results[0].metric_type,
            baseline_mean=mean_val,
            baseline_std=std_val,
            confidence_interval=confidence_interval,
            sample_size=len(all_values),
            created_at=datetime.now()
        )
        
    @staticmethod
    def detect_regression(current_result: PerformanceResult,
                         baseline: PerformanceBaseline,
                         significance_threshold: float = 0.05) -> Optional[RegressionAlert]:
        """Detect performance regression using statistical tests."""
        
        # Perform t-test to check if current performance differs significantly
        t_stat, p_value = stats.ttest_1samp(
            current_result.values, 
            baseline.baseline_mean
        )
        
        # Calculate regression percentage
        regression_pct = ((current_result.mean - baseline.baseline_mean) / 
                         baseline.baseline_mean) * 100
        
        # Determine severity based on regression percentage and statistical significance
        if p_value > significance_threshold:
            return None  # No significant change
            
        severity = AlertSeverity.INFO
        if abs(regression_pct) > 10:
            severity = AlertSeverity.WARNING
        if abs(regression_pct) > 25:
            severity = AlertSeverity.CRITICAL
            
        message = f"Performance {'regression' if regression_pct > 0 else 'improvement'} detected"
        if current_result.metric_type in [PerformanceMetric.LATENCY, PerformanceMetric.ERROR_RATE]:
            # For latency and error rate, increases are bad
            if regression_pct > 5:
                message = f"Performance regression: {regression_pct:.1f}% increase in {current_result.metric_type.value}"
        else:
            # For throughput, decreases are bad  
            if regression_pct < -5:
                message = f"Performance regression: {abs(regression_pct):.1f}% decrease in {current_result.metric_type.value}"
                
        return RegressionAlert(
            benchmark_name=current_result.benchmark_name,
            severity=severity,
            message=message,
            current_value=current_result.mean,
            baseline_value=baseline.baseline_mean,
            regression_percentage=regression_pct,
            timestamp=datetime.now(),
            statistical_significance=p_value
        )
        
    @staticmethod
    def detect_trend(historical_data: List[Tuple[datetime, float]],
                    trend_window: int = 10) -> Dict[str, Any]:
        """Detect performance trends using linear regression."""
        if len(historical_data) < trend_window:
            return {'trend': 'insufficient_data'}
            
        # Use most recent data points
        recent_data = historical_data[-trend_window:]
        x_values = np.array([i for i in range(len(recent_data))])
        y_values = np.array([point[1] for point in recent_data])
        
        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_values, y_values)
        
        # Determine trend direction and significance
        trend_direction = 'increasing' if slope > 0 else 'decreasing'
        trend_strength = abs(r_value)
        
        return {
            'trend': trend_direction,
            'strength': trend_strength,
            'slope': slope,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'prediction_next': intercept + slope * len(recent_data)
        }

class PerformanceMonitor:
    """Real-time performance monitoring during tests."""
    
    def __init__(self, sampling_interval: float = 0.1):
        self.sampling_interval = sampling_interval
        self.monitoring = False
        self.data = []
        self.monitor_thread = None
        
    def start_monitoring(self, pid: Optional[int] = None):
        """Start performance monitoring."""
        self.monitoring = True
        self.data = []
        self.pid = pid or os.getpid()
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
        
    def stop_monitoring(self) -> Dict[str, List[float]]:
        """Stop monitoring and return collected data."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
            
        if not self.data:
            return {}
            
        # Aggregate data
        cpu_data = [d['cpu_percent'] for d in self.data]
        memory_data = [d['memory_mb'] for d in self.data]
        
        return {
            'cpu_percent': cpu_data,
            'memory_mb': memory_data,
            'timestamps': [d['timestamp'] for d in self.data]
        }
        
    def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            process = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            return
            
        while self.monitoring:
            try:
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                
                self.data.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_info.rss / (1024 * 1024)
                })
                
                time.sleep(self.sampling_interval)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                continue

class PerformanceTester:
    """Main performance testing engine."""
    
    def __init__(self, database_path: Path):
        self.database = PerformanceDatabase(database_path)
        self.analyzer = StatisticalAnalyzer()
        self.monitor = PerformanceMonitor()
        
    def run_benchmark(self, benchmark: PerformanceBenchmark) -> PerformanceResult:
        """Run a single performance benchmark."""
        print(f"Running benchmark: {benchmark.name}")
        
        # Get system information
        system_info = self._get_system_info()
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Warmup iterations
        print(f"  Warming up ({benchmark.warmup_iterations} iterations)...")
        for _ in range(benchmark.warmup_iterations):
            try:
                benchmark.test_function(**benchmark.parameters)
            except Exception as e:
                print(f"  Warmup error: {e}")
                
        # Actual benchmark iterations
        print(f"  Running benchmark ({benchmark.iterations} iterations)...")
        results = []
        
        for i in range(benchmark.iterations):
            start_time = time.perf_counter()
            try:
                benchmark.test_function(**benchmark.parameters)
                end_time = time.perf_counter()
                
                # Calculate metric value based on type
                if benchmark.metric_type == PerformanceMetric.LATENCY:
                    value = (end_time - start_time) * 1000  # Convert to milliseconds
                elif benchmark.metric_type == PerformanceMetric.THROUGHPUT:
                    # Assume throughput is operations per second
                    value = 1.0 / (end_time - start_time)
                else:
                    value = end_time - start_time
                    
                results.append(value)
                
            except Exception as e:
                print(f"  Benchmark error (iteration {i+1}): {e}")
                continue
                
            if (i + 1) % (benchmark.iterations // 10) == 0:
                progress = ((i + 1) / benchmark.iterations) * 100
                print(f"  Progress: {progress:.1f}%")
                
        # Stop monitoring
        monitoring_data = self.monitor.stop_monitoring()
        
        if not results:
            raise RuntimeError(f"Benchmark {benchmark.name} produced no valid results")
            
        # Create result object
        result = PerformanceResult(
            benchmark_name=benchmark.name,
            metric_type=benchmark.metric_type,
            values=results,
            timestamp=datetime.now(),
            system_info={**system_info, **monitoring_data}
        )
        
        # Store in database
        self.database.store_result(result)
        
        return result
        
    def check_regression(self, result: PerformanceResult) -> Optional[RegressionAlert]:
        """Check for performance regression."""
        baseline = self.database.get_baseline(result.benchmark_name, result.metric_type)
        
        if baseline is None:
            print(f"  No baseline found for {result.benchmark_name}, creating baseline...")
            # Create baseline from current result
            baseline = self.analyzer.calculate_baseline([result])
            self.database.store_baseline(baseline)
            return None
            
        # Check for regression
        alert = self.analyzer.detect_regression(result, baseline)
        
        if alert:
            self.database.store_alert(alert)
            print(f"  ALERT: {alert.message}")
            
        return alert
        
    def update_baseline(self, benchmark_name: str, metric_type: PerformanceMetric,
                       days_of_data: int = 7):
        """Update baseline using recent historical data."""
        historical_data = self.database.get_historical_results(benchmark_name, days_of_data)
        
        if len(historical_data) < 10:  # Minimum data points for reliable baseline
            print(f"Insufficient data for baseline update ({len(historical_data)} points)")
            return
            
        # Get results from database and create baseline
        # This is a simplified version - in practice, you'd retrieve full PerformanceResult objects
        print(f"Updating baseline for {benchmark_name} using {len(historical_data)} data points")
        
    def generate_trend_analysis(self, benchmark_name: str, days: int = 30) -> Dict[str, Any]:
        """Generate trend analysis for a benchmark."""
        historical_data = self.database.get_historical_results(benchmark_name, days)
        
        if not historical_data:
            return {'error': 'No historical data available'}
            
        trend_analysis = self.analyzer.detect_trend(historical_data)
        
        return {
            'benchmark_name': benchmark_name,
            'analysis_period_days': days,
            'data_points': len(historical_data),
            'trend_analysis': trend_analysis,
            'recent_performance': historical_data[-5:] if len(historical_data) >= 5 else historical_data
        }
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get current system information."""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None,
                'python_version': sys.version,
                'hostname': socket.gethostname()
            }
        except Exception as e:
            print(f"Error getting system info: {e}")
            return {}

# Example I2C driver performance benchmarks

def mock_i2c_read_benchmark(num_bytes: int = 32, address: int = 0x48):
    """Mock I2C read benchmark."""
    # Simulate I2C read operation
    time.sleep(0.001 + (num_bytes * 0.0001))  # Base latency + byte transfer time
    return b'x00' * num_bytes

def mock_i2c_write_benchmark(data: bytes = b'\x00' * 16, address: int = 0x48):
    """Mock I2C write benchmark."""
    # Simulate I2C write operation
    time.sleep(0.0015 + (len(data) * 0.0001))  # Base latency + byte transfer time
    return True

def create_i2c_performance_suite() -> List[PerformanceBenchmark]:
    """Create I2C driver performance benchmark suite."""
    return [
        PerformanceBenchmark(
            name="I2C Single Byte Read Latency",
            test_function=mock_i2c_read_benchmark,
            metric_type=PerformanceMetric.LATENCY,
            iterations=1000,
            parameters={'num_bytes': 1}
        ),
        PerformanceBenchmark(
            name="I2C Block Read Throughput",
            test_function=mock_i2c_read_benchmark,
            metric_type=PerformanceMetric.THROUGHPUT,
            iterations=500,
            parameters={'num_bytes': 32}
        ),
        PerformanceBenchmark(
            name="I2C Write Latency",
            test_function=mock_i2c_write_benchmark,
            metric_type=PerformanceMetric.LATENCY,
            iterations=1000,
            parameters={'data': b'\x55' * 4}
        ),
        PerformanceBenchmark(
            name="I2C Transaction Rate",
            test_function=lambda: [mock_i2c_read_benchmark(1) for _ in range(10)],
            metric_type=PerformanceMetric.I2C_TRANSACTION_RATE,
            iterations=100
        )
    ]

if __name__ == "__main__":
    import os
    import sys
    import socket
    
    # Run performance tests
    tester = PerformanceTester(Path("performance.db"))
    benchmarks = create_i2c_performance_suite()
    
    results = []
    alerts = []
    
    for benchmark in benchmarks:
        result = tester.run_benchmark(benchmark)
        results.append(result)
        
        alert = tester.check_regression(result)
        if alert:
            alerts.append(alert)
            
        # Generate trend analysis
        trend_analysis = tester.generate_trend_analysis(benchmark.name)
        print(f"\nTrend Analysis for {benchmark.name}:")
        print(f"  Trend: {trend_analysis.get('trend_analysis', {}).get('trend', 'N/A')}")
        
    print(f"\nPerformance Testing Complete")
    print(f"Benchmarks run: {len(results)}")
    print(f"Regression alerts: {len(alerts)}")
    
    if alerts:
        print("\nAlerts:")
        for alert in alerts:
            print(f"  {alert.severity.value.upper()}: {alert.message}")