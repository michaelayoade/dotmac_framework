"""
Integration Hub - Central management for all integrations
Enforces DRY patterns and provides unified interface
"""

import logging
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.schemas.base_schemas import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseUpdateSchema,
)

from .base_integration import BaseIntegration, IntegrationConfig, IntegrationMetrics

logger = logging.getLogger(__name__)


class IntegrationCreateSchema(BaseCreateSchema):
    """Schema for creating new integration connections."""
    name: str
    integration_type: str
    description: Optional[str] = None
    config: Dict[str, Any]
    credentials: Dict[str, Any]
    enabled: bool = True


class IntegrationUpdateSchema(BaseUpdateSchema):
    """Schema for updating integration connections."""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class IntegrationResponseSchema(BaseResponseSchema):
    """Response schema for integration connections."""
    name: str
    integration_type: str
    description: Optional[str] = None
    status: str
    enabled: bool
    last_sync: Optional[str] = None
    metrics: IntegrationMetrics
    health: Dict[str, Any]


class IntegrationHubService:
    """
    Central service for managing all integrations.
    Follows DRY patterns from dotmac_shared.
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.integrations: Dict[str, BaseIntegration] = {}
        self.integration_types: Dict[str, Type[BaseIntegration]] = {}
        
    def register_integration_type(
        self, 
        name: str, 
        integration_class: Type[BaseIntegration]
    ):
        """Register a new integration type."""
        self.integration_types[name] = integration_class
        logger.info(f"Registered integration type: {name}")

    @standard_exception_handler
    async def create(
        self, 
        data: IntegrationCreateSchema, 
        user_id: UUID
    ) -> IntegrationResponseSchema:
        """Create a new integration connection."""
        
        # Validate integration type
        if data.integration_type not in self.integration_types:
            raise ValueError(f"Unknown integration type: {data.integration_type}")
            
        # Create integration config
        config = IntegrationConfig(
            name=data.name,
            description=data.description or "",
            version="1.0.0",
            enabled=data.enabled,
            **data.config
        )
        
        # Instantiate integration
        integration_class = self.integration_types[data.integration_type]
        integration = integration_class(self.db, self.tenant_id, config)
        
        # Initialize and authenticate
        await integration.initialize()
        
        if data.credentials:
            auth_success = await integration.authenticate(data.credentials)
            if not auth_success:
                raise ValueError("Authentication failed")
        
        # Store in registry
        self.integrations[data.name] = integration
        
        logger.info(f"Created integration: {data.name} ({data.integration_type})")
        
        return await self._integration_to_response(integration)

    @standard_exception_handler
    async def get_by_id(
        self, 
        integration_id: UUID, 
        user_id: UUID
    ) -> IntegrationResponseSchema:
        """Get integration by ID."""
        # In a real implementation, this would query the database
        # For now, using the integration name as identifier
        integration_name = str(integration_id)  # Simplified
        
        if integration_name not in self.integrations:
            raise ValueError(f"Integration not found: {integration_name}")
            
        integration = self.integrations[integration_name]
        return await self._integration_to_response(integration)

    @standard_exception_handler
    async def update(
        self, 
        integration_id: UUID, 
        data: IntegrationUpdateSchema, 
        user_id: UUID
    ) -> IntegrationResponseSchema:
        """Update integration configuration."""
        integration_name = str(integration_id)  # Simplified
        
        if integration_name not in self.integrations:
            raise ValueError(f"Integration not found: {integration_name}")
            
        integration = self.integrations[integration_name]
        
        # Update configuration
        if data.config:
            new_config = IntegrationConfig(
                name=data.name or integration.config.name,
                description=data.description or integration.config.description,
                version=integration.config.version,
                enabled=data.enabled if data.enabled is not None else integration.config.enabled,
                **data.config
            )
            await integration.update_config(new_config)
            
        logger.info(f"Updated integration: {integration_name}")
        
        return await self._integration_to_response(integration)

    @standard_exception_handler
    async def delete(
        self, 
        integration_id: UUID, 
        user_id: UUID, 
        soft_delete: bool = True
    ):
        """Delete/disable integration."""
        integration_name = str(integration_id)  # Simplified
        
        if integration_name not in self.integrations:
            raise ValueError(f"Integration not found: {integration_name}")
            
        if soft_delete:
            await self.integrations[integration_name].disable()
        else:
            del self.integrations[integration_name]
            
        logger.info(f"{'Disabled' if soft_delete else 'Deleted'} integration: {integration_name}")

    @standard_exception_handler
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "name",
        user_id: Optional[UUID] = None,
    ) -> List[IntegrationResponseSchema]:
        """List all integrations with filtering."""
        integrations = []
        
        for name, integration in self.integrations.items():
            # Apply filters
            if filters:
                if "enabled" in filters and integration.config.enabled != filters["enabled"]:
                    continue
                if "integration_type" in filters:
                    # Would need to store type info
                    pass
                    
            integrations.append(await self._integration_to_response(integration))
            
        # Apply pagination
        return integrations[skip:skip + limit]

    @standard_exception_handler
    async def count(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> int:
        """Count integrations with filters."""
        count = 0
        for integration in self.integrations.values():
            if filters:
                if "enabled" in filters and integration.config.enabled != filters["enabled"]:
                    continue
            count += 1
        return count

    async def _integration_to_response(
        self, 
        integration: BaseIntegration
    ) -> IntegrationResponseSchema:
        """Convert integration to response schema."""
        health = await integration.health_check()
        metrics = await integration.get_metrics()
        
        return IntegrationResponseSchema(
            id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
            name=integration.config.name,
            integration_type="generic",  # Would need to track this
            description=integration.config.description,
            status="healthy" if health.get("status") == "ok" else "unhealthy",
            enabled=integration.config.enabled,
            metrics=metrics,
            health=health,
            created_at="2024-01-01T00:00:00Z",  # Placeholder
            updated_at="2024-01-01T00:00:00Z",  # Placeholder
        )

    @standard_exception_handler
    async def test_connection(
        self, 
        integration_name: str
    ) -> Dict[str, Any]:
        """Test connection for specific integration."""
        if integration_name not in self.integrations:
            raise ValueError(f"Integration not found: {integration_name}")
            
        integration = self.integrations[integration_name]
        return await integration.test_connection()

    @standard_exception_handler
    async def sync_integration(
        self, 
        integration_name: str
    ) -> Dict[str, Any]:
        """Trigger data sync for specific integration."""
        if integration_name not in self.integrations:
            raise ValueError(f"Integration not found: {integration_name}")
            
        integration = self.integrations[integration_name]
        return await integration.sync_data()

    @standard_exception_handler
    async def get_hub_status(self) -> Dict[str, Any]:
        """Get overall integration hub status."""
        total_integrations = len(self.integrations)
        enabled_integrations = sum(
            1 for i in self.integrations.values() 
            if i.config.enabled
        )
        
        health_checks = {}
        for name, integration in self.integrations.items():
            try:
                health = await integration.health_check()
                health_checks[name] = health
            except Exception as e:
                health_checks[name] = {"status": "error", "error": str(e)}
        
        healthy_integrations = sum(
            1 for health in health_checks.values()
            if health.get("status") == "ok"
        )
        
        return {
            "total_integrations": total_integrations,
            "enabled_integrations": enabled_integrations,
            "healthy_integrations": healthy_integrations,
            "health_checks": health_checks,
            "overall_status": "healthy" if healthy_integrations == enabled_integrations else "degraded"
        }


class IntegrationHubRouter:
    """Router factory for Integration Hub following DRY patterns."""

    @classmethod
    def create_router(cls) -> APIRouter:
        """Create Integration Hub router using RouterFactory."""
        
        # Use RouterFactory for standard CRUD operations
        router = RouterFactory.create_crud_router(
            service_class=IntegrationHubService,
            create_schema=IntegrationCreateSchema,
            update_schema=IntegrationUpdateSchema,
            response_schema=IntegrationResponseSchema,
            prefix="/integrations",
            tags=["integrations", "hub"],
            enable_search=True,
            enable_bulk_operations=False,  # Integrations are typically managed individually
        )

        # Add custom integration-specific endpoints
        @router.get("/status", response_model=Dict[str, Any])
        @standard_exception_handler
        async def get_hub_status(deps: StandardDependencies = Depends(get_standard_deps) = Depends()):
            """Get integration hub status."""
            service = IntegrationHubService(deps.db, deps.tenant_id)
            return await service.get_hub_status()

        @router.post("/{integration_name}/test", response_model=Dict[str, Any])
        @standard_exception_handler
        async def test_integration_connection(
            integration_name: str,
            deps: StandardDependencies = Depends(get_standard_deps) = Depends()
        ):
            """Test connection for specific integration."""
            service = IntegrationHubService(deps.db, deps.tenant_id)
            return await service.test_connection(integration_name)

        @router.post("/{integration_name}/sync", response_model=Dict[str, Any])
        @standard_exception_handler
        async def sync_integration(
            integration_name: str,
            deps: StandardDependencies = Depends(get_standard_deps) = Depends()
        ):
            """Trigger data sync for specific integration."""
            service = IntegrationHubService(deps.db, deps.tenant_id)
            return await service.sync_integration(integration_name)

        return router