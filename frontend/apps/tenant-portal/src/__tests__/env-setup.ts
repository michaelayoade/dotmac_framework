/**
 * Environment Setup for Tests
 * Set environment variables and configuration for testing
 */

// Set NODE_ENV to test (using Object.assign to avoid readonly error)
Object.assign(process.env, { NODE_ENV: 'test' });

// App configuration
process.env.NEXT_PUBLIC_APP_NAME = 'DotMac Tenant Portal';
process.env.NEXT_PUBLIC_APP_VERSION = '1.0.0';
process.env.NEXT_PUBLIC_PORTAL_TYPE = 'tenant';
process.env.NEXT_PUBLIC_ENVIRONMENT = 'test';

// API configuration
process.env.MANAGEMENT_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_MANAGEMENT_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8001';

// Site configuration
process.env.NEXT_PUBLIC_SITE_URL = 'http://localhost:3003';

// Security configuration (test values - not for production)
process.env.JWT_SECRET_KEY = 'test-jwt-secret-key-for-testing-only-32-chars';
process.env.SESSION_SECRET = 'test-session-secret-for-testing-only-32-chars';
process.env.CSRF_SECRET = 'test-csrf-secret-for-testing-only-32-chars';
process.env.SESSION_MAX_AGE = '3600'; // 1 hour

// Demo configuration (enabled for tests)
process.env.DEMO_ENABLED = 'true';
process.env.DEMO_ADMIN_EMAIL = 'admin@test-tenant.local';
process.env.DEMO_ADMIN_PASSWORD = 'TestPassword123!';
process.env.DEMO_USER_EMAIL = 'user@test-tenant.local';
process.env.DEMO_USER_PASSWORD = 'TestUser123!';
process.env.DEMO_TENANT_ID = 'test_tenant_12345';
process.env.DEMO_TENANT_NAME = 'test-tenant';
process.env.DEMO_TENANT_DISPLAY = 'Test ISP Solutions';

// Feature flags (all enabled for comprehensive testing)
process.env.NEXT_PUBLIC_FEATURE_BILLING_ENABLED = 'true';
process.env.NEXT_PUBLIC_FEATURE_ANALYTICS_ENABLED = 'true';
process.env.NEXT_PUBLIC_FEATURE_SUPPORT_CHAT = 'true';
process.env.NEXT_PUBLIC_FEATURE_MFA_ENABLED = 'true';

// Development settings
process.env.DEBUG = 'true';
process.env.NEXT_PUBLIC_DEBUG = 'true';
process.env.MOCK_API_ENABLED = 'true';
process.env.MOCK_DELAY_MS = '0'; // No delay in tests

// Rate limiting (relaxed for tests)
process.env.RATE_LIMIT_LOGIN_ATTEMPTS = '100';
process.env.RATE_LIMIT_WINDOW_MS = '60000';

// CSP configuration
process.env.CSP_REPORT_ONLY = 'true';
process.env.CSP_REPORT_URI = '/api/csp-report';

// Contact information
process.env.NEXT_PUBLIC_SUPPORT_EMAIL = 'support@test.local';
process.env.NEXT_PUBLIC_SUPPORT_PHONE = '+1-800-TEST';

// Logging
process.env.LOG_LEVEL = 'debug';
process.env.LOG_FORMAT = 'dev';

// External services (disabled for tests)
process.env.SENTRY_DSN = '';
process.env.NEXT_PUBLIC_ANALYTICS_ID = '';

// Test-specific configurations
process.env.TEST_TIMEOUT = '30000'; // 30 seconds
process.env.TEST_DATABASE_URL = 'sqlite::memory:';
process.env.TEST_REDIS_URL = 'redis://localhost:6379/15'; // Use DB 15 for tests