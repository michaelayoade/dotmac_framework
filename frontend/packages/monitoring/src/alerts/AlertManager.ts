/**
 * Production Alert Management System
 * Handles error thresholds, escalation policies, and notification routing
 */

interface AlertRule {
  id: string;
  name: string;
  condition: AlertCondition;
  threshold: AlertThreshold;
  escalation: EscalationPolicy;
  enabled: boolean;
  tags?: string[];
}

interface AlertCondition {
  metric: string;
  operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
  window: number; // Time window in minutes
  groupBy?: string[]; // Group alerts by these fields
}

interface AlertThreshold {
  warning: number;
  critical: number;
  recovery?: number; // Auto-recovery threshold
}

interface EscalationPolicy {
  levels: EscalationLevel[];
  maxEscalations: number;
  escalationDelay: number; // Minutes between escalations
}

interface EscalationLevel {
  level: number;
  channels: NotificationChannel[];
  acknowledgmentTimeout: number; // Minutes before escalating
}

interface NotificationChannel {
  type: 'email' | 'slack' | 'webhook' | 'sms' | 'pagerduty';
  config: Record<string, any>;
  enabled: boolean;
}

interface Alert {
  id: string;
  ruleId: string;
  severity: 'warning' | 'critical';
  status: 'open' | 'acknowledged' | 'resolved';
  title: string;
  description: string;
  tags: Record<string, string>;
  metadata: Record<string, any>;
  createdAt: number;
  acknowledgedAt?: number;
  resolvedAt?: number;
  acknowledgedBy?: string;
  escalationLevel: number;
  nextEscalationAt?: number;
}

export class AlertManager {
  private rules: Map<string, AlertRule> = new Map();
  private activeAlerts: Map<string, Alert> = new Map();
  private metricStore: Map<string, MetricValue[]> = new Map();
  private notificationChannels: Map<string, NotificationChannel> = new Map();
  private escalationTimers: Map<string, NodeJS.Timeout> = new Map();

  constructor() {
    this.setupDefaultRules();
    this.setupDefaultChannels();
    this.startMetricCleanup();
  }

  /**
   * Add a custom alert rule
   */
  addRule(rule: AlertRule): void {
    this.rules.set(rule.id, rule);
    console.log(`Alert rule added: ${rule.name}`);
  }

  /**
   * Remove an alert rule
   */
  removeRule(ruleId: string): void {
    this.rules.delete(ruleId);
    console.log(`Alert rule removed: ${ruleId}`);
  }

  /**
   * Add a notification channel
   */
  addNotificationChannel(id: string, channel: NotificationChannel): void {
    this.notificationChannels.set(id, channel);
    console.log(`Notification channel added: ${id} (${channel.type})`);
  }

  /**
   * Record a metric value for evaluation
   */
  recordMetric(metric: string, value: number, tags: Record<string, string> = {}): void {
    const metricValue: MetricValue = {
      value,
      timestamp: Date.now(),
      tags,
    };

    if (!this.metricStore.has(metric)) {
      this.metricStore.set(metric, []);
    }

    const values = this.metricStore.get(metric)!;
    values.push(metricValue);

    // Keep only last 24 hours of data
    const cutoffTime = Date.now() - (24 * 60 * 60 * 1000);
    this.metricStore.set(metric, values.filter(v => v.timestamp > cutoffTime));

    // Evaluate rules for this metric
    this.evaluateRulesForMetric(metric);
  }

  /**
   * Acknowledge an alert
   */
  acknowledgeAlert(alertId: string, acknowledgedBy: string): void {
    const alert = this.activeAlerts.get(alertId);
    if (!alert || alert.status !== 'open') return;

    alert.status = 'acknowledged';
    alert.acknowledgedAt = Date.now();
    alert.acknowledgedBy = acknowledgedBy;

    // Clear escalation timer
    const timer = this.escalationTimers.get(alertId);
    if (timer) {
      clearTimeout(timer);
      this.escalationTimers.delete(alertId);
    }

    console.log(`Alert acknowledged: ${alert.title} by ${acknowledgedBy}`);
    this.notifyAcknowledgment(alert);
  }

  /**
   * Resolve an alert
   */
  resolveAlert(alertId: string): void {
    const alert = this.activeAlerts.get(alertId);
    if (!alert) return;

    alert.status = 'resolved';
    alert.resolvedAt = Date.now();

    // Clear escalation timer
    const timer = this.escalationTimers.get(alertId);
    if (timer) {
      clearTimeout(timer);
      this.escalationTimers.delete(alertId);
    }

    this.activeAlerts.delete(alertId);
    console.log(`Alert resolved: ${alert.title}`);
    this.notifyResolution(alert);
  }

  /**
   * Get all active alerts
   */
  getActiveAlerts(): Alert[] {
    return Array.from(this.activeAlerts.values());
  }

  /**
   * Get alert statistics
   */
  getAlertStats(): {
    total: number;
    open: number;
    acknowledged: number;
    critical: number;
    warning: number;
    byRule: Record<string, number>;
  } {
    const alerts = Array.from(this.activeAlerts.values());
    
    return {
      total: alerts.length,
      open: alerts.filter(a => a.status === 'open').length,
      acknowledged: alerts.filter(a => a.status === 'acknowledged').length,
      critical: alerts.filter(a => a.severity === 'critical').length,
      warning: alerts.filter(a => a.severity === 'warning').length,
      byRule: alerts.reduce((acc, alert) => {
        acc[alert.ruleId] = (acc[alert.ruleId] || 0) + 1;
        return acc;
      }, {} as Record<string, number>),
    };
  }

  /**
   * Evaluate all rules for a given metric
   */
  private evaluateRulesForMetric(metric: string): void {
    for (const rule of this.rules.values()) {
      if (!rule.enabled || rule.condition.metric !== metric) continue;
      
      this.evaluateRule(rule);
    }
  }

  /**
   * Evaluate a specific rule
   */
  private evaluateRule(rule: AlertRule): void {
    const metrics = this.metricStore.get(rule.condition.metric);
    if (!metrics || metrics.length === 0) return;

    const windowStart = Date.now() - (rule.condition.window * 60 * 1000);
    const windowMetrics = metrics.filter(m => m.timestamp >= windowStart);
    
    if (windowMetrics.length === 0) return;

    // Group metrics if specified
    const groups = rule.condition.groupBy 
      ? this.groupMetricsByTags(windowMetrics, rule.condition.groupBy)
      : { '': windowMetrics };

    for (const [groupKey, groupMetrics] of Object.entries(groups)) {
      this.evaluateRuleForGroup(rule, groupKey, groupMetrics);
    }
  }

  /**
   * Evaluate a rule for a specific group of metrics
   */
  private evaluateRuleForGroup(rule: AlertRule, groupKey: string, metrics: MetricValue[]): void {
    const value = this.calculateMetricValue(metrics);
    const alertId = `${rule.id}-${groupKey}`;
    const existingAlert = this.activeAlerts.get(alertId);

    // Check for critical threshold
    if (this.evaluateCondition(value, rule.condition.operator, rule.threshold.critical)) {
      if (!existingAlert) {
        this.createAlert(rule, groupKey, 'critical', value, metrics[0]?.tags || {});
      } else if (existingAlert.severity === 'warning') {
        this.escalateAlert(existingAlert, 'critical');
      }
    }
    // Check for warning threshold
    else if (this.evaluateCondition(value, rule.condition.operator, rule.threshold.warning)) {
      if (!existingAlert) {
        this.createAlert(rule, groupKey, 'warning', value, metrics[0]?.tags || {});
      }
    }
    // Check for recovery
    else if (existingAlert && rule.threshold.recovery !== undefined) {
      if (this.evaluateCondition(value, this.getInverseOperator(rule.condition.operator), rule.threshold.recovery)) {
        this.resolveAlert(alertId);
      }
    }
  }

  /**
   * Create a new alert
   */
  private createAlert(
    rule: AlertRule, 
    groupKey: string, 
    severity: 'warning' | 'critical', 
    value: number, 
    tags: Record<string, string>
  ): void {
    const alertId = `${rule.id}-${groupKey}`;
    const alert: Alert = {
      id: alertId,
      ruleId: rule.id,
      severity,
      status: 'open',
      title: `${rule.name}${groupKey ? ` (${groupKey})` : ''}`,
      description: `${rule.condition.metric} ${rule.condition.operator} ${severity === 'critical' ? rule.threshold.critical : rule.threshold.warning} (current: ${value})`,
      tags,
      metadata: {
        metric: rule.condition.metric,
        currentValue: value,
        threshold: severity === 'critical' ? rule.threshold.critical : rule.threshold.warning,
        window: rule.condition.window,
      },
      createdAt: Date.now(),
      escalationLevel: 0,
    };

    this.activeAlerts.set(alertId, alert);
    console.log(`Alert created: ${alert.title} (${severity})`);
    
    this.sendNotification(alert, rule.escalation.levels[0]);
    this.scheduleEscalation(alert, rule.escalation);
  }

  /**
   * Escalate an existing alert
   */
  private escalateAlert(alert: Alert, newSeverity: 'critical'): void {
    const oldSeverity = alert.severity;
    alert.severity = newSeverity;
    
    console.log(`Alert escalated: ${alert.title} (${oldSeverity} → ${newSeverity})`);
    
    const rule = this.rules.get(alert.ruleId);
    if (rule) {
      this.sendNotification(alert, rule.escalation.levels[alert.escalationLevel]);
    }
  }

  /**
   * Schedule escalation for an alert
   */
  private scheduleEscalation(alert: Alert, policy: EscalationPolicy): void {
    if (alert.escalationLevel >= policy.levels.length - 1) return;

    const nextLevel = policy.levels[alert.escalationLevel];
    const escalationTime = nextLevel.acknowledgmentTimeout * 60 * 1000;
    
    const timer = setTimeout(() => {
      if (alert.status === 'open' && alert.escalationLevel < policy.maxEscalations) {
        alert.escalationLevel++;
        alert.nextEscalationAt = Date.now() + (policy.escalationDelay * 60 * 1000);
        
        console.log(`Alert escalated to level ${alert.escalationLevel}: ${alert.title}`);
        
        const rule = this.rules.get(alert.ruleId);
        if (rule && alert.escalationLevel < policy.levels.length) {
          this.sendNotification(alert, policy.levels[alert.escalationLevel]);
          this.scheduleEscalation(alert, policy);
        }
      }
    }, escalationTime);

    this.escalationTimers.set(alert.id, timer);
  }

  /**
   * Send notification for an alert
   */
  private async sendNotification(alert: Alert, level: EscalationLevel): Promise<void> {
    for (const channelConfig of level.channels) {
      if (!channelConfig.enabled) continue;

      try {
        await this.sendToChannel(alert, channelConfig);
      } catch (error) {
        console.error(`Failed to send notification to ${channelConfig.type}:`, error);
      }
    }
  }

  /**
   * Send notification to specific channel
   */
  private async sendToChannel(alert: Alert, channel: NotificationChannel): Promise<void> {
    switch (channel.type) {
      case 'email':
        await this.sendEmailNotification(alert, channel.config);
        break;
      case 'slack':
        await this.sendSlackNotification(alert, channel.config);
        break;
      case 'webhook':
        await this.sendWebhookNotification(alert, channel.config);
        break;
      case 'sms':
        await this.sendSMSNotification(alert, channel.config);
        break;
      case 'pagerduty':
        await this.sendPagerDutyNotification(alert, channel.config);
        break;
    }
  }

  /**
   * Send email notification
   */
  private async sendEmailNotification(alert: Alert, config: any): Promise<void> {
    // Implementation would integrate with email service
    console.log(`📧 Email notification: ${alert.title} to ${config.recipients}`);
  }

  /**
   * Send Slack notification
   */
  private async sendSlackNotification(alert: Alert, config: any): Promise<void> {
    // Implementation would integrate with Slack API
    console.log(`📱 Slack notification: ${alert.title} to ${config.channel}`);
  }

  /**
   * Send webhook notification
   */
  private async sendWebhookNotification(alert: Alert, config: any): Promise<void> {
    try {
      await fetch(config.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(config.headers || {}),
        },
        body: JSON.stringify({
          alert,
          timestamp: Date.now(),
        }),
      });
      console.log(`🔗 Webhook notification sent: ${alert.title}`);
    } catch (error) {
      console.error('Webhook notification failed:', error);
    }
  }

  /**
   * Send SMS notification
   */
  private async sendSMSNotification(alert: Alert, config: any): Promise<void> {
    // Implementation would integrate with SMS service
    console.log(`📲 SMS notification: ${alert.title} to ${config.phoneNumbers}`);
  }

  /**
   * Send PagerDuty notification
   */
  private async sendPagerDutyNotification(alert: Alert, config: any): Promise<void> {
    // Implementation would integrate with PagerDuty API
    console.log(`🚨 PagerDuty notification: ${alert.title}`);
  }

  /**
   * Notify about alert acknowledgment
   */
  private notifyAcknowledgment(alert: Alert): void {
    console.log(`✅ Alert acknowledged: ${alert.title} by ${alert.acknowledgedBy}`);
    // Send acknowledgment notifications if configured
  }

  /**
   * Notify about alert resolution
   */
  private notifyResolution(alert: Alert): void {
    console.log(`✅ Alert resolved: ${alert.title}`);
    // Send resolution notifications if configured
  }

  /**
   * Group metrics by specified tags
   */
  private groupMetricsByTags(metrics: MetricValue[], groupBy: string[]): Record<string, MetricValue[]> {
    return metrics.reduce((groups, metric) => {
      const key = groupBy.map(tag => `${tag}:${metric.tags[tag] || 'unknown'}`).join(',');
      if (!groups[key]) groups[key] = [];
      groups[key].push(metric);
      return groups;
    }, {} as Record<string, MetricValue[]>);
  }

  /**
   * Calculate aggregate value from metrics
   */
  private calculateMetricValue(metrics: MetricValue[]): number {
    // For now, use average. Could be configurable (sum, max, min, etc.)
    return metrics.reduce((sum, m) => sum + m.value, 0) / metrics.length;
  }

  /**
   * Evaluate condition
   */
  private evaluateCondition(value: number, operator: string, threshold: number): boolean {
    switch (operator) {
      case 'gt': return value > threshold;
      case 'gte': return value >= threshold;
      case 'lt': return value < threshold;
      case 'lte': return value <= threshold;
      case 'eq': return value === threshold;
      default: return false;
    }
  }

  /**
   * Get inverse operator for recovery conditions
   */
  private getInverseOperator(operator: string): string {
    const inverseMap: Record<string, string> = {
      'gt': 'lte',
      'gte': 'lt',
      'lt': 'gte',
      'lte': 'gt',
      'eq': 'eq',
    };
    return inverseMap[operator] || operator;
  }

  /**
   * Setup default alert rules
   */
  private setupDefaultRules(): void {
    // Error rate rule
    this.addRule({
      id: 'error-rate-high',
      name: 'High Error Rate',
      condition: {
        metric: 'error_rate',
        operator: 'gt',
        window: 5,
        groupBy: ['environment'],
      },
      threshold: {
        warning: 0.05, // 5%
        critical: 0.1,  // 10%
        recovery: 0.02, // 2%
      },
      escalation: {
        levels: [
          {
            level: 0,
            channels: [
              { type: 'slack', config: { channel: '#alerts' }, enabled: true }
            ],
            acknowledgmentTimeout: 15,
          },
          {
            level: 1,
            channels: [
              { type: 'email', config: { recipients: ['oncall@dotmac.com'] }, enabled: true }
            ],
            acknowledgmentTimeout: 30,
          },
        ],
        maxEscalations: 2,
        escalationDelay: 5,
      },
      enabled: true,
      tags: ['production', 'critical'],
    });

    // Response time rule
    this.addRule({
      id: 'response-time-high',
      name: 'High Response Time',
      condition: {
        metric: 'response_time',
        operator: 'gt',
        window: 10,
      },
      threshold: {
        warning: 2000, // 2 seconds
        critical: 5000, // 5 seconds
        recovery: 1000, // 1 second
      },
      escalation: {
        levels: [
          {
            level: 0,
            channels: [
              { type: 'slack', config: { channel: '#performance' }, enabled: true }
            ],
            acknowledgmentTimeout: 30,
          },
        ],
        maxEscalations: 1,
        escalationDelay: 10,
      },
      enabled: true,
      tags: ['performance'],
    });
  }

  /**
   * Setup default notification channels
   */
  private setupDefaultChannels(): void {
    this.addNotificationChannel('default-webhook', {
      type: 'webhook',
      config: {
        url: '/api/monitoring/alerts/webhook',
        headers: {
          'X-Alert-Source': 'dotmac-frontend',
        },
      },
      enabled: true,
    });
  }

  /**
   * Start cleanup process for old metrics
   */
  private startMetricCleanup(): void {
    setInterval(() => {
      const cutoffTime = Date.now() - (24 * 60 * 60 * 1000); // 24 hours
      
      for (const [metric, values] of this.metricStore.entries()) {
        const filteredValues = values.filter(v => v.timestamp > cutoffTime);
        this.metricStore.set(metric, filteredValues);
      }
    }, 60 * 60 * 1000); // Run every hour
  }
}

interface MetricValue {
  value: number;
  timestamp: number;
  tags: Record<string, string>;
}

// Global alert manager instance
let globalAlertManager: AlertManager | null = null;

/**
 * Initialize global alert manager
 */
export function initAlertManager(): AlertManager {
  globalAlertManager = new AlertManager();
  return globalAlertManager;
}

/**
 * Get global alert manager instance
 */
export function getAlertManager(): AlertManager | null {
  return globalAlertManager;
}

export type { AlertRule, Alert, NotificationChannel, EscalationPolicy };