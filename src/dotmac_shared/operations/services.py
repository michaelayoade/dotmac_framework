"""
Operations Services Layer

Service layer for operations automation following DRY patterns.
Integrates with existing repository patterns and exception handling.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.core.exceptions import BusinessRuleError, EntityNotFoundError
from dotmac_management.user_management.schemas.lifecycle_schemas import UserRegistration
from dotmac_management.user_management.schemas.user_schemas import UserType

from .automation import InfrastructureAutomation, OperationsOrchestrator
from .health_monitoring import NetworkEndpoint, NetworkHealthMonitor, ServiceHealthChecker
from .lifecycle_management import CustomerLifecycleManager, ServiceProvisioningAutomation
from .schemas import (
    CustomerLifecycleResponse,
    EndpointTrendsResponse,
    MaintenanceResult,
    NetworkEndpointResponse,
    NetworkHealthSummary,
    OperationsStatus,
    ServiceHealthCheckResponse,
    ServiceProvisioningResponse,
)

logger = logging.getLogger(__name__)


class NetworkMonitoringService:
    """Service layer for network health monitoring operations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.health_monitor = NetworkHealthMonitor(db_session)
        self.service_checker = ServiceHealthChecker()

    @standard_exception_handler
    async def register_endpoint(
        self, endpoint_data: Dict[str, Any], user_id: UUID
    ) -> NetworkEndpointResponse:
        """Register network endpoint for monitoring."""
        
        endpoint = NetworkEndpoint(
            id=uuid4(),
            name=endpoint_data["name"],
            host=endpoint_data["host"],
            port=endpoint_data["port"],
            service_type=endpoint_data["service_type"],
            tenant_id=endpoint_data.get("tenant_id"),
            check_interval=endpoint_data.get("check_interval", 30),
            timeout=endpoint_data.get("timeout", 5),
            retry_count=endpoint_data.get("retry_count", 3),
            expected_response_time=endpoint_data.get("expected_response_time", 1.0),
        )
        
        await self.health_monitor.register_endpoint(endpoint)
        
        return NetworkEndpointResponse(
            id=endpoint.id,
            name=endpoint.name,
            host=endpoint.host,
            port=endpoint.port,
            service_type=endpoint.service_type,
            tenant_id=endpoint.tenant_id,
            check_interval=endpoint.check_interval,
            timeout=endpoint.timeout,
            retry_count=endpoint.retry_count,
            expected_response_time=endpoint.expected_response_time,
            created_at=None,  # Would need database persistence
            updated_at=None,
        )

    @standard_exception_handler
    async def get_network_health_summary(self, user_id: UUID) -> NetworkHealthSummary:
        """Get comprehensive network health summary."""
        summary = await self.health_monitor.get_network_health_summary()
        
        return NetworkHealthSummary(
            overall_status=summary["overall_status"],
            total_endpoints=summary["total_endpoints"],
            healthy_count=summary["healthy_count"],
            degraded_count=summary["degraded_count"],
            critical_count=summary["critical_count"],
            offline_count=summary["offline_count"],
            average_response_time=summary["average_response_time"],
            timestamp=summary["timestamp"],
            details=summary["details"],
        )

    @standard_exception_handler
    async def get_endpoint_trends(
        self, endpoint_id: UUID, hours: int, user_id: UUID
    ) -> EndpointTrendsResponse:
        """Get endpoint health trends."""
        trends = await self.health_monitor.get_endpoint_trends(endpoint_id, hours)
        
        return EndpointTrendsResponse(
            endpoint_id=UUID(trends["endpoint_id"]),
            endpoint_name=trends.get("endpoint_name"),
            period_hours=trends["period_hours"],
            total_checks=trends["total_checks"],
            availability_percentage=trends["availability_percentage"],
            average_response_time=trends["average_response_time"],
            status_distribution=trends["status_distribution"],
            recent_issues=trends["recent_issues"],
        )

    @standard_exception_handler
    async def check_service_health(
        self, service_type: str, connection_params: Dict[str, Any], user_id: UUID
    ) -> ServiceHealthCheckResponse:
        """Check specific service health."""
        
        if service_type == "database":
            if "connection_string" not in connection_params:
                raise BusinessRuleError("Database connection string required")
            
            result = await self.service_checker.check_database_health(
                connection_params["connection_string"],
                connection_params.get("timeout", 5)
            )
            
        elif service_type == "redis":
            if "redis_url" not in connection_params:
                raise BusinessRuleError("Redis URL required")
            
            result = await self.service_checker.check_redis_health(
                connection_params["redis_url"],
                connection_params.get("timeout", 5)
            )
            
        elif service_type == "container":
            if "container_id" not in connection_params:
                raise BusinessRuleError("Container ID required")
            
            result = await self.service_checker.check_container_health(
                connection_params["container_id"]
            )
            
        else:
            raise BusinessRuleError(f"Unsupported service type: {service_type}")
        
        return ServiceHealthCheckResponse(
            status=result["status"],
            response_time=result.get("response_time", 0.0),
            message=result["message"],
            details=result.get("details", {}),
        )

    @standard_exception_handler
    async def unregister_endpoint(self, endpoint_id: UUID, user_id: UUID) -> bool:
        """Unregister endpoint from monitoring."""
        await self.health_monitor.unregister_endpoint(endpoint_id)
        return True


class CustomerLifecycleService:
    """Service layer for customer lifecycle management."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.lifecycle_manager = CustomerLifecycleManager(db_session)
        self.provisioning = ServiceProvisioningAutomation(db_session)

    @standard_exception_handler
    async def register_customer(
        self, registration_data: Dict[str, Any], user_id: UUID
    ) -> CustomerLifecycleResponse:
        """Register new customer."""
        
        # Convert to UserRegistration schema
        user_registration = UserRegistration(
            username=registration_data["username"],
            email=registration_data["email"],
            first_name=registration_data["first_name"],
            last_name=registration_data["last_name"],
            user_type=UserType(registration_data["user_type"]),
            tenant_id=registration_data.get("tenant_id"),
            requires_approval=registration_data.get("requires_approval", False),
            referral_code=registration_data.get("referral_code"),
            terms_accepted=registration_data.get("terms_accepted", True),
            privacy_policy_accepted=registration_data.get("privacy_policy_accepted", True),
            marketing_consent=registration_data.get("marketing_consent", False),
        )
        
        result = await self.lifecycle_manager.process_new_registration(user_registration)
        
        return CustomerLifecycleResponse(
            id=result["user_id"],
            user_id=result["user_id"],
            status=result["status"],
            lifecycle_stage=result["lifecycle_stage"],
            next_actions=result["next_actions"],
            timestamp=result["created_at"],
            created_at=result["created_at"],
            updated_at=result["created_at"],
        )

    @standard_exception_handler
    async def verify_customer(
        self, customer_id: UUID, verification_data: Dict[str, Any], user_id: UUID
    ) -> CustomerLifecycleResponse:
        """Verify customer account."""
        
        result = await self.lifecycle_manager.verify_customer_account(
            customer_id, verification_data
        )
        
        return CustomerLifecycleResponse(
            id=customer_id,
            user_id=customer_id,
            status=result["status"],
            lifecycle_stage=result["lifecycle_stage"],
            next_actions=result["next_actions"],
            timestamp=result["verified_at"],
            created_at=None,
            updated_at=result["verified_at"],
        )

    @standard_exception_handler
    async def suspend_customer(
        self, customer_id: UUID, reason: str, suspension_data: Dict[str, Any], user_id: UUID
    ) -> CustomerLifecycleResponse:
        """Suspend customer account."""
        
        result = await self.lifecycle_manager.suspend_customer(
            customer_id, reason, suspension_data
        )
        
        return CustomerLifecycleResponse(
            id=customer_id,
            user_id=customer_id,
            status=result["status"],
            lifecycle_stage=result["lifecycle_stage"],
            next_actions=[],
            timestamp=result["suspended_at"],
            created_at=None,
            updated_at=result["suspended_at"],
        )

    @standard_exception_handler
    async def provision_service(
        self, customer_id: UUID, service_name: str, custom_config: Dict[str, Any], user_id: UUID
    ) -> ServiceProvisioningResponse:
        """Provision service for customer."""
        
        result = await self.provisioning.provision_service(
            customer_id, service_name, custom_config
        )
        
        return ServiceProvisioningResponse(
            id=UUID(result["request_id"]),
            request_id=UUID(result["request_id"]),
            customer_id=customer_id,
            service_name=service_name,
            status=result["status"],
            message=result["message"],
            created_at=None,
            updated_at=None,
        )

    @standard_exception_handler
    async def get_provisioning_status(
        self, request_id: UUID, user_id: UUID
    ) -> ServiceProvisioningResponse:
        """Get service provisioning status."""
        
        result = await self.provisioning.get_provisioning_status(request_id)
        
        return ServiceProvisioningResponse(
            id=request_id,
            request_id=request_id,
            customer_id=UUID(result["customer_id"]),
            service_name=result["service_name"],
            status=result["status"],
            message=result.get("error", ""),
            created_at=result["created_at"],
            updated_at=result.get("provisioned_at"),
        )

    @standard_exception_handler
    async def get_customer_lifecycle_summary(
        self, customer_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """Get customer lifecycle summary."""
        return await self.lifecycle_manager.get_customer_lifecycle_summary(customer_id)


class InfrastructureMaintenanceService:
    """Service layer for infrastructure maintenance operations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.orchestrator = OperationsOrchestrator(db_session)

    @standard_exception_handler
    async def execute_maintenance(
        self, maintenance_type: str, parameters: Dict[str, Any], user_id: UUID
    ) -> MaintenanceResult:
        """Execute maintenance operation manually."""
        
        automation = self.orchestrator.infrastructure_automation
        
        if maintenance_type == "database_cleanup":
            result = await automation.database_cleanup(parameters)
        elif maintenance_type == "log_rotation":
            result = await automation.log_rotation_cleanup(parameters)
        elif maintenance_type == "cache_cleanup":
            result = await automation.cache_cleanup(parameters)
        elif maintenance_type == "performance_optimization":
            result = await automation.performance_optimization(parameters)
        else:
            raise BusinessRuleError(f"Unsupported maintenance type: {maintenance_type}")
        
        return MaintenanceResult(
            task_id=result.task_id,
            task_name=result.task_name,
            status=result.status,
            start_time=result.start_time,
            end_time=result.end_time,
            duration_seconds=result.duration_seconds,
            items_processed=result.items_processed,
            items_cleaned=result.items_cleaned,
            space_freed_mb=result.space_freed_mb,
            error_message=result.error_message,
            details=result.details,
        )

    @standard_exception_handler
    async def get_operations_status(self, user_id: UUID) -> OperationsStatus:
        """Get comprehensive operations status."""
        status = await self.orchestrator.get_operations_status()
        
        return OperationsStatus(
            scheduler_running=status["scheduler_running"],
            active_tasks=status["active_tasks"],
            recent_results=status["recent_results"],
            maintenance_tasks=status["maintenance_tasks"],
            timestamp=status["timestamp"],
        )

    @standard_exception_handler
    async def start_operations(self, user_id: UUID) -> Dict[str, str]:
        """Start operations automation."""
        # This would typically be done at application startup
        await self.orchestrator.start_operations()
        return {"message": "Operations automation started"}

    @standard_exception_handler
    async def stop_operations(self, user_id: UUID) -> Dict[str, str]:
        """Stop operations automation."""
        await self.orchestrator.stop_operations()
        return {"message": "Operations automation stopped"}


# Combined Operations Service
class OperationsService:
    """Combined service for all operations automation."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[UUID] = None):
        self.db = db_session
        self.tenant_id = tenant_id
        
        # Initialize sub-services
        self.network_monitoring = NetworkMonitoringService(db_session)
        self.customer_lifecycle = CustomerLifecycleService(db_session)
        self.infrastructure_maintenance = InfrastructureMaintenanceService(db_session)

    # Network Monitoring Operations
    async def create_endpoint(self, data: Dict[str, Any], user_id: UUID):
        """Create network monitoring endpoint."""
        return await self.network_monitoring.register_endpoint(data, user_id)

    async def get_network_health(self, user_id: UUID):
        """Get network health summary."""
        return await self.network_monitoring.get_network_health_summary(user_id)

    async def get_endpoint_trends(self, endpoint_id: UUID, hours: int, user_id: UUID):
        """Get endpoint trends."""
        return await self.network_monitoring.get_endpoint_trends(endpoint_id, hours, user_id)

    # Customer Lifecycle Operations
    async def register_customer(self, data: Dict[str, Any], user_id: UUID):
        """Register new customer."""
        return await self.customer_lifecycle.register_customer(data, user_id)

    async def provision_service(self, customer_id: UUID, service_name: str, config: Dict[str, Any], user_id: UUID):
        """Provision service for customer."""
        return await self.customer_lifecycle.provision_service(customer_id, service_name, config, user_id)

    # Infrastructure Maintenance Operations
    async def execute_maintenance(self, maintenance_type: str, parameters: Dict[str, Any], user_id: UUID):
        """Execute maintenance operation."""
        return await self.infrastructure_maintenance.execute_maintenance(maintenance_type, parameters, user_id)

    async def get_operations_status(self, user_id: UUID):
        """Get operations status."""
        return await self.infrastructure_maintenance.get_operations_status(user_id)

    # Required methods for RouterFactory
    async def get_by_id(self, entity_id: UUID, user_id: UUID):
        """Get entity by ID (placeholder for RouterFactory compatibility)."""
        raise EntityNotFoundError(f"Entity {entity_id} not found")

    async def list(self, skip: int = 0, limit: int = 100, filters: Dict = None, order_by: str = "created_at", user_id: UUID = None):
        """List entities (placeholder for RouterFactory compatibility)."""
        return []

    async def count(self, filters: Dict = None, user_id: UUID = None):
        """Count entities (placeholder for RouterFactory compatibility)."""
        return 0

    async def update(self, entity_id: UUID, data: Dict[str, Any], user_id: UUID):
        """Update entity (placeholder for RouterFactory compatibility)."""
        raise EntityNotFoundError(f"Entity {entity_id} not found")

    async def delete(self, entity_id: UUID, user_id: UUID, soft_delete: bool = True):
        """Delete entity (placeholder for RouterFactory compatibility)."""
        raise EntityNotFoundError(f"Entity {entity_id} not found")