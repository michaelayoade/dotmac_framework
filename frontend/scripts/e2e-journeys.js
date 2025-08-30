#!/usr/bin/env node

const { spawn } = require('node:child_process');
const path = require('node:path');

const PORTALS = ['admin', 'customer', 'reseller', 'technician'];

class E2ETestRunner {
  constructor() {
    this.args = process.argv.slice(2);
    this.targetPortal = this.getTargetPortal();
    this.targetJourney = this.getTargetJourney();
  }

  getTargetPortal() {
    const portalArg = this.args.find(arg => arg.startsWith('--portal='));
    return portalArg ? portalArg.split('=')[1] : null;
  }

  getTargetJourney() {
    const journeyArg = this.args.find(arg => arg.startsWith('--journey='));
    return journeyArg ? journeyArg.split('=')[1] : null;
  }

  async run() {
    if (this.targetJourney) {
      await this.runSpecificJourney();
    } else if (this.targetPortal) {
      await this.runPortalTests(this.targetPortal);
    } else {
      await this.runAllPortalTests();
    }
  }

  async runSpecificJourney() {
    console.log(`🧪 Running journey test: ${this.targetJourney}`);
    // Find which portal contains this journey
    const portal = this.findPortalForJourney(this.targetJourney);
    if (portal) {
      await this.runPlaywrightTest(portal, `tests/e2e/${this.targetJourney}.spec.ts`);
    } else {
      console.error(`Journey ${this.targetJourney} not found`);
      process.exit(1);
    }
  }

  async runPortalTests(portal) {
    console.log(`🧪 Running all tests for ${portal} portal`);
    await this.runPlaywrightTest(portal);
  }

  async runAllPortalTests() {
    console.log('🧪 Running user journey tests for all portals');

    for (const portal of PORTALS) {
      const appPath = path.join(process.cwd(), 'apps', portal);
      try {
        require('fs').accessSync(appPath);
        await this.runPortalTests(portal);
      } catch {
        console.log(`⚠️  Skipping ${portal} (not found)`);
      }
    }
  }

  async runPlaywrightTest(portal, testFile = '') {
    return new Promise((resolve, reject) => {
      const appPath = path.join(process.cwd(), 'apps', portal);
      const args = ['playwright', 'test'];

      if (testFile) {
        args.push(testFile);
      }

      args.push('--reporter=html', '--reporter=json');

      const playwright = spawn('npx', args, {
        cwd: appPath,
        stdio: 'inherit'
      });

      playwright.on('close', (code) => {
        if (code === 0) {
          console.log(`✅ ${portal} tests passed`);
          resolve();
        } else {
          console.error(`❌ ${portal} tests failed`);
          reject(new Error(`Tests failed with code ${code}`));
        }
      });
    });
  }

  findPortalForJourney(journeyName) {
        {
    \"customer\": [
        {
            \"name\": \"customer-onboarding\",
            \"description\": \"Complete customer onboarding flow\",
            \"steps\": [
                \"registration\",
                \"email-verification\",
                \"profile-setup\",
                \"service-selection\",
                \"payment-setup\"
            ]
        },
        {
            \"name\": \"service-management\",
            \"description\": \"Manage services and view usage\",
            \"steps\": [
                \"login\",
                \"view-services\",
                \"upgrade-service\",
                \"view-usage\",
                \"download-invoice\"
            ]
        },
        {
            \"name\": \"support-ticket\",
            \"description\": \"Create and track support ticket\",
            \"steps\": [
                \"login\",
                \"create-ticket\",
                \"upload-attachments\",
                \"track-status\",
                \"close-ticket\"
            ]
        },
        {
            \"name\": \"billing-payment\",
            \"description\": \"Complete billing and payment flow\",
            \"steps\": [
                \"login\",
                \"view-invoices\",
                \"add-payment-method\",
                \"make-payment\",
                \"download-receipt\"
            ]
        }
    ],
    \"admin\": [
        {
            \"name\": \"customer-provisioning\",
            \"description\": \"Provision new customer account\",
            \"steps\": [
                \"login\",
                \"create-customer\",
                \"assign-services\",
                \"configure-network\",
                \"send-welcome-email\"
            ]
        },
        {
            \"name\": \"network-monitoring\",
            \"description\": \"Monitor network performance and handle alerts\",
            \"steps\": [
                \"login\",
                \"check-dashboard\",
                \"view-alerts\",
                \"diagnose-issue\",
                \"resolve-alert\"
            ]
        },
        {
            \"name\": \"billing-management\",
            \"description\": \"Manage customer billing and invoices\",
            \"steps\": [
                \"login\",
                \"generate-invoices\",
                \"apply-credits\",
                \"send-statements\",
                \"track-payments\"
            ]
        }
    ],
    \"reseller\": [
        {
            \"name\": \"territory-management\",
            \"description\": \"Manage assigned territory and customers\",
            \"steps\": [
                \"login\",
                \"view-territory\",
                \"add-customer\",
                \"track-commission\",
                \"generate-report\"
            ]
        },
        {
            \"name\": \"sales-process\",
            \"description\": \"Complete sales process from lead to activation\",
            \"steps\": [
                \"login\",
                \"create-lead\",
                \"generate-quote\",
                \"process-order\",
                \"schedule-installation\"
            ]
        }
    ],
    \"technician\": [
        {
            \"name\": \"field-service\",
            \"description\": \"Complete field service installation\",
            \"steps\": [
                \"mobile-login\",
                \"view-jobs\",
                \"navigate-to-site\",
                \"complete-installation\",
                \"update-status\"
            ]
        },
        {
            \"name\": \"diagnostic-tools\",
            \"description\": \"Use diagnostic tools for troubleshooting\",
            \"steps\": [
                \"mobile-login\",
                \"select-customer\",
                \"run-diagnostics\",
                \"identify-issues\",
                \"resolve-problems\"
            ]
        }
    ]
}

    for (const [portal, journeys] of Object.entries(journeyMap)) {
      if (journeys.some(j => j.name === journeyName)) {
        return portal;
      }
    }
    return null;
  }
}

if (require.main === module) {
  const runner = new E2ETestRunner();
  runner.run().catch(console.error);
}
