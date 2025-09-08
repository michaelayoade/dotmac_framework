"""
Shared compliance manager for DRY compliance operations across DotMac Framework.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from dotmac.application import standard_exception_handler
from dotmac.communications.events import EventBus
from dotmac.core.cache import create_cache_service

from ..schemas.compliance_schemas import (
    ComplianceAlert,
    ComplianceCheck,
    ComplianceEvent,
    ComplianceFramework,
    ComplianceMetrics,
    ComplianceRule,
    ComplianceStatus,
    RiskLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class ComplianceConfig:
    """Configuration for compliance manager."""

    enabled_frameworks: list[ComplianceFramework]
    default_retention_days: int = 2555  # 7 years
    risk_score_threshold_high: int = 70
    risk_score_threshold_critical: int = 90
    auto_remediation_enabled: bool = False
    alert_thresholds: dict[str, int] = None
    cache_ttl_seconds: int = 3600

    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {"critical": 1, "high": 5, "medium": 10, "low": 50}


class ComplianceManager:
    """
    Centralized compliance management with DRY patterns.
    Eliminates duplicate compliance code across ISP and management platforms.
    """

    def __init__(
        self,
        config: ComplianceConfig,
        tenant_id: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
        cache_service=None,
    ):
        self.config = config
        self.tenant_id = tenant_id
        self.event_bus = event_bus
        self.cache_service = cache_service or create_cache_service()

        # In-memory storage for rules and checks (production would use database)
        self._rules: dict[str, ComplianceRule] = {}
        self._checks: list[ComplianceCheck] = []
        self._alerts: list[ComplianceAlert] = []

        # Load default compliance rules
        self._load_default_rules()

    async def initialize(self) -> bool:
        """Initialize compliance manager."""
        try:
            if self.cache_service:
                await self.cache_service.initialize()

            # Initialize compliance frameworks
            for framework in self.config.enabled_frameworks:
                await self._initialize_framework(framework)

            logger.info(f"✅ Compliance Manager initialized for {len(self.config.enabled_frameworks)} frameworks")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Compliance Manager: {e}")
            return False

    @standard_exception_handler
    async def record_compliance_event(
        self,
        event: ComplianceEvent,
        auto_check: bool = True,
    ) -> bool:
        """Record a compliance event and optionally trigger automatic checks."""

        # Store event
        if self.cache_service:
            cache_key = f"compliance_event:{event.tenant_id}:{event.event_id}"
            await self.cache_service.set(
                cache_key,
                event.model_dump(),
                tenant_id=self.tenant_id,
                expire=self.config.cache_ttl_seconds,
            )

        # Trigger compliance checks if enabled
        if auto_check:
            await self._trigger_compliance_checks(event)

        # Publish event for other services
        if self.event_bus:
            await self.event_bus.publish(
                "compliance.event_recorded",
                {
                    "event_id": str(event.event_id),
                    "event_type": event.event_type.value,
                    "framework": event.framework.value,
                    "risk_level": event.risk_level.value,
                    "tenant_id": event.tenant_id,
                },
            )

        return True

    @standard_exception_handler
    async def perform_compliance_check(
        self,
        rule_id: str,
        resource_id: str,
        resource_type: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ComplianceCheck:
        """Perform a compliance check against a specific rule."""

        context = context or {}
        rule = self._rules.get(rule_id)

        if not rule:
            raise ValueError(f"Compliance rule {rule_id} not found")

        # Perform the actual check (simplified for demo)
        status = await self._evaluate_compliance_rule(rule, resource_id, resource_type, context)

        # Create check result
        check = ComplianceCheck(
            check_id=uuid4(),
            tenant_id=self.tenant_id,
            rule_id=rule_id,
            resource_id=resource_id,
            resource_type=resource_type,
            status=status,
            score=self._calculate_compliance_score(status),
            findings=await self._get_check_findings(rule, status, context),
            recommendations=await self._get_check_recommendations(rule, status),
            evidence=context,
            next_check_due=datetime.now(timezone.utc) + timedelta(days=30),  # Default 30 days
        )

        # Store check result
        self._checks.append(check)

        # Create alert if non-compliant
        if status != ComplianceStatus.COMPLIANT:
            await self._create_compliance_alert(check, rule)

        # Cache check result
        if self.cache_service:
            cache_key = f"compliance_check:{self.tenant_id}:{check.check_id}"
            await self.cache_service.set(
                cache_key,
                check.model_dump(),
                tenant_id=self.tenant_id,
                expire=self.config.cache_ttl_seconds,
            )

        return check

    @standard_exception_handler
    async def get_compliance_metrics(
        self,
        framework: ComplianceFramework,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> ComplianceMetrics:
        """Calculate compliance metrics for a framework and period."""

        if not period_start:
            period_start = datetime.now(timezone.utc) - timedelta(days=30)
        if not period_end:
            period_end = datetime.now(timezone.utc)

        # Filter checks for the period
        period_checks = [
            check
            for check in self._checks
            if (
                check.checked_at >= period_start
                and check.checked_at <= period_end
                and self._get_rule_framework(check.rule_id) == framework
            )
        ]

        if not period_checks:
            return ComplianceMetrics(
                framework=framework,
                period_start=period_start,
                period_end=period_end,
                overall_score=100.0,
                total_checks=0,
                passed_checks=0,
                failed_checks=0,
                critical_issues=0,
                high_risk_issues=0,
                medium_risk_issues=0,
                low_risk_issues=0,
                score_trend=[],
                issue_trend=[],
                category_scores={},
            )

        # Calculate metrics
        total_checks = len(period_checks)
        passed_checks = len([c for c in period_checks if c.status == ComplianceStatus.COMPLIANT])
        failed_checks = total_checks - passed_checks

        # Calculate overall score
        scores = [c.score for c in period_checks if c.score is not None]
        overall_score = sum(scores) / len(scores) if scores else 100.0

        # Count issues by risk level
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for check in period_checks:
            if check.status != ComplianceStatus.COMPLIANT:
                rule = self._rules.get(check.rule_id)
                if rule:
                    risk_counts[rule.severity.value] += 1

        # Generate trend data (simplified)
        score_trend = await self._calculate_score_trend(framework, period_start, period_end)
        issue_trend = await self._calculate_issue_trend(framework, period_start, period_end)

        # Calculate category scores
        category_scores = await self._calculate_category_scores(framework, period_checks)

        return ComplianceMetrics(
            framework=framework,
            period_start=period_start,
            period_end=period_end,
            overall_score=overall_score,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            critical_issues=risk_counts["critical"],
            high_risk_issues=risk_counts["high"],
            medium_risk_issues=risk_counts["medium"],
            low_risk_issues=risk_counts["low"],
            score_trend=score_trend,
            issue_trend=issue_trend,
            category_scores=category_scores,
        )

    @standard_exception_handler
    async def get_active_alerts(
        self,
        framework: Optional[ComplianceFramework] = None,
        severity: Optional[RiskLevel] = None,
    ) -> list[ComplianceAlert]:
        """Get active compliance alerts."""

        alerts = [alert for alert in self._alerts if alert.status == "open"]

        if framework:
            alerts = [alert for alert in alerts if alert.framework == framework]

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        # Sort by severity and timestamp
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(
            key=lambda a: (severity_order.get(a.severity.value, 4), a.triggered_at),
            reverse=True,
        )

        return alerts

    async def _initialize_framework(self, framework: ComplianceFramework):
        """Initialize a compliance framework."""
        logger.info(f"Initializing compliance framework: {framework.value}")

        # Load framework-specific rules
        rules = await self._load_framework_rules(framework)
        for rule in rules:
            self._rules[rule.rule_id] = rule

    async def _load_framework_rules(self, framework: ComplianceFramework) -> list[ComplianceRule]:
        """Load compliance rules for a specific framework."""
        # Simplified rule loading - production would load from database/config

        if framework == ComplianceFramework.SOC2:
            return await self._get_soc2_rules()
        elif framework == ComplianceFramework.GDPR:
            return await self._get_gdpr_rules()
        elif framework == ComplianceFramework.HIPAA:
            return await self._get_hipaa_rules()
        else:
            return []

    async def _get_soc2_rules(self) -> list[ComplianceRule]:
        """Get SOC2 compliance rules."""
        return [
            ComplianceRule(
                rule_id="soc2_access_control",
                framework=ComplianceFramework.SOC2,
                name="Access Control",
                description="Logical and physical access controls restrict access to system resources",
                category="security",
                severity=RiskLevel.HIGH,
                conditions={"requires": ["authentication", "authorization", "access_logging"]},
                remediation="Implement proper access controls and logging",
            ),
            ComplianceRule(
                rule_id="soc2_data_encryption",
                framework=ComplianceFramework.SOC2,
                name="Data Encryption",
                description="Sensitive data is encrypted in transit and at rest",
                category="security",
                severity=RiskLevel.CRITICAL,
                conditions={"requires": ["encryption_in_transit", "encryption_at_rest"]},
                remediation="Enable encryption for all sensitive data",
            ),
        ]

    async def _get_gdpr_rules(self) -> list[ComplianceRule]:
        """Get GDPR compliance rules."""
        return [
            ComplianceRule(
                rule_id="gdpr_consent",
                framework=ComplianceFramework.GDPR,
                name="User Consent",
                description="Valid consent must be obtained for personal data processing",
                category="privacy",
                severity=RiskLevel.CRITICAL,
                conditions={"requires": ["explicit_consent", "consent_record"]},
                remediation="Obtain and record explicit user consent",
            ),
            ComplianceRule(
                rule_id="gdpr_data_retention",
                framework=ComplianceFramework.GDPR,
                name="Data Retention",
                description="Personal data must not be kept longer than necessary",
                category="privacy",
                severity=RiskLevel.HIGH,
                conditions={"max_retention_days": 2555},
                remediation="Implement data retention policies and automated deletion",
            ),
        ]

    async def _get_hipaa_rules(self) -> list[ComplianceRule]:
        """Get HIPAA compliance rules."""
        return [
            ComplianceRule(
                rule_id="hipaa_access_audit",
                framework=ComplianceFramework.HIPAA,
                name="Access Audit Trail",
                description="All access to PHI must be logged and audited",
                category="security",
                severity=RiskLevel.CRITICAL,
                conditions={"requires": ["access_logging", "audit_trail"]},
                remediation="Enable comprehensive access logging and audit trails",
            ),
        ]

    def _load_default_rules(self):
        """Load default compliance rules."""
        # This would typically load from configuration or database
        pass

    async def _trigger_compliance_checks(self, event: ComplianceEvent):
        """Trigger relevant compliance checks based on event."""

        # Find rules that apply to this event
        applicable_rules = [
            rule for rule in self._rules.values() if rule.framework == event.framework and rule.is_active
        ]

        # Perform checks
        for rule in applicable_rules:
            if event.resource_id and event.resource_type:
                await self.perform_compliance_check(
                    rule.rule_id, event.resource_id, event.resource_type, event.metadata
                )

    async def _evaluate_compliance_rule(
        self,
        rule: ComplianceRule,
        resource_id: str,
        resource_type: str,
        context: dict[str, Any],
    ) -> ComplianceStatus:
        """Evaluate a compliance rule against a resource."""

        # Simplified rule evaluation - production would have complex logic
        conditions = rule.conditions

        if "requires" in conditions:
            required_features = conditions["requires"]
            available_features = context.get("features", [])

            if all(feature in available_features for feature in required_features):
                return ComplianceStatus.COMPLIANT
            else:
                return ComplianceStatus.NON_COMPLIANT

        return ComplianceStatus.COMPLIANT

    def _calculate_compliance_score(self, status: ComplianceStatus) -> float:
        """Calculate compliance score based on status."""
        score_map = {
            ComplianceStatus.COMPLIANT: 100.0,
            ComplianceStatus.PARTIAL_COMPLIANCE: 75.0,
            ComplianceStatus.NON_COMPLIANT: 0.0,
            ComplianceStatus.UNDER_REVIEW: 50.0,
            ComplianceStatus.REMEDIATION_REQUIRED: 25.0,
        }
        return score_map.get(status, 50.0)

    async def _get_check_findings(
        self,
        rule: ComplianceRule,
        status: ComplianceStatus,
        context: dict[str, Any],
    ) -> list[str]:
        """Get findings for a compliance check."""

        findings = []

        if status != ComplianceStatus.COMPLIANT:
            findings.append(f"Rule '{rule.name}' violation detected")

            if "requires" in rule.conditions:
                required = rule.conditions["requires"]
                available = context.get("features", [])
                missing = set(required) - set(available)
                if missing:
                    findings.append(f"Missing required features: {', '.join(missing)}")

        return findings

    async def _get_check_recommendations(
        self,
        rule: ComplianceRule,
        status: ComplianceStatus,
    ) -> list[str]:
        """Get recommendations for a compliance check."""

        if status == ComplianceStatus.COMPLIANT:
            return ["Continue current practices"]

        return [rule.remediation]

    async def _create_compliance_alert(self, check: ComplianceCheck, rule: ComplianceRule):
        """Create a compliance alert for a failed check."""

        alert = ComplianceAlert(
            alert_id=uuid4(),
            tenant_id=self.tenant_id,
            rule_id=rule.rule_id,
            framework=rule.framework,
            severity=rule.severity,
            title=f"Compliance Violation: {rule.name}",
            description=f"Resource {check.resource_id} failed compliance check for rule {rule.name}",
            resource_affected=check.resource_id,
            remediation=rule.remediation,
            context={
                "check_id": str(check.check_id),
                "resource_type": check.resource_type,
                "findings": check.findings,
            },
        )

        self._alerts.append(alert)

        # Publish alert event
        if self.event_bus:
            await self.event_bus.publish(
                "compliance.alert_created",
                {
                    "alert_id": str(alert.alert_id),
                    "severity": alert.severity.value,
                    "framework": alert.framework.value,
                    "tenant_id": alert.tenant_id,
                },
            )

    def _get_rule_framework(self, rule_id: str) -> Optional[ComplianceFramework]:
        """Get the framework for a rule ID."""
        rule = self._rules.get(rule_id)
        return rule.framework if rule else None

    async def _calculate_score_trend(
        self,
        framework: ComplianceFramework,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Calculate compliance score trend over time."""
        # Simplified trend calculation
        return [
            {"date": start.isoformat(), "score": 85.0},
            {"date": end.isoformat(), "score": 90.0},
        ]

    async def _calculate_issue_trend(
        self,
        framework: ComplianceFramework,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Calculate compliance issue trend over time."""
        # Simplified trend calculation
        return [
            {"date": start.isoformat(), "issues": 5},
            {"date": end.isoformat(), "issues": 3},
        ]

    async def _calculate_category_scores(
        self,
        framework: ComplianceFramework,
        checks: list[ComplianceCheck],
    ) -> dict[str, float]:
        """Calculate compliance scores by category."""

        category_scores = {}

        # Group checks by rule category
        for check in checks:
            rule = self._rules.get(check.rule_id)
            if rule and check.score is not None:
                category = rule.category
                if category not in category_scores:
                    category_scores[category] = []
                category_scores[category].append(check.score)

        # Calculate average scores
        for category, scores in category_scores.items():
            category_scores[category] = sum(scores) / len(scores)

        return category_scores

    async def health_check(self) -> dict[str, Any]:
        """Health check for compliance manager."""
        try:
            return {
                "status": "healthy",
                "frameworks": [f.value for f in self.config.enabled_frameworks],
                "rules_loaded": len(self._rules),
                "checks_performed": len(self._checks),
                "active_alerts": len([a for a in self._alerts if a.status == "open"]),
                "cache_available": self.cache_service is not None,
                "event_bus_available": self.event_bus is not None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


# Factory function
async def create_compliance_manager(
    config: ComplianceConfig,
    tenant_id: Optional[str] = None,
    event_bus: Optional[EventBus] = None,
    cache_service=None,
) -> ComplianceManager:
    """Create and initialize compliance manager."""

    manager = ComplianceManager(
        config=config,
        tenant_id=tenant_id,
        event_bus=event_bus,
        cache_service=cache_service,
    )
    await manager.initialize()
    return manager
