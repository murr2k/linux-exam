/**
 * Intelligent Test Execution Strategy
 * Implements fast-fail, selective execution, sharding, and prediction
 */

const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const { performance } = require('perf_hooks');

class IntelligentTestExecutionStrategy {
  constructor(options = {}) {
    this.testDatabase = new TestDatabase();
    this.changeAnalyzer = new ChangeAnalyzer();
    this.predictiveModel = new TestPredictiveModel();
    this.shardingStrategy = new TestShardingStrategy();
    this.fastFailDetector = new FastFailDetector();
    this.executionPlanner = new ExecutionPlanner();
    
    this.executionHistory = [];
    this.testMetrics = new Map();
    this.failurePatterns = new Map();
    
    // Configuration
    this.fastFailEnabled = options.fastFail !== false;
    this.selectiveExecution = options.selective !== false;
    this.shardingEnabled = options.sharding !== false;
    this.predictionEnabled = options.prediction !== false;
    this.maxShards = options.maxShards || 8;
    this.failureProbabilityThreshold = options.failureProbabilityThreshold || 0.7;
  }

  async initialize() {
    console.log('Initializing intelligent test execution strategy');
    
    // Initialize components
    await this.testDatabase.initialize();
    await this.changeAnalyzer.initialize();
    await this.predictiveModel.initialize();
    
    // Load historical data
    await this.loadHistoricalData();
    
    console.log('Test execution strategy initialized');
  }

  async planExecution(testSuite, changes = [], options = {}) {
    console.log(`Planning execution for ${testSuite.tests.length} tests with ${changes.length} changes`);
    
    const startTime = performance.now();
    
    try {
      // Analyze changes to determine affected tests
      const affectedTests = await this.changeAnalyzer.analyzeImpact(changes, testSuite.tests);
      
      // Get test predictions
      const predictions = await this.predictiveModel.predictTestOutcomes(testSuite.tests, changes);
      
      // Create execution plan
      const executionPlan = await this.executionPlanner.createPlan({
        allTests: testSuite.tests,
        affectedTests: affectedTests,
        predictions: predictions,
        changes: changes,
        options: options
      });
      
      // Apply optimization strategies
      const optimizedPlan = await this.applyOptimizationStrategies(executionPlan, options);
      
      const planningTime = performance.now() - startTime;
      
      return {
        success: true,
        executionPlan: optimizedPlan,
        planningTime: planningTime,
        statistics: {
          totalTests: testSuite.tests.length,
          selectedTests: optimizedPlan.selectedTests.length,
          skippedTests: testSuite.tests.length - optimizedPlan.selectedTests.length,
          estimatedDuration: optimizedPlan.estimatedDuration,
          shards: optimizedPlan.shards?.length || 1,
          fastFailTests: optimizedPlan.fastFailTests?.length || 0
        }
      };
      
    } catch (error) {
      console.error('Execution planning failed:', error);
      return {
        success: false,
        error: error.message,
        planningTime: performance.now() - startTime
      };
    }
  }

  async applyOptimizationStrategies(executionPlan, options) {
    let optimizedPlan = { ...executionPlan };
    
    // Apply selective execution
    if (this.selectiveExecution && !options.runAll) {
      optimizedPlan = await this.applySelectiveExecution(optimizedPlan);
    }
    
    // Apply fast-fail strategy
    if (this.fastFailEnabled) {
      optimizedPlan = await this.applyFastFailStrategy(optimizedPlan);
    }
    
    // Apply test sharding
    if (this.shardingEnabled && optimizedPlan.selectedTests.length > 10) {
      optimizedPlan = await this.applyTestSharding(optimizedPlan);
    }
    
    // Apply prediction-based ordering
    if (this.predictionEnabled) {
      optimizedPlan = await this.applyPredictiveOrdering(optimizedPlan);
    }
    
    return optimizedPlan;
  }

  async applySelectiveExecution(executionPlan) {
    console.log('Applying selective test execution strategy');
    
    const selectedTests = [];
    const skippedTests = [];
    
    for (const test of executionPlan.allTests) {
      const shouldRun = await this.shouldRunTest(test, executionPlan);
      
      if (shouldRun) {
        selectedTests.push(test);
      } else {
        skippedTests.push({
          test: test,
          reason: shouldRun.reason || 'No changes affecting test'
        });
      }
    }
    
    console.log(`Selective execution: ${selectedTests.length} selected, ${skippedTests.length} skipped`);
    
    return {
      ...executionPlan,
      selectedTests: selectedTests,
      skippedTests: skippedTests,
      optimizationApplied: 'selective_execution'
    };
  }

  async shouldRunTest(test, executionPlan) {
    // Always run if explicitly requested
    if (test.alwaysRun || test.tags?.includes('critical')) {
      return { shouldRun: true, reason: 'Critical or always-run test' };
    }
    
    // Run if test is in affected tests
    if (executionPlan.affectedTests.some(t => t.id === test.id)) {
      return { shouldRun: true, reason: 'Test affected by changes' };
    }
    
    // Run if test has high failure probability
    const prediction = executionPlan.predictions?.get(test.id);
    if (prediction && prediction.failureProbability > this.failureProbabilityThreshold) {
      return { shouldRun: true, reason: 'High failure probability predicted' };
    }
    
    // Run if test hasn't been run recently
    const lastRun = await this.testDatabase.getLastRunTime(test.id);
    if (!lastRun || Date.now() - lastRun > 24 * 60 * 60 * 1000) { // 24 hours
      return { shouldRun: true, reason: 'Test not run recently' };
    }
    
    // Run if dependencies have changed
    if (test.dependencies) {
      for (const dep of test.dependencies) {
        if (executionPlan.changes.some(change => change.file.includes(dep))) {
          return { shouldRun: true, reason: 'Test dependencies changed' };
        }
      }
    }
    
    // Skip test
    return { shouldRun: false, reason: 'No changes affecting test' };
  }

  async applyFastFailStrategy(executionPlan) {
    console.log('Applying fast-fail execution strategy');
    
    // Identify fast-fail tests
    const fastFailTests = await this.fastFailDetector.identifyFastFailTests(
      executionPlan.selectedTests, executionPlan.predictions
    );
    
    // Reorder tests to put fast-fail tests first
    const reorderedTests = [
      ...fastFailTests,
      ...executionPlan.selectedTests.filter(test => 
        !fastFailTests.some(ff => ff.id === test.id)
      )
    ];
    
    console.log(`Fast-fail strategy: ${fastFailTests.length} fast-fail tests identified`);
    
    return {
      ...executionPlan,
      selectedTests: reorderedTests,
      fastFailTests: fastFailTests,
      optimizationApplied: 'fast_fail'
    };
  }

  async applyTestSharding(executionPlan) {
    console.log('Applying test sharding strategy');
    
    const shards = await this.shardingStrategy.createShards(
      executionPlan.selectedTests, 
      this.maxShards
    );
    
    // Calculate execution time for each shard
    for (const shard of shards) {
      shard.estimatedDuration = shard.tests.reduce(
        (total, test) => total + (test.estimatedDuration || 5000), 0
      );
    }
    
    console.log(`Sharding strategy: Created ${shards.length} shards`);
    
    return {
      ...executionPlan,
      shards: shards,
      optimizationApplied: 'sharding'
    };
  }

  async applyPredictiveOrdering(executionPlan) {
    console.log('Applying predictive test ordering');
    
    // Sort tests by failure probability (highest first for fast feedback)
    const sortedTests = executionPlan.selectedTests.sort((a, b) => {
      const predictionA = executionPlan.predictions?.get(a.id);
      const predictionB = executionPlan.predictions?.get(b.id);
      
      const probA = predictionA?.failureProbability || 0;
      const probB = predictionB?.failureProbability || 0;
      
      // Secondary sort by estimated duration (shorter tests first)
      if (Math.abs(probA - probB) < 0.1) {
        const durationA = a.estimatedDuration || 5000;
        const durationB = b.estimatedDuration || 5000;
        return durationA - durationB;
      }
      
      return probB - probA;
    });
    
    return {
      ...executionPlan,
      selectedTests: sortedTests,
      optimizationApplied: 'predictive_ordering'
    };
  }

  async executeWithStrategy(executionPlan, options = {}) {
    console.log('Executing tests with intelligent strategy');
    
    const startTime = performance.now();
    const results = {
      totalTests: 0,
      passedTests: 0,
      failedTests: 0,
      skippedTests: 0,
      executionTime: 0,
      shardResults: [],
      fastFailTriggered: false,
      failures: []
    };
    
    try {
      if (executionPlan.shards && executionPlan.shards.length > 1) {
        // Execute shards in parallel
        results.shardResults = await this.executeShards(executionPlan.shards, options);
        
        // Aggregate results
        for (const shardResult of results.shardResults) {
          results.totalTests += shardResult.totalTests;
          results.passedTests += shardResult.passedTests;
          results.failedTests += shardResult.failedTests;
          results.failures.push(...shardResult.failures);
        }
      } else {
        // Execute tests sequentially with fast-fail
        const executionResult = await this.executeSequentialWithFastFail(
          executionPlan.selectedTests, options
        );
        
        results.totalTests = executionResult.totalTests;
        results.passedTests = executionResult.passedTests;
        results.failedTests = executionResult.failedTests;
        results.fastFailTriggered = executionResult.fastFailTriggered;
        results.failures = executionResult.failures;
      }
      
      results.executionTime = performance.now() - startTime;
      
      // Update test database with results
      await this.updateTestResults(results);
      
      return {
        success: true,
        results: results
      };
      
    } catch (error) {
      console.error('Test execution failed:', error);
      return {
        success: false,
        error: error.message,
        partialResults: results,
        executionTime: performance.now() - startTime
      };
    }
  }

  async executeShards(shards, options) {
    console.log(`Executing ${shards.length} shards in parallel`);
    
    const shardPromises = shards.map((shard, index) => 
      this.executeShard(shard, index, options)
    );
    
    return await Promise.all(shardPromises);
  }

  async executeShard(shard, shardIndex, options) {
    console.log(`Executing shard ${shardIndex} with ${shard.tests.length} tests`);
    
    const startTime = performance.now();
    const result = {
      shardIndex: shardIndex,
      totalTests: shard.tests.length,
      passedTests: 0,
      failedTests: 0,
      executionTime: 0,
      failures: []
    };
    
    for (const test of shard.tests) {
      const testResult = await this.executeTest(test, options);
      
      if (testResult.success) {
        result.passedTests++;
      } else {
        result.failedTests++;
        result.failures.push({
          testId: test.id,
          testName: test.name,
          error: testResult.error,
          shard: shardIndex
        });
      }
    }
    
    result.executionTime = performance.now() - startTime;
    
    console.log(`Shard ${shardIndex} completed: ${result.passedTests}/${result.totalTests} passed`);
    
    return result;
  }

  async executeSequentialWithFastFail(tests, options) {
    const result = {
      totalTests: tests.length,
      passedTests: 0,
      failedTests: 0,
      fastFailTriggered: false,
      failures: []
    };
    
    let consecutiveFailures = 0;
    const maxConsecutiveFailures = options.maxConsecutiveFailures || 3;
    
    for (const test of tests) {
      const testResult = await this.executeTest(test, options);
      
      if (testResult.success) {
        result.passedTests++;
        consecutiveFailures = 0;
      } else {
        result.failedTests++;
        consecutiveFailures++;
        
        result.failures.push({
          testId: test.id,
          testName: test.name,
          error: testResult.error
        });
        
        // Check fast-fail conditions
        if (this.fastFailEnabled && this.shouldFastFail(test, consecutiveFailures, maxConsecutiveFailures)) {
          console.log(`Fast-fail triggered after ${consecutiveFailures} consecutive failures`);
          result.fastFailTriggered = true;
          break;
        }
      }
    }
    
    return result;
  }

  shouldFastFail(test, consecutiveFailures, maxConsecutiveFailures) {
    // Fast-fail if too many consecutive failures
    if (consecutiveFailures >= maxConsecutiveFailures) {
      return true;
    }
    
    // Fast-fail for critical test failures
    if (test.tags?.includes('critical')) {
      return true;
    }
    
    // Fast-fail for build-breaking tests
    if (test.tags?.includes('build-breaking')) {
      return true;
    }
    
    return false;
  }

  async executeTest(test, options) {
    // This would integrate with the actual test runner
    // For now, simulate test execution
    const startTime = performance.now();
    
    try {
      // Simulate test execution time
      const executionTime = test.estimatedDuration || Math.random() * 5000 + 1000;
      await this.sleep(executionTime / 1000); // Convert to seconds for simulation
      
      // Simulate test result based on historical data or prediction
      const prediction = await this.predictiveModel.predictTestOutcome(test);
      const success = Math.random() > (prediction?.failureProbability || 0.1);
      
      return {
        success: success,
        executionTime: performance.now() - startTime,
        error: success ? null : 'Simulated test failure'
      };
      
    } catch (error) {
      return {
        success: false,
        executionTime: performance.now() - startTime,
        error: error.message
      };
    }
  }

  async updateTestResults(results) {
    // Update test database with execution results
    await this.testDatabase.updateExecutionResults(results);
    
    // Update predictive model with new data
    await this.predictiveModel.updateWithResults(results);
    
    // Update execution history
    this.executionHistory.push({
      timestamp: Date.now(),
      results: results
    });
    
    // Keep only last 100 executions
    if (this.executionHistory.length > 100) {
      this.executionHistory.shift();
    }
  }

  async getExecutionStatistics() {
    return {
      executionHistory: this.executionHistory.slice(-10), // Last 10 executions
      testMetrics: await this.getTestMetrics(),
      failurePatterns: await this.getFailurePatterns(),
      optimizationEffectiveness: await this.calculateOptimizationEffectiveness()
    };
  }

  async calculateOptimizationEffectiveness() {
    if (this.executionHistory.length < 2) {
      return null;
    }
    
    const recent = this.executionHistory.slice(-5);
    const older = this.executionHistory.slice(-10, -5);
    
    const recentAvgTime = recent.reduce((sum, exec) => sum + exec.results.executionTime, 0) / recent.length;
    const olderAvgTime = older.reduce((sum, exec) => sum + exec.results.executionTime, 0) / older.length;
    
    return {
      timeImprovement: ((olderAvgTime - recentAvgTime) / olderAvgTime) * 100,
      recentExecutions: recent.length,
      averageExecutionTime: recentAvgTime,
      testSelectionEffectiveness: this.calculateTestSelectionEffectiveness(recent)
    };
  }

  sleep(seconds) {
    return new Promise(resolve => setTimeout(resolve, seconds * 1000));
  }
}

class ChangeAnalyzer {
  async initialize() {
    this.fileTestMapping = new Map();
    await this.buildFileTestMapping();
  }

  async analyzeImpact(changes, allTests) {
    const affectedTests = new Set();
    
    for (const change of changes) {
      // Direct file-to-test mapping
      const directlyAffected = this.fileTestMapping.get(change.file) || [];
      directlyAffected.forEach(test => affectedTests.add(test));
      
      // Analyze dependencies
      const dependencyAffected = await this.analyzeDependencyImpact(change, allTests);
      dependencyAffected.forEach(test => affectedTests.add(test));
      
      // Pattern-based analysis
      const patternAffected = await this.analyzePatternImpact(change, allTests);
      patternAffected.forEach(test => affectedTests.add(test));
    }
    
    return Array.from(affectedTests);
  }

  async buildFileTestMapping() {
    // This would analyze the codebase to build mapping
    // For now, use simple heuristics
    
    // Example mappings
    this.fileTestMapping.set('src/user.js', ['user.test.js', 'integration.test.js']);
    this.fileTestMapping.set('src/auth.js', ['auth.test.js', 'security.test.js']);
    this.fileTestMapping.set('package.json', ['*']); // All tests affected by package.json changes
  }

  async analyzeDependencyImpact(change, allTests) {
    const affected = [];
    
    // Check if any tests import or depend on the changed file
    for (const test of allTests) {
      if (test.dependencies && test.dependencies.some(dep => change.file.includes(dep))) {
        affected.push(test);
      }
    }
    
    return affected;
  }

  async analyzePatternImpact(change, allTests) {
    const affected = [];
    
    // Check for pattern-based impacts
    if (change.file.includes('config')) {
      // Configuration changes affect all tests
      affected.push(...allTests.filter(test => test.tags?.includes('config')));
    }
    
    if (change.file.includes('database')) {
      // Database changes affect database tests
      affected.push(...allTests.filter(test => test.tags?.includes('database')));
    }
    
    return affected;
  }
}

class TestPredictiveModel {
  constructor() {
    this.trainingData = [];
    this.model = null;
  }

  async initialize() {
    await this.loadTrainingData();
    await this.trainModel();
  }

  async predictTestOutcomes(tests, changes) {
    const predictions = new Map();
    
    for (const test of tests) {
      const prediction = await this.predictTestOutcome(test, changes);
      predictions.set(test.id, prediction);
    }
    
    return predictions;
  }

  async predictTestOutcome(test, changes = []) {
    // Simple prediction based on historical data
    const historicalFailureRate = this.getHistoricalFailureRate(test);
    const changeImpactFactor = this.calculateChangeImpactFactor(test, changes);
    
    const failureProbability = Math.min(0.95, historicalFailureRate * changeImpactFactor);
    
    return {
      failureProbability: failureProbability,
      confidence: 0.7,
      estimatedDuration: test.estimatedDuration || 5000,
      factors: {
        historicalFailureRate: historicalFailureRate,
        changeImpact: changeImpactFactor
      }
    };
  }

  getHistoricalFailureRate(test) {
    // Calculate failure rate from training data
    const testHistory = this.trainingData.filter(data => data.testId === test.id);
    
    if (testHistory.length === 0) {
      return 0.1; // Default 10% failure rate
    }
    
    const failures = testHistory.filter(data => !data.success).length;
    return failures / testHistory.length;
  }

  calculateChangeImpactFactor(test, changes) {
    let impactFactor = 1.0;
    
    // Increase factor based on related changes
    for (const change of changes) {
      if (test.dependencies?.some(dep => change.file.includes(dep))) {
        impactFactor *= 1.5;
      }
      
      if (change.type === 'breaking') {
        impactFactor *= 2.0;
      }
    }
    
    return Math.min(3.0, impactFactor);
  }

  async loadTrainingData() {
    // Load historical test execution data
    // For now, generate sample data
    this.trainingData = [];
  }

  async trainModel() {
    // Train the prediction model
    // For now, use simple statistical model
    console.log('Training predictive model with', this.trainingData.length, 'data points');
  }

  async updateWithResults(results) {
    // Update training data with new results
    for (const failure of results.failures) {
      this.trainingData.push({
        testId: failure.testId,
        success: false,
        timestamp: Date.now()
      });
    }
    
    // Retrain model periodically
    if (this.trainingData.length % 100 === 0) {
      await this.trainModel();
    }
  }
}

class TestShardingStrategy {
  async createShards(tests, maxShards) {
    // Balance shards by execution time and dependencies
    const shards = [];
    
    // Sort tests by estimated duration (longest first)
    const sortedTests = tests.sort((a, b) => 
      (b.estimatedDuration || 5000) - (a.estimatedDuration || 5000)
    );
    
    // Initialize shards
    for (let i = 0; i < Math.min(maxShards, tests.length); i++) {
      shards.push({
        id: i,
        tests: [],
        estimatedDuration: 0,
        dependencies: new Set()
      });
    }
    
    // Distribute tests using longest processing time first algorithm
    for (const test of sortedTests) {
      const optimalShard = this.findOptimalShard(shards, test);
      optimalShard.tests.push(test);
      optimalShard.estimatedDuration += test.estimatedDuration || 5000;
      
      // Add test dependencies to shard
      if (test.dependencies) {
        test.dependencies.forEach(dep => optimalShard.dependencies.add(dep));
      }
    }
    
    return shards;
  }

  findOptimalShard(shards, test) {
    // Find shard with minimal duration that can accommodate the test
    let optimalShard = shards[0];
    
    for (const shard of shards) {
      // Prefer shard with shorter duration
      if (shard.estimatedDuration < optimalShard.estimatedDuration) {
        // Check for dependency conflicts
        if (!this.hasDependencyConflicts(shard, test)) {
          optimalShard = shard;
        }
      }
    }
    
    return optimalShard;
  }

  hasDependencyConflicts(shard, test) {
    // Check if test has conflicting dependencies with shard
    if (!test.conflictsWith) {
      return false;
    }
    
    return test.conflictsWith.some(conflict => shard.dependencies.has(conflict));
  }
}

class FastFailDetector {
  async identifyFastFailTests(tests, predictions) {
    const fastFailTests = [];
    
    for (const test of tests) {
      if (this.shouldBeFastFailTest(test, predictions)) {
        fastFailTests.push(test);
      }
    }
    
    // Sort by failure probability (highest first)
    return fastFailTests.sort((a, b) => {
      const predA = predictions?.get(a.id);
      const predB = predictions?.get(b.id);
      return (predB?.failureProbability || 0) - (predA?.failureProbability || 0);
    });
  }

  shouldBeFastFailTest(test, predictions) {
    // Critical tests should fail fast
    if (test.tags?.includes('critical')) {
      return true;
    }
    
    // Build-breaking tests should fail fast
    if (test.tags?.includes('build-breaking')) {
      return true;
    }
    
    // Tests with high failure probability should fail fast
    const prediction = predictions?.get(test.id);
    if (prediction && prediction.failureProbability > 0.6) {
      return true;
    }
    
    // Fast tests that provide quick feedback
    if ((test.estimatedDuration || 5000) < 2000 && test.tags?.includes('smoke')) {
      return true;
    }
    
    return false;
  }
}

class ExecutionPlanner {
  async createPlan(planningInput) {
    const { allTests, affectedTests, predictions, changes, options } = planningInput;
    
    const plan = {
      allTests: allTests,
      affectedTests: affectedTests,
      selectedTests: allTests, // Initially select all tests
      predictions: predictions,
      changes: changes,
      estimatedDuration: this.calculateEstimatedDuration(allTests),
      optimizations: [],
      metadata: {
        planCreated: Date.now(),
        totalTests: allTests.length,
        affectedTests: affectedTests.length,
        hasChanges: changes.length > 0
      }
    };
    
    return plan;
  }

  calculateEstimatedDuration(tests) {
    return tests.reduce((total, test) => total + (test.estimatedDuration || 5000), 0);
  }
}

class TestDatabase {
  constructor() {
    this.testHistory = new Map();
    this.executionData = [];
  }

  async initialize() {
    // Initialize test database
    console.log('Initializing test database');
  }

  async getLastRunTime(testId) {
    const history = this.testHistory.get(testId);
    return history ? Math.max(...history.map(h => h.timestamp)) : null;
  }

  async updateExecutionResults(results) {
    // Update test execution history
    for (const failure of results.failures) {
      if (!this.testHistory.has(failure.testId)) {
        this.testHistory.set(failure.testId, []);
      }
      
      this.testHistory.get(failure.testId).push({
        timestamp: Date.now(),
        success: false,
        error: failure.error
      });
    }
  }
}

module.exports = {
  IntelligentTestExecutionStrategy,
  ChangeAnalyzer,
  TestPredictiveModel,
  TestShardingStrategy,
  FastFailDetector,
  ExecutionPlanner,
  TestDatabase
};