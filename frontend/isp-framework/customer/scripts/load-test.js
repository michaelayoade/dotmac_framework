#!/usr/bin/env node

/**
 * Production Load Testing Script
 * Tests critical endpoints under realistic load conditions
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

class LoadTester {
  constructor() {
    this.results = {
      total: 0,
      successful: 0,
      failed: 0,
      avgResponseTime: 0,
      maxResponseTime: 0,
      minResponseTime: Infinity,
      errors: [],
      responseTimes: [],
    };
    this.startTime = Date.now();
  }

  log(message, level = 'info') {
    const timestamp = new Date().toISOString();
    const prefix =
      {
        info: '📊',
        success: '✅',
        error: '❌',
        warning: '⚠️',
        critical: '🚨',
      }[level] || 'ℹ️';

    console.log(`${timestamp} ${prefix} ${message}`);
  }

  async makeRequest(options) {
    return new Promise((resolve) => {
      const startTime = Date.now();
      const client = options.protocol === 'https:' ? https : http;

      const req = client.request(options, (res) => {
        let data = '';

        res.on('data', (chunk) => {
          data += chunk;
        });

        res.on('end', () => {
          const responseTime = Date.now() - startTime;
          resolve({
            statusCode: res.statusCode,
            responseTime,
            data,
            headers: res.headers,
            success: res.statusCode >= 200 && res.statusCode < 400,
          });
        });
      });

      req.on('error', (error) => {
        const responseTime = Date.now() - startTime;
        resolve({
          statusCode: 0,
          responseTime,
          error: error.message,
          success: false,
        });
      });

      req.setTimeout(10000, () => {
        req.destroy();
        const responseTime = Date.now() - startTime;
        resolve({
          statusCode: 408,
          responseTime,
          error: 'Request timeout',
          success: false,
        });
      });

      if (options.body) {
        req.write(options.body);
      }

      req.end();
    });
  }

  async testEndpoint(endpoint, options = {}) {
    const {
      method = 'GET',
      headers = {},
      body = null,
      concurrent = 10,
      requests = 100,
      name = endpoint.path || 'endpoint',
    } = options;

    this.log(`Testing ${name}: ${concurrent} concurrent users, ${requests} total requests`, 'info');

    const requestOptions = {
      hostname: endpoint.hostname || 'localhost',
      port: endpoint.port || (endpoint.protocol === 'https:' ? 443 : 3000),
      path: endpoint.path || '/',
      method,
      headers: {
        'User-Agent': 'LoadTest/1.0',
        Accept: 'application/json',
        ...headers,
      },
      protocol: endpoint.protocol || 'http:',
      body,
    };

    // Execute requests in batches
    const batchSize = Math.ceil(requests / concurrent);
    const batches = [];

    for (let i = 0; i < concurrent; i++) {
      const batch = [];
      for (let j = 0; j < batchSize && i * batchSize + j < requests; j++) {
        batch.push(this.makeRequest(requestOptions));
      }
      batches.push(batch);
    }

    // Execute all batches concurrently
    const allResults = [];
    for (const batch of batches) {
      const batchResults = await Promise.all(batch);
      allResults.push(...batchResults);
    }

    // Process results
    this.processResults(allResults, name);
    return allResults;
  }

  processResults(results, testName) {
    const successful = results.filter((r) => r.success).length;
    const failed = results.length - successful;
    const responseTimes = results.map((r) => r.responseTime);
    const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
    const maxResponseTime = Math.max(...responseTimes);
    const minResponseTime = Math.min(...responseTimes);

    this.results.total += results.length;
    this.results.successful += successful;
    this.results.failed += failed;
    this.results.responseTimes.push(...responseTimes);

    // Update global stats
    if (maxResponseTime > this.results.maxResponseTime) {
      this.results.maxResponseTime = maxResponseTime;
    }
    if (minResponseTime < this.results.minResponseTime) {
      this.results.minResponseTime = minResponseTime;
    }

    // Collect errors
    const errors = results
      .filter((r) => !r.success)
      .map((r) => r.error || `Status ${r.statusCode}`);
    this.results.errors.push(...errors);

    const successRate = (successful / results.length) * 100;
    const errorRate = (failed / results.length) * 100;

    this.log(`${testName} Results:`, 'info');
    this.log(
      `  ✅ Successful: ${successful}/${results.length} (${successRate.toFixed(2)}%)`,
      'success'
    );
    this.log(
      `  ❌ Failed: ${failed}/${results.length} (${errorRate.toFixed(2)}%)`,
      failed > 0 ? 'error' : 'info'
    );
    this.log(`  📈 Avg Response: ${avgResponseTime.toFixed(2)}ms`, 'info');
    this.log(`  📊 Min/Max: ${minResponseTime}ms / ${maxResponseTime}ms`, 'info');

    if (failed > results.length * 0.05) {
      // More than 5% failure rate
      this.log(
        `  🚨 HIGH FAILURE RATE: ${errorRate.toFixed(2)}% - Investigation required`,
        'critical'
      );
    }

    if (avgResponseTime > 2000) {
      // Slow response time
      this.log(
        `  ⚠️  SLOW RESPONSE: ${avgResponseTime.toFixed(2)}ms avg - Optimization needed`,
        'warning'
      );
    }
  }

  async runLoadTests() {
    this.log('🚀 Starting Production Load Testing Suite', 'info');
    this.log('==========================================', 'info');

    // Test 1: Health Check Endpoint (Critical for load balancers)
    await this.testEndpoint(
      { path: '/api/health', hostname: 'localhost', port: 3000 },
      {
        concurrent: 20,
        requests: 200,
        name: 'Health Check',
        headers: {
          'Cache-Control': 'no-cache',
        },
      }
    );

    // Test 2: Authentication Endpoint (High security load)
    await this.testEndpoint(
      { path: '/api/auth/login', hostname: 'localhost', port: 3000 },
      {
        method: 'POST',
        concurrent: 5, // Lower concurrency for auth
        requests: 50,
        name: 'Authentication',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': 'test-token',
        },
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'TestPassword123!',
        }),
      }
    );

    // Test 3: Dashboard Data (Authenticated endpoints)
    await this.testEndpoint(
      { path: '/api/dashboard/data', hostname: 'localhost', port: 3000 },
      {
        concurrent: 15,
        requests: 150,
        name: 'Dashboard Data',
        headers: {
          Authorization: 'Bearer test-token',
          Cookie: 'secure-auth-token=test; portal-type=customer',
        },
      }
    );

    // Test 4: Billing Information (Data-intensive)
    await this.testEndpoint(
      { path: '/api/billing/current', hostname: 'localhost', port: 3000 },
      {
        concurrent: 10,
        requests: 100,
        name: 'Billing Data',
        headers: {
          Authorization: 'Bearer test-token',
          Cookie: 'secure-auth-token=test; portal-type=customer',
        },
      }
    );

    // Test 5: Static Assets (CDN performance)
    await this.testEndpoint(
      { path: '/favicon.ico', hostname: 'localhost', port: 3000 },
      {
        concurrent: 30,
        requests: 300,
        name: 'Static Assets',
        headers: {
          Accept: 'image/*',
        },
      }
    );

    this.generateReport();
  }

  generateReport() {
    const totalTime = Date.now() - this.startTime;
    const overallAvgResponse =
      this.results.responseTimes.reduce((a, b) => a + b, 0) / this.results.responseTimes.length;
    const successRate = (this.results.successful / this.results.total) * 100;

    // Calculate percentiles
    const sortedTimes = [...this.results.responseTimes].sort((a, b) => a - b);
    const p95 = sortedTimes[Math.floor(sortedTimes.length * 0.95)];
    const p99 = sortedTimes[Math.floor(sortedTimes.length * 0.99)];

    this.log('', 'info');
    this.log('📋 LOAD TESTING FINAL REPORT', 'info');
    this.log('==============================', 'info');
    this.log(`🕒 Total Test Duration: ${(totalTime / 1000).toFixed(2)}s`, 'info');
    this.log(`📊 Total Requests: ${this.results.total}`, 'info');
    this.log(`✅ Successful: ${this.results.successful} (${successRate.toFixed(2)}%)`, 'success');
    this.log(`❌ Failed: ${this.results.failed} (${(100 - successRate).toFixed(2)}%)`, 'info');
    this.log(
      `⚡ Throughput: ${(this.results.total / (totalTime / 1000)).toFixed(2)} req/sec`,
      'info'
    );
    this.log('', 'info');
    this.log('📈 Response Time Statistics:', 'info');
    this.log(`  Average: ${overallAvgResponse.toFixed(2)}ms`, 'info');
    this.log(`  Min: ${this.results.minResponseTime}ms`, 'info');
    this.log(`  Max: ${this.results.maxResponseTime}ms`, 'info');
    this.log(`  95th Percentile: ${p95}ms`, 'info');
    this.log(`  99th Percentile: ${p99}ms`, 'info');

    // Performance Assessment
    this.log('', 'info');
    this.log('🎯 Performance Assessment:', 'info');

    if (successRate >= 99.9) {
      this.log('✅ EXCELLENT: >99.9% success rate', 'success');
    } else if (successRate >= 99.5) {
      this.log('✅ GOOD: >99.5% success rate', 'success');
    } else if (successRate >= 99.0) {
      this.log('⚠️  ACCEPTABLE: >99% success rate', 'warning');
    } else {
      this.log('❌ POOR: <99% success rate - Investigation required', 'error');
    }

    if (p95 <= 500) {
      this.log('✅ EXCELLENT: P95 response time ≤500ms', 'success');
    } else if (p95 <= 1000) {
      this.log('✅ GOOD: P95 response time ≤1000ms', 'success');
    } else if (p95 <= 2000) {
      this.log('⚠️  ACCEPTABLE: P95 response time ≤2000ms', 'warning');
    } else {
      this.log('❌ SLOW: P95 response time >2000ms - Optimization needed', 'error');
    }

    const throughput = this.results.total / (totalTime / 1000);
    if (throughput >= 100) {
      this.log('✅ HIGH THROUGHPUT: ≥100 req/sec', 'success');
    } else if (throughput >= 50) {
      this.log('✅ GOOD THROUGHPUT: ≥50 req/sec', 'success');
    } else if (throughput >= 20) {
      this.log('⚠️  MODERATE THROUGHPUT: ≥20 req/sec', 'warning');
    } else {
      this.log('❌ LOW THROUGHPUT: <20 req/sec - Scaling required', 'error');
    }

    // Production Readiness
    const isProductionReady = successRate >= 99.5 && p95 <= 1000 && throughput >= 50;
    this.log('', 'info');
    this.log('🏆 PRODUCTION READINESS:', isProductionReady ? 'success' : 'critical');
    if (isProductionReady) {
      this.log('✅ PASSED: Application ready for production deployment', 'success');
    } else {
      this.log('❌ FAILED: Application requires optimization before production', 'critical');
      this.log('', 'info');
      this.log('🔧 Recommended Actions:', 'info');
      if (successRate < 99.5) {
        this.log('- Investigate and fix error sources', 'info');
      }
      if (p95 > 1000) {
        this.log('- Optimize slow endpoints and database queries', 'info');
      }
      if (throughput < 50) {
        this.log('- Scale infrastructure and optimize performance', 'info');
      }
    }

    // Save detailed report
    const reportPath = path.join(__dirname, '../reports/load-test-report.json');
    const reportDir = path.dirname(reportPath);

    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true });
    }

    const detailedReport = {
      timestamp: new Date().toISOString(),
      summary: {
        totalTime: totalTime / 1000,
        totalRequests: this.results.total,
        successfulRequests: this.results.successful,
        failedRequests: this.results.failed,
        successRate,
        throughput,
        avgResponseTime: overallAvgResponse,
        minResponseTime: this.results.minResponseTime,
        maxResponseTime: this.results.maxResponseTime,
        p95ResponseTime: p95,
        p99ResponseTime: p99,
        isProductionReady,
      },
      errors: [...new Set(this.results.errors)],
      responseTimes: this.results.responseTimes,
    };

    fs.writeFileSync(reportPath, JSON.stringify(detailedReport, null, 2));
    this.log(`📄 Detailed report saved: ${reportPath}`, 'info');
  }
}

// CLI handling
async function main() {
  const args = process.argv.slice(2);
  const loadTester = new LoadTester();

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Load Testing Tool for Customer Portal

Usage:
  node load-test.js [options]

Options:
  --help, -h     Show this help message
  --quick        Run quick test (fewer requests)
  --intensive    Run intensive test (more concurrent users)

Examples:
  node load-test.js              # Standard load test
  node load-test.js --quick      # Quick validation test
  node load-test.js --intensive  # Stress test
`);
    process.exit(0);
  }

  try {
    await loadTester.runLoadTests();

    // Exit with appropriate code based on results
    const successRate = (loadTester.results.successful / loadTester.results.total) * 100;
    const avgResponse =
      loadTester.results.responseTimes.reduce((a, b) => a + b, 0) /
      loadTester.results.responseTimes.length;

    if (successRate >= 99.5 && avgResponse <= 1000) {
      process.exit(0); // Success
    } else {
      process.exit(1); // Failed performance criteria
    }
  } catch (error) {
    console.error('❌ Load test failed:', error.message);
    process.exit(2); // Error in test execution
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { LoadTester };
