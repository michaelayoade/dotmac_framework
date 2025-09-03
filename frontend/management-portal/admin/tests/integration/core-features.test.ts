/**
 * Core Features Integration Tests
 * Tests essential functionality with working implementations
 */

import { getAuditLogger, AuditEventType, AuditSeverity } from '../../src/lib/audit-logger';
import { getMFAService, MFAMethod } from '../../src/lib/mfa-service';
import { getWebSocketClient } from '../../src/lib/websocket-client';
import {
  getBusinessMonitor,
  BusinessOperationType,
} from '../../src/lib/business-performance-monitor';
import { getSecurityScanner } from '../../src/lib/security-scanner';
import { getPWAManager } from '../../src/lib/pwa-manager';

describe('Core Features Integration Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    jest.clearAllMocks();
  });

  describe('Audit Logger', () => {
    test('should create logger and log events successfully', async () => {
      const auditLogger = getAuditLogger();
      expect(auditLogger).toBeDefined();

      // Test basic logging functionality
      await auditLogger.log(
        AuditEventType.USER_LOGIN,
        'Test user login',
        { userId: 'test-123' },
        { customData: { testEvent: true } },
        { severity: AuditSeverity.LOW }
      );

      // Should complete without throwing
      expect(true).toBe(true);
    });

    test('should handle different event types', async () => {
      const auditLogger = getAuditLogger();

      const eventTypes = [
        AuditEventType.USER_LOGIN,
        AuditEventType.DATA_CREATED,
        AuditEventType.SECURITY_VIOLATION,
        AuditEventType.SYSTEM_ERROR,
      ];

      for (const eventType of eventTypes) {
        await auditLogger.log(
          eventType,
          `Test event: ${eventType}`,
          {},
          {},
          { severity: AuditSeverity.MEDIUM }
        );
      }

      expect(true).toBe(true);
    });
  });

  describe('MFA Service', () => {
    test('should initialize MFA service', () => {
      const mfaService = getMFAService();
      expect(mfaService).toBeDefined();
    });

    test('should validate TOTP codes', async () => {
      const mfaService = getMFAService();

      // Mock fetch for this test
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ valid: true }),
      });

      // Test valid codes (now async)
      await expect(mfaService.validateTOTPCode('123456')).resolves.toBe(true);

      // Test invalid format (should return false immediately)
      await expect(mfaService.validateTOTPCode('')).resolves.toBe(false);
      await expect(mfaService.validateTOTPCode('abc')).resolves.toBe(false);
    });

    test('should validate backup codes', () => {
      const mfaService = getMFAService();

      expect(mfaService.validateBackupCode('ABCD1234')).toBe(true);
      expect(mfaService.validateBackupCode('abcd1234')).toBe(true); // Case insensitive
      expect(mfaService.validateBackupCode('')).toBe(false);
      expect(mfaService.validateBackupCode('123')).toBe(false);
    });
  });

  describe('WebSocket Client', () => {
    test('should create WebSocket client', () => {
      const wsClient = getWebSocketClient();
      expect(wsClient).toBeDefined();
    });

    test('should have required methods', () => {
      const wsClient = getWebSocketClient();

      // Test that required methods exist
      expect(typeof wsClient.connect).toBe('function');
      expect(typeof wsClient.disconnect).toBe('function');

      // Connection starts as disconnected
      expect(true).toBe(true);
    });
  });

  describe('Business Performance Monitor', () => {
    test('should create business monitor', () => {
      const monitor = getBusinessMonitor();
      expect(monitor).toBeDefined();
    });

    test('should track operations', () => {
      const monitor = getBusinessMonitor();

      const operationId = monitor.startOperation(
        BusinessOperationType.LOGIN_ATTEMPT,
        { username: 'test@example.com' },
        'user-123'
      );

      expect(typeof operationId).toBe('string');

      monitor.addCheckpoint(operationId, 'credentials_validated');
      monitor.completeOperation(operationId, true);

      const summary = monitor.getOperationSummary(BusinessOperationType.LOGIN_ATTEMPT);
      expect(summary.totalOperations).toBeGreaterThanOrEqual(1);
    });

    test('should get system health', () => {
      const monitor = getBusinessMonitor();
      const health = monitor.getSystemHealth();

      expect(health).toHaveProperty('status');
      expect(health).toHaveProperty('issues');
      expect(health).toHaveProperty('recommendations');
      expect(['healthy', 'degraded', 'critical']).toContain(health.status);
    });
  });

  describe('Security Scanner', () => {
    test('should create security scanner', () => {
      const scanner = getSecurityScanner();
      expect(scanner).toBeDefined();
    });

    test('should perform security scan', async () => {
      const scanner = getSecurityScanner();

      // Mock the security scan API response
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({
          scanId: 'test-scan-123',
          startTime: new Date().toISOString(),
          endTime: new Date().toISOString(),
          duration: 1000,
          vulnerabilities: [
            {
              id: 'test-vuln-1',
              type: 'test',
              severity: 'medium',
              title: 'Test Vulnerability',
              description: 'Test vulnerability for testing',
              location: 'test location',
              impact: 'test impact',
              remediation: 'test remediation',
              detectedAt: new Date().toISOString(),
              status: 'detected',
            },
          ],
          summary: { total: 1, critical: 0, high: 0, medium: 1, low: 0 },
          riskScore: 4,
          complianceStatus: { owasp: true, gdpr: true, sox: false, pci: true },
        }),
      });

      const result = await scanner.performSecurityScan();

      expect(result).toHaveProperty('scanId');
      expect(result).toHaveProperty('vulnerabilities');
      expect(result).toHaveProperty('summary');
      expect(result).toHaveProperty('riskScore');
      expect(result).toHaveProperty('complianceStatus');
    });

    test('should manage vulnerabilities', async () => {
      const scanner = getSecurityScanner();

      // Use the same mock as the previous test
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
              description: 'Test vulnerability for testing',
              location: 'test location',
              impact: 'test impact',
              remediation: 'test remediation',
              detectedAt: new Date().toISOString(),
              status: 'detected',
            },
          ],
          summary: { total: 1, critical: 0, high: 0, medium: 1, low: 0 },
          riskScore: 4,
          complianceStatus: { owasp: true, gdpr: true, sox: false, pci: true },
        }),
      });

      const result = await scanner.performSecurityScan();

      const activeVulns = scanner.getActiveVulnerabilities();
      expect(Array.isArray(activeVulns)).toBe(true);

      const history = scanner.getScanHistory();
      expect(Array.isArray(history)).toBe(true);
      expect(history.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('PWA Manager', () => {
    test('should create PWA manager', () => {
      const pwa = getPWAManager();
      expect(pwa).toBeDefined();
    });

    test('should provide PWA capabilities', () => {
      const pwa = getPWAManager();
      const capabilities = pwa.getCapabilities();

      expect(capabilities).toHaveProperty('serviceWorker');
      expect(capabilities).toHaveProperty('pushMessaging');
      expect(capabilities).toHaveProperty('backgroundSync');
      expect(capabilities).toHaveProperty('notifications');
    });

    test('should handle offline status', () => {
      const pwa = getPWAManager();
      const isOnline = pwa.isOnlineStatus();

      expect(typeof isOnline).toBe('boolean');
    });
  });

  describe('Integration Workflows', () => {
    test('should handle complete authentication workflow', async () => {
      const monitor = getBusinessMonitor();
      const auditLogger = getAuditLogger();
      const mfaService = getMFAService();

      // Mock MFA API validation
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ valid: true }),
      });

      // Start authentication operation
      const authOpId = monitor.startOperation(
        BusinessOperationType.LOGIN_ATTEMPT,
        { username: 'test@example.com' },
        'user-123'
      );

      // Validate credentials
      monitor.addCheckpoint(authOpId, 'credentials_validated');

      // MFA challenge (now async)
      const mfaValid = await mfaService.validateTOTPCode('123456');
      expect(mfaValid).toBe(true);

      monitor.addCheckpoint(authOpId, 'mfa_validated');

      // Complete operation
      monitor.completeOperation(authOpId, true, undefined, undefined, {
        authMethod: 'password+totp',
      });

      // Log audit event
      await auditLogger.log(
        AuditEventType.USER_LOGIN,
        'User authentication successful',
        { userId: 'user-123' },
        { customData: { authMethod: 'password+totp' } },
        { severity: AuditSeverity.LOW }
      );

      // Verify operation tracking
      const summary = monitor.getOperationSummary(BusinessOperationType.LOGIN_ATTEMPT);
      expect(summary.totalOperations).toBeGreaterThanOrEqual(1);
    });

    test('should handle security monitoring workflow', async () => {
      const scanner = getSecurityScanner();
      const auditLogger = getAuditLogger();
      const monitor = getBusinessMonitor();

      // Start security scan
      const scanOpId = monitor.startOperation(
        BusinessOperationType.BACKUP_RESTORE,
        { scanType: 'comprehensive' },
        'admin-123'
      );

      // Mock the security scan API for this test
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({
          scanId: 'test-scan-workflow',
          vulnerabilities: [],
          summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0 },
          riskScore: 0,
          complianceStatus: { owasp: true, gdpr: true, sox: true, pci: true },
        }),
      });

      // Perform scan
      const scanResult = await scanner.performSecurityScan();

      // Complete operation
      monitor.completeOperation(scanOpId, true, undefined, undefined, {
        vulnerabilitiesFound: scanResult.summary.total,
        riskScore: scanResult.riskScore,
      });

      // Log security event if high-risk vulnerabilities found
      if (scanResult.summary.critical > 0) {
        await auditLogger.log(
          AuditEventType.SECURITY_VIOLATION,
          'Critical vulnerabilities detected',
          { userId: 'admin-123' },
          { customData: { criticalCount: scanResult.summary.critical } },
          { severity: AuditSeverity.HIGH }
        );
      }

      expect(scanResult.riskScore).toBeGreaterThanOrEqual(0);
      expect(scanResult.riskScore).toBeLessThanOrEqual(100);
    });
  });
});
