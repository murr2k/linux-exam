#!/usr/bin/env python3
"""
Coverage Quality Gate Script for MPU-6050 Linux Kernel Driver

This script enforces coverage quality gates in CI/CD pipelines.
It analyzes coverage reports and determines whether builds should pass or fail
based on configurable thresholds and trend analysis.

Usage:
    python3 scripts/coverage-gate.py [options]

Features:
- Configurable coverage thresholds
- Trend analysis and regression detection
- Component-specific quality gates
- CI/CD integration with exit codes
- Detailed reporting and recommendations
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class CoverageGateConfig:
    """Configuration for coverage quality gates."""
    min_line_coverage: float = 80.0
    min_branch_coverage: float = 75.0
    min_function_coverage: float = 90.0
    fail_under: float = 70.0
    allow_regression: float = 2.0  # Max allowed coverage drop %
    require_improvement: bool = False
    component_gates: Dict[str, Dict[str, float]] = None
    
    def __post_init__(self):
        if self.component_gates is None:
            self.component_gates = {
                'mpu6050_main.c': {
                    'min_line': 95.0,
                    'min_branch': 90.0,
                    'min_function': 98.0
                },
                'mpu6050_i2c.c': {
                    'min_line': 92.0,
                    'min_branch': 88.0,
                    'min_function': 95.0
                },
                'mpu6050_sysfs.c': {
                    'min_line': 88.0,
                    'min_branch': 85.0,
                    'min_function': 92.0
                },
                'mpu6050_chardev.c': {
                    'min_line': 90.0,
                    'min_branch': 87.0,
                    'min_function': 95.0
                }
            }


@dataclass
class CoverageResult:
    """Coverage analysis result."""
    passed: bool
    overall_coverage: Dict[str, float]
    component_coverage: Dict[str, Dict[str, float]]
    failures: List[str]
    warnings: List[str]
    recommendations: List[str]
    trend_analysis: Optional[Dict] = None


class CoverageGate:
    """Coverage quality gate analyzer."""
    
    def __init__(self, config: CoverageGateConfig):
        self.config = config
        self.history_file = "build/coverage/coverage_history.json"
        
    def load_coverage_data(self, coverage_file: str) -> Dict:
        """Load coverage data from LCOV or JSON file."""
        if not os.path.exists(coverage_file):
            raise FileNotFoundError(f"Coverage file not found: {coverage_file}")
        
        if coverage_file.endswith('.info'):
            return self._parse_lcov_file(coverage_file)
        elif coverage_file.endswith('.json'):
            with open(coverage_file, 'r') as f:
                return json.load(f)
        else:
            raise ValueError("Unsupported coverage file format. Use .info or .json")
    
    def _parse_lcov_file(self, lcov_file: str) -> Dict:
        """Parse LCOV info file into structured data."""
        coverage_data = {
            'overall': {'line': 0, 'branch': 0, 'function': 0},
            'files': {}
        }
        
        current_file = None
        file_data = None
        
        with open(lcov_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                if line.startswith('SF:'):
                    # Source file
                    current_file = os.path.basename(line[3:])
                    file_data = {
                        'lines_total': 0, 'lines_covered': 0,
                        'branches_total': 0, 'branches_covered': 0,
                        'functions_total': 0, 'functions_covered': 0
                    }
                    coverage_data['files'][current_file] = file_data
                    
                elif line.startswith('LF:') and file_data:
                    file_data['lines_total'] = int(line[3:])
                elif line.startswith('LH:') and file_data:
                    file_data['lines_covered'] = int(line[3:])
                elif line.startswith('BRF:') and file_data:
                    file_data['branches_total'] = int(line[4:])
                elif line.startswith('BRH:') and file_data:
                    file_data['branches_covered'] = int(line[4:])
                elif line.startswith('FNF:') and file_data:
                    file_data['functions_total'] = int(line[4:])
                elif line.startswith('FNH:') and file_data:
                    file_data['functions_covered'] = int(line[4:])
        
        # Calculate overall coverage
        total_lines = sum(f['lines_total'] for f in coverage_data['files'].values())
        covered_lines = sum(f['lines_covered'] for f in coverage_data['files'].values())
        total_branches = sum(f['branches_total'] for f in coverage_data['files'].values())
        covered_branches = sum(f['branches_covered'] for f in coverage_data['files'].values())
        total_functions = sum(f['functions_total'] for f in coverage_data['files'].values())
        covered_functions = sum(f['functions_covered'] for f in coverage_data['files'].values())
        
        coverage_data['overall'] = {
            'line': (covered_lines / total_lines * 100) if total_lines > 0 else 0,
            'branch': (covered_branches / total_branches * 100) if total_branches > 0 else 0,
            'function': (covered_functions / total_functions * 100) if total_functions > 0 else 0
        }
        
        # Calculate per-file percentages
        for filename, data in coverage_data['files'].items():
            data['line_coverage'] = (data['lines_covered'] / data['lines_total'] * 100) if data['lines_total'] > 0 else 0
            data['branch_coverage'] = (data['branches_covered'] / data['branches_total'] * 100) if data['branches_total'] > 0 else 0
            data['function_coverage'] = (data['functions_covered'] / data['functions_total'] * 100) if data['functions_total'] > 0 else 0
        
        return coverage_data
    
    def analyze_coverage(self, coverage_data: Dict) -> CoverageResult:
        """Analyze coverage data against quality gates."""
        failures = []
        warnings = []
        recommendations = []
        
        overall = coverage_data['overall']
        files = coverage_data['files']
        
        # Check overall coverage gates
        if overall['line'] < self.config.fail_under:
            failures.append(f"Line coverage ({overall['line']:.1f}%) is below critical threshold ({self.config.fail_under}%)")
        elif overall['line'] < self.config.min_line_coverage:
            warnings.append(f"Line coverage ({overall['line']:.1f}%) is below target ({self.config.min_line_coverage}%)")
        
        if overall['branch'] < (self.config.fail_under - 5):  # Branch threshold is typically lower
            failures.append(f"Branch coverage ({overall['branch']:.1f}%) is below critical threshold ({self.config.fail_under - 5}%)")
        elif overall['branch'] < self.config.min_branch_coverage:
            warnings.append(f"Branch coverage ({overall['branch']:.1f}%) is below target ({self.config.min_branch_coverage}%)")
        
        if overall['function'] < (self.config.fail_under + 10):  # Function threshold is typically higher
            failures.append(f"Function coverage ({overall['function']:.1f}%) is below critical threshold ({self.config.fail_under + 10}%)")
        elif overall['function'] < self.config.min_function_coverage:
            warnings.append(f"Function coverage ({overall['function']:.1f}%) is below target ({self.config.min_function_coverage}%)")
        
        # Check component-specific gates
        component_coverage = {}\n        for filename, thresholds in self.config.component_gates.items():\n            if filename in files:\n                file_data = files[filename]\n                component_coverage[filename] = {\n                    'line': file_data['line_coverage'],\n                    'branch': file_data['branch_coverage'],\n                    'function': file_data['function_coverage']\n                }\n                \n                # Check component thresholds\n                if file_data['line_coverage'] < thresholds['min_line']:\n                    if file_data['line_coverage'] < (thresholds['min_line'] - 10):\n                        failures.append(f\"{filename}: Line coverage ({file_data['line_coverage']:.1f}%) is critically below target ({thresholds['min_line']}%)\")\n                    else:\n                        warnings.append(f\"{filename}: Line coverage ({file_data['line_coverage']:.1f}%) is below target ({thresholds['min_line']}%)\")\n                \n                if file_data['branch_coverage'] < thresholds['min_branch']:\n                    if file_data['branch_coverage'] < (thresholds['min_branch'] - 10):\n                        failures.append(f\"{filename}: Branch coverage ({file_data['branch_coverage']:.1f}%) is critically below target ({thresholds['min_branch']}%)\")\n                    else:\n                        warnings.append(f\"{filename}: Branch coverage ({file_data['branch_coverage']:.1f}%) is below target ({thresholds['min_branch']}%)\")\n                \n                if file_data['function_coverage'] < thresholds['min_function']:\n                    if file_data['function_coverage'] < (thresholds['min_function'] - 10):\n                        failures.append(f\"{filename}: Function coverage ({file_data['function_coverage']:.1f}%) is critically below target ({thresholds['min_function']}%)\")\n                    else:\n                        warnings.append(f\"{filename}: Function coverage ({file_data['function_coverage']:.1f}%) is below target ({thresholds['min_function']}%)\")\n        \n        # Generate recommendations\n        if overall['line'] < self.config.min_line_coverage:\n            missing_lines = int((self.config.min_line_coverage - overall['line']) / 100 * sum(f['lines_total'] for f in files.values()))\n            recommendations.append(f\"Add tests to cover approximately {missing_lines} more lines of code\")\n        \n        if overall['branch'] < self.config.min_branch_coverage:\n            recommendations.append(\"Focus on testing conditional logic and error handling paths\")\n        \n        if overall['function'] < self.config.min_function_coverage:\n            recommendations.append(\"Ensure all public functions have at least one test case\")\n        \n        # Perform trend analysis\n        trend_analysis = self._analyze_trends(overall)\n        \n        return CoverageResult(\n            passed=len(failures) == 0,\n            overall_coverage=overall,\n            component_coverage=component_coverage,\n            failures=failures,\n            warnings=warnings,\n            recommendations=recommendations,\n            trend_analysis=trend_analysis\n        )\n    \n    def _analyze_trends(self, current_coverage: Dict[str, float]) -> Optional[Dict]:\n        \"\"\"Analyze coverage trends from historical data.\"\"\"\n        if not os.path.exists(self.history_file):\n            return None\n        \n        try:\n            with open(self.history_file, 'r') as f:\n                history = json.load(f)\n        except (json.JSONDecodeError, IOError):\n            return None\n        \n        if not history or len(history) < 2:\n            return None\n        \n        # Get the most recent historical entry\n        last_entry = history[-1]\n        last_coverage = last_entry.get('coverage', {})\n        \n        trends = {}\n        for metric in ['line', 'branch', 'function']:\n            current = current_coverage.get(metric, 0)\n            previous = last_coverage.get(metric, 0)\n            \n            if previous > 0:\n                change = current - previous\n                trends[metric] = {\n                    'current': current,\n                    'previous': previous,\n                    'change': change,\n                    'direction': 'up' if change > 0 else 'down' if change < 0 else 'stable'\n                }\n                \n                # Check for regressions\n                if change < -self.config.allow_regression:\n                    trends[metric]['regression'] = True\n        \n        return trends\n    \n    def save_coverage_history(self, coverage_data: Dict):\n        \"\"\"Save current coverage data to history file.\"\"\"\n        history_entry = {\n            'timestamp': datetime.now().isoformat(),\n            'coverage': coverage_data['overall'],\n            'files': {k: {\n                'line': v['line_coverage'],\n                'branch': v['branch_coverage'],\n                'function': v['function_coverage']\n            } for k, v in coverage_data['files'].items()}\n        }\n        \n        # Load existing history\n        history = []\n        if os.path.exists(self.history_file):\n            try:\n                with open(self.history_file, 'r') as f:\n                    history = json.load(f)\n            except (json.JSONDecodeError, IOError):\n                history = []\n        \n        # Add new entry and keep only last 30 days\n        history.append(history_entry)\n        \n        # Remove entries older than 30 days\n        cutoff_date = datetime.now() - timedelta(days=30)\n        history = [entry for entry in history \n                  if datetime.fromisoformat(entry['timestamp']) > cutoff_date]\n        \n        # Ensure directory exists\n        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)\n        \n        # Save updated history\n        with open(self.history_file, 'w') as f:\n            json.dump(history, f, indent=2)\n    \n    def generate_report(self, result: CoverageResult, output_format: str = 'text') -> str:\n        \"\"\"Generate coverage gate report.\"\"\"\n        if output_format == 'json':\n            return json.dumps({\n                'passed': result.passed,\n                'overall_coverage': result.overall_coverage,\n                'component_coverage': result.component_coverage,\n                'failures': result.failures,\n                'warnings': result.warnings,\n                'recommendations': result.recommendations,\n                'trend_analysis': result.trend_analysis\n            }, indent=2)\n        \n        # Text format\n        report = []\n        report.append(\"=\" * 60)\n        report.append(\"Coverage Quality Gate Report\")\n        report.append(\"=\" * 60)\n        \n        # Overall status\n        status = \"✅ PASS\" if result.passed else \"❌ FAIL\"\n        report.append(f\"Overall Status: {status}\")\n        report.append(\"\")\n        \n        # Overall coverage\n        report.append(\"Overall Coverage:\")\n        for metric, value in result.overall_coverage.items():\n            report.append(f\"  {metric.title()}: {value:.1f}%\")\n        report.append(\"\")\n        \n        # Component coverage\n        if result.component_coverage:\n            report.append(\"Component Coverage:\")\n            for filename, metrics in result.component_coverage.items():\n                report.append(f\"  {filename}:\")\n                for metric, value in metrics.items():\n                    report.append(f\"    {metric.title()}: {value:.1f}%\")\n            report.append(\"\")\n        \n        # Trend analysis\n        if result.trend_analysis:\n            report.append(\"Trend Analysis:\")\n            for metric, trend in result.trend_analysis.items():\n                direction_symbol = {\n                    'up': '📈',\n                    'down': '📉', \n                    'stable': '➡️'\n                }.get(trend['direction'], '')\n                \n                report.append(f\"  {metric.title()}: {trend['current']:.1f}% {direction_symbol} ({trend['change']:+.1f}%)\")\n                \n                if trend.get('regression'):\n                    report.append(f\"    ⚠️  Coverage regression detected!\")\n            report.append(\"\")\n        \n        # Failures\n        if result.failures:\n            report.append(\"❌ FAILURES:\")\n            for failure in result.failures:\n                report.append(f\"  • {failure}\")\n            report.append(\"\")\n        \n        # Warnings\n        if result.warnings:\n            report.append(\"⚠️  WARNINGS:\")\n            for warning in result.warnings:\n                report.append(f\"  • {warning}\")\n            report.append(\"\")\n        \n        # Recommendations\n        if result.recommendations:\n            report.append(\"💡 RECOMMENDATIONS:\")\n            for rec in result.recommendations:\n                report.append(f\"  • {rec}\")\n            report.append(\"\")\n        \n        report.append(\"=\" * 60)\n        \n        return \"\\n\".join(report)\n\n\ndef main():\n    \"\"\"Main entry point for coverage gate script.\"\"\"\n    parser = argparse.ArgumentParser(\n        description=\"Coverage quality gate for MPU-6050 Linux kernel driver\",\n        formatter_class=argparse.RawDescriptionHelpFormatter,\n        epilog=\"\"\"\nExamples:\n  # Basic coverage check\n  python3 scripts/coverage-gate.py --input build/coverage/coverage.info\n  \n  # Strict quality gate\n  python3 scripts/coverage-gate.py --input coverage.info --min-line=90 --min-branch=85\n  \n  # CI/CD integration\n  python3 scripts/coverage-gate.py --input coverage.info --fail-under=80 --format=json\n        \"\"\"\n    )\n    \n    parser.add_argument(\n        '--input', '-i',\n        default='build/coverage/coverage.info',\n        help='Path to coverage file (LCOV .info or JSON format)'\n    )\n    \n    parser.add_argument(\n        '--min-line',\n        type=float,\n        default=80.0,\n        help='Minimum line coverage percentage (default: 80)'\n    )\n    \n    parser.add_argument(\n        '--min-branch',\n        type=float,\n        default=75.0,\n        help='Minimum branch coverage percentage (default: 75)'\n    )\n    \n    parser.add_argument(\n        '--min-function',\n        type=float,\n        default=90.0,\n        help='Minimum function coverage percentage (default: 90)'\n    )\n    \n    parser.add_argument(\n        '--fail-under',\n        type=float,\n        default=70.0,\n        help='Critical threshold - fail build if coverage drops below this (default: 70)'\n    )\n    \n    parser.add_argument(\n        '--allow-regression',\n        type=float,\n        default=2.0,\n        help='Maximum allowed coverage regression percentage (default: 2)'\n    )\n    \n    parser.add_argument(\n        '--format', '-f',\n        choices=['text', 'json'],\n        default='text',\n        help='Output format for the report'\n    )\n    \n    parser.add_argument(\n        '--output', '-o',\n        help='Output file for the report (default: stdout)'\n    )\n    \n    parser.add_argument(\n        '--save-history',\n        action='store_true',\n        help='Save coverage data to history file for trend analysis'\n    )\n    \n    parser.add_argument(\n        '--verbose', '-v',\n        action='store_true',\n        help='Enable verbose output'\n    )\n    \n    args = parser.parse_args()\n    \n    try:\n        # Create configuration\n        config = CoverageGateConfig(\n            min_line_coverage=args.min_line,\n            min_branch_coverage=args.min_branch,\n            min_function_coverage=args.min_function,\n            fail_under=args.fail_under,\n            allow_regression=args.allow_regression\n        )\n        \n        if args.verbose:\n            print(f\"Loading coverage data from: {args.input}\")\n        \n        # Initialize coverage gate\n        gate = CoverageGate(config)\n        \n        # Load and analyze coverage\n        coverage_data = gate.load_coverage_data(args.input)\n        result = gate.analyze_coverage(coverage_data)\n        \n        # Save history if requested\n        if args.save_history:\n            gate.save_coverage_history(coverage_data)\n            if args.verbose:\n                print(\"Coverage history saved\")\n        \n        # Generate report\n        report = gate.generate_report(result, args.format)\n        \n        # Output report\n        if args.output:\n            with open(args.output, 'w') as f:\n                f.write(report)\n            if args.verbose:\n                print(f\"Report saved to: {args.output}\")\n        else:\n            print(report)\n        \n        # Exit with appropriate code\n        if result.passed:\n            if args.verbose:\n                print(\"Coverage quality gate: PASSED\")\n            return 0\n        else:\n            if args.verbose:\n                print(\"Coverage quality gate: FAILED\")\n            return 1\n            \n    except FileNotFoundError as e:\n        print(f\"Error: {e}\", file=sys.stderr)\n        print(\"Run 'make test COVERAGE=1' to generate coverage data first.\", file=sys.stderr)\n        return 1\n    except Exception as e:\n        print(f\"Error: {e}\", file=sys.stderr)\n        if args.verbose:\n            import traceback\n            traceback.print_exc()\n        return 1\n\n\nif __name__ == '__main__':\n    sys.exit(main())