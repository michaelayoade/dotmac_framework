/**
 * Workflow Performance Baseline E2E Tests
 * Tests performance benchmarks, load handling, and optimization for workflow systems
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';

test.describe('Workflow Performance Baselines', () => {
  test.describe.configure({ mode: 'serial' });

  let adminPage: Page;
  let performanceMetrics: Record<string, number> = {};

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    adminPage = await context.newPage();
    await setupAuth(adminPage, 'admin');

    // Setup performance monitoring
    await adminPage.addInitScript(() => {
      window.performanceData = [];
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          window.performanceData.push({
            name: entry.name,
            duration: entry.duration,
            startTime: entry.startTime,
            type: entry.entryType,
          });
        });
      });
      observer.observe({ entryTypes: ['navigation', 'measure', 'mark'] });
    });
  });

  test('workflow designer performance baseline', async () => {
    // Test Visual Workflow Designer performance under normal load

    const startTime = Date.now();

    await adminPage.goto('/admin/workflow-designer');
    await expect(adminPage.locator('[data-testid="workflow-designer"]')).toBeVisible();

    const loadTime = Date.now() - startTime;
    performanceMetrics.designerLoad = loadTime;

    // Baseline: Designer should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);

    // Test workflow creation performance
    const workflowCreationStart = Date.now();

    await adminPage.click('[data-testid="new-workflow-btn"]');
    await adminPage.fill('[data-testid="workflow-name"]', 'Performance Test Workflow');

    // Add 10 steps to test complex workflow handling
    const stepTypes = ['form', 'approval', 'action', 'conditional', 'notification'];

    for (let i = 0; i < 10; i++) {
      const stepType = stepTypes[i % stepTypes.length];
      const stepStart = Date.now();

      await adminPage.click(`[data-testid="add-step-${stepType}"]`);
      await adminPage.fill(`[data-testid="step-title-${i}"]`, `Performance Step ${i + 1}`);

      // Configure step based on type
      switch (stepType) {
        case 'form':
          await adminPage.click('[data-testid="add-field-btn"]');
          await adminPage.fill('[data-testid="field-label"]', `Field ${i + 1}`);
          await adminPage.selectOption('[data-testid="field-type"]', 'text');
          break;
        case 'approval':
          await adminPage.selectOption('[data-testid="approver-role"]', 'admin');
          break;
        case 'action':
          await adminPage.selectOption('[data-testid="action-type"]', 'send_notification');
          break;
        case 'conditional':
          await adminPage.fill('[data-testid="condition-field"]', 'test_field');
          await adminPage.selectOption('[data-testid="condition-operator"]', 'equals');
          await adminPage.fill('[data-testid="condition-value"]', 'test_value');
          break;
      }

      const stepDuration = Date.now() - stepStart;
      performanceMetrics[`step${i + 1}Creation`] = stepDuration;

      // Baseline: Each step should be created within 500ms
      expect(stepDuration).toBeLessThan(500);
    }

    // Test workflow validation performance
    const validationStart = Date.now();
    await adminPage.click('[data-testid="validate-workflow"]');
    await expect(adminPage.locator('[data-testid="validation-success"]')).toBeVisible();

    const validationTime = Date.now() - validationStart;
    performanceMetrics.workflowValidation = validationTime;

    // Baseline: Validation should complete within 2 seconds
    expect(validationTime).toBeLessThan(2000);

    // Test workflow save performance
    const saveStart = Date.now();
    await adminPage.click('[data-testid="save-workflow"]');
    await expect(adminPage.locator('[data-testid="save-success"]')).toBeVisible();

    const saveTime = Date.now() - saveStart;
    performanceMetrics.workflowSave = saveTime;

    // Baseline: Save should complete within 1 second
    expect(saveTime).toBeLessThan(1000);

    const totalCreationTime = Date.now() - workflowCreationStart;
    performanceMetrics.totalWorkflowCreation = totalCreationTime;

    // Baseline: Complete workflow creation should finish within 15 seconds
    expect(totalCreationTime).toBeLessThan(15000);
  });

  test('workflow execution performance under load', async () => {
    // Test workflow execution performance with concurrent workflows

    await adminPage.goto('/admin/workflows/load-testing');

    // Setup concurrent workflow execution test
    await adminPage.fill('[data-testid="concurrent-workflows"]', '20');
    await adminPage.selectOption('[data-testid="workflow-template"]', 'customer_onboarding');
    await adminPage.check('[data-testid="enable-metrics-collection"]');

    const loadTestStart = Date.now();
    await adminPage.click('[data-testid="start-load-test"]');

    // Monitor execution progress
    await expect(adminPage.locator('[data-testid="load-test-running"]')).toBeVisible();

    // Wait for test completion
    await expect(adminPage.locator('[data-testid="load-test-completed"]')).toBeVisible({
      timeout: 60000,
    });

    const loadTestTime = Date.now() - loadTestStart;
    performanceMetrics.concurrentWorkflowExecution = loadTestTime;

    // Collect performance metrics
    const successRate = await adminPage.locator('[data-testid="success-rate"]').textContent();
    const avgExecutionTime = await adminPage
      .locator('[data-testid="avg-execution-time"]')
      .textContent();
    const maxExecutionTime = await adminPage
      .locator('[data-testid="max-execution-time"]')
      .textContent();
    const throughput = await adminPage.locator('[data-testid="throughput"]').textContent();

    // Performance baselines
    expect(Number(successRate?.replace('%', ''))).toBeGreaterThanOrEqual(99); // 99% success rate
    expect(Number(avgExecutionTime?.replace('ms', ''))).toBeLessThan(5000); // Avg under 5 seconds
    expect(Number(maxExecutionTime?.replace('ms', ''))).toBeLessThan(10000); // Max under 10 seconds
    expect(Number(throughput?.split(' ')[0])).toBeGreaterThanOrEqual(2); // At least 2 workflows/second

    performanceMetrics.workflowSuccessRate = Number(successRate?.replace('%', '') || 0);
    performanceMetrics.avgWorkflowExecution = Number(avgExecutionTime?.replace('ms', '') || 0);
    performanceMetrics.maxWorkflowExecution = Number(maxExecutionTime?.replace('ms', '') || 0);
    performanceMetrics.workflowThroughput = Number(throughput?.split(' ')[0] || 0);
  });

  test('real-time data sync performance', async () => {
    // Test real-time synchronization performance across multiple portals

    await adminPage.goto('/admin/performance/websocket-test');

    // Setup WebSocket performance monitoring
    await adminPage.fill('[data-testid="concurrent-connections"]', '100');
    await adminPage.fill('[data-testid="messages-per-connection"]', '50');
    await adminPage.fill('[data-testid="message-size"]', '1024'); // 1KB messages

    const wsTestStart = Date.now();
    await adminPage.click('[data-testid="start-websocket-test"]');

    // Monitor WebSocket performance
    await expect(adminPage.locator('[data-testid="websocket-test-running"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="websocket-test-completed"]')).toBeVisible({
      timeout: 30000,
    });

    const wsTestTime = Date.now() - wsTestStart;
    performanceMetrics.websocketTest = wsTestTime;

    // Collect WebSocket metrics
    const connectionTime = await adminPage
      .locator('[data-testid="avg-connection-time"]')
      .textContent();
    const messageLatency = await adminPage
      .locator('[data-testid="avg-message-latency"]')
      .textContent();
    const messagesPerSecond = await adminPage
      .locator('[data-testid="messages-per-second"]')
      .textContent();
    const failedConnections = await adminPage
      .locator('[data-testid="failed-connections"]')
      .textContent();

    // WebSocket performance baselines
    expect(Number(connectionTime?.replace('ms', ''))).toBeLessThan(500); // Connection under 500ms
    expect(Number(messageLatency?.replace('ms', ''))).toBeLessThan(100); // Message latency under 100ms
    expect(Number(messagesPerSecond)).toBeGreaterThanOrEqual(100); // At least 100 messages/second
    expect(Number(failedConnections)).toBeLessThanOrEqual(1); // Max 1% connection failures

    performanceMetrics.websocketConnectionTime = Number(connectionTime?.replace('ms', '') || 0);
    performanceMetrics.websocketLatency = Number(messageLatency?.replace('ms', '') || 0);
    performanceMetrics.websocketThroughput = Number(messagesPerSecond || 0);
  });

  test('database query performance for workflows', async () => {
    // Test database performance under workflow load

    await adminPage.goto('/admin/performance/database-test');

    // Setup database performance test
    await adminPage.fill('[data-testid="concurrent-queries"]', '50');
    await adminPage.fill('[data-testid="query-complexity"]', 'medium');
    await adminPage.check('[data-testid="include-joins"]');
    await adminPage.check('[data-testid="include-aggregations"]');

    const dbTestStart = Date.now();
    await adminPage.click('[data-testid="start-database-test"]');

    await expect(adminPage.locator('[data-testid="database-test-running"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="database-test-completed"]')).toBeVisible({
      timeout: 45000,
    });

    const dbTestTime = Date.now() - dbTestStart;
    performanceMetrics.databaseTest = dbTestTime;

    // Collect database metrics
    const avgQueryTime = await adminPage.locator('[data-testid="avg-query-time"]').textContent();
    const slowQueries = await adminPage.locator('[data-testid="slow-queries"]').textContent();
    const queriesPerSecond = await adminPage
      .locator('[data-testid="queries-per-second"]')
      .textContent();
    const cacheHitRate = await adminPage.locator('[data-testid="cache-hit-rate"]').textContent();

    // Database performance baselines
    expect(Number(avgQueryTime?.replace('ms', ''))).toBeLessThan(100); // Avg query under 100ms
    expect(Number(slowQueries)).toBeLessThanOrEqual(2); // Max 2 slow queries (>1s)
    expect(Number(queriesPerSecond)).toBeGreaterThanOrEqual(20); // At least 20 queries/second
    expect(Number(cacheHitRate?.replace('%', ''))).toBeGreaterThanOrEqual(80); // 80% cache hit rate

    performanceMetrics.avgQueryTime = Number(avgQueryTime?.replace('ms', '') || 0);
    performanceMetrics.databaseThroughput = Number(queriesPerSecond || 0);
    performanceMetrics.cacheHitRate = Number(cacheHitRate?.replace('%', '') || 0);
  });

  test('memory usage and optimization', async () => {
    // Test memory usage during workflow operations

    await adminPage.goto('/admin/performance/memory-test');

    // Get initial memory usage
    const initialMemory = await adminPage.evaluate(() => {
      return (performance as any).memory
        ? {
            used: (performance as any).memory.usedJSHeapSize,
            total: (performance as any).memory.totalJSHeapSize,
          }
        : { used: 0, total: 0 };
    });

    // Create complex workflow that might cause memory issues
    await adminPage.click('[data-testid="create-complex-workflow"]');
    await adminPage.fill('[data-testid="workflow-steps"]', '100');
    await adminPage.fill('[data-testid="fields-per-step"]', '20');
    await adminPage.check('[data-testid="include-validations"]');

    const complexWorkflowStart = Date.now();
    await adminPage.click('[data-testid="generate-workflow"]');
    await expect(adminPage.locator('[data-testid="workflow-generated"]')).toBeVisible({
      timeout: 30000,
    });

    const complexWorkflowTime = Date.now() - complexWorkflowStart;
    performanceMetrics.complexWorkflowGeneration = complexWorkflowTime;

    // Check memory usage after complex operation
    const peakMemory = await adminPage.evaluate(() => {
      return (performance as any).memory
        ? {
            used: (performance as any).memory.usedJSHeapSize,
            total: (performance as any).memory.totalJSHeapSize,
          }
        : { used: 0, total: 0 };
    });

    const memoryIncrease = peakMemory.used - initialMemory.used;
    performanceMetrics.memoryIncrease = memoryIncrease;

    // Memory baseline: Should not increase by more than 50MB for complex workflow
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);

    // Test memory cleanup
    await adminPage.click('[data-testid="clear-workflow"]');
    await adminPage.waitForTimeout(2000); // Allow time for garbage collection

    const finalMemory = await adminPage.evaluate(() => {
      if (window.gc) {
        window.gc(); // Force garbage collection if available
      }
      return (performance as any).memory
        ? {
            used: (performance as any).memory.usedJSHeapSize,
            total: (performance as any).memory.totalJSHeapSize,
          }
        : { used: 0, total: 0 };
    });

    const memoryReclaimed = peakMemory.used - finalMemory.used;
    performanceMetrics.memoryReclaimed = memoryReclaimed;

    // Should reclaim at least 50% of the memory increase
    expect(memoryReclaimed).toBeGreaterThan(memoryIncrease * 0.5);
  });

  test('frontend bundle size and loading performance', async () => {
    // Test frontend performance and bundle optimization

    await adminPage.goto('/admin/performance/bundle-analysis');

    // Get bundle size information
    const bundleMetrics = await adminPage.evaluate(() => {
      const entries = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: entries.domContentLoadedEventEnd - entries.domContentLoadedEventStart,
        loadComplete: entries.loadEventEnd - entries.loadEventStart,
        firstContentfulPaint: 0, // Will be populated by performance observer
        largestContentfulPaint: 0,
      };
    });

    // Get paint metrics
    const paintMetrics = await adminPage.evaluate(() => {
      const paintEntries = performance.getEntriesByType('paint');
      const fcpEntry = paintEntries.find((entry) => entry.name === 'first-contentful-paint');
      return {
        firstContentfulPaint: fcpEntry ? fcpEntry.startTime : 0,
      };
    });

    performanceMetrics.domContentLoaded = bundleMetrics.domContentLoaded;
    performanceMetrics.loadComplete = bundleMetrics.loadComplete;
    performanceMetrics.firstContentfulPaint = paintMetrics.firstContentfulPaint;

    // Frontend performance baselines
    expect(bundleMetrics.domContentLoaded).toBeLessThan(2000); // DOM loaded within 2s
    expect(bundleMetrics.loadComplete).toBeLessThan(5000); // Complete load within 5s
    expect(paintMetrics.firstContentfulPaint).toBeLessThan(1500); // FCP within 1.5s

    // Test code splitting effectiveness
    await adminPage.click('[data-testid="load-secondary-features"]');

    const secondaryLoadStart = Date.now();
    await expect(adminPage.locator('[data-testid="secondary-features-loaded"]')).toBeVisible({
      timeout: 3000,
    });
    const secondaryLoadTime = Date.now() - secondaryLoadStart;

    performanceMetrics.secondaryFeatureLoad = secondaryLoadTime;

    // Secondary features should load quickly (code splitting working)
    expect(secondaryLoadTime).toBeLessThan(1000);
  });

  test.afterAll(async () => {
    // Generate performance report
    console.log('=== Workflow Performance Baseline Report ===');
    console.log(`Designer Load Time: ${performanceMetrics.designerLoad}ms`);
    console.log(`Workflow Creation Time: ${performanceMetrics.totalWorkflowCreation}ms`);
    console.log(`Workflow Validation Time: ${performanceMetrics.workflowValidation}ms`);
    console.log(`Workflow Save Time: ${performanceMetrics.workflowSave}ms`);
    console.log(`Concurrent Workflow Success Rate: ${performanceMetrics.workflowSuccessRate}%`);
    console.log(`Average Workflow Execution: ${performanceMetrics.avgWorkflowExecution}ms`);
    console.log(`Workflow Throughput: ${performanceMetrics.workflowThroughput} workflows/sec`);
    console.log(`WebSocket Connection Time: ${performanceMetrics.websocketConnectionTime}ms`);
    console.log(`WebSocket Message Latency: ${performanceMetrics.websocketLatency}ms`);
    console.log(`Database Average Query Time: ${performanceMetrics.avgQueryTime}ms`);
    console.log(`Database Cache Hit Rate: ${performanceMetrics.cacheHitRate}%`);
    console.log(
      `Memory Usage Increase: ${Math.round(performanceMetrics.memoryIncrease / 1024 / 1024)}MB`
    );
    console.log(`First Contentful Paint: ${performanceMetrics.firstContentfulPaint}ms`);

    // Write performance data to file for CI/CD tracking
    await adminPage.evaluate((metrics) => {
      const reportData = {
        timestamp: new Date().toISOString(),
        testRun: 'workflow-automation-performance',
        metrics: metrics,
        baselines: {
          designerLoadMax: 3000,
          workflowCreationMax: 15000,
          workflowSuccessRateMin: 99,
          avgExecutionMax: 5000,
          websocketLatencyMax: 100,
          queryTimeMax: 100,
          cacheHitRateMin: 80,
          firstContentfulPaintMax: 1500,
        },
      };

      // In a real scenario, this would send to monitoring system
      console.log('Performance Report:', JSON.stringify(reportData, null, 2));
    }, performanceMetrics);

    await adminPage.context().close();
  });
});
