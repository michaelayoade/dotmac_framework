"""
Dashboard and alerting configuration for workflow operations monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from dotmac_core_ops.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status."""

    FIRING = "firing"
    RESOLVED = "resolved"
    PENDING = "pending"


@dataclass
class AlertRule:
    """Alert rule definition."""

    name: str
    description: str
    query: str
    threshold: float
    severity: AlertSeverity
    duration: int = 300  # seconds
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class Alert:
    """Active alert instance."""

    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    value: float
    threshold: float
    started_at: datetime
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    @property
    def duration(self) -> timedelta:
        """Get alert duration."""
        end_time = self.resolved_at or utc_now()
        return end_time - self.started_at


class DashboardPanel:
    """Dashboard panel configuration."""

    def __init__(
        self,
        title: str,
        panel_type: str,
        query: str,
        unit: str = "",
        description: str = "",
        thresholds: Optional[List[Dict[str, Any]]] = None
    ):
        self.title = title
        self.panel_type = panel_type
        self.query = query
        self.unit = unit
        self.description = description
        self.thresholds = thresholds or []

    def to_grafana_panel(self, panel_id: int, grid_pos: Dict[str, int]) -> Dict[str, Any]:
        """Convert to Grafana panel format."""
        panel = {
            "id": panel_id,
            "title": self.title,
            "type": self.panel_type,
            "gridPos": grid_pos,
            "targets": [
                {
                    "expr": self.query,
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": self.unit,
                    "thresholds": {
                        "steps": [
                            {"color": "green", "value": None}
                        ] + [
                            {"color": threshold.get("color", "red"), "value": threshold["value"]}
                            for threshold in self.thresholds
                        ]
                    }
                }
            }
        }

        if self.description:
            panel["description"] = self.description

        return panel


class Dashboard:
    """Dashboard configuration."""

    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description
        self.panels: List[DashboardPanel] = []
        self.tags = ["dotmac", "workflow", "operations"]

    def add_panel(self, panel: DashboardPanel):
        """Add panel to dashboard."""
        self.panels.append(panel)

    def to_grafana_dashboard(self) -> Dict[str, Any]:
        """Convert to Grafana dashboard format."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": self.title,
                "description": self.description,
                "tags": self.tags,
                "timezone": "UTC",
                "panels": [],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s",
                "schemaVersion": 30,
                "version": 1
            }
        }

        # Add panels with grid positioning
        panel_id = 1
        y_pos = 0

        for i, panel in enumerate(self.panels):
            x_pos = (i % 2) * 12  # 2 panels per row
            if i > 0 and i % 2 == 0:
                y_pos += 8  # Move to next row

            grid_pos = {
                "h": 8,
                "w": 12,
                "x": x_pos,
                "y": y_pos
            }

            grafana_panel = panel.to_grafana_panel(panel_id, grid_pos)
            dashboard["dashboard"]["panels"].append(grafana_panel)
            panel_id += 1

        return dashboard


class AlertManager:
    """Alert manager for monitoring workflow operations."""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: List[Callable[[Alert], None]] = []
        self.evaluation_interval = 30  # seconds
        self.running = False
        self._evaluation_task: Optional[asyncio.Task] = None

    def add_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.rules[rule.name] = rule
        logger.info("Alert rule added", rule_name=rule.name, severity=rule.severity.value)

    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """Add notification handler."""
        self.notification_handlers.append(handler)

    async def start(self):
        """Start alert evaluation."""
        if self.running:
            return

        self.running = True
        self._evaluation_task = asyncio.create_task(self._evaluation_loop())
        logger.info("Alert manager started")

    async def stop(self):
        """Stop alert evaluation."""
        self.running = False

        if self._evaluation_task:
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass

        logger.info("Alert manager stopped")

    async def _evaluation_loop(self):
        """Main alert evaluation loop."""
        while self.running:
            try:
                await self._evaluate_rules()
                await asyncio.sleep(self.evaluation_interval)
            except Exception as e:
                logger.error("Alert evaluation error", error=str(e))
                await asyncio.sleep(self.evaluation_interval)

    async def _evaluate_rules(self):
        """Evaluate all alert rules."""
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            try:
                # In a real implementation, this would query the metrics backend
                # For now, we'll simulate metric evaluation
                current_value = await self._query_metric(rule.query)

                should_fire = self._should_fire_alert(rule, current_value)
                is_currently_firing = rule_name in self.active_alerts

                if should_fire and not is_currently_firing:
                    await self._fire_alert(rule, current_value)
                elif not should_fire and is_currently_firing:
                    await self._resolve_alert(rule_name)

            except Exception as e:
                logger.error("Rule evaluation error", rule_name=rule_name, error=str(e))

    def _should_fire_alert(self, rule: AlertRule, current_value: float) -> bool:
        """Determine if alert should fire."""
        # Simple threshold comparison - could be extended for more complex logic
        return current_value > rule.threshold

    async def _fire_alert(self, rule: AlertRule, current_value: float):
        """Fire an alert."""
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            value=current_value,
            threshold=rule.threshold,
            started_at=utc_now(),
            labels=rule.labels.copy(),
            annotations=rule.annotations.copy()
        )

        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)

        logger.warning(
            "Alert fired",
            rule_name=rule.name,
            severity=rule.severity.value,
            value=current_value,
            threshold=rule.threshold
        )

        # Send notifications
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error("Notification handler error", error=str(e))

    async def _resolve_alert(self, rule_name: str):
        """Resolve an alert."""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = utc_now()

            del self.active_alerts[rule_name]

            logger.info(
                "Alert resolved",
                rule_name=rule_name,
                duration=str(alert.duration)
            )

            # Send resolution notifications
            for handler in self.notification_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error("Notification handler error", error=str(e))

    async def _query_metric(self, query: str) -> float:
        """Query metric value (placeholder implementation)."""
        # In a real implementation, this would query Prometheus or similar
        # For now, return a simulated value
        import secrets
        return (secrets.randbelow(int((100) * 1000)) / 1000)

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts."""
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.started_at, reverse=True)

    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get alert history."""
        alerts = self.alert_history

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.started_at, reverse=True)[:limit]


class WorkflowDashboards:
    """Pre-configured dashboards for workflow monitoring."""

    @staticmethod
    def create_overview_dashboard() -> Dashboard:
        """Create workflow overview dashboard."""
        dashboard = Dashboard(
            "Workflow Operations Overview",
            "High-level metrics for workflow operations"
        )

        # Workflow runs panel
        dashboard.add_panel(DashboardPanel(
            title="Workflow Runs",
            panel_type="stat",
            query="sum(rate(workflow_runs_total[5m]))",
            unit="ops",
            description="Rate of workflow runs per second",
            thresholds=[{"value": 10, "color": "yellow"}, {"value": 50, "color": "red"}]
        ))

        # Active workflows panel
        dashboard.add_panel(DashboardPanel(
            title="Active Workflows",
            panel_type="stat",
            query="sum(workflow_runs_active)",
            unit="short",
            description="Number of currently active workflows"
        ))

        # Workflow duration panel
        dashboard.add_panel(DashboardPanel(
            title="Workflow Duration P95",
            panel_type="stat",
            query="histogram_quantile(0.95, rate(workflow_run_duration_seconds_bucket[5m]))",
            unit="s",
            description="95th percentile workflow duration",
            thresholds=[{"value": 300, "color": "yellow"}, {"value": 600, "color": "red"}]
        ))

        # Error rate panel
        dashboard.add_panel(DashboardPanel(
            title="Error Rate",
            panel_type="stat",
            query="sum(rate(errors_total[5m]))",
            unit="ops",
            description="Rate of errors per second",
            thresholds=[{"value": 1, "color": "yellow"}, {"value": 5, "color": "red"}]
        ))

        return dashboard

    @staticmethod
    def create_queue_dashboard() -> Dashboard:
        """Create queue monitoring dashboard."""
        dashboard = Dashboard(
            "Queue Operations",
            "Monitoring for job queues and processing"
        )

        # Queue lag panel
        dashboard.add_panel(DashboardPanel(
            title="Queue Lag",
            panel_type="graph",
            query="max(queue_lag_seconds) by (queue_name)",
            unit="s",
            description="Maximum queue lag by queue",
            thresholds=[{"value": 60, "color": "yellow"}, {"value": 300, "color": "red"}]
        ))

        # Queue size panel
        dashboard.add_panel(DashboardPanel(
            title="Queue Size",
            panel_type="graph",
            query="sum(queue_size) by (queue_name)",
            unit="short",
            description="Number of jobs in queue"
        ))

        # Processing duration panel
        dashboard.add_panel(DashboardPanel(
            title="Processing Duration P95",
            panel_type="graph",
            query="histogram_quantile(0.95, rate(queue_processing_duration_seconds_bucket[5m]))",
            unit="s",
            description="95th percentile processing duration"
        ))

        # DLQ size panel
        dashboard.add_panel(DashboardPanel(
            title="Dead Letter Queue Size",
            panel_type="stat",
            query="sum(dlq_size)",
            unit="short",
            description="Number of messages in DLQ",
            thresholds=[{"value": 10, "color": "yellow"}, {"value": 100, "color": "red"}]
        ))

        return dashboard

    @staticmethod
    def create_scheduler_dashboard() -> Dashboard:
        """Create scheduler monitoring dashboard."""
        dashboard = Dashboard(
            "Scheduler Operations",
            "Monitoring for scheduled job execution"
        )

        # Scheduler drift panel
        dashboard.add_panel(DashboardPanel(
            title="Scheduler Drift P95",
            panel_type="stat",
            query="histogram_quantile(0.95, rate(scheduler_drift_seconds_bucket[5m]))",
            unit="s",
            description="95th percentile scheduler drift",
            thresholds=[{"value": 60, "color": "yellow"}, {"value": 300, "color": "red"}]
        ))

        # Scheduled jobs panel
        dashboard.add_panel(DashboardPanel(
            title="Scheduled Jobs Rate",
            panel_type="graph",
            query="sum(rate(scheduled_jobs_total[5m])) by (status)",
            unit="ops",
            description="Rate of scheduled job executions"
        ))

        # Scheduler drift over time panel
        dashboard.add_panel(DashboardPanel(
            title="Scheduler Drift Over Time",
            panel_type="graph",
            query="scheduler_drift_seconds",
            unit="s",
            description="Scheduler drift over time"
        ))

        return dashboard


class WorkflowAlerts:
    """Pre-configured alerts for workflow monitoring."""

    @staticmethod
    def get_default_alert_rules() -> List[AlertRule]:
        """Get default alert rules for workflow operations."""
        return [
            # High error rate
            AlertRule(
                name="HighErrorRate",
                description="Error rate is above threshold",
                query="sum(rate(errors_total[5m]))",
                threshold=5.0,
                severity=AlertSeverity.CRITICAL,
                duration=300,
                labels={"component": "workflow"},
                annotations={
                    "summary": "High error rate detected",
                    "description": "Error rate is {{ $value }} errors/sec, above threshold of 5/sec"
                }
            ),

            # High queue lag
            AlertRule(
                name="HighQueueLag",
                description="Queue lag is above threshold",
                query="max(queue_lag_seconds)",
                threshold=300.0,
                severity=AlertSeverity.WARNING,
                duration=300,
                labels={"component": "queue"},
                annotations={
                    "summary": "High queue lag detected",
                    "description": "Queue lag is {{ $value }}s, above threshold of 300s"
                }
            ),

            # High scheduler drift
            AlertRule(
                name="HighSchedulerDrift",
                description="Scheduler drift is above threshold",
                query="histogram_quantile(0.95, rate(scheduler_drift_seconds_bucket[5m]))",
                threshold=60.0,
                severity=AlertSeverity.WARNING,
                duration=300,
                labels={"component": "scheduler"},
                annotations={
                    "summary": "High scheduler drift detected",
                    "description": "Scheduler drift P95 is {{ $value }}s, above threshold of 60s"
                }
            ),

            # Large DLQ size
            AlertRule(
                name="LargeDLQSize",
                description="Dead letter queue size is above threshold",
                query="sum(dlq_size)",
                threshold=100.0,
                severity=AlertSeverity.WARNING,
                duration=600,
                labels={"component": "queue"},
                annotations={
                    "summary": "Large DLQ size detected",
                    "description": "DLQ size is {{ $value }}, above threshold of 100"
                }
            ),

            # High step retry rate
            AlertRule(
                name="HighStepRetryRate",
                description="Step retry rate is above threshold",
                query="sum(rate(step_retries_total[5m]))",
                threshold=10.0,
                severity=AlertSeverity.WARNING,
                duration=300,
                labels={"component": "workflow"},
                annotations={
                    "summary": "High step retry rate detected",
                    "description": "Step retry rate is {{ $value }} retries/sec, above threshold of 10/sec"
                }
            ),

            # High rate limit hits
            AlertRule(
                name="HighRateLimitHits",
                description="Rate limit hits are above threshold",
                query="sum(rate(rate_limit_hits_total[5m]))",
                threshold=50.0,
                severity=AlertSeverity.WARNING,
                duration=300,
                labels={"component": "rate_limiter"},
                annotations={
                    "summary": "High rate limit hits detected",
                    "description": "Rate limit hits are {{ $value }} hits/sec, above threshold of 50/sec"
                }
            )
        ]


def slack_notification_handler(webhook_url: str) -> Callable[[Alert], None]:
    """Create Slack notification handler."""

    def handler(alert: Alert):
        """Send alert to Slack."""
        try:
            import requests

            color = {
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.INFO: "good"
            }.get(alert.severity, "warning")

            status_emoji = {
                AlertStatus.FIRING: "🔥",
                AlertStatus.RESOLVED: "✅",
                AlertStatus.PENDING: "⏳"
            }.get(alert.status, "❓")

            message = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"{status_emoji} {alert.rule_name}",
                        "text": alert.annotations.get("description", ""),
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Status",
                                "value": alert.status.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Value",
                                "value": f"{alert.value:.2f}",
                                "short": True
                            },
                            {
                                "title": "Threshold",
                                "value": f"{alert.threshold:.2f}",
                                "short": True
                            }
                        ],
                        "ts": int(alert.started_at.timestamp())
                    }
                ]
            }

            response = requests.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()

        except Exception as e:
            logger.error("Slack notification failed", error=str(e))

    return handler


def email_notification_handler(smtp_config: Dict[str, Any]) -> Callable[[Alert], None]:
    """Create email notification handler."""

    def handler(alert: Alert):
        """Send alert via email."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg['From'] = smtp_config['from_email']
            msg['To'] = smtp_config['to_email']
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"

            body = f"""
Alert: {alert.rule_name}
Status: {alert.status.value.upper()}
Severity: {alert.severity.value.upper()}
Value: {alert.value:.2f}
Threshold: {alert.threshold:.2f}
Started: {alert.started_at.isoformat()}

Description: {alert.annotations.get('description', 'No description')}
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
            if smtp_config.get('use_tls'):
                server.starttls()
            if smtp_config.get('username'):
                server.login(smtp_config['username'], smtp_config['password'])

            server.send_message(msg)
            server.quit()

        except Exception as e:
            logger.error("Email notification failed", error=str(e))

    return handler


# Global alert manager instance
_global_alert_manager = AlertManager()


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance."""
    return _global_alert_manager


async def setup_default_monitoring():
    """Set up default monitoring dashboards and alerts."""
    alert_manager = get_alert_manager()

    # Add default alert rules
    for rule in WorkflowAlerts.get_default_alert_rules():
        alert_manager.add_rule(rule)

    # Start alert manager
    await alert_manager.start()

    logger.info("Default monitoring setup completed")
