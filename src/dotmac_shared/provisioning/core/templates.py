"""
Container template management for the DotMac Provisioning Service.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import yaml
from pydantic import BaseModel, Field

from .exceptions import TemplateError
from .models import (
    InfrastructureType,
    ISPConfig,
    ResourceRequirements,
)


class ContainerTemplate(BaseModel):
    """Container deployment template."""

    name: str = Field(..., description="Template name")
    version: str = Field(default="1.0.0", description="Template version")
    infrastructure_type: InfrastructureType = Field(..., description="Target infrastructure")
    description: Optional[str] = Field(default=None)

    # Template content
    template_content: dict[str, Any] = Field(..., description="Template specification")
    default_values: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = Field(default_factory=list)

    # Validation
    required_variables: list[str] = Field(default_factory=list)
    optional_variables: list[str] = Field(default_factory=list)

    def render(self, variables: dict[str, Any]) -> dict[str, Any]:
        """Render template with provided variables."""
        # Check required variables
        missing_vars = [var for var in self.required_variables if var not in variables]
        if missing_vars:
            raise TemplateError(
                f"Missing required template variables: {missing_vars}",
                template_name=self.name,
                template_version=self.version,
            )

        # Merge with defaults
        render_vars = {**self.default_values, **variables}

        # Render template
        return self._render_recursive(self.template_content, render_vars)

    def _render_recursive(self, obj: Any, variables: dict[str, Any]) -> Any:
        """Recursively render template variables."""
        if isinstance(obj, dict):
            return {key: self._render_recursive(value, variables) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._render_recursive(item, variables) for item in obj]
        elif isinstance(obj, str):
            return self._render_string(obj, variables)
        else:
            return obj

    def _render_string(self, template_str: str, variables: dict[str, Any]) -> str:
        """Render string template with variables."""
        try:
            # Simple variable substitution: {{variable_name}}
            result = template_str
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                result = result.replace(placeholder, str(value))
            return result
        except Exception as e:
            raise TemplateError(
                f"Failed to render template string: {template_str}: {e}",
                template_name=self.name,
            ) from e


class TemplateManager:
    """Manages container deployment templates."""

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or Path(__file__).parent.parent / "templates"
        self.templates: dict[str, ContainerTemplate] = {}
        self.loaded = False

    async def load_templates(self) -> None:
        """Load all templates from template directory."""
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)
            await self._create_default_templates()

        # Load existing templates
        for template_file in self.template_dir.glob("*.yaml"):
            try:
                await self._load_template_file(template_file)
            except Exception as e:
                raise TemplateError(f"Failed to load template {template_file}: {e}") from e

        # Create default templates if none exist
        if not self.templates:
            await self._create_default_templates()

        self.loaded = True

    async def _load_template_file(self, template_file: Path) -> None:
        """Load a single template file."""
        with open(template_file) as f:
            template_data = yaml.safe_load(f)

        template = ContainerTemplate(**template_data)
        template_key = f"{template.name}:{template.infrastructure_type.value}"
        self.templates[template_key] = template

    async def get_template(self, name: str, infrastructure_type: InfrastructureType) -> ContainerTemplate:
        """Get template by name and infrastructure type."""
        if not self.loaded:
            await self.load_templates()

        template_key = f"{name}:{infrastructure_type.value}"
        if template_key not in self.templates:
            raise TemplateError(f"Template not found: {template_key}")

        return self.templates[template_key]

    async def render_template(
        self,
        template_name: str,
        infrastructure_type: InfrastructureType,
        isp_id: UUID,
        config: ISPConfig,
        resources: ResourceRequirements,
    ) -> dict[str, Any]:
        """Render a template with ISP configuration."""
        template = await self.get_template(template_name, infrastructure_type)

        # Prepare template variables
        variables = self._prepare_template_variables(isp_id, config, resources, infrastructure_type)

        # Render template
        return template.render(variables)

    def _prepare_template_variables(
        self,
        isp_id: UUID,
        config: ISPConfig,
        resources: ResourceRequirements,
        infrastructure_type: InfrastructureType,
    ) -> dict[str, Any]:
        """Prepare variables for template rendering."""

        # Base variables
        variables = {
            "isp_id": str(isp_id),
            "tenant_name": config.tenant_name,
            "display_name": config.display_name,
            "plan_type": config.plan_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Resource variables
        if infrastructure_type == InfrastructureType.KUBERNETES:
            variables.update(
                {
                    "cpu_limit": resources.to_kubernetes_limits()["cpu"],
                    "memory_limit": resources.to_kubernetes_limits()["memory"],
                    "storage_limit": resources.to_kubernetes_limits()["ephemeral-storage"],
                    "namespace": f"tenant-{config.tenant_name}",
                    "container_name": f"isp-framework-{config.tenant_name}",
                    "service_name": f"{config.tenant_name}-service",
                    "ingress_name": f"{config.tenant_name}-ingress",
                }
            )
        elif infrastructure_type == InfrastructureType.DOCKER:
            variables.update(
                {
                    "cpu_limit": resources.cpu_cores,
                    "memory_limit": f"{resources.memory_gb}g",
                    "container_name": f"isp-framework-{config.tenant_name}",
                    "network_name": f"tenant-{config.tenant_name}-network",
                }
            )

        # Network variables
        network = config.network_config
        variables.update(
            {
                "domain": network.domain or f"{network.subdomain}.dotmac.app",
                "subdomain": network.subdomain,
                "ssl_enabled": network.ssl_enabled,
                "external_port": (list(network.port_mapping.values())[0] if network.port_mapping else 80),
            }
        )

        # Database variables
        db_config = config.database_config
        variables.update(
            {
                "database_enabled": db_config.create_dedicated_db,
                "database_size": db_config.database_size,
                "database_name": f"tenant_{config.tenant_name}_db",
                "database_user": f"tenant_{config.tenant_name}_user",
                "connection_pool_size": db_config.connection_pool_size,
            }
        )

        # Feature flags
        features = config.feature_flags
        if features:
            variables.update(
                {
                    "customer_portal_enabled": features.customer_portal,
                    "technician_portal_enabled": features.technician_portal,
                    "admin_portal_enabled": features.admin_portal,
                    "billing_enabled": features.billing_system,
                    "notifications_enabled": features.notification_system,
                    "analytics_enabled": features.analytics_dashboard,
                    "webhooks_enabled": features.api_webhooks,
                    "bulk_ops_enabled": features.bulk_operations,
                }
            )

        # Environment variables
        variables.update(
            {
                "environment_vars": config.environment_variables,
                "secrets": config.secrets,  # These will be handled securely
            }
        )

        return variables

    async def _create_default_templates(self) -> None:
        """Create default container templates."""

        # Kubernetes template
        k8s_template = await self._create_kubernetes_template()
        await self._save_template(k8s_template)

        # Docker template
        docker_template = await self._create_docker_template()
        await self._save_template(docker_template)

    async def _create_kubernetes_template(self) -> ContainerTemplate:
        """Create default Kubernetes deployment template."""

        template_content = [
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    "name": "{{namespace}}",
                    "labels": {
                        "tenant": "{{tenant_name}}",
                        "isp-id": "{{isp_id}}",
                        "plan": "{{plan_type}}",
                    },
                },
                "spec": {},
            },
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "{{container_name}}",
                    "namespace": "{{namespace}}",
                    "labels": {"app": "isp-framework", "tenant": "{{tenant_name}}"},
                },
                "spec": {
                    "replicas": 1,
                    "selector": {"matchLabels": {"app": "isp-framework", "tenant": "{{tenant_name}}"}},
                    "template": {
                        "metadata": {"labels": {"app": "isp-framework", "tenant": "{{tenant_name}}"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "isp-framework",
                                    "image": "registry.dotmac.app/isp-framework:latest",
                                    "ports": [{"containerPort": 8000}],
                                    "resources": {
                                        "limits": {
                                            "cpu": "{{cpu_limit}}",
                                            "memory": "{{memory_limit}}",
                                            "ephemeral-storage": "{{storage_limit}}",
                                        },
                                        "requests": {
                                            "cpu": "{{cpu_limit}}",
                                            "memory": "{{memory_limit}}",
                                        },
                                    },
                                    "env": [
                                        {"name": "TENANT_ID", "value": "{{tenant_name}}"},
                                        {"name": "ISP_ID", "value": "{{isp_id}}"},
                                        {"name": "PLAN_TYPE", "value": "{{plan_type}}"},
                                        {
                                            "name": "DATABASE_URL",
                                            "value": "postgresql://{{database_user}}:{{database_password}}@{{database_host}}/{{database_name}}",
                                        },
                                        {
                                            "name": "REDIS_URL",
                                            "value": "redis://{{redis_host}}:6379/0",
                                        },
                                    ],
                                    "livenessProbe": {
                                        "httpGet": {"path": "/health/live", "port": 8000},
                                        "initialDelaySeconds": 30,
                                        "periodSeconds": 10,
                                    },
                                    "readinessProbe": {
                                        "httpGet": {"path": "/health/ready", "port": 8000},
                                        "initialDelaySeconds": 5,
                                        "periodSeconds": 5,
                                    },
                                }
                            ]
                        },
                    },
                },
            },
        ]

        return ContainerTemplate(
            name="isp-framework",
            version="1.0.0",
            infrastructure_type=InfrastructureType.KUBERNETES,
            description="Default ISP Framework Kubernetes deployment",
            template_content=template_content,
            required_variables=[
                "namespace",
                "container_name",
                "tenant_name",
                "isp_id",
                "cpu_limit",
                "memory_limit",
                "storage_limit",
                "database_user",
                "database_password",
                "database_host",
                "database_name",
                "redis_host",
            ],
            optional_variables=["plan_type", "replicas", "image_tag"],
            tags=["kubernetes", "production", "default"],
        )

    async def _create_docker_template(self) -> ContainerTemplate:
        """Create default Docker Compose template."""

        template_content = {
            "version": "3.8",
            "services": {
                "isp-framework": {
                    "image": "registry.dotmac.app/isp-framework:latest",
                    "container_name": "{{container_name}}",
                    "restart": "unless-stopped",
                    "ports": ["{{external_port}}:8000"],
                    "environment": {
                        "TENANT_ID": "{{tenant_name}}",
                        "ISP_ID": "{{isp_id}}",
                        "PLAN_TYPE": "{{plan_type}}",
                        "DATABASE_URL": "postgresql://{{database_user}}:{{database_password}}@postgres/{{database_name}}",
                        "REDIS_URL": "redis://redis:6379/0",
                    },
                    "depends_on": ["postgres", "redis"],
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "60s",
                    },
                    "deploy": {
                        "resources": {
                            "limits": {
                                "cpus": "{{cpu_limit}}",
                                "memory": "{{memory_limit}}",
                            }
                        }
                    },
                    "networks": ["{{network_name}}"],
                },
                "postgres": {
                    "image": "postgres:15-alpine",
                    "container_name": "{{container_name}}-postgres",
                    "restart": "unless-stopped",
                    "environment": {
                        "POSTGRES_DB": "{{database_name}}",
                        "POSTGRES_USER": "{{database_user}}",
                        "POSTGRES_PASSWORD": "{{database_password}}",
                    },
                    "volumes": ["postgres_data:/var/lib/postgresql/data"],
                    "networks": ["{{network_name}}"],
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "container_name": "{{container_name}}-redis",
                    "restart": "unless-stopped",
                    "volumes": ["redis_data:/data"],
                    "networks": ["{{network_name}}"],
                },
            },
            "volumes": {"postgres_data": {}, "redis_data": {}},
            "networks": {"{{network_name}}": {"driver": "bridge"}},
        }

        return ContainerTemplate(
            name="isp-framework",
            version="1.0.0",
            infrastructure_type=InfrastructureType.DOCKER_COMPOSE,
            description="Default ISP Framework Docker Compose deployment",
            template_content=template_content,
            required_variables=[
                "container_name",
                "tenant_name",
                "isp_id",
                "cpu_limit",
                "memory_limit",
                "external_port",
                "database_user",
                "database_password",
                "database_name",
                "network_name",
            ],
            optional_variables=["plan_type", "image_tag"],
            tags=["docker", "development", "default"],
        )

    async def _save_template(self, template: ContainerTemplate) -> None:
        """Save template to file and memory."""
        # Save to memory
        template_key = f"{template.name}:{template.infrastructure_type.value}"
        self.templates[template_key] = template

        # Save to file
        filename = f"{template.name}-{template.infrastructure_type.value}.yaml"
        filepath = self.template_dir / filename

        template_data = template.model_dump()
        with open(filepath, "w") as f:
            yaml.dump(template_data, f, default_flow_style=False)

    async def list_templates(self) -> list[ContainerTemplate]:
        """List all available templates."""
        if not self.loaded:
            await self.load_templates()
        return list(self.templates.values())

    async def validate_template(self, template: ContainerTemplate) -> bool:
        """Validate template structure and content."""
        try:
            # Test render with sample data
            sample_vars = {var: f"test_{var}" for var in template.required_variables}
            template.render(sample_vars)
            return True
        except Exception:
            return False


# Global template manager instance
template_manager = TemplateManager()
