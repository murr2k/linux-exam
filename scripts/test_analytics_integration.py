#!/usr/bin/env python3
"""
Test Analytics Integration Example

This script demonstrates how to integrate the test analytics system
with existing test infrastructure and provides examples of usage.
"""

import os
import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from analytics.test_metrics_collector import TestMetricsCollector
from analytics.quality_analyzer import QualityAnalyzer
from analytics.performance_analyzer import PerformanceAnalyzer
from analytics.ci_integration import CIIntegration


class TestAnalyticsDemo:
    """Demonstration of test analytics system integration."""
    
    def __init__(self, db_path: str = "data/test_analytics.db"):
        self.db_path = db_path
        
        # Initialize analytics components
        self.metrics_collector = TestMetricsCollector(db_path)
        self.quality_analyzer = QualityAnalyzer(db_path)
        self.performance_analyzer = PerformanceAnalyzer(db_path)
        self.ci_integration = CIIntegration(db_path)
        
        print(f"🚀 Test Analytics Demo initialized with database: {db_path}")
    
    def simulate_test_executions(self, num_tests: int = 50):
        """Simulate a series of test executions with realistic data."""
        print(f"📊 Simulating {num_tests} test executions...")
        
        test_names = [
            "test_mpu6050_initialization",
            "test_sensor_data_reading", 
            "test_i2c_communication",
            "test_calibration_process",
            "test_error_handling",
            "test_performance_stress",
            "test_concurrent_access",
            "test_device_reset",
            "test_interrupt_handling",
            "test_power_management"
        ]
        
        test_categories = ["unit_tests", "integration_tests", "performance_tests", "stress_tests"]
        
        for i in range(num_tests):
            test_name = random.choice(test_names)
            test_category = random.choice(test_categories)
            
            # Start test execution tracking
            test_id = self.metrics_collector.start_test_execution(test_name, test_category)
            
            # Simulate test execution time (varying by category)
            base_time = {
                "unit_tests": 0.1,
                "integration_tests": 2.0,
                "performance_tests": 5.0,
                "stress_tests": 10.0
            }.get(test_category, 1.0)
            
            execution_time = base_time * random.uniform(0.5, 2.0)
            time.sleep(min(execution_time, 0.1))  # Don't actually wait full time
            
            # Simulate test result (mostly pass, some failures)
            status = "PASSED" if random.random() > 0.1 else "FAILED"
            error_message = None
            
            if status == "FAILED":
                error_messages = [
                    "Assertion failed: Expected sensor value in range",
                    "I2C communication timeout",
                    "Device initialization failed",
                    "Memory allocation error",
                    "Invalid sensor configuration"
                ]
                error_message = random.choice(error_messages)
            
            # Simulate coverage data
            coverage_data = {
                'line_coverage': random.uniform(70, 95),
                'branch_coverage': random.uniform(65, 90),
                'function_coverage': random.uniform(80, 98)
            }
            
            # End test execution tracking
            self.metrics_collector.end_test_execution(
                test_id, status, error_message, coverage_data
            )
            
            # Record performance metrics
            self.performance_analyzer.record_performance_metrics(
                test_name=test_name,
                execution_time=execution_time,
                cpu_usage=random.uniform(10, 80),
                memory_usage=random.uniform(50, 200),
                disk_io=random.uniform(0, 1024),
                network_io=random.uniform(0, 512)
            )
            
            # Record coverage trends periodically
            if i % 10 == 0:
                self.metrics_collector.record_coverage_data(
                    coverage_data['function_coverage'],
                    coverage_data['branch_coverage'],
                    coverage_data['line_coverage'],
                    test_category
                )
            
            if i % 10 == 0:
                print(f"  ✓ Completed {i+1}/{num_tests} test simulations")
        
        print(f"✅ Completed simulation of {num_tests} test executions")
    
    def analyze_test_quality(self):
        """Demonstrate test quality analysis."""
        print("\n🔍 Analyzing test quality...")
        
        # Sample test source code for quality analysis
        sample_test_code = '''
        void test_mpu6050_initialization() {
            // Test normal initialization
            mpu6050_dev_t device;
            int result = mpu6050_init(&device, MPU6050_I2C_ADDR);
            EXPECT_EQ(result, MPU6050_SUCCESS);
            EXPECT_TRUE(device.initialized);
            EXPECT_NE(device.handle, NULL);
            
            // Test invalid address boundary condition
            result = mpu6050_init(&device, INVALID_I2C_ADDR);
            EXPECT_EQ(result, MPU6050_ERROR_INVALID_ADDR);
            
            // Test null pointer error handling
            result = mpu6050_init(nullptr, MPU6050_I2C_ADDR);
            EXPECT_EQ(result, MPU6050_ERROR_NULL_PTR);
            
            // Test boundary conditions
            result = mpu6050_init(&device, 0x68);  // MIN valid address
            EXPECT_EQ(result, MPU6050_SUCCESS);
            
            result = mpu6050_init(&device, 0x69);  // MAX valid address  
            EXPECT_EQ(result, MPU6050_SUCCESS);
            
            // Test error recovery
            device.initialized = false;
            result = mpu6050_reinit(&device);
            EXPECT_EQ(result, MPU6050_SUCCESS);
        }
        '''
        
        coverage_data = {
            'line_coverage': 87.5,
            'branch_coverage': 82.3,
            'function_coverage': 94.1
        }
        
        quality_score = self.quality_analyzer.analyze_test_quality(
            "test_mpu6050_initialization", 
            sample_test_code,
            coverage_data
        )
        
        print(f"  📈 Quality Score: {quality_score.overall_score:.3f}")
        print(f"  📊 Coverage Score: {quality_score.coverage_score:.3f}")
        print(f"  🎯 Assertion Score: {quality_score.assertion_score:.3f}")
        print(f"  🔬 Boundary Score: {quality_score.boundary_score:.3f}")
        print(f"  ⚠️  Error Handling Score: {quality_score.error_handling_score:.3f}")
        print(f"  🔧 Maintainability Score: {quality_score.maintainability_score:.3f}")
        
        # Get recommendations
        recommendations = self.quality_analyzer.get_quality_recommendations("test_mpu6050_initialization")
        print("\n💡 Quality Recommendations:")
        for rec in recommendations[:3]:
            print(f"  • {rec}")
    
    def demonstrate_performance_analysis(self):
        """Demonstrate performance analysis and regression detection."""
        print("\n⚡ Demonstrating performance analysis...")
        
        # Establish baseline for a test
        test_name = "test_sensor_data_reading"
        baseline_established = self.performance_analyzer.establish_baseline(test_name)
        
        if baseline_established:
            print(f"  ✅ Baseline established for {test_name}")
        
        # Check for performance regression
        regression_result = self.performance_analyzer.detect_performance_regression(test_name)
        
        print(f"  📊 Regression Analysis for {test_name}:")
        print(f"    • Regression Detected: {regression_result.regression_detected}")
        print(f"    • Current Mean: {regression_result.current_mean:.3f}s")
        print(f"    • Baseline Mean: {regression_result.baseline_mean:.3f}s") 
        print(f"    • Regression Factor: {regression_result.regression_factor:.2f}x")
        print(f"    • Confidence: {regression_result.confidence_level:.1%}")
        print(f"    • Recommendation: {regression_result.recommendation}")
        
        # Analyze resource trends
        print("\n  📈 Resource Usage Trends:")
        resource_trends = self.performance_analyzer.analyze_resource_trends(days=7)
        
        for trend in resource_trends[:5]:  # Show top 5 trends
            print(f"    • {trend.resource_type}: {trend.trend_direction} "
                  f"(strength: {trend.trend_strength:.2f})")
    
    def demonstrate_ci_integration(self):
        """Demonstrate CI/CD integration capabilities."""
        print("\n🔄 Demonstrating CI/CD integration...")
        
        # Generate CI report
        build_id = f"build_{int(time.time())}"
        commit_hash = "abc123def456"
        branch = "feature/analytics-integration"
        
        ci_report = self.ci_integration.generate_ci_report(build_id, commit_hash, branch)
        
        print(f"  📋 CI Report Generated:")
        print(f"    • Build ID: {ci_report.build_id}")
        print(f"    • Commit: {ci_report.commit_hash}")
        print(f"    • Branch: {ci_report.branch}")
        print(f"    • Tests Executed: {ci_report.test_summary['tests_executed']}")
        print(f"    • Success Rate: {ci_report.test_summary['success_rate']:.1f}%")
        print(f"    • Average Coverage: {ci_report.test_summary['coverage']['average']:.1f}%")
        
        print(f"\n  🚪 Quality Gates Status:")
        for gate_name, gate_result in ci_report.quality_gates.items():
            status_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[gate_result.status]
            print(f"    {status_emoji} {gate_name.replace('_', ' ').title()}: {gate_result.status}")
        
        print(f"\n  🚨 Active Alerts: {len(ci_report.alerts)}")
        for alert in ci_report.alerts[:3]:  # Show first 3 alerts
            print(f"    • {alert['test_name']}: {alert['level']}")
        
        print(f"\n  💡 Recommendations: {len(ci_report.recommendations)}")
        for rec in ci_report.recommendations[:3]:  # Show first 3 recommendations
            print(f"    • {rec[:80]}...")
    
    def export_reports(self):
        """Export various analytics reports."""
        print("\n📄 Exporting analytics reports...")
        
        output_dir = Path("test-reports")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export metrics to JSON
        metrics_file = output_dir / f"test_metrics_{timestamp}.json"
        self.metrics_collector.export_metrics_json(str(metrics_file))
        print(f"  ✅ Test metrics exported to: {metrics_file}")
        
        # Export quality report
        quality_file = output_dir / f"quality_report_{timestamp}.json"
        self.quality_analyzer.export_quality_report(str(quality_file))
        print(f"  ✅ Quality report exported to: {quality_file}")
        
        # Export performance report
        performance_file = output_dir / f"performance_report_{timestamp}.json"
        self.performance_analyzer.generate_performance_report(str(performance_file))
        print(f"  ✅ Performance report exported to: {performance_file}")
    
    def display_dashboard_info(self):
        """Display information about the dashboard."""
        print("\n🖥️  Dashboard Information:")
        print("  To start the real-time dashboard:")
        print("    1. Run: ./scripts/start_analytics.sh")
        print("    2. Open: http://localhost:5000")
        print("  ")
        print("  Dashboard features:")
        print("    • Real-time test execution monitoring")
        print("    • Quality gate status visualization")
        print("    • Performance trend charts")
        print("    • Active alerts and recommendations")
        print("    • Historical data analysis")
    
    def run_comprehensive_demo(self):
        """Run comprehensive demonstration of all features."""
        print("🎯 Running Comprehensive Test Analytics Demo\n")
        
        # Simulate test data
        self.simulate_test_executions(30)
        
        # Demonstrate quality analysis
        self.analyze_test_quality()
        
        # Demonstrate performance analysis
        self.demonstrate_performance_analysis()
        
        # Demonstrate CI integration
        self.demonstrate_ci_integration()
        
        # Export reports
        self.export_reports()
        
        # Display dashboard info
        self.display_dashboard_info()
        
        print("\n" + "="*70)
        print("🎉 Test Analytics Demo completed successfully!")
        print("="*70)
        print("\nNext steps:")
        print("1. Review the generated reports in test-reports/")
        print("2. Start the dashboard: ./scripts/start_analytics.sh")
        print("3. Integrate with your actual test suite")
        print("4. Configure CI/CD integration (see config/analytics_config.json)")


def integration_example():
    """Example of how to integrate analytics with existing tests."""
    print("\n" + "="*50)
    print("INTEGRATION EXAMPLE")
    print("="*50)
    
    example_code = '''
# Example: Integrating with existing test framework

import unittest
from src.analytics.test_metrics_collector import TestMetricsCollector

class AnalyticsTestCase(unittest.TestCase):
    """Test case with analytics integration."""
    
    @classmethod
    def setUpClass(cls):
        cls.metrics_collector = TestMetricsCollector()
    
    def setUp(self):
        """Start metrics collection for each test."""
        test_name = f"{self.__class__.__name__}.{self._testMethodName}"
        self.test_id = self.metrics_collector.start_test_execution(
            test_name, "unit_tests"
        )
    
    def tearDown(self):
        """End metrics collection and record results."""
        status = "PASSED" if self._outcome.success else "FAILED"
        error_msg = None
        
        if hasattr(self._outcome, 'errors') and self._outcome.errors:
            error_msg = str(self._outcome.errors[0][1])
        
        # Get coverage data (implement based on your coverage tool)
        coverage_data = self.get_coverage_data()
        
        self.metrics_collector.end_test_execution(
            self.test_id, status, error_msg, coverage_data
        )
    
    def get_coverage_data(self):
        """Get coverage data from your coverage tool."""
        # Integrate with your coverage measurement tool
        return {
            'line_coverage': 85.0,
            'branch_coverage': 78.0,
            'function_coverage': 92.0
        }
    
    def test_sensor_initialization(self):
        """Example test with analytics tracking."""
        # Your test code here
        device = initialize_mpu6050()
        self.assertIsNotNone(device)
        self.assertTrue(device.is_initialized)

# Example: Using analytics in pytest

import pytest
from src.analytics.test_metrics_collector import TestMetricsCollector

@pytest.fixture(scope="session")
def metrics_collector():
    return TestMetricsCollector()

@pytest.fixture(autouse=True)
def track_test_metrics(request, metrics_collector):
    """Automatically track metrics for all tests."""
    test_name = f"{request.node.module.__name__}.{request.node.name}"
    test_id = metrics_collector.start_test_execution(test_name, "pytest")
    
    def finalize():
        # Determine test result
        if hasattr(request.node, 'rep_call'):
            status = "PASSED" if request.node.rep_call.passed else "FAILED"
            error_msg = str(request.node.rep_call.longrepr) if request.node.rep_call.failed else None
        else:
            status = "PASSED"
            error_msg = None
        
        metrics_collector.end_test_execution(test_id, status, error_msg)
    
    request.addfinalizer(finalize)

# Example: CI/CD Pipeline Integration

# In your CI/CD pipeline script:
from src.analytics.ci_integration import CIIntegration

def run_ci_pipeline():
    """Run CI pipeline with analytics."""
    build_id = os.getenv('BUILD_ID', 'local')
    commit_hash = os.getenv('COMMIT_SHA', 'unknown')
    branch = os.getenv('BRANCH_NAME', 'main')
    pr_number = os.getenv('PR_NUMBER')
    
    ci_integration = CIIntegration()
    
    # Run your tests here with analytics collection
    # ... test execution ...
    
    # Generate analytics report and check quality gates
    success = ci_integration.run_ci_pipeline(
        build_id, commit_hash, branch, 
        int(pr_number) if pr_number else None
    )
    
    if not success:
        print("Quality gates failed - blocking deployment")
        sys.exit(1)
    
    print("All quality gates passed - deployment approved")

# Example: Custom Metrics Collection

from src.analytics.performance_analyzer import PerformanceAnalyzer

class CustomPerformanceTracker:
    """Custom performance tracking for specific scenarios."""
    
    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
    
    def track_load_test(self, test_name, duration, concurrent_users):
        """Track load test performance."""
        self.analyzer.record_performance_metrics(
            test_name=f"load_{test_name}",
            execution_time=duration,
            concurrent_tests=concurrent_users,
            # Add custom resource metrics
        )
    
    def track_memory_intensive_test(self, test_name, peak_memory):
        """Track memory-intensive test."""
        self.analyzer.record_performance_metrics(
            test_name=f"memory_{test_name}",
            execution_time=0.0,  # Focus on memory, not time
            memory_usage=peak_memory
        )
'''
    
    print(example_code)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Analytics Integration Demo")
    parser.add_argument("--db-path", default="data/test_analytics.db", 
                       help="Database path for analytics")
    parser.add_argument("--num-tests", type=int, default=30,
                       help="Number of test executions to simulate")
    parser.add_argument("--show-integration-example", action="store_true",
                       help="Show integration example code")
    
    args = parser.parse_args()
    
    if args.show_integration_example:
        integration_example()
    else:
        # Ensure the data directory exists
        db_path = Path(args.db_path)
        db_path.parent.mkdir(exist_ok=True)
        
        # Run the demo
        demo = TestAnalyticsDemo(args.db_path)
        demo.run_comprehensive_demo()