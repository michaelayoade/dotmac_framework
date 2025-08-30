"""Template engine for configuration generation using Jinja2."""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jinja2
import yaml
from jinja2 import BaseLoader, Environment, FileSystemLoader, Template
from jinja2.sandbox import SandboxedEnvironment

from ..schemas.tenant_schemas import SubscriptionPlan, TenantInfo

logger = logging.getLogger(__name__)


class SecureTemplateLoader(BaseLoader):
    """Secure template loader with path validation."""

    def __init__(self, template_dirs: List[str]):
        self.template_dirs = [Path(d).resolve() for d in template_dirs]

    def get_source(self, environment: Environment, template: str) -> tuple:
        """Load template source with security checks."""
        # Validate template name
        if ".." in template or template.startswith("/"):
            raise jinja2.TemplateNotFound(template)

        for template_dir in self.template_dirs:
            template_path = template_dir / template

            # Ensure template is within allowed directory
            try:
                template_path.resolve().relative_to(template_dir)
            except ValueError:
                continue

            if template_path.exists() and template_path.is_file():
                with open(template_path, "r", encoding="utf-8") as f:
                    source = f.read()

                mtime = template_path.stat().st_mtime
                return (
                    source,
                    str(template_path),
                    lambda: mtime == template_path.stat().st_mtime,
                )

        raise jinja2.TemplateNotFound(template)


class TemplateEngine:
    """
    Secure template engine for configuration generation.

    Uses Jinja2 with sandboxing for secure template processing,
    supports caching, and provides configuration-specific filters.
    """

    def __init__(
        self,
        template_dirs: Optional[List[str]] = None,
        enable_caching: bool = True,
        cache_size: int = 100,
        enable_sandbox: bool = True,
        auto_reload: bool = False,
    ):
        """Initialize the template engine."""
        self.template_dirs = template_dirs or [
            str(Path(__file__).parent.parent / "templates"),
            "/etc/dotmac/config/templates",
            os.path.expanduser("~/.dotmac/config/templates"),
        ]

        # Filter to existing directories
        self.template_dirs = [d for d in self.template_dirs if os.path.exists(d)]

        if not self.template_dirs:
            # Create default template directory
            default_dir = str(Path(__file__).parent.parent / "templates")
            os.makedirs(default_dir, exist_ok=True)
            self.template_dirs = [default_dir]

        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self.enable_sandbox = enable_sandbox

        # Initialize Jinja2 environment
        if enable_sandbox:
            self.env = SandboxedEnvironment(
                loader=SecureTemplateLoader(self.template_dirs),
                auto_reload=auto_reload,
                cache_size=cache_size if enable_caching else 0,
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dirs),
                auto_reload=auto_reload,
                cache_size=cache_size if enable_caching else 0,
                trim_blocks=True,
                lstrip_blocks=True,
            )

        # Add custom filters and functions
        self._setup_custom_filters()
        self._setup_custom_functions()

        logger.info(
            f"Template engine initialized with directories: {self.template_dirs}"
        )

    def _setup_custom_filters(self):
        """Setup custom Jinja2 filters for configuration processing."""

        def to_yaml(value, indent=2):
            """Convert value to YAML format."""
            return yaml.dump(value, default_flow_style=False, indent=indent)

        def to_env_var(value):
            """Convert string to environment variable format."""
            return str(value).upper().replace("-", "_").replace(" ", "_")

        def plan_feature_enabled(
            plan: str, feature: str, plan_features: Dict[str, List[str]] = None
        ):
            """Check if a feature is enabled for a subscription plan."""
            if not plan_features:
                return False
            return feature in plan_features.get(plan, [])

        def format_database_url(config: Dict[str, Any]):
            """Format database URL from configuration."""
            db_type = config.get("type", "postgresql")
            username = config.get("username", "user")
            password = config.get("password", "password")
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            name = config.get("name", "database")

            return f"{db_type}://{username}:{password}@{host}:{port}/{name}"

        def format_redis_url(config: Dict[str, Any]):
            """Format Redis URL from configuration."""
            host = config.get("host", "localhost")
            port = config.get("port", 6379)
            database = config.get("database", 0)
            password = config.get("password")

            if password:
                return f"redis://:{password}@{host}:{port}/{database}"
            return f"redis://{host}:{port}/{database}"

        def scale_by_plan(
            base_value: Union[int, float],
            plan: str,
            multipliers: Dict[str, float] = None,
        ):
            """Scale a value based on subscription plan."""
            if not multipliers:
                multipliers = {"basic": 1.0, "premium": 2.0, "enterprise": 4.0}

            multiplier = multipliers.get(plan.lower(), 1.0)
            if isinstance(base_value, int):
                return int(base_value * multiplier)
            return base_value * multiplier

        def resource_limit(
            plan: str, resource: str, limits: Dict[str, Dict[str, Any]] = None
        ):
            """Get resource limit for a plan."""
            if not limits:
                limits = {
                    "basic": {"cpu": 1, "memory": "512MB", "storage": "10GB"},
                    "premium": {"cpu": 2, "memory": "2GB", "storage": "50GB"},
                    "enterprise": {"cpu": 4, "memory": "8GB", "storage": "200GB"},
                }

            return limits.get(plan.lower(), {}).get(resource, "unlimited")

        # Register filters
        self.env.filters["to_yaml"] = to_yaml
        self.env.filters["to_env_var"] = to_env_var
        self.env.filters["plan_feature_enabled"] = plan_feature_enabled
        self.env.filters["format_database_url"] = format_database_url
        self.env.filters["format_redis_url"] = format_redis_url
        self.env.filters["scale_by_plan"] = scale_by_plan
        self.env.filters["resource_limit"] = resource_limit

    def _setup_custom_functions(self):
        """Setup custom Jinja2 global functions."""

        def now():
            """Get current timestamp."""
            return datetime.now().isoformat()

        def env_or_default(env_var: str, default: Any = None):
            """Get environment variable or default value."""
            return os.getenv(env_var, default)

        def generate_secret_placeholder(secret_name: str):
            """Generate placeholder for secret injection."""
            return f"${{SECRET:{secret_name}}}"

        def conditional_config(
            condition: bool, true_config: Any, false_config: Any = None
        ):
            """Conditionally include configuration."""
            return true_config if condition else (false_config or {})

        def merge_configs(*configs):
            """Deep merge multiple configuration dictionaries."""
            result = {}
            for config in configs:
                if isinstance(config, dict):
                    result.update(config)
            return result

        # Register global functions
        self.env.globals["now"] = now
        self.env.globals["env_or_default"] = env_or_default
        self.env.globals["generate_secret_placeholder"] = generate_secret_placeholder
        self.env.globals["conditional_config"] = conditional_config
        self.env.globals["merge_configs"] = merge_configs

    async def render_template(
        self, template_name: str, context: Dict[str, Any], output_format: str = "yaml"
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file
            context: Template context variables
            output_format: Output format (yaml, json, text)

        Returns:
            Rendered template as string
        """
        try:
            template = self.env.get_template(template_name)

            # Add output format to context
            context["output_format"] = output_format

            # Render template
            result = await asyncio.get_event_loop().run_in_executor(
                None, template.render, context
            )

            logger.debug(f"Successfully rendered template {template_name}")
            return result

        except jinja2.TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise
        except jinja2.TemplateSyntaxError as e:
            logger.error(f"Template syntax error in {template_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise

    async def render_string(
        self,
        template_string: str,
        context: Dict[str, Any],
        template_name: str = "inline",
    ) -> str:
        """
        Render a template from string.

        Args:
            template_string: Template content as string
            context: Template context variables
            template_name: Name for error reporting

        Returns:
            Rendered template as string
        """
        try:
            template = self.env.from_string(template_string, template_class=Template)

            result = await asyncio.get_event_loop().run_in_executor(
                None, template.render, context
            )

            logger.debug(f"Successfully rendered inline template {template_name}")
            return result

        except jinja2.TemplateSyntaxError as e:
            logger.error(f"Template syntax error in {template_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to render inline template {template_name}: {e}")
            raise

    async def render_isp_config(
        self,
        tenant_info: TenantInfo,
        environment: str,
        custom_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render ISP configuration using the default template.

        Args:
            tenant_info: Tenant information
            environment: Target environment
            custom_context: Additional context variables

        Returns:
            Rendered ISP configuration
        """
        context = {
            "tenant": tenant_info.to_config_context(),
            "environment": environment,
            "timestamp": datetime.now().isoformat(),
            "plan_features": self._get_plan_features(),
        }

        if custom_context:
            context.update(custom_context)

        return await self.render_template("isp_config.yaml.j2", context)

    async def render_database_config(
        self,
        tenant_info: TenantInfo,
        environment: str,
        database_overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render database configuration template.

        Args:
            tenant_info: Tenant information
            environment: Target environment
            database_overrides: Database configuration overrides

        Returns:
            Rendered database configuration
        """
        context = {
            "tenant": tenant_info.to_config_context(),
            "environment": environment,
            "database_overrides": database_overrides or {},
        }

        return await self.render_template("database_config.j2", context)

    async def render_feature_config(
        self,
        tenant_info: TenantInfo,
        enabled_features: List[str],
        feature_configs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render feature configuration template.

        Args:
            tenant_info: Tenant information
            enabled_features: List of enabled features
            feature_configs: Feature-specific configurations

        Returns:
            Rendered feature configuration
        """
        context = {
            "tenant": tenant_info.to_config_context(),
            "enabled_features": enabled_features,
            "feature_configs": feature_configs or {},
            "plan_features": self._get_plan_features(),
        }

        return await self.render_template("feature_config.j2", context)

    async def validate_template(self, template_name: str) -> Dict[str, Any]:
        """
        Validate a template for syntax errors.

        Args:
            template_name: Name of the template to validate

        Returns:
            Validation result with any errors
        """
        try:
            template = self.env.get_template(template_name)

            # Try to parse without rendering
            self.env.parse(template.source)

            return {"valid": True, "template_name": template_name, "errors": []}

        except jinja2.TemplateNotFound:
            return {
                "valid": False,
                "template_name": template_name,
                "errors": [f"Template not found: {template_name}"],
            }
        except jinja2.TemplateSyntaxError as e:
            return {
                "valid": False,
                "template_name": template_name,
                "errors": [f"Syntax error on line {e.lineno}: {e.message}"],
            }
        except Exception as e:
            return {
                "valid": False,
                "template_name": template_name,
                "errors": [f"Validation error: {str(e)}"],
            }

    async def list_templates(self) -> List[str]:
        """
        List all available templates.

        Returns:
            List of template names
        """
        templates = []

        for template_dir in self.template_dirs:
            if os.path.exists(template_dir):
                for root, dirs, files in os.walk(template_dir):
                    for file in files:
                        if file.endswith((".j2", ".jinja", ".jinja2")):
                            rel_path = os.path.relpath(
                                os.path.join(root, file), template_dir
                            )
                            templates.append(rel_path)

        return sorted(list(set(templates)))

    def _get_plan_features(self) -> Dict[str, List[str]]:
        """Get feature mappings for subscription plans."""
        return {
            "basic": [
                "basic_analytics",
                "email_support",
                "standard_api",
                "basic_integration",
            ],
            "premium": [
                "basic_analytics",
                "advanced_analytics",
                "email_support",
                "phone_support",
                "premium_api",
                "standard_integration",
                "premium_integration",
                "custom_branding",
            ],
            "enterprise": [
                "basic_analytics",
                "advanced_analytics",
                "email_support",
                "phone_support",
                "priority_support",
                "enterprise_api",
                "standard_integration",
                "premium_integration",
                "enterprise_integration",
                "custom_branding",
                "white_label",
                "sso",
                "advanced_security",
                "custom_domains",
            ],
        }

    async def create_template(
        self,
        template_name: str,
        template_content: str,
        template_dir: Optional[str] = None,
    ) -> bool:
        """
        Create a new template file.

        Args:
            template_name: Name of the template
            template_content: Template content
            template_dir: Directory to create template in (uses first directory if None)

        Returns:
            True if created successfully
        """
        try:
            target_dir = template_dir or self.template_dirs[0]
            template_path = Path(target_dir) / template_name

            # Ensure directory exists
            template_path.parent.mkdir(parents=True, exist_ok=True)

            # Write template content
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(template_content)

            logger.info(f"Created template {template_name} in {target_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to create template {template_name}: {e}")
            return False

    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a template.

        Args:
            template_name: Name of the template

        Returns:
            Template information or None if not found
        """
        try:
            template = self.env.get_template(template_name)

            # Get template file info
            for template_dir in self.template_dirs:
                template_path = Path(template_dir) / template_name
                if template_path.exists():
                    stat = template_path.stat()
                    return {
                        "name": template_name,
                        "path": str(template_path),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "directory": template_dir,
                    }

            return None

        except jinja2.TemplateNotFound:
            return None
