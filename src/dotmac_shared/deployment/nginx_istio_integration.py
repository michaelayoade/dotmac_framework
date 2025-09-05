"""
NGINX + Istio Integration for DotMac Framework

Combines NGINX ingress (external traffic) with Istio service mesh (internal traffic)
for comprehensive traffic management in ISP management platform.
"""

import asyncio
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from .rollout_strategies import TrafficManager


@dataclass
class ServiceRoute:
    """Service routing configuration."""

    service_name: str
    external_host: str  # For NGINX ingress
    internal_host: str  # For Istio routing
    paths: list[str]
    rate_limit: Optional[str] = None
    ssl_enabled: bool = True
    auth_required: bool = False
    upstream_timeout: str = "30s"


@dataclass
class TrafficSplitRule:
    """Traffic split configuration for deployments."""

    service_name: str
    versions: dict[str, int]  # version -> weight percentage
    match_conditions: dict[str, str] = field(
        default_factory=dict
    )  # headers, user attributes


class NGINXIstioTrafficManager(TrafficManager):
    """Integrated NGINX + Istio traffic manager for comprehensive routing."""

    def __init__(
        self,
        namespace: str,
        nginx_config_path: str,
        signoz_endpoint: Optional[str] = None,
    ):
        self.namespace = namespace
        self.nginx_config_path = Path(nginx_config_path)
        self.signoz_endpoint = signoz_endpoint
        self.logger = logging.getLogger(__name__)

        # Track service routes for coordination
        self.service_routes: dict[str, ServiceRoute] = {}
        self.active_splits: dict[str, TrafficSplitRule] = {}

    def register_service_route(self, route: ServiceRoute):
        """Register a service route for NGINX + Istio coordination."""
        self.service_routes[route.service_name] = route
        self.logger.info(
            f"Registered route for {route.service_name}: {route.external_host} -> {route.internal_host}"
        )

    async def set_traffic_split(
        self, service_name: str, version_weights: dict[str, int]
    ):
        """Set traffic split using Istio (internal) while maintaining NGINX routing (external)."""
        if service_name not in self.service_routes:
            raise ValueError(f"Service route not registered: {service_name}")

        route = self.service_routes[service_name]

        try:
            # Apply Istio VirtualService for internal traffic splitting
            await self._apply_istio_traffic_split(service_name, version_weights)

            # Update NGINX upstream if needed (usually not required for canary)
            await self._update_nginx_upstream(route, version_weights)

            # Store active split
            self.active_splits[service_name] = TrafficSplitRule(
                service_name=service_name, versions=version_weights
            )

            self.logger.info(
                f"Applied traffic split for {service_name}: {version_weights}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to set traffic split for {service_name}: {str(e)}"
            )
            raise

    async def get_current_split(self, service_name: str) -> dict[str, int]:
        """Get current traffic split configuration."""
        if service_name in self.active_splits:
            return self.active_splits[service_name].versions
        return {}

    async def configure_dotmac_services(self):
        """Configure standard DotMac service routes."""

        # ISP Customer Portal
        self.register_service_route(
            ServiceRoute(
                service_name="dotmac-isp",
                external_host="portal.yourisp.com",
                internal_host="dotmac-isp-service.default.svc.cluster.local",
                paths=["/", "/api/customer", "/api/billing"],
                rate_limit="100r/m",  # 100 requests per minute per IP
                ssl_enabled=True,
                auth_required=False,  # Public portal
            )
        )

        # Management Interface
        self.register_service_route(
            ServiceRoute(
                service_name="dotmac-management",
                external_host="admin.yourisp.com",
                internal_host="dotmac-management-service.default.svc.cluster.local",
                paths=["/admin", "/api/management", "/api/monitoring"],
                rate_limit="500r/m",  # Higher limit for admin users
                ssl_enabled=True,
                auth_required=True,  # Admin authentication required
            )
        )

        # Partner/Reseller Portal
        self.register_service_route(
            ServiceRoute(
                service_name="dotmac-partners",
                external_host="partners.yourisp.com",
                internal_host="dotmac-management-service.default.svc.cluster.local",
                paths=["/partners", "/api/resellers"],
                rate_limit="200r/m",
                ssl_enabled=True,
                auth_required=True,
            )
        )

        # API Gateway (for integrations)
        self.register_service_route(
            ServiceRoute(
                service_name="dotmac-api",
                external_host="api.yourisp.com",
                internal_host="dotmac-gateway-service.default.svc.cluster.local",
                paths=["/v1", "/v2"],
                rate_limit="1000r/m",  # Higher for API integrations
                ssl_enabled=True,
                auth_required=True,
            )
        )

        # Generate configurations
        await self._generate_nginx_config()
        await self._generate_istio_configs()

        self.logger.info("Configured all DotMac service routes")

    async def _apply_istio_traffic_split(
        self, service_name: str, version_weights: dict[str, int]
    ):
        """Apply Istio VirtualService for traffic splitting."""

        virtual_service = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {
                "name": f"{service_name}-split",
                "namespace": self.namespace,
                "labels": {"app": service_name, "managed-by": "dotmac-deployment"},
            },
            "spec": {
                "hosts": [f"{service_name}-service"],
                "http": [
                    {
                        "match": [{"uri": {"prefix": "/"}}],
                        "route": [
                            {
                                "destination": {
                                    "host": f"{service_name}-service",
                                    "subset": version,
                                },
                                "weight": weight,
                                "headers": {
                                    "response": {
                                        "add": {
                                            "x-version": version,
                                            "x-canary-weight": str(weight),
                                        }
                                    }
                                },
                            }
                            for version, weight in version_weights.items()
                        ],
                        "timeout": "30s",
                        "retries": {"attempts": 3, "perTryTimeout": "10s"},
                    }
                ],
            },
        }

        # Apply DestinationRule for version subsets
        destination_rule = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "DestinationRule",
            "metadata": {
                "name": f"{service_name}-destination",
                "namespace": self.namespace,
            },
            "spec": {
                "host": f"{service_name}-service",
                "trafficPolicy": {
                    "circuitBreaker": {
                        "consecutiveErrors": 5,
                        "interval": "30s",
                        "baseEjectionTime": "30s",
                    }
                },
                "subsets": [
                    {"name": version, "labels": {"version": version}}
                    for version in version_weights.keys()
                ],
            },
        }

        # Apply both configurations
        await self._apply_k8s_manifest(virtual_service)
        await self._apply_k8s_manifest(destination_rule)

    async def _update_nginx_upstream(
        self, route: ServiceRoute, version_weights: dict[str, int]
    ):
        """Update NGINX upstream configuration if needed."""
        # For most canary deployments, NGINX doesn't need changes
        # since Istio handles the internal routing

        # Only update if we need to route external traffic differently
        # (e.g., for blue-green where we switch external endpoints)

        if len(version_weights) == 1 and list(version_weights.values())[0] == 100:
            # Full cutover - might need to update NGINX upstream
            new_version = list(version_weights.keys())[0]
            self.logger.info(
                f"Full cutover to version {new_version} - NGINX config unchanged (Istio handles routing)"
            )

    async def _generate_nginx_config(self):
        """Generate comprehensive NGINX configuration for all DotMac services."""

        config_sections = []

        # Rate limiting zones
        config_sections.append(
            """
# Rate limiting zones for different service tiers
http {
    limit_req_zone $binary_remote_addr zone=public:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=admin:10m rate=500r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=1000r/m;
    limit_req_zone $binary_remote_addr zone=partners:10m rate=200r/m;
"""
        )

        # Generate server blocks for each service
        for service_name, route in self.service_routes.items():
            server_block = f"""
    server {{
        listen 443 ssl http2;
        server_name {route.external_host};

        # SSL Configuration
        ssl_certificate /etc/ssl/certs/{route.external_host}.pem;
        ssl_certificate_key /etc/ssl/private/{route.external_host}.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

        # Security Headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # Rate Limiting
        limit_req zone={'public' if 'portal' in route.external_host else 'admin' if 'admin' in route.external_host else 'api' if 'api' in route.external_host else 'partners'} burst=20 nodelay;
"""

            # Add location blocks for each path
            for path in route.paths:
                server_block += f"""
        location {path} {{
            proxy_pass http://{route.internal_host.split('.')[0]}-upstream;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeout settings
            proxy_connect_timeout 5s;
            proxy_send_timeout {route.upstream_timeout};
            proxy_read_timeout {route.upstream_timeout};

            # Buffer settings
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;

            # Health check and error handling
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
"""

                if route.auth_required:
                    server_block += """
            # Authentication requirement
            auth_request /auth;
            auth_request_set $user $upstream_http_x_user;
            proxy_set_header X-User $user;
"""

                server_block += "        }\n"

            # Auth endpoint for protected routes
            if route.auth_required:
                server_block += """
        location = /auth {
            internal;
            proxy_pass http://dotmac-auth-service/validate;
            proxy_pass_request_body off;
            proxy_set_header Content-Length "";
            proxy_set_header X-Original-URI $request_uri;
        }
"""

            server_block += "    }\n"
            config_sections.append(server_block)

        # Upstream definitions (point to Kubernetes services)
        config_sections.append(
            """
    # Upstream definitions for DotMac services
    upstream dotmac-isp-upstream {
        server dotmac-isp-service.default.svc.cluster.local:80 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    upstream dotmac-management-upstream {
        server dotmac-management-service.default.svc.cluster.local:80 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    upstream dotmac-gateway-upstream {
        server dotmac-gateway-service.default.svc.cluster.local:80 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }
}
"""
        )

        # Write complete configuration
        complete_config = "\n".join(config_sections)

        config_file = self.nginx_config_path / "dotmac-services.conf"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            f.write(complete_config)

        self.logger.info(f"Generated NGINX configuration: {config_file}")

    async def _generate_istio_configs(self):
        """Generate Istio configurations for service mesh."""

        # Generate ServiceEntry for external dependencies
        service_entries = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "ServiceEntry",
            "metadata": {
                "name": "dotmac-external-services",
                "namespace": self.namespace,
            },
            "spec": {
                "hosts": [
                    "api.stripe.com",  # Payment processing
                    "api.twilio.com",  # SMS/Communications
                    "smtp.gmail.com",  # Email
                ],
                "ports": [{"number": 443, "name": "https", "protocol": "HTTPS"}],
                "location": "MESH_EXTERNAL",
                "resolution": "DNS",
            },
        }

        # Generate default DestinationRule for circuit breaking
        default_destination_rule = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "DestinationRule",
            "metadata": {
                "name": "dotmac-default-circuit-breaker",
                "namespace": self.namespace,
            },
            "spec": {
                "host": "*.default.svc.cluster.local",
                "trafficPolicy": {
                    "circuitBreaker": {
                        "consecutiveErrors": 5,
                        "interval": "30s",
                        "baseEjectionTime": "30s",
                        "maxEjectionPercent": 50,
                    },
                    "connectionPool": {
                        "tcp": {"maxConnections": 100},
                        "http": {
                            "http1MaxPendingRequests": 64,
                            "maxRequestsPerConnection": 2,
                        },
                    },
                },
            },
        }

        # Apply configurations
        await self._apply_k8s_manifest(service_entries)
        await self._apply_k8s_manifest(default_destination_rule)

    async def _apply_k8s_manifest(self, manifest: dict[str, Any]):
        """Apply Kubernetes manifest."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(manifest, f)
            manifest_file = f.name

        try:
            cmd = ["kubectl", "apply", "-f", manifest_file, "-n", self.namespace]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise Exception(f"kubectl failed: {stderr.decode()}")

            self.logger.debug(f"Applied manifest: {manifest['metadata']['name']}")

        finally:
            import os

            os.unlink(manifest_file)


# Factory for creating integrated traffic manager
class DotMacTrafficManagerFactory:
    """Factory for DotMac-specific traffic management configurations."""

    @staticmethod
    def create_integrated_manager(
        namespace: str = "default",
        nginx_config_path: str = "/etc/nginx/conf.d",
        signoz_endpoint: Optional[str] = None,
    ) -> NGINXIstioTrafficManager:
        """Create integrated NGINX + Istio traffic manager for DotMac."""

        manager = NGINXIstioTrafficManager(
            namespace, nginx_config_path, signoz_endpoint
        )
        return manager


# Convenience setup function
async def setup_dotmac_traffic_management(
    namespace: str = "default", nginx_config_path: str = "/etc/nginx/conf.d"
) -> NGINXIstioTrafficManager:
    """Setup complete DotMac traffic management with NGINX + Istio."""

    factory = DotMacTrafficManagerFactory()
    manager = factory.create_integrated_manager(namespace, nginx_config_path)

    # Configure all DotMac services
    await manager.configure_dotmac_services()

    return manager
