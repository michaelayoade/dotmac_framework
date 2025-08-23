"""
Cross-platform audit logging orchestrator.
Aggregates and coordinates audit trails between Management Platform and ISP Framework instances.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass
import uuid

# Import audit components
from .security.config_audit import (
    get_config_audit,
    ConfigurationAudit,
    AuditEvent,
    ChangeType,
    ChangeSource
)

logger = logging.getLogger(__name__)


class CrossPlatformAuditEvent(BaseModel):
    """Cross-platform audit event with tenant context."""
    # Base audit fields
    event_id: str
    timestamp: datetime
    platform: str  # "management-platform" or "isp-framework"
    tenant_id: Optional[str] = None
    
    # Standard audit fields
    change_type: ChangeType
    source: ChangeSource
    user_id: Optional[str] = None
    service: str
    environment: str
    
    # Change details
    field_path: str
    old_value_hash: Optional[str] = None
    new_value_hash: Optional[str] = None
    change_reason: Optional[str] = None
    
    # Cross-platform context
    platform_instance_id: str
    tenant_deployment_id: Optional[str] = None
    plugin_context: Optional[Dict[str, str]] = None
    
    # Correlation
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    related_events: List[str] = Field(default_factory=list)
    
    # Compliance and security
    compliance_impact: bool = False
    security_impact: bool = False
    audit_trail_complete: bool = True


class AuditAggregationRule(BaseModel):
    """Rules for aggregating audit events across platforms."""
    rule_id: str
    name: str
    description: str
    
    # Matching criteria
    tenant_id_pattern: Optional[str] = None
    service_pattern: Optional[str] = None
    field_path_pattern: Optional[str] = None
    change_type_filter: Optional[List[ChangeType]] = None
    
    # Aggregation settings
    aggregation_window_minutes: int = 60
    correlation_fields: List[str] = Field(default_factory=list)
    require_cross_platform: bool = False
    
    # Actions
    create_summary_event: bool = True
    notify_compliance_team: bool = False
    escalate_to_security: bool = False


class TenantAuditSummary(BaseModel):
    """Audit summary for a specific tenant."""
    tenant_id: str
    summary_period_start: datetime
    summary_period_end: datetime
    
    # Event counts by platform
    management_platform_events: int = 0
    isp_framework_events: int = 0
    total_events: int = 0
    
    # Event types
    configuration_changes: int = 0
    security_events: int = 0
    plugin_events: int = 0
    deployment_events: int = 0
    
    # Risk indicators
    high_risk_changes: int = 0
    compliance_violations: int = 0
    failed_operations: int = 0
    
    # Top users and services
    top_users: List[Dict[str, int]] = Field(default_factory=list)
    top_services: List[Dict[str, int]] = Field(default_factory=list)
    
    # Recommendations
    audit_recommendations: List[str] = Field(default_factory=list)


class CrossPlatformAuditOrchestrator:
    """
    Orchestrates audit logging across Management Platform and ISP Framework instances.
    Provides unified audit trails, compliance reporting, and security analysis.
    """
    
    def __init__(
        self,
        storage_path: str = "/var/log/dotmac/cross-platform-audit",
        aggregation_interval: int = 300,  # 5 minutes
        retention_days: int = 2555,  # 7 years for compliance
        enable_real_time_correlation: bool = True
    ):
        """
        Initialize cross-platform audit orchestrator.
        
        Args:
            storage_path: Path to store aggregated audit logs
            aggregation_interval: Interval for aggregating events (seconds)
            retention_days: Audit log retention period
            enable_real_time_correlation: Enable real-time event correlation
        """
        self.storage_path = storage_path
        self.aggregation_interval = aggregation_interval
        self.retention_days = retention_days
        self.enable_real_time_correlation = enable_real_time_correlation
        
        # Create storage directories
        os.makedirs(storage_path, exist_ok=True)
        os.makedirs(f"{storage_path}/events", exist_ok=True)
        os.makedirs(f"{storage_path}/summaries", exist_ok=True)
        os.makedirs(f"{storage_path}/correlations", exist_ok=True)
        
        # State management
        self.aggregation_rules: List[AuditAggregationRule] = []
        self.tenant_audit_cache: Dict[str, List[CrossPlatformAuditEvent]] = {}
        self.correlation_cache: Dict[str, List[str]] = {}
        
        # Load default aggregation rules
        self._load_default_aggregation_rules()
        
        # Start background tasks
        if enable_real_time_correlation:
            asyncio.create_task(self._correlation_processor())
        asyncio.create_task(self._aggregation_processor())
    
    def _load_default_aggregation_rules(self):
        """Load default audit aggregation rules."""
        default_rules = [
            AuditAggregationRule(
                rule_id="tenant_deployment_changes",
                name="Tenant Deployment Configuration Changes",
                description="Aggregate configuration changes during tenant deployments",
                service_pattern="deployment.*",
                aggregation_window_minutes=30,
                correlation_fields=["tenant_id", "deployment_id"],
                require_cross_platform=True,
                create_summary_event=True
            ),
            AuditAggregationRule(
                rule_id="plugin_licensing_events",
                name="Plugin Licensing Events",
                description="Aggregate plugin licensing and usage events",
                field_path_pattern=".*plugin.*",
                change_type_filter=[ChangeType.CREATE, ChangeType.UPDATE, ChangeType.DELETE],
                aggregation_window_minutes=60,
                correlation_fields=["tenant_id", "plugin_id"],
                create_summary_event=True
            ),
            AuditAggregationRule(
                rule_id="security_configuration_changes",
                name="Security Configuration Changes",
                description="Aggregate security-related configuration changes",
                field_path_pattern=".*(secret|password|key|token|security).*",
                aggregation_window_minutes=15,
                correlation_fields=["tenant_id", "user_id"],
                notify_compliance_team=True,
                escalate_to_security=True
            ),
            AuditAggregationRule(
                rule_id="cross_platform_user_actions",
                name="Cross-Platform User Actions",
                description="Correlate user actions across management platform and ISP framework",
                aggregation_window_minutes=120,
                correlation_fields=["user_id", "session_id"],
                require_cross_platform=True,
                create_summary_event=True
            )
        ]
        
        self.aggregation_rules.extend(default_rules)
        logger.info(f"Loaded {len(default_rules)} default aggregation rules")
    
    async def log_cross_platform_event(
        self,
        platform: str,
        tenant_id: Optional[str],
        audit_event: AuditEvent,
        platform_instance_id: str,
        tenant_deployment_id: Optional[str] = None,
        plugin_context: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Log a cross-platform audit event.
        
        Args:
            platform: Platform name ("management-platform" or "isp-framework")
            tenant_id: Tenant identifier
            audit_event: Base audit event
            platform_instance_id: Platform instance identifier
            tenant_deployment_id: Tenant deployment identifier
            plugin_context: Plugin-specific context
            
        Returns:
            Cross-platform event ID
        """
        # Create cross-platform event
        cross_event = CrossPlatformAuditEvent(
            event_id=f"xp-{uuid.uuid4()}",
            timestamp=audit_event.timestamp,
            platform=platform,
            tenant_id=tenant_id,
            change_type=audit_event.change_type,
            source=audit_event.source,
            user_id=audit_event.user_id,
            service=audit_event.service,
            environment=audit_event.environment,
            field_path=audit_event.field_path,
            old_value_hash=audit_event.old_value_hash,
            new_value_hash=audit_event.new_value_hash,
            change_reason=audit_event.change_reason,
            platform_instance_id=platform_instance_id,
            tenant_deployment_id=tenant_deployment_id,
            plugin_context=plugin_context or {},
            compliance_impact=self._assess_compliance_impact(audit_event),
            security_impact=self._assess_security_impact(audit_event)
        )
        
        # Store event
        await self._store_cross_platform_event(cross_event)
        
        # Add to tenant cache for real-time correlation
        if tenant_id:
            if tenant_id not in self.tenant_audit_cache:
                self.tenant_audit_cache[tenant_id] = []
            self.tenant_audit_cache[tenant_id].append(cross_event)
            
            # Limit cache size
            if len(self.tenant_audit_cache[tenant_id]) > 1000:
                self.tenant_audit_cache[tenant_id] = self.tenant_audit_cache[tenant_id][-500:]
        
        # Trigger real-time correlation
        if self.enable_real_time_correlation:
            await self._correlate_event(cross_event)
        
        logger.info(f"Logged cross-platform audit event: {cross_event.event_id}")
        return cross_event.event_id
    
    async def _store_cross_platform_event(self, event: CrossPlatformAuditEvent):
        """Store cross-platform audit event."""
        # Daily log file
        log_date = event.timestamp.strftime("%Y-%m-%d")
        log_file = f"{self.storage_path}/events/cross-platform-audit-{log_date}.jsonl"
        
        # Write event as JSON line
        with open(log_file, 'a') as f:
            f.write(json.dumps(event.dict(), default=str) + '\n')
        
        # Set secure permissions
        os.chmod(log_file, 0o640)
    
    def _assess_compliance_impact(self, audit_event: AuditEvent) -> bool:
        """Assess if audit event has compliance impact."""
        compliance_patterns = [
            "gdpr", "pci", "soc2", "hipaa", "customer_data", "payment",
            "personal_information", "privacy", "consent", "retention"
        ]
        
        field_path_lower = audit_event.field_path.lower()
        return any(pattern in field_path_lower for pattern in compliance_patterns)
    
    def _assess_security_impact(self, audit_event: AuditEvent) -> bool:
        """Assess if audit event has security impact."""
        security_patterns = [
            "secret", "password", "key", "token", "certificate", "auth",
            "permission", "role", "access", "security", "encryption",
            "ssl", "tls", "firewall", "cors"
        ]
        
        field_path_lower = audit_event.field_path.lower()
        change_reason_lower = (audit_event.change_reason or "").lower()
        
        return (
            any(pattern in field_path_lower for pattern in security_patterns) or
            any(pattern in change_reason_lower for pattern in security_patterns) or
            audit_event.change_type in [ChangeType.ENCRYPT, ChangeType.DECRYPT, ChangeType.ROTATE]
        )
    
    async def _correlate_event(self, event: CrossPlatformAuditEvent):
        """Correlate event with other events in real-time."""
        correlation_keys = []
        
        # Generate correlation keys
        if event.tenant_id:
            correlation_keys.append(f"tenant:{event.tenant_id}")
        if event.user_id:
            correlation_keys.append(f"user:{event.user_id}")
        if event.tenant_deployment_id:
            correlation_keys.append(f"deployment:{event.tenant_deployment_id}")
        if event.plugin_context and event.plugin_context.get("plugin_id"):
            correlation_keys.append(f"plugin:{event.plugin_context['plugin_id']}")
        
        # Find related events
        related_events = []
        cutoff_time = event.timestamp - timedelta(hours=1)  # 1-hour correlation window
        
        for key in correlation_keys:
            if key in self.correlation_cache:
                related_events.extend(self.correlation_cache[key])
        
        # Add correlation if found
        if related_events:
            event.related_events = list(set(related_events))
            event.correlation_id = f"corr-{uuid.uuid4()}"
            
            # Update correlation cache
            for key in correlation_keys:
                if key not in self.correlation_cache:
                    self.correlation_cache[key] = []
                self.correlation_cache[key].append(event.event_id)
        
        # Store correlation
        if event.correlation_id:
            correlation_file = f"{self.storage_path}/correlations/{event.correlation_id}.json"
            correlation_data = {
                "correlation_id": event.correlation_id,
                "events": event.related_events + [event.event_id],
                "tenant_id": event.tenant_id,
                "created_at": event.timestamp.isoformat(),
                "correlation_strength": len(related_events)
            }
            
            with open(correlation_file, 'w') as f:
                json.dump(correlation_data, f, indent=2, default=str)
    
    async def _correlation_processor(self):
        """Background task for processing correlations."""
        while True:
            try:
                # Clean up old correlation cache entries
                cutoff_time = datetime.utcnow() - timedelta(hours=6)
                
                # This is a simplified cleanup - in production, you'd want more sophisticated logic
                if len(self.correlation_cache) > 10000:
                    # Keep only recent correlations
                    self.correlation_cache = {}
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Correlation processor error: {e}")
                await asyncio.sleep(60)
    
    async def _aggregation_processor(self):
        """Background task for processing aggregations."""
        while True:
            try:
                await asyncio.sleep(self.aggregation_interval)
                
                # Process aggregation rules
                for rule in self.aggregation_rules:
                    await self._process_aggregation_rule(rule)
                
            except Exception as e:
                logger.error(f"Aggregation processor error: {e}")
                await asyncio.sleep(60)
    
    async def _process_aggregation_rule(self, rule: AuditAggregationRule):
        """Process a specific aggregation rule."""
        try:
            # Time window for aggregation
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=rule.aggregation_window_minutes)
            
            # Find matching events
            matching_events = await self._find_matching_events(rule, start_time, end_time)
            
            if not matching_events:
                return
            
            # Group by correlation fields
            grouped_events = self._group_events_by_correlation(matching_events, rule.correlation_fields)
            
            # Process each group
            for group_key, events in grouped_events.items():
                if rule.require_cross_platform:
                    # Check if group has events from both platforms
                    platforms = set(event.platform for event in events)
                    if len(platforms) < 2:
                        continue
                
                # Create summary event
                if rule.create_summary_event:
                    await self._create_aggregation_summary(rule, group_key, events)
                
                # Handle notifications
                if rule.notify_compliance_team:
                    await self._notify_compliance_team(rule, group_key, events)
                
                if rule.escalate_to_security:
                    await self._escalate_to_security(rule, group_key, events)
            
        except Exception as e:
            logger.error(f"Failed to process aggregation rule {rule.rule_id}: {e}")
    
    async def _find_matching_events(
        self,
        rule: AuditAggregationRule,
        start_time: datetime,
        end_time: datetime
    ) -> List[CrossPlatformAuditEvent]:
        """Find events matching aggregation rule criteria."""
        matching_events = []
        
        # Read recent event files
        for days_back in range(2):  # Check last 2 days
            check_date = (end_time - timedelta(days=days_back)).strftime("%Y-%m-%d")
            log_file = f"{self.storage_path}/events/cross-platform-audit-{check_date}.jsonl"
            
            if not os.path.exists(log_file):
                continue
            
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        event = CrossPlatformAuditEvent(**event_data)
                        
                        # Check time window
                        if event.timestamp < start_time or event.timestamp > end_time:
                            continue
                        
                        # Apply filters
                        if rule.tenant_id_pattern and event.tenant_id:
                            import re
                            if not re.match(rule.tenant_id_pattern, event.tenant_id):
                                continue
                        
                        if rule.service_pattern:
                            import re
                            if not re.match(rule.service_pattern, event.service):
                                continue
                        
                        if rule.field_path_pattern:
                            import re
                            if not re.match(rule.field_path_pattern, event.field_path):
                                continue
                        
                        if rule.change_type_filter:
                            if event.change_type not in rule.change_type_filter:
                                continue
                        
                        matching_events.append(event)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse event line: {e}")
        
        return matching_events
    
    def _group_events_by_correlation(
        self,
        events: List[CrossPlatformAuditEvent],
        correlation_fields: List[str]
    ) -> Dict[str, List[CrossPlatformAuditEvent]]:
        """Group events by correlation fields."""
        groups = {}
        
        for event in events:
            # Build correlation key
            key_parts = []
            for field in correlation_fields:
                value = getattr(event, field, None)
                if value:
                    key_parts.append(f"{field}:{value}")
            
            if not key_parts:
                continue
            
            group_key = "|".join(key_parts)
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(event)
        
        return groups
    
    async def _create_aggregation_summary(
        self,
        rule: AuditAggregationRule,
        group_key: str,
        events: List[CrossPlatformAuditEvent]
    ):
        """Create aggregation summary event."""
        summary_id = f"summary-{uuid.uuid4()}"
        
        summary_data = {
            "summary_id": summary_id,
            "rule_id": rule.rule_id,
            "rule_name": rule.name,
            "group_key": group_key,
            "event_count": len(events),
            "platforms": list(set(event.platform for event in events)),
            "tenants": list(set(event.tenant_id for event in events if event.tenant_id)),
            "users": list(set(event.user_id for event in events if event.user_id)),
            "time_span": {
                "start": min(event.timestamp for event in events).isoformat(),
                "end": max(event.timestamp for event in events).isoformat()
            },
            "change_types": list(set(event.change_type for event in events)),
            "compliance_impact": any(event.compliance_impact for event in events),
            "security_impact": any(event.security_impact for event in events),
            "created_at": datetime.utcnow().isoformat(),
            "event_ids": [event.event_id for event in events]
        }
        
        # Store summary
        summary_file = f"{self.storage_path}/summaries/{summary_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        logger.info(f"Created aggregation summary: {summary_id} for rule {rule.rule_id}")
    
    async def _notify_compliance_team(
        self,
        rule: AuditAggregationRule,
        group_key: str,
        events: List[CrossPlatformAuditEvent]
    ):
        """Notify compliance team of aggregated events."""
        # This would integrate with notification system
        logger.info(f"Compliance notification: {rule.name} - {group_key} ({len(events)} events)")
    
    async def _escalate_to_security(
        self,
        rule: AuditAggregationRule,
        group_key: str,
        events: List[CrossPlatformAuditEvent]
    ):
        """Escalate aggregated events to security team."""
        # This would integrate with security incident management
        logger.warning(f"Security escalation: {rule.name} - {group_key} ({len(events)} events)")
    
    async def generate_tenant_audit_summary(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> TenantAuditSummary:
        """
        Generate comprehensive audit summary for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            start_date: Summary period start
            end_date: Summary period end
            
        Returns:
            Tenant audit summary
        """
        # Find all events for tenant in period
        tenant_events = await self._find_tenant_events(tenant_id, start_date, end_date)
        
        # Initialize summary
        summary = TenantAuditSummary(
            tenant_id=tenant_id,
            summary_period_start=start_date,
            summary_period_end=end_date,
            total_events=len(tenant_events)
        )
        
        # Analyze events
        user_counts = {}
        service_counts = {}
        
        for event in tenant_events:
            # Count by platform
            if event.platform == "management-platform":
                summary.management_platform_events += 1
            elif event.platform == "isp-framework":
                summary.isp_framework_events += 1
            
            # Count by type
            if "config" in event.field_path.lower():
                summary.configuration_changes += 1
            if event.security_impact:
                summary.security_events += 1
            if event.plugin_context:
                summary.plugin_events += 1
            if "deploy" in event.service.lower():
                summary.deployment_events += 1
            
            # Risk indicators
            if event.change_type in [ChangeType.DELETE, ChangeType.ROTATE]:
                summary.high_risk_changes += 1
            if event.compliance_impact:
                summary.compliance_violations += 1
            
            # Count users and services
            if event.user_id:
                user_counts[event.user_id] = user_counts.get(event.user_id, 0) + 1
            service_counts[event.service] = service_counts.get(event.service, 0) + 1
        
        # Top users and services
        summary.top_users = [
            {"user_id": k, "event_count": v}
            for k, v in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        summary.top_services = [
            {"service": k, "event_count": v}
            for k, v in sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Generate recommendations
        summary.audit_recommendations = self._generate_audit_recommendations(summary, tenant_events)
        
        return summary
    
    async def _find_tenant_events(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[CrossPlatformAuditEvent]:
        """Find all events for a tenant in a date range."""
        events = []
        
        # Check each day in range
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            log_file = f"{self.storage_path}/events/cross-platform-audit-{current_date}.jsonl"
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            event = CrossPlatformAuditEvent(**event_data)
                            
                            if (event.tenant_id == tenant_id and
                                start_date <= event.timestamp <= end_date):
                                events.append(event)
                                
                        except Exception as e:
                            logger.warning(f"Failed to parse event line: {e}")
            
            current_date += timedelta(days=1)
        
        return events
    
    def _generate_audit_recommendations(
        self,
        summary: TenantAuditSummary,
        events: List[CrossPlatformAuditEvent]
    ) -> List[str]:
        """Generate audit recommendations based on summary."""
        recommendations = []
        
        if summary.compliance_violations > 0:
            recommendations.append(f"Review {summary.compliance_violations} compliance violations")
        
        if summary.high_risk_changes > summary.total_events * 0.1:  # > 10%
            recommendations.append("High percentage of risky configuration changes - review change procedures")
        
        if summary.security_events > summary.total_events * 0.05:  # > 5%
            recommendations.append("Elevated security event activity - consider security review")
        
        if summary.management_platform_events == 0 and summary.isp_framework_events > 0:
            recommendations.append("Missing management platform audit trail - verify audit configuration")
        
        # Check for unusual user activity
        if summary.top_users and summary.top_users[0]["event_count"] > summary.total_events * 0.5:
            recommendations.append(f"Single user ({summary.top_users[0]['user_id']}) responsible for >50% of changes")
        
        return recommendations


# Global cross-platform audit orchestrator
_audit_orchestrator: Optional[CrossPlatformAuditOrchestrator] = None


def get_audit_orchestrator() -> CrossPlatformAuditOrchestrator:
    """Get global cross-platform audit orchestrator."""
    global _audit_orchestrator
    if _audit_orchestrator is None:
        _audit_orchestrator = CrossPlatformAuditOrchestrator()
    return _audit_orchestrator


def init_audit_orchestrator(
    storage_path: str = "/var/log/dotmac/cross-platform-audit",
    aggregation_interval: int = 300,
    retention_days: int = 2555,
    enable_real_time_correlation: bool = True
) -> CrossPlatformAuditOrchestrator:
    """Initialize global cross-platform audit orchestrator."""
    global _audit_orchestrator
    _audit_orchestrator = CrossPlatformAuditOrchestrator(
        storage_path=storage_path,
        aggregation_interval=aggregation_interval,
        retention_days=retention_days,
        enable_real_time_correlation=enable_real_time_correlation
    )
    return _audit_orchestrator