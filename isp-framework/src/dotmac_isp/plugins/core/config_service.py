"""Plugin Configuration Service - Database-driven plugin configuration management."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from jsonschema import validate, ValidationError

from .models import PluginRegistry, PluginConfiguration, PluginInstance, PluginEvent
from .base import PluginConfig, PluginCategory
from .exceptions import PluginConfigError, PluginError


class PluginConfigurationService:
    """Service for managing plugin configurations in database."""

    def __init__(self, db: Session, logger: Optional[logging.Logger] = None):
        """Initialize configuration service."""
        self.db = db
        self.logger = logger or logging.getLogger(__name__)

    def create_plugin_config(
        self,
        tenant_id: UUID,
        plugin_id: str,
        config_data: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> PluginConfiguration:
        """
        Create plugin configuration for a tenant.

        Args:
            tenant_id: Tenant ID
            plugin_id: Plugin ID
            config_data: Configuration data dictionary
            user_id: User creating the configuration

        Returns:
            PluginConfiguration instance
        """
        try:
            # Check if plugin exists in registry
            plugin_registry = (
                self.db.query(PluginRegistry)
                .filter(
                    and_(
                        PluginRegistry.tenant_id == tenant_id,
                        PluginRegistry.plugin_id == plugin_id,
                    )
                )
                .first()
            )

            if not plugin_registry:
                raise PluginConfigError(
                    f"Plugin {plugin_id} not found in registry for tenant {tenant_id}"
                )

            # Check if configuration already exists
            existing_config = (
                self.db.query(PluginConfiguration)
                .filter(
                    and_(
                        PluginConfiguration.tenant_id == tenant_id,
                        PluginConfiguration.plugin_id == plugin_id,
                    )
                )
                .first()
            )

            if existing_config:
                raise PluginConfigError(
                    f"Configuration already exists for plugin {plugin_id} in tenant {tenant_id}"
                )

            # Create configuration
            plugin_config = PluginConfiguration(
                tenant_id=tenant_id,
                plugin_id=plugin_id,
                plugin_registry_id=plugin_registry.id,
                config_data=config_data,
                configured_by=user_id,
            )

            # Validate configuration against schema
            if plugin_registry.config_schema:
                try:
                    validate(instance=config_data, schema=plugin_registry.config_schema)
                    plugin_config.mark_valid()
                except ValidationError as e:
                    plugin_config.mark_invalid([str(e)])
                    self.logger.warning(
                        f"Configuration validation failed for plugin {plugin_id}: {e}"
                    )

            self.db.add(plugin_config)
            self.db.commit()
            self.db.refresh(plugin_config)

            # Log event
            self._log_event(
                plugin_id=plugin_id,
                tenant_id=tenant_id,
                event_type="config_created",
                event_message=f"Configuration created for plugin {plugin_id}",
                user_id=user_id,
            )

            self.logger.info(
                f"Created configuration for plugin {plugin_id} in tenant {tenant_id}"
            )

            return plugin_config

        except Exception as e:
            self.db.rollback()
            self.logger.error(
                f"Error creating configuration for plugin {plugin_id}: {e}"
            )
            raise

    def get_plugin_config(
        self, tenant_id: UUID, plugin_id: str
    ) -> Optional[PluginConfiguration]:
        """
        Get plugin configuration for a tenant.

        Args:
            tenant_id: Tenant ID
            plugin_id: Plugin ID

        Returns:
            PluginConfiguration if found, None otherwise
        """
        return (
            self.db.query(PluginConfiguration)
            .filter(
                and_(
                    PluginConfiguration.tenant_id == tenant_id,
                    PluginConfiguration.plugin_id == plugin_id,
                    PluginConfiguration.is_deleted == False,
                )
            )
            .first()
        )

    def update_plugin_config(
        self,
        tenant_id: UUID,
        plugin_id: str,
        config_updates: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> Optional[PluginConfiguration]:
        """
        Update plugin configuration.

        Args:
            tenant_id: Tenant ID
            plugin_id: Plugin ID
            config_updates: Configuration updates
            user_id: User updating the configuration

        Returns:
            Updated PluginConfiguration or None if not found
        """
        try:
            plugin_config = self.get_plugin_config(tenant_id, plugin_id)
            if not plugin_config:
                return None

            # Get current config data
            current_data = plugin_config.config_data or {}

            # Merge updates
            updated_data = {**current_data, **config_updates}

            # Validate updated configuration
            plugin_registry = (
                self.db.query(PluginRegistry)
                .filter(PluginRegistry.id == plugin_config.plugin_registry_id)
                .first()
            )

            if plugin_registry and plugin_registry.config_schema:
                try:
                    validate(
                        instance=updated_data, schema=plugin_registry.config_schema
                    )
                    plugin_config.mark_valid()
                except ValidationError as e:
                    plugin_config.mark_invalid([str(e)])
                    self.logger.warning(
                        f"Configuration validation failed for plugin {plugin_id}: {e}"
                    )

            # Update configuration
            plugin_config.config_data = updated_data
            plugin_config.configured_by = user_id

            # Handle special updates
            for key, value in config_updates.items():
                if key == "enabled":
                    plugin_config.enabled = bool(value)
                elif key == "priority":
                    plugin_config.priority = int(value)
                elif key == "auto_start":
                    plugin_config.auto_start = bool(value)
                elif key == "restart_on_failure":
                    plugin_config.restart_on_failure = bool(value)
                elif key == "max_restart_attempts":
                    plugin_config.max_restart_attempts = int(value)
                elif key == "log_level":
                    plugin_config.log_level = str(value)
                elif key == "resource_limits":
                    plugin_config.resource_limits = value

            self.db.commit()
            self.db.refresh(plugin_config)

            # Log event
            self._log_event(
                plugin_id=plugin_id,
                tenant_id=tenant_id,
                event_type="config_updated",
                event_message=f"Configuration updated for plugin {plugin_id}",
                user_id=user_id,
                event_data={"updates": list(config_updates.keys())},
            )

            self.logger.info(
                f"Updated configuration for plugin {plugin_id} in tenant {tenant_id}"
            )

            return plugin_config

        except Exception as e:
            self.db.rollback()
            self.logger.error(
                f"Error updating configuration for plugin {plugin_id}: {e}"
            )
            raise

    def delete_plugin_config(
        self, tenant_id: UUID, plugin_id: str, user_id: Optional[UUID] = None
    ) -> bool:
        """
        Delete plugin configuration.

        Args:
            tenant_id: Tenant ID
            plugin_id: Plugin ID
            user_id: User deleting the configuration

        Returns:
            True if deleted, False if not found
        """
        try:
            plugin_config = self.get_plugin_config(tenant_id, plugin_id)
            if not plugin_config:
                return False

            # Soft delete
            plugin_config.soft_delete()

            self.db.commit()

            # Log event
            self._log_event(
                plugin_id=plugin_id,
                tenant_id=tenant_id,
                event_type="config_deleted",
                event_message=f"Configuration deleted for plugin {plugin_id}",
                user_id=user_id,
            )

            self.logger.info(
                f"Deleted configuration for plugin {plugin_id} in tenant {tenant_id}"
            )

            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(
                f"Error deleting configuration for plugin {plugin_id}: {e}"
            )
            raise

    def list_plugin_configs(
        self,
        tenant_id: UUID,
        enabled_only: bool = False,
        category: Optional[PluginCategory] = None,
    ) -> List[PluginConfiguration]:
        """
        List plugin configurations for a tenant.

        Args:
            tenant_id: Tenant ID
            enabled_only: Only return enabled configurations
            category: Filter by plugin category

        Returns:
            List of PluginConfiguration instances
        """
        query = self.db.query(PluginConfiguration).filter(
            and_(
                PluginConfiguration.tenant_id == tenant_id,
                PluginConfiguration.is_deleted == False,
            )
        )

        if enabled_only:
            query = query.filter(PluginConfiguration.enabled == True)

        if category:
            # Join with registry to filter by category
            query = query.join(PluginRegistry).filter(
                PluginRegistry.category == category.value
            )

        return query.order_by(PluginConfiguration.priority.desc()).all()

    def get_enabled_plugins(
        self, tenant_id: UUID, auto_start_only: bool = False
    ) -> List[PluginConfiguration]:
        """
        Get enabled plugin configurations for a tenant.

        Args:
            tenant_id: Tenant ID
            auto_start_only: Only return auto-start plugins

        Returns:
            List of enabled PluginConfiguration instances
        """
        query = self.db.query(PluginConfiguration).filter(
            and_(
                PluginConfiguration.tenant_id == tenant_id,
                PluginConfiguration.enabled == True,
                PluginConfiguration.is_valid == True,
                PluginConfiguration.is_deleted == False,
            )
        )

        if auto_start_only:
            query = query.filter(PluginConfiguration.auto_start == True)

        return query.order_by(PluginConfiguration.priority.desc()).all()

    def enable_plugin(
        self, tenant_id: UUID, plugin_id: str, user_id: Optional[UUID] = None
    ) -> bool:
        """
        Enable a plugin configuration.

        Args:
            tenant_id: Tenant ID
            plugin_id: Plugin ID
            user_id: User enabling the plugin

        Returns:
            True if enabled, False if not found
        """
        plugin_config = self.get_plugin_config(tenant_id, plugin_id)
        if not plugin_config:
            return False

        if not plugin_config.is_valid:
            raise PluginConfigError(
                f"Cannot enable plugin {plugin_id} - configuration is invalid"
            )

        plugin_config.enabled = True
        plugin_config.configured_by = user_id

        self.db.commit()

        # Log event
        self._log_event(
            plugin_id=plugin_id,
            tenant_id=tenant_id,
            event_type="plugin_enabled",
            event_message=f"Plugin {plugin_id} enabled",
            user_id=user_id,
        )

        return True

    def disable_plugin(
        self, tenant_id: UUID, plugin_id: str, user_id: Optional[UUID] = None
    ) -> bool:
        """
        Disable a plugin configuration.

        Args:
            tenant_id: Tenant ID
            plugin_id: Plugin ID
            user_id: User disabling the plugin

        Returns:
            True if disabled, False if not found
        """
        plugin_config = self.get_plugin_config(tenant_id, plugin_id)
        if not plugin_config:
            return False

        plugin_config.enabled = False
        plugin_config.configured_by = user_id

        self.db.commit()

        # Log event
        self._log_event(
            plugin_id=plugin_id,
            tenant_id=tenant_id,
            event_type="plugin_disabled",
            event_message=f"Plugin {plugin_id} disabled",
            user_id=user_id,
        )

        return True

    def validate_plugin_config(
        self,
        plugin_id: str,
        config_data: Dict[str, Any],
        tenant_id: Optional[UUID] = None,
    ) -> List[str]:
        """
        Validate plugin configuration against schema.

        Args:
            plugin_id: Plugin ID
            config_data: Configuration data to validate
            tenant_id: Optional tenant ID for tenant-specific validation

        Returns:
            List of validation errors (empty if valid)
        """
        try:
            # Get plugin registry entry
            query = self.db.query(PluginRegistry).filter(
                PluginRegistry.plugin_id == plugin_id
            )

            if tenant_id:
                query = query.filter(PluginRegistry.tenant_id == tenant_id)

            plugin_registry = query.first()

            if not plugin_registry:
                return [f"Plugin {plugin_id} not found in registry"]

            if not plugin_registry.config_schema:
                return []  # No schema to validate against

            # Validate against JSON schema
            validate(instance=config_data, schema=plugin_registry.config_schema)

            return []  # No errors

        except ValidationError as e:
            return [str(e)]
        except Exception as e:
            return [f"Validation error: {str(e)}"]

    def get_plugin_default_config(
        self, tenant_id: UUID, plugin_id: str
    ) -> Dict[str, Any]:
        """
        Get default configuration for a plugin.

        Args:
            tenant_id: Tenant ID
            plugin_id: Plugin ID

        Returns:
            Default configuration dictionary
        """
        plugin_registry = (
            self.db.query(PluginRegistry)
            .filter(
                and_(
                    PluginRegistry.tenant_id == tenant_id,
                    PluginRegistry.plugin_id == plugin_id,
                )
            )
            .first()
        )

        if plugin_registry and plugin_registry.default_config:
            return plugin_registry.default_config

        # Return minimal default configuration
        return {
            "enabled": True,
            "priority": 100,
            "auto_start": False,
            "restart_on_failure": True,
            "max_restart_attempts": 3,
            "log_level": "INFO",
        }

    def bulk_update_configs(
        self,
        tenant_id: UUID,
        updates: Dict[str, Dict[str, Any]],
        user_id: Optional[UUID] = None,
    ) -> Dict[str, bool]:
        """
        Bulk update plugin configurations.

        Args:
            tenant_id: Tenant ID
            updates: Dictionary mapping plugin_id to configuration updates
            user_id: User performing updates

        Returns:
            Dictionary mapping plugin_id to success status
        """
        results = {}

        for plugin_id, config_updates in updates.items():
            try:
                result = self.update_plugin_config(
                    tenant_id, plugin_id, config_updates, user_id
                )
                results[plugin_id] = result is not None
            except Exception as e:
                self.logger.error(f"Error updating config for plugin {plugin_id}: {e}")
                results[plugin_id] = False

        return results

    def get_configuration_statistics(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get configuration statistics for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Statistics dictionary
        """
        # Count configurations by status
        total_configs = (
            self.db.query(PluginConfiguration)
            .filter(
                and_(
                    PluginConfiguration.tenant_id == tenant_id,
                    PluginConfiguration.is_deleted == False,
                )
            )
            .count()
        )

        enabled_configs = (
            self.db.query(PluginConfiguration)
            .filter(
                and_(
                    PluginConfiguration.tenant_id == tenant_id,
                    PluginConfiguration.enabled == True,
                    PluginConfiguration.is_deleted == False,
                )
            )
            .count()
        )

        invalid_configs = (
            self.db.query(PluginConfiguration)
            .filter(
                and_(
                    PluginConfiguration.tenant_id == tenant_id,
                    PluginConfiguration.is_valid == False,
                    PluginConfiguration.is_deleted == False,
                )
            )
            .count()
        )

        auto_start_configs = (
            self.db.query(PluginConfiguration)
            .filter(
                and_(
                    PluginConfiguration.tenant_id == tenant_id,
                    PluginConfiguration.auto_start == True,
                    PluginConfiguration.enabled == True,
                    PluginConfiguration.is_deleted == False,
                )
            )
            .count()
        )

        return {
            "total_configurations": total_configs,
            "enabled_configurations": enabled_configs,
            "disabled_configurations": total_configs - enabled_configs,
            "invalid_configurations": invalid_configs,
            "auto_start_configurations": auto_start_configs,
        }

    def _log_event(
        self,
        plugin_id: str,
        tenant_id: UUID,
        event_type: str,
        event_message: str,
        user_id: Optional[UUID] = None,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a plugin event."""
        try:
            event = PluginEvent(
                tenant_id=tenant_id,
                plugin_id=plugin_id,
                event_type=event_type,
                event_message=event_message,
                event_data=event_data,
                user_id=user_id,
            )

            self.db.add(event)
            self.db.commit()

        except Exception as e:
            self.logger.error(f"Error logging plugin event: {e}")
            # Don't fail the main operation if event logging fails
