"""
DotMac Plugin System Integration for Omnichannel Service

Properly integrates omnichannel service with the DotMac plugin system,
using the official plugin architecture and communication adapters.

Author: DotMac Framework Team
License: MIT
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from dotmac_shared.plugins.adapters.communication import (
    BulkMessageResult,
    CommunicationPlugin,
    Message,
    MessagePriority,
    MessageResult,
    MessageStatus,
)
from dotmac_shared.plugins.core.exceptions import PluginError

# Import DotMac plugin system
from dotmac_shared.plugins.core.manager import PluginManager
from dotmac_shared.plugins.core.plugin_base import PluginMetadata
from dotmac_shared.plugins.core.registry import PluginRegistry

from ..core.interaction_manager import InteractionModel
from ..models.enums import ChannelType
from ..models.enums import MessageStatus as OmnichannelMessageStatus

logger = logging.getLogger(__name__)


class OmnichannelCommunicationPlugin(CommunicationPlugin):
    """
    Base class for omnichannel communication plugins

    Extends the DotMac CommunicationPlugin with omnichannel-specific functionality
    like interaction tracking, routing context, and agent assignment.
    """

    def __init__(self, metadata: PluginMetadata, config: Dict[str, Any]):
        super().__init__(metadata, config)

        # Omnichannel-specific properties
        self.channel_type: ChannelType = ChannelType(
            metadata.category_data.get("channel_type", "webhook")
        )
        self.supports_interactions = config.get("supports_interactions", True)
        self.supports_agent_assignment = config.get("supports_agent_assignment", False)
        self.max_concurrent_messages = config.get("max_concurrent_messages", 100)

        # Rate limiting and capacity
        self.current_messages = 0
        self.rate_limit_per_minute = config.get("rate_limit_per_minute", 60)
        self.last_rate_reset = datetime.utcnow()
        self.message_count_this_minute = 0

    async def send_message_with_context(
        self,
        message: Message,
        interaction_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> MessageResult:
        """
        Send message with omnichannel context

        Args:
            message: The message to send
            interaction_id: Associated interaction ID
            agent_id: Sending agent ID
            tenant_id: Tenant context

        Returns:
            MessageResult with omnichannel metadata
        """
        try:
            # Check rate limits
            if not await self._check_rate_limit():
                return MessageResult(
                    success=False,
                    status=MessageStatus.FAILED,
                    error_message="Rate limit exceeded",
                    metadata={
                        "rate_limited": True,
                        "rate_limit_per_minute": self.rate_limit_per_minute,
                    },
                )

            # Check capacity
            if self.current_messages >= self.max_concurrent_messages:
                return MessageResult(
                    success=False,
                    status=MessageStatus.FAILED,
                    error_message="Channel at capacity",
                    metadata={
                        "at_capacity": True,
                        "max_concurrent": self.max_concurrent_messages,
                        "current_messages": self.current_messages,
                    },
                )

            # Add omnichannel metadata to message
            if not message.metadata:
                message.metadata = {}

            message.metadata.update(
                {
                    "interaction_id": str(interaction_id) if interaction_id else None,
                    "agent_id": str(agent_id) if agent_id else None,
                    "tenant_id": str(tenant_id) if tenant_id else None,
                    "channel_type": self.channel_type.value,
                    "sent_via_omnichannel": True,
                }
            )

            # Increment message counter
            self.current_messages += 1
            self.message_count_this_minute += 1

            try:
                # Send message via plugin implementation
                result = await self.send_message(message)

                # Add omnichannel metadata to result
                if not result.metadata:
                    result.metadata = {}

                result.metadata.update(
                    {
                        "interaction_id": (
                            str(interaction_id) if interaction_id else None
                        ),
                        "agent_id": str(agent_id) if agent_id else None,
                        "tenant_id": str(tenant_id) if tenant_id else None,
                        "channel_type": self.channel_type.value,
                    }
                )

                return result

            finally:
                # Decrement message counter
                self.current_messages = max(0, self.current_messages - 1)

        except Exception as e:
            logger.error(f"Failed to send message with context: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                metadata={"exception_type": type(e).__name__},
            )

    async def get_channel_capabilities(self) -> Dict[str, Any]:
        """Get channel-specific capabilities"""
        capabilities = await self.get_capabilities()

        return {
            "channel_type": self.channel_type.value,
            "supports_interactions": self.supports_interactions,
            "supports_agent_assignment": self.supports_agent_assignment,
            "max_concurrent_messages": self.max_concurrent_messages,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "plugin_capabilities": capabilities,
        }

    async def _check_rate_limit(self) -> bool:
        """Check if message sending is within rate limits"""
        now = datetime.utcnow()

        # Reset counter if minute has passed
        if (now - self.last_rate_reset).total_seconds() >= 60:
            self.message_count_this_minute = 0
            self.last_rate_reset = now

        return self.message_count_this_minute < self.rate_limit_per_minute


class OmnichannelPluginManager:
    """
    Plugin manager specifically for omnichannel communication plugins

    Integrates with the DotMac plugin system to discover, load, and manage
    communication plugins for omnichannel service.
    """

    def __init__(self, tenant_id: UUID):
        """Initialize omnichannel plugin manager"""
        self.tenant_id = tenant_id
        self.plugin_manager = PluginManager()
        self.plugin_registry = PluginRegistry()

        # Omnichannel plugin tracking
        self.communication_plugins: Dict[str, OmnichannelCommunicationPlugin] = {}
        self.plugins_by_channel: Dict[ChannelType, List[str]] = {}
        self.is_initialized = False

    async def initialize(self) -> bool:
        """Initialize the plugin manager"""
        try:
            # Initialize core plugin manager
            await self.plugin_manager.initialize()

            # Load communication plugins
            await self._load_communication_plugins()

            self.is_initialized = True
            logger.info(
                f"Omnichannel plugin manager initialized for tenant {self.tenant_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize omnichannel plugin manager: {e}")
            return False

    async def send_message(
        self,
        channel_type: ChannelType,
        recipient: str,
        content: str,
        subject: Optional[str] = None,
        interaction_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageResult:
        """
        Send message through appropriate channel plugin

        Args:
            channel_type: Type of communication channel
            recipient: Message recipient
            content: Message content
            subject: Message subject (if applicable)
            interaction_id: Associated interaction ID
            agent_id: Sending agent ID
            priority: Message priority
            metadata: Additional metadata

        Returns:
            MessageResult from the channel plugin
        """
        try:
            if not self.is_initialized:
                raise RuntimeError("Plugin manager not initialized")

            # Get available plugins for channel
            plugin_ids = self.plugins_by_channel.get(channel_type, [])
            if not plugin_ids:
                return MessageResult(
                    success=False,
                    status=MessageStatus.FAILED,
                    error_message=f"No plugins available for channel {channel_type.value}",
                    metadata={"channel_type": channel_type.value},
                )

            # Use first available plugin (could implement load balancing here)
            plugin_id = plugin_ids[0]
            plugin = self.communication_plugins.get(plugin_id)

            if not plugin:
                return MessageResult(
                    success=False,
                    status=MessageStatus.FAILED,
                    error_message=f"Plugin {plugin_id} not found",
                    metadata={"plugin_id": plugin_id},
                )

            # Create message object
            message = Message(
                recipient=recipient,
                content=content,
                subject=subject,
                message_type="text",  # Default to text
                priority=priority,
                metadata=metadata or {},
            )

            # Send with omnichannel context
            return await plugin.send_message_with_context(
                message=message,
                interaction_id=interaction_id,
                agent_id=agent_id,
                tenant_id=self.tenant_id,
            )

        except Exception as e:
            logger.error(f"Failed to send message via plugin system: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                metadata={"exception_type": type(e).__name__},
            )

    async def get_available_channels(self) -> Dict[ChannelType, List[Dict[str, Any]]]:
        """Get all available communication channels"""
        try:
            channels = {}

            for channel_type, plugin_ids in self.plugins_by_channel.items():
                channel_info = []

                for plugin_id in plugin_ids:
                    plugin = self.communication_plugins.get(plugin_id)
                    if plugin:
                        capabilities = await plugin.get_channel_capabilities()
                        channel_info.append(
                            {
                                "plugin_id": plugin_id,
                                "plugin_name": plugin.metadata.name,
                                "version": plugin.metadata.version,
                                "capabilities": capabilities,
                                "enabled": plugin.enabled,
                                "health_status": await plugin.health_check(),
                            }
                        )

                if channel_info:
                    channels[channel_type] = channel_info

            return channels

        except Exception as e:
            logger.error(f"Failed to get available channels: {e}")
            return {}

    async def get_plugin_status(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a specific plugin"""
        try:
            plugin = self.communication_plugins.get(plugin_id)
            if not plugin:
                return None

            capabilities = await plugin.get_channel_capabilities()
            health = await plugin.health_check()

            return {
                "plugin_id": plugin_id,
                "plugin_name": plugin.metadata.name,
                "version": plugin.metadata.version,
                "channel_type": plugin.channel_type.value,
                "enabled": plugin.enabled,
                "capabilities": capabilities,
                "health_status": health,
                "current_messages": plugin.current_messages,
                "max_concurrent": plugin.max_concurrent_messages,
                "rate_limit": plugin.rate_limit_per_minute,
                "message_count_this_minute": plugin.message_count_this_minute,
            }

        except Exception as e:
            logger.error(f"Failed to get plugin status for {plugin_id}: {e}")
            return None

    async def reload_plugins(self) -> bool:
        """Reload all communication plugins"""
        try:
            # Shutdown existing plugins
            for plugin in self.communication_plugins.values():
                try:
                    await plugin.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down plugin: {e}")

            # Clear registries
            self.communication_plugins.clear()
            self.plugins_by_channel.clear()

            # Reload plugins
            await self._load_communication_plugins()

            logger.info("Successfully reloaded omnichannel communication plugins")
            return True

        except Exception as e:
            logger.error(f"Failed to reload plugins: {e}")
            return False

    # Private helper methods

    async def _load_communication_plugins(self):
        """Load communication plugins from the plugin system"""
        try:
            # Get all communication plugins from the registry
            plugins = await self.plugin_registry.get_plugins_by_category(
                "communication"
            )

            for plugin_id, plugin_instance in plugins.items():
                try:
                    # Ensure it's a communication plugin
                    if isinstance(plugin_instance, CommunicationPlugin):
                        # Wrap as omnichannel plugin if needed
                        if not isinstance(
                            plugin_instance, OmnichannelCommunicationPlugin
                        ):
                            plugin_instance = self._wrap_as_omnichannel_plugin(
                                plugin_instance
                            )

                        # Initialize plugin
                        await plugin_instance.initialize()

                        # Register plugin
                        self.communication_plugins[plugin_id] = plugin_instance

                        # Map to channel type
                        channel_type = plugin_instance.channel_type
                        if channel_type not in self.plugins_by_channel:
                            self.plugins_by_channel[channel_type] = []
                        self.plugins_by_channel[channel_type].append(plugin_id)

                        logger.info(
                            f"Loaded communication plugin: {plugin_id} ({channel_type.value})"
                        )

                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_id}: {e}")
                    continue

            logger.info(
                f"Loaded {len(self.communication_plugins)} communication plugins"
            )

        except Exception as e:
            logger.error(f"Failed to load communication plugins: {e}")
            raise

    def _wrap_as_omnichannel_plugin(
        self, plugin: CommunicationPlugin
    ) -> OmnichannelCommunicationPlugin:
        """Wrap a standard communication plugin as an omnichannel plugin"""

        class WrappedOmnichannelPlugin(OmnichannelCommunicationPlugin):
            """Wrapper for standard communication plugins"""

            def __init__(self, wrapped_plugin: CommunicationPlugin):
                # Initialize with wrapped plugin's metadata and config
                super().__init__(wrapped_plugin.metadata, wrapped_plugin.config)
                self.wrapped_plugin = wrapped_plugin

            async def send_message(self, message: Message) -> MessageResult:
                """Delegate to wrapped plugin"""
                return await self.wrapped_plugin.send_message(message)

            async def send_bulk_messages(
                self, messages: List[Message]
            ) -> BulkMessageResult:
                """Delegate to wrapped plugin if supported"""
                if hasattr(self.wrapped_plugin, "send_bulk_messages"):
                    return await self.wrapped_plugin.send_bulk_messages(messages)
                else:
                    # Fallback to individual sends
                    results = []
                    successful = 0
                    failed = 0

                    for message in messages:
                        result = await self.send_message(message)
                        results.append(result)

                        if result.success:
                            successful += 1
                        else:
                            failed += 1

                    return BulkMessageResult(
                        total_messages=len(messages),
                        successful=successful,
                        failed=failed,
                        results=results,
                    )

            async def get_capabilities(self) -> Dict[str, Any]:
                """Delegate to wrapped plugin"""
                return await self.wrapped_plugin.get_capabilities()

            async def health_check(self) -> Dict[str, Any]:
                """Delegate to wrapped plugin"""
                return await self.wrapped_plugin.health_check()

        return WrappedOmnichannelPlugin(plugin)

    async def shutdown(self):
        """Shutdown all plugins"""
        try:
            for plugin in self.communication_plugins.values():
                try:
                    await plugin.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down plugin: {e}")

            await self.plugin_manager.shutdown()
            logger.info("Omnichannel plugin manager shut down")

        except Exception as e:
            logger.error(f"Error during plugin manager shutdown: {e}")


# Helper functions for converting between formats


def omnichannel_to_plugin_message_status(
    status: OmnichannelMessageStatus,
) -> MessageStatus:
    """Convert omnichannel message status to plugin message status"""
    status_mapping = {
        OmnichannelMessageStatus.PENDING: MessageStatus.PENDING,
        OmnichannelMessageStatus.QUEUED: MessageStatus.PENDING,
        OmnichannelMessageStatus.SENT: MessageStatus.SENT,
        OmnichannelMessageStatus.DELIVERED: MessageStatus.DELIVERED,
        OmnichannelMessageStatus.FAILED: MessageStatus.FAILED,
        OmnichannelMessageStatus.BOUNCED: MessageStatus.BOUNCED,
        OmnichannelMessageStatus.READ: MessageStatus.DELIVERED,  # Map read to delivered
        OmnichannelMessageStatus.SPAM: MessageStatus.FAILED,
    }

    return status_mapping.get(status, MessageStatus.FAILED)


def plugin_to_omnichannel_message_status(
    status: MessageStatus,
) -> OmnichannelMessageStatus:
    """Convert plugin message status to omnichannel message status"""
    status_mapping = {
        MessageStatus.PENDING: OmnichannelMessageStatus.PENDING,
        MessageStatus.SENT: OmnichannelMessageStatus.SENT,
        MessageStatus.DELIVERED: OmnichannelMessageStatus.DELIVERED,
        MessageStatus.FAILED: OmnichannelMessageStatus.FAILED,
        MessageStatus.BOUNCED: OmnichannelMessageStatus.BOUNCED,
    }

    return status_mapping.get(status, OmnichannelMessageStatus.FAILED)
