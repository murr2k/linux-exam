#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Test Analytics System

Tests the complete analytics system integration including metrics collection,
quality analysis, performance monitoring, and reporting functionality.
"""

import unittest
import tempfile
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from analytics.test_metrics_collector import TestMetricsCollector, TestExecution
from analytics.quality_analyzer import QualityAnalyzer, QualityScore
from analytics.performance_analyzer import PerformanceAnalyzer
from analytics.ci_integration import CIIntegration


class TestAnalyticsIntegrationTest(unittest.TestCase):
    """Comprehensive integration tests for the analytics system."""
    
    def setUp(self):
        """Set up test environment with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize analytics components
        self.metrics_collector = TestMetricsCollector(self.db_path)
        self.quality_analyzer = QualityAnalyzer(self.db_path)
        self.performance_analyzer = PerformanceAnalyzer(self.db_path)
        self.ci_integration = CIIntegration(self.db_path)
    
    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_end_to_end_test_execution_tracking(self):
        """Test complete test execution tracking workflow."""
        test_name = "test_integration_example"
        test_category = "integration_tests"
        
        # Start test execution
        test_id = self.metrics_collector.start_test_execution(test_name, test_category)
        self.assertIsNotNone(test_id)
        self.assertIn(test_id, self.metrics_collector.active_tests)
        
        # Verify active test
        active_test = self.metrics_collector.active_tests[test_id]
        self.assertEqual(active_test.test_name, test_name)
        self.assertEqual(active_test.test_category, test_category)
        self.assertEqual(active_test.status, "RUNNING")
        
        # End test execution with results
        coverage_data = {
            'line_coverage': 85.5,
            'branch_coverage': 78.2,
            'function_coverage': 92.1
        }
        
        self.metrics_collector.end_test_execution(
            test_id, "PASSED", None, coverage_data
        )
        
        # Verify test is no longer active
        self.assertNotIn(test_id, self.metrics_collector.active_tests)
        
        # Verify data was stored in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM test_executions WHERE test_id = ?', 
                (test_id,)
            )
            result = cursor.fetchone()
            
            self.assertIsNotNone(result)
            self.assertEqual(result[2], test_name)  # test_name column
            self.assertEqual(result[3], test_category)  # test_category column
            self.assertEqual(result[5], "PASSED")  # status column
    
    def test_coverage_trend_analysis(self):
        """Test coverage trend tracking and analysis."""
        test_suite = "unit_tests"
        
        # Record several coverage data points over time
        coverage_points = [
            (80.0, 75.0, 85.0),
            (82.0, 77.0, 87.0),
            (85.0, 80.0, 90.0),
            (87.0, 82.0, 92.0),
            (90.0, 85.0, 94.0)
        ]
        
        for func_cov, branch_cov, line_cov in coverage_points:
            self.metrics_collector.record_coverage_data(
                func_cov, branch_cov, line_cov, test_suite
            )
        
        # Get coverage trends
        trends = self.metrics_collector.get_coverage_trends(days=1)
        
        self.assertGreaterEqual(len(trends), 5)
        
        # Verify latest trend
        latest = trends[0]  # Most recent first
        self.assertEqual(latest['function_coverage'], 90.0)
        self.assertEqual(latest['branch_coverage'], 85.0)
        self.assertEqual(latest['line_coverage'], 94.0)
        self.assertEqual(latest['test_suite'], test_suite)
    
    def test_quality_analysis_workflow(self):
        """Test complete quality analysis workflow."""
        test_name = "test_quality_example"
        
        # Sample test source code
        test_source = '''
        void test_sensor_initialization() {
            // Test normal initialization
            sensor_t sensor;
            int result = sensor_init(&sensor, SENSOR_TYPE_ACCEL);
            EXPECT_EQ(result, SENSOR_SUCCESS);
            EXPECT_TRUE(sensor.initialized);
            
            // Test null pointer error handling
            result = sensor_init(NULL, SENSOR_TYPE_ACCEL);
            EXPECT_EQ(result, SENSOR_ERROR_NULL_PTR);
            
            // Test invalid type boundary condition
            result = sensor_init(&sensor, INVALID_SENSOR_TYPE);
            EXPECT_EQ(result, SENSOR_ERROR_INVALID_TYPE);
            
            // Test boundary values
            result = sensor_init(&sensor, SENSOR_TYPE_MIN);
            EXPECT_EQ(result, SENSOR_SUCCESS);
            
            result = sensor_init(&sensor, SENSOR_TYPE_MAX);
            EXPECT_EQ(result, SENSOR_SUCCESS);
        }
        '''
        
        coverage_data = {
            'line_coverage': 88.5,
            'branch_coverage': 81.3,
            'function_coverage': 95.2
        }
        
        # Analyze test quality
        quality_score = self.quality_analyzer.analyze_test_quality(
            test_name, test_source, coverage_data
        )
        
        # Verify quality score structure
        self.assertIsInstance(quality_score, QualityScore)
        self.assertGreater(quality_score.overall_score, 0.0)
        self.assertLessEqual(quality_score.overall_score, 1.0)
        
        # Verify individual scores are reasonable
        self.assertGreater(quality_score.coverage_score, 0.7)  # Good coverage
        self.assertGreater(quality_score.assertion_score, 0.0)  # Has assertions
        self.assertGreater(quality_score.boundary_score, 0.0)   # Has boundary tests
        self.assertGreater(quality_score.error_handling_score, 0.0)  # Has error handling
        
        # Get recommendations
        recommendations = self.quality_analyzer.get_quality_recommendations(test_name)
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Verify quality score was stored
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM test_quality_scores WHERE test_name = ?',
                (test_name,)
            )
            result = cursor.fetchone()
            
            self.assertIsNotNone(result)
            self.assertEqual(result[1], test_name)  # test_name column
    
    def test_performance_analysis_and_regression_detection(self):
        """Test performance analysis and regression detection."""
        test_name = "test_performance_example"
        
        # Record baseline performance data
        baseline_times = [1.0, 1.1, 0.9, 1.05, 0.95, 1.02, 0.98, 1.08, 0.92, 1.03]
        
        for exec_time in baseline_times:
            self.performance_analyzer.record_performance_metrics(
                test_name=test_name,
                execution_time=exec_time,
                cpu_usage=45.0,
                memory_usage=128.0
            )
        
        # Establish baseline
        baseline_established = self.performance_analyzer.establish_baseline(test_name)
        self.assertTrue(baseline_established)
        
        # Record some recent data with slight regression
        recent_times = [1.3, 1.25, 1.35, 1.28, 1.32]  # ~30% slower
        
        for exec_time in recent_times:
            self.performance_analyzer.record_performance_metrics(
                test_name=test_name,
                execution_time=exec_time,
                cpu_usage=55.0,
                memory_usage=140.0
            )
        
        # Detect regression
        regression_result = self.performance_analyzer.detect_performance_regression(test_name)
        
        # Verify regression detection
        self.assertTrue(regression_result.regression_detected)
        self.assertGreater(regression_result.regression_factor, 1.2)  # Significant regression
        self.assertGreater(regression_result.confidence_level, 0.9)   # High confidence
        self.assertIn("regression", regression_result.recommendation.lower())
        
        # Get performance statistics
        stats = self.performance_analyzer.get_performance_statistics(test_name)
        
        self.assertIn('execution_time', stats)
        self.assertIn('resource_usage', stats)
        self.assertGreater(stats['execution_time']['mean'], 1.0)
        self.assertGreater(stats['sample_size'], 10)
    
    def test_ci_integration_workflow(self):
        """Test complete CI integration workflow."""
        build_id = "test_build_123"
        commit_hash = "abc123def456"
        branch = "feature/test-branch"
        
        # Generate some test data first
        test_names = ["test_unit_example", "test_integration_example"]
        
        for test_name in test_names:
            # Record test execution
            test_id = self.metrics_collector.start_test_execution(test_name, "unit_tests")
            self.metrics_collector.end_test_execution(
                test_id, "PASSED", None,
                {'line_coverage': 85.0, 'branch_coverage': 80.0, 'function_coverage': 90.0}
            )
            
            # Record performance metrics
            self.performance_analyzer.record_performance_metrics(
                test_name=test_name,
                execution_time=1.0,
                cpu_usage=40.0,
                memory_usage=100.0
            )
        
        # Record coverage trends
        self.metrics_collector.record_coverage_data(85.0, 80.0, 90.0, "unit_tests")
        
        # Generate CI report
        ci_report = self.ci_integration.generate_ci_report(build_id, commit_hash, branch)
        
        # Verify CI report structure
        self.assertEqual(ci_report.build_id, build_id)
        self.assertEqual(ci_report.commit_hash, commit_hash)
        self.assertEqual(ci_report.branch, branch)
        
        # Verify test summary
        self.assertIn('tests_executed', ci_report.test_summary)
        self.assertIn('success_rate', ci_report.test_summary)
        self.assertIn('coverage', ci_report.test_summary)
        
        # Verify quality gates were evaluated
        self.assertGreater(len(ci_report.quality_gates), 0)
        
        # Check that report was stored
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM ci_reports WHERE build_id = ?',
                (build_id,)
            )
            result = cursor.fetchone()
            
            self.assertIsNotNone(result)
            self.assertEqual(result[1], build_id)  # build_id column
    
    def test_quality_gates_evaluation(self):
        """Test quality gates evaluation logic."""
        # Set up test data that should pass quality gates
        test_name = "test_quality_gate"
        
        # High coverage test
        test_id = self.metrics_collector.start_test_execution(test_name, "unit_tests")
        self.metrics_collector.end_test_execution(
            test_id, "PASSED", None,
            {'line_coverage': 92.0, 'branch_coverage': 88.0, 'function_coverage': 95.0}
        )
        
        # Record good performance
        self.performance_analyzer.record_performance_metrics(
            test_name=test_name,
            execution_time=0.5,
            cpu_usage=30.0,
            memory_usage=80.0
        )
        
        # Record coverage trends
        self.metrics_collector.record_coverage_data(92.0, 88.0, 95.0, "unit_tests")
        
        # Evaluate quality gates through CI integration
        ci_report = self.ci_integration.generate_ci_report("test_build", "abc123", "main")
        
        # Verify quality gates
        quality_gates = ci_report.quality_gates
        
        self.assertIn('code_coverage', quality_gates)
        self.assertIn('test_success_rate', quality_gates)
        
        # Coverage gate should pass with high coverage
        coverage_gate = quality_gates['code_coverage']
        self.assertIn(coverage_gate.status, ['PASS', 'WARN'])  # Should at least warn, ideally pass
        
        # Success rate gate should pass with 100% success
        success_gate = quality_gates['test_success_rate']
        self.assertEqual(success_gate.status, 'PASS')
    
    def test_alert_generation_and_tracking(self):
        """Test alert generation and tracking system."""
        test_name = "test_alert_example"
        
        # Create baseline
        for i in range(10):
            self.performance_analyzer.record_performance_metrics(
                test_name=test_name,
                execution_time=1.0,
                cpu_usage=40.0,
                memory_usage=100.0
            )
        
        self.performance_analyzer.establish_baseline(test_name)
        
        # Create significant regression to trigger alert
        for i in range(5):
            self.performance_analyzer.record_performance_metrics(
                test_name=test_name,
                execution_time=2.5,  # 150% slower - should trigger alert
                cpu_usage=40.0,
                memory_usage=100.0
            )
        
        # Check for alerts in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM regression_alerts WHERE test_name = ? AND resolved = FALSE',
                (test_name,)
            )
            alerts = cursor.fetchall()
        
        self.assertGreater(len(alerts), 0, "Performance regression should trigger alert")
        
        alert = alerts[0]
        self.assertEqual(alert[1], test_name)  # test_name column
        self.assertIn(alert[2], ['MAJOR', 'CRITICAL'])  # alert_level column
        self.assertGreater(alert[3], 2.0)  # regression_factor column
    
    def test_data_export_functionality(self):
        """Test data export functionality."""
        # Generate some test data
        test_name = "test_export_example"
        
        test_id = self.metrics_collector.start_test_execution(test_name, "unit_tests")
        self.metrics_collector.end_test_execution(
            test_id, "PASSED", None,
            {'line_coverage': 85.0, 'branch_coverage': 80.0, 'function_coverage': 90.0}
        )
        
        # Test metrics export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name
        
        try:
            self.metrics_collector.export_metrics_json(export_path)
            
            # Verify export file exists and contains data
            self.assertTrue(os.path.exists(export_path))
            
            with open(export_path, 'r') as f:
                exported_data = json.load(f)
            
            self.assertIn('generated_at', exported_data)
            self.assertIn('test_metrics', exported_data)
            
            # Should contain our test
            test_metrics = exported_data['test_metrics']
            self.assertIn(test_name, test_metrics)
            
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)
    
    def test_system_health_metrics(self):
        """Test system health metrics calculation."""
        # Generate diverse test data
        test_data = [
            ("test_reliable_1", "PASSED"),
            ("test_reliable_1", "PASSED"),
            ("test_reliable_1", "PASSED"),
            ("test_reliable_1", "PASSED"),
            ("test_reliable_1", "PASSED"),
            ("test_flaky_1", "PASSED"),
            ("test_flaky_1", "FAILED"),
            ("test_flaky_1", "PASSED"),
            ("test_flaky_1", "FAILED"),
            ("test_flaky_1", "PASSED"),
        ]
        
        for test_name, status in test_data:
            test_id = self.metrics_collector.start_test_execution(test_name, "unit_tests")
            error_msg = "Test failure message" if status == "FAILED" else None
            self.metrics_collector.end_test_execution(test_id, status, error_msg)
        
        # Get system health metrics
        health_metrics = self.metrics_collector.get_system_health_metrics()
        
        # Verify structure
        self.assertIn('overall_success_rate', health_metrics)
        self.assertIn('total_tests_executed', health_metrics)
        self.assertIn('reliable_tests_count', health_metrics)
        self.assertIn('test_reliability_details', health_metrics)
        
        # Verify calculated values
        self.assertEqual(health_metrics['total_tests_executed'], 10)
        self.assertEqual(health_metrics['overall_success_rate'], 80.0)  # 8/10 passed
        
        # Check test reliability details
        reliability_details = health_metrics['test_reliability_details']
        self.assertEqual(len(reliability_details), 2)  # Two different tests
        
        # Find reliable test
        reliable_test = next(
            (t for t in reliability_details if t['test_name'] == 'test_reliable_1'), 
            None
        )
        self.assertIsNotNone(reliable_test)
        self.assertEqual(reliable_test['success_rate'], 100.0)


class TestAnalyticsPerformanceTest(unittest.TestCase):
    """Performance tests for the analytics system."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.metrics_collector = TestMetricsCollector(self.db_path)
    
    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_large_volume_data_handling(self):
        """Test handling of large volumes of test data."""
        import time
        
        start_time = time.time()
        
        # Generate 1000 test executions
        for i in range(1000):
            test_name = f"test_volume_{i % 100}"  # 100 unique test names
            test_id = self.metrics_collector.start_test_execution(test_name, "load_tests")
            
            status = "PASSED" if i % 10 != 0 else "FAILED"  # 10% failure rate
            coverage_data = {
                'line_coverage': 80.0 + (i % 20),
                'branch_coverage': 75.0 + (i % 15),
                'function_coverage': 85.0 + (i % 10)
            }
            
            self.metrics_collector.end_test_execution(test_id, status, None, coverage_data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 1000 tests in reasonable time (< 30 seconds)
        self.assertLess(processing_time, 30.0, 
                       f"Processing 1000 tests took {processing_time:.2f}s, expected < 30s")
        
        # Verify data integrity
        health_metrics = self.metrics_collector.get_system_health_metrics()
        self.assertEqual(health_metrics['total_tests_executed'], 1000)
        self.assertAlmostEqual(health_metrics['overall_success_rate'], 90.0, delta=1.0)
    
    def test_concurrent_access_safety(self):
        """Test concurrent access to the analytics system."""
        import threading
        import time
        
        results = []
        
        def worker_thread(thread_id):
            """Worker thread for concurrent testing."""
            try:
                for i in range(100):
                    test_name = f"test_concurrent_{thread_id}_{i}"
                    test_id = self.metrics_collector.start_test_execution(test_name, "concurrent_tests")
                    time.sleep(0.001)  # Simulate test execution
                    self.metrics_collector.end_test_execution(test_id, "PASSED")
                results.append(f"Thread {thread_id} completed successfully")
            except Exception as e:
                results.append(f"Thread {thread_id} failed: {str(e)}")
        
        # Start 5 concurrent threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all threads completed successfully
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIn("completed successfully", result)
        
        # Verify data integrity
        health_metrics = self.metrics_collector.get_system_health_metrics()
        self.assertEqual(health_metrics['total_tests_executed'], 500)  # 5 threads * 100 tests


def run_comprehensive_tests():
    """Run all comprehensive integration tests."""
    print("🧪 Running Comprehensive Analytics Integration Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add integration tests
    suite.addTest(unittest.makeSuite(TestAnalyticsIntegrationTest))
    suite.addTest(unittest.makeSuite(TestAnalyticsPerformanceTest))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All integration tests passed!")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        return True
    else:
        print("❌ Some integration tests failed!")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
        
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)