#!/usr/bin/env node

/**
 * Pipeline Monitoring System
 * Tracks execution time, success rates, quality trends, and provides alerting
 */

const fs = require('fs').promises;
const path = require('path');
const { performance } = require('perf_hooks');
const EventEmitter = require('events');

class PipelineMonitor extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.config = {
      metricsRetentionDays: options.metricsRetentionDays || 30,
      alertThresholds: {
        executionTime: options.executionTimeThreshold || 1800000, // 30 minutes
        successRate: options.successRateThreshold || 95, // 95%
        qualityScore: options.qualityScoreThreshold || 90, // 90%
        performanceRegression: options.performanceRegressionThreshold || 10 // 10%
      },
      alertChannels: options.alertChannels || ['console', 'file'],
      monitoringInterval: options.monitoringInterval || 60000, // 1 minute
      ...options
    };
    
    this.metrics = {
      currentSession: null,
      historical: [],
      alerts: [],
      trends: new Map()
    };
    
    this.isMonitoring = false;
    this.monitoringTimer = null;
  }

  async initialize() {
    console.log('🔄 Initializing Pipeline Monitor...');
    
    try {
      await this.createDirectories();
      await this.loadHistoricalData();
      await this.startMonitoring();
      
      console.log('✅ Pipeline Monitor initialized successfully');
      this.emit('initialized');
      
    } catch (error) {
      console.error('❌ Failed to initialize Pipeline Monitor:', error);
      throw error;
    }
  }

  async startPipelineSession(sessionInfo) {
    console.log(`📊 Starting monitoring session: ${sessionInfo.sessionId}`);
    
    this.metrics.currentSession = {
      sessionId: sessionInfo.sessionId,
      startTime: performance.now(),
      endTime: null,
      branch: sessionInfo.branch,
      commit: sessionInfo.commit,
      triggeredBy: sessionInfo.triggeredBy,
      
      phases: new Map(),
      jobs: new Map(),
      
      metrics: {
        totalJobs: 0,
        completedJobs: 0,
        failedJobs: 0,
        skippedJobs: 0,
        retryCount: 0
      },
      
      qualityMetrics: {
        testCoverage: 0,
        qualityScore: 0,
        performanceScore: 0,
        securityScore: 0
      },
      
      alerts: [],
      events: []
    };
    
    this.emit('sessionStarted', this.metrics.currentSession);
    return this.metrics.currentSession.sessionId;
  }

  async trackPhase(phaseInfo) {
    if (!this.metrics.currentSession) {
      throw new Error('No active monitoring session');
    }
    
    console.log(`📈 Tracking phase: ${phaseInfo.name}`);
    
    const phase = {
      name: phaseInfo.name,
      startTime: performance.now(),
      endTime: null,
      status: 'running',
      jobs: [],
      metrics: {
        duration: 0,
        jobsCompleted: 0,
        jobsFailed: 0,
        averageJobDuration: 0
      },
      events: []
    };
    
    this.metrics.currentSession.phases.set(phaseInfo.name, phase);
    this.emit('phaseStarted', phase);
    
    return phase;
  }

  async trackJob(jobInfo) {
    if (!this.metrics.currentSession) {
      throw new Error('No active monitoring session');
    }
    
    console.log(`🔍 Tracking job: ${jobInfo.name}`);
    
    const job = {
      name: jobInfo.name,
      type: jobInfo.type,
      phase: jobInfo.phase,
      startTime: performance.now(),
      endTime: null,
      status: 'running',
      retryCount: 0,
      
      metrics: {
        duration: 0,
        cpuUsage: 0,
        memoryUsage: 0,
        diskUsage: 0
      },
      
      results: null,
      error: null,
      events: []
    };
    
    this.metrics.currentSession.jobs.set(jobInfo.name, job);
    this.metrics.currentSession.metrics.totalJobs++;
    
    // Add to phase if specified
    if (jobInfo.phase && this.metrics.currentSession.phases.has(jobInfo.phase)) {
      this.metrics.currentSession.phases.get(jobInfo.phase).jobs.push(jobInfo.name);
    }
    
    this.emit('jobStarted', job);
    return job;
  }

  async completeJob(jobName, results) {
    if (!this.metrics.currentSession || !this.metrics.currentSession.jobs.has(jobName)) {
      throw new Error(`Job ${jobName} not found in current session`);
    }
    
    const job = this.metrics.currentSession.jobs.get(jobName);
    job.endTime = performance.now();
    job.metrics.duration = job.endTime - job.startTime;
    job.status = results.success ? 'completed' : 'failed';
    job.results = results;
    job.error = results.error || null;
    
    // Update session metrics
    if (results.success) {
      this.metrics.currentSession.metrics.completedJobs++;
    } else {
      this.metrics.currentSession.metrics.failedJobs++;
    }
    
    // Update phase metrics
    if (job.phase && this.metrics.currentSession.phases.has(job.phase)) {
      const phase = this.metrics.currentSession.phases.get(job.phase);
      if (results.success) {
        phase.metrics.jobsCompleted++;
      } else {
        phase.metrics.jobsFailed++;
      }
    }
    
    console.log(`${results.success ? '✅' : '❌'} Job ${jobName} ${job.status} in ${Math.round(job.metrics.duration)}ms`);
    
    // Check for alerts
    await this.checkJobAlerts(job);
    
    this.emit('jobCompleted', job);
    return job;
  }

  async completePhase(phaseName) {
    if (!this.metrics.currentSession || !this.metrics.currentSession.phases.has(phaseName)) {
      throw new Error(`Phase ${phaseName} not found in current session`);
    }
    
    const phase = this.metrics.currentSession.phases.get(phaseName);
    phase.endTime = performance.now();
    phase.metrics.duration = phase.endTime - phase.startTime;
    phase.status = phase.metrics.jobsFailed > 0 ? 'failed' : 'completed';
    
    // Calculate average job duration
    if (phase.jobs.length > 0) {
      const jobDurations = phase.jobs.map(jobName => {
        const job = this.metrics.currentSession.jobs.get(jobName);
        return job ? job.metrics.duration : 0;
      });
      phase.metrics.averageJobDuration = jobDurations.reduce((sum, duration) => sum + duration, 0) / jobDurations.length;
    }
    
    console.log(`📊 Phase ${phaseName} ${phase.status} in ${Math.round(phase.metrics.duration)}ms`);
    
    // Check for phase-level alerts
    await this.checkPhaseAlerts(phase);
    
    this.emit('phaseCompleted', phase);
    return phase;
  }

  async endPipelineSession(finalResults) {
    if (!this.metrics.currentSession) {
      throw new Error('No active monitoring session');
    }
    
    console.log(`🏁 Ending monitoring session: ${this.metrics.currentSession.sessionId}`);
    
    this.metrics.currentSession.endTime = performance.now();
    this.metrics.currentSession.totalDuration = this.metrics.currentSession.endTime - this.metrics.currentSession.startTime;
    this.metrics.currentSession.success = finalResults.success;
    this.metrics.currentSession.finalResults = finalResults;
    
    // Update quality metrics
    if (finalResults.qualityMetrics) {
      this.metrics.currentSession.qualityMetrics = {
        ...this.metrics.currentSession.qualityMetrics,
        ...finalResults.qualityMetrics
      };
    }
    
    // Calculate success rate
    const totalJobs = this.metrics.currentSession.metrics.totalJobs;
    this.metrics.currentSession.successRate = totalJobs > 0 
      ? (this.metrics.currentSession.metrics.completedJobs / totalJobs) * 100 
      : 100;
    
    // Generate session report
    const sessionReport = await this.generateSessionReport();
    
    // Store in historical data
    this.metrics.historical.push({
      ...this.metrics.currentSession,
      report: sessionReport
    });
    
    // Check for session-level alerts
    await this.checkSessionAlerts();
    
    // Save to disk
    await this.saveSessionData();
    
    // Update trends
    await this.updateTrends();
    
    console.log(`📈 Session completed: ${this.metrics.currentSession.success ? 'SUCCESS' : 'FAILURE'} in ${Math.round(this.metrics.currentSession.totalDuration)}ms`);
    
    this.emit('sessionEnded', this.metrics.currentSession);
    
    const completedSession = this.metrics.currentSession;
    this.metrics.currentSession = null;
    
    return completedSession;
  }

  async checkJobAlerts(job) {
    const alerts = [];
    
    // Long-running job alert
    if (job.metrics.duration > this.config.alertThresholds.executionTime) {
      alerts.push({
        type: 'job_long_duration',
        severity: 'warning',
        message: `Job ${job.name} took ${Math.round(job.metrics.duration)}ms (threshold: ${this.config.alertThresholds.executionTime}ms)`,
        job: job.name,
        phase: job.phase,
        timestamp: Date.now()
      });
    }
    
    // Job failure alert
    if (!job.results?.success) {
      alerts.push({
        type: 'job_failure',
        severity: 'error',
        message: `Job ${job.name} failed: ${job.error}`,
        job: job.name,
        phase: job.phase,
        timestamp: Date.now()
      });
    }
    
    // High retry count alert
    if (job.retryCount > 2) {
      alerts.push({
        type: 'high_retry_count',
        severity: 'warning',
        message: `Job ${job.name} required ${job.retryCount} retries`,
        job: job.name,
        phase: job.phase,
        timestamp: Date.now()
      });
    }
    
    for (const alert of alerts) {
      await this.sendAlert(alert);
      this.metrics.currentSession.alerts.push(alert);
    }
  }

  async checkPhaseAlerts(phase) {
    const alerts = [];
    
    // Phase failure rate alert
    const totalJobs = phase.metrics.jobsCompleted + phase.metrics.jobsFailed;
    if (totalJobs > 0) {
      const failureRate = (phase.metrics.jobsFailed / totalJobs) * 100;
      if (failureRate > (100 - this.config.alertThresholds.successRate)) {
        alerts.push({
          type: 'phase_high_failure_rate',
          severity: 'error',
          message: `Phase ${phase.name} has ${failureRate.toFixed(1)}% failure rate (${phase.metrics.jobsFailed}/${totalJobs} jobs failed)`,
          phase: phase.name,
          timestamp: Date.now()
        });
      }
    }
    
    // Long-running phase alert
    if (phase.metrics.duration > this.config.alertThresholds.executionTime * 2) {
      alerts.push({
        type: 'phase_long_duration',
        severity: 'warning',
        message: `Phase ${phase.name} took ${Math.round(phase.metrics.duration)}ms`,
        phase: phase.name,
        timestamp: Date.now()
      });
    }
    
    for (const alert of alerts) {
      await this.sendAlert(alert);
      this.metrics.currentSession.alerts.push(alert);
    }
  }

  async checkSessionAlerts() {
    const alerts = [];
    const session = this.metrics.currentSession;
    
    // Overall success rate alert
    if (session.successRate < this.config.alertThresholds.successRate) {
      alerts.push({
        type: 'low_success_rate',
        severity: 'critical',
        message: `Pipeline success rate is ${session.successRate.toFixed(1)}% (threshold: ${this.config.alertThresholds.successRate}%)`,
        timestamp: Date.now()
      });
    }
    
    // Quality gate alerts
    if (session.qualityMetrics.qualityScore < this.config.alertThresholds.qualityScore) {
      alerts.push({
        type: 'quality_gate_failure',
        severity: 'error',
        message: `Quality score ${session.qualityMetrics.qualityScore}% below threshold ${this.config.alertThresholds.qualityScore}%`,
        timestamp: Date.now()
      });
    }
    
    // Performance regression alert
    const trend = this.getTrend('performance');
    if (trend && trend.regression > this.config.alertThresholds.performanceRegression) {
      alerts.push({
        type: 'performance_regression',
        severity: 'warning',
        message: `Performance regression detected: ${trend.regression.toFixed(1)}% slower than baseline`,
        timestamp: Date.now()
      });
    }
    
    // Long pipeline alert
    if (session.totalDuration > this.config.alertThresholds.executionTime * 3) {
      alerts.push({
        type: 'pipeline_long_duration',
        severity: 'warning',
        message: `Pipeline took ${Math.round(session.totalDuration)}ms (${(session.totalDuration / 60000).toFixed(1)} minutes)`,
        timestamp: Date.now()
      });
    }
    
    for (const alert of alerts) {
      await this.sendAlert(alert);
      session.alerts.push(alert);
    }
  }

  async sendAlert(alert) {
    console.log(`🚨 ALERT [${alert.severity.toUpperCase()}]: ${alert.message}`);
    
    for (const channel of this.config.alertChannels) {
      try {
        await this.sendAlertToChannel(alert, channel);
      } catch (error) {
        console.error(`Failed to send alert to ${channel}:`, error);
      }
    }
    
    this.emit('alert', alert);
  }

  async sendAlertToChannel(alert, channel) {
    switch (channel) {
      case 'console':
        // Already logged above
        break;
        
      case 'file':
        await this.writeAlertToFile(alert);
        break;
        
      case 'webhook':
        await this.sendAlertToWebhook(alert);
        break;
        
      case 'slack':
        await this.sendAlertToSlack(alert);
        break;
        
      default:
        console.warn(`Unknown alert channel: ${channel}`);
    }
  }

  async writeAlertToFile(alert) {
    const alertsDir = path.join(process.cwd(), 'monitoring', 'alerts');
    await fs.mkdir(alertsDir, { recursive: true });
    
    const alertFile = path.join(alertsDir, `alerts-${new Date().toISOString().split('T')[0]}.json`);
    
    let alerts = [];
    try {
      const existingData = await fs.readFile(alertFile, 'utf8');
      alerts = JSON.parse(existingData);
    } catch (error) {
      // File doesn't exist or is invalid, start with empty array
    }
    
    alerts.push(alert);
    await fs.writeFile(alertFile, JSON.stringify(alerts, null, 2));
  }

  async generateSessionReport() {
    const session = this.metrics.currentSession;
    
    const report = {
      sessionId: session.sessionId,
      timestamp: new Date().toISOString(),
      duration: session.totalDuration,
      success: session.success,
      
      summary: {
        totalJobs: session.metrics.totalJobs,
        completedJobs: session.metrics.completedJobs,
        failedJobs: session.metrics.failedJobs,
        successRate: session.successRate,
        retryCount: session.metrics.retryCount
      },
      
      phases: Array.from(session.phases.values()).map(phase => ({
        name: phase.name,
        duration: phase.metrics.duration,
        status: phase.status,
        jobsCompleted: phase.metrics.jobsCompleted,
        jobsFailed: phase.metrics.jobsFailed,
        averageJobDuration: phase.metrics.averageJobDuration
      })),
      
      longestJobs: Array.from(session.jobs.values())
        .sort((a, b) => b.metrics.duration - a.metrics.duration)
        .slice(0, 5)
        .map(job => ({
          name: job.name,
          type: job.type,
          duration: job.metrics.duration,
          status: job.status
        })),
      
      qualityMetrics: session.qualityMetrics,
      
      alerts: session.alerts,
      
      performance: {
        totalExecutionTime: session.totalDuration,
        averageJobTime: Array.from(session.jobs.values())
          .reduce((sum, job) => sum + job.metrics.duration, 0) / session.metrics.totalJobs,
        parallelEfficiency: this.calculateParallelEfficiency()
      },
      
      trends: {
        durationTrend: this.getTrend('duration'),
        successRateTrend: this.getTrend('successRate'),
        qualityTrend: this.getTrend('quality')
      }
    };
    
    return report;
  }

  getTrend(metricType) {
    return this.metrics.trends.get(metricType) || null;
  }

  async updateTrends() {
    if (this.metrics.historical.length < 2) {
      return; // Need at least 2 data points for trends
    }
    
    const recent = this.metrics.historical.slice(-10); // Last 10 sessions
    const older = this.metrics.historical.slice(-20, -10); // Previous 10 sessions
    
    // Duration trend
    const recentAvgDuration = recent.reduce((sum, s) => sum + s.totalDuration, 0) / recent.length;
    const olderAvgDuration = older.length > 0 
      ? older.reduce((sum, s) => sum + s.totalDuration, 0) / older.length
      : recentAvgDuration;
    
    this.metrics.trends.set('duration', {
      current: recentAvgDuration,
      previous: olderAvgDuration,
      change: ((recentAvgDuration - olderAvgDuration) / olderAvgDuration) * 100,
      trend: recentAvgDuration > olderAvgDuration ? 'increasing' : 'decreasing'
    });
    
    // Success rate trend
    const recentAvgSuccessRate = recent.reduce((sum, s) => sum + s.successRate, 0) / recent.length;
    const olderAvgSuccessRate = older.length > 0 
      ? older.reduce((sum, s) => sum + s.successRate, 0) / older.length
      : recentAvgSuccessRate;
    
    this.metrics.trends.set('successRate', {
      current: recentAvgSuccessRate,
      previous: olderAvgSuccessRate,
      change: recentAvgSuccessRate - olderAvgSuccessRate,
      trend: recentAvgSuccessRate > olderAvgSuccessRate ? 'improving' : 'declining'
    });
    
    // Quality trend
    const recentAvgQuality = recent.reduce((sum, s) => sum + (s.qualityMetrics?.qualityScore || 0), 0) / recent.length;
    const olderAvgQuality = older.length > 0 
      ? older.reduce((sum, s) => sum + (s.qualityMetrics?.qualityScore || 0), 0) / older.length
      : recentAvgQuality;
    
    this.metrics.trends.set('quality', {
      current: recentAvgQuality,
      previous: olderAvgQuality,
      change: recentAvgQuality - olderAvgQuality,
      trend: recentAvgQuality > olderAvgQuality ? 'improving' : 'declining'
    });
  }

  async startMonitoring() {
    if (this.isMonitoring) {
      return;
    }
    
    this.isMonitoring = true;
    console.log('🔄 Starting continuous monitoring...');
    
    this.monitoringTimer = setInterval(async () => {
      try {
        await this.collectSystemMetrics();
        await this.checkSystemHealth();
      } catch (error) {
        console.error('Monitoring error:', error);
      }
    }, this.config.monitoringInterval);
  }

  async stopMonitoring() {
    if (!this.isMonitoring) {
      return;
    }
    
    this.isMonitoring = false;
    if (this.monitoringTimer) {
      clearInterval(this.monitoringTimer);
      this.monitoringTimer = null;
    }
    
    console.log('⏹️ Monitoring stopped');
  }

  async getMonitoringReport() {
    return {
      isActive: this.isMonitoring,
      currentSession: this.metrics.currentSession,
      recentSessions: this.metrics.historical.slice(-5),
      trends: Object.fromEntries(this.metrics.trends),
      alertsSummary: {
        total: this.metrics.alerts.length,
        byType: this.groupAlertsByType(),
        recent: this.metrics.alerts.slice(-10)
      }
    };
  }

  groupAlertsByType() {
    const grouped = {};
    this.metrics.alerts.forEach(alert => {
      grouped[alert.type] = (grouped[alert.type] || 0) + 1;
    });
    return grouped;
  }

  calculateParallelEfficiency() {
    if (!this.metrics.currentSession) return 0;
    
    const totalSequentialTime = Array.from(this.metrics.currentSession.jobs.values())
      .reduce((sum, job) => sum + job.metrics.duration, 0);
    
    if (totalSequentialTime === 0) return 100;
    
    return ((totalSequentialTime - this.metrics.currentSession.totalDuration) / totalSequentialTime) * 100;
  }

  async createDirectories() {
    const dirs = ['monitoring', 'monitoring/alerts', 'monitoring/sessions', 'monitoring/trends'];
    for (const dir of dirs) {
      await fs.mkdir(dir, { recursive: true });
    }
  }

  async saveSessionData() {
    const sessionFile = path.join(
      process.cwd(), 
      'monitoring', 
      'sessions', 
      `session-${this.metrics.currentSession.sessionId}.json`
    );
    
    await fs.writeFile(sessionFile, JSON.stringify(this.metrics.currentSession, null, 2));
  }

  async loadHistoricalData() {
    try {
      const sessionsDir = path.join(process.cwd(), 'monitoring', 'sessions');
      const files = await fs.readdir(sessionsDir);
      
      for (const file of files.filter(f => f.endsWith('.json'))) {
        try {
          const sessionData = await fs.readFile(path.join(sessionsDir, file), 'utf8');
          const session = JSON.parse(sessionData);
          this.metrics.historical.push(session);
        } catch (error) {
          console.warn(`Failed to load session file ${file}:`, error.message);
        }
      }
      
      // Sort by start time
      this.metrics.historical.sort((a, b) => a.startTime - b.startTime);
      
      console.log(`📊 Loaded ${this.metrics.historical.length} historical sessions`);
      
    } catch (error) {
      console.log('📊 No historical data found, starting fresh');
    }
  }
}

// CLI execution
if (require.main === module) {
  const monitor = new PipelineMonitor({
    alertChannels: ['console', 'file'],
    alertThresholds: {
      executionTime: 1800000, // 30 minutes
      successRate: 95,
      qualityScore: 90,
      performanceRegression: 10
    }
  });
  
  monitor.initialize()
    .then(() => {
      console.log('✅ Pipeline Monitor initialized and running');
      
      // Keep process alive
      process.on('SIGINT', async () => {
        console.log('\n⏹️ Stopping monitoring...');
        await monitor.stopMonitoring();
        process.exit(0);
      });
    })
    .catch(error => {
      console.error('❌ Failed to start monitoring:', error);
      process.exit(1);
    });
}

module.exports = { PipelineMonitor };