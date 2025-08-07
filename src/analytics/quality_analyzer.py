#!/usr/bin/env python3
"""
Test Quality Analytics System

Implements test quality scoring, defect detection rate metrics,
false positive/negative tracking, and test effectiveness measurement.
"""

import json
import sqlite3
import statistics
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import logging
import re
import math


@dataclass
class QualityScore:
    """Test quality scoring components."""
    coverage_score: float  # 0-1 based on code coverage achieved
    assertion_score: float  # 0-1 based on assertion quality
    boundary_score: float  # 0-1 based on boundary condition testing
    error_handling_score: float  # 0-1 based on error condition coverage
    maintainability_score: float  # 0-1 based on test complexity/readability
    overall_score: float  # Weighted combination of above scores


@dataclass
class DefectMetrics:
    """Defect detection and prevention metrics."""
    defects_detected: int
    defects_prevented: int
    false_positives: int
    false_negatives: int
    detection_rate: float
    prevention_rate: float
    precision: float
    recall: float
    f1_score: float


@dataclass
class TestEffectiveness:
    """Test effectiveness measurement."""
    test_name: str
    mutation_score: float  # Percentage of mutations caught
    code_coverage: float
    branch_coverage: float
    defect_detection_ability: float
    maintenance_cost: float
    execution_efficiency: float
    overall_effectiveness: float


class QualityAnalyzer:
    """Analyzes test quality and effectiveness."""
    
    def __init__(self, db_path: str = "test_analytics.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()
        self._init_quality_database()
        
        # Quality scoring weights
        self.quality_weights = {
            'coverage': 0.25,
            'assertion': 0.20,
            'boundary': 0.20,
            'error_handling': 0.20,
            'maintainability': 0.15
        }
        
        # Effectiveness thresholds
        self.effectiveness_thresholds = {
            'excellent': 0.90,
            'good': 0.75,
            'acceptable': 0.60,
            'poor': 0.40
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('QualityAnalyzer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_quality_database(self):
        """Initialize database tables for quality metrics."""
        with sqlite3.connect(self.db_path) as conn:
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
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS defect_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_suite TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    defects_detected INTEGER NOT NULL,
                    defects_prevented INTEGER NOT NULL,
                    false_positives INTEGER NOT NULL,
                    false_negatives INTEGER NOT NULL,
                    analysis_period_days INTEGER NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS mutation_test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    mutations_generated INTEGER NOT NULL,
                    mutations_caught INTEGER NOT NULL,
                    mutation_score REAL NOT NULL,
                    uncaught_mutations TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS test_effectiveness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    mutation_score REAL NOT NULL,
                    code_coverage REAL NOT NULL,
                    branch_coverage REAL NOT NULL,
                    defect_detection_ability REAL NOT NULL,
                    maintenance_cost REAL NOT NULL,
                    execution_efficiency REAL NOT NULL,
                    overall_effectiveness REAL NOT NULL
                )
            ''')
    
    def analyze_test_quality(self, test_name: str, test_source: str, 
                           coverage_data: Dict[str, float]) -> QualityScore:
        """Analyze the quality of a specific test."""
        
        # Calculate individual quality components
        coverage_score = self._calculate_coverage_score(coverage_data)
        assertion_score = self._calculate_assertion_score(test_source)
        boundary_score = self._calculate_boundary_score(test_source)
        error_handling_score = self._calculate_error_handling_score(test_source)
        maintainability_score = self._calculate_maintainability_score(test_source)
        
        # Calculate overall score using weights
        overall_score = (
            coverage_score * self.quality_weights['coverage'] +
            assertion_score * self.quality_weights['assertion'] +
            boundary_score * self.quality_weights['boundary'] +
            error_handling_score * self.quality_weights['error_handling'] +
            maintainability_score * self.quality_weights['maintainability']
        )
        
        quality_score = QualityScore(
            coverage_score=coverage_score,
            assertion_score=assertion_score,
            boundary_score=boundary_score,
            error_handling_score=error_handling_score,
            maintainability_score=maintainability_score,
            overall_score=overall_score
        )
        
        # Store in database
        self._store_quality_score(test_name, quality_score)
        
        self.logger.info(f"Quality analysis for {test_name}: {overall_score:.3f}")
        
        return quality_score
    
    def _calculate_coverage_score(self, coverage_data: Dict[str, float]) -> float:
        """Calculate coverage-based quality score."""
        if not coverage_data:
            return 0.0
        
        # Weighted combination of coverage types
        weights = {
            'line_coverage': 0.3,
            'branch_coverage': 0.4,
            'function_coverage': 0.3
        }
        
        score = 0.0
        total_weight = 0.0
        
        for coverage_type, weight in weights.items():
            if coverage_type in coverage_data:
                score += (coverage_data[coverage_type] / 100.0) * weight
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_assertion_score(self, test_source: str) -> float:
        """Calculate assertion quality score."""
        if not test_source:
            return 0.0
        
        # Count different types of assertions
        assertion_patterns = {
            'equality': r'(?:EXPECT_EQ|ASSERT_EQ|assertEqual|assertEquals)',
            'comparison': r'(?:EXPECT_[LG][TE]|ASSERT_[LG][TE]|assert[LG][TE])',
            'boolean': r'(?:EXPECT_TRUE|EXPECT_FALSE|ASSERT_TRUE|ASSERT_FALSE|assertTrue|assertFalse)',
            'exception': r'(?:EXPECT_THROW|ASSERT_THROW|assertRaises|with.*raises)',
            'null_check': r'(?:EXPECT_NULL|ASSERT_NULL|assertIsNone|assertIsNotNone)',
            'near_equal': r'(?:EXPECT_NEAR|ASSERT_NEAR|assertAlmostEqual)'
        }
        
        assertion_types_used = 0
        total_assertions = 0
        
        for pattern_name, pattern in assertion_patterns.items():
            matches = len(re.findall(pattern, test_source, re.IGNORECASE))
            if matches > 0:
                assertion_types_used += 1
                total_assertions += matches
        
        # Score based on variety and quantity of assertions
        variety_score = min(assertion_types_used / len(assertion_patterns), 1.0)
        
        # Lines of test code
        test_lines = len([line for line in test_source.split('\n') 
                         if line.strip() and not line.strip().startswith('//')])
        
        assertion_density = total_assertions / max(test_lines, 1)
        density_score = min(assertion_density * 2, 1.0)  # Optimal around 0.5 assertions per line
        
        return (variety_score * 0.6 + density_score * 0.4)
    
    def _calculate_boundary_score(self, test_source: str) -> float:
        """Calculate boundary condition testing score."""
        boundary_indicators = [
            # Numeric boundaries
            r'(?:MIN|MAX)_\w+',
            r'\b(?:0|1|-1)\b',
            r'(?:INT_MIN|INT_MAX|LONG_MIN|LONG_MAX)',
            r'(?:null|nullptr|NULL)',
            
            # Array/string boundaries
            r'(?:empty|size|length).*(?:0|1)',
            r'(?:first|last|end).*(?:element|index)',
            
            # State boundaries
            r'(?:init|uninitialized|closed|open)',
            r'(?:before|after).*(?:start|end)',
            
            # Range testing
            r'(?:minimum|maximum|limit)',
            r'(?:overflow|underflow)',
            r'(?:boundary|edge).*(?:case|condition)'
        ]
        
        boundary_patterns_found = 0
        for pattern in boundary_indicators:
            if re.search(pattern, test_source, re.IGNORECASE):
                boundary_patterns_found += 1
        
        # Score based on how many boundary patterns are tested
        return min(boundary_patterns_found / len(boundary_indicators), 1.0)
    
    def _calculate_error_handling_score(self, test_source: str) -> float:
        """Calculate error handling testing score."""
        error_patterns = [
            # Exception handling
            r'(?:try|catch|except|finally)',
            r'(?:throw|throws|raise)',
            r'(?:Exception|Error)',
            
            # Error conditions
            r'(?:invalid|illegal).*(?:argument|parameter|input)',
            r'(?:null|nullptr|NULL).*(?:pointer|reference)',
            r'(?:out.*of.*bounds|index.*error)',
            r'(?:timeout|expired)',
            r'(?:connection.*(?:failed|lost|refused))',
            r'(?:permission.*denied|access.*denied)',
            r'(?:file.*not.*found|path.*not.*found)',
            r'(?:memory.*(?:allocation|insufficient))',
            
            # Return code checking
            r'(?:return.*code|status.*code|error.*code)',
            r'(?:EXPECT|ASSERT).*(?:FAIL|ERROR|THROW)'
        ]
        
        error_patterns_found = 0
        for pattern in error_patterns:
            if re.search(pattern, test_source, re.IGNORECASE):
                error_patterns_found += 1
        
        return min(error_patterns_found / len(error_patterns), 1.0)
    
    def _calculate_maintainability_score(self, test_source: str) -> float:
        """Calculate test maintainability score."""
        lines = test_source.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        if not non_empty_lines:
            return 0.0
        
        # Factor 1: Test size (smaller is better for maintainability)
        size_penalty = min(len(non_empty_lines) / 100.0, 1.0)  # Penalty starts at 100 lines
        size_score = 1.0 - size_penalty
        
        # Factor 2: Complexity (fewer nested structures is better)
        nesting_levels = []
        for line in non_empty_lines:
            leading_spaces = len(line) - len(line.lstrip())
            nesting_levels.append(leading_spaces // 4)  # Assuming 4-space indentation
        
        max_nesting = max(nesting_levels) if nesting_levels else 0
        nesting_score = 1.0 - min(max_nesting / 8.0, 1.0)  # Penalty for deep nesting
        
        # Factor 3: Documentation (comments and descriptive names)
        comment_lines = len([line for line in lines if line.strip().startswith('//')])
        documentation_score = min(comment_lines / max(len(non_empty_lines), 1) * 4, 1.0)
        
        # Factor 4: Variable naming quality (descriptive names)
        descriptive_names = 0
        variable_pattern = r'\b(?:test|expect|actual|expected|result|input|output)\w*\b'
        for line in non_empty_lines:
            if re.search(variable_pattern, line, re.IGNORECASE):
                descriptive_names += 1
        
        naming_score = min(descriptive_names / max(len(non_empty_lines), 1) * 2, 1.0)
        
        # Combined maintainability score
        return (size_score * 0.3 + nesting_score * 0.25 + 
                documentation_score * 0.2 + naming_score * 0.25)
    
    def _store_quality_score(self, test_name: str, quality_score: QualityScore):
        """Store quality score in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO test_quality_scores 
                (test_name, timestamp, coverage_score, assertion_score, 
                 boundary_score, error_handling_score, maintainability_score, overall_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_name,
                datetime.now().isoformat(),
                quality_score.coverage_score,
                quality_score.assertion_score,
                quality_score.boundary_score,
                quality_score.error_handling_score,
                quality_score.maintainability_score,
                quality_score.overall_score
            ))
    
    def calculate_defect_metrics(self, test_suite: str, 
                               analysis_period_days: int = 30) -> DefectMetrics:
        """Calculate defect detection and prevention metrics."""
        cutoff_date = datetime.now() - timedelta(days=analysis_period_days)
        
        # Get test execution data for the period
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT status, error_message FROM test_executions 
                WHERE test_category = ? AND timestamp > ?
            ''', (test_suite, cutoff_date.isoformat()))
            
            executions = cursor.fetchall()
        
        if not executions:
            return DefectMetrics(0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Analyze execution results
        total_executions = len(executions)
        failed_executions = [e for e in executions if e[0] == 'FAILED']
        
        # Classify failures (this would need to be enhanced with real failure analysis)
        defects_detected = len([f for f in failed_executions 
                               if self._is_real_defect(f[1])])
        false_positives = len(failed_executions) - defects_detected
        
        # Estimate prevented defects based on test effectiveness
        # This is a simplified model - real implementation would need historical data
        test_effectiveness = self.calculate_test_effectiveness(test_suite)
        estimated_total_defects = int(defects_detected / max(test_effectiveness, 0.1))
        defects_prevented = estimated_total_defects - defects_detected
        
        # False negatives are harder to detect - estimate based on production issues
        # For now, use a conservative estimate
        false_negatives = max(0, int(defects_detected * 0.1))  # Assume 10% FN rate
        
        # Calculate rates
        detection_rate = defects_detected / max(estimated_total_defects, 1)
        prevention_rate = defects_prevented / max(estimated_total_defects, 1)
        
        # Calculate precision, recall, F1
        true_positives = defects_detected
        precision = true_positives / max(true_positives + false_positives, 1)
        recall = true_positives / max(true_positives + false_negatives, 1)
        f1_score = (2 * precision * recall) / max(precision + recall, 0.001)
        
        defect_metrics = DefectMetrics(
            defects_detected=defects_detected,
            defects_prevented=defects_prevented,
            false_positives=false_positives,
            false_negatives=false_negatives,
            detection_rate=detection_rate,
            prevention_rate=prevention_rate,
            precision=precision,
            recall=recall,
            f1_score=f1_score
        )
        
        # Store in database
        self._store_defect_metrics(test_suite, defect_metrics, analysis_period_days)
        
        return defect_metrics
    
    def _is_real_defect(self, error_message: Optional[str]) -> bool:
        """Determine if a failure represents a real defect (vs test issue)."""
        if not error_message:
            return False
        
        # Patterns that indicate real defects
        defect_patterns = [
            r'assertion.*failed',
            r'unexpected.*value',
            r'null.*pointer',
            r'segmentation.*fault',
            r'memory.*leak',
            r'buffer.*overflow',
            r'race.*condition',
            r'deadlock',
            r'timeout.*exceeded',
            r'invalid.*state'
        ]
        
        # Patterns that indicate test infrastructure issues
        infrastructure_patterns = [
            r'test.*setup.*failed',
            r'mock.*not.*configured',
            r'fixture.*initialization',
            r'environment.*not.*ready',
            r'dependency.*unavailable'
        ]
        
        error_lower = error_message.lower()
        
        # Check for infrastructure issues first
        for pattern in infrastructure_patterns:
            if re.search(pattern, error_lower):
                return False
        
        # Check for defect patterns
        for pattern in defect_patterns:
            if re.search(pattern, error_lower):
                return True
        
        # Default: assume it's a real defect if we can't classify it
        return True
    
    def _store_defect_metrics(self, test_suite: str, metrics: DefectMetrics, 
                             analysis_period_days: int):
        """Store defect metrics in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO defect_tracking 
                (test_suite, timestamp, defects_detected, defects_prevented, 
                 false_positives, false_negatives, analysis_period_days)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_suite,
                datetime.now().isoformat(),
                metrics.defects_detected,
                metrics.defects_prevented,
                metrics.false_positives,
                metrics.false_negatives,
                analysis_period_days
            ))
    
    def record_mutation_test_results(self, test_name: str, mutations_generated: int,
                                   mutations_caught: int, uncaught_mutations: List[str]):
        """Record mutation testing results."""
        mutation_score = (mutations_caught / max(mutations_generated, 1)) * 100
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO mutation_test_results 
                (test_name, timestamp, mutations_generated, mutations_caught, 
                 mutation_score, uncaught_mutations)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                test_name,
                datetime.now().isoformat(),
                mutations_generated,
                mutations_caught,
                mutation_score,
                json.dumps(uncaught_mutations)
            ))
        
        self.logger.info(f"Mutation test results for {test_name}: "
                        f"{mutations_caught}/{mutations_generated} ({mutation_score:.1f}%)")
    
    def calculate_test_effectiveness(self, test_name: str) -> float:
        """Calculate overall test effectiveness score."""
        # Get recent quality scores
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT overall_score FROM test_quality_scores 
                WHERE test_name = ? 
                ORDER BY timestamp DESC LIMIT 1
            ''', (test_name,))
            
            result = cursor.fetchone()
            quality_score = result[0] if result else 0.5
            
            # Get mutation test results
            cursor = conn.execute('''
                SELECT mutation_score FROM mutation_test_results 
                WHERE test_name = ? 
                ORDER BY timestamp DESC LIMIT 1
            ''', (test_name,))
            
            result = cursor.fetchone()
            mutation_score = (result[0] / 100.0) if result else 0.5
            
            # Get defect detection ability (from recent executions)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor = conn.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'FAILED' AND error_message IS NOT NULL 
                           THEN 1 ELSE 0 END) as failures
                FROM test_executions 
                WHERE test_name = ? AND timestamp > ?
            ''', (test_name, week_ago))
            
            total, failures = cursor.fetchone()
            defect_detection = (failures / max(total, 1)) if total > 0 else 0.0
        
        # Combine scores with weights
        effectiveness = (
            quality_score * 0.4 +
            mutation_score * 0.4 +
            defect_detection * 0.2
        )
        
        return effectiveness
    
    def get_quality_trends(self, test_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get quality trend data for a test."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT timestamp, overall_score, coverage_score, assertion_score,
                       boundary_score, error_handling_score, maintainability_score
                FROM test_quality_scores 
                WHERE test_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (test_name, cutoff_date.isoformat()))
            
            return [{
                'timestamp': datetime.fromisoformat(row[0]),
                'overall_score': row[1],
                'coverage_score': row[2],
                'assertion_score': row[3],
                'boundary_score': row[4],
                'error_handling_score': row[5],
                'maintainability_score': row[6]
            } for row in cursor.fetchall()]
    
    def get_quality_recommendations(self, test_name: str) -> List[str]:
        """Get recommendations for improving test quality."""
        recommendations = []
        
        # Get latest quality scores
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT coverage_score, assertion_score, boundary_score,
                       error_handling_score, maintainability_score
                FROM test_quality_scores 
                WHERE test_name = ? 
                ORDER BY timestamp DESC LIMIT 1
            ''', (test_name,))
            
            result = cursor.fetchone()
            if not result:
                return ["No quality data available for this test"]
            
            coverage, assertion, boundary, error_handling, maintainability = result
        
        # Generate specific recommendations
        if coverage < 0.8:
            recommendations.append(
                f"Improve code coverage (current: {coverage:.1%}). "
                "Add tests for uncovered branches and functions."
            )
        
        if assertion < 0.7:
            recommendations.append(
                f"Enhance assertion quality (current: {assertion:.1%}). "
                "Use more diverse assertion types and increase assertion density."
            )
        
        if boundary < 0.6:
            recommendations.append(
                f"Add more boundary condition tests (current: {boundary:.1%}). "
                "Test edge cases, null values, and limit conditions."
            )
        
        if error_handling < 0.6:
            recommendations.append(
                f"Improve error handling coverage (current: {error_handling:.1%}). "
                "Add tests for exception conditions and error paths."
            )
        
        if maintainability < 0.7:
            recommendations.append(
                f"Enhance test maintainability (current: {maintainability:.1%}). "
                "Reduce complexity, add comments, use descriptive names."
            )
        
        if not recommendations:
            recommendations.append("Test quality is good across all dimensions!")
        
        return recommendations
    
    def export_quality_report(self, output_path: str, days: int = 30):
        """Export comprehensive quality report."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all tests with quality scores
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT DISTINCT test_name FROM test_quality_scores 
                WHERE timestamp > ?
            ''', (cutoff_date.isoformat(),))
            
            test_names = [row[0] for row in cursor.fetchall()]
        
        # Collect data for each test
        test_reports = {}
        for test_name in test_names:
            trends = self.get_quality_trends(test_name, days)
            recommendations = self.get_quality_recommendations(test_name)
            effectiveness = self.calculate_test_effectiveness(test_name)
            
            test_reports[test_name] = {
                'quality_trends': [
                    {**trend, 'timestamp': trend['timestamp'].isoformat()} 
                    for trend in trends
                ],
                'recommendations': recommendations,
                'effectiveness_score': effectiveness,
                'effectiveness_level': self._get_effectiveness_level(effectiveness)
            }
        
        # Generate summary statistics
        all_scores = []
        for trends in [test_reports[test]['quality_trends'] for test in test_reports]:
            if trends:
                all_scores.extend([trend['overall_score'] for trend in trends])
        
        summary = {
            'total_tests_analyzed': len(test_names),
            'average_quality_score': statistics.mean(all_scores) if all_scores else 0,
            'quality_distribution': {
                'excellent': len([s for s in all_scores if s >= 0.9]),
                'good': len([s for s in all_scores if 0.75 <= s < 0.9]),
                'acceptable': len([s for s in all_scores if 0.6 <= s < 0.75]),
                'poor': len([s for s in all_scores if s < 0.6])
            }
        }
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_period_days': days,
            'summary': summary,
            'test_reports': test_reports
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Quality report exported to {output_path}")
    
    def _get_effectiveness_level(self, score: float) -> str:
        """Convert effectiveness score to level description."""
        for level, threshold in sorted(self.effectiveness_thresholds.items(), 
                                     key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return level
        return 'very_poor'


if __name__ == "__main__":
    # Example usage
    analyzer = QualityAnalyzer()
    
    # Example test source for analysis
    test_source = '''
    void test_mpu6050_init() {
        // Test normal initialization
        mpu6050_dev_t device;
        int result = mpu6050_init(&device, I2C_ADDR);
        EXPECT_EQ(result, MPU6050_SUCCESS);
        EXPECT_TRUE(device.initialized);
        
        // Test null pointer
        result = mpu6050_init(nullptr, I2C_ADDR);
        EXPECT_EQ(result, MPU6050_ERROR_NULL_PTR);
        
        // Test invalid address
        result = mpu6050_init(&device, INVALID_ADDR);
        EXPECT_EQ(result, MPU6050_ERROR_INVALID_ADDR);
        
        // Test boundary conditions
        result = mpu6050_init(&device, 0x68);  // MIN valid address
        EXPECT_EQ(result, MPU6050_SUCCESS);
        
        result = mpu6050_init(&device, 0x69);  // MAX valid address
        EXPECT_EQ(result, MPU6050_SUCCESS);
    }
    '''
    
    coverage_data = {
        'line_coverage': 85.5,
        'branch_coverage': 78.2,
        'function_coverage': 92.1
    }
    
    # Analyze test quality
    quality = analyzer.analyze_test_quality("test_mpu6050_init", test_source, coverage_data)
    print(f"Quality score: {quality.overall_score:.3f}")
    
    # Get recommendations
    recommendations = analyzer.get_quality_recommendations("test_mpu6050_init")
    print("Recommendations:")
    for rec in recommendations:
        print(f"  - {rec}")
    
    # Export quality report
    analyzer.export_quality_report("quality_report.json")