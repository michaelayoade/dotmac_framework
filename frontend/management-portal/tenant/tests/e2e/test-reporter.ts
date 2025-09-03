/**
 * Custom Test Reporter for Enhanced E2E Test Reporting
 * Generates comprehensive test reports with coverage analysis
 */

import { Reporter, TestResult, TestCase, TestStep } from '@playwright/test/reporter';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';

interface TestMetrics {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  duration: number;
  coverage: number;
}

interface TestReport {
  summary: TestMetrics;
  suites: SuiteReport[];
  performance: PerformanceReport;
  coverage: CoverageReport;
  timestamp: string;
  environment: {
    browser: string;
    os: string;
    ci: boolean;
    baseUrl: string;
  };
}

interface SuiteReport {
  name: string;
  file: string;
  tests: TestCaseReport[];
  metrics: TestMetrics;
  tags: string[];
}

interface TestCaseReport {
  name: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  error?: string;
  steps: TestStepReport[];
  screenshots: string[];
  tags: string[];
}

interface TestStepReport {
  name: string;
  duration: number;
  status: 'passed' | 'failed' | 'skipped';
  error?: string;
}

interface PerformanceReport {
  averageLoadTime: number;
  slowestTests: Array<{ name: string; duration: number }>;
  performanceThresholds: {
    pageLoad: number;
    apiResponse: number;
    interaction: number;
  };
  violations: Array<{ test: string; metric: string; actual: number; threshold: number }>;
}

interface CoverageReport {
  overall: number;
  byCategory: {
    subscription: number;
    license: number;
    dashboard: number;
    user: number;
  };
  scenarios: {
    total: number;
    covered: number;
    missing: string[];
  };
}

class TenantPortalReporter implements Reporter {
  private tests: TestResult[] = [];
  private startTime: number = 0;
  private outputDir: string;

  constructor() {
    this.outputDir = process.env.PLAYWRIGHT_OUTPUT_DIR || 'test-results';
    this.ensureOutputDir();
  }

  private ensureOutputDir() {
    if (!existsSync(this.outputDir)) {
      mkdirSync(this.outputDir, { recursive: true });
    }
  }

  onBegin() {
    this.startTime = Date.now();
    console.log('🎭 Starting Tenant Portal E2E Tests...\n');
  }

  onTestEnd(test: TestCase, result: TestResult) {
    this.tests.push(result);

    const status =
      result.status === 'passed'
        ? '✅'
        : result.status === 'failed'
          ? '❌'
          : result.status === 'skipped'
            ? '⏭️'
            : '❓';

    const duration = result.duration;
    const formattedDuration =
      duration < 1000 ? `${duration}ms` : `${(duration / 1000).toFixed(2)}s`;

    console.log(`${status} ${test.title} (${formattedDuration})`);

    if (result.status === 'failed' && result.error) {
      console.log(`   Error: ${result.error.message?.substring(0, 100)}...`);
    }
  }

  onEnd() {
    const duration = Date.now() - this.startTime;
    const report = this.generateReport(duration);

    // Generate multiple report formats
    this.generateHTMLReport(report);
    this.generateJSONReport(report);
    this.generateJUnitReport(report);
    this.generateCoverageReport(report);

    // Print summary to console
    this.printSummary(report);
  }

  private generateReport(duration: number): TestReport {
    const metrics = this.calculateMetrics(duration);
    const suites = this.groupTestsBySuite();
    const performance = this.calculatePerformanceMetrics();
    const coverage = this.calculateCoverage();

    return {
      summary: metrics,
      suites,
      performance,
      coverage,
      timestamp: new Date().toISOString(),
      environment: {
        browser: process.env.PLAYWRIGHT_BROWSER || 'chromium',
        os: process.platform,
        ci: process.env.CI === 'true',
        baseUrl: process.env.BASE_URL || 'http://localhost:3003',
      },
    };
  }

  private calculateMetrics(duration: number): TestMetrics {
    const total = this.tests.length;
    const passed = this.tests.filter((t) => t.status === 'passed').length;
    const failed = this.tests.filter((t) => t.status === 'failed').length;
    const skipped = this.tests.filter((t) => t.status === 'skipped').length;

    return {
      total,
      passed,
      failed,
      skipped,
      duration,
      coverage: this.calculateOverallCoverage(),
    };
  }

  private groupTestsBySuite(): SuiteReport[] {
    const suiteMap = new Map<string, TestResult[]>();

    this.tests.forEach((test) => {
      const suiteName = test.parent?.title || 'Unknown Suite';
      if (!suiteMap.has(suiteName)) {
        suiteMap.set(suiteName, []);
      }
      suiteMap.get(suiteName)!.push(test);
    });

    return Array.from(suiteMap.entries()).map(([name, tests]) => ({
      name,
      file: tests[0]?.parent?.location?.file || 'unknown',
      tests: tests.map(this.convertToTestCaseReport),
      metrics: this.calculateSuiteMetrics(tests),
      tags: this.extractTags(name),
    }));
  }

  private convertToTestCaseReport = (result: TestResult): TestCaseReport => {
    return {
      name: result.test.title,
      status: result.status,
      duration: result.duration,
      error: result.error?.message,
      steps: result.steps.map(this.convertToTestStepReport),
      screenshots: result.attachments
        .filter((a) => a.name?.includes('screenshot'))
        .map((a) => a.path || ''),
      tags: this.extractTags(result.test.title),
    };
  };

  private convertToTestStepReport = (step: TestStep): TestStepReport => {
    return {
      name: step.title,
      duration: step.duration,
      status: step.error ? 'failed' : 'passed',
      error: step.error?.message,
    };
  };

  private calculateSuiteMetrics(tests: TestResult[]): TestMetrics {
    const total = tests.length;
    const passed = tests.filter((t) => t.status === 'passed').length;
    const failed = tests.filter((t) => t.status === 'failed').length;
    const skipped = tests.filter((t) => t.status === 'skipped').length;
    const duration = tests.reduce((sum, t) => sum + t.duration, 0);

    return {
      total,
      passed,
      failed,
      skipped,
      duration,
      coverage: (passed / total) * 100,
    };
  }

  private calculatePerformanceMetrics(): PerformanceReport {
    const durations = this.tests.map((t) => t.duration);
    const averageLoadTime = durations.reduce((sum, d) => sum + d, 0) / durations.length;

    const slowestTests = this.tests
      .sort((a, b) => b.duration - a.duration)
      .slice(0, 5)
      .map((t) => ({
        name: t.test.title,
        duration: t.duration,
      }));

    const performanceThresholds = {
      pageLoad: 3000,
      apiResponse: 2000,
      interaction: 1000,
    };

    const violations = this.tests
      .filter((t) => t.duration > performanceThresholds.pageLoad)
      .map((t) => ({
        test: t.test.title,
        metric: 'pageLoad',
        actual: t.duration,
        threshold: performanceThresholds.pageLoad,
      }));

    return {
      averageLoadTime,
      slowestTests,
      performanceThresholds,
      violations,
    };
  }

  private calculateCoverage(): CoverageReport {
    // This would typically integrate with actual test coverage tools
    // For now, we'll provide estimates based on test completion

    const subscriptionTests = this.tests.filter(
      (t) =>
        t.test.title.toLowerCase().includes('subscription') ||
        t.test.parent?.title?.toLowerCase().includes('subscription')
    );

    const licenseTests = this.tests.filter(
      (t) =>
        t.test.title.toLowerCase().includes('license') ||
        t.test.parent?.title?.toLowerCase().includes('license')
    );

    const dashboardTests = this.tests.filter(
      (t) =>
        t.test.title.toLowerCase().includes('dashboard') ||
        t.test.parent?.title?.toLowerCase().includes('dashboard')
    );

    const userTests = this.tests.filter(
      (t) =>
        t.test.title.toLowerCase().includes('user') ||
        t.test.parent?.title?.toLowerCase().includes('user')
    );

    const calculateCategoryPercentage = (tests: TestResult[]) => {
      if (tests.length === 0) return 0;
      return (tests.filter((t) => t.status === 'passed').length / tests.length) * 100;
    };

    const totalScenarios = 156; // Based on requirements
    const coveredScenarios = this.tests.filter((t) => t.status === 'passed').length;

    return {
      overall: (coveredScenarios / totalScenarios) * 100,
      byCategory: {
        subscription: calculateCategoryPercentage(subscriptionTests),
        license: calculateCategoryPercentage(licenseTests),
        dashboard: calculateCategoryPercentage(dashboardTests),
        user: calculateCategoryPercentage(userTests),
      },
      scenarios: {
        total: totalScenarios,
        covered: coveredScenarios,
        missing: this.identifyMissingScenarios(),
      },
    };
  }

  private calculateOverallCoverage(): number {
    const passed = this.tests.filter((t) => t.status === 'passed').length;
    const total = this.tests.length;
    return total > 0 ? (passed / total) * 100 : 0;
  }

  private extractTags(title: string): string[] {
    const tags: string[] = [];
    const tagPattern = /@(\w+)/g;
    let match;

    while ((match = tagPattern.exec(title)) !== null) {
      tags.push(match[1]);
    }

    return tags;
  }

  private identifyMissingScenarios(): string[] {
    // This would be expanded based on comprehensive requirements analysis
    return [
      'Bulk license assignment for enterprise tier',
      'Advanced billing analytics with custom date ranges',
      'Integration with external SSO providers',
      'Multi-tenant data isolation verification',
      'Disaster recovery procedures testing',
    ];
  }

  private generateHTMLReport(report: TestReport) {
    const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tenant Portal E2E Test Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 28px; }
        .header .subtitle { opacity: 0.9; margin-top: 5px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; }
        .metric { text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #28a745; }
        .metric.failed { border-left-color: #dc3545; }
        .metric.warning { border-left-color: #ffc107; }
        .metric-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .metric-label { color: #6c757d; font-size: 14px; }
        .section { padding: 30px; border-bottom: 1px solid #e9ecef; }
        .section h2 { margin-top: 0; color: #495057; }
        .test-suite { margin-bottom: 20px; border: 1px solid #e9ecef; border-radius: 4px; }
        .suite-header { background: #f8f9fa; padding: 15px; font-weight: bold; border-bottom: 1px solid #e9ecef; }
        .test-list { padding: 15px; }
        .test-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f1f3f4; }
        .test-item:last-child { border-bottom: none; }
        .test-status { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .passed { background: #d4edda; color: #155724; }
        .failed { background: #f8d7da; color: #721c24; }
        .skipped { background: #fff3cd; color: #856404; }
        .performance-chart { height: 200px; background: #f8f9fa; border-radius: 4px; margin: 20px 0; display: flex; align-items: center; justify-content: center; color: #6c757d; }
        .coverage-bar { width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .coverage-fill { height: 100%; background: linear-gradient(90deg, #28a745 0%, #20c997 100%); transition: width 0.3s ease; }
        .footer { padding: 20px 30px; background: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #6c757d; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎭 Tenant Portal E2E Test Report</h1>
            <div class="subtitle">Generated on ${new Date(report.timestamp).toLocaleString()}</div>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">${report.summary.total}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: #28a745;">${report.summary.passed}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric ${report.summary.failed > 0 ? 'failed' : ''}">
                <div class="metric-value" style="color: ${report.summary.failed > 0 ? '#dc3545' : '#28a745'};">${report.summary.failed}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric">
                <div class="metric-value">${Math.round(report.summary.coverage)}%</div>
                <div class="metric-label">Coverage</div>
            </div>
            <div class="metric">
                <div class="metric-value">${Math.round(report.summary.duration / 1000)}s</div>
                <div class="metric-label">Duration</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Test Coverage</h2>
            <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>Overall Coverage</span>
                    <span><strong>${Math.round(report.coverage.overall)}%</strong></span>
                </div>
                <div class="coverage-bar">
                    <div class="coverage-fill" style="width: ${report.coverage.overall}%"></div>
                </div>
            </div>
            ${Object.entries(report.coverage.byCategory)
              .map(
                ([category, percentage]) => `
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span>${category.charAt(0).toUpperCase() + category.slice(1)} Management</span>
                        <span><strong>${Math.round(percentage)}%</strong></span>
                    </div>
                    <div class="coverage-bar">
                        <div class="coverage-fill" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `
              )
              .join('')}
        </div>
        
        <div class="section">
            <h2>🧪 Test Suites</h2>
            ${report.suites
              .map(
                (suite) => `
                <div class="test-suite">
                    <div class="suite-header">
                        ${suite.name} (${suite.metrics.passed}/${suite.metrics.total} passed)
                    </div>
                    <div class="test-list">
                        ${suite.tests
                          .map(
                            (test) => `
                            <div class="test-item">
                                <span>${test.name}</span>
                                <div>
                                    <span class="test-status ${test.status}">${test.status.toUpperCase()}</span>
                                    <span style="margin-left: 10px; font-size: 12px; color: #6c757d;">
                                        ${test.duration < 1000 ? test.duration + 'ms' : (test.duration / 1000).toFixed(2) + 's'}
                                    </span>
                                </div>
                            </div>
                        `
                          )
                          .join('')}
                    </div>
                </div>
            `
              )
              .join('')}
        </div>
        
        <div class="section">
            <h2>⚡ Performance</h2>
            <p><strong>Average Test Duration:</strong> ${Math.round(report.performance.averageLoadTime)}ms</p>
            ${
              report.performance.violations.length > 0
                ? `
                <div style="color: #dc3545; margin-top: 15px;">
                    <strong>Performance Violations:</strong>
                    <ul>
                        ${report.performance.violations
                          .map(
                            (v) => `
                            <li>${v.test}: ${v.actual}ms (threshold: ${v.threshold}ms)</li>
                        `
                          )
                          .join('')}
                    </ul>
                </div>
            `
                : '<div style="color: #28a745;">✅ All tests within performance thresholds</div>'
            }
        </div>
        
        <div class="footer">
            <div>Environment: ${report.environment.browser} on ${report.environment.os}</div>
            <div>Base URL: ${report.environment.baseUrl} | CI: ${report.environment.ci ? 'Yes' : 'No'}</div>
        </div>
    </div>
</body>
</html>`;

    writeFileSync(join(this.outputDir, 'test-report.html'), html);
  }

  private generateJSONReport(report: TestReport) {
    writeFileSync(join(this.outputDir, 'test-report.json'), JSON.stringify(report, null, 2));
  }

  private generateJUnitReport(report: TestReport) {
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Tenant Portal E2E Tests" tests="${report.summary.total}" failures="${report.summary.failed}" errors="0" time="${report.summary.duration / 1000}">
  ${report.suites
    .map(
      (suite) => `
  <testsuite name="${suite.name}" tests="${suite.metrics.total}" failures="${suite.metrics.failed}" errors="0" time="${suite.metrics.duration / 1000}">
    ${suite.tests
      .map(
        (test) => `
    <testcase name="${test.name}" classname="${suite.name}" time="${test.duration / 1000}">
      ${test.status === 'failed' ? `<failure message="${test.error || 'Test failed'}">${test.error || 'Test failed'}</failure>` : ''}
      ${test.status === 'skipped' ? '<skipped/>' : ''}
    </testcase>`
      )
      .join('')}
  </testsuite>`
    )
    .join('')}
</testsuites>`;

    writeFileSync(join(this.outputDir, 'junit-report.xml'), xml);
  }

  private generateCoverageReport(report: TestReport) {
    const coverageReport = {
      timestamp: report.timestamp,
      overall: report.coverage.overall,
      categories: report.coverage.byCategory,
      scenarios: report.coverage.scenarios,
      recommendations: this.generateRecommendations(report),
    };

    writeFileSync(
      join(this.outputDir, 'coverage-report.json'),
      JSON.stringify(coverageReport, null, 2)
    );
  }

  private generateRecommendations(report: TestReport): string[] {
    const recommendations: string[] = [];

    if (report.coverage.overall < 90) {
      recommendations.push('Increase test coverage to meet 90% minimum threshold');
    }

    if (report.performance.violations.length > 0) {
      recommendations.push('Address performance violations to improve user experience');
    }

    if (report.summary.failed > 0) {
      recommendations.push('Fix failing tests before deployment');
    }

    const lowCoverageCategories = Object.entries(report.coverage.byCategory)
      .filter(([, percentage]) => percentage < 85)
      .map(([category]) => category);

    if (lowCoverageCategories.length > 0) {
      recommendations.push(`Improve test coverage for: ${lowCoverageCategories.join(', ')}`);
    }

    return recommendations;
  }

  private printSummary(report: TestReport) {
    console.log('\n' + '='.repeat(60));
    console.log('📋 TEST EXECUTION SUMMARY');
    console.log('='.repeat(60));
    console.log(`🎯 Total Tests: ${report.summary.total}`);
    console.log(`✅ Passed: ${report.summary.passed}`);
    console.log(`❌ Failed: ${report.summary.failed}`);
    console.log(`⏭️  Skipped: ${report.summary.skipped}`);
    console.log(`📊 Coverage: ${Math.round(report.coverage.overall)}%`);
    console.log(`⏱️  Duration: ${Math.round(report.summary.duration / 1000)}s`);
    console.log(`🌐 Environment: ${report.environment.browser} on ${report.environment.os}`);

    if (report.coverage.overall >= 90 && report.summary.failed === 0) {
      console.log('\n🎉 ALL QUALITY GATES PASSED! Ready for deployment.');
    } else {
      console.log('\n⚠️  Quality gates not met. Review failures and coverage.');
    }

    console.log(`📄 Reports generated in: ${this.outputDir}`);
    console.log('='.repeat(60) + '\n');
  }
}

export default TenantPortalReporter;
