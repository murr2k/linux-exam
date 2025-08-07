#!/usr/bin/env python3
"""
Performance Analytics System

Creates performance regression detection, statistical analysis of test runs,
resource usage tracking, and performance trend reports.
"""

import json
import sqlite3
import statistics
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging
import math
from scipy import stats
from scipy.stats import mannwhitneyu, ttest_ind
import warnings
warnings.filterwarnings('ignore')


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single test execution."""
    test_name: str
    execution_time: float
    cpu_usage: float
    memory_usage: float
    disk_io: float
    network_io: float
    timestamp: datetime
    baseline_comparison: Optional[float] = None


@dataclass
class RegressionResult:
    """Performance regression detection result."""
    test_name: str
    regression_detected: bool
    confidence_level: float
    current_mean: float
    baseline_mean: float
    regression_factor: float
    statistical_significance: float
    recommendation: str
    trend_analysis: Dict[str, Any]


@dataclass
class ResourceTrend:
    """Resource usage trend analysis."""
    resource_type: str
    trend_direction: str  # INCREASING, DECREASING, STABLE
    trend_strength: float  # 0-1
    current_average: float
    historical_average: float
    peak_usage: float
    projected_usage: Optional[float] = None


class PerformanceAnalyzer:
    """Analyzes test performance and detects regressions."""
    
    def __init__(self, db_path: str = "test_analytics.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()
        self._init_performance_database()
        
        # Statistical thresholds
        self.regression_thresholds = {
            'minor': 1.1,      # 10% increase
            'moderate': 1.25,   # 25% increase
            'major': 1.5,      # 50% increase
            'critical': 2.0     # 100% increase
        }
        
        # Confidence levels for statistical tests
        self.confidence_levels = [0.95, 0.99, 0.999]
        
        # Trend analysis window
        self.trend_window_days = 30
        self.baseline_window_days = 90
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('PerformanceAnalyzer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_performance_database(self):
        """Initialize database tables for performance metrics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    cpu_usage REAL NOT NULL,
                    memory_usage REAL NOT NULL,
                    disk_io REAL NOT NULL,
                    network_io REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    baseline_comparison REAL,
                    system_load REAL,
                    concurrent_tests INTEGER DEFAULT 1
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_baselines (
                    test_name TEXT PRIMARY KEY,
                    baseline_execution_time REAL NOT NULL,
                    baseline_cpu_usage REAL NOT NULL,
                    baseline_memory_usage REAL NOT NULL,
                    baseline_disk_io REAL NOT NULL,
                    baseline_network_io REAL NOT NULL,
                    sample_size INTEGER NOT NULL,
                    confidence_interval_lower REAL NOT NULL,
                    confidence_interval_upper REAL NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS regression_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    alert_level TEXT NOT NULL,
                    regression_factor REAL NOT NULL,
                    confidence_level REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_notes TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    trend_direction TEXT NOT NULL,
                    trend_strength REAL NOT NULL,
                    current_average REAL NOT NULL,
                    historical_average REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    forecast_days INTEGER,
                    projected_value REAL
                )
            ''')
    
    def record_performance_metrics(self, test_name: str, execution_time: float,
                                 cpu_usage: float = 0.0, memory_usage: float = 0.0,
                                 disk_io: float = 0.0, network_io: float = 0.0,
                                 system_load: float = 0.0, concurrent_tests: int = 1):
        """Record performance metrics for a test execution."""
        
        # Calculate baseline comparison if baseline exists
        baseline_comparison = self._calculate_baseline_comparison(
            test_name, execution_time, cpu_usage, memory_usage, disk_io, network_io
        )
        
        # Store metrics
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO performance_metrics 
                (test_name, execution_time, cpu_usage, memory_usage, disk_io, 
                 network_io, timestamp, baseline_comparison, system_load, concurrent_tests)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_name, execution_time, cpu_usage, memory_usage, disk_io,
                network_io, datetime.now().isoformat(), baseline_comparison,
                system_load, concurrent_tests
            ))
        
        self.logger.info(f"Recorded performance metrics for {test_name}: "
                        f"Time={execution_time:.3f}s, CPU={cpu_usage:.1f}%, "
                        f"Memory={memory_usage:.1f}MB")
        
        # Check for regressions
        regression = self.detect_performance_regression(test_name)
        if regression.regression_detected:
            self._create_regression_alert(test_name, regression)
    
    def _calculate_baseline_comparison(self, test_name: str, execution_time: float,
                                     cpu_usage: float, memory_usage: float,
                                     disk_io: float, network_io: float) -> Optional[float]:
        """Calculate comparison to baseline performance."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT baseline_execution_time, baseline_cpu_usage, 
                       baseline_memory_usage, baseline_disk_io, baseline_network_io
                FROM performance_baselines WHERE test_name = ?
            ''', (test_name,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            baseline_exec, baseline_cpu, baseline_mem, baseline_disk, baseline_net = result
            
            # Calculate weighted comparison score
            weights = {
                'execution_time': 0.4,
                'cpu_usage': 0.2,
                'memory_usage': 0.2,
                'disk_io': 0.1,
                'network_io': 0.1
            }
            
            comparisons = {
                'execution_time': execution_time / max(baseline_exec, 0.001),
                'cpu_usage': cpu_usage / max(baseline_cpu, 0.001),
                'memory_usage': memory_usage / max(baseline_mem, 0.001),
                'disk_io': disk_io / max(baseline_disk, 0.001),
                'network_io': network_io / max(baseline_net, 0.001)
            }
            
            weighted_comparison = sum(
                comparisons[metric] * weights[metric]
                for metric in weights.keys()
            )
            
            return weighted_comparison
    
    def establish_baseline(self, test_name: str, confidence_level: float = 0.95):
        """Establish performance baseline for a test."""
        # Get recent performance data
        cutoff_date = (datetime.now() - timedelta(days=self.baseline_window_days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT execution_time, cpu_usage, memory_usage, disk_io, network_io
                FROM performance_metrics 
                WHERE test_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (test_name, cutoff_date))
            
            data = cursor.fetchall()
        
        if len(data) < 10:
            self.logger.warning(f"Insufficient data for baseline establishment: {len(data)} samples")
            return False
        
        # Calculate statistics for each metric
        execution_times = [d[0] for d in data]
        cpu_usages = [d[1] for d in data]
        memory_usages = [d[2] for d in data]
        disk_ios = [d[3] for d in data]
        network_ios = [d[4] for d in data]
        
        # Calculate means and confidence intervals
        exec_mean = statistics.mean(execution_times)
        exec_ci = self._calculate_confidence_interval(execution_times, confidence_level)
        
        cpu_mean = statistics.mean(cpu_usages)
        memory_mean = statistics.mean(memory_usages)
        disk_mean = statistics.mean(disk_ios)
        network_mean = statistics.mean(network_ios)
        
        # Store baseline
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO performance_baselines 
                (test_name, baseline_execution_time, baseline_cpu_usage, 
                 baseline_memory_usage, baseline_disk_io, baseline_network_io,
                 sample_size, confidence_interval_lower, confidence_interval_upper, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_name, exec_mean, cpu_mean, memory_mean, disk_mean, network_mean,
                len(data), exec_ci[0], exec_ci[1], datetime.now().isoformat()
            ))
        
        self.logger.info(f"Established baseline for {test_name}: {exec_mean:.3f}s "
                        f"(CI: {exec_ci[0]:.3f}-{exec_ci[1]:.3f})")
        return True
    
    def _calculate_confidence_interval(self, data: List[float], 
                                     confidence_level: float) -> Tuple[float, float]:
        """Calculate confidence interval for data."""
        if len(data) < 2:
            return (0.0, 0.0)
        
        mean = statistics.mean(data)
        std_err = statistics.stdev(data) / math.sqrt(len(data))
        
        # Use t-distribution for small samples
        alpha = 1 - confidence_level
        df = len(data) - 1
        t_value = stats.t.ppf(1 - alpha/2, df)
        
        margin_error = t_value * std_err
        
        return (mean - margin_error, mean + margin_error)
    
    def detect_performance_regression(self, test_name: str, 
                                    recent_days: int = 7) -> RegressionResult:
        """Detect performance regression using statistical analysis."""
        
        # Get baseline data
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT baseline_execution_time, confidence_interval_lower, 
                       confidence_interval_upper, sample_size
                FROM performance_baselines WHERE test_name = ?
            ''', (test_name,))
            
            baseline_result = cursor.fetchone()
            
            if not baseline_result:
                return RegressionResult(
                    test_name=test_name,
                    regression_detected=False,
                    confidence_level=0.0,
                    current_mean=0.0,
                    baseline_mean=0.0,
                    regression_factor=1.0,
                    statistical_significance=0.0,
                    recommendation="No baseline available",
                    trend_analysis={}
                )
            
            baseline_mean, ci_lower, ci_upper, baseline_sample_size = baseline_result
            
            # Get recent performance data
            cutoff_date = (datetime.now() - timedelta(days=recent_days)).isoformat()
            cursor = conn.execute('''
                SELECT execution_time FROM performance_metrics 
                WHERE test_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (test_name, cutoff_date))
            
            recent_data = [row[0] for row in cursor.fetchall()]
        
        if len(recent_data) < 5:
            return RegressionResult(
                test_name=test_name,
                regression_detected=False,
                confidence_level=0.0,
                current_mean=0.0,
                baseline_mean=baseline_mean,
                regression_factor=1.0,
                statistical_significance=0.0,
                recommendation="Insufficient recent data",
                trend_analysis={}
            )
        
        current_mean = statistics.mean(recent_data)
        regression_factor = current_mean / baseline_mean
        
        # Perform statistical tests
        statistical_significance = self._perform_regression_test(
            recent_data, baseline_mean, ci_lower, ci_upper
        )
        
        # Determine if regression is significant
        regression_detected = (
            regression_factor > self.regression_thresholds['minor'] and
            statistical_significance > 0.95
        )
        
        # Get trend analysis
        trend_analysis = self._analyze_performance_trend(test_name, recent_days * 2)
        
        # Generate recommendation
        recommendation = self._generate_regression_recommendation(
            regression_factor, statistical_significance, trend_analysis
        )
        
        return RegressionResult(
            test_name=test_name,
            regression_detected=regression_detected,
            confidence_level=statistical_significance,
            current_mean=current_mean,
            baseline_mean=baseline_mean,
            regression_factor=regression_factor,
            statistical_significance=statistical_significance,
            recommendation=recommendation,
            trend_analysis=trend_analysis
        )
    
    def _perform_regression_test(self, recent_data: List[float], baseline_mean: float,
                               ci_lower: float, ci_upper: float) -> float:
        """Perform statistical test for regression detection."""
        current_mean = statistics.mean(recent_data)
        
        # Simple threshold test using confidence intervals
        if current_mean > ci_upper:
            # Current performance is outside baseline confidence interval
            # Calculate how far outside (as confidence level)
            baseline_range = ci_upper - ci_lower
            excess = current_mean - ci_upper
            
            # Convert excess to confidence level (simplified)
            confidence = min(0.95 + (excess / baseline_range) * 0.04, 0.999)
            return confidence
        
        return 0.0
    
    def _analyze_performance_trend(self, test_name: str, 
                                 analysis_days: int) -> Dict[str, Any]:
        """Analyze performance trend over specified period."""
        cutoff_date = (datetime.now() - timedelta(days=analysis_days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT execution_time, timestamp FROM performance_metrics 
                WHERE test_name = ? AND timestamp > ?
                ORDER BY timestamp ASC
            ''', (test_name, cutoff_date))
            
            data = cursor.fetchall()
        
        if len(data) < 10:
            return {'trend': 'insufficient_data', 'correlation': 0.0}
        
        # Create time series
        times = [datetime.fromisoformat(d[1]).timestamp() for d in data]
        values = [d[0] for d in data]
        
        # Normalize time to start from 0
        start_time = min(times)
        times = [(t - start_time) / 3600 for t in times]  # Convert to hours
        
        # Calculate correlation with time (trend strength)
        correlation, p_value = stats.pearsonr(times, values)
        
        # Linear regression for trend line
        slope, intercept, r_value, p_value, std_err = stats.linregress(times, values)
        
        # Determine trend direction
        if abs(correlation) < 0.3:
            trend_direction = 'stable'
        elif correlation > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'
        
        return {
            'trend': trend_direction,
            'correlation': correlation,
            'slope': slope,
            'r_squared': r_value**2,
            'p_value': p_value,
            'trend_strength': abs(correlation)
        }
    
    def _generate_regression_recommendation(self, regression_factor: float,
                                          statistical_significance: float,
                                          trend_analysis: Dict[str, Any]) -> str:
        """Generate recommendation based on regression analysis."""
        if not trend_analysis:
            return "Unable to analyze trend - insufficient data"
        
        if regression_factor >= self.regression_thresholds['critical']:
            return (f"CRITICAL: Performance degraded by {(regression_factor-1)*100:.1f}%. "
                   f"Immediate investigation required. Consider reverting recent changes.")
        
        elif regression_factor >= self.regression_thresholds['major']:
            return (f"MAJOR: Significant performance regression ({(regression_factor-1)*100:.1f}%). "
                   f"Review recent commits and system changes.")
        
        elif regression_factor >= self.regression_thresholds['moderate']:
            if trend_analysis['trend'] == 'increasing':
                return (f"MODERATE: Performance declining trend detected. "
                       f"Monitor closely and consider optimization.")
            else:
                return (f"MODERATE: Performance regression detected but may be temporary. "
                       f"Continue monitoring.")
        
        elif regression_factor >= self.regression_thresholds['minor']:
            if statistical_significance > 0.99:
                return (f"MINOR: Small but statistically significant regression. "
                       f"Consider investigating if trend continues.")
            else:
                return (f"MINOR: Slight performance change detected. "
                       f"May be within normal variance.")
        
        else:
            return "Performance within acceptable range."
    
    def _create_regression_alert(self, test_name: str, regression: RegressionResult):
        """Create regression alert in database."""
        severity_map = {
            (2.0, float('inf')): 'CRITICAL',
            (1.5, 2.0): 'MAJOR',
            (1.25, 1.5): 'MODERATE',
            (1.1, 1.25): 'MINOR'
        }
        
        alert_level = 'MINOR'
        for (low, high), level in severity_map.items():
            if low <= regression.regression_factor < high:
                alert_level = level
                break
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO regression_alerts 
                (test_name, alert_level, regression_factor, confidence_level, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                test_name, alert_level, regression.regression_factor,
                regression.confidence_level, datetime.now().isoformat()
            ))
        
        self.logger.warning(f"{alert_level} regression alert created for {test_name}: "
                           f"{regression.regression_factor:.2f}x slower")
    
    def analyze_resource_trends(self, days: int = 30) -> List[ResourceTrend]:
        """Analyze resource usage trends across all tests."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT test_name, cpu_usage, memory_usage, disk_io, network_io, timestamp
                FROM performance_metrics 
                WHERE timestamp > ?
                ORDER BY test_name, timestamp ASC
            ''', (cutoff_date,))
            
            data = cursor.fetchall()
        
        # Group by test name
        test_data = defaultdict(list)
        for row in data:
            test_data[row[0]].append(row[1:])  # Exclude test_name
        
        trends = []
        resource_types = ['cpu_usage', 'memory_usage', 'disk_io', 'network_io']
        
        for test_name, test_metrics in test_data.items():
            if len(test_metrics) < 10:
                continue
            
            for i, resource_type in enumerate(resource_types):
                values = [row[i] for row in test_metrics]
                timestamps = [datetime.fromisoformat(row[4]).timestamp() for row in test_metrics]
                
                # Calculate trend
                correlation, _ = stats.pearsonr(
                    [(t - min(timestamps)) / 3600 for t in timestamps], 
                    values
                )
                
                if abs(correlation) < 0.3:
                    trend_direction = 'STABLE'
                elif correlation > 0:
                    trend_direction = 'INCREASING'
                else:
                    trend_direction = 'DECREASING'
                
                current_avg = statistics.mean(values[-10:])  # Last 10 measurements
                historical_avg = statistics.mean(values)
                peak_usage = max(values)
                
                # Simple linear projection
                projected_usage = None
                if abs(correlation) > 0.5:
                    slope = (values[-1] - values[0]) / len(values)
                    projected_usage = values[-1] + slope * 10  # 10 periods ahead
                
                trend = ResourceTrend(
                    resource_type=f"{test_name}_{resource_type}",
                    trend_direction=trend_direction,
                    trend_strength=abs(correlation),
                    current_average=current_avg,
                    historical_average=historical_avg,
                    peak_usage=peak_usage,
                    projected_usage=projected_usage
                )
                
                trends.append(trend)
        
        return trends
    
    def generate_performance_report(self, output_path: str, days: int = 30):
        """Generate comprehensive performance report."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all tests with performance data
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT DISTINCT test_name FROM performance_metrics 
                WHERE timestamp > ?
            ''', (cutoff_date.isoformat(),))
            
            test_names = [row[0] for row in cursor.fetchall()]
        
        # Collect regression analysis for each test
        regression_results = {}
        for test_name in test_names:
            regression = self.detect_performance_regression(test_name)
            regression_results[test_name] = asdict(regression)
        
        # Get resource trends
        resource_trends = self.analyze_resource_trends(days)
        trend_data = [asdict(trend) for trend in resource_trends]
        
        # Get active alerts
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT test_name, alert_level, regression_factor, timestamp
                FROM regression_alerts 
                WHERE resolved = FALSE AND timestamp > ?
                ORDER BY regression_factor DESC
            ''', (cutoff_date.isoformat(),))
            
            active_alerts = [{
                'test_name': row[0],
                'alert_level': row[1],
                'regression_factor': row[2],
                'timestamp': row[3]
            } for row in cursor.fetchall()]
        
        # Generate summary statistics
        all_factors = [r['regression_factor'] for r in regression_results.values() 
                      if r['regression_factor'] > 0]
        
        summary = {
            'total_tests_analyzed': len(test_names),
            'tests_with_regression': len([r for r in regression_results.values() 
                                        if r['regression_detected']]),
            'active_alerts': len(active_alerts),
            'average_regression_factor': statistics.mean(all_factors) if all_factors else 1.0,
            'worst_regression': max(all_factors) if all_factors else 1.0
        }
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_period_days': days,
            'summary': summary,
            'regression_analysis': regression_results,
            'resource_trends': trend_data,
            'active_alerts': active_alerts
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Performance report generated: {output_path}")
    
    def get_performance_statistics(self, test_name: str, 
                                 days: int = 30) -> Dict[str, Any]:
        """Get detailed performance statistics for a test."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT execution_time, cpu_usage, memory_usage, disk_io, 
                       network_io, system_load, concurrent_tests
                FROM performance_metrics 
                WHERE test_name = ? AND timestamp > ?
                ORDER BY timestamp ASC
            ''', (test_name, cutoff_date))
            
            data = cursor.fetchall()
        
        if not data:
            return {'error': 'No performance data available'}
        
        # Extract metrics
        exec_times = [d[0] for d in data]
        cpu_usage = [d[1] for d in data]
        memory_usage = [d[2] for d in data]
        disk_io = [d[3] for d in data]
        network_io = [d[4] for d in data]
        
        return {
            'execution_time': {
                'mean': statistics.mean(exec_times),
                'median': statistics.median(exec_times),
                'std_dev': statistics.stdev(exec_times) if len(exec_times) > 1 else 0,
                'min': min(exec_times),
                'max': max(exec_times),
                'p95': np.percentile(exec_times, 95),
                'p99': np.percentile(exec_times, 99)
            },
            'resource_usage': {
                'cpu': {
                    'mean': statistics.mean(cpu_usage),
                    'max': max(cpu_usage),
                    'std_dev': statistics.stdev(cpu_usage) if len(cpu_usage) > 1 else 0
                },
                'memory': {
                    'mean': statistics.mean(memory_usage),
                    'max': max(memory_usage),
                    'std_dev': statistics.stdev(memory_usage) if len(memory_usage) > 1 else 0
                },
                'disk_io': {
                    'mean': statistics.mean(disk_io),
                    'max': max(disk_io)
                },
                'network_io': {
                    'mean': statistics.mean(network_io),
                    'max': max(network_io)
                }
            },
            'sample_size': len(data),
            'analysis_period_days': days
        }


if __name__ == "__main__":
    # Example usage
    analyzer = PerformanceAnalyzer()
    
    # Record some performance metrics
    analyzer.record_performance_metrics(
        test_name="test_mpu6050_performance",
        execution_time=1.25,
        cpu_usage=45.2,
        memory_usage=128.5,
        disk_io=1024.0,
        network_io=0.0
    )
    
    # Establish baseline
    analyzer.establish_baseline("test_mpu6050_performance")
    
    # Check for regression
    regression = analyzer.detect_performance_regression("test_mpu6050_performance")
    print(f"Regression detected: {regression.regression_detected}")
    
    # Get statistics
    stats = analyzer.get_performance_statistics("test_mpu6050_performance")
    print(f"Performance stats: {stats}")
    
    # Generate report
    analyzer.generate_performance_report("performance_report.json")