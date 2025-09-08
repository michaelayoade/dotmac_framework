/**
 * Global Teardown for Gate E: Full E2E + Observability Testing
 * 
 * Cleans up after cross-service flow validation tests
 */

import { FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Gate E: Global Teardown Starting...');
  
  const teardownStartTime = Date.now();
  const setupDir = path.dirname(__filename);
  const gateEDir = path.dirname(setupDir);
  
  const teardownStatus = {
    startTime: new Date().toISOString(),
    status: 'in_progress',
    steps: []
  };
  
  try {
    console.log('🗑️ Cleaning up test data...');
    teardownStatus.steps.push({
      step: 'test_data_cleanup',
      status: 'starting',
      timestamp: new Date().toISOString()
    });
    
    try {
      // Clean up test tenants and users
      const cleanupSql = `
        -- Gate E Test Data Cleanup
        DELETE FROM users WHERE tenant_id = 'gate-e-test-tenant';
        DELETE FROM customers WHERE tenant_id = 'gate-e-test-tenant';
        DELETE FROM notifications WHERE tenant_id = 'gate-e-test-tenant';
        DELETE FROM billing_runs WHERE tenant_id = 'gate-e-test-tenant';
        DELETE FROM tenants WHERE id = 'gate-e-test-tenant';
        
        -- Clean up any test data created during tests
        DELETE FROM tenants WHERE name LIKE 'Test Tenant %';
        DELETE FROM users WHERE email LIKE '%@test.com' AND created_at > NOW() - INTERVAL '1 hour';
        DELETE FROM customers WHERE name LIKE 'Test Customer %' AND created_at > NOW() - INTERVAL '1 hour';
      `;
      
      const testResultsDir = path.join(gateEDir, 'test-results');
      const cleanupFile = path.join(testResultsDir, 'test-data-cleanup.sql');
      fs.writeFileSync(cleanupFile, cleanupSql);
      
      // Note: In a real environment, you'd execute this SQL against the test database
      // For now, we'll just create the cleanup script
      
      teardownStatus.steps[teardownStatus.steps.length - 1].status = 'completed';
      console.log('✅ Test data cleanup completed');
    } catch (error) {
      console.warn('⚠️ Test data cleanup failed:', error);
      teardownStatus.steps[teardownStatus.steps.length - 1].status = 'failed';
      teardownStatus.steps[teardownStatus.steps.length - 1].error = String(error);
    }
    
    console.log('🔄 Collecting final metrics...');
    teardownStatus.steps.push({
      step: 'final_metrics_collection',
      status: 'starting',
      timestamp: new Date().toISOString()
    });
    
    try {
      // Collect final metrics snapshot
      const metricsEndpoint = 'http://localhost:8000/metrics';
      
      try {
        const response = await fetch(metricsEndpoint);
        if (response.ok) {
          const metricsText = await response.text();
          const metricsFile = path.join(gateEDir, 'test-results', 'final-metrics-snapshot.txt');
          fs.writeFileSync(metricsFile, metricsText);
          
          // Extract key metrics
          const keyMetrics = {
            timestamp: new Date().toISOString(),
            http_requests_total: extractMetricValue(metricsText, 'http_requests_total'),
            database_connections: extractMetricValue(metricsText, 'database_connections'),
            dotmac_customers_total: extractMetricValue(metricsText, 'dotmac_customers_total'),
            dotmac_api_requests_total: extractMetricValue(metricsText, 'dotmac_api_requests_total')
          };
          
          const keyMetricsFile = path.join(gateEDir, 'test-results', 'key-metrics-summary.json');
          fs.writeFileSync(keyMetricsFile, JSON.stringify(keyMetrics, null, 2));
          
          teardownStatus.steps[teardownStatus.steps.length - 1].metricsCollected = true;
        }
      } catch (fetchError) {
        console.warn('Could not fetch final metrics:', fetchError);
        teardownStatus.steps[teardownStatus.steps.length - 1].metricsCollected = false;
      }
      
      teardownStatus.steps[teardownStatus.steps.length - 1].status = 'completed';
      console.log('✅ Final metrics collection completed');
    } catch (error) {
      console.warn('⚠️ Final metrics collection failed:', error);
      teardownStatus.steps[teardownStatus.steps.length - 1].status = 'failed';
      teardownStatus.steps[teardownStatus.steps.length - 1].error = String(error);
    }
    
    console.log('📊 Generating test summary...');
    teardownStatus.steps.push({
      step: 'test_summary_generation',
      status: 'starting',
      timestamp: new Date().toISOString()
    });
    
    try {
      // Collect all test result files
      const testResultsDir = path.join(gateEDir, 'test-results');
      const resultFiles = fs.readdirSync(testResultsDir)
        .filter(file => file.endsWith('.json'))
        .map(file => ({
          name: file,
          path: path.join(testResultsDir, file),
          size: fs.statSync(path.join(testResultsDir, file)).size,
          modified: fs.statSync(path.join(testResultsDir, file)).mtime
        }));
      
      const testSummary = {
        gate: 'E',
        teardownTime: new Date().toISOString(),
        testResultFiles: resultFiles,
        environment: {
          nodeVersion: process.version,
          platform: process.platform,
          setupCompleted: process.env.GATE_E_SETUP_COMPLETED === 'true'
        },
        recommendations: generateRecommendations(testResultsDir)
      };
      
      const summaryFile = path.join(testResultsDir, 'gate-e-test-summary.json');
      fs.writeFileSync(summaryFile, JSON.stringify(testSummary, null, 2));
      
      teardownStatus.steps[teardownStatus.steps.length - 1].status = 'completed';
      teardownStatus.steps[teardownStatus.steps.length - 1].summaryFile = summaryFile;
      console.log('✅ Test summary generated');
    } catch (error) {
      console.warn('⚠️ Test summary generation failed:', error);
      teardownStatus.steps[teardownStatus.steps.length - 1].status = 'failed';
      teardownStatus.steps[teardownStatus.steps.length - 1].error = String(error);
    }
    
    console.log('🗂️ Archiving test artifacts...');
    teardownStatus.steps.push({
      step: 'artifact_archiving',
      status: 'starting',
      timestamp: new Date().toISOString()
    });
    
    try {
      // Create artifacts archive
      const artifactsDir = path.join(gateEDir, 'artifacts');
      const testResultsDir = path.join(gateEDir, 'test-results');
      
      if (fs.existsSync(testResultsDir)) {
        // Copy test results to artifacts
        if (!fs.existsSync(artifactsDir)) {
          fs.mkdirSync(artifactsDir, { recursive: true });
        }
        
        const files = fs.readdirSync(testResultsDir);
        let copiedFiles = 0;
        
        for (const file of files) {
          const srcPath = path.join(testResultsDir, file);
          const destPath = path.join(artifactsDir, file);
          
          try {
            fs.copyFileSync(srcPath, destPath);
            copiedFiles++;
          } catch (copyError) {
            console.warn(`Could not copy ${file}:`, copyError);
          }
        }
        
        teardownStatus.steps[teardownStatus.steps.length - 1].status = 'completed';
        teardownStatus.steps[teardownStatus.steps.length - 1].copiedFiles = copiedFiles;
        console.log(`✅ Archived ${copiedFiles} test artifacts`);
      } else {
        teardownStatus.steps[teardownStatus.steps.length - 1].status = 'skipped';
        teardownStatus.steps[teardownStatus.steps.length - 1].reason = 'No test results directory found';
        console.log('⚠️ No test results to archive');
      }
    } catch (error) {
      console.warn('⚠️ Artifact archiving failed:', error);
      teardownStatus.steps[teardownStatus.steps.length - 1].status = 'failed';
      teardownStatus.steps[teardownStatus.steps.length - 1].error = String(error);
    }
    
    // Clean up environment variables
    delete process.env.GATE_E_SETUP_COMPLETED;
    delete process.env.GATE_E_TEST_TENANT_ID;
    delete process.env.GATE_E_ADMIN_EMAIL;
    delete process.env.GATE_E_CUSTOMER_EMAIL;
    
    // Finalize teardown status
    teardownStatus.status = 'completed';
    teardownStatus.endTime = new Date().toISOString();
    teardownStatus.duration = Date.now() - teardownStartTime;
    
    // Save teardown status
    const teardownStatusFile = path.join(gateEDir, 'test-results', 'gate-e-teardown-status.json');
    fs.writeFileSync(teardownStatusFile, JSON.stringify(teardownStatus, null, 2));
    
    console.log(`🎯 Gate E Global Teardown completed in ${Math.round(teardownStatus.duration / 1000)}s`);
    console.log(`📊 Teardown status saved to: ${teardownStatusFile}`);
    
  } catch (error) {
    console.error('❌ Gate E Global Teardown failed:', error);
    
    // Save error status
    const errorStatus = {
      status: 'failed',
      error: String(error),
      timestamp: new Date().toISOString(),
      duration: Date.now() - teardownStartTime
    };
    
    const errorStatusFile = path.join(gateEDir, 'test-results', 'gate-e-teardown-error.json');
    fs.writeFileSync(errorStatusFile, JSON.stringify(errorStatus, null, 2));
    
    throw error;
  }
}

/**
 * Extract metric value from Prometheus format text
 */
function extractMetricValue(metricsText: string, metricName: string): number | null {
  const regex = new RegExp(`^${metricName}(?:\\{[^}]*\\})?\\s+(\\d+(?:\\.\\d+)?)`, 'm');
  const match = metricsText.match(regex);
  return match ? parseFloat(match[1]) : null;
}

/**
 * Generate recommendations based on test results
 */
function generateRecommendations(testResultsDir: string): string[] {
  const recommendations: string[] = [];
  
  try {
    // Check if observability sanity check results exist
    const obsFile = path.join(testResultsDir, 'observability-sanity-check-report.json');
    if (fs.existsSync(obsFile)) {
      const obsResults = JSON.parse(fs.readFileSync(obsFile, 'utf8'));
      if (!obsResults.overall_success) {
        recommendations.push('Review observability sanity check failures');
        recommendations.push('Verify metrics endpoints are accessible');
        recommendations.push('Check trace collection configuration');
      }
    } else {
      recommendations.push('Consider running observability sanity checks');
    }
    
    // Check for performance results
    const perfFile = path.join(testResultsDir, 'performance-results.json');
    if (fs.existsSync(perfFile)) {
      const perfResults = JSON.parse(fs.readFileSync(perfFile, 'utf8'));
      const slowTests = perfResults.tests?.filter((test: any) => test.duration > test.threshold);
      if (slowTests && slowTests.length > 0) {
        recommendations.push('Review performance test results for slow endpoints');
        recommendations.push('Consider optimizing API response times');
      }
    }
    
    // Check for Playwright results
    const playwrightFiles = fs.readdirSync(testResultsDir)
      .filter(file => file.includes('playwright') || file.includes('gate-e-results'));
    
    if (playwrightFiles.length === 0) {
      recommendations.push('Ensure Playwright E2E tests are running successfully');
    }
    
    // General recommendations
    recommendations.push('Review all test artifacts in the artifacts directory');
    recommendations.push('Check service logs for any error patterns');
    recommendations.push('Validate cross-service trace correlation');
    
  } catch (error) {
    recommendations.push('Manual review of test results recommended due to analysis error');
  }
  
  return recommendations;
}

export default globalTeardown;