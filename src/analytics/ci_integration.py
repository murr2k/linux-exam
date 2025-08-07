#!/usr/bin/env python3
"""
CI/CD Integration for Test Analytics

Provides automated report generation, PR comment integration,
alert systems for quality degradation, and historical data persistence.
"""

import json
import os
import subprocess
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from dataclasses import dataclass, asdict

# Import our analytics modules
try:
    from .test_metrics_collector import TestMetricsCollector
    from .quality_analyzer import QualityAnalyzer
    from .performance_analyzer import PerformanceAnalyzer
except ImportError:
    # Fallback for direct execution
    from test_metrics_collector import TestMetricsCollector
    from quality_analyzer import QualityAnalyzer
    from performance_analyzer import PerformanceAnalyzer


@dataclass
class CIReport:
    """CI/CD integration report."""
    build_id: str
    commit_hash: str
    branch: str
    timestamp: datetime
    test_summary: Dict[str, Any]
    quality_gates: Dict[str, Any]
    performance_analysis: Dict[str, Any]
    recommendations: List[str]
    alerts: List[Dict[str, Any]]
    comparison_with_main: Optional[Dict[str, Any]] = None


@dataclass
class QualityGateResult:
    """Quality gate evaluation result."""
    gate_name: str
    status: str  # PASS, FAIL, WARN
    current_value: float
    threshold: float
    target: float
    message: str


class CIIntegration:
    """CI/CD integration for test analytics."""
    
    def __init__(self, db_path: str = "test_analytics.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()
        
        # Initialize analytics components
        self.metrics_collector = TestMetricsCollector(db_path)
        self.quality_analyzer = QualityAnalyzer(db_path)
        self.performance_analyzer = PerformanceAnalyzer(db_path)
        
        # CI/CD configuration
        self.config = self._load_ci_config()
        
        # Quality gates configuration
        self.quality_gates = {
            'code_coverage': {
                'min_threshold': 80.0,
                'target_threshold': 90.0,
                'weight': 0.3
            },
            'test_success_rate': {
                'min_threshold': 95.0,
                'target_threshold': 99.0,
                'weight': 0.25
            },
            'performance_regression': {
                'max_threshold': 1.2,  # Max 20% slower
                'target_threshold': 1.05,  # Target <5% slower
                'weight': 0.25
            },
            'test_quality_score': {
                'min_threshold': 0.7,
                'target_threshold': 0.85,
                'weight': 0.2
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('CIIntegration')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_ci_config(self) -> Dict[str, Any]:
        """Load CI/CD configuration."""
        default_config = {
            'github': {
                'enabled': os.getenv('GITHUB_INTEGRATION_ENABLED', 'false').lower() == 'true',
                'token': os.getenv('GITHUB_TOKEN'),
                'repo': os.getenv('GITHUB_REPOSITORY'),
                'pr_comments_enabled': True
            },
            'slack': {
                'enabled': os.getenv('SLACK_INTEGRATION_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.getenv('SLACK_WEBHOOK_URL'),
                'channel': os.getenv('SLACK_CHANNEL', '#test-alerts')
            },
            'email': {
                'enabled': os.getenv('EMAIL_ALERTS_ENABLED', 'false').lower() == 'true',
                'smtp_host': os.getenv('SMTP_HOST'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'username': os.getenv('SMTP_USERNAME'),
                'password': os.getenv('SMTP_PASSWORD'),
                'recipients': os.getenv('ALERT_RECIPIENTS', '').split(',')
            },
            'reports': {
                'output_directory': os.getenv('REPORT_OUTPUT_DIR', 'test-reports'),
                'formats': ['json', 'html', 'junit'],
                'retention_days': int(os.getenv('REPORT_RETENTION_DAYS', '30'))
            }
        }
        
        # Try to load from file if exists
        config_file = Path('ci_config.json')
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                # Merge with default config
                default_config.update(file_config)
            except Exception as e:
                self.logger.warning(f"Could not load CI config file: {e}")
        
        return default_config
    
    def generate_ci_report(self, build_id: str, commit_hash: str, 
                          branch: str = "main") -> CIReport:
        """Generate comprehensive CI report."""
        self.logger.info(f"Generating CI report for build {build_id}")
        
        # Get test summary
        test_summary = self._get_test_summary()
        
        # Evaluate quality gates
        quality_gates = self._evaluate_quality_gates()
        
        # Get performance analysis
        performance_analysis = self._get_performance_analysis()
        
        # Generate recommendations
        recommendations = self._generate_ci_recommendations(
            test_summary, quality_gates, performance_analysis
        )
        
        # Get alerts
        alerts = self._get_critical_alerts()
        
        # Compare with main branch (if not on main)
        comparison_with_main = None
        if branch != "main":
            comparison_with_main = self._compare_with_main_branch()
        
        report = CIReport(
            build_id=build_id,
            commit_hash=commit_hash,
            branch=branch,
            timestamp=datetime.now(),
            test_summary=test_summary,
            quality_gates=quality_gates,
            performance_analysis=performance_analysis,
            recommendations=recommendations,
            alerts=alerts,
            comparison_with_main=comparison_with_main
        )
        
        # Store report
        self._store_ci_report(report)
        
        return report
    
    def _get_test_summary(self) -> Dict[str, Any]:
        """Get test execution summary for CI."""
        health_metrics = self.metrics_collector.get_system_health_metrics()
        
        # Get coverage data
        coverage_trends = self.metrics_collector.get_coverage_trends(days=1)
        latest_coverage = coverage_trends[0] if coverage_trends else {
            'function_coverage': 0, 'branch_coverage': 0, 'line_coverage': 0
        }
        
        return {
            'total_tests': health_metrics.get('total_test_types', 0),
            'tests_executed': health_metrics.get('total_tests_executed', 0),
            'success_rate': health_metrics.get('overall_success_rate', 0),
            'reliable_tests': health_metrics.get('reliable_tests_count', 0),
            'coverage': {
                'function': latest_coverage.get('function_coverage', 0),
                'branch': latest_coverage.get('branch_coverage', 0),
                'line': latest_coverage.get('line_coverage', 0),
                'average': (
                    latest_coverage.get('function_coverage', 0) +
                    latest_coverage.get('branch_coverage', 0) +
                    latest_coverage.get('line_coverage', 0)
                ) / 3
            }
        }
    
    def _evaluate_quality_gates(self) -> Dict[str, QualityGateResult]:
        """Evaluate all quality gates."""
        results = {}
        
        # Get test summary for evaluation
        test_summary = self._get_test_summary()
        
        # Coverage gate
        avg_coverage = test_summary['coverage']['average']
        coverage_gate = self.quality_gates['code_coverage']
        
        if avg_coverage >= coverage_gate['target_threshold']:
            status = 'PASS'
            message = f"Excellent coverage: {avg_coverage:.1f}%"
        elif avg_coverage >= coverage_gate['min_threshold']:
            status = 'WARN'
            message = f"Coverage meets minimum: {avg_coverage:.1f}%"
        else:
            status = 'FAIL'
            message = f"Coverage below minimum: {avg_coverage:.1f}%"
        
        results['code_coverage'] = QualityGateResult(
            gate_name='code_coverage',
            status=status,
            current_value=avg_coverage,
            threshold=coverage_gate['min_threshold'],
            target=coverage_gate['target_threshold'],
            message=message
        )
        
        # Success rate gate
        success_rate = test_summary['success_rate']
        success_gate = self.quality_gates['test_success_rate']
        
        if success_rate >= success_gate['target_threshold']:
            status = 'PASS'
            message = f"Excellent test reliability: {success_rate:.1f}%"
        elif success_rate >= success_gate['min_threshold']:
            status = 'WARN'
            message = f"Test reliability acceptable: {success_rate:.1f}%"
        else:
            status = 'FAIL'
            message = f"Test reliability below threshold: {success_rate:.1f}%"
        
        results['test_success_rate'] = QualityGateResult(
            gate_name='test_success_rate',
            status=status,
            current_value=success_rate,
            threshold=success_gate['min_threshold'],
            target=success_gate['target_threshold'],
            message=message
        )
        
        # Performance regression gate
        avg_regression_factor = self._get_average_regression_factor()
        perf_gate = self.quality_gates['performance_regression']
        
        if avg_regression_factor <= perf_gate['target_threshold']:
            status = 'PASS'
            message = f"Performance stable: {avg_regression_factor:.2f}x"
        elif avg_regression_factor <= perf_gate['max_threshold']:
            status = 'WARN'
            message = f"Minor performance regression: {avg_regression_factor:.2f}x"
        else:
            status = 'FAIL'
            message = f"Significant performance regression: {avg_regression_factor:.2f}x"
        
        results['performance_regression'] = QualityGateResult(
            gate_name='performance_regression',
            status=status,
            current_value=avg_regression_factor,
            threshold=perf_gate['max_threshold'],
            target=perf_gate['target_threshold'],
            message=message
        )
        
        return results
    
    def _get_average_regression_factor(self) -> float:
        """Get average regression factor across all tests."""
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT AVG(regression_factor) FROM regression_alerts 
                    WHERE timestamp > ? AND resolved = FALSE
                ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
                
                result = cursor.fetchone()
                return result[0] if result[0] else 1.0
        except Exception as e:
            self.logger.warning(f"Could not get regression factor: {e}")
            return 1.0
    
    def _get_performance_analysis(self) -> Dict[str, Any]:
        """Get performance analysis for CI report."""
        # Get resource trends
        resource_trends = self.performance_analyzer.analyze_resource_trends(7)
        
        # Summarize trends
        trending_up = len([t for t in resource_trends 
                          if t.trend_direction == 'INCREASING' and t.trend_strength > 0.7])
        trending_down = len([t for t in resource_trends 
                           if t.trend_direction == 'DECREASING' and t.trend_strength > 0.7])
        stable = len([t for t in resource_trends 
                     if t.trend_direction == 'STABLE' or t.trend_strength <= 0.7])
        
        return {
            'total_metrics_analyzed': len(resource_trends),
            'trending_up': trending_up,
            'trending_down': trending_down,
            'stable': stable,
            'performance_concerns': trending_up > len(resource_trends) * 0.3,
            'top_concerns': [
                {
                    'resource': t.resource_type,
                    'trend_strength': t.trend_strength,
                    'current_avg': t.current_average,
                    'projected': t.projected_usage
                }
                for t in sorted(resource_trends, 
                              key=lambda x: x.trend_strength if x.trend_direction == 'INCREASING' else 0,
                              reverse=True)[:5]
            ]
        }
    
    def _generate_ci_recommendations(self, test_summary: Dict[str, Any],
                                   quality_gates: Dict[str, QualityGateResult],
                                   performance_analysis: Dict[str, Any]) -> List[str]:
        """Generate CI-specific recommendations."""
        recommendations = []
        
        # Quality gate failures
        failed_gates = [gate for gate in quality_gates.values() if gate.status == 'FAIL']
        if failed_gates:
            recommendations.append(
                f"🚨 {len(failed_gates)} quality gate(s) failed. "
                f"Consider blocking deployment until resolved."
            )
        
        # Coverage recommendations
        if test_summary['coverage']['average'] < 85:
            recommendations.append(
                f"📈 Increase code coverage from {test_summary['coverage']['average']:.1f}% "
                f"to at least 85% before merging."
            )
        
        # Performance concerns
        if performance_analysis.get('performance_concerns'):
            recommendations.append(
                "⚡ Performance regression detected. "
                "Review recent changes for optimization opportunities."
            )
        
        # Test reliability
        if test_summary['success_rate'] < 98:
            recommendations.append(
                f"🔧 Improve test reliability from {test_summary['success_rate']:.1f}% "
                f"to reduce flaky test impact."
            )
        
        return recommendations
    
    def _get_critical_alerts(self) -> List[Dict[str, Any]]:
        """Get critical alerts for CI report."""
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT test_name, alert_level, regression_factor, timestamp
                    FROM regression_alerts 
                    WHERE resolved = FALSE AND alert_level IN ('CRITICAL', 'MAJOR')
                    AND timestamp > ?
                    ORDER BY regression_factor DESC
                    LIMIT 10
                ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
                
                return [{
                    'test_name': row[0],
                    'level': row[1],
                    'regression_factor': row[2],
                    'timestamp': row[3],
                    'type': 'performance_regression'
                } for row in cursor.fetchall()]
        except Exception as e:
            self.logger.warning(f"Could not get alerts: {e}")
            return []
    
    def _compare_with_main_branch(self) -> Dict[str, Any]:
        """Compare current branch metrics with main branch."""
        # This would typically compare with stored main branch metrics
        # For now, return a placeholder comparison
        return {
            'coverage_delta': 0.0,
            'performance_delta': 1.0,
            'new_test_failures': 0,
            'resolved_test_failures': 0,
            'recommendation': "Branch metrics comparable to main"
        }
    
    def _store_ci_report(self, report: CIReport):
        """Store CI report in database."""
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS ci_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        build_id TEXT NOT NULL,
                        commit_hash TEXT NOT NULL,
                        branch TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        report_data TEXT NOT NULL
                    )
                ''')
                
                conn.execute('''
                    INSERT INTO ci_reports (build_id, commit_hash, branch, timestamp, report_data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    report.build_id,
                    report.commit_hash,
                    report.branch,
                    report.timestamp.isoformat(),
                    json.dumps(asdict(report), default=str)
                ))
                
                self.logger.info(f"Stored CI report for build {report.build_id}")
        except Exception as e:
            self.logger.error(f"Failed to store CI report: {e}")
    
    def post_github_pr_comment(self, pr_number: int, report: CIReport) -> bool:
        """Post test analytics comment to GitHub PR."""
        if not self.config['github']['enabled']:
            self.logger.info("GitHub integration disabled")
            return False
        
        # Generate markdown comment
        comment = self._generate_pr_comment_markdown(report)
        
        try:
            headers = {
                'Authorization': f"token {self.config['github']['token']}",
                'Accept': 'application/vnd.github.v3+json'
            }
            
            url = f"https://api.github.com/repos/{self.config['github']['repo']}/issues/{pr_number}/comments"
            
            response = requests.post(url, 
                                   headers=headers,
                                   json={'body': comment})
            
            if response.status_code == 201:
                self.logger.info(f"Posted PR comment for build {report.build_id}")
                return True
            else:
                self.logger.error(f"Failed to post PR comment: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error posting GitHub comment: {e}")
            return False
    
    def _generate_pr_comment_markdown(self, report: CIReport) -> str:
        """Generate markdown comment for PR."""
        # Count gate statuses
        gate_results = report.quality_gates
        passed_gates = len([g for g in gate_results.values() if g.status == 'PASS'])
        failed_gates = len([g for g in gate_results.values() if g.status == 'FAIL'])
        warning_gates = len([g for g in gate_results.values() if g.status == 'WARN'])
        
        # Overall status
        if failed_gates > 0:
            overall_status = "❌ Failed"
            status_emoji = "❌"
        elif warning_gates > 0:
            overall_status = "⚠️ Warning"
            status_emoji = "⚠️"
        else:
            overall_status = "✅ Passed"
            status_emoji = "✅"
        
        comment = f"""## {status_emoji} Test Analytics Report
        
**Build:** `{report.build_id}` | **Commit:** `{report.commit_hash[:8]}` | **Branch:** `{report.branch}`

### Quality Gates ({passed_gates} passed, {warning_gates} warning, {failed_gates} failed)

"""
        
        # Quality gates table
        comment += "| Gate | Status | Current | Threshold | Target |\n"
        comment += "|------|--------|---------|-----------|--------|\n"
        
        for gate_name, gate_result in gate_results.items():
            status_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[gate_result.status]
            comment += f"| {gate_name.replace('_', ' ').title()} | {status_icon} {gate_result.status} | {gate_result.current_value:.2f} | {gate_result.threshold:.2f} | {gate_result.target:.2f} |\n"
        
        # Test summary
        comment += f"""
### Test Summary

- **Tests Executed:** {report.test_summary['tests_executed']}
- **Success Rate:** {report.test_summary['success_rate']:.1f}%
- **Code Coverage:** {report.test_summary['coverage']['average']:.1f}%
  - Function: {report.test_summary['coverage']['function']:.1f}%
  - Branch: {report.test_summary['coverage']['branch']:.1f}%
  - Line: {report.test_summary['coverage']['line']:.1f}%

"""
        
        # Alerts
        if report.alerts:
            comment += "### 🚨 Active Alerts\n\n"
            for alert in report.alerts[:5]:  # Show top 5
                comment += f"- **{alert['test_name']}**: {alert['level']} - {alert.get('regression_factor', 'N/A')}x regression\n"
            comment += "\n"
        
        # Recommendations
        if report.recommendations:
            comment += "### 💡 Recommendations\n\n"
            for rec in report.recommendations[:5]:  # Show top 5
                comment += f"- {rec}\n"
            comment += "\n"
        
        # Performance analysis
        if report.performance_analysis.get('performance_concerns'):
            comment += "### ⚡ Performance Concerns\n\n"
            for concern in report.performance_analysis.get('top_concerns', [])[:3]:
                comment += f"- **{concern['resource']}**: Trending up (strength: {concern['trend_strength']:.2f})\n"
            comment += "\n"
        
        comment += f"---\n*Generated by Test Analytics System at {report.timestamp.isoformat()}*"
        
        return comment
    
    def send_slack_alert(self, message: str, level: str = "info") -> bool:
        """Send alert to Slack."""
        if not self.config['slack']['enabled']:
            return False
        
        color_map = {
            'info': '#36a64f',
            'warning': '#ff9900',
            'error': '#ff0000',
            'critical': '#ff0000'
        }
        
        payload = {
            'channel': self.config['slack']['channel'],
            'attachments': [{
                'color': color_map.get(level, '#36a64f'),
                'title': f"Test Analytics Alert - {level.upper()}",
                'text': message,
                'footer': 'Test Analytics System',
                'ts': int(datetime.now().timestamp())
            }]
        }
        
        try:
            response = requests.post(self.config['slack']['webhook_url'], 
                                   json=payload)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def export_junit_xml(self, report: CIReport, output_path: str):
        """Export test results in JUnit XML format."""
        junit_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="TestAnalytics" tests="{len(report.quality_gates)}" failures="{len([g for g in report.quality_gates.values() if g.status == 'FAIL'])}" time="0">
    <testsuite name="QualityGates" tests="{len(report.quality_gates)}">
'''
        
        for gate_name, gate_result in report.quality_gates.items():
            if gate_result.status == 'FAIL':
                junit_xml += f'''        <testcase name="{gate_name}" classname="QualityGates">
            <failure message="{gate_result.message}">
                Current: {gate_result.current_value}, Threshold: {gate_result.threshold}
            </failure>
        </testcase>
'''
            else:
                junit_xml += f'''        <testcase name="{gate_name}" classname="QualityGates"/>
'''
        
        junit_xml += '''    </testsuite>
</testsuites>'''
        
        with open(output_path, 'w') as f:
            f.write(junit_xml)
        
        self.logger.info(f"Exported JUnit XML to {output_path}")
    
    def export_html_report(self, report: CIReport, output_path: str):
        """Export HTML report."""
        html_report = f'''<!DOCTYPE html>
<html>
<head>
    <title>Test Analytics Report - Build {report.build_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .gate-pass {{ color: #28a745; }}
        .gate-warn {{ color: #ffc107; }}
        .gate-fail {{ color: #dc3545; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .alert {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .alert-critical {{ background: #f8d7da; border: 1px solid #f5c6cb; }}
        .alert-warning {{ background: #fff3cd; border: 1px solid #ffeaa7; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Analytics Report</h1>
        <p><strong>Build:</strong> {report.build_id}</p>
        <p><strong>Commit:</strong> {report.commit_hash}</p>
        <p><strong>Branch:</strong> {report.branch}</p>
        <p><strong>Generated:</strong> {report.timestamp.isoformat()}</p>
    </div>
    
    <h2>Quality Gates</h2>
    <table>
        <tr><th>Gate</th><th>Status</th><th>Current</th><th>Threshold</th><th>Target</th><th>Message</th></tr>
'''
        
        for gate_name, gate_result in report.quality_gates.items():
            status_class = f"gate-{gate_result.status.lower()}"
            html_report += f'''        <tr>
            <td>{gate_name.replace('_', ' ').title()}</td>
            <td class="{status_class}">{gate_result.status}</td>
            <td>{gate_result.current_value:.2f}</td>
            <td>{gate_result.threshold:.2f}</td>
            <td>{gate_result.target:.2f}</td>
            <td>{gate_result.message}</td>
        </tr>
'''
        
        html_report += '''    </table>
    
    <h2>Test Summary</h2>
    <ul>
'''
        
        summary = report.test_summary
        html_report += f'''        <li><strong>Tests Executed:</strong> {summary['tests_executed']}</li>
        <li><strong>Success Rate:</strong> {summary['success_rate']:.1f}%</li>
        <li><strong>Code Coverage:</strong> {summary['coverage']['average']:.1f}%</li>
    </ul>
'''
        
        if report.recommendations:
            html_report += '''    <h2>Recommendations</h2>
    <ul>
'''
            for rec in report.recommendations:
                html_report += f"        <li>{rec}</li>\n"
            html_report += "    </ul>\n"
        
        html_report += '''</body>
</html>'''
        
        with open(output_path, 'w') as f:
            f.write(html_report)
        
        self.logger.info(f"Exported HTML report to {output_path}")
    
    def run_ci_pipeline(self, build_id: str, commit_hash: str, 
                       branch: str = "main", pr_number: Optional[int] = None) -> bool:
        """Run complete CI pipeline integration."""
        self.logger.info(f"Running CI pipeline for build {build_id}")
        
        try:
            # Generate report
            report = self.generate_ci_report(build_id, commit_hash, branch)
            
            # Create output directory
            output_dir = Path(self.config['reports']['output_directory'])
            output_dir.mkdir(exist_ok=True)
            
            # Export reports in different formats
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if 'json' in self.config['reports']['formats']:
                json_path = output_dir / f"report_{build_id}_{timestamp}.json"
                with open(json_path, 'w') as f:
                    json.dump(asdict(report), f, indent=2, default=str)
            
            if 'html' in self.config['reports']['formats']:
                html_path = output_dir / f"report_{build_id}_{timestamp}.html"
                self.export_html_report(report, str(html_path))
            
            if 'junit' in self.config['reports']['formats']:
                junit_path = output_dir / f"junit_{build_id}_{timestamp}.xml"
                self.export_junit_xml(report, str(junit_path))
            
            # Post PR comment if this is a PR build
            if pr_number and self.config['github']['pr_comments_enabled']:
                self.post_github_pr_comment(pr_number, report)
            
            # Send alerts if quality gates failed
            failed_gates = [g for g in report.quality_gates.values() if g.status == 'FAIL']
            if failed_gates:
                alert_message = f"Quality gates failed for build {build_id}: {', '.join([g.gate_name for g in failed_gates])}"
                self.send_slack_alert(alert_message, 'error')
            
            # Determine if build should pass
            critical_failures = len([g for g in report.quality_gates.values() 
                                   if g.status == 'FAIL' and g.gate_name in ['code_coverage', 'test_success_rate']])
            
            build_passed = critical_failures == 0
            
            self.logger.info(f"CI pipeline completed for build {build_id}: {'PASSED' if build_passed else 'FAILED'}")
            return build_passed
            
        except Exception as e:
            self.logger.error(f"CI pipeline failed: {e}")
            return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CI/CD Integration for Test Analytics")
    parser.add_argument("--build-id", required=True, help="Build ID")
    parser.add_argument("--commit", required=True, help="Commit hash")
    parser.add_argument("--branch", default="main", help="Branch name")
    parser.add_argument("--pr-number", type=int, help="PR number for GitHub integration")
    
    args = parser.parse_args()
    
    ci_integration = CIIntegration()
    success = ci_integration.run_ci_pipeline(
        args.build_id, 
        args.commit, 
        args.branch, 
        args.pr_number
    )
    
    exit(0 if success else 1)