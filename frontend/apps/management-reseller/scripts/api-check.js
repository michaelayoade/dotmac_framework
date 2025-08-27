#!/usr/bin/env node

/**
 * API Integration Check Script
 * Tests API connectivity and endpoint availability
 */

// Use Node.js built-in fetch (Node 18+)
const fetch = globalThis.fetch;

const BASE_URL = process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8000';

console.log('🔍 API Integration Check');
console.log('=======================');
console.log(`Base URL: ${BASE_URL}`);
console.log('');

// Test endpoints we expect to exist
const ENDPOINTS_TO_TEST = [
  { path: '/api/v1/health', method: 'GET', critical: true },
  { path: '/api/v1/auth/login', method: 'POST', critical: true },
  { path: '/api/v1/partners', method: 'GET', critical: true },
  { path: '/api/v1/commissions', method: 'GET', critical: false },
  { path: '/api/v1/analytics/channel-metrics', method: 'GET', critical: false },
  { path: '/api/v1/onboarding', method: 'GET', critical: false },
];

async function testEndpoint(endpoint, timeout = 5000) {
  const { path, method, critical } = endpoint;
  const url = `${BASE_URL}${path}`;
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    const startTime = Date.now();
    const response = await fetch(url, {
      method: 'OPTIONS', // Use OPTIONS to test endpoint existence
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      }
    });
    
    clearTimeout(timeoutId);
    const responseTime = Date.now() - startTime;
    
    const status = response.status;
    const exists = status < 500; // 404 means endpoint doesn't exist, 405 means wrong method but endpoint exists
    
    return {
      ...endpoint,
      url,
      status,
      exists,
      responseTime,
      critical,
    };
  } catch (error) {
    return {
      ...endpoint,
      url,
      exists: false,
      error: error.message,
      critical,
    };
  }
}

async function checkAPIHealth() {
  console.log('🏥 Checking API Health...');
  
  try {
    const response = await fetch(`${BASE_URL}/api/v1/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(10000),
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ API server is healthy');
      console.log(`   Version: ${data.version || 'unknown'}`);
      console.log(`   Environment: ${data.environment || 'unknown'}`);
      return true;
    } else {
      console.log(`❌ API health check failed: ${response.status} ${response.statusText}`);
      return false;
    }
  } catch (error) {
    console.log(`❌ Cannot connect to API server: ${error.message}`);
    return false;
  }
}

async function testAllEndpoints() {
  console.log('🧪 Testing API Endpoints...');
  console.log('');
  
  const results = [];
  
  for (const endpoint of ENDPOINTS_TO_TEST) {
    process.stdout.write(`Testing ${endpoint.method} ${endpoint.path}... `);
    
    const result = await testEndpoint(endpoint);
    results.push(result);
    
    if (result.exists) {
      console.log(`✅ (${result.status}, ${result.responseTime || 0}ms)`);
    } else {
      const icon = result.critical ? '❌' : '⚠️';
      console.log(`${icon} ${result.error ? result.error : `HTTP ${result.status}`}`);
    }
  }
  
  return results;
}

function generateReport(results) {
  console.log('');
  console.log('📊 Summary Report');
  console.log('=================');
  
  const total = results.length;
  const existing = results.filter(r => r.exists).length;
  const missing = results.filter(r => !r.exists).length;
  const criticalMissing = results.filter(r => !r.exists && r.critical).length;
  
  console.log(`Total endpoints tested: ${total}`);
  console.log(`✅ Available: ${existing}`);
  console.log(`❌ Missing: ${missing}`);
  if (criticalMissing > 0) {
    console.log(`🚨 Critical missing: ${criticalMissing}`);
  }
  
  if (missing > 0) {
    console.log('');
    console.log('Missing endpoints:');
    results.filter(r => !r.exists).forEach(result => {
      const icon = result.critical ? '🚨' : '⚠️';
      console.log(`  ${icon} ${result.method} ${result.path}`);
    });
  }
  
  // Generate recommendations
  console.log('');
  console.log('💡 Recommendations:');
  
  if (criticalMissing > 0) {
    console.log('  🚨 CRITICAL: Some essential endpoints are missing');
    console.log('     The application may not work properly without these endpoints');
  }
  
  if (missing > 0) {
    console.log('  📝 Create missing API endpoints in the backend');
    console.log('  🔧 Use the frontend API stubs to implement backend routes');
  }
  
  if (existing === total) {
    console.log('  🎉 All endpoints are available! The API integration looks good.');
  }
  
  // Return status for CI/CD
  const success = criticalMissing === 0;
  console.log('');
  console.log(`🎯 Integration Status: ${success ? 'READY' : 'NEEDS_WORK'}`);
  
  return success;
}

async function main() {
  try {
    // Step 1: Check basic connectivity
    const isHealthy = await checkAPIHealth();
    console.log('');
    
    if (!isHealthy) {
      console.log('⚠️  API server is not responding. Some tests may fail.');
      console.log('   Make sure the backend server is running and accessible.');
      console.log('');
    }
    
    // Step 2: Test all endpoints
    const results = await testAllEndpoints();
    
    // Step 3: Generate report
    const success = generateReport(results);
    
    // Exit with appropriate code
    process.exit(success ? 0 : 1);
    
  } catch (error) {
    console.error('❌ API check failed:', error.message);
    process.exit(1);
  }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n⏹️  API check interrupted');
  process.exit(1);
});

if (require.main === module) {
  main();
}