/**
 * Example Usage of Pipeline Performance Optimizer
 * Demonstrates various optimization scenarios and configurations
 */

const { PipelinePerformanceOrchestrator } = require('../src/pipeline-orchestrator');

// Example 1: Basic Pipeline Optimization
async function basicOptimizationExample() {
  console.log('=== Basic Pipeline Optimization Example ===');
  
  const orchestrator = new PipelinePerformanceOrchestrator({
    qualityThreshold: 100,
    performanceTargets: {
      testExecutionSpeed: 2.0,
      cacheHitRate: 0.85,
      resourceEfficiency: 0.75,
      pipelineDuration: 0.6
    }
  });

  // Sample pipeline configuration
  const pipelineConfig = {
    name: 'basic-web-app-pipeline',
    stages: [
      {
        name: 'install-dependencies',
        type: 'build',
        steps: ['npm ci'],
        estimatedDuration: 60000
      },
      {
        name: 'lint',
        type: 'lint',
        steps: ['npm run lint'],
        estimatedDuration: 30000,
        depends_on: ['install-dependencies']
      },
      {
        name: 'test',
        type: 'test',
        steps: ['npm test'],
        estimatedDuration: 120000,
        depends_on: ['install-dependencies']
      },
      {
        name: 'build',
        type: 'build',
        steps: ['npm run build'],
        estimatedDuration: 90000,
        depends_on: ['test', 'lint']
      },
      {
        name: 'deploy',
        type: 'deploy',
        steps: ['npm run deploy'],
        estimatedDuration: 180000,
        depends_on: ['build']
      }
    ]
  };

  // Sample test suite
  const testSuite = {
    tests: [
      {
        id: 'unit-tests-auth',
        name: 'Authentication Unit Tests',
        type: 'unit',
        estimatedDuration: 5000,
        tags: ['critical', 'auth'],
        dependencies: []
      },
      {
        id: 'unit-tests-user',
        name: 'User Management Unit Tests', 
        type: 'unit',
        estimatedDuration: 8000,
        tags: ['user'],
        dependencies: []
      },
      {
        id: 'integration-api',
        name: 'API Integration Tests',
        type: 'integration',
        estimatedDuration: 15000,
        tags: ['api'],
        dependencies: ['unit-tests-auth']
      },
      {
        id: 'e2e-critical-flow',
        name: 'Critical User Flow E2E',
        type: 'e2e',
        estimatedDuration: 45000,
        tags: ['critical', 'e2e'],
        dependencies: ['integration-api']
      }
    ]
  };

  try {
    await orchestrator.initialize();
    
    const result = await orchestrator.optimizePipeline(
      pipelineConfig,
      testSuite,
      { maintainQuality: true }
    );

    if (result.success) {
      console.log('✅ Basic optimization completed successfully!');
      console.log(`Performance improvement: ${result.performanceGains?.overall || 0}%`);
      console.log(`Quality maintained: ${result.qualityMaintained}`);
      console.log(`Applied optimizations: ${result.report.summary.totalOptimizations}`);
    } else {
      console.error('❌ Basic optimization failed:', result.error);
    }

    return result;
  } catch (error) {
    console.error('❌ Basic optimization error:', error.message);
    throw error;
  }
}

// Example 2: Advanced Configuration with Custom Settings
async function advancedOptimizationExample() {
  console.log('\n=== Advanced Pipeline Optimization Example ===');
  
  const orchestrator = new PipelinePerformanceOrchestrator({
    // Higher quality threshold for production
    qualityThreshold: 100,
    
    // Aggressive performance targets
    performanceTargets: {
      testExecutionSpeed: 3.0,  // 3x faster
      cacheHitRate: 0.90,       // 90% cache hit rate
      resourceEfficiency: 0.80, // 80% resource efficiency
      pipelineDuration: 0.5     // 50% duration reduction
    },
    
    // Advanced test execution settings
    testExecution: {
      maxWorkers: 16,
      testTimeout: 45000,
      retryAttempts: 3,
      fastFail: true,
      selective: true,
      sharding: true,
      prediction: true
    },
    
    // Advanced caching configuration
    cache: {
      cacheDir: './cache',
      maxCacheSize: 2 * 1024 * 1024 * 1024, // 2GB
      compression: true,
      encryption: true,
      layers: {
        L1: { maxSize: 200 * 1024 * 1024, ttl: 600000 },  // 200MB, 10min
        L2: { maxSize: 800 * 1024 * 1024, ttl: 3600000 }, // 800MB, 1hr  
        L3: { maxSize: 1024 * 1024 * 1024, ttl: 7200000 } // 1GB, 2hr
      }
    },
    
    // Resource optimization settings
    resources: {
      maxCpuPercent: 90,
      maxMemoryMB: 4096,
      monitoring: true,
      autoScaling: true
    },
    
    // Performance monitoring
    metrics: {
      collectionInterval: 2000,
      realTimeMonitoring: true,
      alerting: true
    }
  });

  // Complex pipeline with multiple parallel paths
  const complexPipelineConfig = {
    name: 'advanced-microservices-pipeline',
    stages: [
      // Parallel preparation stages
      {
        name: 'install-frontend-deps',
        type: 'build',
        steps: ['cd frontend && npm ci'],
        estimatedDuration: 80000,
        resources: { cpu: 2, memory: 1024 }
      },
      {
        name: 'install-backend-deps',
        type: 'build', 
        steps: ['cd backend && npm ci'],
        estimatedDuration: 70000,
        resources: { cpu: 2, memory: 1024 }
      },
      {
        name: 'install-shared-deps',
        type: 'build',
        steps: ['cd shared && npm ci'],
        estimatedDuration: 30000,
        resources: { cpu: 1, memory: 512 }
      },
      
      // Parallel quality checks
      {
        name: 'lint-frontend',
        type: 'lint',
        steps: ['cd frontend && npm run lint'],
        estimatedDuration: 20000,
        depends_on: ['install-frontend-deps', 'install-shared-deps'],
        cacheable: true
      },
      {
        name: 'lint-backend',
        type: 'lint',
        steps: ['cd backend && npm run lint'],
        estimatedDuration: 25000,
        depends_on: ['install-backend-deps', 'install-shared-deps'],
        cacheable: true
      },
      {
        name: 'security-scan',
        type: 'security',
        steps: ['npm audit', 'snyk test'],
        estimatedDuration: 45000,
        depends_on: ['install-frontend-deps', 'install-backend-deps'],
        tags: ['critical']
      },
      
      // Parallel testing stages
      {
        name: 'test-frontend',
        type: 'test',
        steps: ['cd frontend && npm test'],
        estimatedDuration: 90000,
        depends_on: ['lint-frontend']
      },
      {
        name: 'test-backend',
        type: 'test', 
        steps: ['cd backend && npm test'],
        estimatedDuration: 120000,
        depends_on: ['lint-backend']
      },
      {
        name: 'test-integration',
        type: 'test',
        steps: ['npm run test:integration'],
        estimatedDuration: 180000,
        depends_on: ['test-frontend', 'test-backend']
      },
      
      // Parallel build stages
      {
        name: 'build-frontend',
        type: 'build',
        steps: ['cd frontend && npm run build'],
        estimatedDuration: 60000,
        depends_on: ['test-frontend'],
        artifacts: ['frontend/dist/**']
      },
      {
        name: 'build-backend',
        type: 'build',
        steps: ['cd backend && npm run build'], 
        estimatedDuration: 40000,
        depends_on: ['test-backend'],
        artifacts: ['backend/dist/**']
      },
      
      // E2E testing
      {
        name: 'test-e2e',
        type: 'test',
        steps: ['npm run test:e2e'],
        estimatedDuration: 300000,
        depends_on: ['build-frontend', 'build-backend', 'test-integration'],
        resources: { cpu: 4, memory: 2048 }
      },
      
      // Deployment stages
      {
        name: 'deploy-staging',
        type: 'deploy',
        steps: ['npm run deploy:staging'],
        estimatedDuration: 120000,
        depends_on: ['test-e2e', 'security-scan']
      },
      {
        name: 'deploy-production',
        type: 'deploy',
        steps: ['npm run deploy:production'],
        estimatedDuration: 180000,
        depends_on: ['deploy-staging'],
        manual: true
      }
    ]
  };

  // Comprehensive test suite
  const comprehensiveTestSuite = {
    tests: generateTestSuite(200) // 200 tests of various types
  };

  try {
    await orchestrator.initialize();
    
    console.log('Starting advanced optimization...');
    const startTime = Date.now();
    
    const result = await orchestrator.optimizePipeline(
      complexPipelineConfig,
      comprehensiveTestSuite,
      {
        maintainQuality: true,
        maxOptimizationTime: 600000, // 10 minutes max
        aggressiveOptimization: true
      }
    );

    const duration = Date.now() - startTime;
    
    if (result.success) {
      console.log('✅ Advanced optimization completed successfully!');
      console.log(`Optimization time: ${duration}ms`);
      console.log(`Performance improvement: ${result.performanceGains?.overall || 0}%`);
      console.log(`Quality maintained: ${result.qualityMaintained}`);
      console.log(`Cache optimization: ${result.report.performanceGains.caching.hitRateImprovement}%`);
      console.log(`Resource efficiency: ${result.report.performanceGains.resources.utilizationImprovement}%`);
      console.log(`Pipeline duration reduction: ${result.report.performanceGains.pipeline.durationReduction}%`);
      
      // Show detailed breakdown
      console.log('\nOptimization Breakdown:');
      console.log(`- Test execution speed: ${result.report.performanceGains.testExecution.speedImprovement}%`);
      console.log(`- Parallelism gain: ${result.report.performanceGains.testExecution.parallelismGain}%`);
      console.log(`- Cache hit rate improvement: ${result.report.performanceGains.caching.hitRateImprovement}%`);
      console.log(`- Resource utilization improvement: ${result.report.performanceGains.resources.utilizationImprovement}%`);
      
    } else {
      console.error('❌ Advanced optimization failed:', result.error);
    }

    return result;
  } catch (error) {
    console.error('❌ Advanced optimization error:', error.message);
    throw error;
  }
}

// Example 3: Real-time Monitoring and Metrics
async function monitoringExample() {
  console.log('\n=== Real-time Monitoring Example ===');
  
  const orchestrator = new PipelinePerformanceOrchestrator({
    metrics: {
      realTimeMonitoring: true,
      collectionInterval: 1000,
      alerting: true
    }
  });

  await orchestrator.initialize();
  
  // Start monitoring
  console.log('Starting real-time monitoring...');
  
  // Get initial metrics
  const initialReport = await orchestrator.getOrchestrationReport();
  console.log('Initial system status:', initialReport.systemHealth);
  
  // Monitor for 30 seconds
  const monitoringInterval = setInterval(async () => {
    try {
      const currentMetrics = await orchestrator.collectCurrentMetrics();
      
      console.log(`[${new Date().toISOString()}] Metrics:`, {
        cpu: `${currentMetrics.resources?.cpu || 0}%`,
        memory: `${currentMetrics.resources?.memory || 0}%`,
        activeOptimizations: initialReport.activeOptimizations,
        qualityScore: `${currentMetrics.quality?.overallScore || 100}%`
      });
      
    } catch (error) {
      console.error('Monitoring error:', error.message);
    }
  }, 5000);
  
  // Stop monitoring after 30 seconds
  setTimeout(() => {
    clearInterval(monitoringInterval);
    console.log('Monitoring stopped');
  }, 30000);
  
  return new Promise(resolve => {
    setTimeout(resolve, 35000);
  });
}

// Helper function to generate test suite
function generateTestSuite(testCount) {
  const tests = [];
  const testTypes = ['unit', 'integration', 'e2e', 'performance'];
  const tags = ['critical', 'auth', 'user', 'api', 'ui', 'database', 'security'];
  
  for (let i = 0; i < testCount; i++) {
    const testType = testTypes[i % testTypes.length];
    const testTags = [tags[i % tags.length]];
    
    // Add critical tag to some tests
    if (i < 20) {
      testTags.push('critical');
    }
    
    // Add smoke tag to fast tests
    if (testType === 'unit' && i % 10 === 0) {
      testTags.push('smoke');
    }
    
    tests.push({
      id: `test-${i + 1}`,
      name: `${testType.charAt(0).toUpperCase() + testType.slice(1)} Test ${i + 1}`,
      type: testType,
      estimatedDuration: getEstimatedDuration(testType),
      tags: testTags,
      dependencies: getDependencies(i, testType),
      requiresDatabase: testType === 'integration' && Math.random() > 0.7,
      requiresServices: testType === 'e2e' && Math.random() > 0.8,
      requiresFiles: testType === 'performance' ? ['test-data.json'] : undefined
    });
  }
  
  return tests;
}

function getEstimatedDuration(testType) {
  const durations = {
    'unit': () => Math.random() * 5000 + 1000,        // 1-6 seconds
    'integration': () => Math.random() * 15000 + 5000, // 5-20 seconds
    'e2e': () => Math.random() * 30000 + 15000,       // 15-45 seconds
    'performance': () => Math.random() * 60000 + 30000 // 30-90 seconds
  };
  
  return Math.round(durations[testType]());
}

function getDependencies(index, testType) {
  const dependencies = [];
  
  // Integration tests depend on some unit tests
  if (testType === 'integration' && index > 10) {
    const depIndex = Math.max(0, index - Math.floor(Math.random() * 10));
    dependencies.push(`test-${depIndex}`);
  }
  
  // E2E tests depend on integration tests
  if (testType === 'e2e' && index > 50) {
    const depIndex = Math.max(20, index - Math.floor(Math.random() * 30));
    dependencies.push(`test-${depIndex}`);
  }
  
  return dependencies;
}

// Example 4: Error Handling and Recovery
async function errorHandlingExample() {
  console.log('\n=== Error Handling Example ===');
  
  const orchestrator = new PipelinePerformanceOrchestrator();
  
  // Invalid pipeline configuration to test error handling
  const invalidPipelineConfig = {
    name: 'invalid-pipeline',
    stages: null // This will cause an error
  };
  
  const testSuite = { tests: [] };
  
  try {
    await orchestrator.initialize();
    
    const result = await orchestrator.optimizePipeline(
      invalidPipelineConfig,
      testSuite
    );
    
    if (!result.success) {
      console.log('✅ Error handling worked correctly');
      console.log(`Error captured: ${result.error}`);
    } else {
      console.log('❌ Expected error was not captured');
    }
    
    return result;
  } catch (error) {
    console.log('✅ Exception handling worked correctly');
    console.log(`Exception: ${error.message}`);
    return { success: false, error: error.message };
  }
}

// Example 5: Performance Benchmarking
async function benchmarkingExample() {
  console.log('\n=== Performance Benchmarking Example ===');
  
  const configurations = [
    { workers: 2, cacheSize: 50 * 1024 * 1024 },
    { workers: 4, cacheSize: 100 * 1024 * 1024 },
    { workers: 8, cacheSize: 200 * 1024 * 1024 }
  ];
  
  const results = [];
  
  for (const config of configurations) {
    console.log(`\nBenchmarking configuration: ${JSON.stringify(config)}`);
    
    const orchestrator = new PipelinePerformanceOrchestrator({
      testExecution: { maxWorkers: config.workers },
      cache: { maxCacheSize: config.cacheSize }
    });
    
    const pipelineConfig = {
      name: `benchmark-pipeline-${config.workers}w`,
      stages: [
        { name: 'test', type: 'test', estimatedDuration: 60000 }
      ]
    };
    
    const testSuite = { tests: generateTestSuite(100) };
    
    const startTime = Date.now();
    
    try {
      await orchestrator.initialize();
      const result = await orchestrator.optimizePipeline(pipelineConfig, testSuite);
      
      const duration = Date.now() - startTime;
      
      results.push({
        configuration: config,
        duration: duration,
        success: result.success,
        performanceGain: result.performanceGains?.overall || 0
      });
      
      console.log(`Benchmark completed in ${duration}ms`);
      
    } catch (error) {
      console.error(`Benchmark failed: ${error.message}`);
      results.push({
        configuration: config,
        duration: Date.now() - startTime,
        success: false,
        error: error.message
      });
    }
  }
  
  // Print benchmark results
  console.log('\n📊 Benchmark Results:');
  console.log('Config\t\tDuration\tSuccess\tGain');
  console.log('------\t\t--------\t-------\t----');
  
  for (const result of results) {
    const config = `${result.configuration.workers}w/${Math.round(result.configuration.cacheSize / 1024 / 1024)}MB`;
    const duration = `${result.duration}ms`;
    const success = result.success ? '✅' : '❌';
    const gain = result.performanceGain ? `${result.performanceGain.toFixed(1)}%` : 'N/A';
    
    console.log(`${config}\t\t${duration}\t${success}\t${gain}`);
  }
  
  return results;
}

// Main execution function
async function runExamples() {
  console.log('🚀 Pipeline Performance Optimizer - Example Usage\n');
  
  try {
    // Run all examples
    await basicOptimizationExample();
    await advancedOptimizationExample();
    await monitoringExample();
    await errorHandlingExample();
    await benchmarkingExample();
    
    console.log('\n🎉 All examples completed successfully!');
    
  } catch (error) {
    console.error('\n❌ Example execution failed:', error.message);
    process.exit(1);
  }
}

// Export functions for individual use
module.exports = {
  basicOptimizationExample,
  advancedOptimizationExample,
  monitoringExample,
  errorHandlingExample,
  benchmarkingExample,
  runExamples
};

// Run examples if this file is executed directly
if (require.main === module) {
  runExamples().catch(error => {
    console.error('Failed to run examples:', error);
    process.exit(1);
  });
}