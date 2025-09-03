/**
 * CI/CD Configuration for Dev 4 Integration Tests
 * 
 * Provides environment-specific configurations for running
 * integration tests in CI/CD pipelines with proper mocking
 * and service management.
 */

export interface CIConfig {
  useMockServices: boolean;
  testTimeout: number;
  retryAttempts: number;
  parallelWorkers: number;
  mockEndpoints: {
    managementApi: string;
    tenantMock: string;
    stripeWebhook: string;
  };
  realEndpoints: {
    managementApi: string;
    stripe: string;
    sendGrid: string;
    twilio: string;
  };
}

const isCI = process.env.CI === 'true';
const useMockServices = process.env.USE_MOCK_SERVICES === 'true' || isCI;

export const ciConfig: CIConfig = {
  useMockServices,
  testTimeout: isCI ? 30000 : 60000, // Shorter timeouts in CI
  retryAttempts: isCI ? 2 : 1,
  parallelWorkers: isCI ? 2 : 4,
  
  mockEndpoints: {
    managementApi: 'http://localhost:8000',
    tenantMock: 'http://localhost:3100',
    stripeWebhook: 'http://localhost:8001/webhook'
  },
  
  realEndpoints: {
    managementApi: process.env.MANAGEMENT_API_URL || 'http://localhost:8000',
    stripe: 'https://api.stripe.com',
    sendGrid: 'https://api.sendgrid.com',
    twilio: 'https://api.twilio.com'
  }
};

/**
 * Get API endpoint based on environment
 */
export function getApiEndpoint(service: keyof CIConfig['mockEndpoints']): string {
  return useMockServices ? ciConfig.mockEndpoints[service] : ciConfig.realEndpoints[service as keyof CIConfig['realEndpoints']] || ciConfig.mockEndpoints[service];
}

/**
 * Test environment setup utilities
 */
export class TestEnvironment {
  static async waitForService(url: string, timeout = 30000): Promise<void> {
    const start = Date.now();
    
    while (Date.now() - start < timeout) {
      try {
        const response = await fetch(url);
        if (response.ok) {
          return;
        }
      } catch (error) {
        // Service not ready, continue waiting
      }
      
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    throw new Error(`Service at ${url} not ready after ${timeout}ms`);
  }
  
  static async setupMockServices(): Promise<void> {
    if (!useMockServices) return;
    
    // Wait for mock services to be available
    await Promise.all([
      this.waitForService(ciConfig.mockEndpoints.managementApi + '/api/health'),
      this.waitForService(ciConfig.mockEndpoints.tenantMock + '/health')
    ]);
    
    console.log('Mock services are ready for testing');
  }
  
  static getTestCredentials() {
    return {
      stripe: {
        publishableKey: process.env.STRIPE_TEST_KEY || 'pk_test_mock',
        secretKey: process.env.STRIPE_SECRET_KEY || 'sk_test_mock',
        webhookSecret: process.env.STRIPE_WEBHOOK_SECRET || 'whsec_mock'
      },
      sendGrid: {
        apiKey: process.env.SENDGRID_API_KEY || 'SG.mock.test'
      },
      twilio: {
        accountSid: process.env.TWILIO_ACCOUNT_SID || 'AC_mock_test',
        authToken: process.env.TWILIO_AUTH_TOKEN || 'mock_token'
      },
      testApi: {
        key: process.env.TEST_API_KEY || 'test_key_ci_12345'
      }
    };
  }
}

/**
 * Mock service response generators for consistent testing
 */
export class MockResponses {
  static stripePaymentIntent(amount: number, currency = 'usd') {
    return {
      id: `pi_mock_${Math.random().toString(36).substr(2, 9)}`,
      amount: amount * 100, // Stripe uses cents
      currency,
      status: 'succeeded',
      payment_method: 'pm_mock_card',
      created: Math.floor(Date.now() / 1000)
    };
  }
  
  static stripeCustomer(email: string) {
    return {
      id: `cus_mock_${Math.random().toString(36).substr(2, 9)}`,
      email,
      created: Math.floor(Date.now() / 1000),
      default_source: null,
      subscriptions: { data: [] }
    };
  }
  
  static sendGridResponse() {
    return {
      message_id: `mock_msg_${Date.now()}`,
      status: 'delivered',
      timestamp: Date.now()
    };
  }
  
  static twilioSmsResponse(to: string, message: string) {
    return {
      sid: `SM_mock_${Math.random().toString(36).substr(2, 10)}`,
      to,
      body: message,
      status: 'sent',
      date_created: new Date().toISOString()
    };
  }
  
  static kubernetesDeployment(name: string, namespace: string) {
    return {
      apiVersion: 'apps/v1',
      kind: 'Deployment',
      metadata: {
        name,
        namespace,
        uid: `mock-${Math.random().toString(36).substr(2, 9)}`
      },
      status: {
        readyReplicas: 1,
        replicas: 1,
        conditions: [{
          type: 'Available',
          status: 'True'
        }]
      }
    };
  }
}