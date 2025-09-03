#!/usr/bin/env node

const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs').promises;

const APPS = [
  'admin',
  'customer',
  'reseller',
  'management-admin',
  'management-reseller',
  'technician',
  'tenant-portal',
];

class LighthouseCIRunner {
  constructor() {
    this.results = {};
    this.args = process.argv.slice(2);
    this.targetApp = this.getTargetApp();
  }

  getTargetApp() {
    const appArg = this.args.find((arg) => arg.startsWith('--app='));
    return appArg ? appArg.split('=')[1] : null;
  }

  async run() {
    const appsToTest = this.targetApp ? [this.targetApp] : APPS;

    console.log('🚀 Running Lighthouse CI for:', appsToTest.join(', '));

    for (const app of appsToTest) {
      try {
        await this.runLighthouseForApp(app);
      } catch (error) {
        console.error(`❌ Failed to run Lighthouse for ${app}:`, error.message);
        this.results[app] = { success: false, error: error.message };
      }
    }

    await this.generateSummaryReport();
    this.printSummary();
  }

  async runLighthouseForApp(appName) {
    console.log(`\n📊 Running Lighthouse CI for ${appName}...`);

    const appPath = path.join(process.cwd(), 'apps', appName);

    try {
      await fs.access(appPath);
    } catch {
      throw new Error(`App directory not found: ${appPath}`);
    }

    return new Promise((resolve, reject) => {
      const lhci = spawn('npx', ['lhci', 'autorun'], {
        cwd: appPath,
        stdio: 'inherit',
      });

      lhci.on('close', (code) => {
        if (code === 0) {
          console.log(`✅ ${appName} passed Lighthouse CI`);
          this.results[appName] = { success: true };
          resolve();
        } else {
          const error = `Lighthouse CI failed with exit code ${code}`;
          this.results[appName] = { success: false, error };
          reject(new Error(error));
        }
      });
    });
  }

  async generateSummaryReport() {
    const timestamp = new Date().toISOString();
    const reportDir = path.join(process.cwd(), 'reports', 'lighthouse-ci');

    await fs.mkdir(reportDir, { recursive: true });

    const report = {
      timestamp,
      summary: {
        total: Object.keys(this.results).length,
        passed: Object.values(this.results).filter((r) => r.success).length,
        failed: Object.values(this.results).filter((r) => !r.success).length,
      },
      results: this.results,
    };

    await fs.writeFile(
      path.join(reportDir, `lighthouse-ci-${timestamp.split('T')[0]}.json`),
      JSON.stringify(report, null, 2)
    );

    console.log(`\n📄 Report saved to: ${reportDir}`);
  }

  printSummary() {
    console.log('\n📊 LIGHTHOUSE CI SUMMARY');
    console.log('='.repeat(50));

    const passed = Object.values(this.results).filter((r) => r.success).length;
    const failed = Object.values(this.results).filter((r) => !r.success).length;

    console.log(`Total Apps: ${Object.keys(this.results).length}`);
    console.log(`Passed: ${passed}`);
    console.log(`Failed: ${failed}`);

    if (failed > 0) {
      console.log('\n❌ FAILED APPS:');
      Object.entries(this.results)
        .filter(([, result]) => !result.success)
        .forEach(([app, result]) => {
          console.log(`  - ${app}: ${result.error}`);
        });

      process.exit(1);
    }

    console.log('\n🎉 All Lighthouse CI checks passed!');
  }
}

if (require.main === module) {
  const runner = new LighthouseCIRunner();
  runner.run().catch(console.error);
}
