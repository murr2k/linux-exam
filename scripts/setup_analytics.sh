#!/bin/bash
#
# Test Analytics and Reporting System Setup Script
#
# This script sets up the comprehensive test analytics infrastructure
# including metrics collection, quality analysis, performance monitoring,
# and real-time dashboard.
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ANALYTICS_DIR="$PROJECT_ROOT/src/analytics"
DASHBOARD_DIR="$PROJECT_ROOT/src/dashboard"
VENV_DIR="$PROJECT_ROOT/.venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print banner
print_banner() {
    echo "========================================================================="
    echo "  Test Analytics and Reporting System Setup"
    echo "  Comprehensive test quality, performance, and reliability monitoring"
    echo "========================================================================="
    echo ""
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    local missing_deps=""
    
    # Check Python
    if ! command -v python3 >/dev/null 2>&1; then
        missing_deps+="python3 "
    else
        python_version=$(python3 --version | cut -d' ' -f2)
        if [[ $(echo "$python_version" | cut -d'.' -f1) -lt 3 ]] || [[ $(echo "$python_version" | cut -d'.' -f2) -lt 8 ]]; then
            log_warning "Python 3.8+ recommended (found $python_version)"
        fi
    fi
    
    # Check pip
    if ! command -v pip3 >/dev/null 2>&1; then
        missing_deps+="python3-pip "
    fi
    
    # Check git (for CI integration)
    if ! command -v git >/dev/null 2>&1; then
        log_warning "Git not found - CI integration may be limited"
    fi
    
    # Check Node.js (for dashboard dependencies)
    if ! command -v node >/dev/null 2>&1; then
        log_warning "Node.js not found - some dashboard features may be limited"
    fi
    
    if [ -n "$missing_deps" ]; then
        log_error "Missing required dependencies: $missing_deps"
        log_info "Please install missing dependencies:"
        echo "  Ubuntu/Debian: sudo apt-get install $missing_deps"
        echo "  CentOS/RHEL:   sudo yum install $missing_deps"
        echo "  macOS:         brew install $missing_deps"
        exit 1
    fi
    
    log_success "System requirements check passed"
}

# Setup Python virtual environment
setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        log_success "Created Python virtual environment"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install required packages
    log_info "Installing Python dependencies..."
    
    cat > "$PROJECT_ROOT/requirements-analytics.txt" << EOF
# Core analytics dependencies
numpy>=1.21.0
pandas>=1.3.0
scipy>=1.7.0
sqlite3  # Built-in, but listed for documentation

# Web framework for dashboard
flask>=2.0.0
flask-socketio>=5.0.0

# Data visualization
plotly>=5.0.0

# Statistical analysis
scikit-learn>=1.0.0

# Database
sqlalchemy>=1.4.0

# HTTP requests for CI integration
requests>=2.26.0

# Configuration and utilities
python-dotenv>=0.19.0
click>=8.0.0

# Testing framework integration
pytest>=6.0.0
pytest-cov>=3.0.0

# Development tools
black>=21.0.0
flake8>=4.0.0
mypy>=0.910
EOF
    
    pip install -r "$PROJECT_ROOT/requirements-analytics.txt"
    
    log_success "Python environment setup complete"
}

# Create directory structure
setup_directories() {
    log_info "Creating directory structure..."
    
    # Create main directories
    mkdir -p "$ANALYTICS_DIR"
    mkdir -p "$DASHBOARD_DIR/templates"
    mkdir -p "$DASHBOARD_DIR/static/css"
    mkdir -p "$DASHBOARD_DIR/static/js"
    mkdir -p "$PROJECT_ROOT/test-reports"
    mkdir -p "$PROJECT_ROOT/coverage-reports"
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/data"
    mkdir -p "$PROJECT_ROOT/config"
    
    log_success "Directory structure created"
}

# Setup database
setup_database() {
    log_info "Setting up analytics database..."
    
    # Create database initialization script
    cat > "$PROJECT_ROOT/scripts/init_analytics_db.py" << 'EOF'
#!/usr/bin/env python3
"""Initialize analytics database with all required tables."""

import sqlite3
import sys
from pathlib import Path

def init_database(db_path: str):
    """Initialize all database tables."""
    
    with sqlite3.connect(db_path) as conn:
        # Test executions table
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
        
        # Coverage trends table
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
        
        # Performance baselines table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS performance_baselines (
                test_name TEXT PRIMARY KEY,
                baseline_time REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Quality scores table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_quality_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                coverage_score REAL NOT NULL,
                assertion_score REAL NOT NULL,
                boundary_score REAL NOT NULL,
                error_handling_score REAL NOT NULL,
                maintainability_score REAL NOT NULL,
                overall_score REAL NOT NULL,
                analysis_details TEXT
            )
        ''')
        
        # Performance metrics table
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
        
        # Regression alerts table
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
        
        # CI reports table
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
        
        # Create indexes for better performance
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_test_name ON test_executions(test_name)',
            'CREATE INDEX IF NOT EXISTS idx_timestamp ON test_executions(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_status ON test_executions(status)',
            'CREATE INDEX IF NOT EXISTS idx_coverage_timestamp ON coverage_trends(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_perf_test_name ON performance_metrics(test_name)',
            'CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON performance_metrics(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON regression_alerts(resolved)',
            'CREATE INDEX IF NOT EXISTS idx_ci_build ON ci_reports(build_id)'
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        conn.commit()
    
    print(f"Database initialized successfully: {db_path}")

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "test_analytics.db"
    init_database(db_path)
EOF
    
    # Make script executable and run it
    chmod +x "$PROJECT_ROOT/scripts/init_analytics_db.py"
    python3 "$PROJECT_ROOT/scripts/init_analytics_db.py" "$PROJECT_ROOT/data/test_analytics.db"
    
    log_success "Analytics database initialized"
}

# Create configuration files
create_config_files() {
    log_info "Creating configuration files..."
    
    # Analytics configuration
    cat > "$PROJECT_ROOT/config/analytics_config.json" << EOF
{
    "database": {
        "path": "data/test_analytics.db",
        "backup_interval_hours": 24,
        "retention_days": 90
    },
    "metrics_collection": {
        "enabled": true,
        "collection_interval_seconds": 60,
        "resource_monitoring": true,
        "coverage_tracking": true
    },
    "quality_analysis": {
        "enabled": true,
        "quality_thresholds": {
            "coverage_minimum": 80.0,
            "success_rate_minimum": 95.0,
            "performance_regression_max": 1.2
        },
        "mutation_testing": {
            "enabled": false,
            "sample_rate": 0.1
        }
    },
    "performance_analysis": {
        "enabled": true,
        "baseline_window_days": 90,
        "regression_detection": true,
        "statistical_confidence": 0.95
    },
    "dashboard": {
        "enabled": true,
        "port": 5000,
        "real_time_updates": true,
        "data_refresh_seconds": 30
    },
    "ci_integration": {
        "github": {
            "enabled": false,
            "pr_comments": true
        },
        "slack": {
            "enabled": false,
            "channel": "#test-alerts"
        },
        "email_alerts": {
            "enabled": false,
            "smtp_host": "localhost",
            "smtp_port": 587
        }
    },
    "logging": {
        "level": "INFO",
        "file": "logs/analytics.log",
        "max_size_mb": 100,
        "backup_count": 5
    }
}
EOF
    
    # Dashboard static files
    mkdir -p "$DASHBOARD_DIR/static/css"
    cat > "$DASHBOARD_DIR/static/css/dashboard.css" << EOF
/* Dashboard Styles */
.dashboard-container {
    padding: 20px;
}

.metric-card {
    transition: transform 0.2s ease-in-out;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.quality-gate-pass {
    color: #28a745;
    font-weight: bold;
}

.quality-gate-fail {
    color: #dc3545;
    font-weight: bold;
}

.quality-gate-warn {
    color: #ffc107;
    font-weight: bold;
}

.trend-indicator {
    font-size: 0.8em;
    margin-left: 5px;
}

.trend-up { color: #28a745; }
.trend-down { color: #dc3545; }
.trend-stable { color: #6c757d; }

.alert-critical {
    border-left: 4px solid #dc3545;
}

.alert-warning {
    border-left: 4px solid #ffc107;
}

.alert-info {
    border-left: 4px solid #17a2b8;
}

.chart-container {
    min-height: 400px;
}

@media (max-width: 768px) {
    .dashboard-container {
        padding: 10px;
    }
    
    .metric-card {
        margin-bottom: 15px;
    }
}
EOF
    
    log_success "Configuration files created"
}

# Setup CI integration scripts
setup_ci_integration() {
    log_info "Setting up CI integration scripts..."
    
    # GitHub Actions workflow
    mkdir -p "$PROJECT_ROOT/.github/workflows"
    cat > "$PROJECT_ROOT/.github/workflows/test-analytics.yml" << EOF
name: Test Analytics Integration

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  ANALYTICS_DB_PATH: data/test_analytics.db

jobs:
  test-with-analytics:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-analytics.txt
    
    - name: Initialize analytics database
      run: |
        mkdir -p data
        python scripts/init_analytics_db.py \$ANALYTICS_DB_PATH
    
    - name: Run tests with metrics collection
      run: |
        # Start metrics collector in background
        python -c "
from src.analytics.test_metrics_collector import TestMetricsCollector
collector = TestMetricsCollector('$ANALYTICS_DB_PATH')
# Your test execution with metrics collection
"
    
    - name: Generate analytics report
      run: |
        python src/analytics/ci_integration.py \\
          --build-id \${{ github.run_id }} \\
          --commit \${{ github.sha }} \\
          --branch \${{ github.ref_name }} \\
          \${{ github.event.pull_request.number && '--pr-number' || '' }} \\
          \${{ github.event.pull_request.number || '' }}
    
    - name: Upload test reports
      uses: actions/upload-artifact@v3
      with:
        name: test-analytics-reports
        path: test-reports/
        retention-days: 30
    
    - name: Comment PR
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          // This would be implemented to post analytics results
          console.log('Analytics results would be posted here');
EOF
    
    # Pre-commit hook
    mkdir -p "$PROJECT_ROOT/.git/hooks"
    cat > "$PROJECT_ROOT/.git/hooks/pre-commit" << 'EOF'
#!/bin/bash
#
# Pre-commit hook to run basic analytics checks
#

echo "Running test analytics pre-commit checks..."

# Check if analytics components are importable
if ! python3 -c "from src.analytics.test_metrics_collector import TestMetricsCollector" 2>/dev/null; then
    echo "Warning: Test metrics collector not available"
fi

# Run quick quality checks on modified test files
modified_files=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(py|c|cpp|h|hpp)$' | grep -i test)

if [ -n "$modified_files" ]; then
    echo "Analyzing modified test files for quality..."
    # This would run quality analysis on modified files
fi

exit 0
EOF
    
    chmod +x "$PROJECT_ROOT/.git/hooks/pre-commit"
    
    log_success "CI integration scripts created"
}

# Create startup scripts
create_startup_scripts() {
    log_info "Creating startup scripts..."
    
    # Analytics daemon startup script
    cat > "$PROJECT_ROOT/scripts/start_analytics.sh" << EOF
#!/bin/bash
#
# Start Test Analytics System
#

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="\$(dirname "\$SCRIPT_DIR")"
VENV_DIR="\$PROJECT_ROOT/.venv"

# Activate virtual environment
if [ -d "\$VENV_DIR" ]; then
    source "\$VENV_DIR/bin/activate"
else
    echo "Virtual environment not found. Run setup_analytics.sh first."
    exit 1
fi

echo "Starting Test Analytics System..."

# Set environment variables
export PYTHONPATH="\$PROJECT_ROOT:\$PYTHONPATH"
export ANALYTICS_CONFIG_PATH="\$PROJECT_ROOT/config/analytics_config.json"
export ANALYTICS_DB_PATH="\$PROJECT_ROOT/data/test_analytics.db"

# Start dashboard server
echo "Starting dashboard server on port 5000..."
python "\$PROJECT_ROOT/src/dashboard/dashboard_server.py" &
DASHBOARD_PID=\$!

# Start metrics collection daemon (if needed)
# python "\$PROJECT_ROOT/src/analytics/metrics_daemon.py" &
# METRICS_PID=\$!

echo "Test Analytics System started!"
echo "Dashboard available at: http://localhost:5000"
echo "Dashboard PID: \$DASHBOARD_PID"

# Create PID file
echo \$DASHBOARD_PID > "\$PROJECT_ROOT/analytics.pid"

echo "To stop the system, run: scripts/stop_analytics.sh"
EOF
    
    # Stop script
    cat > "$PROJECT_ROOT/scripts/stop_analytics.sh" << EOF
#!/bin/bash
#
# Stop Test Analytics System
#

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="\$(dirname "\$SCRIPT_DIR")"
PID_FILE="\$PROJECT_ROOT/analytics.pid"

if [ -f "\$PID_FILE" ]; then
    PID=\$(cat "\$PID_FILE")
    if kill -0 "\$PID" 2>/dev/null; then
        echo "Stopping Test Analytics System (PID: \$PID)..."
        kill "\$PID"
        rm "\$PID_FILE"
        echo "Test Analytics System stopped."
    else
        echo "Process not running (stale PID file removed)."
        rm "\$PID_FILE"
    fi
else
    echo "PID file not found. System may not be running."
fi
EOF
    
    # Make scripts executable
    chmod +x "$PROJECT_ROOT/scripts/start_analytics.sh"
    chmod +x "$PROJECT_ROOT/scripts/stop_analytics.sh"
    
    # Development helper script
    cat > "$PROJECT_ROOT/scripts/dev_analytics.sh" << EOF
#!/bin/bash
#
# Development mode for Test Analytics System
#

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="\$(dirname "\$SCRIPT_DIR")"
VENV_DIR="\$PROJECT_ROOT/.venv"

# Activate virtual environment
source "\$VENV_DIR/bin/activate"

# Set environment variables
export PYTHONPATH="\$PROJECT_ROOT:\$PYTHONPATH"
export ANALYTICS_CONFIG_PATH="\$PROJECT_ROOT/config/analytics_config.json"
export ANALYTICS_DB_PATH="\$PROJECT_ROOT/data/test_analytics.db"
export FLASK_ENV=development
export FLASK_DEBUG=1

echo "Starting Test Analytics System in development mode..."
echo "Dashboard will reload automatically on changes."

# Start dashboard in development mode
python "\$PROJECT_ROOT/src/dashboard/dashboard_server.py"
EOF
    
    chmod +x "$PROJECT_ROOT/scripts/dev_analytics.sh"
    
    log_success "Startup scripts created"
}

# Generate documentation
generate_documentation() {
    log_info "Generating documentation..."
    
    cat > "$PROJECT_ROOT/docs/test-analytics-guide.md" << EOF
# Test Analytics and Reporting System Guide

## Overview

The Test Analytics and Reporting System provides comprehensive monitoring and analysis of test quality, performance, and reliability. It includes:

1. **Test Metrics Collection**: Execution time tracking, reliability metrics, coverage analysis
2. **Quality Analytics**: Test quality scoring, defect detection, effectiveness measurement  
3. **Performance Analytics**: Regression detection, statistical analysis, resource monitoring
4. **Real-time Dashboard**: Live monitoring, trend visualization, actionable recommendations
5. **CI/CD Integration**: Automated reports, PR comments, quality gates

## Quick Start

### 1. Setup the System

\`\`\`bash
# Run the setup script
./scripts/setup_analytics.sh

# Start the analytics system
./scripts/start_analytics.sh
\`\`\`

### 2. Access the Dashboard

Open your browser to: http://localhost:5000

### 3. Integrate with Your Tests

\`\`\`python
from src.analytics.test_metrics_collector import TestMetricsCollector

# Initialize collector
collector = TestMetricsCollector()

# Start test tracking
test_id = collector.start_test_execution("my_test", "unit_tests")

# ... run your test ...

# End test tracking
collector.end_test_execution(test_id, "PASSED", coverage_data={
    'line_coverage': 85.5,
    'branch_coverage': 78.2,
    'function_coverage': 92.1
})
\`\`\`

## Components

### Test Metrics Collector

Tracks test executions and collects metrics:
- Execution time and resource usage
- Test reliability and maintenance burden
- Coverage trends and quality scores

### Quality Analyzer

Analyzes test quality across multiple dimensions:
- Coverage quality scoring
- Assertion effectiveness
- Boundary condition testing
- Error handling coverage
- Test maintainability

### Performance Analyzer

Monitors performance and detects regressions:
- Statistical regression detection
- Baseline establishment and comparison
- Resource usage trend analysis
- Performance forecasting

### Dashboard Server

Provides real-time visualization:
- Quality gate status monitoring
- Performance trend charts
- Active alerts and recommendations
- Historical data analysis

### CI Integration

Automates quality gates and reporting:
- GitHub PR comment integration
- Slack/email alerting
- Quality gate enforcement
- Historical data persistence

## Configuration

Edit \`config/analytics_config.json\` to customize:

\`\`\`json
{
  "quality_thresholds": {
    "coverage_minimum": 80.0,
    "success_rate_minimum": 95.0,
    "performance_regression_max": 1.2
  },
  "dashboard": {
    "port": 5000,
    "real_time_updates": true
  },
  "ci_integration": {
    "github": {
      "enabled": true,
      "pr_comments": true
    }
  }
}
\`\`\`

## API Endpoints

- \`GET /api/overview\` - Dashboard overview data
- \`GET /api/test_metrics/<test_name>\` - Detailed test metrics
- \`GET /api/quality_gates\` - Quality gate status
- \`GET /api/recommendations\` - Actionable recommendations
- \`GET /api/alerts\` - Active alerts

## Quality Gates

The system enforces these quality gates:

1. **Code Coverage**: Minimum 80%, Target 90%
2. **Test Success Rate**: Minimum 95%, Target 99%
3. **Performance Regression**: Maximum 20% slower, Target <5%
4. **Test Quality Score**: Minimum 0.7, Target 0.85

## Development

### Running in Development Mode

\`\`\`bash
./scripts/dev_analytics.sh
\`\`\`

### Adding New Metrics

1. Extend the \`TestMetricsCollector\` class
2. Add database schema updates
3. Update dashboard visualization
4. Add CI integration hooks

### Testing the Analytics System

\`\`\`bash
# Run analytics system tests
python -m pytest tests/analytics/

# Run integration tests
python -m pytest tests/integration/
\`\`\`

## Troubleshooting

### Database Issues

\`\`\`bash
# Reinitialize database
python scripts/init_analytics_db.py data/test_analytics.db
\`\`\`

### Dashboard Not Starting

\`\`\`bash
# Check logs
tail -f logs/analytics.log

# Verify virtual environment
source .venv/bin/activate
python -c "import flask; print('Flask available')"
\`\`\`

### CI Integration Issues

1. Check GitHub token permissions
2. Verify webhook URLs for Slack
3. Ensure proper environment variables

## Support

For issues and questions:
1. Check the logs in \`logs/analytics.log\`
2. Review the configuration in \`config/analytics_config.json\`
3. Verify database integrity with \`scripts/check_db.py\`
EOF
    
    log_success "Documentation generated"
}

# Validation tests
run_validation_tests() {
    log_info "Running validation tests..."
    
    # Test database initialization
    if [ -f "$PROJECT_ROOT/data/test_analytics.db" ]; then
        log_success "Database file created successfully"
    else
        log_error "Database file not found"
        return 1
    fi
    
    # Test Python imports
    source "$VENV_DIR/bin/activate"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    if python3 -c "from src.analytics.test_metrics_collector import TestMetricsCollector; print('✓ Metrics collector import successful')" 2>/dev/null; then
        log_success "Test metrics collector import successful"
    else
        log_error "Failed to import test metrics collector"
        return 1
    fi
    
    if python3 -c "from src.analytics.quality_analyzer import QualityAnalyzer; print('✓ Quality analyzer import successful')" 2>/dev/null; then
        log_success "Quality analyzer import successful"
    else
        log_error "Failed to import quality analyzer"
        return 1
    fi
    
    if python3 -c "from src.analytics.performance_analyzer import PerformanceAnalyzer; print('✓ Performance analyzer import successful')" 2>/dev/null; then
        log_success "Performance analyzer import successful"
    else
        log_error "Failed to import performance analyzer"
        return 1
    fi
    
    # Test basic functionality
    python3 -c "
from src.analytics.test_metrics_collector import TestMetricsCollector
import tempfile
import os

# Test with temporary database
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    db_path = f.name

try:
    collector = TestMetricsCollector(db_path)
    test_id = collector.start_test_execution('test_validation', 'unit_tests')
    collector.end_test_execution(test_id, 'PASSED')
    print('✓ Basic functionality test passed')
finally:
    if os.path.exists(db_path):
        os.unlink(db_path)
"
    
    if [ $? -eq 0 ]; then
        log_success "Basic functionality test passed"
    else
        log_error "Basic functionality test failed"
        return 1
    fi
    
    log_success "All validation tests passed"
    return 0
}

# Print usage instructions
print_usage() {
    echo ""
    echo "========================================================================="
    echo "  Setup Complete!"
    echo "========================================================================="
    echo ""
    echo "The Test Analytics and Reporting System has been successfully installed."
    echo ""
    echo "📊 NEXT STEPS:"
    echo ""
    echo "1. Start the analytics system:"
    echo "   ./scripts/start_analytics.sh"
    echo ""
    echo "2. Open the dashboard in your browser:"
    echo "   http://localhost:5000"
    echo ""
    echo "3. Integrate with your tests (see examples in docs/test-analytics-guide.md)"
    echo ""
    echo "📁 IMPORTANT FILES:"
    echo "   • Configuration:    config/analytics_config.json"
    echo "   • Database:         data/test_analytics.db"
    echo "   • Logs:            logs/analytics.log"
    echo "   • Documentation:    docs/test-analytics-guide.md"
    echo ""
    echo "🛠️  MANAGEMENT COMMANDS:"
    echo "   • Start system:     ./scripts/start_analytics.sh"
    echo "   • Stop system:      ./scripts/stop_analytics.sh"
    echo "   • Development mode: ./scripts/dev_analytics.sh"
    echo ""
    echo "For detailed usage instructions, see: docs/test-analytics-guide.md"
    echo ""
    echo "========================================================================="
}

# Main execution
main() {
    print_banner
    
    log_info "Starting Test Analytics and Reporting System setup..."
    
    check_requirements
    setup_directories
    setup_python_environment
    setup_database
    create_config_files
    setup_ci_integration
    create_startup_scripts
    generate_documentation
    
    if run_validation_tests; then
        print_usage
        log_success "Setup completed successfully!"
        exit 0
    else
        log_error "Setup validation failed. Please check the errors above."
        exit 1
    fi
}

# Run main function
main "$@"