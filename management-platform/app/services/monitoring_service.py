"""
Monitoring service for metrics, alerts, and observability.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.monitoring_additional import (
    MetricRepository, AlertRepository, HealthCheckRepository, SLARecordRepository
)
from ..schemas.monitoring import (
    MetricCreate, AlertRuleCreate, AlertRule, AlertCreate,
    NotificationChannel, NotificationChannelCreate, LogEntryCreate,
    SyntheticCheckCreate, MetricQuery, LogQuery
)
from ..models.monitoring import Alert, Metric, HealthCheck, SLARecord
from ..core.plugins.service_integration import service_integration

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring, alerting, and observability operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.metric_repo = MetricRepository(db)
        self.alert_repo = AlertRepository(db)
        self.health_check_repo = HealthCheckRepository(db)
        self.sla_record_repo = SLARecordRepository(db)
    
    async def ingest_metrics(
        self,
        metrics: List[MetricCreate],
        source: Optional[str] = None
    ) -> bool:
        """Ingest multiple metrics."""
        try:
            for metric_data in metrics:
                metric_dict = metric_data.model_dump()
                await self.metric_repo.create(metric_dict, source)
            
            # Check for alert rule violations
            await self._evaluate_alert_rules(metrics)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest metrics: {e}")
            return False
    
    async def _evaluate_alert_rules(self, metrics: List[MetricCreate]):
        """Evaluate alert rules against incoming metrics."""
        for metric in metrics:
            # Get alert rules for this metric
            rules = await self.alert_rule_repo.get_by_metric(
                metric.tenant_id, metric.service_name, metric.metric_name
            )
            
            for rule in rules:
                if not rule.enabled:
                    continue
                
                # Check if metric violates rule
                violation = await self._check_rule_violation(rule, metric)
                if violation:
                    await self._handle_alert_violation(rule, metric)
    
    async def _check_rule_violation(self, rule: AlertRule, metric: MetricCreate) -> bool:
        """Check if a metric violates an alert rule."""
        try:
            if rule.condition == ">":
                return metric.value > rule.threshold
            elif rule.condition == "<":
                return metric.value < rule.threshold
            elif rule.condition == ">=":
                return metric.value >= rule.threshold
            elif rule.condition == "<=":
                return metric.value <= rule.threshold
            elif rule.condition == "==":
                return metric.value == rule.threshold
            elif rule.condition == "!=":
                return metric.value != rule.threshold
            
            return False
        except Exception as e:
            logger.error(f"Error checking rule violation: {e}")
            return False
    
    async def _handle_alert_violation(self, rule: AlertRule, metric: MetricCreate):
        """Handle an alert rule violation."""
        # Check if alert is already firing
        existing_alert = await self.alert_repo.get_active_alert(
            rule.id, self._generate_alert_fingerprint(rule, metric)
        )
        
        if existing_alert:
            return  # Alert already firing
        
        # Create new alert
        alert_data = {
            "tenant_id": metric.tenant_id,
            "rule_id": rule.id,
            "status": "firing",
            "severity": rule.severity,
            "message": f"{rule.name}: {metric.metric_name} {rule.condition} {rule.threshold} (current: {metric.value})",
            "started_at": datetime.utcnow(),
            "labels": {**rule.labels, **metric.labels},
            "annotations": rule.annotations,
            "fingerprint": self._generate_alert_fingerprint(rule, metric)
        }
        
        alert = await self.alert_repo.create(alert_data, "system")
        
        # Send notifications
        await self._send_alert_notifications(alert)
        
        logger.warning(f"Alert fired: {rule.name} for tenant {metric.tenant_id}")
    
    def _generate_alert_fingerprint(self, rule: AlertRule, metric: MetricCreate) -> str:
        """Generate unique fingerprint for an alert."""
        import hashlib
        
        data = f"{rule.id}-{metric.service_name}-{metric.metric_name}-{metric.labels}"
        return hashlib.md5(data.encode()).hexdigest()
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        # Get notification channels for the tenant
        channels = await self.notification_channel_repo.get_by_tenant(alert.tenant_id)
        
        for channel in channels:
            if not channel.enabled:
                continue
            
            # Check channel filters
            if not self._check_channel_filters(channel, alert):
                continue
            
            # Create notification record
            notification_data = {
                "tenant_id": alert.tenant_id,
                "alert_id": alert.id,
                "channel_id": channel.id,
                "status": "pending"
            }
            
            notification = await self.notification_repo.create(notification_data, "system")
            
            # Send notification
            await self._deliver_notification(notification, channel, alert)
    
    def _check_channel_filters(self, channel: NotificationChannel, alert: Alert) -> bool:
        """Check if alert matches channel filters."""
        filters = channel.filters
        if not filters:
            return True
        
        # Check severity filter
        if "severity" in filters:
            allowed_severities = filters["severity"]
            if isinstance(allowed_severities, list) and alert.severity not in allowed_severities:
                return False
        
        # Check label filters
        if "labels" in filters:
            label_filters = filters["labels"]
            for key, value in label_filters.items():
                if key not in alert.labels or alert.labels[key] != value:
                    return False
        
        return True
    
    async def _deliver_notification(
        self,
        notification,
        channel: NotificationChannel,
        alert: Alert
    ):
        """Deliver a notification through a channel."""
        try:
            await self.notification_repo.update_status(notification.id, "sending", "system")
            
            if channel.type == "email":
                await self._send_email_notification(channel, alert)
            elif channel.type == "slack":
                await self._send_slack_notification(channel, alert)
            elif channel.type == "webhook":
                await self._send_webhook_notification(channel, alert)
            
            await self.notification_repo.update(
                notification.id,
                {
                    "status": "delivered",
                    "delivered_at": datetime.utcnow()
                },
                "system"
            )
            
        except Exception as e:
            logger.error(f"Failed to deliver notification: {e}")
            await self.notification_repo.update(
                notification.id,
                {
                    "status": "failed",
                    "error_message": str(e)
                },
                "system"
            )
    
    async def _send_email_notification(self, channel: NotificationChannel, alert: Alert):
        """Send email notification via plugin."""
        try:
            alert_data = {
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "tenant_id": alert.tenant_id,
                "details": alert.metadata or {}
            }
            
            recipients = channel.configuration.get('recipients', [])
            success = await service_integration.send_notification(
                'email', alert.message, recipients, {'subject': f'Alert: {alert.alert_type}'}
            )
            
            if success:
                logger.info(f"Email notification sent for alert {alert.id}")
            else:
                logger.error(f"Failed to send email notification for alert {alert.id}")
                
        except Exception as e:
            logger.error(f"Email notification error for alert {alert.id}: {e}")
    
    async def _send_slack_notification(self, channel: NotificationChannel, alert: Alert):
        """Send Slack notification via plugin."""
        try:
            alert_data = {
                "type": alert.alert_type,
                "severity": alert.severity, 
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "tenant_id": alert.tenant_id,
                "details": alert.metadata or {},
                "channel": channel.configuration.get('channel', '#alerts')
            }
            
            recipients = channel.configuration.get('recipients', [])
            success = await service_integration.send_alert_via_plugins(alert_data, ['slack'])
            
            if success.get('slack', False):
                logger.info(f"Slack notification sent for alert {alert.id}")
            else:
                logger.error(f"Failed to send Slack notification for alert {alert.id}")
                
        except Exception as e:
            logger.error(f"Slack notification error for alert {alert.id}: {e}")
    
    async def _send_webhook_notification(self, channel: NotificationChannel, alert: Alert):
        """Send webhook notification."""
        try:
            import aiohttp
            
            webhook_url = channel.configuration.get('webhook_url')
            if not webhook_url:
                logger.error(f"No webhook URL configured for channel {channel.id}")
                return
            
            alert_payload = {
                "alert_id": str(alert.id),
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "tenant_id": str(alert.tenant_id),
                "metadata": alert.metadata or {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=alert_payload) as response:
                    if response.status == 200:
                        logger.info(f"Webhook notification sent for alert {alert.id}")
                    else:
                        logger.error(f"Webhook notification failed for alert {alert.id}: {response.status}")
                        
        except Exception as e:
            logger.error(f"Webhook notification error for alert {alert.id}: {e}")
    
    async def create_alert_rule(
        self,
        rule_data: AlertRuleCreate,
        created_by: str
    ) -> AlertRule:
        """Create a new alert rule."""
        try:
            rule_dict = rule_data.model_dump()
            rule = await self.alert_rule_repo.create(rule_dict, created_by)
            
            logger.info(f"Alert rule created: {rule.name} (ID: {rule.id})")
            return rule
            
        except Exception as e:
            logger.error(f"Failed to create alert rule: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create alert rule"
            )
    
    async def create_notification_channel(
        self,
        channel_data: NotificationChannelCreate,
        created_by: str
    ) -> NotificationChannel:
        """Create a new notification channel."""
        try:
            # Validate channel configuration based on type
            await self._validate_channel_configuration(
                channel_data.type, channel_data.configuration
            )
            
            channel_dict = channel_data.model_dump()
            channel = await self.notification_channel_repo.create(channel_dict, created_by)
            
            logger.info(f"Notification channel created: {channel.name} (ID: {channel.id})")
            return channel
            
        except Exception as e:
            logger.error(f"Failed to create notification channel: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create notification channel"
            )
    
    async def _validate_channel_configuration(self, channel_type: str, config: Dict[str, Any]):
        """Validate notification channel configuration."""
        if channel_type == "email":
            required_fields = ["to", "smtp_server"]
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field for email channel: {field}")
        
        elif channel_type == "slack":
            required_fields = ["webhook_url"]
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field for Slack channel: {field}")
        
        elif channel_type == "webhook":
            required_fields = ["url"]
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field for webhook channel: {field}")
    
    async def query_metrics(
        self,
        tenant_id: UUID,
        query: MetricQuery
    ) -> Dict[str, Any]:
        """Query metrics with time range and filters."""
        try:
            metrics = await self.metric_repo.query_metrics(
                tenant_id=tenant_id,
                query=query.query,
                start_time=query.start_time,
                end_time=query.end_time,
                step=query.step,
                labels=query.labels
            )
            
            # Group metrics by labels for time series response
            series_data = {}
            for metric in metrics:
                key = f"{metric.service_name}.{metric.metric_name}"
                if key not in series_data:
                    series_data[key] = {
                        "metric": {
                            "service": metric.service_name,
                            "name": metric.metric_name,
                            **metric.labels
                        },
                        "values": []
                    }
                
                series_data[key]["values"].append([
                    metric.timestamp.timestamp(),
                    str(metric.value)
                ])
            
            return {
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": list(series_data.values())
                },
                "query": query.query,
                "execution_time": 0.1  # TODO: Measure actual execution time
            }
            
        except Exception as e:
            logger.error(f"Failed to query metrics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to query metrics"
            )
    
    async def query_logs(
        self,
        tenant_id: UUID,
        query: LogQuery
    ) -> List[Dict[str, Any]]:
        """Query logs with filters and time range."""
        try:
            logs = await self.log_repo.query_logs(
                tenant_id=tenant_id,
                query=query.query,
                start_time=query.start_time,
                end_time=query.end_time,
                limit=query.limit,
                labels=query.labels
            )
            
            return [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "service": log.service_name,
                    "level": log.level,
                    "message": log.message,
                    "source": log.source,
                    "trace_id": log.trace_id,
                    "span_id": log.span_id,
                    "labels": log.labels,
                    "structured_data": log.structured_data
                }
                for log in logs
            ]
            
        except Exception as e:
            logger.error(f"Failed to query logs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to query logs"
            )
    
    async def ingest_logs(
        self,
        logs: List[LogEntryCreate],
        source: Optional[str] = None
    ) -> bool:
        """Ingest multiple log entries."""
        try:
            for log_data in logs:
                log_dict = log_data.model_dump()
                await self.log_repo.create(log_dict, source)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest logs: {e}")
            return False
    
    async def get_service_health_status(
        self,
        tenant_id: UUID,
        service_name: str
    ) -> Dict[str, Any]:
        """Get health status for a specific service."""
        try:
            # Get recent metrics for the service
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            # Get error rate
            error_metrics = await self.metric_repo.get_service_metrics(
                tenant_id, service_name, "error_rate", start_time, end_time
            )
            error_rate = error_metrics[-1].value if error_metrics else 0.0
            
            # Get response time
            response_metrics = await self.metric_repo.get_service_metrics(
                tenant_id, service_name, "response_time_p95", start_time, end_time
            )
            response_time_p95 = response_metrics[-1].value if response_metrics else 0.0
            
            # Get uptime
            uptime_metrics = await self.metric_repo.get_service_metrics(
                tenant_id, service_name, "uptime", start_time, end_time
            )
            uptime_percentage = uptime_metrics[-1].value if uptime_metrics else 100.0
            
            # Get active alerts
            active_alerts = await self.alert_repo.get_active_alerts_for_service(
                tenant_id, service_name
            )
            
            # Determine overall status
            if error_rate > 5.0 or uptime_percentage < 95.0:
                status = "critical"
            elif error_rate > 1.0 or response_time_p95 > 1000:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "service_name": service_name,
                "status": status,
                "uptime_percentage": uptime_percentage,
                "error_rate": error_rate,
                "response_time_p95": response_time_p95,
                "last_deployment": None,  # TODO: Get from deployment service
                "active_alerts": len(active_alerts),
                "resource_usage": await self._get_service_resource_usage(tenant_id, service_name)
            }
            
        except Exception as e:
            logger.error(f"Failed to get service health status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get service health status"
            )
    
    async def _get_service_resource_usage(
        self,
        tenant_id: UUID,
        service_name: str
    ) -> Dict[str, float]:
        """Get resource usage metrics for a service."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)
            
            metrics = {}
            for metric_name in ["cpu_usage", "memory_usage", "disk_usage", "network_usage"]:
                metric_data = await self.metric_repo.get_service_metrics(
                    tenant_id, service_name, metric_name, start_time, end_time
                )
                metrics[metric_name.replace("_usage", "")] = metric_data[-1].value if metric_data else 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            return {"cpu": 0.0, "memory": 0.0, "disk": 0.0, "network": 0.0}
    
    async def get_tenant_monitoring_overview(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get comprehensive monitoring overview for a tenant."""
        try:
            # Get service health statuses
            services = await self.metric_repo.get_tenant_services(tenant_id)
            service_health = []
            
            for service_name in services:
                health = await self.get_service_health_status(tenant_id, service_name)
                service_health.append(health)
            
            # Get alert counts
            alerts = await self.alert_repo.get_active_alerts(tenant_id)
            critical_alerts = sum(1 for a in alerts if a.severity == "critical")
            
            # Calculate overall metrics
            total_services = len(service_health)
            avg_response_time = sum(s["response_time_p95"] for s in service_health) / max(total_services, 1)
            avg_uptime = sum(s["uptime_percentage"] for s in service_health) / max(total_services, 1)
            avg_error_rate = sum(s["error_rate"] for s in service_health) / max(total_services, 1)
            
            # Get storage metrics
            total_metrics = await self.metric_repo.count_tenant_metrics(tenant_id)
            total_logs = await self.log_repo.count_tenant_logs(tenant_id)
            
            return {
                "tenant_id": tenant_id,
                "services_monitored": total_services,
                "active_alerts": len(alerts),
                "critical_alerts": critical_alerts,
                "avg_response_time": avg_response_time,
                "uptime_percentage": avg_uptime,
                "error_rate": avg_error_rate,
                "total_metrics_stored": total_metrics,
                "total_logs_stored": total_logs,
                "monitoring_cost": None,  # TODO: Calculate from usage
                "service_health": service_health,
                "recent_alerts": alerts[:5]
            }
            
        except Exception as e:
            logger.error(f"Failed to get monitoring overview: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get monitoring overview"
            )
    
    async def resolve_alert(
        self,
        alert_id: UUID,
        resolved_by: str,
        resolution_note: Optional[str] = None
    ) -> bool:
        """Manually resolve an alert."""
        try:
            alert = await self.alert_repo.get_by_id(alert_id)
            if not alert:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Alert not found"
                )
            
            if alert.status == "resolved":
                return True  # Already resolved
            
            # Update alert status
            update_data = {
                "status": "resolved",
                "resolved_at": datetime.utcnow()
            }
            
            if resolution_note:
                update_data["annotations"] = {
                    **alert.annotations,
                    "resolution_note": resolution_note
                }
            
            await self.alert_repo.update(alert_id, update_data, resolved_by)
            
            logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    async def create_synthetic_check(
        self,
        check_data: SyntheticCheckCreate,
        created_by: str
    ) -> bool:
        """Create a synthetic monitoring check."""
        try:
            check_dict = check_data.model_dump()
            check = await self.synthetic_repo.create(check_dict, created_by)
            
            # TODO: Schedule synthetic check execution
            logger.info(f"Synthetic check created: {check.name} (ID: {check.id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create synthetic check: {e}")
            return False