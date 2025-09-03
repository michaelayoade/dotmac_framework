/**
 * Security Manager Unit Tests
 * Tests for modular security scanning functionality
 */

import { getSecurityScanner, SecuritySeverity, VulnerabilityType } from '../../src/lib/security';

describe('Security Manager', () => {
  let scanner: any;

  beforeEach(() => {
    // Mock fetch for API calls
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        scanId: 'test-scan-123',
        vulnerabilities: [],
        summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0 },
        riskScore: 0,
        complianceStatus: { owasp: true, gdpr: true, sox: true, pci: true },
      }),
    });

    scanner = getSecurityScanner();
  });

  afterEach(() => {
    jest.clearAllMocks();
    if (scanner && typeof scanner.destroy === 'function') {
      scanner.destroy();
    }
  });

  describe('Initialization', () => {
    test('should create security manager', () => {
      expect(scanner).toBeDefined();
    });

    test('should return singleton instance', () => {
      const scanner1 = getSecurityScanner();
      const scanner2 = getSecurityScanner();
      expect(scanner1).toBe(scanner2);
    });
  });

  describe('Security Scan', () => {
    test('should perform security scan', async () => {
      const result = await scanner.performSecurityScan();

      expect(result).toHaveProperty('scanId');
      expect(result).toHaveProperty('vulnerabilities');
      expect(result).toHaveProperty('summary');
      expect(result).toHaveProperty('riskScore');
      expect(result).toHaveProperty('complianceStatus');
    });

    test('should handle scan failures gracefully', async () => {
      // Mock a failed API response
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      // In development mode, should fallback to local scan
      process.env.NODE_ENV = 'development';

      const result = await scanner.performSecurityScan();
      expect(result).toBeDefined();
    });
  });

  describe('Vulnerability Management', () => {
    test('should track active vulnerabilities', async () => {
      // Mock response with vulnerabilities
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({
          scanId: 'test-scan-123',
          vulnerabilities: [
            {
              id: 'test-vuln-1',
              type: 'test',
              severity: 'high',
              title: 'Test Vulnerability',
              description: 'Test vulnerability',
              location: 'test location',
              impact: 'test impact',
              remediation: 'test remediation',
              detectedAt: new Date().toISOString(),
              status: 'detected',
            },
          ],
          summary: { total: 1, critical: 0, high: 1, medium: 0, low: 0 },
          riskScore: 7,
          complianceStatus: { owasp: false, gdpr: false, sox: false, pci: false },
        }),
      });

      await scanner.performSecurityScan();
      const activeVulns = scanner.getActiveVulnerabilities();

      expect(Array.isArray(activeVulns)).toBe(true);
      expect(activeVulns.length).toBeGreaterThan(0);
    });

    test('should provide scan history', async () => {
      await scanner.performSecurityScan();
      const history = scanner.getScanHistory();

      expect(Array.isArray(history)).toBe(true);
      expect(history.length).toBeGreaterThanOrEqual(1);
    });

    test('should acknowledge vulnerabilities', async () => {
      // Mock response with vulnerabilities
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({
          scanId: 'test-scan-123',
          vulnerabilities: [
            {
              id: 'test-vuln-1',
              type: 'test',
              severity: 'medium',
              title: 'Test Vulnerability',
              description: 'Test vulnerability',
              location: 'test location',
              impact: 'test impact',
              remediation: 'test remediation',
              detectedAt: new Date().toISOString(),
              status: 'detected',
            },
          ],
          summary: { total: 1, critical: 0, high: 0, medium: 1, low: 0 },
          riskScore: 4,
          complianceStatus: { owasp: true, gdpr: true, sox: true, pci: true },
        }),
      });

      await scanner.performSecurityScan();
      const result = scanner.acknowledgeVulnerability('test-vuln-1', 'Test acknowledgment');

      expect(typeof result).toBe('boolean');
    });
  });

  describe('Security Configuration', () => {
    test('should validate security severity levels', () => {
      expect(SecuritySeverity.LOW).toBe('low');
      expect(SecuritySeverity.MEDIUM).toBe('medium');
      expect(SecuritySeverity.HIGH).toBe('high');
      expect(SecuritySeverity.CRITICAL).toBe('critical');
    });

    test('should validate vulnerability types', () => {
      expect(VulnerabilityType.XSS).toBe('xss');
      expect(VulnerabilityType.CSRF).toBe('csrf');
      expect(VulnerabilityType.AUTHENTICATION_BYPASS).toBe('authentication_bypass');
    });
  });
});
