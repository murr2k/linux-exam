#!/usr/bin/env node

/**
 * Matrix Configuration Generator
 * Generates dynamic GitHub Actions matrix configurations based on strategy and changes
 */

const fs = require('fs').promises;
const path = require('path');

class MatrixGenerator {
  constructor(options = {}) {
    this.strategy = options.strategy || 'standard';
    this.ref = options.ref || 'refs/heads/main';
    this.event = options.event || 'push';
    this.changedFiles = options.changedFiles || [];
    
    this.baseMatrix = this.getBaseMatrix();
  }

  async generate() {
    console.log(`📐 Generating matrix for strategy: ${this.strategy}`);
    
    let matrix = [];
    
    switch (this.strategy) {
      case 'full':
        matrix = this.generateFullMatrix();
        break;
        
      case 'comprehensive':
        matrix = this.generateComprehensiveMatrix();
        break;
        
      case 'selective':
        matrix = await this.generateSelectiveMatrix();
        break;
        
      case 'standard':
      default:
        matrix = this.generateStandardMatrix();
        break;
    }
    
    // Add common properties to all matrix entries
    matrix = matrix.map(entry => ({
      ...entry,
      node_version: '18',
      cache_key: this.generateCacheKey(entry),
      timeout: this.calculateTimeout(entry)
    }));
    
    console.log(`📊 Generated matrix with ${matrix.length} configurations`);
    
    // Output for GitHub Actions
    console.log(`::set-output name=config::${JSON.stringify(matrix)}`);
    
    return matrix;
  }

  getBaseMatrix() {
    return {
      suites: [
        { name: 'unit', pattern: '**/*.test.js', parallel: true, coverage: true },
        { name: 'integration', pattern: '**/integration/**/*.test.js', parallel: true, coverage: false },
        { name: 'e2e', pattern: '**/e2e/**/*.test.js', parallel: false, coverage: false }
      ],
      
      areas: [
        { name: 'frontend', path: 'src/frontend', dependencies: ['ui', 'components'] },
        { name: 'backend', path: 'src/backend', dependencies: ['api', 'services'] },
        { name: 'shared', path: 'src/shared', dependencies: ['utils', 'types'] },
        { name: 'config', path: 'config', dependencies: ['environment'] }
      ],
      
      environments: [
        { name: 'node-16', node: '16' },
        { name: 'node-18', node: '18' },
        { name: 'node-20', node: '20' }
      ],
      
      platforms: [
        { name: 'ubuntu', os: 'ubuntu-latest' },
        { name: 'windows', os: 'windows-latest' },
        { name: 'macos', os: 'macos-latest' }
      ]
    };
  }

  generateFullMatrix() {
    const matrix = [];
    
    // All suites x all environments x all platforms
    for (const suite of this.baseMatrix.suites) {
      for (const env of this.baseMatrix.environments) {
        for (const platform of this.baseMatrix.platforms) {
          matrix.push({
            suite: suite.name,
            area: 'all',
            node_version: env.node,
            os: platform.os,
            pattern: suite.pattern,
            parallel: suite.parallel,
            coverage: suite.coverage,
            priority: 'standard'
          });
        }
      }
    }
    
    return matrix;
  }

  generateComprehensiveMatrix() {
    const matrix = [];
    
    // Main combinations with high coverage
    for (const suite of this.baseMatrix.suites) {
      for (const area of this.baseMatrix.areas) {
        matrix.push({
          suite: suite.name,
          area: area.name,
          node_version: '18', // Primary version
          os: 'ubuntu-latest', // Primary OS
          pattern: suite.pattern,
          parallel: suite.parallel,
          coverage: suite.coverage,
          priority: 'high'
        });
      }
    }
    
    // Cross-platform testing for critical suites
    const criticalSuites = ['unit', 'integration'];
    for (const suiteName of criticalSuites) {
      const suite = this.baseMatrix.suites.find(s => s.name === suiteName);
      for (const platform of this.baseMatrix.platforms) {
        matrix.push({
          suite: suite.name,
          area: 'all',
          node_version: '18',
          os: platform.os,
          pattern: suite.pattern,
          parallel: suite.parallel,
          coverage: suiteName === 'unit', // Only unit tests for coverage
          priority: platform.name === 'ubuntu' ? 'high' : 'standard'
        });
      }
    }
    
    return matrix;
  }

  async generateSelectiveMatrix() {
    const matrix = [];
    const affectedAreas = await this.detectAffectedAreas();
    
    console.log(`🎯 Detected affected areas: ${affectedAreas.join(', ')}`);
    
    // Always run unit tests for affected areas
    for (const area of affectedAreas) {
      matrix.push({
        suite: 'unit',
        area: area,
        node_version: '18',
        os: 'ubuntu-latest',
        pattern: `**/${area}/**/*.test.js`,
        parallel: true,
        coverage: true,
        priority: 'high'
      });
    }
    
    // Run integration tests if backend or shared code changed
    if (affectedAreas.some(area => ['backend', 'shared', 'config'].includes(area))) {
      matrix.push({
        suite: 'integration',
        area: 'backend',
        node_version: '18',
        os: 'ubuntu-latest',
        pattern: '**/integration/**/*.test.js',
        parallel: true,
        coverage: false,
        priority: 'high'
      });
    }
    
    // Run e2e tests if frontend or critical backend changes
    if (affectedAreas.some(area => ['frontend', 'backend'].includes(area))) {
      matrix.push({
        suite: 'e2e',
        area: 'frontend',
        node_version: '18',
        os: 'ubuntu-latest',
        pattern: '**/e2e/**/*.test.js',
        parallel: false,
        coverage: false,
        priority: 'standard'
      });
    }
    
    // Fallback: if no specific areas affected, run basic suite
    if (matrix.length === 0) {
      matrix.push({
        suite: 'unit',
        area: 'all',
        node_version: '18',
        os: 'ubuntu-latest',
        pattern: '**/*.test.js',
        parallel: true,
        coverage: true,
        priority: 'high'
      });
    }
    
    return matrix;
  }

  generateStandardMatrix() {
    return [
      {
        suite: 'unit',
        area: 'all',
        node_version: '18',
        os: 'ubuntu-latest',
        pattern: '**/*.test.js',
        parallel: true,
        coverage: true,
        priority: 'high'
      },
      {
        suite: 'integration',
        area: 'all',
        node_version: '18',
        os: 'ubuntu-latest',
        pattern: '**/integration/**/*.test.js',
        parallel: true,
        coverage: false,
        priority: 'standard'
      }
    ];
  }

  async detectAffectedAreas() {
    const areas = new Set();
    
    try {
      // Get changed files from git
      const { execSync } = require('child_process');
      const gitOutput = execSync('git diff --name-only HEAD~1 HEAD', { encoding: 'utf8' });
      const changedFiles = gitOutput.trim().split('\n').filter(Boolean);
      
      console.log(`📁 Changed files: ${changedFiles.length}`);
      
      // Map files to areas
      for (const file of changedFiles) {
        const area = this.mapFileToArea(file);
        if (area) {
          areas.add(area);
        }
      }
      
      // If no specific areas detected, include all for safety
      if (areas.size === 0) {
        this.baseMatrix.areas.forEach(area => areas.add(area.name));
      }
      
    } catch (error) {
      console.warn('⚠️ Could not detect changes, including all areas');
      this.baseMatrix.areas.forEach(area => areas.add(area.name));
    }
    
    return Array.from(areas);
  }

  mapFileToArea(filePath) {
    // Frontend files
    if (filePath.startsWith('src/frontend/') || 
        filePath.includes('/components/') || 
        filePath.includes('/ui/') ||
        filePath.endsWith('.html') || 
        filePath.endsWith('.css') || 
        filePath.endsWith('.scss')) {
      return 'frontend';
    }
    
    // Backend files
    if (filePath.startsWith('src/backend/') || 
        filePath.startsWith('src/api/') || 
        filePath.startsWith('src/services/') ||
        filePath.includes('/controllers/') || 
        filePath.includes('/middleware/')) {
      return 'backend';
    }
    
    // Shared files
    if (filePath.startsWith('src/shared/') || 
        filePath.startsWith('src/utils/') || 
        filePath.startsWith('src/types/') ||
        filePath.startsWith('lib/')) {
      return 'shared';
    }
    
    // Configuration files
    if (filePath.startsWith('config/') || 
        filePath.includes('.env') || 
        filePath.includes('package.json') ||
        filePath.includes('yarn.lock') || 
        filePath.includes('tsconfig.json') ||
        filePath.includes('webpack.config.js')) {
      return 'config';
    }
    
    // Test files
    if (filePath.includes('.test.') || 
        filePath.includes('.spec.') || 
        filePath.startsWith('test/') ||
        filePath.startsWith('tests/')) {
      return 'test';
    }
    
    // Documentation
    if (filePath.endsWith('.md') || 
        filePath.startsWith('docs/')) {
      return 'docs';
    }
    
    return null;
  }

  generateCacheKey(entry) {
    const keyParts = [
      'test',
      entry.suite,
      entry.area,
      entry.node_version,
      entry.os.replace('-latest', ''),
      this.strategy
    ];
    
    return keyParts.join('-');
  }

  calculateTimeout(entry) {
    const timeouts = {
      unit: 30000,      // 30 seconds
      integration: 120000,  // 2 minutes
      e2e: 600000       // 10 minutes
    };
    
    let timeout = timeouts[entry.suite] || 60000;
    
    // Increase timeout for certain conditions
    if (entry.coverage) timeout *= 1.5;
    if (entry.area === 'all') timeout *= 1.2;
    if (entry.os.includes('windows')) timeout *= 1.3;
    
    return Math.round(timeout);
  }

  async saveMatrix(matrix) {
    const matrixPath = path.join(process.cwd(), 'test-results', 'matrix.json');
    await fs.mkdir(path.dirname(matrixPath), { recursive: true });
    await fs.writeFile(matrixPath, JSON.stringify(matrix, null, 2));
    
    console.log(`💾 Matrix saved to ${matrixPath}`);
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
    options[key] = value;
  }
  
  const generator = new MatrixGenerator(options);
  
  generator.generate()
    .then(async matrix => {
      await generator.saveMatrix(matrix);
      console.log('\n✅ Matrix generation completed');
    })
    .catch(error => {
      console.error('\n❌ Matrix generation failed:', error);
      process.exit(1);
    });
}

module.exports = { MatrixGenerator };