#!/usr/bin/env python3
"""
Test Metrics Collection System

This module implements comprehensive test execution time tracking,
reliability metrics, coverage trend analysis, and test maintenance burden tracking.
"""

import json
import time
import sqlite3
import threading
import subprocess
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
import logging


@dataclass
class TestExecution:
    """Represents a single test execution record."""
    test_id: str
    test_name: str
    test_category: str
    execution_time: float
    status: str  # PASSED, FAILED, SKIPPED, TIMEOUT
    timestamp: datetime
    resource_usage: Dict[str, float]
    error_message: Optional[str] = None
    coverage_data: Optional[Dict[str, float]] = None
    maintenance_score: float = 0.0


@dataclass
class TestMetrics:
    """Aggregated test metrics for analytics."""
    test_name: str
    total_executions: int
    success_rate: float
    avg_execution_time: float
    p95_execution_time: float
    p99_execution_time: float
    trend_direction: str  # IMPROVING, DEGRADING, STABLE
    maintenance_burden: float
    last_execution: datetime
    failure_patterns: List[str]


class TestMetricsCollector:
    """Collects and analyzes test execution metrics."""
    
    def __init__(self, db_path: str = "test_analytics.db"):
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self.active_tests: Dict[str, TestExecution] = {}
        self.coverage_history: deque = deque(maxlen=1000)
        self.performance_baselines: Dict[str, float] = {}
        
        # Initialize logging
        self.logger = self._setup_logging()
        
        # Initialize database
        self._init_database()
        
        # Load performance baselines
        self._load_baselines()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('TestMetricsCollector')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_database(self):
        """Initialize SQLite database for metrics storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS test_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    test_category TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resource_usage TEXT,
                    error_message TEXT,
                    coverage_data TEXT,
                    maintenance_score REAL DEFAULT 0.0
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS coverage_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    function_coverage REAL NOT NULL,
                    branch_coverage REAL NOT NULL,
                    line_coverage REAL NOT NULL,
                    test_suite TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_baselines (
                    test_name TEXT PRIMARY KEY,
                    baseline_time REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_name ON test_executions(test_name);
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON test_executions(timestamp);
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status ON test_executions(status);
            ''')
    
    def _load_baselines(self):
        """Load performance baselines from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT test_name, baseline_time FROM performance_baselines'
            )
            for test_name, baseline_time in cursor.fetchall():
                self.performance_baselines[test_name] = baseline_time
    
    def start_test_execution(self, test_name: str, test_category: str) -> str:
        """Start tracking a test execution."""
        test_id = f"{test_name}_{int(time.time() * 1000000)}"
        
        execution = TestExecution(
            test_id=test_id,
            test_name=test_name,
            test_category=test_category,
            execution_time=0.0,
            status="RUNNING",
            timestamp=datetime.now(),
            resource_usage=self._get_current_resource_usage()
        )
        
        self.active_tests[test_id] = execution
        self.logger.info(f"Started tracking test: {test_name} (ID: {test_id})")
        
        return test_id
    
    def end_test_execution(self, test_id: str, status: str, 
                          error_message: Optional[str] = None,
                          coverage_data: Optional[Dict[str, float]] = None):
        """End tracking a test execution."""
        if test_id not in self.active_tests:
            self.logger.warning(f"Unknown test ID: {test_id}")
            return
        
        execution = self.active_tests[test_id]
        execution.execution_time = (datetime.now() - execution.timestamp).total_seconds()
        execution.status = status
        execution.error_message = error_message
        execution.coverage_data = coverage_data
        execution.maintenance_score = self._calculate_maintenance_score(execution)
        
        # Store in database
        self._store_execution(execution)
        
        # Remove from active tests
        del self.active_tests[test_id]
        
        self.logger.info(f"Completed test: {execution.test_name} - "
                        f"Status: {status}, Time: {execution.execution_time:.3f}s")
    
    def _get_current_resource_usage(self) -> Dict[str, float]:
        """Get current system resource usage."""
        try:
            # Get memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                mem_total = int([line for line in meminfo.split('\n') 
                               if 'MemTotal' in line][0].split()[1])
                mem_available = int([line for line in meminfo.split('\n') 
                                   if 'MemAvailable' in line][0].split()[1])
                memory_usage = (mem_total - mem_available) / mem_total * 100
            
            # Get CPU load
            with open('/proc/loadavg', 'r') as f:
                load_avg = float(f.read().split()[0])
            
            return {
                'memory_percent': memory_usage,
                'cpu_load': load_avg,
                'timestamp': time.time()
            }
        except Exception as e:
            self.logger.warning(f"Could not get resource usage: {e}")
            return {'memory_percent': 0.0, 'cpu_load': 0.0, 'timestamp': time.time()}
    
    def _calculate_maintenance_score(self, execution: TestExecution) -> float:
        """Calculate test maintenance burden score."""
        score = 0.0
        
        # Factor 1: Test complexity (based on execution time)
        if execution.execution_time > 10.0:
            score += 0.3
        elif execution.execution_time > 5.0:
            score += 0.2
        elif execution.execution_time > 1.0:
            score += 0.1
        
        # Factor 2: Failure rate
        recent_failures = self._get_recent_failure_rate(execution.test_name)
        score += recent_failures * 0.4
        
        # Factor 3: Resource usage
        memory_usage = execution.resource_usage.get('memory_percent', 0)
        if memory_usage > 80:
            score += 0.2
        elif memory_usage > 60:
            score += 0.1
        
        # Factor 4: Error complexity
        if execution.error_message and len(execution.error_message) > 500:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_recent_failure_rate(self, test_name: str, days: int = 7) -> float:
        """Get failure rate for a test in recent days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failures
                FROM test_executions 
                WHERE test_name = ? AND timestamp > ?
            ''', (test_name, cutoff_date.isoformat()))
            
            result = cursor.fetchone()
            if result[0] == 0:
                return 0.0
            
            return result[1] / result[0]
    
    def _store_execution(self, execution: TestExecution):
        """Store test execution in database."""
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO test_executions 
                    (test_id, test_name, test_category, execution_time, status, 
                     timestamp, resource_usage, error_message, coverage_data, maintenance_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    execution.test_id,
                    execution.test_name,
                    execution.test_category,
                    execution.execution_time,
                    execution.status,
                    execution.timestamp.isoformat(),
                    json.dumps(execution.resource_usage),
                    execution.error_message,
                    json.dumps(execution.coverage_data) if execution.coverage_data else None,
                    execution.maintenance_score
                ))
    
    def record_coverage_data(self, function_cov: float, branch_cov: float, 
                           line_cov: float, test_suite: str):
        """Record coverage trend data."""
        timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO coverage_trends 
                (timestamp, function_coverage, branch_coverage, line_coverage, test_suite)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp.isoformat(), function_cov, branch_cov, line_cov, test_suite))
        
        # Add to in-memory history
        self.coverage_history.append({
            'timestamp': timestamp,
            'function_coverage': function_cov,
            'branch_coverage': branch_cov,
            'line_coverage': line_cov,
            'test_suite': test_suite
        })
        
        self.logger.info(f"Recorded coverage: F:{function_cov:.1f}% B:{branch_cov:.1f}% L:{line_cov:.1f}%")
    
    def get_test_metrics(self, test_name: str, days: int = 30) -> Optional[TestMetrics]:
        """Get aggregated metrics for a specific test."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT execution_time, status, timestamp, maintenance_score, error_message
                FROM test_executions 
                WHERE test_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (test_name, cutoff_date.isoformat()))
            
            records = cursor.fetchall()
            
            if not records:
                return None
            
            execution_times = [r[0] for r in records]
            statuses = [r[1] for r in records]
            maintenance_scores = [r[3] for r in records if r[3] is not None]
            error_messages = [r[4] for r in records if r[4] is not None]
            
            success_rate = sum(1 for s in statuses if s == 'PASSED') / len(statuses)
            
            # Analyze trend
            if len(execution_times) >= 5:
                recent_times = execution_times[:5]
                older_times = execution_times[5:10] if len(execution_times) >= 10 else execution_times[5:]
                
                if older_times:
                    recent_avg = statistics.mean(recent_times)
                    older_avg = statistics.mean(older_times)
                    
                    if recent_avg < older_avg * 0.95:
                        trend = "IMPROVING"
                    elif recent_avg > older_avg * 1.05:
                        trend = "DEGRADING"
                    else:
                        trend = "STABLE"
                else:
                    trend = "INSUFFICIENT_DATA"
            else:
                trend = "INSUFFICIENT_DATA"
            
            # Extract failure patterns
            failure_patterns = list(set(error_messages[:5]))  # Top 5 unique error messages
            
            return TestMetrics(
                test_name=test_name,
                total_executions=len(records),
                success_rate=success_rate,
                avg_execution_time=statistics.mean(execution_times),
                p95_execution_time=statistics.quantiles(execution_times, n=20)[18] if len(execution_times) >= 20 else max(execution_times),
                p99_execution_time=statistics.quantiles(execution_times, n=100)[98] if len(execution_times) >= 100 else max(execution_times),
                trend_direction=trend,
                maintenance_burden=statistics.mean(maintenance_scores) if maintenance_scores else 0.0,
                last_execution=datetime.fromisoformat(records[0][2]),
                failure_patterns=failure_patterns
            )
    
    def get_coverage_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get coverage trend data for the specified period."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT timestamp, function_coverage, branch_coverage, line_coverage, test_suite
                FROM coverage_trends 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (cutoff_date.isoformat(),))
            
            return [{
                'timestamp': datetime.fromisoformat(row[0]),
                'function_coverage': row[1],
                'branch_coverage': row[2],
                'line_coverage': row[3],
                'test_suite': row[4]
            } for row in cursor.fetchall()]
    
    def detect_performance_regression(self, test_name: str, 
                                    threshold: float = 1.2) -> Dict[str, Any]:
        """Detect performance regression for a specific test."""
        baseline = self.performance_baselines.get(test_name)
        if not baseline:
            return {'regression_detected': False, 'reason': 'No baseline available'}
        
        # Get recent executions
        recent_metrics = self.get_test_metrics(test_name, days=7)
        if not recent_metrics:
            return {'regression_detected': False, 'reason': 'No recent executions'}
        
        current_avg = recent_metrics.avg_execution_time
        regression_detected = current_avg > baseline * threshold
        
        return {
            'regression_detected': regression_detected,
            'baseline_time': baseline,
            'current_avg_time': current_avg,
            'regression_factor': current_avg / baseline if baseline > 0 else 0,
            'threshold': threshold,
            'recommendation': self._get_regression_recommendation(
                regression_detected, current_avg / baseline if baseline > 0 else 0
            )
        }
    
    def _get_regression_recommendation(self, regression_detected: bool, 
                                     factor: float) -> str:
        """Get recommendation based on regression analysis."""
        if not regression_detected:
            return "Performance is within acceptable range"
        
        if factor > 2.0:
            return "CRITICAL: Performance degraded by >100%. Immediate investigation required."
        elif factor > 1.5:
            return "WARNING: Significant performance degradation detected. Review recent changes."
        elif factor > 1.2:
            return "NOTICE: Minor performance degradation. Monitor closely."
        else:
            return "Performance is stable"
    
    def update_baseline(self, test_name: str, new_baseline: float):
        """Update performance baseline for a test."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO performance_baselines 
                (test_name, baseline_time, updated_at)
                VALUES (?, ?, ?)
            ''', (test_name, new_baseline, datetime.now().isoformat()))
        
        self.performance_baselines[test_name] = new_baseline
        self.logger.info(f"Updated baseline for {test_name}: {new_baseline:.3f}s")
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        with sqlite3.connect(self.db_path) as conn:
            # Overall test success rate (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor = conn.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'PASSED' THEN 1 ELSE 0 END) as passed
                FROM test_executions 
                WHERE timestamp > ?
            ''', (week_ago,))
            
            total, passed = cursor.fetchone()
            success_rate = (passed / total * 100) if total > 0 else 0
            
            # Average execution time trend
            cursor = conn.execute('''
                SELECT AVG(execution_time) as avg_time,
                       DATE(timestamp) as date
                FROM test_executions 
                WHERE timestamp > ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            ''', (week_ago,))
            
            daily_averages = cursor.fetchall()
            
            # Test reliability (tests with >90% success rate)
            cursor = conn.execute('''
                SELECT test_name,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'PASSED' THEN 1 ELSE 0 END) as passed
                FROM test_executions 
                WHERE timestamp > ?
                GROUP BY test_name
                HAVING total >= 5
            ''', (week_ago,))
            
            test_reliability = []
            for test_name, total, passed in cursor.fetchall():
                rate = (passed / total) * 100
                test_reliability.append({
                    'test_name': test_name,
                    'success_rate': rate,
                    'total_executions': total
                })
            
            reliable_tests = sum(1 for t in test_reliability if t['success_rate'] >= 90)
            
            return {
                'overall_success_rate': success_rate,
                'total_tests_executed': total,
                'reliable_tests_count': reliable_tests,
                'total_test_types': len(test_reliability),
                'avg_execution_time_trend': daily_averages,
                'test_reliability_details': test_reliability
            }
    
    def export_metrics_json(self, output_path: str, days: int = 30):
        """Export all metrics to JSON file."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all test names
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT DISTINCT test_name FROM test_executions 
                WHERE timestamp > ?
            ''', (cutoff_date.isoformat(),))
            
            test_names = [row[0] for row in cursor.fetchall()]
        
        # Collect metrics for all tests
        all_metrics = {}
        for test_name in test_names:
            metrics = self.get_test_metrics(test_name, days)
            if metrics:
                all_metrics[test_name] = asdict(metrics)
                # Convert datetime to string for JSON serialization
                all_metrics[test_name]['last_execution'] = metrics.last_execution.isoformat()
        
        # Add system health metrics
        system_metrics = self.get_system_health_metrics()
        
        # Add coverage trends
        coverage_trends = self.get_coverage_trends(days)
        for trend in coverage_trends:
            trend['timestamp'] = trend['timestamp'].isoformat()
        
        export_data = {
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'test_metrics': all_metrics,
            'system_health': system_metrics,
            'coverage_trends': coverage_trends
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"Exported metrics to {output_path}")


if __name__ == "__main__":
    # Example usage
    collector = TestMetricsCollector()
    
    # Simulate some test executions
    test_id = collector.start_test_execution("test_mpu6050_init", "unit_tests")
    time.sleep(0.1)  # Simulate test execution
    collector.end_test_execution(test_id, "PASSED")
    
    # Record coverage data
    collector.record_coverage_data(95.0, 87.0, 92.0, "unit_tests")
    
    # Get metrics
    metrics = collector.get_test_metrics("test_mpu6050_init")
    if metrics:
        print(f"Test metrics: {metrics}")
    
    # Export to JSON
    collector.export_metrics_json("test_metrics_export.json")