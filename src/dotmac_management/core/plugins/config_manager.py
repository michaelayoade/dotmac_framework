"""
Plugin Configuration Manager
Handles plugin configuration loading, validation, and management
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from dotmac.application import standard_exception_handler
from dotmac_shared.core.logging import get_logger

from .base import PluginError, PluginType

logger = get_logger(__name__)


@dataclass
class PluginConfig:
    """Plugin configuration data structure."""

    name: str
    plugin_type: PluginType
    enabled: bool = True
    config: dict[str, Any] = None
    priority: int = 0
    auto_load: bool = True
    dependencies: list[str] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.dependencies is None:
            self.dependencies = []


class PluginConfigManager:
    """
    Manages plugin configuration from various sources.
    Supports environment variables, JSON/YAML files, and runtime configuration.
    """

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or os.getenv("PLUGIN_CONFIG_DIR", "./config/plugins"))
        self.configs: dict[str, PluginConfig] = {}
        self.env_prefix = "DOTMAC_PLUGIN_"

    @standard_exception_handler
    async def load_configurations(self) -> bool:
        """Load plugin configurations from all sources."""
        try:
            # Load from configuration files
            await self._load_from_files()

            # Override with environment variables
            await self._load_from_environment()

            # Validate all configurations
            await self._validate_configurations()

            logger.info(f"✅ Loaded {len(self.configs)} plugin configurations")
            return True

        except PluginError:
            logger.exception("Failed to load plugin configurations due to validation error")
            return False

    async def _load_from_files(self):
        """Load plugin configurations from JSON/YAML files."""
        if not self.config_dir.exists():
            logger.warning(f"Plugin config directory not found: {self.config_dir}")
            return

        config_files = (
            list(self.config_dir.glob("*.json"))
            + list(self.config_dir.glob("*.yaml"))
            + list(self.config_dir.glob("*.yml"))
        )

        for config_file in config_files:
            try:
                with open(config_file) as f:
                    if config_file.suffix == ".json":
                        data = json.load(f)
                    else:
                        data = yaml.safe_load(f)

                await self._process_config_data(data, str(config_file))

            except (OSError, json.JSONDecodeError, yaml.YAMLError, PluginError, ValueError, TypeError):
                logger.exception(f"Failed to load config file {config_file}")

    async def _load_from_environment(self):
        """Load plugin configurations from environment variables."""
        # Environment variable format: DOTMAC_PLUGIN_{PLUGIN_NAME}_{CONFIG_KEY}=value
        env_configs = {}

        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Parse: DOTMAC_PLUGIN_COOLIFY_DEPLOYMENT_BASE_URL -> coolify_deployment.base_url
                parts = key[len(self.env_prefix) :].lower().split("_")
                if len(parts) >= 2:
                    plugin_name = "_".join(parts[:-1])
                    config_key = parts[-1]

                    if plugin_name not in env_configs:
                        env_configs[plugin_name] = {}

                    # Try to parse JSON values, fall back to string
                    try:
                        parsed_value = json.loads(value)
                    except json.JSONDecodeError:
                        parsed_value = value

                    env_configs[plugin_name][config_key] = parsed_value

        # Apply environment configurations
        for plugin_name, config in env_configs.items():
            if plugin_name in self.configs:
                # Update existing configuration
                self.configs[plugin_name].config.update(config)
                logger.info(f"Updated plugin config from environment: {plugin_name}")
            else:
                # Create new configuration from environment
                plugin_config = PluginConfig(
                    name=plugin_name,
                    plugin_type=PluginType.INFRASTRUCTURE_PROVIDER,  # Default type
                    config=config,
                )
                self.configs[plugin_name] = plugin_config
                logger.info(f"Created plugin config from environment: {plugin_name}")

    async def _process_config_data(self, data: dict[str, Any], source: str):
        """Process configuration data from a source."""
        if "plugins" in data:
            # Multiple plugins in one file
            for plugin_data in data["plugins"]:
                await self._create_plugin_config(plugin_data, source)
        else:
            # Single plugin configuration
            await self._create_plugin_config(data, source)

    async def _create_plugin_config(self, data: dict[str, Any], source: str):
        """Create plugin configuration from data."""
        try:
            plugin_name = data.get("name")
            if not plugin_name:
                logger.error(f"Plugin configuration missing 'name' in {source}")
                return

            plugin_type_str = data.get("plugin_type", "infrastructure_provider")

            # Convert string to PluginType enum
            try:
                plugin_type = PluginType(plugin_type_str)
            except ValueError:
                logger.error(f"Invalid plugin type '{plugin_type_str}' for plugin {plugin_name}")
                plugin_type = PluginType.INFRASTRUCTURE_PROVIDER

            config = PluginConfig(
                name=plugin_name,
                plugin_type=plugin_type,
                enabled=data.get("enabled", True),
                config=data.get("config", {}),
                priority=data.get("priority", 0),
                auto_load=data.get("auto_load", True),
                dependencies=data.get("dependencies", []),
            )

            self.configs[plugin_name] = config
            logger.info(f"Loaded plugin configuration: {plugin_name} from {source}")

        except (PluginError, ValueError, TypeError):
            logger.exception(f"Failed to process plugin configuration in {source}")

    async def _validate_configurations(self):
        """Validate all loaded plugin configurations."""
        for name, config in self.configs.items():
            try:
                # Basic validation
                if not config.name:
                    raise PluginError(f"Plugin name is required: {name}")

                if not isinstance(config.config, dict):
                    raise PluginError(f"Plugin config must be a dictionary: {name}")

                # Type-specific validation
                await self._validate_plugin_type_config(config)

            except (PluginError, TypeError, ValueError):
                logger.exception(f"Configuration validation failed for plugin {name}")
                # Disable invalid configurations
                config.enabled = False

    async def _validate_plugin_type_config(self, config: PluginConfig):
        """Validate plugin configuration based on its type."""
        if config.plugin_type == PluginType.DEPLOYMENT_PROVIDER:
            # Validate deployment provider configuration
            required_fields = ["base_url", "api_token"]
            for field in required_fields:
                if field not in config.config:
                    logger.warning(f"Deployment provider {config.name} missing recommended field: {field}")

        elif config.plugin_type == PluginType.DNS_PROVIDER:
            # Validate DNS provider configuration
            if "base_domain" not in config.config:
                logger.warning(f"DNS provider {config.name} missing base_domain configuration")

    def get_plugin_config(self, plugin_name: str) -> Optional[PluginConfig]:
        """Get configuration for a specific plugin."""
        return self.configs.get(plugin_name)

    def get_configs_by_type(self, plugin_type: PluginType) -> list[PluginConfig]:
        """Get all configurations for a specific plugin type."""
        return [config for config in self.configs.values() if config.plugin_type == plugin_type and config.enabled]

    def get_enabled_configs(self) -> list[PluginConfig]:
        """Get all enabled plugin configurations."""
        return [config for config in self.configs.values() if config.enabled]

    def get_auto_load_configs(self) -> list[PluginConfig]:
        """Get all configurations that should be auto-loaded."""
        return [config for config in self.configs.values() if config.enabled and config.auto_load]

    @standard_exception_handler
    async def add_runtime_config(self, plugin_config: PluginConfig) -> bool:
        """Add a plugin configuration at runtime."""
        try:
            # Validate the configuration
            await self._validate_plugin_type_config(plugin_config)

            # Add to configurations
            self.configs[plugin_config.name] = plugin_config

            logger.info(f"✅ Added runtime plugin configuration: {plugin_config.name}")
            return True

        except (PluginError, TypeError):
            logger.exception("Failed to add runtime plugin configuration")
            return False

    @standard_exception_handler
    async def update_plugin_config(self, plugin_name: str, config_updates: dict[str, Any]) -> bool:
        """Update configuration for an existing plugin."""
        try:
            if plugin_name not in self.configs:
                raise PluginError(f"Plugin configuration not found: {plugin_name}")

            # Update configuration
            self.configs[plugin_name].config.update(config_updates)

            # Revalidate
            await self._validate_plugin_type_config(self.configs[plugin_name])

            logger.info(f"✅ Updated plugin configuration: {plugin_name}")
            return True

        except (PluginError, TypeError):
            logger.exception(f"Failed to update plugin configuration {plugin_name}")
            return False

    @standard_exception_handler
    async def remove_plugin_config(self, plugin_name: str) -> bool:
        """Remove a plugin configuration."""
        try:
            if plugin_name not in self.configs:
                logger.warning(f"Plugin configuration not found for removal: {plugin_name}")
                return False

            del self.configs[plugin_name]
            logger.info(f"✅ Removed plugin configuration: {plugin_name}")
            return True

        except KeyError:
            logger.exception(f"Unexpected KeyError removing plugin configuration {plugin_name}")
            return False

    def export_configurations(self) -> dict[str, Any]:
        """Export all configurations to a dictionary format."""
        return {"plugins": [asdict(config) for config in self.configs.values()]}

    @standard_exception_handler
    async def save_configurations(self, file_path: Optional[str] = None) -> bool:
        """Save current configurations to a file."""
        try:
            if file_path is None:
                file_path = self.config_dir / "generated_config.json"

            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Export and save
            config_data = self.export_configurations()

            with open(file_path, "w") as f:
                json.dump(config_data, f, indent=2, default=str)

            logger.info(f"✅ Saved plugin configurations to: {file_path}")
            return True

        except OSError:
            logger.exception("Failed to save plugin configurations")
            return False

    def list_configurations(self) -> dict[str, dict[str, Any]]:
        """List all loaded configurations with their status."""
        return {
            name: {
                "plugin_type": config.plugin_type.value,
                "enabled": config.enabled,
                "auto_load": config.auto_load,
                "priority": config.priority,
                "has_config": bool(config.config),
                "dependencies": config.dependencies,
            }
            for name, config in self.configs.items()
        }


# Default configuration for built-in plugins
DEFAULT_PLUGIN_CONFIGS = {
    "coolify_deployment": {
        "name": "coolify_deployment",
        "plugin_type": "deployment_provider",
        "enabled": True,
        "auto_load": True,
        "priority": 10,
        "config": {"base_url": "http://localhost:8000", "project_id": "default"},
    },
    "standard_dns": {
        "name": "standard_dns",
        "plugin_type": "dns_provider",
        "enabled": True,
        "auto_load": True,
        "priority": 10,
        "config": {"timeout": 10},
    },
}
