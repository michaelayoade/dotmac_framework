const fs = require('fs');
const path = require('path');

class CoverageReporter {
  constructor(globalConfig, options) {
    this.globalConfig = globalConfig;
    this.options = options;
  }

  onRunComplete(contexts, results) {
    const coverageMap = results.coverageMap;

    if (!coverageMap) {
      console.log('No coverage data available');
      return;
    }

    // Generate detailed coverage report
    this.generateCoverageReport(coverageMap);

    // Check coverage thresholds
    this.checkThresholds(coverageMap);

    // Generate badge data
    this.generateBadgeData(coverageMap);
  }

  generateCoverageReport(coverageMap) {
    const summary = coverageMap.getCoverageSummary();
    const report = {
      timestamp: new Date().toISOString(),
      total: {
        lines: summary.lines.toSummary(),
        functions: summary.functions.toSummary(),
        branches: summary.branches.toSummary(),
        statements: summary.statements.toSummary(),
      },
      files: {},
    };

    // Add per-file coverage
    coverageMap.files().forEach((file) => {
      const fileCoverage = coverageMap.fileCoverageFor(file);
      const fileSummary = fileCoverage.toSummary();

      report.files[file] = {
        lines: fileSummary.lines.toSummary(),
        functions: fileSummary.functions.toSummary(),
        branches: fileSummary.branches.toSummary(),
        statements: fileSummary.statements.toSummary(),
      };
    });

    // Write detailed report
    const reportPath = path.join(process.cwd(), 'coverage', 'coverage-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    console.log('\n📊 Coverage Report Generated:');
    console.log(`Lines: ${report.total.lines.pct}%`);
    console.log(`Functions: ${report.total.functions.pct}%`);
    console.log(`Branches: ${report.total.branches.pct}%`);
    console.log(`Statements: ${report.total.statements.pct}%`);
    console.log(`\nDetailed report: ${reportPath}`);
  }

  checkThresholds(coverageMap) {
    const summary = coverageMap.getCoverageSummary();
    const thresholds = this.globalConfig.coverageThreshold?.global || {};

    let failed = false;

    Object.entries(thresholds).forEach(([metric, threshold]) => {
      const actual = summary[metric].pct;

      if (actual < threshold) {
        console.error(`❌ ${metric} coverage (${actual}%) below threshold (${threshold}%)`);
        failed = true;
      } else {
        console.log(`✅ ${metric} coverage (${actual}%) meets threshold (${threshold}%)`);
      }
    });

    if (failed) {
      console.error('\n🚫 Coverage thresholds not met!');
      process.exit(1);
    } else {
      console.log('\n🎉 All coverage thresholds met!');
    }
  }

  generateBadgeData(coverageMap) {
    const summary = coverageMap.getCoverageSummary();
    const linesCoverage = summary.lines.pct;

    // Generate shield.io badge data
    const color =
      linesCoverage >= 90
        ? 'brightgreen'
        : linesCoverage >= 80
          ? 'green'
          : linesCoverage >= 70
            ? 'yellow'
            : linesCoverage >= 60
              ? 'orange'
              : 'red';

    const badgeData = {
      schemaVersion: 1,
      label: 'coverage',
      message: `${linesCoverage}%`,
      color: color,
    };

    const badgePath = path.join(process.cwd(), 'coverage', 'badge.json');
    fs.writeFileSync(badgePath, JSON.stringify(badgeData, null, 2));

    console.log(`Coverage badge data generated: ${badgePath}`);
  }
}

module.exports = CoverageReporter;
