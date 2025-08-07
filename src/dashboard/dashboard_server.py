#!/usr/bin/env python3
"""
Real-time Test Analytics Dashboard Server

Provides real-time test status dashboards, historical trend visualization,
quality gate status reporting, and actionable recommendation system.
"""

import json
import sqlite3
import asyncio
import aiofiles
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from dataclasses import asdict

# Web framework imports
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import plotly.graph_objs as go
import plotly.utils

# Import our analytics modules
import sys
sys.path.append(str(Path(__file__).parent.parent / 'analytics'))
from test_metrics_collector import TestMetricsCollector, TestMetrics
from quality_analyzer import QualityAnalyzer, QualityScore
from performance_analyzer import PerformanceAnalyzer, RegressionResult


class DashboardServer:
    """Real-time test analytics dashboard server."""
    
    def __init__(self, db_path: str = "test_analytics.db", port: int = 5000):
        self.db_path = db_path
        self.port = port
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                        template_folder=str(Path(__file__).parent / 'templates'),
                        static_folder=str(Path(__file__).parent / 'static'))
        self.app.config['SECRET_KEY'] = 'test_analytics_dashboard_secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Initialize analytics components
        self.metrics_collector = TestMetricsCollector(db_path)
        self.quality_analyzer = QualityAnalyzer(db_path)
        self.performance_analyzer = PerformanceAnalyzer(db_path)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Quality gates configuration
        self.quality_gates = {
            'coverage': {'min': 80.0, 'target': 90.0},
            'success_rate': {'min': 95.0, 'target': 99.0},
            'performance_regression': {'max': 1.2, 'target': 1.05},
            'test_quality': {'min': 0.7, 'target': 0.85}
        }
        
        # Register routes
        self._register_routes()
        self._register_socket_events()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('DashboardServer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _register_routes(self):
        """Register Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('dashboard.html')
        
        @self.app.route('/api/overview')
        def api_overview():
            """Get dashboard overview data."""
            try:
                overview = self._get_overview_data()
                return jsonify(overview)
            except Exception as e:
                self.logger.error(f"Error getting overview data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/test_metrics/<test_name>')
        def api_test_metrics(test_name: str):
            """Get detailed metrics for a specific test."""
            try:
                days = request.args.get('days', 30, type=int)
                metrics = self._get_test_detailed_metrics(test_name, days)
                return jsonify(metrics)
            except Exception as e:
                self.logger.error(f"Error getting test metrics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/performance_trends')
        def api_performance_trends():
            """Get performance trend data."""
            try:
                days = request.args.get('days', 30, type=int)
                trends = self._get_performance_trends(days)
                return jsonify(trends)
            except Exception as e:
                self.logger.error(f"Error getting performance trends: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/quality_gates')
        def api_quality_gates():
            """Get quality gate status."""
            try:
                gates = self._get_quality_gates_status()
                return jsonify(gates)
            except Exception as e:
                self.logger.error(f"Error getting quality gates: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/recommendations')
        def api_recommendations():
            """Get actionable recommendations."""
            try:
                recommendations = self._get_recommendations()
                return jsonify(recommendations)
            except Exception as e:
                self.logger.error(f"Error getting recommendations: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/alerts')
        def api_alerts():
            """Get active alerts."""
            try:
                alerts = self._get_active_alerts()
                return jsonify(alerts)
            except Exception as e:
                self.logger.error(f"Error getting alerts: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/coverage_trends')
        def api_coverage_trends():
            """Get coverage trend charts."""
            try:
                days = request.args.get('days', 30, type=int)
                trends = self._get_coverage_trend_charts(days)
                return jsonify(trends)
            except Exception as e:
                self.logger.error(f"Error getting coverage trends: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health')
        def health_check():
            """Health check endpoint."""
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    
    def _register_socket_events(self):
        """Register Socket.IO events for real-time updates."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            self.logger.info(f"Client connected: {request.sid}")
            emit('connected', {'data': 'Connected to dashboard'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            self.logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('subscribe_test')
        def handle_subscribe_test(data):
            """Handle test subscription for real-time updates."""
            test_name = data.get('test_name')
            if test_name:
                # Add client to test-specific room
                # This would be implemented with proper room management
                self.logger.info(f"Client {request.sid} subscribed to {test_name}")
    
    def _start_background_tasks(self):
        """Start background tasks for real-time updates."""
        
        @self.socketio.on('start_monitoring')
        def start_monitoring():
            """Start real-time monitoring."""
            # This would start a background task to emit updates
            self.logger.info("Started real-time monitoring")
    
    def _get_overview_data(self) -> Dict[str, Any]:
        """Get dashboard overview data."""
        # Get system health metrics
        health_metrics = self.metrics_collector.get_system_health_metrics()
        
        # Get recent quality gates status
        quality_gates = self._get_quality_gates_status()
        
        # Get active alerts count
        alerts = self._get_active_alerts()
        
        # Get test execution summary
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(DISTINCT test_name) as total_tests,
                       COUNT(*) as total_executions,
                       SUM(CASE WHEN status = 'PASSED' THEN 1 ELSE 0 END) as passed,
                       AVG(execution_time) as avg_time
                FROM test_executions 
                WHERE timestamp > ?
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
            
            test_summary = cursor.fetchone()
        
        return {
            'system_health': health_metrics,
            'quality_gates': quality_gates,
            'alerts': {
                'total': len(alerts),
                'critical': len([a for a in alerts if a.get('level') == 'CRITICAL']),
                'warnings': len([a for a in alerts if a.get('level') in ['WARNING', 'MAJOR']])
            },
            'test_summary': {
                'total_tests': test_summary[0] if test_summary[0] else 0,
                'total_executions': test_summary[1] if test_summary[1] else 0,
                'success_rate': (test_summary[2] / test_summary[1] * 100) if test_summary[1] else 0,
                'average_execution_time': test_summary[3] if test_summary[3] else 0
            },
            'last_updated': datetime.now().isoformat()
        }
    
    def _get_test_detailed_metrics(self, test_name: str, days: int) -> Dict[str, Any]:
        """Get detailed metrics for a specific test."""
        # Get test metrics
        metrics = self.metrics_collector.get_test_metrics(test_name, days)
        
        # Get quality trends
        quality_trends = self.quality_analyzer.get_quality_trends(test_name, days)
        
        # Get performance statistics
        perf_stats = self.performance_analyzer.get_performance_statistics(test_name, days)
        
        # Get regression analysis
        regression = self.performance_analyzer.detect_performance_regression(test_name)
        
        # Get recommendations
        recommendations = self.quality_analyzer.get_quality_recommendations(test_name)
        
        return {
            'test_metrics': asdict(metrics) if metrics else None,
            'quality_trends': [
                {**trend, 'timestamp': trend['timestamp'].isoformat()} 
                for trend in quality_trends
            ],
            'performance_stats': perf_stats,
            'regression_analysis': asdict(regression),
            'recommendations': recommendations
        }
    
    def _get_performance_trends(self, days: int) -> Dict[str, Any]:
        """Get performance trend data for charts."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT test_name, execution_time, cpu_usage, memory_usage, timestamp
                FROM performance_metrics 
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            ''', (cutoff_date,))
            
            data = cursor.fetchall()
        
        # Group by test name
        test_trends = {}
        for row in data:
            test_name, exec_time, cpu_usage, memory_usage, timestamp = row
            if test_name not in test_trends:
                test_trends[test_name] = {
                    'timestamps': [],
                    'execution_times': [],
                    'cpu_usage': [],
                    'memory_usage': []
                }
            
            test_trends[test_name]['timestamps'].append(timestamp)
            test_trends[test_name]['execution_times'].append(exec_time)
            test_trends[test_name]['cpu_usage'].append(cpu_usage)
            test_trends[test_name]['memory_usage'].append(memory_usage)
        
        return test_trends
    
    def _get_quality_gates_status(self) -> Dict[str, Any]:
        """Get quality gates status."""
        gates_status = {}
        
        # Coverage gate
        coverage_trends = self.metrics_collector.get_coverage_trends(days=7)
        if coverage_trends:
            latest_coverage = coverage_trends[0]
            avg_coverage = (
                latest_coverage['function_coverage'] + 
                latest_coverage['branch_coverage'] + 
                latest_coverage['line_coverage']
            ) / 3
            
            gates_status['coverage'] = {
                'current_value': avg_coverage,
                'threshold': self.quality_gates['coverage']['min'],
                'target': self.quality_gates['coverage']['target'],
                'status': 'PASS' if avg_coverage >= self.quality_gates['coverage']['min'] else 'FAIL',
                'trend': 'STABLE'  # Would calculate actual trend
            }
        
        # Success rate gate
        health_metrics = self.metrics_collector.get_system_health_metrics()
        success_rate = health_metrics.get('overall_success_rate', 0)
        
        gates_status['success_rate'] = {
            'current_value': success_rate,
            'threshold': self.quality_gates['success_rate']['min'],
            'target': self.quality_gates['success_rate']['target'],
            'status': 'PASS' if success_rate >= self.quality_gates['success_rate']['min'] else 'FAIL',
            'trend': 'STABLE'
        }
        
        # Performance regression gate
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT AVG(regression_factor) FROM regression_alerts 
                WHERE timestamp > ? AND resolved = FALSE
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
            
            result = cursor.fetchone()
            avg_regression = result[0] if result[0] else 1.0
        
        gates_status['performance_regression'] = {
            'current_value': avg_regression,
            'threshold': self.quality_gates['performance_regression']['max'],
            'target': self.quality_gates['performance_regression']['target'],
            'status': 'PASS' if avg_regression <= self.quality_gates['performance_regression']['max'] else 'FAIL',
            'trend': 'STABLE'
        }
        
        return gates_status
    
    def _get_recommendations(self) -> List[Dict[str, Any]]:
        """Get actionable recommendations."""
        recommendations = []
        
        # Get all test names
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT DISTINCT test_name FROM test_executions 
                WHERE timestamp > ?
                LIMIT 20
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
            
            test_names = [row[0] for row in cursor.fetchall()]
        
        # Get quality recommendations for each test
        for test_name in test_names[:10]:  # Limit to top 10
            test_recommendations = self.quality_analyzer.get_quality_recommendations(test_name)
            
            for rec in test_recommendations:
                if "improve" in rec.lower() or "add" in rec.lower() or "enhance" in rec.lower():
                    recommendations.append({
                        'test_name': test_name,
                        'type': 'quality',
                        'priority': 'medium',
                        'description': rec,
                        'category': 'test_improvement'
                    })
        
        # Get performance recommendations
        resource_trends = self.performance_analyzer.analyze_resource_trends(7)
        for trend in resource_trends[:5]:  # Top 5 trends
            if trend.trend_direction == 'INCREASING' and trend.trend_strength > 0.7:
                recommendations.append({
                    'test_name': trend.resource_type.split('_')[0],
                    'type': 'performance',
                    'priority': 'high' if trend.trend_strength > 0.9 else 'medium',
                    'description': f"Resource usage trending upward: {trend.resource_type}",
                    'category': 'performance_optimization'
                })
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return recommendations[:20]  # Return top 20
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts."""
        alerts = []
        
        # Get regression alerts
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT test_name, alert_level, regression_factor, timestamp
                FROM regression_alerts 
                WHERE resolved = FALSE AND timestamp > ?
                ORDER BY regression_factor DESC
            ''', ((datetime.now() - timedelta(days=30)).isoformat(),))
            
            for row in cursor.fetchall():
                alerts.append({
                    'test_name': row[0],
                    'type': 'performance_regression',
                    'level': row[1],
                    'message': f"Performance regression detected: {row[2]:.2f}x slower",
                    'timestamp': row[3],
                    'details': {
                        'regression_factor': row[2]
                    }
                })
        
        # Get quality alerts (tests with very low scores)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT test_name, overall_score, timestamp
                FROM test_quality_scores 
                WHERE overall_score < 0.5 AND timestamp > ?
                ORDER BY overall_score ASC
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
            
            for row in cursor.fetchall():
                alerts.append({
                    'test_name': row[0],
                    'type': 'quality',
                    'level': 'WARNING',
                    'message': f"Low test quality score: {row[1]:.2f}",
                    'timestamp': row[2],
                    'details': {
                        'quality_score': row[1]
                    }
                })
        
        return alerts[:50]  # Limit to 50 most recent
    
    def _get_coverage_trend_charts(self, days: int) -> Dict[str, Any]:
        """Get coverage trend charts data."""
        trends = self.metrics_collector.get_coverage_trends(days)
        
        # Prepare data for Plotly charts
        timestamps = [trend['timestamp'].isoformat() for trend in trends]
        function_coverage = [trend['function_coverage'] for trend in trends]
        branch_coverage = [trend['branch_coverage'] for trend in trends]
        line_coverage = [trend['line_coverage'] for trend in trends]
        
        # Create Plotly figure
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=function_coverage,
            mode='lines+markers',
            name='Function Coverage',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=branch_coverage,
            mode='lines+markers',
            name='Branch Coverage',
            line=dict(color='red')
        ))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=line_coverage,
            mode='lines+markers',
            name='Line Coverage',
            line=dict(color='green')
        ))
        
        fig.update_layout(
            title='Code Coverage Trends',
            xaxis_title='Time',
            yaxis_title='Coverage (%)',
            hovermode='x unified'
        )
        
        return {
            'chart_json': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
            'summary': {
                'latest_function_coverage': function_coverage[0] if function_coverage else 0,
                'latest_branch_coverage': branch_coverage[0] if branch_coverage else 0,
                'latest_line_coverage': line_coverage[0] if line_coverage else 0,
                'trend_points': len(timestamps)
            }
        }
    
    def run(self, debug: bool = False):
        """Run the dashboard server."""
        self.logger.info(f"Starting dashboard server on port {self.port}")
        self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=debug)


# Create dashboard templates
def create_dashboard_templates():
    """Create HTML templates for the dashboard."""
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Main dashboard template
    dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Analytics Dashboard</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .metric-card {
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
        }
        .alert-critical { border-left: 4px solid #dc3545; }
        .alert-warning { border-left: 4px solid #ffc107; }
        .alert-info { border-left: 4px solid #17a2b8; }
        .quality-gate-pass { color: #28a745; }
        .quality-gate-fail { color: #dc3545; }
        .trend-up { color: #28a745; }
        .trend-down { color: #dc3545; }
        .trend-stable { color: #6c757d; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="#">Test Analytics Dashboard</a>
            <span class="navbar-text" id="last-updated"></span>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <!-- Overview Cards -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Success Rate</h5>
                        <h2 class="text-success" id="success-rate">--</h2>
                        <small class="text-muted">Last 7 days</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Total Tests</h5>
                        <h2 class="text-primary" id="total-tests">--</h2>
                        <small class="text-muted">Active test suites</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Avg Execution Time</h5>
                        <h2 class="text-info" id="avg-exec-time">--</h2>
                        <small class="text-muted">Seconds</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Active Alerts</h5>
                        <h2 class="text-warning" id="active-alerts">--</h2>
                        <small class="text-muted">Requires attention</small>
                    </div>
                </div>
            </div>
        </div>

        <!-- Quality Gates -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5>Quality Gates Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="row" id="quality-gates">
                            <!-- Quality gates will be populated here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Coverage Trends</h5>
                    </div>
                    <div class="card-body">
                        <div id="coverage-chart"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Performance Trends</h5>
                    </div>
                    <div class="card-body">
                        <div id="performance-chart"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Alerts and Recommendations -->
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Active Alerts</h5>
                    </div>
                    <div class="card-body">
                        <div id="alerts-list">
                            <!-- Alerts will be populated here -->
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Recommendations</h5>
                    </div>
                    <div class="card-body">
                        <div id="recommendations-list">
                            <!-- Recommendations will be populated here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Initialize Socket.IO connection
        const socket = io();
        
        // Update functions
        function updateOverview() {
            fetch('/api/overview')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('success-rate').textContent = 
                        data.test_summary.success_rate.toFixed(1) + '%';
                    document.getElementById('total-tests').textContent = 
                        data.test_summary.total_tests;
                    document.getElementById('avg-exec-time').textContent = 
                        data.test_summary.average_execution_time.toFixed(2) + 's';
                    document.getElementById('active-alerts').textContent = 
                        data.alerts.total;
                    document.getElementById('last-updated').textContent = 
                        'Last updated: ' + new Date(data.last_updated).toLocaleTimeString();
                    
                    updateQualityGates(data.quality_gates);
                })
                .catch(error => console.error('Error updating overview:', error));
        }
        
        function updateQualityGates(gates) {
            const container = document.getElementById('quality-gates');
            container.innerHTML = '';
            
            Object.entries(gates).forEach(([gate, data]) => {
                const statusClass = data.status === 'PASS' ? 'quality-gate-pass' : 'quality-gate-fail';
                const statusIcon = data.status === 'PASS' ? '✓' : '✗';
                
                container.innerHTML += `
                    <div class="col-md-4 mb-3">
                        <div class="d-flex align-items-center">
                            <span class="${statusClass} fs-4 me-2">${statusIcon}</span>
                            <div>
                                <strong>${gate.replace('_', ' ').toUpperCase()}</strong><br>
                                <small>Current: ${data.current_value.toFixed(2)} / Target: ${data.target}</small>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        
        function updateCharts() {
            // Update coverage chart
            fetch('/api/coverage_trends?days=30')
                .then(response => response.json())
                .then(data => {
                    Plotly.newPlot('coverage-chart', 
                        JSON.parse(data.chart_json).data,
                        JSON.parse(data.chart_json).layout,
                        {responsive: true}
                    );
                })
                .catch(error => console.error('Error updating coverage chart:', error));
        }
        
        function updateAlerts() {
            fetch('/api/alerts')
                .then(response => response.json())
                .then(alerts => {
                    const container = document.getElementById('alerts-list');
                    container.innerHTML = '';
                    
                    if (alerts.length === 0) {
                        container.innerHTML = '<p class="text-muted">No active alerts</p>';
                        return;
                    }
                    
                    alerts.slice(0, 5).forEach(alert => {
                        const alertClass = alert.level === 'CRITICAL' ? 'alert-critical' : 
                                         alert.level === 'WARNING' ? 'alert-warning' : 'alert-info';
                        
                        container.innerHTML += `
                            <div class="alert alert-light ${alertClass} mb-2">
                                <strong>${alert.test_name}</strong><br>
                                <small>${alert.message}</small><br>
                                <small class="text-muted">${new Date(alert.timestamp).toLocaleString()}</small>
                            </div>
                        `;
                    });
                })
                .catch(error => console.error('Error updating alerts:', error));
        }
        
        function updateRecommendations() {
            fetch('/api/recommendations')
                .then(response => response.json())
                .then(recommendations => {
                    const container = document.getElementById('recommendations-list');
                    container.innerHTML = '';
                    
                    if (recommendations.length === 0) {
                        container.innerHTML = '<p class="text-muted">No recommendations available</p>';
                        return;
                    }
                    
                    recommendations.slice(0, 5).forEach(rec => {
                        const priorityClass = rec.priority === 'high' ? 'text-danger' : 
                                            rec.priority === 'medium' ? 'text-warning' : 'text-muted';
                        
                        container.innerHTML += `
                            <div class="mb-3">
                                <span class="badge bg-secondary">${rec.priority.toUpperCase()}</span>
                                <strong class="ms-2">${rec.test_name}</strong><br>
                                <small>${rec.description}</small>
                            </div>
                        `;
                    });
                })
                .catch(error => console.error('Error updating recommendations:', error));
        }
        
        // Initialize dashboard
        function initDashboard() {
            updateOverview();
            updateCharts();
            updateAlerts();
            updateRecommendations();
        }
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            updateOverview();
            updateAlerts();
            updateRecommendations();
        }, 30000);
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', initDashboard);
        
        // Socket.IO event handlers
        socket.on('connect', function() {
            console.log('Connected to dashboard server');
        });
        
        socket.on('test_update', function(data) {
            console.log('Test update received:', data);
            updateOverview();
        });
    </script>
</body>
</html>'''
    
    with open(templates_dir / 'dashboard.html', 'w') as f:
        f.write(dashboard_html)


if __name__ == "__main__":
    # Create templates
    create_dashboard_templates()
    
    # Create and run dashboard
    dashboard = DashboardServer(port=5000)
    dashboard.run(debug=True)