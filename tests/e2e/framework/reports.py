#!/usr/bin/env python3
"""
MPU-6050 Test Reporting Module

This module provides comprehensive test reporting capabilities including
HTML report generation, JSON metrics export, JUnit XML for CI integration,
performance graphs, and coverage reports.

Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import os
import json
import time
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

# Optional imports for advanced features
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from jinja2 import Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


@dataclass
class TestSummary:
    """Test execution summary"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_duration: float
    success_rate: float
    start_time: datetime
    end_time: datetime


@dataclass
class TestCase:
    """Individual test case information"""
    name: str
    suite: str
    status: str  # PASS, FAIL, SKIP, ERROR
    duration: float
    error_message: Optional[str] = None
    failure_message: Optional[str] = None
    output: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class MetricsCollector:
    """Collect and aggregate test metrics"""
    
    def __init__(self):
        self.test_metrics: Dict[str, Dict[str, Any]] = {}
        self.system_metrics: Dict[str, Any] = {}
        self.performance_data: Dict[str, List[float]] = {}
    
    def add_test_metrics(self, test_name: str, metrics: Dict[str, Any]):
        """Add metrics for a specific test"""
        self.test_metrics[test_name] = metrics
    
    def add_system_metrics(self, metrics: Dict[str, Any]):
        """Add system-wide metrics"""
        self.system_metrics.update(metrics)
    
    def add_performance_data(self, metric_name: str, values: List[float]):
        """Add performance data points"""
        if metric_name not in self.performance_data:
            self.performance_data[metric_name] = []
        self.performance_data[metric_name].extend(values)
    
    def get_test_metrics(self, test_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific test"""
        return self.test_metrics.get(test_name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        return {
            'test_metrics': self.test_metrics,
            'system_metrics': self.system_metrics,
            'performance_data': self.performance_data
        }


class ReportGenerator:
    """Generate comprehensive test reports in various formats"""
    
    def __init__(self):
        self.report_template = self._get_html_template()
    
    def generate_html_report(self, test_results: Dict[str, Any], output_path: str) -> bool:
        """Generate comprehensive HTML report"""
        try:
            # Parse test results
            summary = self._create_test_summary(test_results)
            test_cases = self._extract_test_cases(test_results)
            
            # Generate performance charts
            charts = {}
            if MATPLOTLIB_AVAILABLE and 'performance_metrics' in test_results:
                charts = self._generate_performance_charts(test_results['performance_metrics'])
            
            # Generate coverage data
            coverage_data = self._extract_coverage_data(test_results)
            
            # Create HTML content
            html_content = self._create_html_content(summary, test_cases, charts, coverage_data)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"HTML report generated: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generating HTML report: {e}")
            return False
    
    def generate_junit_xml(self, test_results: Dict[str, Any], output_path: str) -> bool:
        """Generate JUnit XML report for CI integration"""
        try:
            # Create root testsuites element
            testsuites = ET.Element('testsuites')
            
            # Extract test data
            test_run_info = test_results.get('test_run_info', {})
            test_results_data = test_results.get('test_results', [])
            
            # Group tests by suite
            suites = {}
            for test_result in test_results_data:
                test_name = test_result.get('test_name', '')
                if '::' in test_name:
                    suite_name, case_name = test_name.split('::', 1)
                else:
                    suite_name = 'default'
                    case_name = test_name
                
                if suite_name not in suites:
                    suites[suite_name] = []
                
                suites[suite_name].append({
                    'name': case_name,
                    'classname': suite_name,
                    'time': test_result.get('duration', 0.0),
                    'passed': test_result.get('passed', False),
                    'error_message': test_result.get('error_message'),
                    'metrics': test_result.get('metrics')
                })
            
            # Create testsuite elements
            for suite_name, test_cases in suites.items():
                testsuite = ET.SubElement(testsuites, 'testsuite')
                testsuite.set('name', suite_name)
                testsuite.set('tests', str(len(test_cases)))
                
                failures = sum(1 for tc in test_cases if not tc['passed'])
                testsuite.set('failures', str(failures))
                testsuite.set('errors', '0')
                testsuite.set('skipped', '0')
                
                total_time = sum(tc['time'] for tc in test_cases)
                testsuite.set('time', str(total_time))
                testsuite.set('timestamp', test_run_info.get('timestamp', ''))
                
                # Add test cases
                for test_case in test_cases:
                    testcase = ET.SubElement(testsuite, 'testcase')
                    testcase.set('name', test_case['name'])
                    testcase.set('classname', test_case['classname'])
                    testcase.set('time', str(test_case['time']))
                    
                    if not test_case['passed']:
                        failure = ET.SubElement(testcase, 'failure')
                        failure.set('message', test_case['error_message'] or 'Test failed')
                        failure.text = test_case['error_message'] or 'Test failed'
                    
                    # Add properties if metrics available
                    if test_case['metrics']:
                        properties = ET.SubElement(testcase, 'properties')
                        for key, value in test_case['metrics'].items():
                            prop = ET.SubElement(properties, 'property')
                            prop.set('name', str(key))
                            prop.set('value', str(value))
            
            # Write XML to file
            tree = ET.ElementTree(testsuites)
            ET.indent(tree, space="  ", level=0)  # Pretty print
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            print(f"JUnit XML report generated: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generating JUnit XML report: {e}")
            return False
    
    def generate_json_metrics(self, test_results: Dict[str, Any], output_path: str) -> bool:
        """Generate JSON metrics export"""
        try:
            # Extract key metrics
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'test_summary': self._create_test_summary(test_results).__dict__,
                'performance_metrics': test_results.get('performance_metrics', {}),
                'resource_metrics': test_results.get('resource_metrics', {}),
                'system_info': {
                    'platform': os.name,
                    'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                },
                'test_details': []
            }
            
            # Add detailed test information
            for test_result in test_results.get('test_results', []):
                metrics['test_details'].append({
                    'name': test_result.get('test_name', ''),
                    'passed': test_result.get('passed', False),
                    'duration': test_result.get('duration', 0.0),
                    'error': test_result.get('error_message'),
                    'metrics': test_result.get('metrics', {})
                })
            
            # Write JSON to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, default=str)
            
            print(f"JSON metrics report generated: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generating JSON metrics report: {e}")
            return False
    
    def generate_comprehensive_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive report data"""
        try:
            summary = self._create_test_summary(test_results)
            test_cases = self._extract_test_cases(test_results)
            
            report = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'generator': 'MPU-6050 Test Framework',
                    'version': '1.0.0'
                },
                'summary': {
                    'total_tests': summary.total_tests,
                    'passed_tests': summary.passed_tests,
                    'failed_tests': summary.failed_tests,
                    'skipped_tests': summary.skipped_tests,
                    'success_rate': summary.success_rate,
                    'total_duration': summary.total_duration,
                    'start_time': summary.start_time.isoformat(),
                    'end_time': summary.end_time.isoformat()
                },
                'test_cases': [
                    {
                        'name': tc.name,
                        'suite': tc.suite,
                        'status': tc.status,
                        'duration': tc.duration,
                        'error_message': tc.error_message,
                        'failure_message': tc.failure_message,
                        'output': tc.output,
                        'metrics': tc.metrics
                    }
                    for tc in test_cases
                ],
                'performance_analysis': self._analyze_performance_data(test_results),
                'resource_analysis': self._analyze_resource_data(test_results),
                'recommendations': self._generate_recommendations(test_results)
            }
            
            return report
            
        except Exception as e:
            print(f"Error generating comprehensive report: {e}")
            return {}
    
    def _create_test_summary(self, test_results: Dict[str, Any]) -> TestSummary:
        """Create test summary from results"""
        test_run_info = test_results.get('test_run_info', {})
        test_results_data = test_results.get('test_results', [])
        
        total_tests = len(test_results_data)
        passed_tests = sum(1 for r in test_results_data if r.get('passed', False))
        failed_tests = total_tests - passed_tests
        skipped_tests = 0  # Not currently used
        
        total_duration = sum(r.get('duration', 0.0) for r in test_results_data)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0
        
        # Parse timestamps
        try:
            start_time = datetime.fromisoformat(test_run_info.get('timestamp', datetime.now().isoformat()))
        except:
            start_time = datetime.now()
        
        end_time = start_time  # For now, using start time as end time
        
        return TestSummary(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            total_duration=total_duration,
            success_rate=success_rate,
            start_time=start_time,
            end_time=end_time
        )
    
    def _extract_test_cases(self, test_results: Dict[str, Any]) -> List[TestCase]:
        """Extract test cases from results"""
        test_cases = []
        
        for test_result in test_results.get('test_results', []):
            test_name = test_result.get('test_name', '')
            
            # Split suite and case name
            if '::' in test_name:
                suite_name, case_name = test_name.split('::', 1)
            else:
                suite_name = 'default'
                case_name = test_name
            
            # Determine status
            if test_result.get('passed', False):
                status = 'PASS'
            elif test_result.get('error_message'):
                status = 'ERROR'
            else:
                status = 'FAIL'
            
            test_case = TestCase(
                name=case_name,
                suite=suite_name,
                status=status,
                duration=test_result.get('duration', 0.0),
                error_message=test_result.get('error_message'),
                failure_message=test_result.get('error_message') if status == 'FAIL' else None,
                output=None,  # Not currently captured
                metrics=test_result.get('metrics')
            )
            
            test_cases.append(test_case)
        
        return test_cases
    
    def _generate_performance_charts(self, performance_metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate performance charts as base64 encoded images"""
        if not MATPLOTLIB_AVAILABLE:
            return {}
        
        charts = {}
        
        try:
            # Throughput chart
            if any('throughput' in str(v) for v in performance_metrics.values()):
                fig, ax = plt.subplots(figsize=(10, 6))
                
                operations = []
                throughputs = []
                
                for op_name, metrics in performance_metrics.items():
                    if isinstance(metrics, dict) and 'throughput' in metrics:
                        operations.append(op_name)
                        throughputs.append(metrics['throughput'])
                
                if operations and throughputs:
                    bars = ax.bar(operations, throughputs, color='skyblue')
                    ax.set_title('Operation Throughput')
                    ax.set_ylabel('Operations per Second')
                    ax.tick_params(axis='x', rotation=45)
                    
                    # Add value labels on bars
                    for bar in bars:
                        height = bar.get_height()
                        ax.annotate(f'{height:.1f}',
                                  xy=(bar.get_x() + bar.get_width() / 2, height),
                                  xytext=(0, 3),
                                  textcoords="offset points",
                                  ha='center', va='bottom')
                    
                    plt.tight_layout()
                    
                    # Convert to base64
                    import io
                    buffer = io.BytesIO()
                    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                    buffer.seek(0)
                    chart_data = base64.b64encode(buffer.read()).decode('utf-8')
                    charts['throughput'] = chart_data
                    
                plt.close(fig)
            
            # Latency chart
            latency_data = {}
            for op_name, metrics in performance_metrics.items():
                if isinstance(metrics, dict):
                    for latency_type in ['avg_latency', 'median_latency', 'p95_latency', 'p99_latency']:
                        if latency_type in metrics:
                            if latency_type not in latency_data:
                                latency_data[latency_type] = {}
                            latency_data[latency_type][op_name] = metrics[latency_type] * 1000  # Convert to ms
            
            if latency_data:
                fig, ax = plt.subplots(figsize=(12, 6))
                
                operations = list(next(iter(latency_data.values())).keys())
                x_pos = range(len(operations))
                width = 0.2
                
                colors = ['lightblue', 'lightgreen', 'orange', 'red']
                for i, (latency_type, values) in enumerate(latency_data.items()):
                    latencies = [values.get(op, 0) for op in operations]
                    ax.bar([x + width * i for x in x_pos], latencies, 
                          width, label=latency_type.replace('_', ' ').title(), 
                          color=colors[i % len(colors)])
                
                ax.set_title('Operation Latency Comparison')
                ax.set_ylabel('Latency (ms)')
                ax.set_xticks([x + width * 1.5 for x in x_pos])
                ax.set_xticklabels(operations, rotation=45)
                ax.legend()
                
                plt.tight_layout()
                
                # Convert to base64
                import io
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                chart_data = base64.b64encode(buffer.read()).decode('utf-8')
                charts['latency'] = chart_data
                
                plt.close(fig)
        
        except Exception as e:
            print(f"Error generating performance charts: {e}")
        
        return charts
    
    def _extract_coverage_data(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract code coverage data if available"""
        # Placeholder for coverage data extraction
        # This would typically integrate with coverage tools like gcov
        return {
            'line_coverage': 0.0,
            'branch_coverage': 0.0,
            'function_coverage': 0.0,
            'files': []
        }
    
    def _create_html_content(self, summary: TestSummary, test_cases: List[TestCase], 
                           charts: Dict[str, str], coverage: Dict[str, Any]) -> str:
        """Create HTML content for the report"""
        if JINJA2_AVAILABLE:
            template = Template(self.report_template)
            return template.render(
                summary=summary,
                test_cases=test_cases,
                charts=charts,
                coverage=coverage,
                generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        else:
            # Simple HTML without templating
            return self._create_simple_html(summary, test_cases, charts)
    
    def _create_simple_html(self, summary: TestSummary, test_cases: List[TestCase], 
                          charts: Dict[str, str]) -> str:
        """Create simple HTML report without templating engine"""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPU-6050 Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .summary-item {{ text-align: center; }}
        .summary-value {{ font-size: 24px; font-weight: bold; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .error {{ color: orange; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .chart {{ text-align: center; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>MPU-6050 Test Report</h1>
        <p>Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    
    <div class="summary">
        <div class="summary-item">
            <div class="summary-value">{summary.total_tests}</div>
            <div>Total Tests</div>
        </div>
        <div class="summary-item">
            <div class="summary-value pass">{summary.passed_tests}</div>
            <div>Passed</div>
        </div>
        <div class="summary-item">
            <div class="summary-value fail">{summary.failed_tests}</div>
            <div>Failed</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{summary.success_rate:.1f}%</div>
            <div>Success Rate</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{summary.total_duration:.2f}s</div>
            <div>Total Duration</div>
        </div>
    </div>
    
    <h2>Test Cases</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Suite</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Error</th>
        </tr>
"""
        
        for test_case in test_cases:
            status_class = test_case.status.lower()
            error_msg = test_case.error_message or test_case.failure_message or ''
            error_msg = error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
            
            html += f"""
        <tr>
            <td>{test_case.name}</td>
            <td>{test_case.suite}</td>
            <td class="{status_class}">{test_case.status}</td>
            <td>{test_case.duration:.3f}s</td>
            <td>{error_msg}</td>
        </tr>
"""
        
        html += """
    </table>
"""
        
        # Add charts if available
        for chart_name, chart_data in charts.items():
            html += f"""
    <div class="chart">
        <h3>{chart_name.replace('_', ' ').title()} Chart</h3>
        <img src="data:image/png;base64,{chart_data}" alt="{chart_name} chart">
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html
    
    def _analyze_performance_data(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance data and provide insights"""
        analysis = {
            'throughput_analysis': {},
            'latency_analysis': {},
            'trends': {},
            'bottlenecks': []
        }
        
        performance_metrics = test_results.get('performance_metrics', {})
        
        # Analyze throughput
        throughputs = []
        for metrics in performance_metrics.values():
            if isinstance(metrics, dict) and 'throughput' in metrics:
                throughputs.append(metrics['throughput'])
        
        if throughputs:
            analysis['throughput_analysis'] = {
                'average': sum(throughputs) / len(throughputs),
                'max': max(throughputs),
                'min': min(throughputs),
                'variance': sum((x - sum(throughputs) / len(throughputs))**2 for x in throughputs) / len(throughputs)
            }
        
        # Identify bottlenecks
        for op_name, metrics in performance_metrics.items():
            if isinstance(metrics, dict):
                if metrics.get('error_rate', 0) > 0.05:  # > 5% error rate
                    analysis['bottlenecks'].append(f"High error rate in {op_name}: {metrics['error_rate']:.1%}")
                
                if metrics.get('p99_latency', 0) > 0.1:  # > 100ms P99 latency
                    analysis['bottlenecks'].append(f"High P99 latency in {op_name}: {metrics['p99_latency']*1000:.1f}ms")
        
        return analysis
    
    def _analyze_resource_data(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resource usage data"""
        analysis = {
            'memory_analysis': {},
            'cpu_analysis': {},
            'resource_efficiency': {}
        }
        
        resource_metrics = test_results.get('resource_metrics', {})
        
        for process_name, metrics in resource_metrics.items():
            if isinstance(metrics, dict):
                analysis['memory_analysis'][process_name] = {
                    'max_memory_mb': metrics.get('max_memory_mb', 0),
                    'avg_memory_mb': metrics.get('avg_memory_mb', 0),
                    'memory_efficiency': 'Good' if metrics.get('max_memory_mb', 0) < 100 else 'Needs attention'
                }
                
                analysis['cpu_analysis'][process_name] = {
                    'max_cpu_percent': metrics.get('max_cpu_percent', 0),
                    'avg_cpu_percent': metrics.get('avg_cpu_percent', 0),
                    'cpu_efficiency': 'Good' if metrics.get('avg_cpu_percent', 0) < 50 else 'Needs attention'
                }
        
        return analysis
    
    def _generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Analyze test results
        test_run_info = test_results.get('test_run_info', {})
        failed_tests = test_run_info.get('failed_tests', 0)
        total_tests = test_run_info.get('total_tests', 0)
        
        if total_tests > 0:
            failure_rate = failed_tests / total_tests
            
            if failure_rate > 0.1:  # More than 10% failure rate
                recommendations.append("High test failure rate detected. Review failed test cases and fix underlying issues.")
            
            if failure_rate == 0:
                recommendations.append("Excellent! All tests passed. Consider adding more edge case tests.")
        
        # Analyze performance
        performance_metrics = test_results.get('performance_metrics', {})
        for op_name, metrics in performance_metrics.items():
            if isinstance(metrics, dict):
                if metrics.get('throughput', 0) < 50:  # Less than 50 ops/sec
                    recommendations.append(f"Low throughput detected for {op_name}. Consider optimizing the operation.")
                
                if metrics.get('error_rate', 0) > 0.02:  # More than 2% error rate
                    recommendations.append(f"High error rate for {op_name}. Investigate error conditions.")
        
        # Analyze resource usage
        resource_metrics = test_results.get('resource_metrics', {})
        for process_name, metrics in resource_metrics.items():
            if isinstance(metrics, dict):
                if metrics.get('max_memory_mb', 0) > 200:  # More than 200MB
                    recommendations.append(f"High memory usage detected for {process_name}. Check for memory leaks.")
                
                if metrics.get('avg_cpu_percent', 0) > 80:  # More than 80% CPU
                    recommendations.append(f"High CPU usage for {process_name}. Consider optimization.")
        
        if not recommendations:
            recommendations.append("All metrics look good! The system is performing well.")
        
        return recommendations
    
    def _get_html_template(self) -> str:
        """Get HTML template for report generation"""
        # This would typically be loaded from a file
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPU-6050 Test Report</title>
    <style>
        /* CSS styles would go here */
    </style>
</head>
<body>
    <!-- Template content would go here -->
</body>
</html>
"""