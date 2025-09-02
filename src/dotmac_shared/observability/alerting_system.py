"""
Comprehensive alerting and notification system for DotMac monitoring.
Provides multi-channel alerting with escalation policies and smart routing.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import smtplib
import requests
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from .logging import get_logger, business_logger
from .otel import get_tracer

logger = get_logger("dotmac.alerting")

class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning" 
    INFO = "info"
    DEBUG = "debug"

class AlertStatus(Enum):
    """Alert status values."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"

class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"

@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    name: str
    metric: str
    condition: str  # e.g., "> 5", "< 99.9", "!= 0"
    threshold: float
    severity: AlertSeverity
    duration_minutes: int = 5  # How long condition must persist
    cooldown_minutes: int = 30  # Minimum time between alerts
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    runbook_url: str = ""

@dataclass 
class NotificationTarget:
    """Configuration for notification targets."""
    name: str
    channel: NotificationChannel
    config: Dict[str, Any]  # Channel-specific configuration
    severities: List[AlertSeverity] = field(default_factory=lambda: [AlertSeverity.CRITICAL, AlertSeverity.WARNING])
    business_hours_only: bool = False
    escalation_delay_minutes: int = 0

@dataclass
class Alert:
    """Active alert instance."""
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    labels: Dict[str, str]
    started_at: datetime
    last_seen: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    notification_count: int = 0
    escalation_level: int = 0

class AlertManager:
    """
    Central alert management system with multi-channel notifications.
    
    Features:
    - Rule-based alerting with flexible conditions
    - Multi-channel notifications (email, Slack, webhooks, SMS)
    - Smart escalation policies
    - Alert grouping and deduplication
    - Business hours awareness
    - Notification rate limiting
    """
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_targets: Dict[str, NotificationTarget] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_queue: asyncio.Queue = asyncio.Queue()
        
        # Escalation policies
        self.escalation_policies: Dict[str, List[str]] = {}
        
        # Notification channels
        self.notification_handlers: Dict[NotificationChannel, Callable] = {
            NotificationChannel.EMAIL: self._send_email,
            NotificationChannel.SLACK: self._send_slack,
            NotificationChannel.WEBHOOK: self._send_webhook,
            NotificationChannel.SMS: self._send_sms,
            NotificationChannel.PAGERDUTY: self._send_pagerduty,
        }
        
        # Initialize default rules and targets
        self._initialize_default_rules()
        self._initialize_default_targets()
        
        # Start background tasks
        asyncio.create_task(self._notification_processor())
        asyncio.create_task(self._alert_evaluator())
        asyncio.create_task(self._escalation_manager())
    
    def _initialize_default_rules(self):
        """Initialize default alert rules for DotMac monitoring."""
        default_rules = [
            # API Performance Rules
            AlertRule(
                name="high_error_rate",
                metric="dotmac_error_rate",
                condition="> 5.0",
                threshold=5.0,
                severity=AlertSeverity.WARNING,
                duration_minutes=5,
                description="API error rate is above 5%",
                runbook_url="https://docs.dotmac.com/runbooks/high-error-rate"
            ),
            AlertRule(
                name="critical_error_rate", 
                metric="dotmac_error_rate",
                condition="> 10.0",
                threshold=10.0,
                severity=AlertSeverity.CRITICAL,
                duration_minutes=2,
                description="API error rate is critically high (>10%)",
                runbook_url="https://docs.dotmac.com/runbooks/critical-error-rate"
            ),
            
            # System Resource Rules
            AlertRule(
                name="high_memory_usage",
                metric="dotmac_memory_usage_percent",
                condition="> 85.0",
                threshold=85.0,
                severity=AlertSeverity.WARNING,
                duration_minutes=10,
                description="System memory usage is above 85%"
            ),
            AlertRule(
                name="critical_memory_usage",
                metric="dotmac_memory_usage_percent", 
                condition="> 95.0",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                duration_minutes=5,
                description="System memory usage is critically high (>95%)"
            ),
            
            # Database Rules
            AlertRule(
                name="slow_database_queries",
                metric="dotmac_db_slow_queries_total",
                condition="> 10",
                threshold=10,
                severity=AlertSeverity.WARNING,
                duration_minutes=15,
                description="High number of slow database queries detected"
            ),
            AlertRule(
                name="database_connection_pool_exhaustion",
                metric="dotmac_database_connections_active",
                condition="> 90",
                threshold=90,
                severity=AlertSeverity.CRITICAL,
                duration_minutes=5,
                description="Database connection pool near exhaustion"
            ),
            
            # Business Logic Rules
            AlertRule(
                name="tenant_isolation_violation",
                metric="dotmac_tenant_isolation_violations_total",
                condition="> 0",
                threshold=0,
                severity=AlertSeverity.CRITICAL,
                duration_minutes=0,  # Immediate alert
                description="SECURITY: Tenant data isolation violation detected"
            ),
            AlertRule(
                name="payment_processing_failures",
                metric="dotmac_payments_failed_total",
                condition="> 5",
                threshold=5,
                severity=AlertSeverity.WARNING,
                duration_minutes=10,
                description="High number of payment processing failures"
            ),
            
            # SLA Rules  
            AlertRule(
                name="sla_breach_api_availability",
                metric="dotmac_sla_compliance_percent",
                condition="< 99.9",
                threshold=99.9,
                severity=AlertSeverity.CRITICAL,
                duration_minutes=5,
                labels={"service_type": "api_availability"},
                description="API availability SLA breach"
            ),
            
            # Partner Business Rules
            AlertRule(
                name="partner_performance_degradation",
                metric="dotmac_partner_performance_score",
                condition="< 60",
                threshold=60,
                severity=AlertSeverity.WARNING,
                duration_minutes=30,
                description="Partner performance score has degraded"
            ),
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.name] = rule
    
    def _initialize_default_targets(self):
        """Initialize default notification targets."""
        default_targets = [
            # Operations team email
            NotificationTarget(
                name="ops_team_email",
                channel=NotificationChannel.EMAIL,
                config={
                    "to": ["ops@dotmac.com"],
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "alerts@dotmac.com",
                    "password": "app_password"
                },
                severities=[AlertSeverity.CRITICAL, AlertSeverity.WARNING]
            ),
            
            # Critical alerts Slack channel
            NotificationTarget(
                name="critical_alerts_slack",
                channel=NotificationChannel.SLACK,
                config={
                    "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                    "channel": "#critical-alerts"
                },
                severities=[AlertSeverity.CRITICAL]
            ),
            
            # General operations Slack channel
            NotificationTarget(
                name="ops_alerts_slack",
                channel=NotificationChannel.SLACK,
                config={
                    "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                    "channel": "#ops-alerts"
                },
                severities=[AlertSeverity.WARNING, AlertSeverity.INFO]
            ),
            
            # PagerDuty for critical issues
            NotificationTarget(
                name="pagerduty_critical",
                channel=NotificationChannel.PAGERDUTY,
                config={
                    "integration_key": "YOUR_PAGERDUTY_INTEGRATION_KEY",
                    "service_key": "YOUR_PAGERDUTY_SERVICE_KEY"
                },
                severities=[AlertSeverity.CRITICAL],
                escalation_delay_minutes=15
            ),
        ]
        
        for target in default_targets:
            self.notification_targets[target.name] = target
    
    async def evaluate_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Evaluate a metric value against all applicable rules."""
        labels = labels or {}
        
        for rule_name, rule in self.alert_rules.items():
            if rule.metric != metric_name:
                continue
            
            # Check if labels match rule labels
            if rule.labels and not all(labels.get(k) == v for k, v in rule.labels.items()):
                continue
            
            # Evaluate condition
            is_triggered = self._evaluate_condition(value, rule.condition, rule.threshold)
            
            alert_key = f"{rule_name}:{':'.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
            
            if is_triggered:
                await self._handle_alert_triggered(alert_key, rule, value, labels)
            else:
                await self._handle_alert_resolved(alert_key)
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate if a condition is met."""
        try:
            if condition.startswith('>'):
                return value > threshold
            elif condition.startswith('<'):
                return value < threshold
            elif condition.startswith('>='):
                return value >= threshold  
            elif condition.startswith('<='):
                return value <= threshold
            elif condition.startswith('=='):
                return value == threshold
            elif condition.startswith('!='):
                return value != threshold
            else:
                return False
        except Exception as e:
            logger.error(f"Error evaluating condition: {condition}", error=str(e))
            return False
    
    async def _handle_alert_triggered(self, alert_key: str, rule: AlertRule, value: float, labels: Dict[str, str]):
        """Handle when an alert condition is triggered."""
        now = datetime.utcnow()
        
        if alert_key in self.active_alerts:
            # Update existing alert
            alert = self.active_alerts[alert_key]
            alert.last_seen = now
            
            # Check if duration threshold is met for notification
            if (now - alert.started_at).total_seconds() >= rule.duration_minutes * 60:
                await self._queue_notification(alert, value)
        else:
            # Create new alert
            alert = Alert(
                rule_name=rule.name,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                message=f"{rule.description} (current: {value}, threshold: {rule.threshold})",
                labels=labels,
                started_at=now,
                last_seen=now
            )
            
            self.active_alerts[alert_key] = alert
            
            # Log alert creation
            logger.warning(
                f"Alert triggered: {rule.name}",
                rule_name=rule.name,
                severity=rule.severity.value,
                value=value,
                threshold=rule.threshold,
                labels=labels
            )
            
            # Queue immediate notification if no duration requirement
            if rule.duration_minutes == 0:
                await self._queue_notification(alert, value)
    
    async def _handle_alert_resolved(self, alert_key: str):
        """Handle when an alert condition is resolved."""
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            
            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[alert_key]
            
            # Send resolution notification
            await self._queue_resolution_notification(alert)
            
            logger.info(
                f"Alert resolved: {alert.rule_name}",
                rule_name=alert.rule_name,
                duration_minutes=(alert.resolved_at - alert.started_at).total_seconds() / 60
            )
    
    async def _queue_notification(self, alert: Alert, current_value: float):
        """Queue a notification for processing."""
        now = datetime.utcnow()
        rule = self.alert_rules[alert.rule_name]
        
        # Check cooldown period
        if alert.notification_count > 0:
            time_since_last = (now - alert.last_seen).total_seconds() / 60
            if time_since_last < rule.cooldown_minutes:
                return
        
        notification_data = {
            "type": "alert",
            "alert": alert,
            "current_value": current_value,
            "rule": rule,
            "timestamp": now
        }
        
        await self.notification_queue.put(notification_data)
        alert.notification_count += 1
    
    async def _queue_resolution_notification(self, alert: Alert):
        """Queue a resolution notification."""
        notification_data = {
            "type": "resolution", 
            "alert": alert,
            "timestamp": datetime.utcnow()
        }
        
        await self.notification_queue.put(notification_data)
    
    async def _notification_processor(self):
        """Background task to process notification queue."""
        while True:
            try:
                notification_data = await self.notification_queue.get()
                await self._process_notification(notification_data)
            except Exception as e:
                logger.error("Error processing notification", error=str(e))
    
    async def _process_notification(self, notification_data: Dict[str, Any]):
        """Process a single notification."""
        alert = notification_data["alert"]
        notification_type = notification_data["type"]
        
        # Determine which targets should receive this notification
        applicable_targets = []
        for target in self.notification_targets.values():
            if alert.severity in target.severities:
                # Check business hours if required
                if target.business_hours_only and not self._is_business_hours():
                    continue
                applicable_targets.append(target)
        
        # Send notifications
        for target in applicable_targets:
            try:
                handler = self.notification_handlers[target.channel]
                await handler(target, alert, notification_data)
                
                logger.info(
                    f"Notification sent via {target.channel.value}",
                    target=target.name,
                    alert_rule=alert.rule_name,
                    severity=alert.severity.value
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to send notification via {target.channel.value}",
                    target=target.name,
                    error=str(e)
                )
    
    async def _send_email(self, target: NotificationTarget, alert: Alert, notification_data: Dict[str, Any]):
        """Send email notification."""
        config = target.config
        
        # Create message
        msg = MimeMultipart()
        msg['From'] = config.get('from', config['username'])
        msg['To'] = ', '.join(config['to'])
        
        if notification_data["type"] == "alert":
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            
            body = f"""
Alert: {alert.rule_name}
Severity: {alert.severity.value.upper()}
Status: {alert.status.value}
Message: {alert.message}
Started: {alert.started_at.isoformat()}
Current Value: {notification_data.get('current_value', 'N/A')}

Labels:
{chr(10).join(f'  {k}: {v}' for k, v in alert.labels.items())}

Runbook: {notification_data['rule'].runbook_url if notification_data['rule'].runbook_url else 'N/A'}
"""
        else:  # resolution
            msg['Subject'] = f"[RESOLVED] {alert.rule_name}"
            body = f"""
Alert Resolved: {alert.rule_name}
Duration: {(alert.resolved_at - alert.started_at).total_seconds() / 60:.1f} minutes
Resolved: {alert.resolved_at.isoformat()}
"""
        
        msg.attach(MimeText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['username'], config['password'])
            server.send_message(msg)
    
    async def _send_slack(self, target: NotificationTarget, alert: Alert, notification_data: Dict[str, Any]):
        """Send Slack notification."""
        config = target.config
        
        if notification_data["type"] == "alert":
            color = "danger" if alert.severity == AlertSeverity.CRITICAL else "warning"
            text = f"🚨 *{alert.rule_name}* - {alert.severity.value.upper()}"
        else:
            color = "good"
            text = f"✅ *Resolved: {alert.rule_name}*"
        
        payload = {
            "channel": config.get('channel', '#alerts'),
            "username": "DotMac Alerts",
            "icon_emoji": ":warning:",
            "attachments": [{
                "color": color,
                "title": text,
                "text": alert.message,
                "fields": [
                    {"title": "Started", "value": alert.started_at.isoformat(), "short": True},
                    {"title": "Status", "value": alert.status.value, "short": True},
                ] + [
                    {"title": k, "value": v, "short": True} 
                    for k, v in alert.labels.items()
                ],
                "ts": notification_data["timestamp"].timestamp()
            }]
        }
        
        async with asyncio.create_task(
            self._make_http_request("POST", config['webhook_url'], json=payload)
        ):
            pass
    
    async def _send_webhook(self, target: NotificationTarget, alert: Alert, notification_data: Dict[str, Any]):
        """Send webhook notification."""
        config = target.config
        
        payload = {
            "alert": {
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "labels": alert.labels,
                "started_at": alert.started_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            },
            "notification_type": notification_data["type"],
            "current_value": notification_data.get("current_value"),
            "timestamp": notification_data["timestamp"].isoformat(),
        }
        
        async with asyncio.create_task(
            self._make_http_request("POST", config['url'], json=payload)
        ):
            pass
    
    async def _send_sms(self, target: NotificationTarget, alert: Alert, notification_data: Dict[str, Any]):
        """Send SMS notification (placeholder - requires SMS provider)."""
        # This would integrate with an SMS provider like Twilio
        logger.info(f"SMS notification would be sent: {alert.rule_name}")
    
    async def _send_pagerduty(self, target: NotificationTarget, alert: Alert, notification_data: Dict[str, Any]):
        """Send PagerDuty notification."""
        config = target.config
        
        if notification_data["type"] == "alert":
            event_action = "trigger"
        else:
            event_action = "resolve"
        
        payload = {
            "routing_key": config['integration_key'],
            "event_action": event_action,
            "dedup_key": f"{alert.rule_name}:{':'.join(f'{k}={v}' for k, v in sorted(alert.labels.items()))}",
            "payload": {
                "summary": alert.message,
                "severity": alert.severity.value,
                "source": "dotmac-monitoring",
                "component": alert.labels.get("component", "unknown"),
                "custom_details": {
                    "rule_name": alert.rule_name,
                    "labels": alert.labels,
                    "current_value": notification_data.get("current_value"),
                }
            }
        }
        
        async with asyncio.create_task(
            self._make_http_request(
                "POST", 
                "https://events.pagerduty.com/v2/enqueue", 
                json=payload
            )
        ):
            pass
    
    async def _make_http_request(self, method: str, url: str, **kwargs):
        """Make async HTTP request."""
        # In a real implementation, you'd use aiohttp or similar
        # For now, we'll use requests in a thread
        import concurrent.futures
        import threading
        
        loop = asyncio.get_event_loop()
        
        def make_request():
            return requests.request(method, url, **kwargs)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            response = await loop.run_in_executor(executor, make_request)
            return response
    
    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours."""
        now = datetime.utcnow()
        # Assuming business hours are 9 AM to 5 PM UTC, Monday to Friday
        return (
            now.weekday() < 5 and  # Monday = 0, Friday = 4
            9 <= now.hour < 17
        )
    
    async def _alert_evaluator(self):
        """Background task to continuously evaluate alerts."""
        while True:
            try:
                await asyncio.sleep(60)  # Evaluate every minute
                # This would integrate with your metrics collection system
                # to automatically evaluate rules against current metric values
                
            except Exception as e:
                logger.error("Error in alert evaluation", error=str(e))
    
    async def _escalation_manager(self):
        """Background task to handle alert escalations."""
        while True:
            try:
                await asyncio.sleep(300)  # Check escalations every 5 minutes
                
                now = datetime.utcnow()
                for alert_key, alert in list(self.active_alerts.items()):
                    if alert.severity == AlertSeverity.CRITICAL and alert.status == AlertStatus.ACTIVE:
                        time_active = (now - alert.started_at).total_seconds() / 60
                        
                        # Escalate after 15 minutes for critical alerts
                        if time_active >= 15 and alert.escalation_level == 0:
                            await self._escalate_alert(alert)
                        # Further escalation after 30 minutes
                        elif time_active >= 30 and alert.escalation_level == 1:
                            await self._escalate_alert(alert)
                
            except Exception as e:
                logger.error("Error in escalation management", error=str(e))
    
    async def _escalate_alert(self, alert: Alert):
        """Escalate an alert to higher notification targets."""
        alert.escalation_level += 1
        
        business_logger.critical(
            f"Alert escalated: {alert.rule_name}",
            rule_name=alert.rule_name,
            escalation_level=alert.escalation_level,
            time_active_minutes=(datetime.utcnow() - alert.started_at).total_seconds() / 60
        )
        
        # Queue escalated notification
        notification_data = {
            "type": "escalation",
            "alert": alert,
            "escalation_level": alert.escalation_level,
            "timestamp": datetime.utcnow()
        }
        
        await self.notification_queue.put(notification_data)


# Global alert manager instance
alert_manager = AlertManager()

# Convenience functions
async def trigger_alert(metric_name: str, value: float, labels: Dict[str, str] = None):
    """Trigger alert evaluation for a metric."""
    await alert_manager.evaluate_metric(metric_name, value, labels)

def add_alert_rule(rule: AlertRule):
    """Add a new alert rule."""
    alert_manager.alert_rules[rule.name] = rule

def add_notification_target(target: NotificationTarget):
    """Add a new notification target."""
    alert_manager.notification_targets[target.name] = target