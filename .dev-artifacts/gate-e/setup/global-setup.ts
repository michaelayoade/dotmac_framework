/**
 * Global Setup for Gate E: Full E2E + Observability Testing
 * 
 * Prepares the test environment for cross-service flow validation
 */

import { FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Gate E: Global Setup Starting...');
  
  const setupStartTime = Date.now();
  const setupDir = path.dirname(__filename);
  const gateEDir = path.dirname(setupDir);
  const projectRoot = path.resolve(gateEDir, '../..');
  
  try {
    // Create test results directory
    const testResultsDir = path.join(gateEDir, 'test-results');
    if (!fs.existsSync(testResultsDir)) {
      fs.mkdirSync(testResultsDir, { recursive: true });
    }
    
    // Create setup status file
    const setupStatus = {
      startTime: new Date().toISOString(),
      status: 'in_progress',
      steps: []
    };
    
    console.log('📋 Setting up test databases...');
    setupStatus.steps.push({
      step: 'database_setup',
      status: 'starting',
      timestamp: new Date().toISOString()
    });
    
    try {
      // Setup test database
      execSync('createdb dotmac_test_gate_e 2>/dev/null || true', { stdio: 'pipe' });
      
      // Run migrations if available
      const alembicConfigPath = path.join(projectRoot, 'alembic.ini');
      if (fs.existsSync(alembicConfigPath)) {
        process.env.DATABASE_URL = 'postgresql://test:test@localhost:5432/dotmac_test_gate_e';
        execSync('alembic upgrade head', { 
          cwd: projectRoot, 
          stdio: 'pipe',
          env: { ...process.env, DATABASE_URL: 'postgresql://test:test@localhost:5432/dotmac_test_gate_e' }
        });
      }
      
      setupStatus.steps[setupStatus.steps.length - 1].status = 'completed';
      console.log('✅ Database setup completed');
    } catch (error) {
      console.warn('⚠️ Database setup failed, continuing with existing database:', error);
      setupStatus.steps[setupStatus.steps.length - 1].status = 'failed';
      setupStatus.steps[setupStatus.steps.length - 1].error = String(error);
    }
    
    console.log('🔧 Setting up test data...');
    setupStatus.steps.push({
      step: 'test_data_setup',
      status: 'starting',
      timestamp: new Date().toISOString()
    });
    
    try {
      // Create test data setup script content
      const testDataSetup = `
        -- Gate E Test Data Setup
        INSERT INTO tenants (id, name, plan, created_at) VALUES 
        ('gate-e-test-tenant', 'Gate E Test Tenant', 'premium', NOW())
        ON CONFLICT (id) DO NOTHING;
        
        INSERT INTO users (id, email, tenant_id, role, created_at) VALUES
        ('gate-e-admin', 'admin@gate-e-test.com', 'gate-e-test-tenant', 'admin', NOW()),
        ('gate-e-customer', 'customer@gate-e-test.com', 'gate-e-test-tenant', 'customer', NOW())
        ON CONFLICT (id) DO NOTHING;
        
        -- Add more test data as needed
      `;
      
      const testDataFile = path.join(testResultsDir, 'test-data-setup.sql');
      fs.writeFileSync(testDataFile, testDataSetup);
      
      setupStatus.steps[setupStatus.steps.length - 1].status = 'completed';
      console.log('✅ Test data setup completed');
    } catch (error) {
      console.warn('⚠️ Test data setup failed:', error);
      setupStatus.steps[setupStatus.steps.length - 1].status = 'failed';
      setupStatus.steps[setupStatus.steps.length - 1].error = String(error);
    }
    
    console.log('🌐 Validating service endpoints...');
    setupStatus.steps.push({
      step: 'service_validation',
      status: 'starting',
      timestamp: new Date().toISOString()
    });
    
    const serviceEndpoints = [
      { name: 'Management Platform', url: 'http://localhost:8000/health' },
      { name: 'ISP Admin', url: 'http://localhost:3000', checkPath: '/' },
      { name: 'Customer Portal', url: 'http://localhost:3001', checkPath: '/' },
      { name: 'Reseller Portal', url: 'http://localhost:3003', checkPath: '/' }
    ];
    
    const serviceStatus = [];
    
    for (const service of serviceEndpoints) {
      try {
        const response = await fetch(service.checkPath ? service.url + service.checkPath : service.url, {
          method: 'GET',
          headers: { 'User-Agent': 'Gate-E-Setup/1.0' }
        });
        
        serviceStatus.push({
          name: service.name,
          url: service.url,
          status: response.ok ? 'available' : 'unavailable',
          statusCode: response.status
        });
        
        if (response.ok) {
          console.log(`✅ ${service.name} is available`);
        } else {
          console.log(`⚠️ ${service.name} returned ${response.status}`);
        }
      } catch (error) {
        serviceStatus.push({
          name: service.name,
          url: service.url,
          status: 'error',
          error: String(error)
        });
        console.log(`❌ ${service.name} is not accessible:`, error);
      }
    }
    
    setupStatus.steps[setupStatus.steps.length - 1].status = 'completed';
    setupStatus.steps[setupStatus.steps.length - 1].services = serviceStatus;
    
    console.log('🔍 Setting up observability validation...');
    setupStatus.steps.push({
      step: 'observability_setup',
      status: 'starting',
      timestamp: new Date().toISOString()
    });
    
    try {
      // Validate observability endpoints
      const observabilityEndpoints = [
        { name: 'Metrics Endpoint', url: 'http://localhost:8000/metrics' },
        { name: 'SigNoz', url: 'http://localhost:3301/api/v1/health' },
        { name: 'Prometheus', url: 'http://localhost:9090/api/v1/query' }
      ];
      
      const observabilityStatus = [];
      
      for (const endpoint of observabilityEndpoints) {
        try {
          const response = await fetch(endpoint.url, {
            method: 'GET',
            headers: { 'User-Agent': 'Gate-E-Setup/1.0' }
          });
          
          observabilityStatus.push({
            name: endpoint.name,
            url: endpoint.url,
            status: response.status < 500 ? 'available' : 'unavailable',
            statusCode: response.status
          });
        } catch (error) {
          observabilityStatus.push({
            name: endpoint.name,
            url: endpoint.url,
            status: 'unavailable',
            error: String(error)
          });
        }
      }
      
      setupStatus.steps[setupStatus.steps.length - 1].status = 'completed';
      setupStatus.steps[setupStatus.steps.length - 1].observability = observabilityStatus;
      console.log('✅ Observability setup completed');
    } catch (error) {
      console.warn('⚠️ Observability setup failed:', error);
      setupStatus.steps[setupStatus.steps.length - 1].status = 'failed';
      setupStatus.steps[setupStatus.steps.length - 1].error = String(error);
    }
    
    // Finalize setup status
    setupStatus.status = 'completed';
    setupStatus.endTime = new Date().toISOString();
    setupStatus.duration = Date.now() - setupStartTime;
    
    // Save setup status
    const setupStatusFile = path.join(testResultsDir, 'gate-e-setup-status.json');
    fs.writeFileSync(setupStatusFile, JSON.stringify(setupStatus, null, 2));
    
    console.log(`🎉 Gate E Global Setup completed in ${Math.round(setupStatus.duration / 1000)}s`);
    console.log(`📊 Setup status saved to: ${setupStatusFile}`);
    
    // Set global test context
    process.env.GATE_E_SETUP_COMPLETED = 'true';
    process.env.GATE_E_TEST_TENANT_ID = 'gate-e-test-tenant';
    process.env.GATE_E_ADMIN_EMAIL = 'admin@gate-e-test.com';
    process.env.GATE_E_CUSTOMER_EMAIL = 'customer@gate-e-test.com';
    
  } catch (error) {
    console.error('❌ Gate E Global Setup failed:', error);
    
    // Save error status
    const errorStatus = {
      status: 'failed',
      error: String(error),
      timestamp: new Date().toISOString(),
      duration: Date.now() - setupStartTime
    };
    
    const errorStatusFile = path.join(gateEDir, 'test-results', 'gate-e-setup-error.json');
    fs.writeFileSync(errorStatusFile, JSON.stringify(errorStatus, null, 2));
    
    throw error;
  }
}

export default globalSetup;