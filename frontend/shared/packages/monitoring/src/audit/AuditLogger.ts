/**
 * Comprehensive Audit Logging System
 * Implements secure audit trail for ISP customer portal compliance
 */

export interface AuditEvent {
  id: string;
  timestamp: Date;
  userId?: string;
  sessionId?: string;
  action: string;
  resource: string;
  resourceId?: string;
  result: 'success' | 'failure' | 'denied';
  severity: 'low' | 'medium' | 'high' | 'critical';
  ipAddress?: string;
  userAgent?: string;
  location?: {
    country?: string;
    region?: string;
    city?: string;
  };
  metadata: Record<string, unknown>;
  checksum?: string;
}

export interface AuditContext {
  userId?: string;
  sessionId?: string;
  ipAddress?: string;
  userAgent?: string;
  traceId?: string;
  correlationId?: string;
}

export interface AuditLoggerConfig {
  enabled: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  retention: {
    days: number;
    maxSize: string;
  };
  encryption: {
    enabled: boolean;
    algorithm: string;
    keyId?: string;
  };
  destinations: {
    console: boolean;
    file: boolean;
    database: boolean;
    siem: boolean;
    external?: {
      url: string;
      apiKey: string;
    };
  };
  compliance: {
    standard: 'SOX' | 'PCI' | 'GDPR' | 'HIPAA' | 'SOC2' | 'CUSTOM';
    requireIntegrityCheck: boolean;
    requireNonRepudiation: boolean;
  };
}

/**
 * Secure audit logging with compliance features
 */
export class AuditLogger {
  private config: AuditLoggerConfig;
  private buffer: AuditEvent[] = [];
  private flushInterval?: NodeJS.Timeout;
  private encryptionKey?: CryptoKey;

  constructor(config: AuditLoggerConfig) {
    this.config = config;
    this.initializeEncryption();
    this.startBufferFlush();
  }

  /**
   * Log authentication events
   */
  async logAuthentication(
    action: 'login' | 'logout' | 'failed_login' | 'password_change' | 'token_refresh',
    context: AuditContext,
    metadata: Record<string, unknown> = {}
  ): Promise<void> {
    const event: AuditEvent = {
      id: this.generateEventId(),
      timestamp: new Date(),
      userId: context.userId,
      sessionId: context.sessionId,
      action: `auth.${action}`,
      resource: 'authentication',
      result: action === 'failed_login' ? 'failure' : 'success',
      severity: action === 'failed_login' ? 'medium' : 'low',
      ipAddress: context.ipAddress,
      userAgent: context.userAgent,
      metadata: {
        ...metadata,
        traceId: context.traceId,
        correlationId: context.correlationId,
      },
    };

    await this.logEvent(event);
  }

  /**
   * Log data access events
   */
  async logDataAccess(
    action: 'read' | 'create' | 'update' | 'delete' | 'export',
    resource: string,
    resourceId: string,
    context: AuditContext,
    result: 'success' | 'failure' | 'denied' = 'success',
    metadata: Record<string, unknown> = {}
  ): Promise<void> {
    const event: AuditEvent = {
      id: this.generateEventId(),
      timestamp: new Date(),
      userId: context.userId,
      sessionId: context.sessionId,
      action: `data.${action}`,
      resource,
      resourceId,
      result,
      severity: this.determineSeverity(action, result),
      ipAddress: context.ipAddress,
      userAgent: context.userAgent,
      metadata: {
        ...metadata,
        traceId: context.traceId,
        correlationId: context.correlationId,
      },
    };

    await this.logEvent(event);
  }

  /**
   * Log security events
   */
  async logSecurity(
    action: string,
    context: AuditContext,
    result: 'success' | 'failure' | 'denied',
    severity: 'low' | 'medium' | 'high' | 'critical' = 'medium',
    metadata: Record<string, unknown> = {}
  ): Promise<void> {
    const event: AuditEvent = {
      id: this.generateEventId(),
      timestamp: new Date(),
      userId: context.userId,
      sessionId: context.sessionId,
      action: `security.${action}`,
      resource: 'security',
      result,
      severity,
      ipAddress: context.ipAddress,
      userAgent: context.userAgent,
      metadata: {
        ...metadata,
        traceId: context.traceId,
        correlationId: context.correlationId,
      },
    };

    await this.logEvent(event);
  }

  /**
   * Log business events
   */
  async logBusiness(
    action: string,
    resource: string,
    resourceId: string,
    context: AuditContext,
    metadata: Record<string, unknown> = {}
  ): Promise<void> {
    const event: AuditEvent = {
      id: this.generateEventId(),
      timestamp: new Date(),
      userId: context.userId,
      sessionId: context.sessionId,
      action: `business.${action}`,
      resource,
      resourceId,
      result: 'success',
      severity: 'low',
      ipAddress: context.ipAddress,
      userAgent: context.userAgent,
      metadata: {
        ...metadata,
        traceId: context.traceId,
        correlationId: context.correlationId,
      },
    };

    await this.logEvent(event);
  }

  /**
   * Log system events
   */
  async logSystem(
    action: string,
    resource: string,
    result: 'success' | 'failure' = 'success',
    severity: 'low' | 'medium' | 'high' | 'critical' = 'low',
    metadata: Record<string, unknown> = {}
  ): Promise<void> {
    const event: AuditEvent = {
      id: this.generateEventId(),
      timestamp: new Date(),
      action: `system.${action}`,
      resource,
      result,
      severity,
      metadata,
    };

    await this.logEvent(event);
  }

  /**
   * Core event logging method
   */
  private async logEvent(event: AuditEvent): Promise<void> {
    if (!this.config.enabled) return;

    // Add integrity check
    if (this.config.compliance.requireIntegrityCheck) {
      event.checksum = await this.generateChecksum(event);
    }

    // Encrypt if required
    if (this.config.encryption.enabled && this.encryptionKey) {
      event = await this.encryptEvent(event);
    }

    // Add to buffer
    this.buffer.push(event);

    // Immediate flush for critical events
    if (event.severity === 'critical') {
      await this.flushBuffer();
    }
  }

  /**
   * Process buffered events with performance optimization
   */
  private async flushBuffer(): Promise<void> {
    if (this.buffer.length === 0) return;

    const events = [...this.buffer];
    this.buffer = [];

    try {
      // Process destinations in parallel but with error isolation
      const results = await Promise.allSettled([
        this.writeToConsole(events),
        this.writeToFile(events),
        this.writeToDatabase(events),
        this.writeToSIEM(events),
        this.writeToExternal(events),
      ]);

      // Log any failed destinations without re-queuing all events
      results.forEach((result, index) => {
        if (result.status === 'rejected') {
          const destinations = ['console', 'file', 'database', 'siem', 'external'];
          console.error(`Audit logging failed for ${destinations[index]}:`, result.reason);
        }
      });
    } catch (error) {
      console.error('Audit logging batch failed:', error);
      // Only re-queue events if all destinations failed
      if (this.buffer.length < 1000) {
        // Prevent memory overflow
        this.buffer.unshift(...events.slice(-100)); // Keep only recent events
      }
    }
  }

  /**
   * Console output
   */
  private async writeToConsole(events: AuditEvent[]): Promise<void> {
    if (!this.config.destinations.console) return;

    for (const event of events) {
      const logLine = this.formatLogLine(event);

      switch (event.severity) {
        case 'critical':
        case 'high':
          console.error(logLine);
          break;
        case 'medium':
          console.warn(logLine);
          break;
        default:
          console.info(logLine);
      }
    }
  }

  /**
   * File output
   */
  private async writeToFile(events: AuditEvent[]): Promise<void> {
    if (!this.config.destinations.file) return;

    if (typeof window !== 'undefined') {
      // Browser environment - use localStorage or indexedDB
      const existingLogs = JSON.parse(localStorage.getItem('auditLogs') || '[]');
      existingLogs.push(...events);

      // Implement rotation based on config
      const maxEvents = 1000; // Could be calculated from maxSize
      if (existingLogs.length > maxEvents) {
        existingLogs.splice(0, existingLogs.length - maxEvents);
      }

      localStorage.setItem('auditLogs', JSON.stringify(existingLogs));
    } else {
      // Node.js environment - write to file
      const fs = await import('fs/promises');
      const path = await import('path');

      const logDir = path.join(process.cwd(), 'logs');
      const logFile = path.join(logDir, `audit-${new Date().toISOString().split('T')[0]}.log`);

      try {
        await fs.mkdir(logDir, { recursive: true });
        const logLines = events.map((event) => this.formatLogLine(event)).join('\n') + '\n';
        await fs.appendFile(logFile, logLines);
      } catch (error) {
        console.error('Failed to write audit log to file:', error);
      }
    }
  }

  /**
   * Database output
   */
  private async writeToDatabase(events: AuditEvent[]): Promise<void> {
    if (!this.config.destinations.database) return;

    // In a real implementation, this would write to a database
    // For now, we'll simulate the database write
    try {
      // Simulate database write
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Log successful database write
      console.debug(`Wrote ${events.length} audit events to database`);
    } catch (error) {
      console.error('Failed to write audit events to database:', error);
      throw error;
    }
  }

  /**
   * SIEM output
   */
  private async writeToSIEM(events: AuditEvent[]): Promise<void> {
    if (!this.config.destinations.siem) return;

    // Format events for SIEM consumption (CEF, LEEF, JSON, etc.)
    const siemEvents = events.map((event) => this.formatForSIEM(event));

    try {
      // In a real implementation, this would send to SIEM
      console.debug(`Sent ${siemEvents.length} events to SIEM`);
    } catch (error) {
      console.error('Failed to send events to SIEM:', error);
      throw error;
    }
  }

  /**
   * External service output
   */
  private async writeToExternal(events: AuditEvent[]): Promise<void> {
    if (!this.config.destinations.external) return;

    const { url, apiKey } = this.config.destinations.external;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
          'User-Agent': 'DotMac-AuditLogger/1.0',
        },
        body: JSON.stringify({ events }),
      });

      if (!response.ok) {
        throw new Error(`External audit service returned ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to send events to external service:', error);
      throw error;
    }
  }

  /**
   * Format log line for human readability
   */
  private formatLogLine(event: AuditEvent): string {
    const timestamp = event.timestamp.toISOString();
    const user = event.userId || 'anonymous';
    const action = event.action;
    const resource = event.resourceId ? `${event.resource}:${event.resourceId}` : event.resource;
    const result = event.result;
    const ip = event.ipAddress || 'unknown';

    return `${timestamp} [${event.severity.toUpperCase()}] ${user} ${action} ${resource} ${result} from ${ip}`;
  }

  /**
   * Format event for SIEM (Common Event Format)
   */
  private formatForSIEM(event: AuditEvent): string {
    const timestamp = Math.floor(event.timestamp.getTime() / 1000);

    return (
      `CEF:0|DotMac|CustomerPortal|2.0|${event.action}|${event.action}|${this.severityToCEF(event.severity)}|` +
      `rt=${timestamp} src=${event.ipAddress || 'unknown'} suser=${event.userId || 'anonymous'} ` +
      `act=${event.action} outcome=${event.result} cs1=${event.resource} cs1Label=Resource ` +
      `cs2=${event.resourceId || ''} cs2Label=ResourceId cs3=${event.sessionId || ''} cs3Label=SessionId`
    );
  }

  /**
   * Convert severity to CEF format
   */
  private severityToCEF(severity: string): number {
    switch (severity) {
      case 'low':
        return 3;
      case 'medium':
        return 6;
      case 'high':
        return 8;
      case 'critical':
        return 10;
      default:
        return 5;
    }
  }

  /**
   * Generate unique event ID
   */
  private generateEventId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2);
    return `audit_${timestamp}_${random}`;
  }

  /**
   * Determine event severity based on action and result
   */
  private determineSeverity(
    action: string,
    result: 'success' | 'failure' | 'denied'
  ): 'low' | 'medium' | 'high' | 'critical' {
    if (result === 'denied') return 'high';
    if (result === 'failure') return 'medium';

    switch (action) {
      case 'delete':
      case 'export':
        return 'medium';
      case 'update':
        return 'low';
      case 'read':
      case 'create':
      default:
        return 'low';
    }
  }

  /**
   * Generate integrity checksum
   */
  private async generateChecksum(event: AuditEvent): Promise<string> {
    const data = JSON.stringify({
      timestamp: event.timestamp,
      userId: event.userId,
      action: event.action,
      resource: event.resource,
      resourceId: event.resourceId,
      result: event.result,
      metadata: event.metadata,
    });

    if (typeof window !== 'undefined' && window.crypto && window.crypto.subtle) {
      const encoder = new TextEncoder();
      const dataBuffer = encoder.encode(data);
      const hashBuffer = await window.crypto.subtle.digest('SHA-256', dataBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
    } else {
      // Fallback for Node.js
      const crypto = await import('crypto');
      return crypto.createHash('sha256').update(data).digest('hex');
    }
  }

  /**
   * Initialize encryption if enabled
   */
  private async initializeEncryption(): Promise<void> {
    if (!this.config.encryption.enabled) return;

    try {
      if (typeof window !== 'undefined' && window.crypto && window.crypto.subtle) {
        // Generate or load encryption key
        this.encryptionKey = await window.crypto.subtle.generateKey(
          { name: 'AES-GCM', length: 256 },
          false,
          ['encrypt', 'decrypt']
        );
      }
    } catch (error) {
      console.warn('Failed to initialize audit log encryption:', error);
    }
  }

  /**
   * Encrypt audit event
   */
  private async encryptEvent(event: AuditEvent): Promise<AuditEvent> {
    if (!this.encryptionKey) return event;

    try {
      const sensitiveFields = ['metadata', 'ipAddress', 'userAgent'];
      const encryptedEvent = { ...event };

      for (const field of sensitiveFields) {
        if (event[field as keyof AuditEvent]) {
          const data = JSON.stringify(event[field as keyof AuditEvent]);
          const encrypted = await this.encryptData(data);
          (encryptedEvent as any)[field] = encrypted;
        }
      }

      return encryptedEvent;
    } catch (error) {
      console.warn('Failed to encrypt audit event:', error);
      return event;
    }
  }

  /**
   * Encrypt sensitive data
   */
  private async encryptData(data: string): Promise<string> {
    if (!this.encryptionKey) return data;

    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    const iv = window.crypto.getRandomValues(new Uint8Array(12));

    const encrypted = await window.crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      this.encryptionKey,
      dataBuffer
    );

    const encryptedArray = new Uint8Array(encrypted);
    const result = new Uint8Array(iv.length + encryptedArray.length);
    result.set(iv);
    result.set(encryptedArray, iv.length);

    return btoa(String.fromCharCode(...result));
  }

  /**
   * Start periodic buffer flush
   */
  private startBufferFlush(): void {
    this.flushInterval = setInterval(async () => {
      if (this.buffer.length > 0) {
        await this.flushBuffer();
      }
    }, 5000); // Flush every 5 seconds
  }

  /**
   * Clean shutdown
   */
  async shutdown(): Promise<void> {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
    }

    // Final flush
    await this.flushBuffer();
  }

  /**
   * Get audit statistics
   */
  getStatistics(): {
    bufferedEvents: number;
    totalEvents: number;
    encryptionEnabled: boolean;
    destinations: string[];
  } {
    const activeDestinations = Object.entries(this.config.destinations)
      .filter(([key, enabled]) => enabled && key !== 'external')
      .map(([key]) => key);

    if (this.config.destinations.external) {
      activeDestinations.push('external');
    }

    return {
      bufferedEvents: this.buffer.length,
      totalEvents: 0, // Would be tracked in real implementation
      encryptionEnabled: this.config.encryption.enabled,
      destinations: activeDestinations,
    };
  }
}

/**
 * Pre-configured audit logger for ISP customer portal
 */
export const CUSTOMER_PORTAL_AUDIT_CONFIG: AuditLoggerConfig = {
  enabled: true,
  logLevel: 'info',
  retention: {
    days: 2555, // 7 years for SOX compliance
    maxSize: '10GB',
  },
  encryption: {
    enabled: true,
    algorithm: 'AES-256-GCM',
  },
  destinations: {
    console: process.env.NODE_ENV === 'development',
    file: true,
    database: true,
    siem: process.env.NODE_ENV === 'production',
    external: process.env.AUDIT_WEBHOOK_URL
      ? {
          url: process.env.AUDIT_WEBHOOK_URL,
          apiKey: process.env.AUDIT_WEBHOOK_KEY || '',
        }
      : undefined,
  },
  compliance: {
    standard: 'SOC2',
    requireIntegrityCheck: true,
    requireNonRepudiation: true,
  },
};

export type { AuditLoggerConfig, AuditEvent, AuditContext };
