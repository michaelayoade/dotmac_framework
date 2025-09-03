"""
Shared compliance service implementing DRY patterns for DotMac Framework.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.cache import create_cache_service
from dotmac_shared.events import EventBus
from dotmac_shared.services_framework.core.base import ServiceHealth, ServiceStatus, StatefulService
from dotmac_shared.application.config import DeploymentContext

from ..core.compliance_manager import ComplianceManager, ComplianceConfig
from ..core.regulatory_reporter import RegulatoryReporter, ReportingConfig
from ..schemas.compliance_schemas import (
    ComplianceFramework,
    ComplianceEvent,
    ComplianceReportRequest,
    RegulatoryReport,
    ComplianceMetrics,
    ComplianceAlert,
)

logger = logging.getLogger(__name__)


@dataclass
class ComplianceServiceConfig:
    """Configuration for compliance service."""
    
    # Framework configuration
    enabled_frameworks: List[ComplianceFramework]
    deployment_context: Optional[DeploymentContext] = None
    
    # Component configurations
    compliance_config: Optional[ComplianceConfig] = None
    reporting_config: Optional[ReportingConfig] = None
    
    # Service settings
    auto_compliance_checks: bool = True
    real_time_monitoring: bool = True
    alert_notifications: bool = True
    
    # Performance settings
    max_concurrent_operations: int = 10
    cache_ttl_seconds: int = 3600
    
    def __post_init__(self):
        """Initialize sub-configurations if not provided."""
        if self.compliance_config is None:
            self.compliance_config = ComplianceConfig(
                enabled_frameworks=self.enabled_frameworks
            )
        
        if self.reporting_config is None:
            self.reporting_config = ReportingConfig(
                enabled_frameworks=self.enabled_frameworks
            )


class ComplianceService(StatefulService):
    """
    Comprehensive compliance service with DRY patterns.
    Eliminates duplicate compliance functionality across ISP and management platforms.
    """
    
    def __init__(self, config: ComplianceServiceConfig):
        """Initialize compliance service."""
        super().__init__(
            name="compliance",
            config=config.__dict__,
            required_config=["enabled_frameworks"]
        )
        
        self.compliance_config = config
        self.priority = 95  # Very high priority for compliance
        
        # Component managers
        self.compliance_manager: Optional[ComplianceManager] = None
        self.regulatory_reporter: Optional[RegulatoryReporter] = None
        
        # Service dependencies
        self.event_bus: Optional[EventBus] = None
        self.cache_service = None
        
        # Service state
        self._active_operations = 0
        self._total_events_processed = 0
        self._total_reports_generated = 0
        self._total_alerts_created = 0
    
    async def _initialize_stateful_service(self) -> bool:
        """Initialize compliance service components."""
        try:
            # Initialize cache and event bus
            self.cache_service = create_cache_service()
            if self.cache_service:
                await self.cache_service.initialize()
            
            # Get tenant context
            tenant_id = None
            if (self.compliance_config.deployment_context and 
                hasattr(self.compliance_config.deployment_context, 'tenant_id')):
                tenant_id = self.compliance_config.deployment_context.tenant_id
            
            # Initialize compliance manager
            self.compliance_manager = ComplianceManager(
                config=self.compliance_config.compliance_config,
                tenant_id=tenant_id,
                event_bus=self.event_bus,
                cache_service=self.cache_service,
            )
            await self.compliance_manager.initialize()
            
            # Initialize regulatory reporter
            self.regulatory_reporter = RegulatoryReporter(
                config=self.compliance_config.reporting_config,
                compliance_manager=self.compliance_manager,
                tenant_id=tenant_id,
                event_bus=self.event_bus,
                cache_service=self.cache_service,
            )
            await self.regulatory_reporter.initialize()
            
            # Initialize state tracking
            self.set_state("events_processed", 0)
            self.set_state("reports_generated", 0)
            self.set_state("alerts_created", 0)
            self.set_state("last_health_check", datetime.now(timezone.utc).isoformat())
            
            await self._set_status(
                ServiceStatus.READY,
                f"Compliance service ready with {len(self.compliance_config.enabled_frameworks)} frameworks",
                {
                    "frameworks": [f.value for f in self.compliance_config.enabled_frameworks],
                    "auto_checks": self.compliance_config.auto_compliance_checks,
                    "real_time_monitoring": self.compliance_config.real_time_monitoring,
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize compliance service: {e}")
            await self._set_status(ServiceStatus.ERROR, f"Initialization failed: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown compliance service."""
        await self._set_status(ServiceStatus.SHUTTING_DOWN, "Shutting down compliance service")
        
        # Clear state
        self.clear_state()
        
        await self._set_status(ServiceStatus.SHUTDOWN, "Compliance service shutdown complete")
        return True
    
    async def _health_check_stateful_service(self) -> ServiceHealth:
        """Perform health check on compliance service."""
        try:
            details = {
                "frameworks": [f.value for f in self.compliance_config.enabled_frameworks],
                "active_operations": self._active_operations,
                "events_processed": self.get_state("events_processed", 0),
                "reports_generated": self.get_state("reports_generated", 0),
                "alerts_created": self.get_state("alerts_created", 0),
                "compliance_manager": "healthy" if self.compliance_manager else "unavailable",
                "regulatory_reporter": "healthy" if self.regulatory_reporter else "unavailable",
                "cache_service": "available" if self.cache_service else "unavailable",
            }
            
            # Check component health
            if self.compliance_manager:
                compliance_health = await self.compliance_manager.health_check()
                details["compliance_manager_details"] = compliance_health
                
                if compliance_health.get("status") != "healthy":
                    return ServiceHealth(
                        status=ServiceStatus.ERROR,
                        message="Compliance manager unhealthy",
                        details=details
                    )
            
            if self.regulatory_reporter:
                reporter_health = await self.regulatory_reporter.health_check()
                details["reporter_details"] = reporter_health
                
                if reporter_health.get("status") != "healthy":
                    return ServiceHealth(
                        status=ServiceStatus.ERROR,
                        message="Regulatory reporter unhealthy",
                        details=details
                    )
            
            # Check operational limits
            if self._active_operations > self.compliance_config.max_concurrent_operations:
                return ServiceHealth(
                    status=ServiceStatus.READY,
                    message=f"High load: {self._active_operations} active operations",
                    details=details
                )
            
            # Update last health check
            self.set_state("last_health_check", datetime.now(timezone.utc).isoformat())
            
            return ServiceHealth(
                status=ServiceStatus.READY,
                message="Compliance service healthy",
                details=details
            )
            
        except Exception as e:
            return ServiceHealth(
                status=ServiceStatus.ERROR,
                message=f"Health check failed: {e}",
                details={"error": str(e)}
            )
    
    @standard_exception_handler
    async def record_compliance_event(self, event: ComplianceEvent) -> bool:
        """Record a compliance event."""
        if not self.is_ready():
            raise RuntimeError("Compliance service not ready")
        
        self._active_operations += 1
        try:
            result = await self.compliance_manager.record_compliance_event(event)
            
            # Update statistics
            events_processed = self.get_state("events_processed", 0)
            self.set_state("events_processed", events_processed + 1)
            self._total_events_processed += 1
            
            return result
            
        finally:
            self._active_operations -= 1
    
    @standard_exception_handler
    async def generate_compliance_report(
        self,
        request: ComplianceReportRequest,
        user_id: Optional[UUID] = None,
    ) -> RegulatoryReport:
        """Generate a compliance report."""
        if not self.is_ready():
            raise RuntimeError("Compliance service not ready")
        
        self._active_operations += 1
        try:
            report = await self.regulatory_reporter.generate_report(request, user_id)
            
            # Update statistics
            reports_generated = self.get_state("reports_generated", 0)
            self.set_state("reports_generated", reports_generated + 1)
            self._total_reports_generated += 1
            
            return report
            
        finally:
            self._active_operations -= 1
    
    @standard_exception_handler
    async def get_compliance_metrics(
        self,
        framework: ComplianceFramework,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> ComplianceMetrics:
        """Get compliance metrics for a framework."""
        if not self.is_ready():
            raise RuntimeError("Compliance service not ready")
        
        return await self.compliance_manager.get_compliance_metrics(
            framework, period_start, period_end
        )
    
    @standard_exception_handler
    async def get_compliance_dashboard(
        self,
        frameworks: Optional[List[ComplianceFramework]] = None,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """Get compliance dashboard data."""
        if not self.is_ready():
            raise RuntimeError("Compliance service not ready")
        
        return await self.regulatory_reporter.get_compliance_dashboard_data(
            frameworks, period_days
        )
    
    @standard_exception_handler
    async def get_active_alerts(
        self,
        framework: Optional[ComplianceFramework] = None,
    ) -> List[ComplianceAlert]:
        """Get active compliance alerts."""
        if not self.is_ready():
            raise RuntimeError("Compliance service not ready")
        
        alerts = await self.compliance_manager.get_active_alerts(framework)
        
        # Update alert statistics
        active_alert_count = len([a for a in alerts if a.status == "open"])
        self.set_state("active_alerts", active_alert_count)
        
        return alerts
    
    @standard_exception_handler
    async def schedule_report(
        self,
        framework: ComplianceFramework,
        report_type: str,
        frequency: str,
        recipients: List[str],
        user_id: Optional[UUID] = None,
    ) -> str:
        """Schedule automatic report generation."""
        if not self.is_ready():
            raise RuntimeError("Compliance service not ready")
        
        from ..schemas.compliance_schemas import ReportFrequency
        
        try:
            freq = ReportFrequency(frequency)
        except ValueError:
            raise ValueError(f"Invalid frequency: {frequency}")
        
        return await self.regulatory_reporter.schedule_report(
            framework, report_type, freq, recipients, user_id
        )
    
    @standard_exception_handler
    async def perform_compliance_check(
        self,
        framework: ComplianceFramework,
        resource_id: str,
        resource_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform compliance checks for a resource."""
        if not self.is_ready():
            raise RuntimeError("Compliance service not ready")
        
        # Get all rules for the framework
        # In production, this would query the compliance manager's rules
        # For now, simulate with basic checks
        
        results = []
        check_result = await self.compliance_manager.perform_compliance_check(
            f"{framework.value}_basic_check",  # Simplified rule ID
            resource_id,
            resource_type,
            context or {}
        )
        
        results.append({
            "check_id": str(check_result.check_id),
            "rule_id": check_result.rule_id,
            "status": check_result.status.value,
            "score": check_result.score,
            "findings": check_result.findings,
            "recommendations": check_result.recommendations,
        })
        
        return results
    
    async def track_event(
        self,
        event_type: str,
        entity_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track analytics event through compliance system."""
        if not self.is_ready():
            return False
        
        try:
            # Create compliance event
            compliance_event = ComplianceEvent(
                event_id=uuid4(),
                tenant_id=getattr(self.compliance_config.deployment_context, 'tenant_id', None),
                event_type=event_type,
                framework=ComplianceFramework.SOC2,  # Default framework
                resource_id=entity_id,
                metadata=metadata or {}
            )
            
            return await self.record_compliance_event(compliance_event)
            
        except Exception as e:
            logger.error(f"Failed to track compliance event: {e}")
            return False
    
    async def get_analytics_stats(self) -> Dict[str, Any]:
        """Get compliance analytics statistics."""
        return {
            "service_name": "compliance",
            "frameworks": [f.value for f in self.compliance_config.enabled_frameworks],
            "events_processed": self.get_state("events_processed", 0),
            "reports_generated": self.get_state("reports_generated", 0),
            "alerts_created": self.get_state("alerts_created", 0),
            "active_operations": self._active_operations,
            "last_health_check": self.get_state("last_health_check"),
            "status": self.status.value if self.status else "unknown",
        }


async def create_compliance_service(config: ComplianceServiceConfig) -> ComplianceService:
    """Create and initialize compliance service."""
    service = ComplianceService(config)
    
    # Service will be initialized by the registry
    return service