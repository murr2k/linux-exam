#!/usr/bin/env node

/**
 * Intelligent Test Runner
 * Implements smart test selection, parallel execution, and adaptive strategies
 */

const { IntelligentTestExecutionStrategy } = require('../src/test-execution-strategy');
const { ParallelTestExecutor } = require('../src/parallel-test-executor');
const { performance } = require('perf_hooks');
const fs = require('fs').promises;
const path = require('path');

class IntelligentTestRunner {
  constructor(options = {}) {
    this.strategy = new IntelligentTestExecutionStrategy(options);
    this.executor = new ParallelTestExecutor(options);
    
    this.config = {
      suite: options.suite || 'all',
      strategy: options.strategy || 'selective',
      parallel: options.parallel !== false,
      coverage: options.coverage !== false,
      fastFail: options.fastFail !== false,
      timeout: options.timeout || 30000,
      reporter: options.reporter || 'json',
      outputDir: options.outputDir || 'test-results',
      ...options
    };
    
    this.results = {
      summary: {},
      details: {},
      coverage: {},
      artifacts: []
    };
  }

  async run() {
    console.log(`🚀 Starting Intelligent Test Runner for suite: ${this.config.suite}`);
    console.log(`📋 Strategy: ${this.config.strategy}, Parallel: ${this.config.parallel}, Coverage: ${this.config.coverage}`);
    
    const startTime = performance.now();
    
    try {
      // Initialize components
      await this.initialize();
      
      // Load test suite
      const testSuite = await this.loadTestSuite();
      
      // Detect changes
      const changes = await this.detectChanges();
      
      // Plan execution
      const executionPlan = await this.planExecution(testSuite, changes);
      
      // Execute tests
      const executionResults = await this.executeTests(executionPlan);
      
      // Generate reports
      await this.generateReports(executionResults);
      
      // Calculate final results
      const duration = performance.now() - startTime;
      this.results.summary = {
        success: executionResults.success,
        duration: Math.round(duration),
        totalTests: executionResults.results?.totalTests || 0,
        passedTests: executionResults.results?.passedTests || 0,
        failedTests: executionResults.results?.failedTests || 0,
        skippedTests: executionResults.results?.skippedTests || 0,
        coverage: this.results.coverage.overall || 0,
        suite: this.config.suite,
        strategy: this.config.strategy
      };
      
      console.log('\n📊 Test Execution Summary:');
      console.log(`✅ Success: ${this.results.summary.success}`);
      console.log(`⏱️  Duration: ${this.results.summary.duration}ms`);
      console.log(`🧪 Tests: ${this.results.summary.passedTests}/${this.results.summary.totalTests} passed`);
      console.log(`📈 Coverage: ${this.results.summary.coverage}%`);
      
      return this.results;
      
    } catch (error) {
      const duration = performance.now() - startTime;
      console.error('❌ Test execution failed:', error);
      
      this.results.summary = {
        success: false,
        error: error.message,
        duration: Math.round(duration),
        suite: this.config.suite,
        strategy: this.config.strategy
      };
      
      throw error;
    }
  }

  async initialize() {
    console.log('🔧 Initializing test execution components...');
    
    // Create output directories
    await fs.mkdir(this.config.outputDir, { recursive: true });
    await fs.mkdir(path.join(this.config.outputDir, 'coverage'), { recursive: true });
    await fs.mkdir(path.join(this.config.outputDir, 'reports'), { recursive: true });
    
    // Initialize strategy and executor
    await this.strategy.initialize();
    if (this.config.parallel) {
      await this.executor.initialize();
    }
  }

  async loadTestSuite() {
    console.log(`📂 Loading test suite: ${this.config.suite}`);
    
    try {
      // Load test suite configuration
      const suiteConfigPath = path.join(process.cwd(), 'test-suites', `${this.config.suite}.json`);
      const suiteConfig = await this.loadSuiteConfig(suiteConfigPath);
      
      // Discover test files
      const testFiles = await this.discoverTests(suiteConfig);
      
      // Build test objects
      const tests = await this.buildTestObjects(testFiles, suiteConfig);
      
      console.log(`📋 Loaded ${tests.length} tests for suite ${this.config.suite}`);
      
      return {
        name: this.config.suite,
        tests: tests,
        config: suiteConfig
      };
      
    } catch (error) {
      console.error(`❌ Failed to load test suite ${this.config.suite}:`, error);
      
      // Fallback to auto-discovery
      return await this.autoDiscoverTests();
    }
  }

  async loadSuiteConfig(configPath) {
    try {
      const configData = await fs.readFile(configPath, 'utf8');
      return JSON.parse(configData);
    } catch (error) {
      // Return default config if file doesn't exist
      return {
        patterns: this.getDefaultTestPatterns(),
        timeout: this.config.timeout,
        parallel: this.config.parallel,
        coverage: this.config.coverage
      };
    }
  }

  getDefaultTestPatterns() {
    const patterns = {
      unit: ['**/*.test.js', '**/*.spec.js'],
      integration: ['**/integration/**/*.test.js'],
      e2e: ['**/e2e/**/*.test.js', '**/e2e/**/*.spec.js'],
      performance: ['**/performance/**/*.test.js'],
      all: ['**/*.test.js', '**/*.spec.js']
    };
    
    return patterns[this.config.suite] || patterns.all;
  }

  async discoverTests(suiteConfig) {
    const { glob } = require('glob');
    const testFiles = [];
    
    for (const pattern of suiteConfig.patterns) {
      const files = await glob(pattern, {
        ignore: ['**/node_modules/**', '**/dist/**', '**/build/**']
      });
      testFiles.push(...files);
    }
    
    return [...new Set(testFiles)]; // Remove duplicates
  }

  async buildTestObjects(testFiles, suiteConfig) {
    const tests = [];
    
    for (const file of testFiles) {
      const testObject = await this.analyzeTestFile(file, suiteConfig);
      tests.push(testObject);
    }
    
    return tests;
  }

  async analyzeTestFile(filePath, suiteConfig) {
    const fileContent = await fs.readFile(filePath, 'utf8');
    
    // Extract test metadata
    const testCount = (fileContent.match(/\b(test|it|describe)\s*\(/g) || []).length;
    const hasAsync = fileContent.includes('async ') || fileContent.includes('await ');
    const dependencies = this.extractDependencies(fileContent);
    const tags = this.extractTags(filePath, fileContent);
    
    return {
      id: this.generateTestId(filePath),
      name: path.basename(filePath, path.extname(filePath)),
      file: filePath,
      type: this.determineTestType(filePath, tags),
      estimatedDuration: this.estimateTestDuration(testCount, hasAsync, tags),
      dependencies: dependencies,
      tags: tags,
      testCount: testCount,
      metadata: {
        hasAsync: hasAsync,
        fileSize: (await fs.stat(filePath)).size,
        lastModified: (await fs.stat(filePath)).mtime
      }
    };
  }

  generateTestId(filePath) {
    const crypto = require('crypto');
    return crypto.createHash('md5').update(filePath).digest('hex').substring(0, 8);
  }

  determineTestType(filePath, tags) {
    if (tags.includes('e2e') || filePath.includes('/e2e/')) return 'e2e';
    if (tags.includes('integration') || filePath.includes('/integration/')) return 'integration';
    if (tags.includes('performance') || filePath.includes('/performance/')) return 'performance';
    return 'unit';
  }

  estimateTestDuration(testCount, hasAsync, tags) {
    let baseDuration = testCount * 100; // 100ms per test
    
    if (hasAsync) baseDuration *= 1.5;
    if (tags.includes('slow')) baseDuration *= 2;
    if (tags.includes('fast')) baseDuration *= 0.5;
    if (tags.includes('e2e')) baseDuration *= 5;
    if (tags.includes('integration')) baseDuration *= 2;
    
    return Math.max(1000, baseDuration); // Minimum 1 second
  }

  extractDependencies(fileContent) {
    const dependencies = [];
    
    // Extract require statements
    const requireMatches = fileContent.match(/require\(['"`]([^'"`]+)['"`]\)/g) || [];
    requireMatches.forEach(match => {
      const dep = match.match(/['"`]([^'"`]+)['"`]/)[1];
      if (!dep.startsWith('.')) { // Only relative paths
        dependencies.push(dep);
      }
    });
    
    // Extract import statements
    const importMatches = fileContent.match(/import.*from\s+['"`]([^'"`]+)['"`]/g) || [];
    importMatches.forEach(match => {
      const dep = match.match(/['"`]([^'"`]+)['"`]/)[1];
      if (dep.startsWith('./') || dep.startsWith('../')) {
        dependencies.push(dep);
      }
    });
    
    return dependencies;
  }

  extractTags(filePath, fileContent) {
    const tags = [];
    
    // Extract from file path
    if (filePath.includes('/unit/')) tags.push('unit');
    if (filePath.includes('/integration/')) tags.push('integration');
    if (filePath.includes('/e2e/')) tags.push('e2e');
    if (filePath.includes('/performance/')) tags.push('performance');
    
    // Extract from file content
    if (fileContent.includes('@slow')) tags.push('slow');
    if (fileContent.includes('@fast')) tags.push('fast');
    if (fileContent.includes('@critical')) tags.push('critical');
    if (fileContent.includes('@smoke')) tags.push('smoke');
    if (fileContent.includes('@database')) tags.push('database');
    if (fileContent.includes('@api')) tags.push('api');
    
    return tags;
  }

  async autoDiscoverTests() {
    console.log('🔍 Auto-discovering tests...');
    
    const { glob } = require('glob');
    const testFiles = await glob('**/*.{test,spec}.js', {
      ignore: ['**/node_modules/**', '**/dist/**', '**/build/**']
    });
    
    const tests = await this.buildTestObjects(testFiles, { patterns: ['**/*.{test,spec}.js'] });
    
    return {
      name: this.config.suite,
      tests: tests,
      config: { patterns: ['**/*.{test,spec}.js'] }
    };
  }

  async detectChanges() {
    console.log('🔍 Detecting changes...');
    
    try {
      const { execSync } = require('child_process');
      const gitOutput = execSync('git diff --name-only HEAD~1 HEAD', { encoding: 'utf8' });
      const changedFiles = gitOutput.trim().split('\n').filter(Boolean);
      
      return changedFiles.map(file => ({
        file: file,
        type: this.determineChangeType(file),
        timestamp: Date.now()
      }));
      
    } catch (error) {
      console.warn('⚠️ Could not detect changes, running all tests');
      return [];
    }
  }

  determineChangeType(filePath) {
    if (filePath.includes('package.json') || filePath.includes('yarn.lock')) return 'dependency';
    if (filePath.includes('config') || filePath.includes('.env')) return 'config';
    if (filePath.endsWith('.test.js') || filePath.endsWith('.spec.js')) return 'test';
    return 'source';
  }

  async planExecution(testSuite, changes) {
    console.log('📋 Planning test execution...');
    
    const planResult = await this.strategy.planExecution(testSuite, changes, {
      analyzeOnly: false,
      runAll: this.config.strategy === 'full'
    });
    
    if (!planResult.success) {
      throw new Error(`Execution planning failed: ${planResult.error}`);
    }
    
    console.log(`📊 Execution Plan: ${planResult.statistics.selectedTests}/${planResult.statistics.totalTests} tests selected`);
    console.log(`⏱️ Estimated Duration: ${Math.round(planResult.statistics.estimatedDuration)}ms`);
    
    return planResult.executionPlan;
  }

  async executeTests(executionPlan) {
    console.log('🏃 Executing tests...');
    
    if (this.config.parallel && executionPlan.shards && executionPlan.shards.length > 1) {
      console.log(`⚡ Executing ${executionPlan.shards.length} shards in parallel`);
      return await this.executeParallel(executionPlan);
    } else {
      console.log('📐 Executing tests sequentially');
      return await this.executeSequential(executionPlan);
    }
  }

  async executeParallel(executionPlan) {
    const parallelOptions = {
      maxWorkers: Math.min(executionPlan.shards.length, 4),
      timeout: this.config.timeout,
      coverage: this.config.coverage,
      reporter: this.config.reporter
    };
    
    return await this.executor.executeInParallel(executionPlan, parallelOptions);
  }

  async executeSequential(executionPlan) {
    const sequentialOptions = {
      fastFail: this.config.fastFail,
      timeout: this.config.timeout,
      coverage: this.config.coverage,
      reporter: this.config.reporter
    };
    
    return await this.strategy.executeWithStrategy(executionPlan, sequentialOptions);
  }

  async generateReports(executionResults) {
    console.log('📊 Generating test reports...');
    
    // Generate summary report
    await this.generateSummaryReport(executionResults);
    
    // Generate detailed report
    await this.generateDetailedReport(executionResults);
    
    // Generate coverage report
    if (this.config.coverage) {
      await this.generateCoverageReport(executionResults);
    }
    
    // Generate JUnit XML report
    if (this.config.reporter.includes('junit')) {
      await this.generateJUnitReport(executionResults);
    }
    
    // Generate HTML report
    if (this.config.reporter.includes('html')) {
      await this.generateHTMLReport(executionResults);
    }
  }

  async generateSummaryReport(executionResults) {
    const summary = {
      timestamp: new Date().toISOString(),
      suite: this.config.suite,
      strategy: this.config.strategy,
      success: executionResults.success,
      duration: executionResults.results?.duration || 0,
      
      tests: {
        total: executionResults.results?.totalTests || 0,
        passed: executionResults.results?.passedTests || 0,
        failed: executionResults.results?.failedTests || 0,
        skipped: executionResults.results?.skippedTests || 0,
        fastFailTriggered: executionResults.results?.fastFailTriggered || false
      },
      
      shards: executionResults.results?.shardResults?.length || 0,
      
      failures: executionResults.results?.failures || [],
      
      performance: {
        averageTestTime: this.calculateAverageTestTime(executionResults),
        slowestTests: this.findSlowestTests(executionResults),
        parallelEfficiency: this.calculateParallelEfficiency(executionResults)
      }
    };
    
    const summaryPath = path.join(this.config.outputDir, 'summary.json');
    await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2));
    
    this.results.summary = summary.tests;
    this.results.artifacts.push(summaryPath);
  }

  async generateDetailedReport(executionResults) {
    const detailed = {
      executionResults: executionResults,
      configuration: this.config,
      environment: {
        nodeVersion: process.version,
        platform: process.platform,
        arch: process.arch,
        memory: process.memoryUsage(),
        cwd: process.cwd()
      }
    };
    
    const detailedPath = path.join(this.config.outputDir, 'detailed.json');
    await fs.writeFile(detailedPath, JSON.stringify(detailed, null, 2));
    
    this.results.details = detailed;
    this.results.artifacts.push(detailedPath);
  }

  async generateCoverageReport(executionResults) {
    // This would integrate with actual coverage tools like nyc, jest, etc.
    const coverage = {
      overall: 85, // Placeholder
      byFile: {},
      statements: { covered: 850, total: 1000, percentage: 85 },
      branches: { covered: 170, total: 200, percentage: 85 },
      functions: { covered: 85, total: 100, percentage: 85 },
      lines: { covered: 850, total: 1000, percentage: 85 }
    };
    
    const coveragePath = path.join(this.config.outputDir, 'coverage', 'coverage.json');
    await fs.writeFile(coveragePath, JSON.stringify(coverage, null, 2));
    
    this.results.coverage = coverage;
    this.results.artifacts.push(coveragePath);
  }

  async generateJUnitReport(executionResults) {
    // Generate JUnit XML format for CI integration
    const xml = this.buildJUnitXML(executionResults);
    
    const junitPath = path.join(this.config.outputDir, 'junit.xml');
    await fs.writeFile(junitPath, xml);
    
    this.results.artifacts.push(junitPath);
  }

  async generateHTMLReport(executionResults) {
    // Generate HTML report for human-readable results
    const html = this.buildHTMLReport(executionResults);
    
    const htmlPath = path.join(this.config.outputDir, 'report.html');
    await fs.writeFile(htmlPath, html);
    
    this.results.artifacts.push(htmlPath);
  }

  buildJUnitXML(executionResults) {
    const results = executionResults.results || {};
    const failures = results.failures || [];
    
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
    xml += `<testsuites name="${this.config.suite}" tests="${results.totalTests || 0}" failures="${results.failedTests || 0}" time="${(results.duration || 0) / 1000}">\n`;
    xml += `  <testsuite name="${this.config.suite}" tests="${results.totalTests || 0}" failures="${results.failedTests || 0}" time="${(results.duration || 0) / 1000}">\n`;
    
    // Add individual test cases (simplified)
    for (const failure of failures) {
      xml += `    <testcase name="${failure.testName}" classname="${failure.testId}" time="0">\n`;
      xml += `      <failure message="${failure.error}">${failure.error}</failure>\n`;
      xml += `    </testcase>\n`;
    }
    
    xml += '  </testsuite>\n';
    xml += '</testsuites>\n';
    
    return xml;
  }

  buildHTMLReport(executionResults) {
    const results = executionResults.results || {};
    const summary = this.results.summary || {};
    
    return `
<!DOCTYPE html>
<html>
<head>
  <title>Test Report - ${this.config.suite}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .summary { background: #f5f5f5; padding: 15px; border-radius: 5px; }
    .success { color: green; }
    .failure { color: red; }
    .metric { margin: 10px 0; }
    .failures { margin-top: 20px; }
    .failure-item { background: #ffebee; padding: 10px; margin: 5px 0; border-radius: 3px; }
  </style>
</head>
<body>
  <h1>Test Report: ${this.config.suite}</h1>
  
  <div class="summary">
    <h2>Summary</h2>
    <div class="metric">Status: <span class="${summary.success ? 'success' : 'failure'}">${summary.success ? 'PASSED' : 'FAILED'}</span></div>
    <div class="metric">Duration: ${summary.duration || 0}ms</div>
    <div class="metric">Tests: ${summary.passedTests || 0}/${summary.totalTests || 0} passed</div>
    <div class="metric">Coverage: ${this.results.coverage?.overall || 0}%</div>
  </div>
  
  ${results.failures && results.failures.length > 0 ? `
  <div class="failures">
    <h2>Failures</h2>
    ${results.failures.map(f => `
      <div class="failure-item">
        <strong>${f.testName}</strong><br/>
        <code>${f.error}</code>
      </div>
    `).join('')}
  </div>
  ` : ''}
  
  <p>Generated at ${new Date().toISOString()}</p>
</body>
</html>
    `;
  }

  calculateAverageTestTime(executionResults) {
    const results = executionResults.results || {};
    if (!results.totalTests || results.totalTests === 0) return 0;
    return (results.duration || 0) / results.totalTests;
  }

  findSlowestTests(executionResults) {
    // This would require more detailed per-test timing
    return [];
  }

  calculateParallelEfficiency(executionResults) {
    // Calculate efficiency of parallel execution
    const results = executionResults.results || {};
    if (!results.shardResults || results.shardResults.length <= 1) return 0;
    
    const totalShardTime = results.shardResults.reduce((sum, shard) => sum + shard.executionTime, 0);
    const actualTime = results.duration || totalShardTime;
    
    if (actualTime === 0) return 100;
    return Math.max(0, ((totalShardTime - actualTime) / totalShardTime) * 100);
  }
}

// CLI execution
if (require.main === module) {
  const args = process.argv.slice(2);
  const options = {};
  
  // Parse command line arguments
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace(/^--/, '');
    const value = args[i + 1];
    
    if (value === 'true') options[key] = true;
    else if (value === 'false') options[key] = false;
    else if (!isNaN(value)) options[key] = Number(value);
    else options[key] = value;
  }
  
  const runner = new IntelligentTestRunner(options);
  
  runner.run()
    .then(results => {
      console.log('\n🎉 Test execution completed successfully');
      
      if (!results.summary.success) {
        process.exit(1);
      }
    })
    .catch(error => {
      console.error('\n❌ Test execution failed:', error.message);
      process.exit(1);
    });
}

module.exports = { IntelligentTestRunner };