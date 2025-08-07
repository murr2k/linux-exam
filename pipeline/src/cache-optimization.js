/**
 * Intelligent Cache Optimization System
 * Implements layered caching with intelligent invalidation
 */

const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');
const { performance } = require('perf_hooks');

class IntelligentCacheSystem {
  constructor(options = {}) {
    this.cacheDir = options.cacheDir || './cache';
    this.maxCacheSize = options.maxCacheSize || 1024 * 1024 * 1024; // 1GB
    this.defaultTTL = options.defaultTTL || 3600000; // 1 hour
    this.layers = new Map();
    this.hitRatioMonitor = new CacheHitRatioMonitor();
    this.invalidationStrategy = new SmartInvalidationStrategy();
    this.compressionEnabled = options.compression !== false;
    this.encryptionEnabled = options.encryption === true;
    this.statistics = new CacheStatistics();
  }

  async initialize() {
    console.log('Initializing intelligent cache system');
    
    // Create cache directory
    await this.ensureCacheDirectory();
    
    // Initialize cache layers
    await this.initializeCacheLayers();
    
    // Start background processes
    this.startBackgroundCleanup();
    this.startHitRatioMonitoring();
    
    console.log('Cache system initialized successfully');
  }

  async initializeCacheLayers() {
    // L1 Cache - In-memory, fastest access
    this.layers.set('L1', new MemoryCache({
      maxSize: 100 * 1024 * 1024, // 100MB
      evictionPolicy: 'LRU',
      ttl: 300000 // 5 minutes
    }));
    
    // L2 Cache - SSD/Fast disk, medium access speed
    this.layers.set('L2', new DiskCache({
      directory: path.join(this.cacheDir, 'L2'),
      maxSize: 500 * 1024 * 1024, // 500MB
      compression: this.compressionEnabled,
      ttl: 1800000 // 30 minutes
    }));
    
    // L3 Cache - Long-term storage, slower access
    this.layers.set('L3', new PersistentCache({
      directory: path.join(this.cacheDir, 'L3'),
      maxSize: this.maxCacheSize - 600 * 1024 * 1024, // Remaining space
      compression: this.compressionEnabled,
      encryption: this.encryptionEnabled,
      ttl: this.defaultTTL
    }));
    
    // Initialize each layer
    for (const [layerName, layer] of this.layers) {
      await layer.initialize();
      console.log(`Initialized cache layer: ${layerName}`);
    }
  }

  async get(key, options = {}) {
    const startTime = performance.now();
    let result = null;
    let sourceLayer = null;
    
    try {
      // Generate cache key
      const cacheKey = this.generateCacheKey(key, options);
      
      // Try each layer in order (L1 -> L2 -> L3)
      for (const [layerName, layer] of this.layers) {
        result = await layer.get(cacheKey);
        
        if (result !== null) {
          sourceLayer = layerName;
          
          // Promote to higher layers for future access
          await this.promoteToHigherLayers(cacheKey, result, layerName);
          
          break;
        }
      }
      
      // Record hit/miss statistics
      const executionTime = performance.now() - startTime;
      
      if (result !== null) {
        this.statistics.recordHit(sourceLayer, executionTime);
        this.hitRatioMonitor.recordHit(key, sourceLayer);
      } else {
        this.statistics.recordMiss(executionTime);
        this.hitRatioMonitor.recordMiss(key);
      }
      
      return result;
      
    } catch (error) {
      console.error('Cache get error:', error);
      this.statistics.recordError(error);
      return null;
    }
  }

  async set(key, value, options = {}) {
    const startTime = performance.now();
    
    try {
      const cacheKey = this.generateCacheKey(key, options);
      const serializedValue = await this.serializeValue(value, options);
      const ttl = options.ttl || this.defaultTTL;
      
      // Determine optimal cache layer based on value characteristics
      const optimalLayer = this.determineOptimalLayer(serializedValue, options);
      
      // Store in optimal layer and potentially others
      const promises = [];
      
      // Always store in L1 for fast access
      if (optimalLayer !== 'L1') {
        promises.push(this.layers.get('L1').set(cacheKey, serializedValue, { ttl: Math.min(ttl, 300000) }));
      }
      
      // Store in optimal layer
      promises.push(this.layers.get(optimalLayer).set(cacheKey, serializedValue, { ttl }));
      
      // Store in L3 for persistence if not already
      if (optimalLayer !== 'L3' && options.persist !== false) {
        promises.push(this.layers.get('L3').set(cacheKey, serializedValue, { ttl }));
      }
      
      await Promise.all(promises);
      
      // Record statistics
      const executionTime = performance.now() - startTime;
      this.statistics.recordSet(optimalLayer, executionTime, serializedValue.length);
      
      // Update cache key metadata
      await this.updateKeyMetadata(cacheKey, {
        size: serializedValue.length,
        layer: optimalLayer,
        timestamp: Date.now(),
        accessCount: 1,
        ttl: ttl
      });
      
      return true;
      
    } catch (error) {
      console.error('Cache set error:', error);
      this.statistics.recordError(error);
      return false;
    }
  }

  async invalidate(pattern, options = {}) {
    console.log(`Invalidating cache entries matching pattern: ${pattern}`);
    
    const strategy = options.strategy || 'smart';
    
    switch (strategy) {
      case 'immediate':
        return await this.immediateInvalidation(pattern);
      case 'lazy':
        return await this.lazyInvalidation(pattern);
      case 'smart':
      default:
        return await this.smartInvalidation(pattern, options);
    }
  }

  async smartInvalidation(pattern, options) {
    const invalidationPlan = await this.invalidationStrategy.createPlan(pattern, options);
    
    let invalidatedCount = 0;
    
    for (const step of invalidationPlan.steps) {
      switch (step.action) {
        case 'invalidate_immediate':
          invalidatedCount += await this.invalidateKeys(step.keys);
          break;
        case 'mark_stale':
          invalidatedCount += await this.markKeysStale(step.keys);
          break;
        case 'schedule_cleanup':
          await this.scheduleCleanup(step.keys, step.delay);
          break;
      }
    }
    
    console.log(`Smart invalidation completed: ${invalidatedCount} entries affected`);
    return invalidatedCount;
  }

  async promoteToHigherLayers(cacheKey, value, currentLayer) {
    const layerOrder = ['L1', 'L2', 'L3'];
    const currentIndex = layerOrder.indexOf(currentLayer);
    
    // Promote to layers with higher priority (lower index)
    for (let i = 0; i < currentIndex; i++) {
      const higherLayer = this.layers.get(layerOrder[i]);
      await higherLayer.set(cacheKey, value, { 
        ttl: this.calculatePromotionTTL(layerOrder[i]) 
      });
    }
  }

  determineOptimalLayer(serializedValue, options) {
    const size = serializedValue.length;
    const accessPattern = options.accessPattern || 'unknown';
    const frequency = options.frequency || 'medium';
    
    // Small, frequently accessed items -> L1
    if (size < 1024 && frequency === 'high') {
      return 'L1';
    }
    
    // Medium size, moderate frequency -> L2
    if (size < 1024 * 1024 && frequency === 'medium') {
      return 'L2';
    }
    
    // Large or infrequent items -> L3
    return 'L3';
  }

  generateCacheKey(key, options) {
    const keyData = {
      key: key,
      version: options.version || '1.0',
      namespace: options.namespace || 'default',
      variant: options.variant || null
    };
    
    const keyString = JSON.stringify(keyData);
    return crypto.createHash('sha256').update(keyString).digest('hex');
  }

  async serializeValue(value, options) {
    let serialized = JSON.stringify(value);
    
    if (this.compressionEnabled && serialized.length > 1024) {
      const zlib = require('zlib');
      serialized = await new Promise((resolve, reject) => {
        zlib.gzip(serialized, (err, compressed) => {
          if (err) reject(err);
          else resolve(compressed.toString('base64'));
        });
      });
    }
    
    if (this.encryptionEnabled && options.encrypt) {
      // Implement encryption if needed
      serialized = await this.encrypt(serialized);
    }
    
    return serialized;
  }

  startBackgroundCleanup() {
    setInterval(async () => {
      try {
        await this.performBackgroundCleanup();
      } catch (error) {
        console.error('Background cleanup error:', error);
      }
    }, 300000); // 5 minutes
  }

  async performBackgroundCleanup() {
    console.log('Starting background cache cleanup');
    
    let totalCleaned = 0;
    
    for (const [layerName, layer] of this.layers) {
      const cleaned = await layer.cleanup();
      totalCleaned += cleaned;
      console.log(`Cleaned ${cleaned} entries from ${layerName}`);
    }
    
    // Optimize cache distribution
    await this.optimizeCacheDistribution();
    
    console.log(`Background cleanup completed: ${totalCleaned} entries cleaned`);
  }

  async optimizeCacheDistribution() {
    // Analyze access patterns and redistribute frequently accessed items
    const accessPatterns = await this.hitRatioMonitor.getAccessPatterns();
    
    for (const pattern of accessPatterns.hotKeys) {
      // Ensure hot keys are in L1
      if (!await this.layers.get('L1').exists(pattern.key)) {
        const value = await this.get(pattern.key);
        if (value !== null) {
          await this.layers.get('L1').set(pattern.key, value, { ttl: 300000 });
        }
      }
    }
    
    // Move cold keys to lower layers
    for (const pattern of accessPatterns.coldKeys) {
      await this.layers.get('L1').delete(pattern.key);
    }
  }

  async getStatistics() {
    const layerStats = new Map();
    
    for (const [layerName, layer] of this.layers) {
      layerStats.set(layerName, await layer.getStatistics());
    }
    
    return {
      global: this.statistics.getGlobalStats(),
      hitRatio: this.hitRatioMonitor.getHitRatio(),
      layers: Object.fromEntries(layerStats),
      performance: await this.getPerformanceMetrics()
    };
  }

  async getPerformanceMetrics() {
    return {
      avgGetTime: this.statistics.getAverageGetTime(),
      avgSetTime: this.statistics.getAverageSetTime(),
      hitRatio: this.hitRatioMonitor.getOverallHitRatio(),
      cacheEfficiency: await this.calculateCacheEfficiency(),
      memoryUsage: await this.calculateMemoryUsage()
    };
  }
}

class MemoryCache {
  constructor(options = {}) {
    this.maxSize = options.maxSize || 100 * 1024 * 1024;
    this.evictionPolicy = options.evictionPolicy || 'LRU';
    this.ttl = options.ttl || 300000;
    this.cache = new Map();
    this.accessOrder = new Map(); // For LRU
    this.currentSize = 0;
  }

  async initialize() {
    // No initialization needed for memory cache
  }

  async get(key) {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }
    
    // Check TTL
    if (Date.now() > entry.expiry) {
      this.cache.delete(key);
      this.accessOrder.delete(key);
      this.currentSize -= entry.size;
      return null;
    }
    
    // Update access order for LRU
    this.accessOrder.set(key, Date.now());
    
    return entry.value;
  }

  async set(key, value, options = {}) {
    const ttl = options.ttl || this.ttl;
    const size = this.calculateSize(value);
    const expiry = Date.now() + ttl;
    
    // Check if we need to evict entries
    await this.ensureSpace(size);
    
    // Remove existing entry if present
    if (this.cache.has(key)) {
      const existingEntry = this.cache.get(key);
      this.currentSize -= existingEntry.size;
    }
    
    // Add new entry
    const entry = {
      value: value,
      size: size,
      expiry: expiry,
      created: Date.now()
    };
    
    this.cache.set(key, entry);
    this.accessOrder.set(key, Date.now());
    this.currentSize += size;
    
    return true;
  }

  async ensureSpace(requiredSize) {
    while (this.currentSize + requiredSize > this.maxSize && this.cache.size > 0) {
      await this.evictLRU();
    }
  }

  async evictLRU() {
    // Find least recently used entry
    let oldestKey = null;
    let oldestTime = Date.now();
    
    for (const [key, accessTime] of this.accessOrder) {
      if (accessTime < oldestTime) {
        oldestTime = accessTime;
        oldestKey = key;
      }
    }
    
    if (oldestKey) {
      const entry = this.cache.get(oldestKey);
      this.cache.delete(oldestKey);
      this.accessOrder.delete(oldestKey);
      this.currentSize -= entry.size;
    }
  }

  calculateSize(value) {
    return JSON.stringify(value).length * 2; // Rough estimate for UTF-16
  }

  async cleanup() {
    let cleaned = 0;
    const now = Date.now();
    
    for (const [key, entry] of this.cache) {
      if (now > entry.expiry) {
        this.cache.delete(key);
        this.accessOrder.delete(key);
        this.currentSize -= entry.size;
        cleaned++;
      }
    }
    
    return cleaned;
  }

  async exists(key) {
    return this.cache.has(key) && Date.now() <= this.cache.get(key).expiry;
  }

  async delete(key) {
    const entry = this.cache.get(key);
    if (entry) {
      this.cache.delete(key);
      this.accessOrder.delete(key);
      this.currentSize -= entry.size;
      return true;
    }
    return false;
  }

  async getStatistics() {
    return {
      entries: this.cache.size,
      currentSize: this.currentSize,
      maxSize: this.maxSize,
      utilization: (this.currentSize / this.maxSize) * 100
    };
  }
}

class CacheHitRatioMonitor {
  constructor() {
    this.hits = new Map();
    this.misses = new Map();
    this.accessPatterns = new Map();
    this.totalHits = 0;
    this.totalMisses = 0;
  }

  recordHit(key, layer) {
    this.totalHits++;
    
    if (!this.hits.has(layer)) {
      this.hits.set(layer, 0);
    }
    this.hits.set(layer, this.hits.get(layer) + 1);
    
    this.updateAccessPattern(key, 'hit');
  }

  recordMiss(key) {
    this.totalMisses++;
    this.updateAccessPattern(key, 'miss');
  }

  updateAccessPattern(key, type) {
    if (!this.accessPatterns.has(key)) {
      this.accessPatterns.set(key, {
        hits: 0,
        misses: 0,
        lastAccess: Date.now(),
        accessCount: 0
      });
    }
    
    const pattern = this.accessPatterns.get(key);
    pattern[type === 'hit' ? 'hits' : 'misses']++;
    pattern.accessCount++;
    pattern.lastAccess = Date.now();
  }

  getHitRatio() {
    const total = this.totalHits + this.totalMisses;
    return total > 0 ? this.totalHits / total : 0;
  }

  getOverallHitRatio() {
    return this.getHitRatio();
  }

  async getAccessPatterns() {
    const now = Date.now();
    const hotKeys = [];
    const coldKeys = [];
    
    for (const [key, pattern] of this.accessPatterns) {
      const hitRatio = pattern.hits / (pattern.hits + pattern.misses);
      const timeSinceLastAccess = now - pattern.lastAccess;
      
      if (hitRatio > 0.7 && timeSinceLastAccess < 300000) { // 5 minutes
        hotKeys.push({ key, pattern, hitRatio });
      } else if (timeSinceLastAccess > 3600000) { // 1 hour
        coldKeys.push({ key, pattern, hitRatio });
      }
    }
    
    return { hotKeys, coldKeys };
  }
}

class SmartInvalidationStrategy {
  async createPlan(pattern, options) {
    const keys = await this.findMatchingKeys(pattern);
    const plan = {
      steps: [],
      estimatedImpact: 0
    };
    
    // Analyze keys and create invalidation strategy
    for (const key of keys) {
      const metadata = await this.getKeyMetadata(key);
      const step = this.determineInvalidationStep(key, metadata, options);
      plan.steps.push(step);
      plan.estimatedImpact += step.impact;
    }
    
    return plan;
  }

  determineInvalidationStep(key, metadata, options) {
    const now = Date.now();
    const age = now - metadata.timestamp;
    const accessFrequency = metadata.accessCount / Math.max(1, age / 3600000); // per hour
    
    // High-frequency keys - mark as stale for lazy invalidation
    if (accessFrequency > 10) {
      return {
        action: 'mark_stale',
        keys: [key],
        impact: 1,
        reason: 'High frequency access - lazy invalidation'
      };
    }
    
    // Old or infrequently accessed keys - immediate invalidation
    if (age > 3600000 || accessFrequency < 1) {
      return {
        action: 'invalidate_immediate',
        keys: [key],
        impact: 3,
        reason: 'Old or infrequent - immediate invalidation'
      };
    }
    
    // Default - schedule cleanup
    return {
      action: 'schedule_cleanup',
      keys: [key],
      delay: 300000, // 5 minutes
      impact: 2,
      reason: 'Scheduled cleanup'
    };
  }
}

class CacheStatistics {
  constructor() {
    this.globalStats = {
      hits: 0,
      misses: 0,
      sets: 0,
      errors: 0,
      totalGetTime: 0,
      totalSetTime: 0
    };
  }

  recordHit(layer, time) {
    this.globalStats.hits++;
    this.globalStats.totalGetTime += time;
  }

  recordMiss(time) {
    this.globalStats.misses++;
    this.globalStats.totalGetTime += time;
  }

  recordSet(layer, time, size) {
    this.globalStats.sets++;
    this.globalStats.totalSetTime += time;
  }

  recordError(error) {
    this.globalStats.errors++;
  }

  getGlobalStats() {
    return { ...this.globalStats };
  }

  getAverageGetTime() {
    const totalGets = this.globalStats.hits + this.globalStats.misses;
    return totalGets > 0 ? this.globalStats.totalGetTime / totalGets : 0;
  }

  getAverageSetTime() {
    return this.globalStats.sets > 0 ? this.globalStats.totalSetTime / this.globalStats.sets : 0;
  }
}

module.exports = {
  IntelligentCacheSystem,
  MemoryCache,
  CacheHitRatioMonitor,
  SmartInvalidationStrategy,
  CacheStatistics
};