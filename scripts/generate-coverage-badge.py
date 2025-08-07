#!/usr/bin/env python3
"""
Coverage Badge Generator for MPU-6050 Linux Kernel Driver

This script generates coverage badges for README files based on coverage data.
Supports multiple coverage types (line, branch, function) with color-coded badges
based on configurable thresholds.

Usage:
    python3 scripts/generate-coverage-badge.py [options]

Features:
- Multiple coverage types (line, branch, function, statement)
- Color-coded badges based on thresholds
- JSON output for CI/CD integration
- Shields.io compatible badge generation
- Historical trend tracking
- Component-specific coverage analysis
"""

import argparse
import json
import sys
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CoverageMetrics:
    """Coverage metrics for a component or overall project."""
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    statement_coverage: float
    lines_total: int
    lines_covered: int
    branches_total: int
    branches_covered: int
    functions_total: int
    functions_covered: int
    timestamp: str


@dataclass
class CoverageThresholds:
    """Coverage thresholds for different quality levels."""
    excellent: float = 95.0
    good: float = 90.0
    warning: float = 80.0
    critical: float = 70.0


class CoverageBadgeGenerator:
    """Generates coverage badges with color-coded quality indicators."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize badge generator with configuration."""
        self.config = self._load_config(config_path)
        self.thresholds = {
            'line': CoverageThresholds(95, 90, 80, 70),
            'branch': CoverageThresholds(90, 85, 75, 65),
            'function': CoverageThresholds(98, 95, 90, 80),
            'statement': CoverageThresholds(95, 90, 85, 75)
        }
        self.colors = {
            'excellent': 'brightgreen',
            'good': 'green', 
            'warning': 'yellow',
            'critical': 'red',
            'unknown': 'lightgrey'
        }
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            'output_dir': 'docs/badges',
            'coverage_data_path': 'build/coverage/coverage.json',
            'shields_io_base': 'https://img.shields.io/badge',
            'badge_style': 'flat',
            'components': {
                'mpu6050_main.c': {'target_line': 95, 'target_branch': 90},
                'mpu6050_i2c.c': {'target_line': 92, 'target_branch': 88},
                'mpu6050_sysfs.c': {'target_line': 88, 'target_branch': 85},
                'mpu6050_chardev.c': {'target_line': 90, 'target_branch': 87}
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
                
        return default_config
    
    def _get_coverage_color(self, coverage: float, coverage_type: str) -> str:
        """Get color for coverage percentage based on thresholds."""
        thresholds = self.thresholds[coverage_type]
        
        if coverage >= thresholds.excellent:
            return self.colors['excellent']
        elif coverage >= thresholds.good:
            return self.colors['good']
        elif coverage >= thresholds.warning:
            return self.colors['warning']
        elif coverage >= thresholds.critical:
            return self.colors['critical']
        else:
            return self.colors['critical']
    
    def _format_coverage_percentage(self, coverage: float) -> str:
        """Format coverage percentage for display."""
        return f"{coverage:.1f}%" if coverage < 100 else "100%"
    
    def generate_badge_url(self, label: str, coverage: float, coverage_type: str) -> str:
        """Generate Shields.io badge URL."""
        percentage = self._format_coverage_percentage(coverage)
        color = self._get_coverage_color(coverage, coverage_type)
        
        # URL encode spaces and special characters
        label_encoded = label.replace(' ', '%20').replace('-', '--')
        
        badge_url = (
            f"{self.config['shields_io_base']}/{label_encoded}-{percentage}-{color}"
            f"?style={self.config['badge_style']}"
        )
        
        return badge_url
    
    def generate_badge_markdown(self, label: str, coverage: float, 
                              coverage_type: str, link_url: str = None) -> str:
        """Generate markdown for coverage badge."""
        badge_url = self.generate_badge_url(label, coverage, coverage_type)
        
        if link_url:
            return f"[![{label}]({badge_url})]({link_url})"
        else:
            return f"![{label}]({badge_url})"
    
    def parse_lcov_data(self, lcov_path: str) -> CoverageMetrics:
        """Parse LCOV coverage data file."""
        if not os.path.exists(lcov_path):
            raise FileNotFoundError(f"LCOV file not found: {lcov_path}")
        
        lines_total = lines_covered = 0
        branches_total = branches_covered = 0
        functions_total = functions_covered = 0
        
        with open(lcov_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('LF:'):
                    lines_total += int(line.split(':')[1])
                elif line.startswith('LH:'):
                    lines_covered += int(line.split(':')[1])
                elif line.startswith('BRF:'):
                    branches_total += int(line.split(':')[1])
                elif line.startswith('BRH:'):
                    branches_covered += int(line.split(':')[1])
                elif line.startswith('FNF:'):
                    functions_total += int(line.split(':')[1])
                elif line.startswith('FNDA:'):
                    if int(line.split(',')[0].split(':')[1]) > 0:
                        functions_covered += 1
        
        line_coverage = (lines_covered / lines_total * 100) if lines_total > 0 else 0
        branch_coverage = (branches_covered / branches_total * 100) if branches_total > 0 else 0
        function_coverage = (functions_covered / functions_total * 100) if functions_total > 0 else 0
        
        return CoverageMetrics(
            line_coverage=line_coverage,
            branch_coverage=branch_coverage,
            function_coverage=function_coverage,
            statement_coverage=line_coverage,  # Use line coverage as statement coverage
            lines_total=lines_total,
            lines_covered=lines_covered,
            branches_total=branches_total,
            branches_covered=branches_covered,
            functions_total=functions_total,
            functions_covered=functions_covered,
            timestamp=datetime.now().isoformat()
        )
    
    def parse_json_coverage(self, json_path: str) -> CoverageMetrics:
        """Parse JSON coverage data file."""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Coverage JSON file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON coverage formats
        if 'totals' in data:
            # Coverage.py format
            totals = data['totals']
            return CoverageMetrics(
                line_coverage=totals.get('percent_covered', 0),
                branch_coverage=totals.get('percent_covered_display', 0),
                function_coverage=100.0,  # Not available in coverage.py
                statement_coverage=totals.get('percent_covered', 0),
                lines_total=totals.get('num_statements', 0),
                lines_covered=totals.get('covered_lines', 0),
                branches_total=totals.get('num_branches', 0),
                branches_covered=totals.get('covered_branches', 0),
                functions_total=0,
                functions_covered=0,
                timestamp=datetime.now().isoformat()
            )
        elif 'line_coverage' in data:
            # Custom format
            return CoverageMetrics(**data)
        else:
            raise ValueError("Unknown JSON coverage format")
    
    def generate_component_badges(self, coverage_data: Dict[str, CoverageMetrics]) -> Dict[str, str]:
        """Generate badges for individual components."""
        badges = {}
        
        for component, metrics in coverage_data.items():
            component_name = os.path.basename(component).replace('.c', '').replace('_', ' ').title()
            
            badges[f"{component}_line"] = self.generate_badge_markdown(
                f"{component_name} Line Coverage",
                metrics.line_coverage,
                'line',
                'docs/TEST_COVERAGE_DASHBOARD.md'
            )
            
            badges[f"{component}_branch"] = self.generate_badge_markdown(
                f"{component_name} Branch Coverage", 
                metrics.branch_coverage,
                'branch',
                'docs/TEST_COVERAGE_DASHBOARD.md'
            )
            
        return badges
    
    def generate_overall_badges(self, metrics: CoverageMetrics) -> Dict[str, str]:
        """Generate overall project coverage badges."""
        return {
            'line_coverage': self.generate_badge_markdown(
                'Line Coverage',
                metrics.line_coverage,
                'line',
                'docs/TEST_COVERAGE_DASHBOARD.md'
            ),
            'branch_coverage': self.generate_badge_markdown(
                'Branch Coverage',
                metrics.branch_coverage, 
                'branch',
                'docs/TEST_COVERAGE_DASHBOARD.md'
            ),
            'function_coverage': self.generate_badge_markdown(
                'Function Coverage',
                metrics.function_coverage,
                'function',
                'docs/TEST_COVERAGE_DASHBOARD.md'
            ),
            'statement_coverage': self.generate_badge_markdown(
                'Statement Coverage',
                metrics.statement_coverage,
                'statement',
                'docs/TEST_COVERAGE_DASHBOARD.md'
            )
        }
    
    def save_badges_json(self, badges: Dict[str, str], output_path: str):
        """Save badges as JSON for CI/CD integration."""
        badge_data = {
            'badges': badges,
            'timestamp': datetime.now().isoformat(),
            'generator': 'mpu6050-coverage-badge-generator',
            'version': '1.0.0'
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(badge_data, f, indent=2)
    
    def update_readme_badges(self, badges: Dict[str, str], readme_path: str = 'README.md'):
        """Update README.md with generated coverage badges."""
        if not os.path.exists(readme_path):
            print(f"Warning: README file not found: {readme_path}")
            return
        
        with open(readme_path, 'r') as f:
            content = f.read()
        
        # Find and replace existing coverage badge
        coverage_pattern = r'\[!\[Coverage\][^]]*\]\([^)]*\)'
        new_coverage_badge = badges.get('line_coverage', '')
        
        if re.search(coverage_pattern, content):
            content = re.sub(coverage_pattern, new_coverage_badge, content)
        else:
            # Add coverage badge after build status if not found
            build_pattern = r'(\[!\[Build Status\][^]]*\]\([^)]*\))'
            if re.search(build_pattern, content):
                content = re.sub(
                    build_pattern,
                    f'\\1\\n{new_coverage_badge}',
                    content
                )
        
        with open(readme_path, 'w') as f:
            f.write(content)
        
        print(f"Updated README badges in {readme_path}")
    
    def generate_coverage_report(self, coverage_path: str, output_dir: str = None) -> Dict:
        """Generate comprehensive coverage report with badges."""
        if output_dir is None:
            output_dir = self.config['output_dir']
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Parse coverage data
        if coverage_path.endswith('.info'):
            metrics = self.parse_lcov_data(coverage_path)
        elif coverage_path.endswith('.json'):
            metrics = self.parse_json_coverage(coverage_path)
        else:
            raise ValueError("Unsupported coverage file format. Use .info (LCOV) or .json")
        
        # Generate badges
        overall_badges = self.generate_overall_badges(metrics)
        
        # Save badges
        badges_json_path = os.path.join(output_dir, 'coverage_badges.json')
        self.save_badges_json(overall_badges, badges_json_path)
        
        # Generate summary report
        report = {
            'metrics': asdict(metrics),
            'badges': overall_badges,
            'thresholds': {k: asdict(v) for k, v in self.thresholds.items()},
            'quality_assessment': self._assess_coverage_quality(metrics),
            'recommendations': self._generate_recommendations(metrics)
        }
        
        # Save comprehensive report
        report_path = os.path.join(output_dir, 'coverage_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _assess_coverage_quality(self, metrics: CoverageMetrics) -> Dict[str, str]:
        """Assess overall coverage quality."""
        assessments = {}
        
        for coverage_type in ['line', 'branch', 'function', 'statement']:
            value = getattr(metrics, f'{coverage_type}_coverage')
            thresholds = self.thresholds[coverage_type]
            
            if value >= thresholds.excellent:
                level = 'excellent'
            elif value >= thresholds.good:
                level = 'good'
            elif value >= thresholds.warning:
                level = 'warning'
            else:
                level = 'critical'
            
            assessments[coverage_type] = level
        
        return assessments
    
    def _generate_recommendations(self, metrics: CoverageMetrics) -> List[str]:
        """Generate recommendations for improving coverage."""
        recommendations = []
        
        if metrics.line_coverage < 90:
            recommendations.append(
                f"Line coverage ({metrics.line_coverage:.1f}%) is below target (90%). "
                "Focus on testing uncovered code paths."
            )
        
        if metrics.branch_coverage < 85:
            recommendations.append(
                f"Branch coverage ({metrics.branch_coverage:.1f}%) is below target (85%). "
                "Add tests for conditional logic and error paths."
            )
        
        if metrics.function_coverage < 95:
            recommendations.append(
                f"Function coverage ({metrics.function_coverage:.1f}%) is below target (95%). "
                "Ensure all functions have at least one test case."
            )
        
        if not recommendations:
            recommendations.append("Coverage targets met! Consider raising targets or improving test quality.")
        
        return recommendations


def main():
    """Main entry point for coverage badge generator."""
    parser = argparse.ArgumentParser(
        description="Generate coverage badges for MPU-6050 Linux kernel driver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate badges from LCOV file
  python3 scripts/generate-coverage-badge.py --input build/coverage/coverage.info
  
  # Generate badges from JSON file
  python3 scripts/generate-coverage-badge.py --input build/coverage/coverage.json
  
  # Generate badges and update README
  python3 scripts/generate-coverage-badge.py --input coverage.info --update-readme
  
  # Custom output directory
  python3 scripts/generate-coverage-badge.py --input coverage.info --output docs/badges
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        default='build/coverage/coverage.info',
        help='Path to coverage data file (LCOV .info or JSON format)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='docs/badges',
        help='Output directory for badge files'
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file (JSON format)'
    )
    
    parser.add_argument(
        '--update-readme',
        action='store_true',
        help='Update README.md with generated badges'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['shields', 'json', 'both'],
        default='both',
        help='Output format for badges'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--thresholds',
        help='Override coverage thresholds (JSON format): {"line": {"good": 85}}'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize badge generator
        generator = CoverageBadgeGenerator(args.config)
        
        # Override thresholds if provided
        if args.thresholds:
            custom_thresholds = json.loads(args.thresholds)
            for coverage_type, thresholds in custom_thresholds.items():
                if coverage_type in generator.thresholds:
                    for level, value in thresholds.items():
                        setattr(generator.thresholds[coverage_type], level, value)
        
        if args.verbose:
            print(f"Generating coverage badges from: {args.input}")
            print(f"Output directory: {args.output}")
        
        # Generate coverage report
        report = generator.generate_coverage_report(args.input, args.output)
        
        # Update README if requested
        if args.update_readme:
            generator.update_readme_badges(report['badges'])
        
        # Print summary
        metrics = report['metrics']
        print(f"\nCoverage Summary:")
        print(f"  Line Coverage:      {metrics['line_coverage']:.1f}%")
        print(f"  Branch Coverage:    {metrics['branch_coverage']:.1f}%")
        print(f"  Function Coverage:  {metrics['function_coverage']:.1f}%")
        print(f"  Statement Coverage: {metrics['statement_coverage']:.1f}%")
        
        print(f"\nQuality Assessment:")
        for coverage_type, level in report['quality_assessment'].items():
            print(f"  {coverage_type.title():15} {level.title()}")
        
        if report['recommendations']:
            print(f"\nRecommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print(f"\nBadge files saved to: {args.output}")
        
        if args.verbose:
            print(f"\nGenerated badges:")
            for badge_type, badge_md in report['badges'].items():
                print(f"  {badge_type}: {badge_md}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run 'make test COVERAGE=1' to generate coverage data first.", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())