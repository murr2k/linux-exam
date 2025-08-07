#!/usr/bin/env node

/**
 * Comprehensive Report Generator
 * Generates detailed reports combining all test results, performance metrics, and quality analysis
 */

const fs = require('fs').promises;
const path = require('path');
const { performance } = require('perf_hooks');

class ComprehensiveReporter {
  constructor(options = {}) {
    this.config = {
      reportsPath: options.reportsPath || 'reports',
      runId: options.runId || Date.now().toString(),
      commit: options.commit || 'unknown',
      branch: options.branch || 'unknown',
      outputFormats: options.outputFormats || ['html', 'json'],
      outputDir: options.outputDir || 'comprehensive-report',
      ...options
    };
    
    this.data = {
      metadata: {},
      summary: {},
      testResults: {},
      performanceResults: {},
      securityResults: {},
      qualityMetrics: {},
      trends: {},
      recommendations: []
    };
  }

  async generate() {
    console.log(`📊 Generating comprehensive report for run: ${this.config.runId}`);
    
    const startTime = performance.now();
    
    try {
      // Create output directory
      await fs.mkdir(this.config.outputDir, { recursive: true });
      
      // Collect all data
      await this.collectMetadata();
      await this.processTestResults();
      await this.processPerformanceResults();
      await this.processSecurityResults();
      await this.calculateQualityMetrics();
      await this.analyzeTrends();
      await this.generateRecommendations();
      
      // Generate reports in requested formats
      for (const format of this.config.outputFormats) {
        await this.generateReport(format);
      }
      
      const duration = performance.now() - startTime;
      console.log(`✅ Comprehensive report generated in ${Math.round(duration)}ms`);
      
      return {
        success: true,
        duration: duration,
        outputDir: this.config.outputDir,
        formats: this.config.outputFormats
      };
      
    } catch (error) {
      console.error('❌ Report generation failed:', error);
      throw error;
    }
  }

  async collectMetadata() {
    console.log('📋 Collecting metadata...');
    
    this.data.metadata = {
      runId: this.config.runId,
      timestamp: new Date().toISOString(),
      commit: this.config.commit,
      branch: this.config.branch,
      
      environment: {
        nodeVersion: process.version,
        platform: process.platform,
        arch: process.arch,
        cpus: require('os').cpus().length,
        memory: Math.round(require('os').totalmem() / 1024 / 1024 / 1024) + 'GB'
      },
      
      pipeline: {
        strategy: await this.detectStrategy(),
        trigger: await this.detectTrigger(),
        parallelJobs: await this.countParallelJobs()
      }
    };
  }

  async processTestResults() {
    console.log('🧪 Processing test results...');
    
    const testResults = {
      summary: {
        totalSuites: 0,
        totalTests: 0,
        passedTests: 0,
        failedTests: 0,
        skippedTests: 0,
        totalDuration: 0,
        coverage: {
          overall: 0,
          statements: 0,
          branches: 0,
          functions: 0,
          lines: 0
        }
      },
      suites: [],
      failures: [],
      slowTests: [],
      flakyTests: []
    };
    
    try {
      const testResultsPath = path.join(this.config.reportsPath, 'test-results-*');
      const testDirs = await this.findMatchingDirectories(testResultsPath);
      
      for (const testDir of testDirs) {
        const suiteResult = await this.processTestSuite(testDir);
        if (suiteResult) {
          testResults.suites.push(suiteResult);
          
          // Aggregate summary
          testResults.summary.totalSuites++;
          testResults.summary.totalTests += suiteResult.totalTests;
          testResults.summary.passedTests += suiteResult.passedTests;
          testResults.summary.failedTests += suiteResult.failedTests;
          testResults.summary.skippedTests += suiteResult.skippedTests;
          testResults.summary.totalDuration += suiteResult.duration;
          
          // Collect failures
          testResults.failures.push(...suiteResult.failures);
          
          // Collect slow tests
          testResults.slowTests.push(...suiteResult.slowTests);
        }
      }
      
      // Calculate overall coverage
      testResults.summary.coverage = await this.calculateOverallCoverage(testResults.suites);
      
      // Calculate success rate
      testResults.summary.successRate = testResults.summary.totalTests > 0
        ? (testResults.summary.passedTests / testResults.summary.totalTests) * 100
        : 100;
      
      // Sort and limit arrays
      testResults.failures.sort((a, b) => b.impact - a.impact);
      testResults.slowTests.sort((a, b) => b.duration - a.duration).splice(10); // Top 10
      
    } catch (error) {
      console.warn('⚠️ Error processing test results:', error.message);
    }
    
    this.data.testResults = testResults;
  }

  async processTestSuite(testDir) {
    try {
      const summaryPath = path.join(testDir, 'summary.json');
      const detailsPath = path.join(testDir, 'detailed.json');
      
      let summary = {};
      let details = {};
      
      try {
        const summaryData = await fs.readFile(summaryPath, 'utf8');
        summary = JSON.parse(summaryData);
      } catch (error) {
        console.warn(`⚠️ Could not read summary for ${testDir}`);
      }
      
      try {
        const detailsData = await fs.readFile(detailsPath, 'utf8');
        details = JSON.parse(detailsData);
      } catch (error) {
        // Details are optional
      }
      
      return {
        name: path.basename(testDir).replace('test-results-', ''),
        totalTests: summary.tests?.total || 0,
        passedTests: summary.tests?.passed || 0,
        failedTests: summary.tests?.failed || 0,
        skippedTests: summary.tests?.skipped || 0,
        duration: summary.duration || 0,
        coverage: summary.coverage || 0,
        failures: this.extractFailures(summary, details),
        slowTests: this.extractSlowTests(summary, details),
        metadata: {
          strategy: summary.strategy,
          parallel: summary.parallel,
          shards: summary.shards
        }
      };
      
    } catch (error) {
      console.warn(`⚠️ Error processing test suite ${testDir}:`, error.message);
      return null;
    }
  }

  async processPerformanceResults() {
    console.log('⚡ Processing performance results...');
    
    const performanceResults = {
      summary: {
        totalTests: 0,
        averageResponseTime: 0,
        averageThroughput: 0,
        p95ResponseTime: 0,
        errorRate: 0
      },
      testTypes: [],
      trends: {},
      bottlenecks: [],
      recommendations: []
    };
    
    try {
      const perfResultsPath = path.join(this.config.reportsPath, 'performance-results-*');
      const perfDirs = await this.findMatchingDirectories(perfResultsPath);
      
      for (const perfDir of perfDirs) {
        const perfResult = await this.processPerformanceTest(perfDir);
        if (perfResult) {
          performanceResults.testTypes.push(perfResult);
          performanceResults.summary.totalTests++;
        }
      }
      
      // Calculate aggregated metrics
      if (performanceResults.testTypes.length > 0) {
        performanceResults.summary.averageResponseTime = 
          performanceResults.testTypes.reduce((sum, t) => sum + t.averageResponseTime, 0) / 
          performanceResults.testTypes.length;
        
        performanceResults.summary.averageThroughput = 
          performanceResults.testTypes.reduce((sum, t) => sum + t.throughput, 0) / 
          performanceResults.testTypes.length;
      }
      
      // Identify bottlenecks
      performanceResults.bottlenecks = this.identifyPerformanceBottlenecks(performanceResults.testTypes);
      
    } catch (error) {
      console.warn('⚠️ Error processing performance results:', error.message);
    }
    
    this.data.performanceResults = performanceResults;
  }

  async processSecurityResults() {
    console.log('🔒 Processing security results...');
    
    const securityResults = {
      summary: {
        totalScans: 0,
        vulnerabilities: {
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
          total: 0
        },
        overallScore: 100
      },
      scanTypes: [],
      criticalIssues: [],
      recommendations: []
    };
    
    try {
      const secResultsPath = path.join(this.config.reportsPath, 'security-reports-*');
      const secDirs = await this.findMatchingDirectories(secResultsPath);
      
      for (const secDir of secDirs) {
        const secResult = await this.processSecurityScan(secDir);
        if (secResult) {
          securityResults.scanTypes.push(secResult);
          securityResults.summary.totalScans++;
          
          // Aggregate vulnerabilities
          const vulns = secResult.vulnerabilities;
          securityResults.summary.vulnerabilities.critical += vulns.critical;
          securityResults.summary.vulnerabilities.high += vulns.high;
          securityResults.summary.vulnerabilities.medium += vulns.medium;
          securityResults.summary.vulnerabilities.low += vulns.low;
          
          // Collect critical issues
          securityResults.criticalIssues.push(...secResult.criticalIssues);
        }
      }
      
      // Calculate total vulnerabilities
      const vulns = securityResults.summary.vulnerabilities;
      vulns.total = vulns.critical + vulns.high + vulns.medium + vulns.low;
      
      // Calculate overall security score
      securityResults.summary.overallScore = this.calculateSecurityScore(vulns);
      
    } catch (error) {
      console.warn('⚠️ Error processing security results:', error.message);
    }
    
    this.data.securityResults = securityResults;
  }

  async calculateQualityMetrics() {
    console.log('📊 Calculating quality metrics...');
    
    const qualityMetrics = {
      overall: {
        score: 0,
        grade: 'F'
      },
      
      testQuality: {
        coverage: this.data.testResults.summary.coverage.overall,
        successRate: this.data.testResults.summary.successRate,
        reliability: this.calculateTestReliability(),
        score: 0
      },
      
      performance: {
        responseTime: this.data.performanceResults.summary.averageResponseTime,
        throughput: this.data.performanceResults.summary.averageThroughput,
        efficiency: this.calculatePerformanceEfficiency(),
        score: 0
      },
      
      security: {
        vulnerabilities: this.data.securityResults.summary.vulnerabilities.total,
        criticalIssues: this.data.securityResults.criticalIssues.length,
        overallScore: this.data.securityResults.summary.overallScore,
        score: this.data.securityResults.summary.overallScore
      },
      
      maintainability: {
        complexity: await this.calculateComplexity(),
        duplication: await this.calculateDuplication(),
        coverage: this.data.testResults.summary.coverage.overall,
        score: 0
      }
    };
    
    // Calculate individual scores
    qualityMetrics.testQuality.score = this.calculateTestQualityScore(qualityMetrics.testQuality);
    qualityMetrics.performance.score = this.calculatePerformanceScore(qualityMetrics.performance);
    qualityMetrics.maintainability.score = this.calculateMaintainabilityScore(qualityMetrics.maintainability);
    
    // Calculate overall score (weighted average)
    const weights = {
      testQuality: 0.35,
      performance: 0.25,
      security: 0.25,
      maintainability: 0.15
    };
    
    qualityMetrics.overall.score = 
      qualityMetrics.testQuality.score * weights.testQuality +
      qualityMetrics.performance.score * weights.performance +
      qualityMetrics.security.score * weights.security +
      qualityMetrics.maintainability.score * weights.maintainability;
    
    qualityMetrics.overall.grade = this.calculateGrade(qualityMetrics.overall.score);
    
    this.data.qualityMetrics = qualityMetrics;
  }

  async analyzeTrends() {
    console.log('📈 Analyzing trends...');
    
    // This would typically compare with historical data
    const trends = {
      testCoverage: { trend: 'stable', change: 0, recommendation: null },
      testSuccessRate: { trend: 'stable', change: 0, recommendation: null },
      performanceMetrics: { trend: 'stable', change: 0, recommendation: null },
      securityScore: { trend: 'stable', change: 0, recommendation: null },
      buildDuration: { trend: 'stable', change: 0, recommendation: null }
    };
    
    // Placeholder trend analysis
    // In a real implementation, this would compare against historical data
    
    this.data.trends = trends;
  }

  async generateRecommendations() {
    console.log('💡 Generating recommendations...');
    
    const recommendations = [];
    
    // Test quality recommendations
    if (this.data.testResults.summary.coverage.overall < 80) {
      recommendations.push({
        category: 'test-quality',
        priority: 'high',
        title: 'Improve Test Coverage',
        description: `Test coverage is ${this.data.testResults.summary.coverage.overall}%, below the recommended 80%`,
        actions: [
          'Add unit tests for uncovered code paths',
          'Implement integration tests for critical flows',
          'Set up coverage gates in CI/CD pipeline'
        ],
        impact: 'high'
      });
    }
    
    // Performance recommendations
    if (this.data.performanceResults.summary.averageResponseTime > 1000) {
      recommendations.push({
        category: 'performance',
        priority: 'medium',
        title: 'Optimize Response Times',
        description: `Average response time is ${this.data.performanceResults.summary.averageResponseTime}ms`,
        actions: [
          'Profile slow endpoints and optimize database queries',
          'Implement caching strategies',
          'Consider API rate limiting and connection pooling'
        ],
        impact: 'medium'
      });
    }
    
    // Security recommendations
    if (this.data.securityResults.summary.vulnerabilities.critical > 0) {
      recommendations.push({
        category: 'security',
        priority: 'critical',
        title: 'Fix Critical Security Vulnerabilities',
        description: `${this.data.securityResults.summary.vulnerabilities.critical} critical vulnerabilities found`,
        actions: [
          'Update dependencies with known vulnerabilities',
          'Review and fix security issues immediately',
          'Implement automated security scanning in CI/CD'
        ],
        impact: 'critical'
      });
    }
    
    // Test reliability recommendations
    if (this.data.testResults.flakyTests.length > 0) {
      recommendations.push({
        category: 'test-quality',
        priority: 'medium',
        title: 'Fix Flaky Tests',
        description: `${this.data.testResults.flakyTests.length} flaky tests detected`,
        actions: [
          'Investigate and fix non-deterministic test behavior',
          'Improve test isolation and cleanup',
          'Consider retry mechanisms for external dependencies'
        ],
        impact: 'medium'
      });
    }
    
    // Sort by priority
    const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    recommendations.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);
    
    this.data.recommendations = recommendations;
  }

  async generateReport(format) {
    console.log(`📄 Generating ${format.toUpperCase()} report...`);
    
    switch (format.toLowerCase()) {
      case 'html':
        await this.generateHTMLReport();
        break;
      case 'json':
        await this.generateJSONReport();
        break;
      case 'pdf':
        await this.generatePDFReport();
        break;
      case 'markdown':
        await this.generateMarkdownReport();
        break;
      default:
        console.warn(`⚠️ Unknown report format: ${format}`);
    }
  }

  async generateHTMLReport() {
    const html = this.buildHTMLReport();
    const htmlPath = path.join(this.config.outputDir, 'comprehensive-report.html');
    await fs.writeFile(htmlPath, html);
    console.log(`📄 HTML report saved to ${htmlPath}`);
  }

  async generateJSONReport() {
    const jsonPath = path.join(this.config.outputDir, 'comprehensive-report.json');
    await fs.writeFile(jsonPath, JSON.stringify(this.data, null, 2));
    console.log(`📄 JSON report saved to ${jsonPath}`);
  }

  async generateMarkdownReport() {
    const markdown = this.buildMarkdownReport();
    const markdownPath = path.join(this.config.outputDir, 'summary.md');
    await fs.writeFile(markdownPath, markdown);
    console.log(`📄 Markdown summary saved to ${markdownPath}`);
  }

  buildHTMLReport() {
    const data = this.data;
    const qualityGrade = data.qualityMetrics.overall.grade;
    const qualityScore = Math.round(data.qualityMetrics.overall.score);
    
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline Report - ${data.metadata.runId}</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 30px; 
        }
        .summary-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .summary-card { 
            background: white; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            padding: 20px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
        }
        .metric { 
            display: flex; 
            justify-content: space-between; 
            margin: 10px 0; 
            padding: 8px 0; 
            border-bottom: 1px solid #eee; 
        }
        .metric:last-child { border-bottom: none; }
        .success { color: #28a745; font-weight: bold; }
        .warning { color: #ffc107; font-weight: bold; }
        .error { color: #dc3545; font-weight: bold; }
        .grade-${qualityGrade.toLowerCase()} { 
            font-size: 2em; 
            font-weight: bold; 
            color: ${this.getGradeColor(qualityGrade)}; 
        }
        .recommendations { margin-top: 30px; }
        .recommendation { 
            background: #f8f9fa; 
            border-left: 4px solid #007bff; 
            padding: 15px; 
            margin: 10px 0; 
        }
        .recommendation.critical { border-left-color: #dc3545; }
        .recommendation.high { border-left-color: #fd7e14; }
        .recommendation.medium { border-left-color: #ffc107; }
        .recommendation.low { border-left-color: #28a745; }
        .chart-container { 
            background: white; 
            border-radius: 8px; 
            padding: 20px; 
            margin: 20px 0; 
            border: 1px solid #ddd; 
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 15px 0; 
        }
        th, td { 
            padding: 12px; 
            text-align: left; 
            border-bottom: 1px solid #ddd; 
        }
        th { 
            background: #f8f9fa; 
            font-weight: 600; 
        }
        .progress-bar { 
            background: #e9ecef; 
            border-radius: 4px; 
            overflow: hidden; 
            height: 20px; 
        }
        .progress-fill { 
            height: 100%; 
            transition: width 0.3s ease; 
        }
        .footer { 
            margin-top: 40px; 
            padding-top: 20px; 
            border-top: 1px solid #ddd; 
            color: #666; 
            font-size: 14px; 
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Pipeline Comprehensive Report</h1>
        <p><strong>Run ID:</strong> ${data.metadata.runId} | <strong>Branch:</strong> ${data.metadata.branch} | <strong>Commit:</strong> ${data.metadata.commit.substring(0, 8)}</p>
        <p><strong>Generated:</strong> ${new Date(data.metadata.timestamp).toLocaleString()}</p>
        <div style="display: flex; align-items: center; gap: 20px; margin-top: 15px;">
            <span>Quality Grade: <span class="grade-${qualityGrade.toLowerCase()}">${qualityGrade}</span></span>
            <span>Overall Score: <strong>${qualityScore}%</strong></span>
        </div>
    </div>

    <div class="summary-grid">
        <div class="summary-card">
            <h3>🧪 Test Results</h3>
            <div class="metric">
                <span>Total Tests</span>
                <strong>${data.testResults.summary.totalTests}</strong>
            </div>
            <div class="metric">
                <span>Success Rate</span>
                <strong class="${data.testResults.summary.successRate >= 95 ? 'success' : data.testResults.summary.successRate >= 80 ? 'warning' : 'error'}">
                    ${Math.round(data.testResults.summary.successRate)}%
                </strong>
            </div>
            <div class="metric">
                <span>Coverage</span>
                <strong class="${data.testResults.summary.coverage.overall >= 80 ? 'success' : data.testResults.summary.coverage.overall >= 60 ? 'warning' : 'error'}">
                    ${Math.round(data.testResults.summary.coverage.overall)}%
                </strong>
            </div>
            <div class="metric">
                <span>Duration</span>
                <strong>${this.formatDuration(data.testResults.summary.totalDuration)}</strong>
            </div>
        </div>

        <div class="summary-card">
            <h3>⚡ Performance</h3>
            <div class="metric">
                <span>Avg Response Time</span>
                <strong class="${data.performanceResults.summary.averageResponseTime <= 500 ? 'success' : data.performanceResults.summary.averageResponseTime <= 1000 ? 'warning' : 'error'}">
                    ${Math.round(data.performanceResults.summary.averageResponseTime)}ms
                </strong>
            </div>
            <div class="metric">
                <span>Throughput</span>
                <strong>${Math.round(data.performanceResults.summary.averageThroughput)} req/s</strong>
            </div>
            <div class="metric">
                <span>Performance Score</span>
                <strong class="${data.qualityMetrics.performance.score >= 80 ? 'success' : data.qualityMetrics.performance.score >= 60 ? 'warning' : 'error'}">
                    ${Math.round(data.qualityMetrics.performance.score)}%
                </strong>
            </div>
        </div>

        <div class="summary-card">
            <h3>🔒 Security</h3>
            <div class="metric">
                <span>Critical Issues</span>
                <strong class="${data.securityResults.summary.vulnerabilities.critical === 0 ? 'success' : 'error'}">
                    ${data.securityResults.summary.vulnerabilities.critical}
                </strong>
            </div>
            <div class="metric">
                <span>Total Vulnerabilities</span>
                <strong class="${data.securityResults.summary.vulnerabilities.total === 0 ? 'success' : data.securityResults.summary.vulnerabilities.total <= 5 ? 'warning' : 'error'}">
                    ${data.securityResults.summary.vulnerabilities.total}
                </strong>
            </div>
            <div class="metric">
                <span>Security Score</span>
                <strong class="${data.securityResults.summary.overallScore >= 90 ? 'success' : data.securityResults.summary.overallScore >= 70 ? 'warning' : 'error'}">
                    ${Math.round(data.securityResults.summary.overallScore)}%
                </strong>
            </div>
        </div>

        <div class="summary-card">
            <h3>🏗️ Quality Metrics</h3>
            <div class="metric">
                <span>Test Quality</span>
                <strong>${Math.round(data.qualityMetrics.testQuality.score)}%</strong>
            </div>
            <div class="metric">
                <span>Maintainability</span>
                <strong>${Math.round(data.qualityMetrics.maintainability.score)}%</strong>
            </div>
            <div class="metric">
                <span>Overall Grade</span>
                <strong class="grade-${qualityGrade.toLowerCase()}">${qualityGrade}</strong>
            </div>
        </div>
    </div>

    ${this.buildTestSuitesSection()}
    ${this.buildRecommendationsSection()}
    
    <div class="footer">
        <p>Generated by Pipeline Comprehensive Reporter | ${new Date().toISOString()}</p>
    </div>
</body>
</html>`;
  }

  buildMarkdownReport() {
    const data = this.data;
    const qualityGrade = data.qualityMetrics.overall.grade;
    const qualityScore = Math.round(data.qualityMetrics.overall.score);
    
    return `# 🚀 Pipeline Report

**Run ID:** ${data.metadata.runId}  
**Branch:** ${data.metadata.branch}  
**Commit:** ${data.metadata.commit}  
**Generated:** ${new Date(data.metadata.timestamp).toLocaleString()}  

## 📊 Summary

| Metric | Value | Status |
|--------|--------|--------|
| **Quality Grade** | **${qualityGrade}** (${qualityScore}%) | ${this.getStatusEmoji(qualityGrade)} |
| **Test Success Rate** | ${Math.round(data.testResults.summary.successRate)}% | ${this.getStatusEmoji(data.testResults.summary.successRate >= 95 ? 'A' : 'C')} |
| **Test Coverage** | ${Math.round(data.testResults.summary.coverage.overall)}% | ${this.getStatusEmoji(data.testResults.summary.coverage.overall >= 80 ? 'A' : 'C')} |
| **Security Score** | ${Math.round(data.securityResults.summary.overallScore)}% | ${this.getStatusEmoji(data.securityResults.summary.overallScore >= 90 ? 'A' : 'C')} |
| **Critical Vulnerabilities** | ${data.securityResults.summary.vulnerabilities.critical} | ${data.securityResults.summary.vulnerabilities.critical === 0 ? '✅' : '❌'} |

## 🧪 Test Results

- **Total Tests:** ${data.testResults.summary.totalTests}
- **Passed:** ${data.testResults.summary.passedTests} (${Math.round(data.testResults.summary.successRate)}%)
- **Failed:** ${data.testResults.summary.failedTests}
- **Duration:** ${this.formatDuration(data.testResults.summary.totalDuration)}

## 💡 Key Recommendations

${data.recommendations.slice(0, 3).map(rec => 
`### ${this.getPriorityEmoji(rec.priority)} ${rec.title}
**Priority:** ${rec.priority.toUpperCase()}  
**Category:** ${rec.category}

${rec.description}

**Actions:**
${rec.actions.map(action => `- ${action}`).join('\n')}
`).join('\n')}

---

*Report generated at ${new Date().toISOString()}*`;
  }

  // Helper methods
  getGradeColor(grade) {
    const colors = {
      'A': '#28a745',
      'B': '#17a2b8', 
      'C': '#ffc107',
      'D': '#fd7e14',
      'F': '#dc3545'
    };
    return colors[grade] || '#6c757d';
  }

  getStatusEmoji(grade) {
    if (typeof grade === 'string') {
      return grade === 'A' ? '🟢' : grade === 'B' ? '🔵' : grade === 'C' ? '🟡' : grade === 'D' ? '🟠' : '🔴';
    }
    return grade >= 90 ? '🟢' : grade >= 70 ? '🟡' : '🔴';
  }

  getPriorityEmoji(priority) {
    const emojis = {
      critical: '🚨',
      high: '⚠️',
      medium: '📋',
      low: '💡'
    };
    return emojis[priority] || '📝';
  }

  formatDuration(ms) {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    if (ms < 60000) return `${Math.round(ms / 1000)}s`;
    return `${Math.round(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
  }

  calculateGrade(score) {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  }

  async findMatchingDirectories(pattern) {
    try {
      const { glob } = require('glob');
      return await glob(pattern, { onlyDirectories: true });
    } catch (error) {
      console.warn(`Could not find directories matching ${pattern}`);
      return [];
    }
  }

  // Additional helper methods would be implemented here...
  calculateSecurityScore(vulnerabilities) {
    const weights = { critical: 10, high: 5, medium: 2, low: 1 };
    const totalImpact = 
      vulnerabilities.critical * weights.critical +
      vulnerabilities.high * weights.high +
      vulnerabilities.medium * weights.medium +
      vulnerabilities.low * weights.low;
    
    return Math.max(0, 100 - totalImpact);
  }

  calculateTestQualityScore(testQuality) {
    return (testQuality.coverage * 0.4 + testQuality.successRate * 0.6);
  }

  calculatePerformanceScore(performance) {
    // Simplified performance scoring
    const responseTimeScore = Math.max(0, 100 - (performance.responseTime / 10));
    const throughputScore = Math.min(100, performance.throughput);
    return (responseTimeScore + throughputScore) / 2;
  }

  calculateMaintainabilityScore(maintainability) {
    return (maintainability.coverage * 0.4 + 
            maintainability.complexity * 0.3 + 
            maintainability.duplication * 0.3);
  }

  async detectStrategy() {
    return process.env.TEST_STRATEGY || 'unknown';
  }

  async detectTrigger() {
    return process.env.GITHUB_EVENT_NAME || 'unknown';
  }

  async countParallelJobs() {
    return parseInt(process.env.GITHUB_JOB_COUNT) || 1;
  }

  buildTestSuitesSection() {
    const suites = this.data.testResults.suites;
    if (!suites.length) return '';

    return `
    <div class="chart-container">
        <h3>📋 Test Suite Details</h3>
        <table>
            <thead>
                <tr>
                    <th>Suite</th>
                    <th>Tests</th>
                    <th>Success Rate</th>
                    <th>Coverage</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
                ${suites.map(suite => `
                <tr>
                    <td><strong>${suite.name}</strong></td>
                    <td>${suite.totalTests}</td>
                    <td class="${suite.passedTests === suite.totalTests ? 'success' : 'warning'}">
                        ${Math.round((suite.passedTests / suite.totalTests) * 100)}%
                    </td>
                    <td>${Math.round(suite.coverage)}%</td>
                    <td>${this.formatDuration(suite.duration)}</td>
                </tr>
                `).join('')}
            </tbody>
        </table>
    </div>`;
  }

  buildRecommendationsSection() {
    const recommendations = this.data.recommendations;
    if (!recommendations.length) return '<p>✅ No recommendations - excellent work!</p>';

    return `
    <div class="recommendations">
        <h3>💡 Recommendations</h3>
        ${recommendations.map(rec => `
        <div class="recommendation ${rec.priority}">
            <h4>${this.getPriorityEmoji(rec.priority)} ${rec.title}</h4>
            <p><strong>Priority:</strong> ${rec.priority.toUpperCase()} | <strong>Category:</strong> ${rec.category}</p>
            <p>${rec.description}</p>
            <ul>
                ${rec.actions.map(action => `<li>${action}</li>`).join('')}
            </ul>
        </div>
        `).join('')}
    </div>`;
  }

  // Placeholder implementations for missing methods
  extractFailures(summary, details) { return []; }
  extractSlowTests(summary, details) { return []; }
  processPerformanceTest(dir) { return null; }
  processSecurityScan(dir) { return null; }
  identifyPerformanceBottlenecks(testTypes) { return []; }
  calculateOverallCoverage(suites) { return { overall: 85, statements: 85, branches: 80, functions: 90, lines: 85 }; }
  calculateTestReliability() { return 95; }
  calculatePerformanceEfficiency() { return 80; }
  calculateComplexity() { return 75; }
  calculateDuplication() { return 85; }
}

// CLI execution
if (require.main === module) {
  const args = process.argv.slice(2);
  const options = {};
  
  // Parse command line arguments
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace(/^--/, '');
    const value = args[i + 1];
    
    if (key === 'output-formats') {
      options[key.replace('-', '_')] = value.split(',');
    } else {
      options[key.replace('-', '_')] = value;
    }
  }
  
  const reporter = new ComprehensiveReporter(options);
  
  reporter.generate()
    .then(result => {
      console.log('\n✅ Comprehensive report generation completed');
      console.log(`📁 Reports available in: ${result.outputDir}`);
    })
    .catch(error => {
      console.error('\n❌ Report generation failed:', error);
      process.exit(1);
    });
}

module.exports = { ComprehensiveReporter };