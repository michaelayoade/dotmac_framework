"""
Service Marketplace Integration

Provides centralized service discovery, registration, and management
for the consolidated DotMac framework services.

This marketplace enables:
- Service registration and discovery
- Service health monitoring and status
- Load balancing and failover
- Service versioning and deployment
- API gateway integration
- Service metrics and analytics
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..core.exceptions import BusinessLogicError, EntityNotFoundError, ValidationError
from .base import BaseService

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service status in the marketplace."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"


class ServiceType(str, Enum):
    """Types of services in the marketplace."""

    BUSINESS_LOGIC = "business_logic"
    DATA_ACCESS = "data_access"
    INTEGRATION = "integration"
    INFRASTRUCTURE = "infrastructure"
    ANALYTICS = "analytics"
    SECURITY = "security"
    WORKFLOW = "workflow"
    NOTIFICATION = "notification"


class DeploymentStatus(str, Enum):
    """Service deployment status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPLOYING = "deploying"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"


class ServiceMetadata:
    """Metadata for a registered service."""

    def __init__(
        self,
        service_id: str,
        name: str,
        version: str,
        service_type: ServiceType,
        description: str,
        endpoints: list[dict[str, Any]],
        dependencies: list[str] | None = None,
        capabilities: list[str] | None = None,
        config_schema: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ):
        self.service_id = service_id
        self.name = name
        self.version = version
        self.service_type = service_type
        self.description = description
        self.endpoints = endpoints
        self.dependencies = dependencies or []
        self.capabilities = capabilities or []
        self.config_schema = config_schema or {}
        self.tags = tags or {}
        self.registered_at = datetime.now(timezone.utc)
        self.last_health_check = datetime.now(timezone.utc)
        self.status = ServiceStatus.UNKNOWN


class ServiceInstance:
    """Runtime instance of a registered service."""

    def __init__(
        self,
        instance_id: str,
        service_id: str,
        host: str,
        port: int,
        base_path: str = "",
        health_check_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.instance_id = instance_id
        self.service_id = service_id
        self.host = host
        self.port = port
        self.base_path = base_path
        self.health_check_url = health_check_url or f"http://{host}:{port}{base_path}/health"
        self.metadata = metadata or {}
        self.status = ServiceStatus.UNKNOWN
        self.last_seen = datetime.now(timezone.utc)
        self.deployment_status = DeploymentStatus.ACTIVE


class ServiceMarketplace(BaseService):
    """
    Centralized service marketplace for discovery, registration, and management.

    Features:
    - Service registration and discovery
    - Health monitoring and status tracking
    - Load balancing and failover
    - Service versioning and lifecycle management
    - API gateway integration
    - Service metrics and analytics
    """

    def __init__(
        self,
        db_session: Session | AsyncSession,
        tenant_id: str | None = None,
        marketplace_config: dict[str, Any] | None = None,
    ):
        super().__init__(db_session, tenant_id)
        self.config = marketplace_config or {}

        # Service registry storage
        self.services: dict[str, ServiceMetadata] = {}
        self.instances: dict[str, dict[str, ServiceInstance]] = {}  # service_id -> {instance_id: instance}

        # Monitoring and health check configuration
        self.health_check_interval = self.config.get("health_check_interval_seconds", 30)
        self.instance_timeout = self.config.get("instance_timeout_seconds", 300)

        # Load balancing strategies
        self.load_balancing_strategies = {
            "round_robin": self._round_robin_strategy,
            "least_connections": self._least_connections_strategy,
            "random": self._random_strategy,
            "health_weighted": self._health_weighted_strategy,
        }

        # Service lifecycle hooks
        self.lifecycle_hooks: dict[str, list[Callable]] = {
            "service_registered": [],
            "service_deregistered": [],
            "instance_added": [],
            "instance_removed": [],
            "health_changed": [],
        }

    # Service Registration

    async def register_service(
        self, metadata: ServiceMetadata, initial_instances: list[ServiceInstance] | None = None
    ) -> bool:
        """Register a new service in the marketplace."""
        try:
            # Validate service metadata
            await self._validate_service_metadata(metadata)

            # Store service metadata
            self.services[metadata.service_id] = metadata

            # Initialize instance storage
            self.instances[metadata.service_id] = {}

            # Register initial instances if provided
            if initial_instances:
                for instance in initial_instances:
                    await self.register_instance(instance)

            # Trigger lifecycle hooks
            await self._trigger_lifecycle_hooks("service_registered", metadata)

            logger.info(f"Registered service: {metadata.name} (ID: {metadata.service_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to register service {metadata.service_id}: {e}")
            raise BusinessLogicError(f"Service registration failed: {e}") from e

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from the marketplace."""
        try:
            if service_id not in self.services:
                raise EntityNotFoundError(f"Service {service_id} not found")

            metadata = self.services[service_id]

            # Remove all instances
            if service_id in self.instances:
                for instance_id in list(self.instances[service_id].keys()):
                    await self.deregister_instance(service_id, instance_id)

            # Remove service metadata
            del self.services[service_id]

            # Trigger lifecycle hooks
            await self._trigger_lifecycle_hooks("service_deregistered", metadata)

            logger.info(f"Deregistered service: {metadata.name} (ID: {service_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            raise BusinessLogicError(f"Service deregistration failed: {e}") from e

    # Instance Management

    async def register_instance(self, instance: ServiceInstance) -> bool:
        """Register a service instance."""
        try:
            if instance.service_id not in self.services:
                raise EntityNotFoundError(f"Service {instance.service_id} not registered")

            # Store instance
            if instance.service_id not in self.instances:
                self.instances[instance.service_id] = {}

            self.instances[instance.service_id][instance.instance_id] = instance

            # Perform initial health check
            await self._check_instance_health(instance)

            # Trigger lifecycle hooks
            await self._trigger_lifecycle_hooks("instance_added", instance)

            logger.info(f"Registered instance: {instance.instance_id} for service {instance.service_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to register instance {instance.instance_id}: {e}")
            raise BusinessLogicError(f"Instance registration failed: {e}") from e

    async def deregister_instance(self, service_id: str, instance_id: str) -> bool:
        """Deregister a service instance."""
        try:
            if service_id not in self.instances or instance_id not in self.instances[service_id]:
                raise EntityNotFoundError(f"Instance {instance_id} not found for service {service_id}")

            instance = self.instances[service_id][instance_id]

            # Remove instance
            del self.instances[service_id][instance_id]

            # Trigger lifecycle hooks
            await self._trigger_lifecycle_hooks("instance_removed", instance)

            logger.info(f"Deregistered instance: {instance_id} for service {service_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to deregister instance {instance_id}: {e}")
            raise BusinessLogicError(f"Instance deregistration failed: {e}") from e

    # Service Discovery

    async def discover_service(
        self,
        service_name: str | None = None,
        service_type: ServiceType | None = None,
        capabilities: list[str] | None = None,
        tags: dict[str, str] | None = None,
        healthy_only: bool = True,
    ) -> list[ServiceMetadata]:
        """Discover services matching the given criteria."""
        results = []

        for service in self.services.values():
            # Apply filters
            if service_name and service.name != service_name:
                continue

            if service_type and service.service_type != service_type:
                continue

            if capabilities and not all(cap in service.capabilities for cap in capabilities):
                continue

            if tags and not all(service.tags.get(k) == v for k, v in tags.items()):
                continue

            if healthy_only and service.status not in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
                continue

            results.append(service)

        return results

    async def get_service_instances(
        self, service_id: str, healthy_only: bool = True, load_balancing_strategy: str = "round_robin"
    ) -> list[ServiceInstance]:
        """Get instances for a service, optionally applying load balancing."""
        if service_id not in self.instances:
            return []

        instances = list(self.instances[service_id].values())

        # Filter healthy instances if requested
        if healthy_only:
            instances = [i for i in instances if i.status == ServiceStatus.HEALTHY]

        # Apply load balancing strategy
        if load_balancing_strategy in self.load_balancing_strategies:
            strategy_func = self.load_balancing_strategies[load_balancing_strategy]
            instances = strategy_func(instances)

        return instances

    # Health Monitoring

    async def check_service_health(self, service_id: str) -> dict[str, Any]:
        """Check health of a service and all its instances."""
        if service_id not in self.services:
            raise EntityNotFoundError(f"Service {service_id} not found")

        service_metadata = self.services[service_id]
        service_instances = self.instances.get(service_id, {})

        health_status = {
            "service_id": service_id,
            "service_name": service_metadata.name,
            "overall_status": ServiceStatus.UNKNOWN,
            "instances": {},
            "healthy_instances": 0,
            "total_instances": len(service_instances),
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

        # Check each instance
        healthy_count = 0
        for instance_id, instance in service_instances.items():
            instance_health = await self._check_instance_health(instance)
            health_status["instances"][instance_id] = instance_health

            if instance_health["status"] == ServiceStatus.HEALTHY:
                healthy_count += 1

        health_status["healthy_instances"] = healthy_count

        # Determine overall service health
        if healthy_count == 0:
            overall_status = ServiceStatus.UNHEALTHY
        elif healthy_count < len(service_instances):
            overall_status = ServiceStatus.DEGRADED
        else:
            overall_status = ServiceStatus.HEALTHY

        # Update service status
        service_metadata.status = overall_status
        service_metadata.last_health_check = datetime.now(timezone.utc)
        health_status["overall_status"] = overall_status

        # Trigger health change hooks if needed
        await self._trigger_lifecycle_hooks(
            "health_changed",
            {"service_id": service_id, "old_status": service_metadata.status, "new_status": overall_status},
        )

        return health_status

    async def check_all_services_health(self) -> dict[str, Any]:
        """Check health of all registered services."""
        health_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_services": len(self.services),
            "healthy_services": 0,
            "degraded_services": 0,
            "unhealthy_services": 0,
            "services": {},
        }

        for service_id in self.services.keys():
            service_health = await self.check_service_health(service_id)
            health_report["services"][service_id] = service_health

            status = service_health["overall_status"]
            if status == ServiceStatus.HEALTHY:
                health_report["healthy_services"] += 1
            elif status == ServiceStatus.DEGRADED:
                health_report["degraded_services"] += 1
            else:
                health_report["unhealthy_services"] += 1

        return health_report

    # Service Metrics and Analytics

    async def get_service_metrics(self, service_id: str, time_range: timedelta = timedelta(hours=1)) -> dict[str, Any]:
        """Get metrics for a service."""
        if service_id not in self.services:
            raise EntityNotFoundError(f"Service {service_id} not found")

        # Placeholder for metrics collection
        # In real implementation, this would query metrics storage
        return {
            "service_id": service_id,
            "time_range": time_range.total_seconds(),
            "requests_per_second": 0,
            "average_response_time": 0,
            "error_rate": 0,
            "availability": 100.0,
        }

    async def get_marketplace_metrics(self) -> dict[str, Any]:
        """Get overall marketplace metrics."""
        total_services = len(self.services)
        total_instances = sum(len(instances) for instances in self.instances.values())

        # Calculate health statistics
        healthy_services = sum(1 for s in self.services.values() if s.status == ServiceStatus.HEALTHY)
        healthy_instances = sum(
            1 for instances in self.instances.values() for i in instances.values() if i.status == ServiceStatus.HEALTHY
        )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_services": total_services,
            "total_instances": total_instances,
            "healthy_services": healthy_services,
            "healthy_instances": healthy_instances,
            "service_availability": (healthy_services / total_services * 100) if total_services > 0 else 0,
            "instance_availability": (healthy_instances / total_instances * 100) if total_instances > 0 else 0,
        }

    # API Gateway Integration

    async def get_api_gateway_config(self) -> dict[str, Any]:
        """Generate API gateway configuration for all registered services."""
        gateway_config = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "routes": [],
            "services": [],
            "upstreams": [],
        }

        for service_id, service_metadata in self.services.items():
            if service_id not in self.instances or not self.instances[service_id]:
                continue

            # Generate service configuration
            service_config = {
                "name": service_metadata.name,
                "id": service_id,
                "type": service_metadata.service_type.value,
                "version": service_metadata.version,
            }

            # Generate upstream configuration
            healthy_instances = [i for i in self.instances[service_id].values() if i.status == ServiceStatus.HEALTHY]

            if healthy_instances:
                upstream_config = {
                    "name": f"{service_metadata.name}_upstream",
                    "targets": [{"target": f"{i.host}:{i.port}", "weight": 100} for i in healthy_instances],
                }
                gateway_config["upstreams"].append(upstream_config)

                # Generate routes from service endpoints
                for endpoint in service_metadata.endpoints:
                    route_config = {
                        "name": f"{service_metadata.name}_{endpoint.get('name', 'default')}",
                        "paths": [f"{service_metadata.name.lower()}{endpoint.get('path', '')}"],
                        "methods": endpoint.get("methods", ["GET", "POST"]),
                        "service": {"name": f"{service_metadata.name}_upstream"},
                    }
                    gateway_config["routes"].append(route_config)

            gateway_config["services"].append(service_config)

        return gateway_config

    # Lifecycle Hooks

    def add_lifecycle_hook(self, event: str, callback: Callable) -> None:
        """Add a lifecycle hook for marketplace events."""
        if event in self.lifecycle_hooks:
            self.lifecycle_hooks[event].append(callback)

    async def _trigger_lifecycle_hooks(self, event: str, data: Any) -> None:
        """Trigger lifecycle hooks for an event."""
        if event in self.lifecycle_hooks:
            for hook in self.lifecycle_hooks[event]:
                try:
                    await hook(data) if callable(hook) else None
                except Exception as e:
                    logger.warning(f"Lifecycle hook failed for event {event}: {e}")

    # Private Helper Methods

    async def _validate_service_metadata(self, metadata: ServiceMetadata) -> None:
        """Validate service metadata."""
        if not metadata.service_id:
            raise ValidationError("Service ID is required")

        if not metadata.name:
            raise ValidationError("Service name is required")

        if not metadata.version:
            raise ValidationError("Service version is required")

        if metadata.service_id in self.services:
            raise ValidationError(f"Service {metadata.service_id} already registered")

    async def _check_instance_health(self, instance: ServiceInstance) -> dict[str, Any]:
        """Check health of a single service instance."""
        health_result = {
            "instance_id": instance.instance_id,
            "status": ServiceStatus.UNKNOWN,
            "response_time_ms": 0,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }

        try:
            # Placeholder for actual health check HTTP request
            # In real implementation, this would make HTTP request to health_check_url

            # Simulate health check
            from secrets import SystemRandom

            _sr = SystemRandom()

            if _sr.random() > 0.1:  # 90% success rate for demo
                instance.status = ServiceStatus.HEALTHY
                health_result["status"] = ServiceStatus.HEALTHY
                health_result["response_time_ms"] = _sr.randint(10, 100)
            else:
                instance.status = ServiceStatus.UNHEALTHY
                health_result["status"] = ServiceStatus.UNHEALTHY
                health_result["error"] = "Health check failed"

            instance.last_seen = datetime.now(timezone.utc)

        except Exception as e:
            instance.status = ServiceStatus.UNHEALTHY
            health_result["status"] = ServiceStatus.UNHEALTHY
            health_result["error"] = str(e)

        return health_result

    # Load Balancing Strategies

    def _round_robin_strategy(self, instances: list[ServiceInstance]) -> list[ServiceInstance]:
        """Round-robin load balancing strategy."""
        # Placeholder - in real implementation, would maintain round-robin state
        return instances

    def _least_connections_strategy(self, instances: list[ServiceInstance]) -> list[ServiceInstance]:
        """Least connections load balancing strategy."""
        # Placeholder - in real implementation, would track connection counts
        return instances

    def _random_strategy(self, instances: list[ServiceInstance]) -> list[ServiceInstance]:
        """Random load balancing strategy."""
        import random

        return random.sample(instances, len(instances))

    def _health_weighted_strategy(self, instances: list[ServiceInstance]) -> list[ServiceInstance]:
        """Health-weighted load balancing strategy."""
        # Placeholder - in real implementation, would weight by health score
        return instances


# Service Marketplace Factory


class ServiceMarketplaceFactory:
    """Factory for creating service marketplace instances."""

    @staticmethod
    def create_marketplace(
        db_session: Session | AsyncSession, tenant_id: str | None = None, config: dict[str, Any] | None = None
    ) -> ServiceMarketplace:
        """Create a service marketplace instance."""
        return ServiceMarketplace(db_session, tenant_id, config)

    @staticmethod
    def create_service_metadata(
        name: str, version: str, service_type: ServiceType, description: str, endpoints: list[dict[str, Any]], **kwargs
    ) -> ServiceMetadata:
        """Create service metadata for registration."""
        service_id = kwargs.get("service_id", str(uuid4()))
        return ServiceMetadata(
            service_id=service_id,
            name=name,
            version=version,
            service_type=service_type,
            description=description,
            endpoints=endpoints,
            **kwargs,
        )

    @staticmethod
    def create_service_instance(service_id: str, host: str, port: int, **kwargs) -> ServiceInstance:
        """Create service instance for registration."""
        instance_id = kwargs.get("instance_id", str(uuid4()))
        return ServiceInstance(instance_id=instance_id, service_id=service_id, host=host, port=port, **kwargs)


# Marketplace Integration for Consolidated Services


def register_consolidated_services(marketplace: ServiceMarketplace) -> dict[str, ServiceMetadata]:
    """Register all consolidated services with the marketplace."""

    consolidated_services = {
        "unified_billing": ServiceMarketplaceFactory.create_service_metadata(
            name="Unified Billing Service",
            version="2.0.0",
            service_type=ServiceType.BUSINESS_LOGIC,
            description="Consolidated billing service handling invoicing, payments, and subscriptions",
            endpoints=[
                {"name": "invoices", "path": "/invoices", "methods": ["GET", "POST"]},
                {"name": "payments", "path": "/payments", "methods": ["GET", "POST"]},
                {"name": "subscriptions", "path": "/subscriptions", "methods": ["GET", "POST", "PUT"]},
            ],
            capabilities=["invoicing", "payment_processing", "subscription_management"],
            tags={"domain": "billing", "consolidated": "true"},
        ),
        "unified_analytics": ServiceMarketplaceFactory.create_service_metadata(
            name="Unified Analytics Service",
            version="2.0.0",
            service_type=ServiceType.ANALYTICS,
            description="Consolidated analytics service for business, workflow, and infrastructure analytics",
            endpoints=[
                {"name": "metrics", "path": "/metrics", "methods": ["GET", "POST"]},
                {"name": "dashboards", "path": "/dashboards", "methods": ["GET", "POST", "PUT"]},
                {"name": "reports", "path": "/reports", "methods": ["GET", "POST"]},
            ],
            capabilities=["business_analytics", "workflow_analytics", "infrastructure_analytics"],
            tags={"domain": "analytics", "consolidated": "true"},
        ),
        "unified_identity": ServiceMarketplaceFactory.create_service_metadata(
            name="Unified Identity Service",
            version="2.0.0",
            service_type=ServiceType.SECURITY,
            description="Consolidated identity service for authentication, authorization, and user management",
            endpoints=[
                {"name": "auth", "path": "/auth", "methods": ["POST"]},
                {"name": "users", "path": "/users", "methods": ["GET", "POST", "PUT", "DELETE"]},
                {"name": "permissions", "path": "/permissions", "methods": ["GET", "POST"]},
            ],
            capabilities=["authentication", "authorization", "user_management", "rbac"],
            tags={"domain": "identity", "consolidated": "true"},
        ),
    }

    return consolidated_services
