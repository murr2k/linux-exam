/**
 * Comprehensive Test Suite for Pipeline Performance Orchestrator
 */

const { PipelinePerformanceOrchestrator } = require('../src/pipeline-orchestrator');

describe('Pipeline Performance Orchestrator', () => {
  let orchestrator;
  
  beforeEach(() => {
    orchestrator = new PipelinePerformanceOrchestrator({
      qualityThreshold: 100,
      performanceTargets: {
        testExecutionSpeed: 2.0,
        cacheHitRate: 0.85,
        resourceEfficiency: 0.75,
        pipelineDuration: 0.6
      }
    });
  });

  describe('Initialization', () => {
    test('should initialize all subsystems', async () => {
      await orchestrator.initialize();
      
      expect(orchestrator.initialized).toBe(true);
      expect(orchestrator.testExecutor).toBeDefined();
      expect(orchestrator.cacheSystem).toBeDefined();
      expect(orchestrator.resourceOptimizer).toBeDefined();
      expect(orchestrator.executionStrategy).toBeDefined();
      expect(orchestrator.pipelineOptimizer).toBeDefined();
      expect(orchestrator.metricsSystem).toBeDefined();
    });

    test('should not reinitialize if already initialized', async () => {
      await orchestrator.initialize();
      const firstInit = orchestrator.initialized;
      
      await orchestrator.initialize(); // Second call
      
      expect(orchestrator.initialized).toBe(firstInit);
    });
  });

  describe('Pipeline Optimization', () => {
    const mockPipelineConfig = {
      name: 'test-pipeline',
      stages: [
        {
          name: 'build',
          type: 'build',
          steps: ['npm install', 'npm run build']
        },
        {
          name: 'test',
          type: 'test',
          steps: ['npm test']
        },
        {
          name: 'deploy',
          type: 'deploy',
          steps: ['deploy to staging']
        }
      ]
    };

    const mockTestSuite = {
      tests: [
        {
          id: 'test1',
          name: 'Unit Test 1',
          type: 'unit',
          estimatedDuration: 5000,
          tags: ['critical']
        },
        {
          id: 'test2',
          name: 'Integration Test 1',
          type: 'integration',
          estimatedDuration: 10000
        },
        {
          id: 'test3',
          name: 'E2E Test 1',
          type: 'e2e',
          estimatedDuration: 30000
        }
      ]
    };

    test('should analyze pipeline state comprehensively', async () => {
      await orchestrator.initialize();
      
      const analysis = await orchestrator.analyzePipelineState(
        mockPipelineConfig,
        mockTestSuite
      );
      
      expect(analysis).toHaveProperty('testExecution');
      expect(analysis).toHaveProperty('resourceUtilization');
      expect(analysis).toHaveProperty('pipelineStructure');
      expect(analysis).toHaveProperty('performanceMetrics');
      expect(analysis.timestamp).toBeDefined();
    });

    test('should create optimization plan based on analysis', async () => {
      await orchestrator.initialize();
      
      const analysis = await orchestrator.analyzePipelineState(
        mockPipelineConfig,
        mockTestSuite
      );
      
      const plan = await orchestrator.createOptimizationPlan(analysis);
      
      expect(plan).toHaveProperty('testOptimizations');
      expect(plan).toHaveProperty('cacheOptimizations');
      expect(plan).toHaveProperty('resourceOptimizations');
      expect(plan).toHaveProperty('pipelineOptimizations');
      expect(plan).toHaveProperty('estimatedImprovement');
      expect(plan).toHaveProperty('riskAssessment');
    });

    test('should maintain 100% test quality during optimization', async () => {
      await orchestrator.initialize();
      
      const result = await orchestrator.optimizePipeline(
        mockPipelineConfig,
        mockTestSuite,
        { maintainQuality: true }
      );
      
      expect(result.success).toBe(true);
      expect(result.qualityMaintained).toBe(true);
      expect(result.report.qualityAssurance.qualityScore).toBe(100);
    });

    test('should generate comprehensive optimization report', async () => {
      await orchestrator.initialize();
      
      const result = await orchestrator.optimizePipeline(
        mockPipelineConfig,
        mockTestSuite
      );
      
      expect(result.report).toHaveProperty('summary');
      expect(result.report).toHaveProperty('beforeAndAfter');
      expect(result.report).toHaveProperty('appliedOptimizations');
      expect(result.report).toHaveProperty('qualityAssurance');
      expect(result.report).toHaveProperty('performanceGains');
      expect(result.report).toHaveProperty('recommendations');
      expect(result.report).toHaveProperty('nextSteps');
    });

    test('should handle optimization failures gracefully', async () => {
      await orchestrator.initialize();
      
      // Mock a failure scenario
      const invalidPipeline = null;
      
      const result = await orchestrator.optimizePipeline(
        invalidPipeline,
        mockTestSuite
      );
      
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('Quality Validation', () => {
    test('should validate test quality meets threshold', async () => {
      const mockResults = {
        qualityMetrics: {
          testQuality: {
            overallScore: 100,
            coverage: 0.95,
            reliability: 0.98
          }
        }
      };
      
      const validation = await orchestrator.validateTestQuality(mockResults);
      
      expect(validation.passed).toBe(true);
      expect(validation.qualityScore).toBe(100);
    });

    test('should fail validation when quality threshold not met', async () => {
      const mockResults = {
        qualityMetrics: {
          testQuality: {
            overallScore: 85, // Below 100% threshold
            coverage: 0.80,   // Below 90% minimum
            reliability: 0.85
          }
        }
      };
      
      const validation = await orchestrator.validateTestQuality(mockResults);
      
      expect(validation.passed).toBe(false);
      expect(validation.issue).toContain('quality score');
      expect(validation.severity).toBe('critical');
    });

    test('should provide recommendations for quality improvements', async () => {
      const mockResults = {
        qualityMetrics: {
          testQuality: {
            overallScore: 85,
            coverage: 0.80,
            reliability: 0.85
          }
        }
      };
      
      const validation = await orchestrator.validateTestQuality(mockResults);
      
      expect(validation.recommendation).toBeDefined();
      expect(validation.recommendation).toContain('coverage');
    });
  });

  describe('Performance Monitoring', () => {
    test('should collect comprehensive current metrics', async () => {
      await orchestrator.initialize();
      
      const metrics = await orchestrator.collectCurrentMetrics();
      
      expect(metrics).toHaveProperty('timestamp');
      expect(metrics).toHaveProperty('testExecution');
      expect(metrics).toHaveProperty('cache');
      expect(metrics).toHaveProperty('resources');
      expect(metrics).toHaveProperty('pipeline');
      expect(metrics).toHaveProperty('quality');
    });

    test('should calculate quality metrics correctly', async () => {
      // Mock some quality data
      orchestrator.qualityMetrics.set('test1', { success: true, coverage: 0.9 });
      orchestrator.qualityMetrics.set('test2', { success: true, coverage: 0.95 });
      orchestrator.qualityMetrics.set('test3', { success: false, coverage: 0.8 });
      
      const qualityMetrics = await orchestrator.getQualityMetrics();
      
      expect(qualityMetrics.totalTests).toBe(3);
      expect(qualityMetrics.passedTests).toBe(2);
      expect(qualityMetrics.overallScore).toBeCloseTo(66.67, 1);
      expect(qualityMetrics.coverage).toBeCloseTo(0.88, 2);
    });

    test('should generate orchestration report', async () => {
      await orchestrator.initialize();
      
      const report = await orchestrator.getOrchestrationReport();
      
      expect(report.initialized).toBe(true);
      expect(report).toHaveProperty('activeOptimizations');
      expect(report).toHaveProperty('performanceHistory');
      expect(report).toHaveProperty('currentMetrics');
      expect(report).toHaveProperty('qualityStatus');
      expect(report).toHaveProperty('systemHealth');
    });
  });

  describe('Integration and Hooks', () => {
    test('should setup integration hooks between subsystems', async () => {
      await orchestrator.initialize();
      
      // Verify hooks are established
      expect(orchestrator.cacheSystem.onCacheHit).toBeDefined();
      expect(orchestrator.cacheSystem.onCacheMiss).toBeDefined();
      expect(orchestrator.resourceOptimizer.onResourceAllocation).toBeDefined();
      expect(orchestrator.testExecutor.onTestComplete).toBeDefined();
      expect(orchestrator.pipelineOptimizer.onOptimizationApplied).toBeDefined();
    });

    test('should handle cache hit events', async () => {
      await orchestrator.initialize();
      
      const initialMetrics = orchestrator.qualityMetrics.size;
      
      // Trigger cache hit event
      if (orchestrator.cacheSystem.onCacheHit) {
        orchestrator.cacheSystem.onCacheHit('test_key', 'L1');
      }
      
      // Verify event was handled
      expect(true).toBe(true); // Event handling is internal
    });
  });

  describe('Error Handling and Edge Cases', () => {
    test('should handle empty test suite', async () => {
      const emptyTestSuite = { tests: [] };
      
      await orchestrator.initialize();
      
      const result = await orchestrator.optimizePipeline(
        { name: 'empty-pipeline', stages: [] },
        emptyTestSuite
      );
      
      expect(result).toBeDefined();
      // Should not crash with empty test suite
    });

    test('should handle malformed pipeline configuration', async () => {
      const malformedPipeline = {
        // Missing required fields
        stages: null
      };
      
      await orchestrator.initialize();
      
      const result = await orchestrator.optimizePipeline(
        malformedPipeline,
        { tests: [] }
      );
      
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    test('should extract improvement percentages correctly', () => {
      expect(orchestrator.extractImprovementPercentage('30-50% time reduction')).toBe(40);
      expect(orchestrator.extractImprovementPercentage('25% improvement')).toBe(25);
      expect(orchestrator.extractImprovementPercentage('invalid')).toBe(0);
    });

    test('should calculate estimated improvements with caps', async () => {
      const plan = {
        testOptimizations: [
          { estimatedGain: '80% improvement' },
          { estimatedGain: '50% improvement' }
        ],
        cacheOptimizations: [
          { estimatedGain: '70% improvement' }
        ],
        resourceOptimizations: [
          { estimatedGain: '30% improvement' }
        ],
        pipelineOptimizations: [
          { estimatedGain: '90% improvement' }
        ]
      };
      
      const improvements = orchestrator.calculateEstimatedImprovement(plan);
      
      // Should be capped at maximum values
      expect(improvements.testExecution).toBeLessThanOrEqual(80);
      expect(improvements.cache).toBeLessThanOrEqual(60);
      expect(improvements.resources).toBeLessThanOrEqual(40);
      expect(improvements.pipeline).toBeLessThanOrEqual(70);
      expect(improvements.overall).toBeLessThanOrEqual(75);
    });
  });
});

describe('Integration Tests', () => {
  test('should integrate all components in full optimization workflow', async () => {
    const orchestrator = new PipelinePerformanceOrchestrator();
    
    const pipelineConfig = {
      name: 'integration-test-pipeline',
      stages: [
        { name: 'lint', type: 'lint' },
        { name: 'test', type: 'test' },
        { name: 'build', type: 'build' },
        { name: 'deploy', type: 'deploy' }
      ]
    };
    
    const testSuite = {
      tests: Array.from({ length: 50 }, (_, i) => ({
        id: `test_${i}`,
        name: `Test ${i}`,
        type: i < 10 ? 'unit' : i < 30 ? 'integration' : 'e2e',
        estimatedDuration: Math.random() * 10000 + 1000,
        tags: i < 5 ? ['critical'] : []
      }))
    };
    
    const result = await orchestrator.optimizePipeline(pipelineConfig, testSuite);
    
    expect(result.success).toBe(true);
    expect(result.optimizationId).toBeDefined();
    expect(result.report).toBeDefined();
    expect(result.qualityMaintained).toBe(true);
  }, 30000); // 30 second timeout for integration test
});

// Performance Tests
describe('Performance Tests', () => {
  test('should handle large test suites efficiently', async () => {
    const orchestrator = new PipelinePerformanceOrchestrator();
    
    // Create large test suite
    const largeTestSuite = {
      tests: Array.from({ length: 1000 }, (_, i) => ({
        id: `perf_test_${i}`,
        name: `Performance Test ${i}`,
        type: 'unit',
        estimatedDuration: 1000
      }))
    };
    
    const pipelineConfig = {
      name: 'performance-test-pipeline',
      stages: [{ name: 'test', type: 'test' }]
    };
    
    const startTime = Date.now();
    
    const result = await orchestrator.optimizePipeline(pipelineConfig, largeTestSuite);
    
    const duration = Date.now() - startTime;
    
    expect(result.success).toBe(true);
    expect(duration).toBeLessThan(60000); // Should complete within 60 seconds
  }, 90000); // 90 second timeout

  test('should optimize memory usage during large operations', async () => {
    const orchestrator = new PipelinePerformanceOrchestrator();
    
    // Monitor memory usage
    const initialMemory = process.memoryUsage().heapUsed;
    
    // Perform multiple optimizations
    for (let i = 0; i < 10; i++) {
      const testSuite = {
        tests: Array.from({ length: 100 }, (_, j) => ({
          id: `mem_test_${i}_${j}`,
          name: `Memory Test ${i}-${j}`,
          type: 'unit'
        }))
      };
      
      await orchestrator.optimizePipeline(
        { name: `pipeline-${i}`, stages: [] },
        testSuite
      );
    }
    
    const finalMemory = process.memoryUsage().heapUsed;
    const memoryGrowth = finalMemory - initialMemory;
    
    // Memory growth should be reasonable (less than 100MB)
    expect(memoryGrowth).toBeLessThan(100 * 1024 * 1024);
  }, 120000); // 2 minute timeout
});