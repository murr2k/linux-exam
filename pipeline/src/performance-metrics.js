/**
 * Performance Metrics and Monitoring System
 * Comprehensive metrics collection, analysis, and reporting
 */

const os = require('os');
const fs = require('fs').promises;
const path = require('path');
const { performance } = require('perf_hooks');

class PerformanceMetricsSystem {
  constructor(options = {}) {
    this.metricsCollector = new MetricsCollector();
    this.performanceAnalyzer = new PerformanceAnalyzer();
    this.alertManager = new AlertManager();
    this.reportGenerator = new ReportGenerator();
    this.dashboardManager = new DashboardManager();
    this.trendAnalyzer = new TrendAnalyzer();
    
    this.metricsBuffer = [];
    this.alertRules = new Map();
    this.performanceBaselines = new Map();
    this.historicalData = [];
    
    // Configuration
    this.collectionInterval = options.collectionInterval || 5000; // 5 seconds
    this.retentionPeriod = options.retentionPeriod || 7 * 24 * 60 * 60 * 1000; // 7 days
    this.alertingEnabled = options.alerting !== false;
    this.realTimeMonitoring = options.realTime === true;
  }

  async initialize() {
    console.log('Initializing performance metrics system');
    
    // Initialize components
    await this.metricsCollector.initialize();
    await this.performanceAnalyzer.initialize();
    await this.alertManager.initialize();
    
    // Load historical data
    await this.loadHistoricalData();
    
    // Setup performance baselines
    await this.establishPerformanceBaselines();
    
    // Start monitoring
    this.startMetricsCollection();
    
    if (this.realTimeMonitoring) {
      this.startRealTimeMonitoring();
    }
    
    console.log('Performance metrics system initialized');
  }

  startMetricsCollection() {
    setInterval(async () => {
      try {
        const metrics = await this.collectCurrentMetrics();
        this.processMetrics(metrics);
      } catch (error) {
        console.error('Metrics collection error:', error);
      }
    }, this.collectionInterval);
  }

  async collectCurrentMetrics() {
    const timestamp = Date.now();
    
    const metrics = {
      timestamp: timestamp,
      system: await this.metricsCollector.collectSystemMetrics(),
      pipeline: await this.metricsCollector.collectPipelineMetrics(),
      tests: await this.metricsCollector.collectTestMetrics(),
      cache: await this.metricsCollector.collectCacheMetrics(),
      resources: await this.metricsCollector.collectResourceMetrics(),
      performance: await this.metricsCollector.collectPerformanceMetrics()
    };
    
    return metrics;
  }

  async processMetrics(metrics) {
    // Add to buffer
    this.metricsBuffer.push(metrics);
    
    // Keep buffer size manageable
    if (this.metricsBuffer.length > 1000) {
      this.metricsBuffer.shift();
    }
    
    // Add to historical data
    this.historicalData.push(metrics);
    
    // Cleanup old historical data
    const cutoffTime = Date.now() - this.retentionPeriod;
    this.historicalData = this.historicalData.filter(m => m.timestamp > cutoffTime);
    
    // Analyze performance
    const analysis = await this.performanceAnalyzer.analyzeMetrics(metrics);
    
    // Check for alerts
    if (this.alertingEnabled) {
      await this.checkAlerts(metrics, analysis);
    }
    
    // Update trends
    await this.trendAnalyzer.updateTrends(metrics);
  }

  async checkAlerts(metrics, analysis) {
    for (const [ruleName, rule] of this.alertRules) {
      const alertTriggered = await this.evaluateAlertRule(rule, metrics, analysis);
      
      if (alertTriggered) {
        await this.alertManager.triggerAlert(ruleName, {
          metrics: metrics,
          analysis: analysis,
          rule: rule,
          severity: rule.severity,
          message: rule.message
        });
      }
    }
  }

  async evaluateAlertRule(rule, metrics, analysis) {
    try {
      switch (rule.type) {
        case 'threshold':
          return this.evaluateThresholdRule(rule, metrics);
        case 'trend':
          return this.evaluateTrendRule(rule, analysis);
        case 'anomaly':
          return this.evaluateAnomalyRule(rule, metrics, analysis);
        case 'composite':
          return this.evaluateCompositeRule(rule, metrics, analysis);
        default:
          console.warn(`Unknown alert rule type: ${rule.type}`);
          return false;
      }
    } catch (error) {
      console.error(`Error evaluating alert rule ${rule.name}:`, error);
      return false;
    }
  }

  evaluateThresholdRule(rule, metrics) {
    const value = this.extractMetricValue(metrics, rule.metric);
    
    switch (rule.operator) {
      case 'gt': return value > rule.threshold;
      case 'lt': return value < rule.threshold;
      case 'gte': return value >= rule.threshold;
      case 'lte': return value <= rule.threshold;
      case 'eq': return value === rule.threshold;
      default: return false;
    }
  }

  evaluateTrendRule(rule, analysis) {
    const trendData = analysis.trends?.[rule.metric];
    if (!trendData) return false;
    
    switch (rule.condition) {
      case 'increasing':
        return trendData.direction === 'up' && trendData.strength > rule.minStrength;
      case 'decreasing':
        return trendData.direction === 'down' && trendData.strength > rule.minStrength;
      case 'volatile':
        return trendData.volatility > rule.threshold;
      default:
        return false;
    }
  }

  evaluateAnomalyRule(rule, metrics, analysis) {
    const anomalies = analysis.anomalies?.[rule.metric];
    return anomalies && anomalies.length > 0;
  }

  extractMetricValue(metrics, metricPath) {
    const pathParts = metricPath.split('.');
    let value = metrics;
    
    for (const part of pathParts) {
      value = value?.[part];
      if (value === undefined) break;
    }
    
    return value;
  }

  async generatePerformanceReport(options = {}) {
    const reportType = options.type || 'comprehensive';
    const timeRange = options.timeRange || '24h';
    const format = options.format || 'json';
    
    const reportData = await this.reportGenerator.generate({
      type: reportType,
      timeRange: timeRange,
      historicalData: this.getHistoricalData(timeRange),
      currentMetrics: this.getCurrentMetrics(),
      trends: await this.trendAnalyzer.getTrends(),
      baselines: this.performanceBaselines,
      alerts: await this.alertManager.getRecentAlerts()
    });
    
    if (format === 'html') {
      return await this.reportGenerator.formatAsHTML(reportData);
    } else if (format === 'pdf') {
      return await this.reportGenerator.formatAsPDF(reportData);
    }
    
    return reportData;
  }

  async getDashboard() {
    return await this.dashboardManager.generateDashboard({
      realTimeMetrics: this.getCurrentMetrics(),
      trends: await this.trendAnalyzer.getTrends(),
      alerts: await this.alertManager.getActiveAlerts(),
      performance: await this.performanceAnalyzer.getCurrentPerformance(),
      resources: await this.getResourceUtilization(),
      pipeline: await this.getPipelineMetrics()
    });
  }

  async establishPerformanceBaselines() {
    console.log('Establishing performance baselines');
    
    // If we have historical data, use it to create baselines
    if (this.historicalData.length > 100) {
      const baselineData = this.historicalData.slice(-100); // Last 100 data points
      
      // Calculate baselines for key metrics
      this.performanceBaselines.set('cpu_usage', this.calculateBaseline(
        baselineData.map(d => d.system?.cpu?.percent || 0)
      ));
      
      this.performanceBaselines.set('memory_usage', this.calculateBaseline(
        baselineData.map(d => d.system?.memory?.percent || 0)
      ));
      
      this.performanceBaselines.set('test_duration', this.calculateBaseline(
        baselineData.map(d => d.tests?.averageDuration || 0)
      ));
      
      this.performanceBaselines.set('pipeline_duration', this.calculateBaseline(
        baselineData.map(d => d.pipeline?.totalDuration || 0)
      ));
    } else {
      // Set default baselines
      this.performanceBaselines.set('cpu_usage', { mean: 30, std: 15, p95: 60 });
      this.performanceBaselines.set('memory_usage', { mean: 40, std: 20, p95: 75 });
      this.performanceBaselines.set('test_duration', { mean: 120000, std: 30000, p95: 180000 });
      this.performanceBaselines.set('pipeline_duration', { mean: 300000, std: 60000, p95: 450000 });
    }
    
    console.log('Performance baselines established');
  }

  calculateBaseline(values) {
    if (values.length === 0) return { mean: 0, std: 0, p95: 0 };
    
    const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
    const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
    const std = Math.sqrt(variance);
    
    const sorted = values.sort((a, b) => a - b);
    const p95Index = Math.floor(values.length * 0.95);
    const p95 = sorted[p95Index];
    
    return { mean, std, p95 };
  }

  setupDefaultAlertRules() {
    // High CPU usage
    this.alertRules.set('high_cpu', {
      name: 'High CPU Usage',
      type: 'threshold',
      metric: 'system.cpu.percent',
      operator: 'gt',
      threshold: 85,
      severity: 'warning',
      message: 'CPU usage is above 85%'
    });
    
    // High memory usage
    this.alertRules.set('high_memory', {
      name: 'High Memory Usage',
      type: 'threshold',
      metric: 'system.memory.percent',
      operator: 'gt',
      threshold: 90,
      severity: 'critical',
      message: 'Memory usage is above 90%'
    });
    
    // Test failure rate
    this.alertRules.set('high_test_failure_rate', {
      name: 'High Test Failure Rate',
      type: 'threshold',
      metric: 'tests.failureRate',
      operator: 'gt',
      threshold: 10,
      severity: 'warning',
      message: 'Test failure rate is above 10%'
    });
    
    // Pipeline duration anomaly
    this.alertRules.set('pipeline_duration_anomaly', {
      name: 'Pipeline Duration Anomaly',
      type: 'anomaly',
      metric: 'pipeline.totalDuration',
      severity: 'warning',
      message: 'Pipeline duration is significantly different from baseline'
    });
    
    // Cache hit rate degradation
    this.alertRules.set('low_cache_hit_rate', {
      name: 'Low Cache Hit Rate',
      type: 'threshold',
      metric: 'cache.hitRate',
      operator: 'lt',
      threshold: 60,
      severity: 'warning',
      message: 'Cache hit rate is below 60%'
    });
  }

  getCurrentMetrics() {
    return this.metricsBuffer.length > 0 ? this.metricsBuffer[this.metricsBuffer.length - 1] : null;
  }

  getHistoricalData(timeRange) {
    const now = Date.now();
    let cutoffTime;
    
    switch (timeRange) {
      case '1h': cutoffTime = now - 60 * 60 * 1000; break;
      case '6h': cutoffTime = now - 6 * 60 * 60 * 1000; break;
      case '24h': cutoffTime = now - 24 * 60 * 60 * 1000; break;
      case '7d': cutoffTime = now - 7 * 24 * 60 * 60 * 1000; break;
      default: cutoffTime = now - 24 * 60 * 60 * 1000;
    }
    
    return this.historicalData.filter(data => data.timestamp > cutoffTime);
  }

  async getResourceUtilization() {
    const current = this.getCurrentMetrics();
    if (!current) return null;
    
    return {
      cpu: current.system?.cpu?.percent || 0,
      memory: current.system?.memory?.percent || 0,
      disk: current.system?.disk?.percent || 0,
      network: current.system?.network?.utilization || 0
    };
  }

  async getPipelineMetrics() {
    const current = this.getCurrentMetrics();
    if (!current) return null;
    
    return current.pipeline || {};
  }

  startRealTimeMonitoring() {
    console.log('Starting real-time performance monitoring');
    
    setInterval(async () => {
      const metrics = this.getCurrentMetrics();
      if (metrics) {
        // Emit real-time updates (could integrate with WebSocket)
        this.emitRealTimeUpdate(metrics);
      }
    }, 1000); // 1 second updates
  }

  emitRealTimeUpdate(metrics) {
    // This would emit to connected clients via WebSocket
    // For now, just log critical metrics
    if (metrics.system?.cpu?.percent > 90 || metrics.system?.memory?.percent > 95) {
      console.log('REAL-TIME ALERT:', {
        cpu: metrics.system.cpu.percent,
        memory: metrics.system.memory.percent,
        timestamp: new Date().toISOString()
      });
    }
  }
}

class MetricsCollector {
  async initialize() {
    this.lastCollection = null;
    this.collectionStats = {
      total: 0,
      errors: 0,
      avgDuration: 0
    };
  }

  async collectSystemMetrics() {
    try {
      const startTime = performance.now();
      
      const metrics = {
        cpu: await this.collectCPUMetrics(),
        memory: await this.collectMemoryMetrics(),
        disk: await this.collectDiskMetrics(),
        network: await this.collectNetworkMetrics(),
        load: os.loadavg()
      };
      
      const collectionTime = performance.now() - startTime;
      this.updateCollectionStats(collectionTime);
      
      return metrics;
      
    } catch (error) {
      this.collectionStats.errors++;
      console.error('System metrics collection error:', error);
      return null;
    }
  }

  async collectCPUMetrics() {
    const cpus = os.cpus();
    
    // Simple CPU usage calculation
    let totalIdle = 0;
    let totalTick = 0;
    
    for (const cpu of cpus) {
      for (const type in cpu.times) {
        totalTick += cpu.times[type];
      }
      totalIdle += cpu.times.idle;
    }
    
    const idle = totalIdle / cpus.length;
    const total = totalTick / cpus.length;
    const percent = Math.round(100 - (100 * idle / total));
    
    return {
      percent: percent,
      cores: cpus.length,
      model: cpus[0]?.model || 'Unknown',
      speed: cpus[0]?.speed || 0
    };
  }

  async collectMemoryMetrics() {
    const totalMemory = os.totalmem();
    const freeMemory = os.freemem();
    const usedMemory = totalMemory - freeMemory;
    
    return {
      total: totalMemory,
      used: usedMemory,
      free: freeMemory,
      percent: Math.round((usedMemory / totalMemory) * 100)
    };
  }

  async collectDiskMetrics() {
    // This would typically use system commands to get disk usage
    // For now, return placeholder data
    return {
      total: 0,
      used: 0,
      free: 0,
      percent: 0
    };
  }

  async collectNetworkMetrics() {
    // This would typically collect network interface statistics
    // For now, return placeholder data
    return {
      bytesIn: 0,
      bytesOut: 0,
      packetsIn: 0,
      packetsOut: 0,
      utilization: 0
    };
  }

  async collectPipelineMetrics() {
    // This would integrate with the actual pipeline system
    // For now, return simulated metrics
    return {
      totalDuration: Math.random() * 600000 + 300000, // 5-15 minutes
      stagesCompleted: Math.floor(Math.random() * 10) + 5,
      stagesFailed: Math.floor(Math.random() * 2),
      avgStageTime: Math.random() * 60000 + 30000, // 0.5-1.5 minutes
      successRate: Math.random() * 0.2 + 0.8, // 80-100%
      parallelism: Math.random() * 3 + 1 // 1-4x
    };
  }

  async collectTestMetrics() {
    // This would integrate with the test execution system
    return {
      totalTests: Math.floor(Math.random() * 500) + 100,
      passedTests: Math.floor(Math.random() * 450) + 80,
      failedTests: Math.floor(Math.random() * 20),
      skippedTests: Math.floor(Math.random() * 30),
      averageDuration: Math.random() * 60000 + 30000,
      failureRate: Math.random() * 0.1, // 0-10%
      coverage: Math.random() * 0.2 + 0.8 // 80-100%
    };
  }

  async collectCacheMetrics() {
    // This would integrate with the cache system
    return {
      hitRate: Math.random() * 0.4 + 0.6, // 60-100%
      hits: Math.floor(Math.random() * 1000),
      misses: Math.floor(Math.random() * 300),
      size: Math.random() * 500 * 1024 * 1024, // 0-500MB
      evictions: Math.floor(Math.random() * 50)
    };
  }

  async collectResourceMetrics() {
    return {
      containers: Math.floor(Math.random() * 10) + 1,
      activeProcesses: Math.floor(Math.random() * 50) + 10,
      openFiles: Math.floor(Math.random() * 1000) + 100,
      networkConnections: Math.floor(Math.random() * 100) + 20
    };
  }

  async collectPerformanceMetrics() {
    return {
      responseTime: Math.random() * 1000 + 100, // 100-1100ms
      throughput: Math.random() * 100 + 50, // 50-150 requests/sec
      errorRate: Math.random() * 0.05, // 0-5%
      availability: Math.random() * 0.05 + 0.95 // 95-100%
    };
  }

  updateCollectionStats(duration) {
    this.collectionStats.total++;
    const prevAvg = this.collectionStats.avgDuration;
    this.collectionStats.avgDuration = 
      (prevAvg * (this.collectionStats.total - 1) + duration) / this.collectionStats.total;
  }
}

class PerformanceAnalyzer {
  async initialize() {
    this.analysisHistory = [];
  }

  async analyzeMetrics(metrics) {
    const analysis = {
      timestamp: metrics.timestamp,
      performance: await this.analyzePerformance(metrics),
      trends: await this.analyzeTrends(metrics),
      anomalies: await this.detectAnomalies(metrics),
      bottlenecks: await this.identifyBottlenecks(metrics),
      recommendations: await this.generateRecommendations(metrics)
    };
    
    this.analysisHistory.push(analysis);
    
    // Keep only recent analysis
    if (this.analysisHistory.length > 100) {
      this.analysisHistory.shift();
    }
    
    return analysis;
  }

  async analyzePerformance(metrics) {
    const performance = {
      overall: 'good',
      scores: {},
      improvements: []
    };
    
    // Calculate performance scores (0-100)
    performance.scores.cpu = this.calculateCPUScore(metrics.system?.cpu);
    performance.scores.memory = this.calculateMemoryScore(metrics.system?.memory);
    performance.scores.pipeline = this.calculatePipelineScore(metrics.pipeline);
    performance.scores.tests = this.calculateTestScore(metrics.tests);
    performance.scores.cache = this.calculateCacheScore(metrics.cache);
    
    // Calculate overall score
    const scores = Object.values(performance.scores).filter(s => s !== null);
    performance.scores.overall = scores.reduce((sum, score) => sum + score, 0) / scores.length;
    
    // Determine overall performance rating
    if (performance.scores.overall >= 90) {
      performance.overall = 'excellent';
    } else if (performance.scores.overall >= 75) {
      performance.overall = 'good';
    } else if (performance.scores.overall >= 60) {
      performance.overall = 'fair';
    } else {
      performance.overall = 'poor';
    }
    
    return performance;
  }

  calculateCPUScore(cpuMetrics) {
    if (!cpuMetrics) return null;
    
    const usage = cpuMetrics.percent;
    
    // Optimal range: 20-70%
    if (usage >= 20 && usage <= 70) {
      return 100;
    } else if (usage < 20) {
      return 80 - (20 - usage); // Underutilization penalty
    } else {
      return Math.max(0, 100 - (usage - 70) * 2); // Overutilization penalty
    }
  }

  calculateMemoryScore(memoryMetrics) {
    if (!memoryMetrics) return null;
    
    const usage = memoryMetrics.percent;
    
    // Good range: 30-80%
    if (usage >= 30 && usage <= 80) {
      return 100;
    } else if (usage < 30) {
      return 90; // Slight penalty for underutilization
    } else {
      return Math.max(0, 100 - (usage - 80) * 3); // High penalty for overutilization
    }
  }

  calculatePipelineScore(pipelineMetrics) {
    if (!pipelineMetrics) return null;
    
    let score = 100;
    
    // Penalize long durations
    if (pipelineMetrics.totalDuration > 600000) { // 10 minutes
      score -= (pipelineMetrics.totalDuration - 600000) / 60000 * 5; // -5 points per minute over
    }
    
    // Reward high success rate
    score = score * (pipelineMetrics.successRate || 1);
    
    return Math.max(0, Math.min(100, score));
  }

  calculateTestScore(testMetrics) {
    if (!testMetrics) return null;
    
    let score = 100;
    
    // Penalize high failure rate
    score = score * (1 - (testMetrics.failureRate || 0));
    
    // Penalize low coverage
    if (testMetrics.coverage && testMetrics.coverage < 0.8) {
      score *= testMetrics.coverage / 0.8;
    }
    
    return Math.max(0, Math.min(100, score));
  }

  calculateCacheScore(cacheMetrics) {
    if (!cacheMetrics) return null;
    
    const hitRate = cacheMetrics.hitRate || 0;
    
    // Cache hit rate scoring
    if (hitRate >= 0.9) return 100;
    if (hitRate >= 0.8) return 90;
    if (hitRate >= 0.7) return 80;
    if (hitRate >= 0.6) return 70;
    return hitRate * 100;
  }

  async detectAnomalies(metrics) {
    const anomalies = {};
    
    // Simple anomaly detection based on historical data
    if (this.analysisHistory.length >= 10) {
      const recentHistory = this.analysisHistory.slice(-10);
      
      // Check CPU anomalies
      if (metrics.system?.cpu) {
        const cpuAnomaly = this.detectCPUAnomaly(metrics.system.cpu, recentHistory);
        if (cpuAnomaly) anomalies.cpu = cpuAnomaly;
      }
      
      // Check memory anomalies
      if (metrics.system?.memory) {
        const memoryAnomaly = this.detectMemoryAnomaly(metrics.system.memory, recentHistory);
        if (memoryAnomaly) anomalies.memory = memoryAnomaly;
      }
      
      // Check pipeline anomalies
      if (metrics.pipeline) {
        const pipelineAnomaly = this.detectPipelineAnomaly(metrics.pipeline, recentHistory);
        if (pipelineAnomaly) anomalies.pipeline = pipelineAnomaly;
      }
    }
    
    return anomalies;
  }

  detectCPUAnomaly(currentCPU, history) {
    const historicalCPU = history.map(h => h.performance?.scores?.cpu).filter(s => s !== null);
    
    if (historicalCPU.length === 0) return null;
    
    const mean = historicalCPU.reduce((sum, val) => sum + val, 0) / historicalCPU.length;
    const stdDev = Math.sqrt(
      historicalCPU.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / historicalCPU.length
    );
    
    const currentScore = this.calculateCPUScore(currentCPU);
    const deviation = Math.abs(currentScore - mean);
    
    if (deviation > stdDev * 2) { // 2 standard deviations
      return {
        type: 'statistical',
        metric: 'cpu_score',
        current: currentScore,
        expected: mean,
        deviation: deviation,
        severity: deviation > stdDev * 3 ? 'high' : 'medium'
      };
    }
    
    return null;
  }

  async getCurrentPerformance() {
    if (this.analysisHistory.length === 0) return null;
    
    return this.analysisHistory[this.analysisHistory.length - 1].performance;
  }
}

class AlertManager {
  async initialize() {
    this.activeAlerts = new Map();
    this.alertHistory = [];
  }

  async triggerAlert(ruleName, alertData) {
    const alertId = `${ruleName}_${Date.now()}`;
    
    const alert = {
      id: alertId,
      rule: ruleName,
      severity: alertData.severity,
      message: alertData.message,
      timestamp: Date.now(),
      metrics: alertData.metrics,
      analysis: alertData.analysis,
      acknowledged: false,
      resolved: false
    };
    
    this.activeAlerts.set(alertId, alert);
    this.alertHistory.push(alert);
    
    // Keep alert history manageable
    if (this.alertHistory.length > 1000) {
      this.alertHistory.shift();
    }
    
    console.log(`ALERT TRIGGERED: ${alert.severity.toUpperCase()} - ${alert.message}`);
    
    // Here you would integrate with external alerting systems
    // (email, Slack, PagerDuty, etc.)
  }

  async getActiveAlerts() {
    return Array.from(this.activeAlerts.values())
      .filter(alert => !alert.resolved)
      .sort((a, b) => {
        const severityOrder = { 'critical': 3, 'warning': 2, 'info': 1 };
        return (severityOrder[b.severity] || 0) - (severityOrder[a.severity] || 0);
      });
  }

  async getRecentAlerts(hours = 24) {
    const cutoffTime = Date.now() - (hours * 60 * 60 * 1000);
    return this.alertHistory.filter(alert => alert.timestamp > cutoffTime);
  }
}

class ReportGenerator {
  async generate(options) {
    const report = {
      metadata: {
        generatedAt: Date.now(),
        type: options.type,
        timeRange: options.timeRange
      },
      summary: this.generateSummary(options),
      performance: this.analyzePerformance(options),
      trends: this.analyzeTrends(options),
      alerts: this.summarizeAlerts(options),
      recommendations: this.generateRecommendations(options)
    };
    
    return report;
  }

  generateSummary(options) {
    const data = options.historicalData || [];
    
    if (data.length === 0) {
      return { message: 'No data available for the specified time range' };
    }
    
    const latest = data[data.length - 1];
    
    return {
      dataPoints: data.length,
      timeRange: options.timeRange,
      currentPerformance: latest.performance?.overall || 'unknown',
      avgCPU: data.reduce((sum, d) => sum + (d.system?.cpu?.percent || 0), 0) / data.length,
      avgMemory: data.reduce((sum, d) => sum + (d.system?.memory?.percent || 0), 0) / data.length,
      totalAlerts: options.alerts?.length || 0
    };
  }

  async formatAsHTML(reportData) {
    // Generate HTML report
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Performance Report</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          .summary { background: #f0f0f0; padding: 15px; border-radius: 5px; }
          .metric { margin: 10px 0; }
          .alert { color: red; font-weight: bold; }
        </style>
      </head>
      <body>
        <h1>Performance Report</h1>
        <div class="summary">
          <h2>Summary</h2>
          <div class="metric">Time Range: ${reportData.metadata.timeRange}</div>
          <div class="metric">Data Points: ${reportData.summary.dataPoints}</div>
          <div class="metric">Current Performance: ${reportData.summary.currentPerformance}</div>
        </div>
        <!-- Add more sections as needed -->
      </body>
      </html>
    `;
  }
}

class DashboardManager {
  async generateDashboard(options) {
    return {
      timestamp: Date.now(),
      realTime: {
        cpu: options.realTimeMetrics?.system?.cpu?.percent || 0,
        memory: options.realTimeMetrics?.system?.memory?.percent || 0,
        tests: options.realTimeMetrics?.tests?.successRate || 1,
        cache: options.realTimeMetrics?.cache?.hitRate || 0
      },
      trends: options.trends || {},
      alerts: {
        active: options.alerts?.length || 0,
        critical: options.alerts?.filter(a => a.severity === 'critical').length || 0
      },
      performance: options.performance || { overall: 'unknown' }
    };
  }
}

class TrendAnalyzer {
  constructor() {
    this.trends = new Map();
  }

  async updateTrends(metrics) {
    // Update CPU trend
    this.updateMetricTrend('cpu', metrics.system?.cpu?.percent);
    
    // Update memory trend
    this.updateMetricTrend('memory', metrics.system?.memory?.percent);
    
    // Update test success rate trend
    this.updateMetricTrend('test_success', (1 - (metrics.tests?.failureRate || 0)) * 100);
    
    // Update cache hit rate trend
    this.updateMetricTrend('cache_hit', (metrics.cache?.hitRate || 0) * 100);
  }

  updateMetricTrend(metricName, value) {
    if (value === undefined || value === null) return;
    
    if (!this.trends.has(metricName)) {
      this.trends.set(metricName, []);
    }
    
    const trendData = this.trends.get(metricName);
    trendData.push({ timestamp: Date.now(), value: value });
    
    // Keep only last 100 points
    if (trendData.length > 100) {
      trendData.shift();
    }
  }

  async getTrends() {
    const trends = {};
    
    for (const [metricName, data] of this.trends) {
      if (data.length >= 2) {
        trends[metricName] = this.analyzeTrend(data);
      }
    }
    
    return trends;
  }

  analyzeTrend(data) {
    if (data.length < 2) return null;
    
    const recent = data.slice(-10); // Last 10 points
    const values = recent.map(d => d.value);
    
    // Simple linear regression
    const n = values.length;
    const x = Array.from({ length: n }, (_, i) => i);
    const sumX = x.reduce((sum, val) => sum + val, 0);
    const sumY = values.reduce((sum, val) => sum + val, 0);
    const sumXY = x.reduce((sum, val, i) => sum + val * values[i], 0);
    const sumX2 = x.reduce((sum, val) => sum + val * val, 0);
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    
    return {
      direction: slope > 0.1 ? 'up' : slope < -0.1 ? 'down' : 'stable',
      strength: Math.abs(slope),
      current: values[values.length - 1],
      change: values[values.length - 1] - values[0],
      volatility: this.calculateVolatility(values)
    };
  }

  calculateVolatility(values) {
    if (values.length < 2) return 0;
    
    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    
    return Math.sqrt(variance);
  }
}

module.exports = {
  PerformanceMetricsSystem,
  MetricsCollector,
  PerformanceAnalyzer,
  AlertManager,
  ReportGenerator,
  DashboardManager,
  TrendAnalyzer
};