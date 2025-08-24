"""Service for managing communication channel plugins."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .channel_plugins import channel_registry
from .channel_plugins.base import BaseChannelPlugin, ChannelConfig, ChannelMessage
from .models_v2 import RegisteredChannel, ChannelConfiguration
from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    DuplicateEntityError,
)

logger = logging.getLogger(__name__)


class ChannelPluginService:
    """Service for managing channel plugins and their configurations."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id
        self.registry = channel_registry

    async def register_available_plugins(self) -> int:
        """Register all available plugins in the database."""
        registered_count = 0

        for channel_id in self.registry.get_available_channels():
            channel_info = self.registry.get_channel_info(channel_id)
            if not channel_info:
                continue

            # Check if already registered for this tenant
            existing = (
                self.db.query(RegisteredChannel)
                .filter(
                    RegisteredChannel.tenant_id == self.tenant_id,
                    RegisteredChannel.channel_id == channel_id,
                )
                .first()
            )

            if existing:
                # Update existing registration
                existing.channel_name = channel_info["channel_name"]
                existing.capabilities = channel_info["capabilities"]
                existing.configuration_schema = {
                    "required_fields": channel_info["required_config"]
                }
            else:
                # Create new registration
                new_channel = RegisteredChannel(
                    tenant_id=self.tenant_id,
                    channel_id=channel_id,
                    channel_name=channel_info["channel_name"],
                    plugin_class=f"dotmac_isp.modules.omnichannel.channel_plugins.{channel_id}_plugin",
                    capabilities=channel_info["capabilities"],
                    configuration_schema={
                        "required_fields": channel_info["required_config"]
                    },
                )
                self.db.add(new_channel)
                registered_count += 1

        try:
            self.db.commit()
            logger.info(
                f"Registered {registered_count} new channel plugins for tenant {self.tenant_id}"
            )
            return registered_count
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to register plugins: {e}")
            raise DuplicateEntityError(
                "Plugin registration failed due to duplicate entry"
            )

    def get_available_channels(self) -> List[Dict[str, Any]]:
        """Get all registered channels for the tenant."""
        channels = (
            self.db.query(RegisteredChannel)
            .filter(
                RegisteredChannel.tenant_id == self.tenant_id,
                RegisteredChannel.is_active == True,
            )
            .all()
        )

        result = []
        for channel in channels:
            # Get configuration status
            config = (
                self.db.query(ChannelConfiguration)
                .filter(
                    ChannelConfiguration.tenant_id == self.tenant_id,
                    ChannelConfiguration.channel_id == channel.id,
                )
                .first()
            )

            result.append(
                {
                    "id": str(channel.id),
                    "channel_id": channel.channel_id,
                    "channel_name": channel.channel_name,
                    "capabilities": channel.capabilities,
                    "is_configured": config is not None and config.is_enabled,
                    "health_status": (
                        config.health_status if config else "not_configured"
                    ),
                    "configuration_schema": channel.configuration_schema,
                }
            )

        return result

    async def configure_channel(
        self, channel_id: str, config_data: Dict[str, Any]
    ) -> bool:
        """Configure a channel with the provided settings."""
        # Get registered channel
        channel = (
            self.db.query(RegisteredChannel)
            .filter(
                RegisteredChannel.tenant_id == self.tenant_id,
                RegisteredChannel.channel_id == channel_id,
            )
            .first()
        )

        if not channel:
            raise EntityNotFoundError(f"Channel {channel_id} not registered")

        # Validate configuration against schema
        required_fields = channel.configuration_schema.get("required_fields", [])
        missing_fields = [
            field for field in required_fields if field not in config_data
        ]
        if missing_fields:
            raise ValidationError(
                f"Missing required configuration fields: {missing_fields}"
            )

        try:
            # Create channel config
            channel_config = ChannelConfig(**config_data)

            # Test plugin initialization
            success = self.registry.configure_channel(channel_id, channel_config)
            if not success:
                raise ValidationError(
                    f"Failed to configure plugin for channel {channel_id}"
                )

            # Test plugin initialization
            init_success = await self.registry.initialize_channel(channel_id)
            if not init_success:
                raise ValidationError(
                    f"Failed to initialize plugin for channel {channel_id}"
                )

            # Save configuration to database
            existing_config = (
                self.db.query(ChannelConfiguration)
                .filter(
                    ChannelConfiguration.tenant_id == self.tenant_id,
                    ChannelConfiguration.channel_id == channel.id,
                )
                .first()
            )

            if existing_config:
                existing_config.configuration = config_data
                existing_config.is_enabled = True
                existing_config.health_status = "healthy"
                existing_config.error_message = None
            else:
                new_config = ChannelConfiguration(
                    tenant_id=self.tenant_id,
                    channel_id=channel.id,
                    configuration=config_data,
                    is_enabled=True,
                    health_status="healthy",
                )
                self.db.add(new_config)

            self.db.commit()
            logger.info(
                f"Successfully configured channel {channel_id} for tenant {self.tenant_id}"
            )
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to configure channel {channel_id}: {e}")

            # Update health status in database if config exists
            existing_config = (
                self.db.query(ChannelConfiguration)
                .filter(
                    ChannelConfiguration.tenant_id == self.tenant_id,
                    ChannelConfiguration.channel_id == channel.id,
                )
                .first()
            )

            if existing_config:
                existing_config.health_status = "unhealthy"
                existing_config.error_message = str(e)
                self.db.commit()

            raise ValidationError(f"Channel configuration failed: {e}")

    async def send_message(
        self, channel_id: str, message: ChannelMessage
    ) -> Dict[str, Any]:
        """Send a message through a specific channel."""
        # Verify channel is configured and healthy
        channel = (
            self.db.query(RegisteredChannel)
            .filter(
                RegisteredChannel.tenant_id == self.tenant_id,
                RegisteredChannel.channel_id == channel_id,
            )
            .first()
        )

        if not channel:
            raise EntityNotFoundError(f"Channel {channel_id} not found")

        config = (
            self.db.query(ChannelConfiguration)
            .filter(
                ChannelConfiguration.tenant_id == self.tenant_id,
                ChannelConfiguration.channel_id == channel.id,
                ChannelConfiguration.is_enabled == True,
            )
            .first()
        )

        if not config:
            raise ValidationError(f"Channel {channel_id} is not configured or disabled")

        if config.health_status != "healthy":
            raise ValidationError(
                f"Channel {channel_id} is unhealthy: {config.error_message}"
            )

        # Send message through registry
        result = await self.registry.send_message(channel_id, message)

        if result is None:
            raise ValidationError(f"Failed to send message through {channel_id}")

        return result

    async def process_webhook(
        self, channel_id: str, webhook_data: Dict[str, Any]
    ) -> Optional[ChannelMessage]:
        """Process incoming webhook data from a channel."""
        # Verify channel is configured
        channel = (
            self.db.query(RegisteredChannel)
            .filter(
                RegisteredChannel.tenant_id == self.tenant_id,
                RegisteredChannel.channel_id == channel_id,
            )
            .first()
        )

        if not channel:
            logger.warning(f"Received webhook for unconfigured channel: {channel_id}")
            return None

        config = (
            self.db.query(ChannelConfiguration)
            .filter(
                ChannelConfiguration.tenant_id == self.tenant_id,
                ChannelConfiguration.channel_id == channel.id,
                ChannelConfiguration.is_enabled == True,
            )
            .first()
        )

        if not config:
            logger.warning(f"Received webhook for disabled channel: {channel_id}")
            return None

        # Process webhook through registry
        return await self.registry.process_webhook(channel_id, webhook_data)

    async def health_check_all_channels(self) -> Dict[str, Dict[str, Any]]:
        """Perform health checks on all configured channels."""
        results = {}

        configs = (
            self.db.query(ChannelConfiguration)
            .filter(
                ChannelConfiguration.tenant_id == self.tenant_id,
                ChannelConfiguration.is_enabled == True,
            )
            .all()
        )

        for config in configs:
            channel = config.channel
            channel_id = channel.channel_id

            try:
                is_healthy = self.registry.is_channel_healthy(channel_id)

                results[channel_id] = {
                    "channel_name": channel.channel_name,
                    "is_healthy": is_healthy,
                    "last_check": config.last_health_check,
                    "error_message": config.error_message,
                }

                # Update database with health check results
                config.health_status = "healthy" if is_healthy else "unhealthy"
                config.last_health_check = datetime.utcnow()

            except Exception as e:
                results[channel_id] = {
                    "channel_name": channel.channel_name,
                    "is_healthy": False,
                    "error_message": str(e),
                }

                config.health_status = "unhealthy"
                config.error_message = str(e)
                config.last_health_check = datetime.utcnow()

        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update health check results: {e}")
            self.db.rollback()

        return results

    def disable_channel(self, channel_id: str) -> bool:
        """Disable a channel configuration."""
        config = (
            self.db.query(ChannelConfiguration)
            .join(RegisteredChannel)
            .filter(
                ChannelConfiguration.tenant_id == self.tenant_id,
                RegisteredChannel.channel_id == channel_id,
            )
            .first()
        )

        if not config:
            raise EntityNotFoundError(
                f"Channel configuration for {channel_id} not found"
            )

        config.is_enabled = False

        try:
            self.db.commit()
            logger.info(f"Disabled channel {channel_id} for tenant {self.tenant_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to disable channel {channel_id}: {e}")
            return False

    def get_channel_capabilities(self, channel_id: str) -> List[str]:
        """Get capabilities of a specific channel."""
        channel = (
            self.db.query(RegisteredChannel)
            .filter(
                RegisteredChannel.tenant_id == self.tenant_id,
                RegisteredChannel.channel_id == channel_id,
            )
            .first()
        )

        if not channel:
            raise EntityNotFoundError(f"Channel {channel_id} not found")

        return channel.capabilities or []

    def get_channels_by_capability(self, capability: str) -> List[str]:
        """Get all channels that support a specific capability."""
        channels = (
            self.db.query(RegisteredChannel)
            .filter(
                RegisteredChannel.tenant_id == self.tenant_id,
                RegisteredChannel.is_active == True,
                RegisteredChannel.capabilities.contains([capability]),
            )
            .all()
        )

        return [channel.channel_id for channel in channels]
