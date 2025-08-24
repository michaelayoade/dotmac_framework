"""
Gateway SDK - Core gateway management, routing, and load balancing.
"""

from datetime import datetime
from ..core.datetime_utils import (
    utc_now_iso,
    utc_now,
    expires_in_days,
    expires_in_hours,
    time_ago_minutes,
    time_ago_hours,
    is_expired_iso,
)
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import GatewayError, RoutingError


class GatewayService:
    """In-memory service for gateway operations."""

    def __init__(self):
        """  Init   operation."""
        self._gateways: Dict[str, Dict[str, Any]] = {}
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._load_balancers: Dict[str, Dict[str, Any]] = {}
        self._gateway_routes: Dict[str, List[str]] = {}
        self._upstream_services: Dict[str, Dict[str, Any]] = {}

    async def create_gateway(self, **kwargs) -> Dict[str, Any]:
        """Create API gateway."""
        gateway_id = kwargs.get("gateway_id") or str(uuid4())

        if gateway_id in self._gateways:
            raise GatewayError(f"Gateway already exists: {gateway_id}")

        gateway = {
            "gateway_id": gateway_id,
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "domains": kwargs.get("domains", []),
            "status": kwargs.get("status", "active"),
            "load_balancer_algorithm": kwargs.get(
                "load_balancer_algorithm", "round_robin"
            ),
            "health_check_enabled": kwargs.get("health_check_enabled", True),
            "health_check_path": kwargs.get("health_check_path", "/health"),
            "health_check_interval": kwargs.get("health_check_interval", 30),
            "ssl_enabled": kwargs.get("ssl_enabled", False),
            "ssl_certificate": kwargs.get("ssl_certificate"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "metadata": kwargs.get("metadata", {}),
        }

        self._gateways[gateway_id] = gateway
        self._gateway_routes[gateway_id] = []

        return gateway

    async def get_gateway(self, gateway_id: str) -> Optional[Dict[str, Any]]:
        """Get gateway by ID."""
        return self._gateways.get(gateway_id)

    async def update_gateway(self, gateway_id: str, **updates) -> Dict[str, Any]:
        """Update gateway."""
        gateway = self._gateways.get(gateway_id)
        if not gateway:
            raise GatewayError(f"Gateway not found: {gateway_id}")

        for key, value in updates.items():
            if key in gateway:
                gateway[key] = value

        gateway["updated_at"] = utc_now_iso()
        return gateway

    async def delete_gateway(self, gateway_id: str) -> bool:
        """Delete gateway."""
        if gateway_id not in self._gateways:
            raise GatewayError(f"Gateway not found: {gateway_id}")

        # Delete associated routes
        route_ids = self._gateway_routes.get(gateway_id, [])
        for route_id in route_ids:
            self._routes.pop(route_id, None)

        del self._gateways[gateway_id]
        del self._gateway_routes[gateway_id]

        return True

    async def create_route(self, **kwargs) -> Dict[str, Any]:
        """Create route."""
        route_id = kwargs.get("route_id") or str(uuid4())
        gateway_id = kwargs["gateway_id"]

        if gateway_id not in self._gateways:
            raise GatewayError(f"Gateway not found: {gateway_id}")

        if route_id in self._routes:
            raise RoutingError(f"Route already exists: {route_id}")

        route = {
            "route_id": route_id,
            "gateway_id": gateway_id,
            "path": kwargs["path"],
            "methods": kwargs.get("methods", ["GET"]),
            "upstream_service": kwargs["upstream_service"],
            "upstream_url": kwargs["upstream_url"],
            "upstream_path": kwargs.get("upstream_path", kwargs["path"]),
            "strip_path": kwargs.get("strip_path", False),
            "preserve_host": kwargs.get("preserve_host", False),
            "timeout": kwargs.get("timeout", 30),
            "retries": kwargs.get("retries", 3),
            "status": kwargs.get("status", "active"),
            "auth_policy_id": kwargs.get("auth_policy_id"),
            "rate_limit_policy_id": kwargs.get("rate_limit_policy_id"),
            "cors_enabled": kwargs.get("cors_enabled", True),
            "cache_enabled": kwargs.get("cache_enabled", False),
            "cache_ttl": kwargs.get("cache_ttl", 300),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "metadata": kwargs.get("metadata", {}),
        }

        self._routes[route_id] = route
        self._gateway_routes[gateway_id].append(route_id)

        return route

    async def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get route by ID."""
        return self._routes.get(route_id)

    async def list_routes(self, gateway_id: str) -> List[Dict[str, Any]]:
        """List routes for gateway."""
        route_ids = self._gateway_routes.get(gateway_id, [])
        return [self._routes[rid] for rid in route_ids if rid in self._routes]

    async def update_route(self, route_id: str, **updates) -> Dict[str, Any]:
        """Update route."""
        route = self._routes.get(route_id)
        if not route:
            raise RoutingError(f"Route not found: {route_id}")

        for key, value in updates.items():
            if key in route:
                route[key] = value

        route["updated_at"] = utc_now_iso()
        return route

    async def delete_route(self, route_id: str) -> bool:
        """Delete route."""
        route = self._routes.get(route_id)
        if not route:
            raise RoutingError(f"Route not found: {route_id}")

        gateway_id = route["gateway_id"]
        if gateway_id in self._gateway_routes:
            self._gateway_routes[gateway_id].remove(route_id)

        del self._routes[route_id]
        return True

    async def configure_load_balancer(
        self, gateway_id: str, **config
    ) -> Dict[str, Any]:
        """Configure load balancer for gateway."""
        if gateway_id not in self._gateways:
            raise GatewayError(f"Gateway not found: {gateway_id}")

        lb_config = {
            "gateway_id": gateway_id,
            "algorithm": config.get("algorithm", "round_robin"),
            "health_check_path": config.get("health_check_path", "/health"),
            "health_check_interval": config.get("health_check_interval", 30),
            "health_check_timeout": config.get("health_check_timeout", 5),
            "connection_timeout": config.get("connection_timeout", 5000),
            "max_connections_per_upstream": config.get(
                "max_connections_per_upstream", 100
            ),
            "upstream_weights": config.get("upstream_weights", {}),
            "sticky_sessions": config.get("sticky_sessions", False),
            "session_cookie_name": config.get("session_cookie_name", "JSESSIONID"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._load_balancers[gateway_id] = lb_config

        # Update gateway with load balancer algorithm
        self._gateways[gateway_id]["load_balancer_algorithm"] = lb_config["algorithm"]
        self._gateways[gateway_id]["updated_at"] = utc_now_iso()

        return lb_config

    async def register_upstream_service(self, **kwargs) -> Dict[str, Any]:
        """Register upstream service."""
        service_id = kwargs.get("service_id") or str(uuid4())

        service = {
            "service_id": service_id,
            "name": kwargs["name"],
            "url": kwargs["url"],
            "health_check_url": kwargs.get(
                "health_check_url", f"{kwargs['url']}/health"
            ),
            "weight": kwargs.get("weight", 100),
            "max_connections": kwargs.get("max_connections", 100),
            "status": kwargs.get("status", "healthy"),
            "last_health_check": None,
            "health_check_failures": 0,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "metadata": kwargs.get("metadata", {}),
        }

        self._upstream_services[service_id] = service
        return service


class GatewaySDK:
    """SDK for API Gateway management."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = GatewayService()

    async def create_gateway(
        self,
        name: str,
        description: str = "",
        domains: List[str] = None,
        load_balancer_algorithm: str = "round_robin",
        **kwargs,
    ) -> Dict[str, Any]:
        """Create API gateway."""
        return await self._service.create_gateway(
            name=name,
            description=description,
            domains=domains or [],
            load_balancer_algorithm=load_balancer_algorithm,
            **kwargs,
        )

    async def get_gateway(self, gateway_id: str) -> Optional[Dict[str, Any]]:
        """Get gateway by ID."""
        return await self._service.get_gateway(gateway_id)

    async def update_gateway(self, gateway_id: str, **updates) -> Dict[str, Any]:
        """Update gateway."""
        return await self._service.update_gateway(gateway_id, **updates)

    async def delete_gateway(self, gateway_id: str) -> bool:
        """Delete gateway."""
        return await self._service.delete_gateway(gateway_id)

    async def create_route(
        self,
        gateway_id: str,
        path: str,
        upstream_service: str,
        upstream_url: str,
        methods: List[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create route."""
        return await self._service.create_route(
            gateway_id=gateway_id,
            path=path,
            upstream_service=upstream_service,
            upstream_url=upstream_url,
            methods=methods or ["GET"],
            **kwargs,
        )

    async def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get route by ID."""
        return await self._service.get_route(route_id)

    async def list_routes(self, gateway_id: str) -> List[Dict[str, Any]]:
        """List routes for gateway."""
        return await self._service.list_routes(gateway_id)

    async def update_route(self, route_id: str, **updates) -> Dict[str, Any]:
        """Update route."""
        return await self._service.update_route(route_id, **updates)

    async def delete_route(self, route_id: str) -> bool:
        """Delete route."""
        return await self._service.delete_route(route_id)

    async def apply_auth_policy(self, route_id: str, auth_policy_id: str) -> bool:
        """Apply authentication policy to route."""
        await self._service.update_route(route_id, auth_policy_id=auth_policy_id)
        return True

    async def apply_rate_limit_policy(
        self, route_id: str, rate_limit_policy_id: str
    ) -> bool:
        """Apply rate limiting policy to route."""
        await self._service.update_route(
            route_id, rate_limit_policy_id=rate_limit_policy_id
        )
        return True

    async def configure_load_balancer(
        self,
        gateway_id: str,
        algorithm: str = "round_robin",
        health_check_path: str = "/health",
        **kwargs,
    ) -> Dict[str, Any]:
        """Configure load balancer for gateway."""
        return await self._service.configure_load_balancer(
            gateway_id,
            algorithm=algorithm,
            health_check_path=health_check_path,
            **kwargs,
        )

    async def configure_cors(
        self,
        gateway_id: str,
        allowed_origins: List[str],
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        max_age: int = 86400,
    ) -> bool:
        """Configure CORS for gateway."""
        cors_config = {
            "cors_enabled": True,
            "cors_origins": allowed_origins,
            "cors_methods": allowed_methods or ["GET", "POST", "PUT", "DELETE"],
            "cors_headers": allowed_headers or ["Content-Type", "Authorization"],
            "cors_max_age": max_age,
        }

        await self._service.update_gateway(gateway_id, **cors_config)
        return True

    async def add_request_transformation(
        self, route_id: str, transformation_type: str, config: Dict[str, Any]
    ) -> bool:
        """Add request transformation to route."""
        transformation = {
            "request_transformations": [{"type": transformation_type, "config": config}]
        }

        await self._service.update_route(route_id, **transformation)
        return True

    async def add_response_transformation(
        self, route_id: str, transformation_type: str, config: Dict[str, Any]
    ) -> bool:
        """Add response transformation to route."""
        transformation = {
            "response_transformations": [
                {"type": transformation_type, "config": config}
            ]
        }

        await self._service.update_route(route_id, **transformation)
        return True

    async def register_upstream_service(
        self, name: str, url: str, weight: int = 100, **kwargs
    ) -> Dict[str, Any]:
        """Register upstream service."""
        return await self._service.register_upstream_service(
            name=name, url=url, weight=weight, **kwargs
        )
