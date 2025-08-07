/**
 * Parallel Test Execution Framework
 * Optimizes test execution while maintaining quality standards
 */

const cluster = require('cluster');
const os = require('os');
const path = require('path');
const fs = require('fs').promises;
const { performance } = require('perf_hooks');

class ParallelTestExecutor {
  constructor(options = {}) {
    this.maxWorkers = options.maxWorkers || os.cpus().length;
    this.testTimeout = options.testTimeout || 30000;
    this.retryAttempts = options.retryAttempts || 2;
    this.loadBalancer = new TestLoadBalancer();
    this.resultAggregator = new TestResultAggregator();
    this.dependencyResolver = new TestDependencyResolver();
    this.qualityGate = new TestQualityGate();
    this.workers = new Map();
    this.testQueue = [];
    this.runningTests = new Map();
    this.completedTests = new Map();
    this.failedTests = new Map();
  }

  async executeTestSuite(testSuite, options = {}) {
    console.log(`Starting parallel execution of ${testSuite.tests.length} tests`);
    
    const startTime = performance.now();
    
    try {
      // Resolve test dependencies and create execution graph
      const executionGraph = await this.dependencyResolver.createExecutionGraph(testSuite.tests);
      
      // Validate quality gates before execution
      await this.qualityGate.validatePreExecution(testSuite);
      
      // Initialize worker pool
      await this.initializeWorkerPool();
      
      // Execute tests in parallel with dependency management
      const results = await this.executeTestGraph(executionGraph, options);
      
      // Aggregate and validate results
      const aggregatedResults = await this.resultAggregator.aggregate(results);
      
      // Validate quality gates after execution
      await this.qualityGate.validatePostExecution(aggregatedResults);
      
      const endTime = performance.now();
      const executionTime = endTime - startTime;
      
      return {
        success: true,
        results: aggregatedResults,
        executionTime: executionTime,
        testsRun: aggregatedResults.total,
        testsPassed: aggregatedResults.passed,
        testsFailed: aggregatedResults.failed,
        testsSkipped: aggregatedResults.skipped,
        parallelism: this.calculateAchievedParallelism(results),
        resourceUsage: await this.getResourceUsage()
      };
      
    } catch (error) {
      console.error('Test execution failed:', error);
      
      return {
        success: false,
        error: error.message,
        partialResults: this.getPartialResults(),
        executionTime: performance.now() - startTime
      };
    } finally {
      // Cleanup worker pool
      await this.cleanupWorkerPool();
    }
  }

  async executeTestGraph(executionGraph, options) {
    const results = new Map();
    const availableWorkers = Array.from(this.workers.keys());
    const executionQueue = this.buildExecutionQueue(executionGraph);
    
    while (executionQueue.length > 0 || this.runningTests.size > 0) {
      // Find tests that can be executed (dependencies satisfied)
      const readyTests = executionQueue.filter(test => 
        this.areDependenciesSatisfied(test, results)
      );
      
      // Assign tests to available workers
      for (const test of readyTests) {
        const worker = this.loadBalancer.selectOptimalWorker(availableWorkers, test);
        
        if (worker && !this.runningTests.has(worker)) {
          // Remove test from queue
          const testIndex = executionQueue.indexOf(test);
          executionQueue.splice(testIndex, 1);
          
          // Execute test on worker
          this.executeTestOnWorker(worker, test, results, options);
        }
      }
      
      // Wait for at least one test to complete
      if (this.runningTests.size > 0) {
        await this.waitForNextCompletion();
      }
      
      // Update available workers
      availableWorkers.splice(0, availableWorkers.length);
      for (const [workerId, worker] of this.workers) {
          if (!this.runningTests.has(workerId)) {
            availableWorkers.push(workerId);
          }
        }
    }
    
    return results;
  }

  async executeTestOnWorker(workerId, test, results, options) {
    const worker = this.workers.get(workerId);
    
    return new Promise((resolve, reject) => {
      const testExecution = {
        test: test,
        startTime: performance.now(),
        timeout: setTimeout(() => {
          this.handleTestTimeout(workerId, test);
          reject(new Error(`Test timeout: ${test.name}`));
        }, this.testTimeout)
      };
      
      this.runningTests.set(workerId, testExecution);
      
      worker.send({
        type: 'executeTest',
        test: test,
        options: options
      });
      
      const handleMessage = (message) => {
        if (message.type === 'testComplete' && message.testId === test.id) {
          clearTimeout(testExecution.timeout);
          this.runningTests.delete(workerId);
          
          const endTime = performance.now();
          const result = {
            ...message.result,
            executionTime: endTime - testExecution.startTime,
            workerId: workerId
          };
          
          results.set(test.id, result);
          
          // Handle retries for failed tests
          if (!result.success && result.retryCount < this.retryAttempts) {
            this.retryTest(test, result.retryCount + 1, results, options);
          }
          
          worker.off('message', handleMessage);
          resolve(result);
        }
      };
      
      worker.on('message', handleMessage);
    });
  }

  buildExecutionQueue(executionGraph) {
    // Topological sort with priority optimization
    const queue = [];
    const inDegree = new Map();
    const priorityMap = new Map();
    
    // Calculate in-degrees and priorities
    for (const test of executionGraph.nodes) {
      inDegree.set(test.id, executionGraph.getDependencies(test.id).length);
      priorityMap.set(test.id, this.calculateTestPriority(test));
    }
    
    // Build initial queue with tests that have no dependencies
    const readyTests = executionGraph.nodes.filter(test => inDegree.get(test.id) === 0);
    
    // Sort by priority (critical tests first)
    readyTests.sort((a, b) => priorityMap.get(b.id) - priorityMap.get(a.id));
    
    queue.push(...readyTests);
    
    return queue;
  }

  calculateTestPriority(test) {
    let priority = 0;
    
    // Critical tests get highest priority
    if (test.tags && test.tags.includes('critical')) {
      priority += 100;
    }
    
    // Fast-fail tests get high priority
    if (test.estimatedDuration && test.estimatedDuration < 1000) {
      priority += 50;
    }
    
    // Tests with many dependents get higher priority
    if (test.dependents) {
      priority += test.dependents.length * 10;
    }
    
    // Recently failed tests get priority for fast feedback
    if (test.recentlyFailed) {
      priority += 75;
    }
    
    return priority;
  }

  areDependenciesSatisfied(test, completedResults) {
    if (!test.dependencies || test.dependencies.length === 0) {
      return true;
    }
    
    return test.dependencies.every(depId => {
      const result = completedResults.get(depId);
      return result && result.success;
    });
  }

  async initializeWorkerPool() {
    console.log(`Initializing worker pool with ${this.maxWorkers} workers`);
    
    for (let i = 0; i < this.maxWorkers; i++) {
      const worker = cluster.fork();
      
      worker.on('error', (error) => {
        console.error(`Worker ${worker.id} error:`, error);
        this.handleWorkerError(worker.id, error);
      });
      
      worker.on('exit', (code, signal) => {
        console.log(`Worker ${worker.id} exited with code ${code} and signal ${signal}`);
        this.handleWorkerExit(worker.id, code, signal);
      });
      
      this.workers.set(worker.id, worker);
    }
    
    // Wait for all workers to be ready
    await this.waitForWorkersReady();
  }

  async cleanupWorkerPool() {
    console.log('Cleaning up worker pool');
    
    for (const [workerId, worker] of this.workers) {
      worker.kill();
    }
    
    this.workers.clear();
    this.runningTests.clear();
  }

  calculateAchievedParallelism(results) {
    if (results.size === 0) return 0;
    
    // Calculate time-weighted parallelism
    const timeline = [];
    
    for (const [testId, result] of results) {
      timeline.push({
        time: result.startTime,
        type: 'start',
        testId: testId
      });
      
      timeline.push({
        time: result.startTime + result.executionTime,
        type: 'end',
        testId: testId
      });
    }
    
    timeline.sort((a, b) => a.time - b.time);
    
    let currentParallel = 0;
    let totalWeightedParallel = 0;
    let totalTime = 0;
    let lastTime = timeline[0]?.time || 0;
    
    for (const event of timeline) {
      const timeDelta = event.time - lastTime;
      totalWeightedParallel += currentParallel * timeDelta;
      totalTime += timeDelta;
      
      if (event.type === 'start') {
        currentParallel++;
      } else {
        currentParallel--;
      }
      
      lastTime = event.time;
    }
    
    return totalTime > 0 ? totalWeightedParallel / totalTime : 0;
  }

  async getResourceUsage() {
    const usage = process.memoryUsage();
    const cpuUsage = process.cpuUsage();
    
    return {
      memory: {
        rss: usage.rss,
        heapTotal: usage.heapTotal,
        heapUsed: usage.heapUsed,
        external: usage.external
      },
      cpu: {
        user: cpuUsage.user,
        system: cpuUsage.system
      },
      workers: this.workers.size,
      runningTests: this.runningTests.size
    };
  }
}

class TestLoadBalancer {
  constructor() {
    this.workerStats = new Map();
    this.testTypeAffinities = new Map();
  }

  selectOptimalWorker(availableWorkers, test) {
    if (availableWorkers.length === 0) {
      return null;
    }
    
    // Consider worker load, test type affinity, and resource requirements
    let bestWorker = null;
    let bestScore = -1;
    
    for (const workerId of availableWorkers) {
      const score = this.calculateWorkerScore(workerId, test);
      
      if (score > bestScore) {
        bestScore = score;
        bestWorker = workerId;
      }
    }
    
    // Update worker stats
    if (bestWorker) {
      this.updateWorkerStats(bestWorker, test);
    }
    
    return bestWorker;
  }

  calculateWorkerScore(workerId, test) {
    const stats = this.workerStats.get(workerId) || {
      completedTests: 0,
      averageExecutionTime: 0,
      lastTestType: null,
      resourceUtilization: 0
    };
    
    let score = 100;
    
    // Prefer workers with lower utilization
    score -= stats.resourceUtilization * 50;
    
    // Prefer workers with affinity for test type
    if (stats.lastTestType === test.type) {
      score += 20; // Cache locality bonus
    }
    
    // Prefer workers with better performance history
    if (stats.averageExecutionTime > 0) {
      const performanceBonus = Math.max(0, 10 - (stats.averageExecutionTime / 1000));
      score += performanceBonus;
    }
    
    return score;
  }

  updateWorkerStats(workerId, test) {
    const stats = this.workerStats.get(workerId) || {
      completedTests: 0,
      averageExecutionTime: 0,
      lastTestType: null,
      resourceUtilization: 0
    };
    
    stats.lastTestType = test.type;
    this.workerStats.set(workerId, stats);
  }
}

class TestResultAggregator {
  constructor() {
    this.coverageAggregator = new CoverageAggregator();
    this.metricsAggregator = new MetricsAggregator();
  }

  async aggregate(testResults) {
    const summary = {
      total: testResults.size,
      passed: 0,
      failed: 0,
      skipped: 0,
      duration: 0,
      coverage: null,
      metrics: {},
      failures: [],
      warnings: []
    };
    
    let totalDuration = 0;
    const coverageData = [];
    const metricsData = [];
    
    for (const [testId, result] of testResults) {
      // Update summary counts
      if (result.success) {
        summary.passed++;
      } else if (result.skipped) {
        summary.skipped++;
      } else {
        summary.failed++;
        summary.failures.push({
          testId: testId,
          name: result.name,
          error: result.error,
          duration: result.executionTime
        });
      }
      
      // Aggregate duration
      totalDuration = Math.max(totalDuration, result.executionTime);
      
      // Collect coverage data
      if (result.coverage) {
        coverageData.push(result.coverage);
      }
      
      // Collect metrics
      if (result.metrics) {
        metricsData.push(result.metrics);
      }
      
      // Collect warnings
      if (result.warnings) {
        summary.warnings.push(...result.warnings);
      }
    }
    
    summary.duration = totalDuration;
    
    // Aggregate coverage
    if (coverageData.length > 0) {
      summary.coverage = await this.coverageAggregator.aggregate(coverageData);
    }
    
    // Aggregate metrics
    if (metricsData.length > 0) {
      summary.metrics = await this.metricsAggregator.aggregate(metricsData);
    }
    
    return summary;
  }
}

class TestDependencyResolver {
  async createExecutionGraph(tests) {
    const graph = {
      nodes: tests,
      edges: new Map(),
      getDependencies: (testId) => {
        return this.edges.get(testId) || [];
      }
    };
    
    // Analyze test dependencies
    for (const test of tests) {
      if (test.dependencies) {
        graph.edges.set(test.id, test.dependencies);
      }
      
      // Auto-detect implicit dependencies
      const implicitDeps = await this.detectImplicitDependencies(test, tests);
      if (implicitDeps.length > 0) {
        const existingDeps = graph.edges.get(test.id) || [];
        graph.edges.set(test.id, [...existingDeps, ...implicitDeps]);
      }
    }
    
    // Validate for circular dependencies
    this.validateNoCycles(graph);
    
    return graph;
  }

  async detectImplicitDependencies(test, allTests) {
    const dependencies = [];
    
    // Database setup dependencies
    if (test.requiresDatabase && !test.setupsDatabase) {
      const setupTests = allTests.filter(t => t.setupsDatabase);
      dependencies.push(...setupTests.map(t => t.id));
    }
    
    // File system dependencies
    if (test.requiresFiles) {
      const fileSetupTests = allTests.filter(t => 
        t.createsFiles && 
        test.requiresFiles.some(file => t.createsFiles.includes(file))
      );
      dependencies.push(...fileSetupTests.map(t => t.id));
    }
    
    // Service dependencies
    if (test.requiresServices) {
      const serviceTests = allTests.filter(t => 
        t.startsServices && 
        test.requiresServices.some(service => t.startsServices.includes(service))
      );
      dependencies.push(...serviceTests.map(t => t.id));
    }
    
    return [...new Set(dependencies)]; // Remove duplicates
  }

  validateNoCycles(graph) {
    const visited = new Set();
    const recursionStack = new Set();
    
    const hasCycle = (nodeId) => {
      visited.add(nodeId);
      recursionStack.add(nodeId);
      
      const dependencies = graph.getDependencies(nodeId);
      
      for (const depId of dependencies) {
        if (!visited.has(depId)) {
          if (hasCycle(depId)) {
            return true;
          }
        } else if (recursionStack.has(depId)) {
          return true;
        }
      }
      
      recursionStack.delete(nodeId);
      return false;
    };
    
    for (const test of graph.nodes) {
      if (!visited.has(test.id)) {
        if (hasCycle(test.id)) {
          throw new Error(`Circular dependency detected involving test: ${test.id}`);
        }
      }
    }
  }
}

class TestQualityGate {
  constructor(options = {}) {
    this.minCoverage = options.minCoverage || 80;
    this.maxFailureRate = options.maxFailureRate || 0.05;
    this.requiredTags = options.requiredTags || ['critical'];
  }

  async validatePreExecution(testSuite) {
    // Validate test suite completeness
    const criticalTests = testSuite.tests.filter(test => 
      test.tags && test.tags.includes('critical')
    );
    
    if (criticalTests.length === 0) {
      throw new Error('No critical tests found in test suite');
    }
    
    // Validate test isolation
    await this.validateTestIsolation(testSuite.tests);
    
    // Validate resource requirements
    await this.validateResourceRequirements(testSuite.tests);
  }

  async validatePostExecution(results) {
    // Validate failure rate
    const failureRate = results.failed / results.total;
    if (failureRate > this.maxFailureRate) {
      throw new Error(`Failure rate ${(failureRate * 100).toFixed(2)}% exceeds maximum allowed ${(this.maxFailureRate * 100)}%`);
    }
    
    // Validate coverage
    if (results.coverage && results.coverage.percentage < this.minCoverage) {
      throw new Error(`Coverage ${results.coverage.percentage}% below required ${this.minCoverage}%`);
    }
    
    // Validate critical tests passed
    const criticalFailures = results.failures.filter(failure => 
      failure.tags && failure.tags.includes('critical')
    );
    
    if (criticalFailures.length > 0) {
      throw new Error(`Critical tests failed: ${criticalFailures.map(f => f.name).join(', ')}`);
    }
  }

  async validateTestIsolation(tests) {
    // Check for potential test interference
    const resourceConflicts = this.detectResourceConflicts(tests);
    
    if (resourceConflicts.length > 0) {
      console.warn('Potential test isolation issues detected:', resourceConflicts);
    }
  }

  detectResourceConflicts(tests) {
    const conflicts = [];
    const resourceMap = new Map();
    
    for (const test of tests) {
      if (test.resources) {
        for (const resource of test.resources) {
          if (!resourceMap.has(resource)) {
            resourceMap.set(resource, []);
          }
          resourceMap.get(resource).push(test.id);
        }
      }
    }
    
    for (const [resource, testIds] of resourceMap) {
      if (testIds.length > 1) {
        conflicts.push({
          resource: resource,
          conflictingTests: testIds
        });
      }
    }
    
    return conflicts;
  }
}

module.exports = {
  ParallelTestExecutor,
  TestLoadBalancer,
  TestResultAggregator,
  TestDependencyResolver,
  TestQualityGate
};