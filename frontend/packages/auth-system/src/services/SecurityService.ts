/**
 * Security Service
 *
 * Provides comprehensive security functionality including event logging,
 * threat detection, security analysis, and audit trail management
 */

import type { AuthEvent, User, PortalVariant } from '../types';

interface SecurityEvent {
  id?: string;
  type: string;
  userId?: string;
  sessionId?: string;
  portalType: PortalVariant;
  ipAddress: string;
  userAgent: string;
  timestamp: Date;
  success: boolean;
  errorCode?: string;
  metadata?: Record<string, any>;
  riskLevel?: 'low' | 'medium' | 'high' | 'critical';
  threatDetected?: boolean;
}

interface SecurityAnalysis {
  riskScore: number;
  threats: string[];
  recommendations: string[];
  anomalies: SecurityAnomaly[];
}

interface SecurityAnomaly {
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  data: Record<string, any>;
}

interface LoginAttemptData {
  email?: string;
  portalId?: string;
  accountNumber?: string;
  partnerCode?: string;
  portalType: PortalVariant;
  ipAddress: string;
  userAgent: string;
}

interface SecurityValidation {
  allowed: boolean;
  reason?: string;
  message?: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

export class SecurityService {
  private events: Map<string, SecurityEvent[]> = new Map();
  private suspiciousIPs: Set<string> = new Set();
  private userSessions: Map<string, Date[]> = new Map();
  private readonly MAX_EVENTS_PER_USER = 1000;
  private readonly SUSPICIOUS_THRESHOLD = 10;

  constructor() {
    this.loadFromStorage();
    this.startPeriodicAnalysis();
  }

  /**
   * Validate login attempt for security threats
   */
  async validateLoginAttempt(data: LoginAttemptData): Promise<SecurityValidation> {
    const analysis = await this.analyzeLoginAttempt(data);

    // Check for immediate threats
    if (analysis.riskScore >= 90) {
      return {
        allowed: false,
        reason: 'HIGH_RISK',
        message: 'Login blocked due to security concerns. Please contact support.',
        riskLevel: 'critical',
      };
    }

    // Check for suspicious IP
    if (this.suspiciousIPs.has(data.ipAddress)) {
      return {
        allowed: false,
        reason: 'SUSPICIOUS_IP',
        message: 'Login blocked from suspicious IP address.',
        riskLevel: 'high',
      };
    }

    // Check for unusual patterns
    const anomalies = this.detectAnomalies(data);
    if (anomalies.some(a => a.severity === 'critical')) {
      return {
        allowed: false,
        reason: 'ANOMALY_DETECTED',
        message: 'Unusual login pattern detected. Additional verification required.',
        riskLevel: 'high',
      };
    }

    return {
      allowed: true,
      riskLevel: this.mapRiskScore(analysis.riskScore),
    };
  }

  /**
   * Record security event
   */
  async recordEvent(event: Omit<SecurityEvent, 'id'>): Promise<void> {
    const securityEvent: SecurityEvent = {
      ...event,
      id: this.generateEventId(),
      riskLevel: event.riskLevel || this.calculateRiskLevel(event),
      threatDetected: this.detectThreat(event),
    };

    // Store event
    const userId = event.userId || 'anonymous';
    const userEvents = this.events.get(userId) || [];
    userEvents.push(securityEvent);

    // Limit events per user
    if (userEvents.length > this.MAX_EVENTS_PER_USER) {
      userEvents.shift();
    }

    this.events.set(userId, userEvents);

    // Update suspicious IP tracking
    if (!securityEvent.success && securityEvent.type.includes('login')) {
      this.trackSuspiciousIP(securityEvent.ipAddress);
    }

    // Save to storage
    this.saveToStorage();

    // Report high-risk events
    if (securityEvent.riskLevel === 'critical') {
      await this.reportHighRiskEvent(securityEvent);
    }
  }

  /**
   * Get security events for a user
   */
  async getUserEvents(userId: string, limit: number = 50): Promise<AuthEvent[]> {
    const userEvents = this.events.get(userId) || [];

    return userEvents
      .slice(-limit)
      .map(event => ({
        id: event.id!,
        type: event.type as any, // Cast to match AuthEvent type
        timestamp: event.timestamp,
        success: event.success,
        ipAddress: event.ipAddress,
        userAgent: event.userAgent,
        portalType: event.portalType,
        metadata: event.metadata || {},
        riskLevel: event.riskLevel || 'low',
      }));
  }

  /**
   * Get all security events (admin function)
   */
  async getAllEvents(limit: number = 100): Promise<SecurityEvent[]> {
    const allEvents: SecurityEvent[] = [];

    for (const userEvents of this.events.values()) {
      allEvents.push(...userEvents);
    }

    return allEvents
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, limit);
  }

  /**
   * Analyze security posture for a user
   */
  async analyzeUserSecurity(userId: string): Promise<SecurityAnalysis> {
    const userEvents = this.events.get(userId) || [];
    const recentEvents = userEvents.filter(
      event => event.timestamp.getTime() > Date.now() - 24 * 60 * 60 * 1000
    );

    let riskScore = 0;
    const threats: string[] = [];
    const recommendations: string[] = [];
    const anomalies: SecurityAnomaly[] = [];

    // Analyze login patterns
    const loginEvents = recentEvents.filter(e => e.type.includes('login'));
    const failedLogins = loginEvents.filter(e => !e.success);

    if (failedLogins.length > 3) {
      riskScore += 30;
      threats.push('Multiple failed login attempts');
      recommendations.push('Enable two-factor authentication');
    }

    // Check for geographic anomalies
    const uniqueIPs = new Set(recentEvents.map(e => e.ipAddress));
    if (uniqueIPs.size > 5) {
      riskScore += 25;
      anomalies.push({
        type: 'geographic_anomaly',
        severity: 'medium',
        description: 'Logins from multiple IP addresses detected',
        data: { uniqueIPs: Array.from(uniqueIPs) },
      });
    }

    // Check for time-based anomalies
    const offHourLogins = recentEvents.filter(e => {
      const hour = e.timestamp.getHours();
      return hour < 6 || hour > 22;
    });

    if (offHourLogins.length > 2) {
      riskScore += 20;
      anomalies.push({
        type: 'temporal_anomaly',
        severity: 'low',
        description: 'Unusual login times detected',
        data: { offHourLogins: offHourLogins.length },
      });
    }

    // Check for suspicious user agents
    const userAgents = recentEvents.map(e => e.userAgent);
    const suspiciousAgents = userAgents.filter(ua => this.isSuspiciousUserAgent(ua));

    if (suspiciousAgents.length > 0) {
      riskScore += 40;
      threats.push('Suspicious user agent detected');
      anomalies.push({
        type: 'suspicious_agent',
        severity: 'high',
        description: 'Potentially automated access detected',
        data: { suspiciousAgents },
      });
    }

    // Generate recommendations
    if (riskScore > 50) {
      recommendations.push('Review recent account activity');
      recommendations.push('Change password immediately');
      recommendations.push('Enable security alerts');
    }

    if (riskScore > 70) {
      recommendations.push('Contact security team');
      recommendations.push('Consider temporary account suspension');
    }

    return {
      riskScore: Math.min(riskScore, 100),
      threats,
      recommendations,
      anomalies,
    };
  }

  /**
   * Detect security anomalies in login attempt
   */
  private detectAnomalies(data: LoginAttemptData): SecurityAnomaly[] {
    const anomalies: SecurityAnomaly[] = [];

    // Check for suspicious user agent
    if (this.isSuspiciousUserAgent(data.userAgent)) {
      anomalies.push({
        type: 'suspicious_user_agent',
        severity: 'high',
        description: 'Automated or suspicious user agent detected',
        data: { userAgent: data.userAgent },
      });
    }

    // Check for unusual portal access patterns
    if (this.isUnusualPortalAccess(data)) {
      anomalies.push({
        type: 'unusual_portal_access',
        severity: 'medium',
        description: 'Unusual portal access pattern detected',
        data: { portalType: data.portalType },
      });
    }

    return anomalies;
  }

  /**
   * Analyze login attempt for security risks
   */
  private async analyzeLoginAttempt(data: LoginAttemptData): Promise<SecurityAnalysis> {
    let riskScore = 0;
    const threats: string[] = [];
    const recommendations: string[] = [];

    // Check IP reputation
    if (this.suspiciousIPs.has(data.ipAddress)) {
      riskScore += 50;
      threats.push('Suspicious IP address');
    }

    // Analyze user agent
    if (this.isSuspiciousUserAgent(data.userAgent)) {
      riskScore += 30;
      threats.push('Suspicious user agent');
    }

    // Check for rapid-fire attempts
    const recentAttempts = this.getRecentAttemptsByIP(data.ipAddress);
    if (recentAttempts > 5) {
      riskScore += 40;
      threats.push('Rapid login attempts');
    }

    return {
      riskScore: Math.min(riskScore, 100),
      threats,
      recommendations,
      anomalies: this.detectAnomalies(data),
    };
  }

  /**
   * Check if user agent is suspicious
   */
  private isSuspiciousUserAgent(userAgent: string): boolean {
    const suspiciousPatterns = [
      /bot/i,
      /crawler/i,
      /spider/i,
      /scraper/i,
      /curl/i,
      /wget/i,
      /python/i,
      /java/i,
    ];

    return suspiciousPatterns.some(pattern => pattern.test(userAgent));
  }

  /**
   * Check for unusual portal access patterns
   */
  private isUnusualPortalAccess(data: LoginAttemptData): boolean {
    // This would typically analyze historical patterns
    // For now, implement basic checks

    const nightTime = new Date().getHours();
    const isNightAccess = nightTime < 6 || nightTime > 22;

    // Admin/management portals accessed at night might be suspicious
    const sensitivePortals = ['management-admin', 'admin'];

    return isNightAccess && sensitivePortals.includes(data.portalType);
  }

  /**
   * Get recent login attempts by IP address
   */
  private getRecentAttemptsByIP(ipAddress: string): number {
    let count = 0;
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;

    for (const userEvents of this.events.values()) {
      count += userEvents.filter(event =>
        event.ipAddress === ipAddress &&
        event.type.includes('login') &&
        event.timestamp.getTime() > fiveMinutesAgo
      ).length;
    }

    return count;
  }

  /**
   * Track suspicious IP addresses
   */
  private trackSuspiciousIP(ipAddress: string): void {
    const recentFailures = this.getRecentFailuresByIP(ipAddress);

    if (recentFailures >= this.SUSPICIOUS_THRESHOLD) {
      this.suspiciousIPs.add(ipAddress);

      // Auto-remove after 24 hours
      setTimeout(() => {
        this.suspiciousIPs.delete(ipAddress);
      }, 24 * 60 * 60 * 1000);
    }
  }

  /**
   * Get recent failures by IP address
   */
  private getRecentFailuresByIP(ipAddress: string): number {
    let count = 0;
    const oneHourAgo = Date.now() - 60 * 60 * 1000;

    for (const userEvents of this.events.values()) {
      count += userEvents.filter(event =>
        event.ipAddress === ipAddress &&
        !event.success &&
        event.timestamp.getTime() > oneHourAgo
      ).length;
    }

    return count;
  }

  /**
   * Calculate risk level for an event
   */
  private calculateRiskLevel(event: SecurityEvent): 'low' | 'medium' | 'high' | 'critical' {
    let score = 0;

    // Failed attempts increase risk
    if (!event.success) score += 20;

    // Login events are higher risk
    if (event.type.includes('login')) score += 10;

    // Suspicious user agent
    if (this.isSuspiciousUserAgent(event.userAgent)) score += 30;

    // Known suspicious IP
    if (this.suspiciousIPs.has(event.ipAddress)) score += 40;

    return this.mapRiskScore(score);
  }

  /**
   * Map numeric score to risk level
   */
  private mapRiskScore(score: number): 'low' | 'medium' | 'high' | 'critical' {
    if (score >= 80) return 'critical';
    if (score >= 60) return 'high';
    if (score >= 30) return 'medium';
    return 'low';
  }

  /**
   * Detect if event represents a threat
   */
  private detectThreat(event: SecurityEvent): boolean {
    // Multiple failed attempts
    if (!event.success && event.type.includes('login')) {
      const recentFailures = this.getRecentFailuresByIP(event.ipAddress);
      return recentFailures >= 3;
    }

    // Suspicious user agent
    if (this.isSuspiciousUserAgent(event.userAgent)) {
      return true;
    }

    // Known suspicious IP
    return this.suspiciousIPs.has(event.ipAddress);
  }

  /**
   * Report high-risk security events
   */
  private async reportHighRiskEvent(event: SecurityEvent): Promise<void> {
    console.warn('High-risk security event detected:', {
      id: event.id,
      type: event.type,
      userId: event.userId,
      ipAddress: event.ipAddress,
      timestamp: event.timestamp,
      riskLevel: event.riskLevel,
    });

    // In production, this would send alerts to security team
    // Could integrate with services like:
    // - Email notifications
    // - Slack/Teams webhooks
    // - Security incident management systems
    // - SIEM systems
  }

  /**
   * Get client IP address
   */
  async getClientIP(): Promise<string> {
    try {
      // In production, this would be provided by the server
      // or obtained through a service
      return 'client_ip_placeholder';
    } catch {
      return 'unknown';
    }
  }

  /**
   * Generate unique event ID
   */
  private generateEventId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  /**
   * Load security data from storage
   */
  private loadFromStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem('security_events');
      if (stored) {
        const data = JSON.parse(stored);

        // Convert stored data back to Map
        this.events = new Map();
        for (const [userId, events] of Object.entries(data.events || {})) {
          this.events.set(userId, (events as any[]).map(e => ({
            ...e,
            timestamp: new Date(e.timestamp),
          })));
        }

        // Load suspicious IPs
        if (data.suspiciousIPs) {
          this.suspiciousIPs = new Set(data.suspiciousIPs);
        }
      }
    } catch (error) {
      console.error('Failed to load security data:', error);
    }
  }

  /**
   * Save security data to storage
   */
  private saveToStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const data = {
        events: Object.fromEntries(this.events.entries()),
        suspiciousIPs: Array.from(this.suspiciousIPs),
        lastSaved: new Date().toISOString(),
      };

      localStorage.setItem('security_events', JSON.stringify(data));
    } catch (error) {
      console.error('Failed to save security data:', error);
    }
  }

  /**
   * Start periodic security analysis
   */
  private startPeriodicAnalysis(): void {
    // Clean up old events every hour
    setInterval(() => {
      this.cleanupOldEvents();
    }, 60 * 60 * 1000);

    // Save to storage every 5 minutes
    setInterval(() => {
      this.saveToStorage();
    }, 5 * 60 * 1000);
  }

  /**
   * Clean up old security events
   */
  private cleanupOldEvents(): void {
    const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;

    for (const [userId, events] of this.events.entries()) {
      const filteredEvents = events.filter(
        event => event.timestamp.getTime() > thirtyDaysAgo
      );

      if (filteredEvents.length === 0) {
        this.events.delete(userId);
      } else {
        this.events.set(userId, filteredEvents);
      }
    }

    this.saveToStorage();
  }

  /**
   * Get security statistics
   */
  async getSecurityStatistics(): Promise<{
    totalEvents: number;
    highRiskEvents: number;
    suspiciousIPs: number;
    threatEvents: number;
    topThreatTypes: Array<{ type: string; count: number }>;
  }> {
    let totalEvents = 0;
    let highRiskEvents = 0;
    let threatEvents = 0;
    const threatTypes: Map<string, number> = new Map();

    for (const userEvents of this.events.values()) {
      totalEvents += userEvents.length;

      for (const event of userEvents) {
        if (event.riskLevel === 'high' || event.riskLevel === 'critical') {
          highRiskEvents++;
        }

        if (event.threatDetected) {
          threatEvents++;
          const count = threatTypes.get(event.type) || 0;
          threatTypes.set(event.type, count + 1);
        }
      }
    }

    const topThreatTypes = Array.from(threatTypes.entries())
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    return {
      totalEvents,
      highRiskEvents,
      suspiciousIPs: this.suspiciousIPs.size,
      threatEvents,
      topThreatTypes,
    };
  }
}
