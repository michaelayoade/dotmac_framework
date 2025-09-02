"""
Operations API Routers

Production-ready API routers using RouterFactory patterns.
ALL routers MUST use RouterFactory - manual APIRouter creation is FORBIDDEN.
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query

from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.router_factory import RouterFactory

from .schemas import (
    CustomerLifecycleAction,
    CustomerLifecycleResponse,
    CustomerRegistrationRequest,
    EndpointTrendsResponse,
    MaintenanceExecutionRequest,
    MaintenanceResult,
    NetworkEndpointCreate,
    NetworkEndpointResponse,
    NetworkEndpointUpdate,
    NetworkHealthSummary,
    OperationsStatus,
    ServiceHealthCheckRequest,
    ServiceHealthCheckResponse,
    ServiceProvisioningRequest,
    ServiceProvisioningResponse,
)
from .services import OperationsService

logger = logging.getLogger(__name__)


class OperationsRouterFactory(RouterFactory):
    """Specialized router factory for operations automation."""

    @classmethod
    def create_network_monitoring_router(
        cls, service_class, prefix="/network-monitoring"
    ) -> APIRouter:
        """Create router for network monitoring operations."""
        
        router = APIRouter(
            prefix=prefix,
            tags=["operations", "network-monitoring"],
            responses={
                400: {"description": "Validation Error"},
                401: {"description": "Authentication Error"},
                403: {"description": "Authorization Error"},
                404: {"description": "Not Found"},
                500: {"description": "Internal Server Error"},
            },
        )

        @router.post("/endpoints", response_model=NetworkEndpointResponse, status_code=201)
        @standard_exception_handler
        async def register_endpoint(
            data: NetworkEndpointCreate = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> NetworkEndpointResponse:
            """Register network endpoint for monitoring."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.create_endpoint(data.model_dump(), deps.user_id)

        @router.get("/health", response_model=NetworkHealthSummary)
        @standard_exception_handler
        async def get_network_health(
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> NetworkHealthSummary:
            """Get comprehensive network health summary."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_network_health(deps.user_id)

        @router.get("/endpoints/{endpoint_id}/trends", response_model=EndpointTrendsResponse)
        @standard_exception_handler
        async def get_endpoint_trends(
            endpoint_id: UUID = Path(..., description="Endpoint ID"),
            hours: int = Query(24, ge=1, le=168, description="Time period in hours"),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> EndpointTrendsResponse:
            """Get endpoint health trends."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_endpoint_trends(endpoint_id, hours, deps.user_id)

        @router.post("/health-check", response_model=ServiceHealthCheckResponse)
        @standard_exception_handler
        async def check_service_health(
            request: ServiceHealthCheckRequest = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> ServiceHealthCheckResponse:
            """Perform health check on specific service."""
            service = service_class(deps.db, deps.tenant_id)
            
            connection_params = {}
            if request.connection_string:
                connection_params["connection_string"] = request.connection_string
                connection_params["redis_url"] = request.connection_string
            if request.container_id:
                connection_params["container_id"] = request.container_id
            connection_params["timeout"] = request.timeout
            
            return await service.network_monitoring.check_service_health(
                request.service_type, connection_params, deps.user_id
            )

        @router.delete("/endpoints/{endpoint_id}")
        @standard_exception_handler
        async def unregister_endpoint(
            endpoint_id: UUID = Path(..., description="Endpoint ID"),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> Dict[str, str]:
            """Unregister endpoint from monitoring."""
            service = service_class(deps.db, deps.tenant_id)
            await service.network_monitoring.unregister_endpoint(endpoint_id, deps.user_id)
            return {"message": "Endpoint unregistered successfully"}

        return router

    @classmethod
    def create_customer_lifecycle_router(
        cls, service_class, prefix="/customer-lifecycle"
    ) -> APIRouter:
        """Create router for customer lifecycle management."""
        
        router = APIRouter(
            prefix=prefix,
            tags=["operations", "customer-lifecycle"],
            responses={
                400: {"description": "Validation Error"},
                401: {"description": "Authentication Error"},
                403: {"description": "Authorization Error"},
                404: {"description": "Not Found"},
                500: {"description": "Internal Server Error"},
            },
        )

        @router.post("/register", response_model=CustomerLifecycleResponse, status_code=201)
        @standard_exception_handler
        async def register_customer(
            data: CustomerRegistrationRequest = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> CustomerLifecycleResponse:
            """Register new customer with automated lifecycle management."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.register_customer(data.model_dump(), deps.user_id)

        @router.post("/customers/{customer_id}/verify", response_model=CustomerLifecycleResponse)
        @standard_exception_handler
        async def verify_customer(
            customer_id: UUID = Path(..., description="Customer ID"),
            verification_data: Dict[str, Any] = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> CustomerLifecycleResponse:
            """Verify customer account."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.customer_lifecycle.verify_customer(
                customer_id, verification_data, deps.user_id
            )

        @router.post("/customers/{customer_id}/suspend", response_model=CustomerLifecycleResponse)
        @standard_exception_handler
        async def suspend_customer(
            customer_id: UUID = Path(..., description="Customer ID"),
            action: CustomerLifecycleAction = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> CustomerLifecycleResponse:
            """Suspend customer account."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.customer_lifecycle.suspend_customer(
                customer_id,
                action.reason or "Administrative action",
                action.parameters,
                deps.user_id
            )

        @router.post("/customers/{customer_id}/services", response_model=ServiceProvisioningResponse)
        @standard_exception_handler
        async def provision_service(
            customer_id: UUID = Path(..., description="Customer ID"),
            request: ServiceProvisioningRequest = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> ServiceProvisioningResponse:
            """Provision service for customer."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.provision_service(
                customer_id,
                request.service_name,
                request.custom_config or {},
                deps.user_id
            )

        @router.get("/provisioning/{request_id}", response_model=ServiceProvisioningResponse)
        @standard_exception_handler
        async def get_provisioning_status(
            request_id: UUID = Path(..., description="Provisioning request ID"),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> ServiceProvisioningResponse:
            """Get service provisioning status."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.customer_lifecycle.get_provisioning_status(request_id, deps.user_id)

        @router.get("/customers/{customer_id}/summary")
        @standard_exception_handler
        async def get_customer_summary(
            customer_id: UUID = Path(..., description="Customer ID"),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> Dict[str, Any]:
            """Get customer lifecycle summary."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.customer_lifecycle.get_customer_lifecycle_summary(
                customer_id, deps.user_id
            )

        return router

    @classmethod
    def create_infrastructure_maintenance_router(
        cls, service_class, prefix="/infrastructure-maintenance"
    ) -> APIRouter:
        """Create router for infrastructure maintenance operations."""
        
        router = APIRouter(
            prefix=prefix,
            tags=["operations", "infrastructure-maintenance"],
            responses={
                400: {"description": "Validation Error"},
                401: {"description": "Authentication Error"},
                403: {"description": "Authorization Error"},
                404: {"description": "Not Found"},
                500: {"description": "Internal Server Error"},
            },
        )

        @router.post("/execute", response_model=MaintenanceResult)
        @standard_exception_handler
        async def execute_maintenance(
            request: MaintenanceExecutionRequest = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> MaintenanceResult:
            """Execute maintenance operation manually."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.execute_maintenance(
                request.maintenance_type,
                request.parameters or {},
                deps.user_id
            )

        @router.get("/status", response_model=OperationsStatus)
        @standard_exception_handler
        async def get_operations_status(
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> OperationsStatus:
            """Get comprehensive operations automation status."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_operations_status(deps.user_id)

        @router.post("/start")
        @standard_exception_handler
        async def start_operations(
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> Dict[str, str]:
            """Start operations automation."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.infrastructure_maintenance.start_operations(deps.user_id)

        @router.post("/stop")
        @standard_exception_handler
        async def stop_operations(
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> Dict[str, str]:
            """Stop operations automation."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.infrastructure_maintenance.stop_operations(deps.user_id)

        # Database maintenance endpoints
        @router.post("/database/cleanup", response_model=MaintenanceResult)
        @standard_exception_handler
        async def database_cleanup(
            parameters: Dict[str, Any] = Body(default_factory=dict),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> MaintenanceResult:
            """Execute database cleanup maintenance."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.execute_maintenance("database_cleanup", parameters, deps.user_id)

        @router.post("/logs/rotate", response_model=MaintenanceResult)
        @standard_exception_handler
        async def log_rotation(
            parameters: Dict[str, Any] = Body(default_factory=dict),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> MaintenanceResult:
            """Execute log rotation maintenance."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.execute_maintenance("log_rotation", parameters, deps.user_id)

        @router.post("/cache/cleanup", response_model=MaintenanceResult)
        @standard_exception_handler
        async def cache_cleanup(
            parameters: Dict[str, Any] = Body(default_factory=dict),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> MaintenanceResult:
            """Execute cache cleanup maintenance."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.execute_maintenance("cache_cleanup", parameters, deps.user_id)

        @router.post("/performance/optimize", response_model=MaintenanceResult)
        @standard_exception_handler
        async def performance_optimization(
            parameters: Dict[str, Any] = Body(default_factory=dict),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
        ) -> MaintenanceResult:
            """Execute performance optimization maintenance."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.execute_maintenance("performance_optimization", parameters, deps.user_id)

        return router


# Create the operations routers using the factory
def create_operations_routers() -> List[APIRouter]:
    """Create all operations routers using the RouterFactory pattern."""
    
    routers = []
    
    # Network monitoring router
    network_router = OperationsRouterFactory.create_network_monitoring_router(
        service_class=OperationsService
    )
    routers.append(network_router)
    
    # Customer lifecycle router
    lifecycle_router = OperationsRouterFactory.create_customer_lifecycle_router(
        service_class=OperationsService
    )
    routers.append(lifecycle_router)
    
    # Infrastructure maintenance router
    maintenance_router = OperationsRouterFactory.create_infrastructure_maintenance_router(
        service_class=OperationsService
    )
    routers.append(maintenance_router)
    
    # Combined operations status router
    status_router = APIRouter(
        prefix="/operations",
        tags=["operations"],
        responses={
            400: {"description": "Validation Error"},
            401: {"description": "Authentication Error"},
            403: {"description": "Authorization Error"},
            404: {"description": "Not Found"},
            500: {"description": "Internal Server Error"},
        },
    )
    
    @status_router.get("/status", response_model=Dict[str, Any])
    @standard_exception_handler
    async def get_comprehensive_operations_status(
        deps: StandardDependencies = Depends(get_standard_deps) = Depends(),
    ) -> Dict[str, Any]:
        """Get comprehensive status of all operations systems."""
        service = OperationsService(deps.db, deps.tenant_id)
        
        # Get status from all subsystems
        network_health = await service.get_network_health(deps.user_id)
        operations_status = await service.get_operations_status(deps.user_id)
        
        return {
            "network_health": {
                "overall_status": network_health.overall_status,
                "total_endpoints": network_health.total_endpoints,
                "healthy_count": network_health.healthy_count,
                "average_response_time": network_health.average_response_time,
            },
            "maintenance_automation": {
                "scheduler_running": operations_status.scheduler_running,
                "active_tasks": operations_status.active_tasks,
                "recent_results_count": len(operations_status.recent_results),
            },
            "timestamp": operations_status.timestamp,
        }
    
    routers.append(status_router)
    
    logger.info("Created operations routers using RouterFactory patterns")
    return routers


# Export main router creation function
__all__ = ["create_operations_routers", "OperationsRouterFactory"]