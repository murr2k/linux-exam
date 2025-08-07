#!/usr/bin/env node

/**
 * Pipeline Optimization CLI Tool
 * Command-line interface for running pipeline optimizations
 */

const fs = require('fs').promises;
const path = require('path');
const { PipelinePerformanceOrchestrator } = require('../src/pipeline-orchestrator');

class PipelineOptimizationCLI {
  constructor() {
    this.orchestrator = null;
    this.config = null;
  }

  async loadConfig(configPath) {
    try {
      const configContent = await fs.readFile(configPath, 'utf8');
      this.config = JSON.parse(configContent);
      console.log(`Configuration loaded from: ${configPath}`);
    } catch (error) {
      console.error(`Failed to load configuration: ${error.message}`);
      process.exit(1);
    }
  }

  async initializeOrchestrator() {
    console.log('Initializing pipeline orchestrator...');
    
    this.orchestrator = new PipelinePerformanceOrchestrator({
      qualityThreshold: this.config.pipelineOptimization?.qualityThreshold || 100,
      performanceTargets: this.config.pipelineOptimization?.performanceTargets || {},
      testExecution: this.config.parallelTestExecution || {},
      cache: this.config.cacheOptimization || {},
      resources: this.config.resourceOptimization || {},
      strategy: this.config.testExecutionStrategy || {},
      pipeline: this.config.pipelineStructureOptimization || {},
      metrics: this.config.performanceMetrics || {}
    });
    
    await this.orchestrator.initialize();
    console.log('Orchestrator initialized successfully');
  }

  async loadPipelineConfig(pipelinePath) {
    try {
      const pipelineContent = await fs.readFile(pipelinePath, 'utf8');
      
      // Support multiple formats
      if (pipelinePath.endsWith('.json')) {
        return JSON.parse(pipelineContent);
      } else if (pipelinePath.endsWith('.yml') || pipelinePath.endsWith('.yaml')) {
        const yaml = require('yaml');
        return yaml.parse(pipelineContent);
      } else {
        throw new Error('Unsupported pipeline configuration format');
      }
    } catch (error) {
      console.error(`Failed to load pipeline configuration: ${error.message}`);
      process.exit(1);
    }
  }

  async loadTestSuite(testSuitePath) {
    try {
      if (testSuitePath) {
        const testSuiteContent = await fs.readFile(testSuitePath, 'utf8');
        return JSON.parse(testSuiteContent);
      } else {
        // Auto-discover test files
        return await this.discoverTests();
      }
    } catch (error) {
      console.warn(`Failed to load test suite: ${error.message}`);
      return await this.discoverTests();
    }
  }

  async discoverTests() {
    console.log('Auto-discovering test files...');
    
    const testPatterns = [
      'test/**/*.test.js',
      'tests/**/*.test.js',
      'spec/**/*.spec.js',
      'src/**/*.test.js',
      '__tests__/**/*.js'
    ];
    
    const glob = require('glob');
    const tests = [];
    let testId = 1;
    
    for (const pattern of testPatterns) {
      try {
        const files = glob.sync(pattern, { cwd: process.cwd() });
        
        for (const file of files) {
          tests.push({
            id: `test_${testId++}`,
            name: path.basename(file, path.extname(file)),
            file: file,
            type: this.inferTestType(file),
            estimatedDuration: 5000, // Default 5 seconds
            tags: this.inferTestTags(file)
          });
        }
      } catch (error) {
        // Pattern not found, continue
      }
    }
    
    console.log(`Discovered ${tests.length} test files`);
    
    return { tests };
  }

  inferTestType(filePath) {
    if (filePath.includes('unit')) return 'unit';
    if (filePath.includes('integration')) return 'integration';
    if (filePath.includes('e2e') || filePath.includes('end-to-end')) return 'e2e';
    if (filePath.includes('performance') || filePath.includes('perf')) return 'performance';
    return 'unit'; // default
  }

  inferTestTags(filePath) {
    const tags = [];
    
    if (filePath.includes('critical') || filePath.includes('core')) {
      tags.push('critical');
    }
    if (filePath.includes('smoke')) {
      tags.push('smoke');
    }
    if (filePath.includes('security')) {
      tags.push('security');
    }
    
    return tags;
  }

  async optimizePipeline(pipelineConfig, testSuite, options) {
    console.log('Starting pipeline optimization...');
    console.log(`Pipeline: ${pipelineConfig.name || 'Unknown'}`);
    console.log(`Test files: ${testSuite.tests.length}`);
    
    const startTime = Date.now();
    
    try {
      const result = await this.orchestrator.optimizePipeline(
        pipelineConfig,
        testSuite,
        options
      );
      
      const duration = Date.now() - startTime;
      
      if (result.success) {
        console.log('\n✅ Pipeline optimization completed successfully!');
        console.log(`Duration: ${duration}ms`);
        console.log(`Quality maintained: ${result.qualityMaintained ? '✅' : '❌'}`);
        
        this.printOptimizationSummary(result.report);
        
        if (options.output) {
          await this.saveResults(result, options.output);
        }
        
        if (options.apply) {
          await this.applyOptimizations(result, options);
        }
        
        return result;
      } else {
        console.error('\n❌ Pipeline optimization failed');
        console.error(`Error: ${result.error}`);
        console.error(`Duration: ${duration}ms`);
        process.exit(1);
      }
    } catch (error) {
      console.error('\n❌ Pipeline optimization crashed');
      console.error(`Error: ${error.message}`);
      console.error(`Stack: ${error.stack}`);
      process.exit(1);
    }
  }

  printOptimizationSummary(report) {
    console.log('\n📊 Optimization Summary:');
    console.log(`  Total optimizations applied: ${report.summary.totalOptimizations}`);
    console.log(`  Estimated time savings: ${report.summary.estimatedTimeSavings}%`);
    console.log(`  Resource efficiency gain: ${report.summary.resourceEfficiencyGain}%`);
    console.log(`  Quality score: ${report.qualityAssurance.qualityScore}%`);
    
    console.log('\n🚀 Performance Gains:');
    const gains = report.performanceGains;
    
    if (gains.testExecution.speedImprovement > 0) {
      console.log(`  Test execution: ${gains.testExecution.speedImprovement}% faster`);
    }
    
    if (gains.caching.hitRateImprovement > 0) {
      console.log(`  Cache hit rate: +${gains.caching.hitRateImprovement}%`);
    }
    
    if (gains.resources.utilizationImprovement > 0) {
      console.log(`  Resource utilization: +${gains.resources.utilizationImprovement}%`);
    }
    
    if (gains.pipeline.durationReduction > 0) {
      console.log(`  Pipeline duration: -${gains.pipeline.durationReduction}%`);
    }
    
    if (report.recommendations.length > 0) {
      console.log('\n💡 Recommendations:');
      report.recommendations.slice(0, 3).forEach(rec => {
        console.log(`  • ${rec}`);
      });
    }
    
    if (report.risks.length > 0) {
      console.log('\n⚠️  Risks identified:');
      report.risks.forEach(risk => {
        console.log(`  • ${risk.issue} (${risk.severity})`);
      });
    }
    
    console.log('\n📋 Next Steps:');
    report.nextSteps.slice(0, 3).forEach(step => {
      console.log(`  • ${step}`);
    });
  }

  async saveResults(result, outputPath) {
    console.log(`\n💾 Saving results to: ${outputPath}`);
    
    try {
      const outputData = {
        timestamp: Date.now(),
        optimizationId: result.optimizationId,
        success: result.success,
        report: result.report,
        optimizedPipeline: result.optimizedPipeline,
        performanceGains: result.performanceGains
      };
      
      await fs.writeFile(
        outputPath,
        JSON.stringify(outputData, null, 2),
        'utf8'
      );
      
      console.log('Results saved successfully');
    } catch (error) {
      console.error(`Failed to save results: ${error.message}`);
    }
  }

  async applyOptimizations(result, options) {
    if (!result.optimizedPipeline) {
      console.log('No optimized pipeline to apply');
      return;
    }
    
    console.log('\n🔧 Applying optimizations to pipeline...');
    
    if (options.dryRun) {
      console.log('DRY RUN: Optimizations would be applied to:');
      console.log(`  Pipeline file: ${options.pipeline}`);
      console.log('  Changes:');
      // Show what would change
      this.showPipelineChanges(result.optimizedPipeline);
    } else {
      // Actually apply the optimizations
      if (options.backup !== false) {
        await this.backupOriginalPipeline(options.pipeline);
      }
      
      await this.writePipelineConfig(result.optimizedPipeline, options.pipeline);
      console.log('Optimizations applied successfully!');
    }
  }

  async backupOriginalPipeline(pipelinePath) {
    const backupPath = `${pipelinePath}.backup.${Date.now()}`;
    
    try {
      await fs.copyFile(pipelinePath, backupPath);
      console.log(`Original pipeline backed up to: ${backupPath}`);
    } catch (error) {
      console.warn(`Failed to backup original pipeline: ${error.message}`);
    }
  }

  async writePipelineConfig(pipelineConfig, pipelinePath) {
    try {
      if (pipelinePath.endsWith('.json')) {
        await fs.writeFile(
          pipelinePath,
          JSON.stringify(pipelineConfig, null, 2),
          'utf8'
        );
      } else if (pipelinePath.endsWith('.yml') || pipelinePath.endsWith('.yaml')) {
        const yaml = require('yaml');
        await fs.writeFile(
          pipelinePath,
          yaml.stringify(pipelineConfig),
          'utf8'
        );
      }
    } catch (error) {
      throw new Error(`Failed to write pipeline configuration: ${error.message}`);
    }
  }

  showPipelineChanges(optimizedPipeline) {
    console.log(`  • Pipeline name: ${optimizedPipeline.name}`);
    console.log(`  • Stages: ${optimizedPipeline.stages?.length || 0}`);
    
    if (optimizedPipeline.optimization) {
      console.log(`  • Applied optimizations: ${optimizedPipeline.optimization.appliedOptimizations}`);
      console.log(`  • Estimated improvement: ${optimizedPipeline.optimization.estimatedImprovement}%`);
    }
  }

  printUsage() {
    console.log(`
Pipeline Performance Optimizer CLI

Usage: node optimize-pipeline.js [options]

Options:
  --config, -c          Configuration file path (default: config/pipeline-config.json)
  --pipeline, -p        Pipeline configuration file (required)
  --tests, -t           Test suite configuration file (optional, auto-discover if not provided)
  --output, -o          Output file for results (optional)
  --apply               Apply optimizations to pipeline file
  --dry-run             Show what would be changed without applying
  --no-backup           Don't create backup when applying changes
  --verbose, -v         Verbose output
  --help, -h            Show this help message

Examples:
  # Basic optimization
  node optimize-pipeline.js -p ./pipeline.yml

  # With custom config and test suite
  node optimize-pipeline.js -c ./custom-config.json -p ./pipeline.yml -t ./tests.json

  # Apply optimizations directly
  node optimize-pipeline.js -p ./pipeline.yml --apply

  # Dry run to see changes
  node optimize-pipeline.js -p ./pipeline.yml --dry-run

  # Save detailed results
  node optimize-pipeline.js -p ./pipeline.yml -o ./optimization-results.json
`);
  }

  async run() {
    const args = process.argv.slice(2);
    const options = this.parseArgs(args);
    
    if (options.help) {
      this.printUsage();
      return;
    }
    
    if (!options.pipeline) {
      console.error('Pipeline configuration file is required');
      this.printUsage();
      process.exit(1);
    }
    
    try {
      // Load configuration
      const configPath = options.config || path.join(__dirname, '../config/pipeline-config.json');
      await this.loadConfig(configPath);
      
      // Initialize orchestrator
      await this.initializeOrchestrator();
      
      // Load pipeline and test configurations
      const pipelineConfig = await this.loadPipelineConfig(options.pipeline);
      const testSuite = await this.loadTestSuite(options.tests);
      
      // Run optimization
      const result = await this.optimizePipeline(pipelineConfig, testSuite, options);
      
      console.log('\n🎉 Pipeline optimization completed successfully!');
      
    } catch (error) {
      console.error(`\n❌ Failed to optimize pipeline: ${error.message}`);
      if (options.verbose) {
        console.error(error.stack);
      }
      process.exit(1);
    }
  }

  parseArgs(args) {
    const options = {};
    
    for (let i = 0; i < args.length; i++) {
      const arg = args[i];
      
      switch (arg) {
        case '--config':
        case '-c':
          options.config = args[++i];
          break;
        case '--pipeline':
        case '-p':
          options.pipeline = args[++i];
          break;
        case '--tests':
        case '-t':
          options.tests = args[++i];
          break;
        case '--output':
        case '-o':
          options.output = args[++i];
          break;
        case '--apply':
          options.apply = true;
          break;
        case '--dry-run':
          options.dryRun = true;
          break;
        case '--no-backup':
          options.backup = false;
          break;
        case '--verbose':
        case '-v':
          options.verbose = true;
          break;
        case '--help':
        case '-h':
          options.help = true;
          break;
        default:
          console.warn(`Unknown option: ${arg}`);
      }
    }
    
    return options;
  }
}

// Run CLI if this file is executed directly
if (require.main === module) {
  const cli = new PipelineOptimizationCLI();
  cli.run().catch(error => {
    console.error('CLI crashed:', error);
    process.exit(1);
  });
}

module.exports = { PipelineOptimizationCLI };