/**
 * Custom License Compliance Reporter for Playwright
 * 
 * Generates specialized reports for license enforcement validation
 * and compliance verification across multi-app platform.
 */

import type {
  FullConfig, FullResult, Reporter, Suite, TestCase, TestResult
} from '@playwright/test/reporter';
import * as fs from 'fs/promises';
import * as path from 'path';

interface LicenseTestResult {
  testId: string;
  title: string;
  feature: string;
  licenseType: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  error?: string;
  apps: string[];
  complianceStatus: 'compliant' | 'violation' | 'warning';
  details: {
    featureAccess: { [app: string]: boolean };
    permissionChecks: { [permission: string]: boolean };
    auditTrail: boolean;
    realTimeUpdates: boolean;
  };
}

interface LicenseComplianceReport {
  summary: {
    totalTests: number;
    passed: number;
    failed: number;
    skipped: number;
    complianceScore: number;
    criticalViolations: number;
    warnings: number;
  };
  licenseTypes: {
    [type: string]: {
      tests: number;
      passed: number;
      complianceRate: number;
    };
  };
  featureCoverage: {
    [feature: string]: {
      tested: boolean;
      compliant: boolean;
      apps: string[];
    };
  };
  crossAppConsistency: {
    [app: string]: {
      tests: number;
      passed: number;
      consistencyScore: number;
    };
  };
  violations: LicenseTestResult[];
  results: LicenseTestResult[];
  timestamp: string;
  testDuration: number;
}

export class LicenseComplianceReporter implements Reporter {
  private results: LicenseTestResult[] = [];
  private startTime: number = 0;
  private config: FullConfig | null = null;

  onBegin(config: FullConfig, suite: Suite) {
    this.config = config;
    this.startTime = Date.now();
    console.log(`🔐 Starting License Compliance Validation...`);
    console.log(`📊 Testing ${this.countTests(suite)} license enforcement scenarios`);
  }

  onTestEnd(test: TestCase, result: TestResult) {
    const licenseResult = this.extractLicenseTestData(test, result);
    this.results.push(licenseResult);
    
    // Real-time compliance feedback
    if (licenseResult.complianceStatus === 'violation') {
      console.log(`❌ COMPLIANCE VIOLATION: ${licenseResult.title}`);
    } else if (licenseResult.complianceStatus === 'warning') {
      console.log(`⚠️  COMPLIANCE WARNING: ${licenseResult.title}`);
    } else {
      console.log(`✅ COMPLIANT: ${licenseResult.title}`);
    }
  }

  async onEnd(result: FullResult) {
    const duration = Date.now() - this.startTime;
    const report = this.generateComplianceReport(duration);
    
    await this.saveReport(report);
    await this.generateSummaryReport(report);
    
    // Console summary
    this.printComplianceSummary(report);
  }

  private extractLicenseTestData(test: TestCase, result: TestResult): LicenseTestResult {
    const title = test.title;
    const testId = test.id;
    
    // Extract test metadata from title and annotations
    const feature = this.extractFeature(title);
    const licenseType = this.extractLicenseType(title);
    const apps = this.extractApps(title);
    
    // Determine compliance status based on test results and title
    const complianceStatus = this.determineComplianceStatus(result, title);
    
    // Extract detailed results from test steps if available
    const details = this.extractTestDetails(result);

    return {
      testId,
      title,
      feature,
      licenseType,
      status: result.status as 'passed' | 'failed' | 'skipped',
      duration: result.duration,
      error: result.error?.message,
      apps,
      complianceStatus,
      details
    };
  }

  private extractFeature(title: string): string {
    // Extract feature being tested from test title
    const patterns = [
      /access to ([\w\s]+) feature/i,
      /feature.*([\w]+).*(enforcement|access)/i,
      /(sso|analytics|api|billing|crm)/i
    ];
    
    for (const pattern of patterns) {
      const match = title.match(pattern);
      if (match) return match[1].toLowerCase();
    }
    
    return 'unknown';
  }

  private extractLicenseType(title: string): string {
    const types = ['basic', 'premium', 'enterprise', 'trial'];
    for (const type of types) {
      if (title.toLowerCase().includes(type)) return type;
    }
    return 'unknown';
  }

  private extractApps(title: string): string[] {
    const apps = ['admin', 'customer', 'crm', 'reseller', 'field-ops'];
    return apps.filter(app => title.toLowerCase().includes(app));
  }

  private determineComplianceStatus(result: TestResult, title: string): 'compliant' | 'violation' | 'warning' {
    if (result.status === 'failed') {
      // Check if failure indicates a compliance violation
      if (title.includes('should deny') || title.includes('should restrict')) {
        return 'violation'; // Test expected denial but it didn't happen
      }
      return 'warning';
    }
    
    if (result.status === 'passed') {
      return 'compliant';
    }
    
    return 'warning';
  }

  private extractTestDetails(result: TestResult): LicenseTestResult['details'] {
    // Extract detailed information from test steps
    const details = {
      featureAccess: {} as { [app: string]: boolean },
      permissionChecks: {} as { [permission: string]: boolean },
      auditTrail: false,
      realTimeUpdates: false
    };

    // Parse test steps to extract compliance details
    for (const step of result.steps || []) {
      if (step.title.includes('feature access')) {
        // Extract feature access results
        const appMatch = step.title.match(/(admin|customer|crm|reseller)/);
        if (appMatch) {
          details.featureAccess[appMatch[1]] = step.error ? false : true;
        }
      }
      
      if (step.title.includes('audit log') || step.title.includes('logging')) {
        details.auditTrail = step.error ? false : true;
      }
      
      if (step.title.includes('real-time') || step.title.includes('propagation')) {
        details.realTimeUpdates = step.error ? false : true;
      }
    }

    return details;
  }

  private generateComplianceReport(duration: number): LicenseComplianceReport {
    const passed = this.results.filter(r => r.status === 'passed').length;
    const failed = this.results.filter(r => r.status === 'failed').length;
    const skipped = this.results.filter(r => r.status === 'skipped').length;
    const total = this.results.length;
    
    const criticalViolations = this.results.filter(r => r.complianceStatus === 'violation').length;
    const warnings = this.results.filter(r => r.complianceStatus === 'warning').length;
    
    const complianceScore = total > 0 ? Math.round(((passed - criticalViolations) / total) * 100) : 0;

    // Group by license types
    const licenseTypes = this.groupByLicenseType();
    
    // Feature coverage analysis
    const featureCoverage = this.analyzeFeatureCoverage();
    
    // Cross-app consistency analysis
    const crossAppConsistency = this.analyzeCrossAppConsistency();
    
    // Filter violations for detailed reporting
    const violations = this.results.filter(r => r.complianceStatus === 'violation');

    return {
      summary: {
        totalTests: total,
        passed,
        failed,
        skipped,
        complianceScore,
        criticalViolations,
        warnings
      },
      licenseTypes,
      featureCoverage,
      crossAppConsistency,
      violations,
      results: this.results,
      timestamp: new Date().toISOString(),
      testDuration: duration
    };
  }

  private groupByLicenseType(): LicenseComplianceReport['licenseTypes'] {
    const types: { [type: string]: LicenseTestResult[] } = {};
    
    for (const result of this.results) {
      if (!types[result.licenseType]) types[result.licenseType] = [];
      types[result.licenseType].push(result);
    }

    const licenseTypes: LicenseComplianceReport['licenseTypes'] = {};
    
    for (const [type, results] of Object.entries(types)) {
      const passed = results.filter(r => r.status === 'passed').length;
      licenseTypes[type] = {
        tests: results.length,
        passed,
        complianceRate: results.length > 0 ? Math.round((passed / results.length) * 100) : 0
      };
    }

    return licenseTypes;
  }

  private analyzeFeatureCoverage(): LicenseComplianceReport['featureCoverage'] {
    const features: { [feature: string]: LicenseTestResult[] } = {};
    
    for (const result of this.results) {
      if (!features[result.feature]) features[result.feature] = [];
      features[result.feature].push(result);
    }

    const featureCoverage: LicenseComplianceReport['featureCoverage'] = {};
    
    for (const [feature, results] of Object.entries(features)) {
      const compliant = results.every(r => r.complianceStatus === 'compliant');
      const apps = [...new Set(results.flatMap(r => r.apps))];
      
      featureCoverage[feature] = {
        tested: true,
        compliant,
        apps
      };
    }

    return featureCoverage;
  }

  private analyzeCrossAppConsistency(): LicenseComplianceReport['crossAppConsistency'] {
    const apps: { [app: string]: LicenseTestResult[] } = {};
    
    for (const result of this.results) {
      for (const app of result.apps) {
        if (!apps[app]) apps[app] = [];
        apps[app].push(result);
      }
    }

    const crossAppConsistency: LicenseComplianceReport['crossAppConsistency'] = {};
    
    for (const [app, results] of Object.entries(apps)) {
      const passed = results.filter(r => r.status === 'passed').length;
      crossAppConsistency[app] = {
        tests: results.length,
        passed,
        consistencyScore: results.length > 0 ? Math.round((passed / results.length) * 100) : 0
      };
    }

    return crossAppConsistency;
  }

  private async saveReport(report: LicenseComplianceReport) {
    const outputDir = 'test-results';
    await fs.mkdir(outputDir, { recursive: true });
    
    // Save detailed JSON report
    const reportPath = path.join(outputDir, 'license-compliance-report.json');
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
    
    console.log(`📄 License compliance report saved: ${reportPath}`);
  }

  private async generateSummaryReport(report: LicenseComplianceReport) {
    const outputDir = 'test-results';
    const summaryPath = path.join(outputDir, 'license-compliance-summary.md');
    
    const markdown = `# License Compliance Report

## Summary
- **Total Tests**: ${report.summary.totalTests}
- **Compliance Score**: ${report.summary.complianceScore}%
- **Critical Violations**: ${report.summary.criticalViolations}
- **Warnings**: ${report.summary.warnings}
- **Test Duration**: ${Math.round(report.testDuration / 1000)}s

## License Type Coverage
${Object.entries(report.licenseTypes)
  .map(([type, data]) => `- **${type}**: ${data.passed}/${data.tests} tests passed (${data.complianceRate}%)`)
  .join('\n')}

## Feature Compliance
${Object.entries(report.featureCoverage)
  .map(([feature, data]) => `- **${feature}**: ${data.compliant ? '✅ Compliant' : '❌ Issues Found'} (Apps: ${data.apps.join(', ')})`)
  .join('\n')}

## Cross-App Consistency
${Object.entries(report.crossAppConsistency)
  .map(([app, data]) => `- **${app}**: ${data.consistencyScore}% consistent (${data.passed}/${data.tests})`)
  .join('\n')}

${report.violations.length > 0 ? `## Critical Violations
${report.violations.map(v => `- **${v.title}**: ${v.error || 'License enforcement failure'}`).join('\n')}` : '## ✅ No Critical Violations'}

---
*Generated on ${new Date(report.timestamp).toLocaleString()}*
`;
    
    await fs.writeFile(summaryPath, markdown);
    console.log(`📋 License compliance summary saved: ${summaryPath}`);
  }

  private printComplianceSummary(report: LicenseComplianceReport) {
    console.log('\n🔐 LICENSE COMPLIANCE SUMMARY');
    console.log('='.repeat(50));
    console.log(`Compliance Score: ${report.summary.complianceScore}%`);
    console.log(`Tests: ${report.summary.passed}/${report.summary.totalTests} passed`);
    
    if (report.summary.criticalViolations > 0) {
      console.log(`❌ Critical Violations: ${report.summary.criticalViolations}`);
    } else {
      console.log(`✅ No critical violations found`);
    }
    
    if (report.summary.warnings > 0) {
      console.log(`⚠️  Warnings: ${report.summary.warnings}`);
    }
    
    console.log(`⏱️  Duration: ${Math.round(report.testDuration / 1000)}s`);
    console.log('='.repeat(50));
    
    // Compliance threshold check
    if (report.summary.complianceScore < 95) {
      console.log('⚠️  WARNING: Compliance score below 95% threshold');
    }
    
    if (report.summary.criticalViolations > 0) {
      console.log('❌ CRITICAL: License violations detected - review required');
      process.exitCode = 1;
    }
  }

  private countTests(suite: Suite): number {
    let count = suite.tests.length;
    for (const child of suite.suites) {
      count += this.countTests(child);
    }
    return count;
  }
}