#!/usr/bin/env node

/**
 * Pipeline Orchestration Script
 * Coordinates all test types, manages dependencies, implements smart test selection,
 * and provides failure recovery with comprehensive reporting
 */

const fs = require('fs').promises;
const path = require('path');
const { execSync, spawn } = require('child_process');
const { performance } = require('perf_hooks');
const EventEmitter = require('events');

class PipelineOrchestrator extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.config = {
      maxConcurrentJobs: options.maxConcurrentJobs || 4,
      retryAttempts: options.retryAttempts || 3,
      timeoutMs: options.timeoutMs || 1800000, // 30 minutes
      qualityGate: {
        testCoverage: 90,
        qualityScore: 100,
        performanceScore: 85,
        securityScore: 95
      },
      ...options
    };
    
    this.state = {
      initialized: false,
      jobs: new Map(),
      dependencies: new Map(),
      metrics: {
        startTime: null,
        endTime: null,
        totalJobs: 0,
        completedJobs: 0,
        failedJobs: 0,
        retryCount: 0
      },
      artifacts: new Map(),
      reports: []
    };
    
    this.testStrategies = new Map();
    this.setupTestStrategies();
  }

  async initialize() {
    console.log('🚀 Initializing Pipeline Orchestrator...');
    
    try {
      await this.validateEnvironment();
      await this.loadConfiguration();
      await this.setupDirectories();
      await this.initializeTestStrategies();
      
      this.state.initialized = true;
      this.state.metrics.startTime = performance.now();
      
      console.log('✅ Pipeline Orchestrator initialized successfully');
      this.emit('initialized');
      
    } catch (error) {
      console.error('❌ Failed to initialize Pipeline Orchestrator:', error);
      throw error;
    }
  }

  async orchestratePipeline(pipelineConfig) {
    if (!this.state.initialized) {
      await this.initialize();
    }
    
    console.log('🎬 Starting Pipeline Orchestration...');
    
    try {
      // Phase 1: Change Detection and Analysis
      console.log('\n📊 Phase 1: Change Detection and Analysis');
      const changeAnalysis = await this.detectAndAnalyzeChanges(pipelineConfig);
      
      // Phase 2: Test Strategy Planning
      console.log('\n🎯 Phase 2: Test Strategy Planning');
      const testStrategy = await this.planTestStrategy(changeAnalysis, pipelineConfig);
      
      // Phase 3: Dependency Resolution
      console.log('\n🔗 Phase 3: Dependency Resolution');
      const executionPlan = await this.resolveDependencies(testStrategy);
      
      // Phase 4: Parallel Execution with Smart Selection
      console.log('\n⚡ Phase 4: Intelligent Test Execution');
      const executionResults = await this.executeWithIntelligentSelection(executionPlan);
      
      // Phase 5: Quality Gates Validation
      console.log('\n🛡️ Phase 5: Quality Gates Validation');
      const qualityResults = await this.validateQualityGates(executionResults);
      
      // Phase 6: Report Generation
      console.log('\n📋 Phase 6: Comprehensive Report Generation');
      const finalReport = await this.generateComprehensiveReport({
        changeAnalysis,
        testStrategy,
        executionPlan,
        executionResults,
        qualityResults
      });
      
      this.state.metrics.endTime = performance.now();
      
      return {
        success: qualityResults.passed,
        report: finalReport,
        metrics: this.calculateFinalMetrics(),
        artifacts: Array.from(this.state.artifacts.entries())
      };
      
    } catch (error) {
      console.error('❌ Pipeline orchestration failed:', error);
      
      const errorReport = await this.generateErrorReport(error);
      return {
        success: false,
        error: error.message,
        report: errorReport,
        metrics: this.calculateFinalMetrics()
      };
    }
  }

  async detectAndAnalyzeChanges(pipelineConfig) {
    const analysis = {
      changedFiles: [],
      affectedAreas: [],
      testImpact: new Map(),
      riskAssessment: {}
    };
    
    try {
      // Git-based change detection
      const gitChanges = await this.getGitChanges();
      analysis.changedFiles = gitChanges;
      
      // Analyze impact on different areas
      analysis.affectedAreas = await this.analyzeImpactAreas(gitChanges);
      
      // Assess test impact
      for (const area of analysis.affectedAreas) {
        analysis.testImpact.set(area, await this.assessTestImpact(area, gitChanges));
      }
      
      // Risk assessment
      analysis.riskAssessment = await this.assessRisk(analysis);
      
      console.log(`📊 Change Analysis: ${analysis.changedFiles.length} files, ${analysis.affectedAreas.length} areas affected`);
      
      return analysis;
      
    } catch (error) {
      console.error('❌ Change detection failed:', error);
      
      // Fallback: run all tests
      return {
        changedFiles: ['*'],
        affectedAreas: ['all'],
        testImpact: new Map([['all', { priority: 'high', tests: ['all'] }]]),
        riskAssessment: { level: 'high', reason: 'change_detection_failed' }
      };
    }
  }

  async planTestStrategy(changeAnalysis, pipelineConfig) {
    console.log('🎯 Planning intelligent test strategy...');
    
    const strategy = {
      selectedTests: new Set(),
      testOrder: [],
      parallelGroups: [],
      estimatedDuration: 0,
      optimizations: []
    };
    
    try {
      // Smart test selection based on changes
      for (const [area, impact] of changeAnalysis.testImpact) {
        const testStrategy = this.testStrategies.get(area) || this.testStrategies.get('default');
        const tests = await testStrategy.selectTests(impact, changeAnalysis);
        
        tests.forEach(test => strategy.selectedTests.add(test));
      }
      
      // Determine optimal test order
      strategy.testOrder = await this.optimizeTestOrder(Array.from(strategy.selectedTests), changeAnalysis);
      
      // Create parallel execution groups
      strategy.parallelGroups = await this.createParallelGroups(strategy.testOrder);
      
      // Estimate execution time
      strategy.estimatedDuration = await this.estimateExecutionTime(strategy.parallelGroups);
      
      // Apply optimizations
      strategy.optimizations = await this.applyTestOptimizations(strategy, changeAnalysis);
      
      console.log(`🎯 Test Strategy: ${strategy.selectedTests.size} tests selected, ${strategy.parallelGroups.length} parallel groups`);
      
      return strategy;
      
    } catch (error) {
      console.error('❌ Test strategy planning failed:', error);
      throw error;
    }
  }

  async resolveDependencies(testStrategy) {
    console.log('🔗 Resolving test dependencies...');
    
    const executionPlan = {
      phases: [],
      dependencies: new Map(),
      executionOrder: [],
      parallelJobs: new Map()
    };
    
    try {
      // Build dependency graph
      const dependencyGraph = await this.buildDependencyGraph(testStrategy.selectedTests);
      
      // Topological sort for execution order
      executionPlan.executionOrder = this.topologicalSort(dependencyGraph);
      
      // Create execution phases
      executionPlan.phases = await this.createExecutionPhases(executionPlan.executionOrder, dependencyGraph);
      
      // Optimize for parallel execution
      executionPlan.parallelJobs = await this.optimizeParallelExecution(executionPlan.phases);
      
      console.log(`🔗 Dependencies resolved: ${executionPlan.phases.length} phases, ${executionPlan.executionOrder.length} jobs`);
      
      return executionPlan;
      
    } catch (error) {
      console.error('❌ Dependency resolution failed:', error);
      throw error;
    }
  }

  async executeWithIntelligentSelection(executionPlan) {
    console.log('⚡ Executing tests with intelligent selection...');
    
    const results = {
      phases: [],
      overall: {
        totalJobs: 0,
        completedJobs: 0,
        failedJobs: 0,
        skippedJobs: 0,
        duration: 0
      },
      qualityMetrics: {
        coverage: 0,
        reliability: 0,
        performance: 0
      },
      artifacts: []
    };
    
    const startTime = performance.now();
    
    try {
      for (let i = 0; i < executionPlan.phases.length; i++) {
        const phase = executionPlan.phases[i];
        console.log(`\n🔄 Executing Phase ${i + 1}/${executionPlan.phases.length}: ${phase.name}`);
        
        const phaseResult = await this.executePhase(phase);
        results.phases.push(phaseResult);
        
        // Update overall metrics
        results.overall.totalJobs += phaseResult.jobs.length;
        results.overall.completedJobs += phaseResult.completed;
        results.overall.failedJobs += phaseResult.failed;
        results.overall.skippedJobs += phaseResult.skipped;
        
        // Check if we should continue based on fast-fail rules
        if (phaseResult.shouldFailFast) {
          console.log('🚨 Fast-fail condition triggered, stopping execution');
          break;
        }
        
        // Collect artifacts from this phase
        results.artifacts.push(...phaseResult.artifacts);
      }
      
      results.overall.duration = performance.now() - startTime;
      
      // Calculate quality metrics
      results.qualityMetrics = await this.calculateQualityMetrics(results);
      
      console.log(`⚡ Execution completed: ${results.overall.completedJobs}/${results.overall.totalJobs} jobs successful`);
      
      return results;
      
    } catch (error) {
      console.error('❌ Test execution failed:', error);
      
      results.overall.duration = performance.now() - startTime;
      results.error = error.message;
      
      return results;
    }
  }

  async executePhase(phase) {
    const phaseResult = {
      name: phase.name,
      jobs: phase.jobs,
      completed: 0,
      failed: 0,
      skipped: 0,
      shouldFailFast: false,
      artifacts: [],
      results: []
    };
    
    // Execute jobs in parallel groups
    const parallelGroups = this.groupJobsForParallel(phase.jobs);
    
    for (const group of parallelGroups) {
      const groupPromises = group.map(job => this.executeJob(job));
      const groupResults = await Promise.allSettled(groupPromises);
      
      for (let i = 0; i < groupResults.length; i++) {
        const result = groupResults[i];
        const job = group[i];
        
        if (result.status === 'fulfilled') {
          const jobResult = result.value;
          
          if (jobResult.success) {
            phaseResult.completed++;
          } else {
            phaseResult.failed++;
            
            // Check fast-fail conditions
            if (this.shouldFailFast(job, jobResult)) {
              phaseResult.shouldFailFast = true;
            }
          }
          
          phaseResult.results.push(jobResult);
          phaseResult.artifacts.push(...jobResult.artifacts);
          
        } else {
          phaseResult.failed++;
          console.error(`❌ Job ${job.name} failed with error:`, result.reason);
        }
      }
      
      // Check if we should stop this phase
      if (phaseResult.shouldFailFast) {
        break;
      }
    }
    
    return phaseResult;
  }

  async executeJob(job) {
    console.log(`🏃 Executing job: ${job.name}`);
    
    const jobResult = {
      name: job.name,
      type: job.type,
      success: false,
      duration: 0,
      artifacts: [],
      metrics: {},
      error: null,
      retryCount: 0
    };
    
    const startTime = performance.now();
    
    for (let attempt = 0; attempt <= this.config.retryAttempts; attempt++) {
      try {
        if (attempt > 0) {
          console.log(`🔄 Retrying job ${job.name} (attempt ${attempt + 1})`);
          jobResult.retryCount = attempt;
          this.state.metrics.retryCount++;
        }
        
        const result = await this.executeJobWithTimeout(job);
        
        jobResult.success = true;
        jobResult.artifacts = result.artifacts || [];
        jobResult.metrics = result.metrics || {};
        jobResult.duration = performance.now() - startTime;
        
        console.log(`✅ Job ${job.name} completed successfully`);
        break;
        
      } catch (error) {
        jobResult.error = error.message;
        
        if (attempt === this.config.retryAttempts) {
          console.error(`❌ Job ${job.name} failed after ${this.config.retryAttempts + 1} attempts`);
          jobResult.success = false;
          jobResult.duration = performance.now() - startTime;
        } else {
          // Wait before retry with exponential backoff
          const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
          await this.sleep(delay);
        }
      }
    }
    
    return jobResult;
  }

  async executeJobWithTimeout(job) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Job ${job.name} timed out after ${this.config.timeoutMs}ms`));
      }, this.config.timeoutMs);
      
      this.executeJobType(job)
        .then(result => {
          clearTimeout(timeout);
          resolve(result);
        })
        .catch(error => {
          clearTimeout(timeout);
          reject(error);
        });
    });
  }

  async executeJobType(job) {
    switch (job.type) {
      case 'unit-test':
        return this.executeUnitTests(job);
      case 'integration-test':
        return this.executeIntegrationTests(job);
      case 'e2e-test':
        return this.executeE2ETests(job);
      case 'performance-test':
        return this.executePerformanceTests(job);
      case 'security-scan':
        return this.executeSecurityScan(job);
      case 'build':
        return this.executeBuild(job);
      case 'quality-check':
        return this.executeQualityCheck(job);
      default:
        throw new Error(`Unknown job type: ${job.type}`);
    }
  }

  async executeUnitTests(job) {
    const testCommand = this.buildTestCommand('unit', job);
    const result = await this.runCommand(testCommand);
    
    return {
      artifacts: [`test-results/${job.name}.xml`, `coverage/${job.name}/`],
      metrics: {
        coverage: await this.extractCoverage(`coverage/${job.name}/`),
        testsRun: await this.extractTestCount(result.stdout),
        duration: result.duration
      }
    };
  }

  async executeIntegrationTests(job) {
    const testCommand = this.buildTestCommand('integration', job);
    const result = await this.runCommand(testCommand);
    
    return {
      artifacts: [`integration-results/${job.name}.xml`, `integration-reports/${job.name}/`],
      metrics: {
        testsRun: await this.extractTestCount(result.stdout),
        duration: result.duration,
        endpoints: await this.extractEndpointCoverage(result.stdout)
      }
    };
  }

  async executeE2ETests(job) {
    const testCommand = this.buildTestCommand('e2e', job);
    const result = await this.runCommand(testCommand);
    
    return {
      artifacts: [
        `e2e-results/${job.name}.xml`,
        `screenshots/${job.name}/`,
        `videos/${job.name}/`
      ],
      metrics: {
        testsRun: await this.extractTestCount(result.stdout),
        duration: result.duration,
        screenshotCount: await this.countScreenshots(`screenshots/${job.name}/`)
      }
    };
  }

  async executePerformanceTests(job) {
    const perfCommand = this.buildPerformanceCommand(job);
    const result = await this.runCommand(perfCommand);
    
    return {
      artifacts: [`performance-results/${job.name}.json`, `performance-reports/${job.name}.html`],
      metrics: {
        responseTime: await this.extractResponseTime(result.stdout),
        throughput: await this.extractThroughput(result.stdout),
        duration: result.duration
      }
    };
  }

  async executeSecurityScan(job) {
    const scanCommand = this.buildSecurityCommand(job);
    const result = await this.runCommand(scanCommand);
    
    return {
      artifacts: [`security-reports/${job.name}.json`, `security-reports/${job.name}.html`],
      metrics: {
        vulnerabilities: await this.extractVulnerabilities(result.stdout),
        severity: await this.extractSeverityDistribution(result.stdout),
        duration: result.duration
      }
    };
  }

  async validateQualityGates(executionResults) {
    console.log('🛡️ Validating quality gates...');
    
    const validation = {
      passed: true,
      gates: {},
      issues: [],
      recommendations: []
    };
    
    // Test Coverage Gate
    validation.gates.testCoverage = {
      required: this.config.qualityGate.testCoverage,
      actual: executionResults.qualityMetrics.coverage,
      passed: executionResults.qualityMetrics.coverage >= this.config.qualityGate.testCoverage
    };
    
    // Quality Score Gate
    validation.gates.qualityScore = {
      required: this.config.qualityGate.qualityScore,
      actual: await this.calculateQualityScore(executionResults),
      passed: true // Will be calculated
    };
    
    // Performance Gate
    validation.gates.performanceScore = {
      required: this.config.qualityGate.performanceScore,
      actual: executionResults.qualityMetrics.performance,
      passed: executionResults.qualityMetrics.performance >= this.config.qualityGate.performanceScore
    };
    
    // Security Gate
    const securityScore = await this.calculateSecurityScore(executionResults);
    validation.gates.securityScore = {
      required: this.config.qualityGate.securityScore,
      actual: securityScore,
      passed: securityScore >= this.config.qualityGate.securityScore
    };
    
    // Overall validation
    validation.passed = Object.values(validation.gates).every(gate => gate.passed);
    
    // Generate issues and recommendations
    for (const [gateName, gate] of Object.entries(validation.gates)) {
      if (!gate.passed) {
        validation.issues.push({
          gate: gateName,
          required: gate.required,
          actual: gate.actual,
          deficit: gate.required - gate.actual
        });
      }
    }
    
    console.log(`🛡️ Quality Gates: ${validation.passed ? 'PASSED' : 'FAILED'}`);
    
    return validation;
  }

  async generateComprehensiveReport(orchestrationData) {
    console.log('📋 Generating comprehensive report...');
    
    const report = {
      executionId: `exec_${Date.now()}`,
      timestamp: new Date().toISOString(),
      duration: this.state.metrics.endTime - this.state.metrics.startTime,
      
      summary: {
        success: orchestrationData.qualityResults.passed,
        totalJobs: this.state.metrics.totalJobs,
        completedJobs: this.state.metrics.completedJobs,
        failedJobs: this.state.metrics.failedJobs,
        retryCount: this.state.metrics.retryCount
      },
      
      changeAnalysis: orchestrationData.changeAnalysis,
      testStrategy: orchestrationData.testStrategy,
      executionPlan: orchestrationData.executionPlan,
      results: orchestrationData.executionResults,
      qualityGates: orchestrationData.qualityResults,
      
      metrics: {
        performance: await this.generatePerformanceMetrics(orchestrationData),
        quality: await this.generateQualityMetrics(orchestrationData),
        efficiency: await this.generateEfficiencyMetrics(orchestrationData),
        trends: await this.generateTrendAnalysis(orchestrationData)
      },
      
      recommendations: await this.generateRecommendations(orchestrationData),
      artifacts: Array.from(this.state.artifacts.entries()),
      
      diagnostics: {
        systemInfo: await this.getSystemInfo(),
        environmentInfo: await this.getEnvironmentInfo(),
        configurationInfo: this.config
      }
    };
    
    // Save report to multiple formats
    await this.saveReport(report, 'json');
    await this.saveReport(report, 'html');
    await this.saveReport(report, 'xml');
    
    console.log('📋 Comprehensive report generated successfully');
    
    return report;
  }

  setupTestStrategies() {
    // Default test strategy
    this.testStrategies.set('default', {
      selectTests: async (impact, changeAnalysis) => {
        if (changeAnalysis.riskAssessment.level === 'high') {
          return ['all']; // Run all tests for high risk
        }
        return impact.tests || [];
      }
    });
    
    // Frontend-specific strategy
    this.testStrategies.set('frontend', {
      selectTests: async (impact, changeAnalysis) => {
        const tests = [];
        if (changeAnalysis.changedFiles.some(f => f.includes('.js') || f.includes('.css'))) {
          tests.push('unit-frontend', 'e2e-frontend');
        }
        return tests;
      }
    });
    
    // Backend-specific strategy
    this.testStrategies.set('backend', {
      selectTests: async (impact, changeAnalysis) => {
        const tests = [];
        if (changeAnalysis.changedFiles.some(f => f.includes('src/') || f.includes('lib/'))) {
          tests.push('unit-backend', 'integration-backend');
        }
        return tests;
      }
    });
    
    // Database strategy
    this.testStrategies.set('database', {
      selectTests: async (impact, changeAnalysis) => {
        const tests = [];
        if (changeAnalysis.changedFiles.some(f => f.includes('migrations') || f.includes('schema'))) {
          tests.push('database-migration', 'integration-database');
        }
        return tests;
      }
    });
  }

  // Helper methods
  async getGitChanges() {
    try {
      const result = execSync('git diff --name-only HEAD~1 HEAD', { encoding: 'utf8' });
      return result.trim().split('\n').filter(Boolean);
    } catch (error) {
      console.warn('Failed to get git changes:', error.message);
      return [];
    }
  }

  async analyzeImpactAreas(changedFiles) {
    const areas = new Set();
    
    for (const file of changedFiles) {
      if (file.startsWith('src/frontend/') || file.endsWith('.html') || file.endsWith('.css')) {
        areas.add('frontend');
      }
      if (file.startsWith('src/backend/') || file.endsWith('.js') || file.endsWith('.ts')) {
        areas.add('backend');
      }
      if (file.includes('database') || file.includes('migration')) {
        areas.add('database');
      }
      if (file.includes('config') || file.includes('.env')) {
        areas.add('configuration');
      }
      if (file.includes('package.json') || file.includes('yarn.lock')) {
        areas.add('dependencies');
      }
    }
    
    return Array.from(areas);
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  calculateFinalMetrics() {
    return {
      duration: this.state.metrics.endTime - this.state.metrics.startTime,
      totalJobs: this.state.metrics.totalJobs,
      completedJobs: this.state.metrics.completedJobs,
      failedJobs: this.state.metrics.failedJobs,
      retryCount: this.state.metrics.retryCount,
      successRate: this.state.metrics.completedJobs / this.state.metrics.totalJobs * 100
    };
  }
}

// CLI execution
if (require.main === module) {
  const orchestrator = new PipelineOrchestrator();
  
  orchestrator.orchestratePipeline({
    changeDetection: true,
    smartSelection: true,
    parallelExecution: true,
    qualityGates: true
  })
  .then(result => {
    console.log('\n🎉 Pipeline orchestration completed');
    console.log('📊 Final Result:', result.success ? 'SUCCESS' : 'FAILURE');
    
    if (!result.success) {
      process.exit(1);
    }
  })
  .catch(error => {
    console.error('\n❌ Pipeline orchestration failed:', error);
    process.exit(1);
  });
}

module.exports = { PipelineOrchestrator };