"""
Communication domain adapter for the plugin system.

Provides specialized interfaces and utilities for communication plugins
like email, SMS, push notifications, and webhooks.
"""

import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from ..core.exceptions import PluginError
from ..core.plugin_base import BasePlugin


class MessagePriority(Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(Enum):
    """Message delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


@dataclass
class Message:
    """Universal message structure."""

    recipient: str
    content: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    message_type: str = "text"
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MessageResult:
    """Message sending result."""

    success: bool
    message_id: Optional[str] = None
    status: MessageStatus = MessageStatus.PENDING
    error_message: Optional[str] = None
    provider_response: Optional[dict[str, Any]] = None
    sent_at: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BulkMessageResult:
    """Bulk message sending result."""

    total_messages: int
    successful: int
    failed: int
    results: list[MessageResult]
    batch_id: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CommunicationPlugin(BasePlugin):
    """
    Base class for communication plugins.

    Provides common interface for all communication channels.
    """

    @abstractmethod
    async def send_message(self, message: Message) -> MessageResult:
        """
        Send a single message.

        Args:
            message: Message to send

        Returns:
            Message sending result
        """
        pass

    async def send_bulk_messages(self, messages: list[Message]) -> BulkMessageResult:
        """
        Send multiple messages in bulk.

        Default implementation sends messages individually.
        Override for provider-specific bulk sending.

        Args:
            messages: List of messages to send

        Returns:
            Bulk sending result
        """
        results = []
        successful = 0
        failed = 0

        for message in messages:
            try:
                result = await self.send_message(message)
                results.append(result)

                if result.success:
                    successful += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                results.append(MessageResult(success=False, error_message=str(e), status=MessageStatus.FAILED))

        return BulkMessageResult(
            total_messages=len(messages),
            successful=successful,
            failed=failed,
            results=results,
        )

    async def get_message_status(self, message_id: str) -> Optional[MessageStatus]:
        """
        Get status of a sent message.

        Args:
            message_id: Message ID to check

        Returns:
            Message status or None if not supported
        """
        return None  # Override if provider supports status checking

    async def validate_recipient(self, recipient: str) -> bool:
        """
        Validate recipient format.

        Args:
            recipient: Recipient to validate

        Returns:
            True if valid
        """
        return bool(recipient)  # Basic validation - override for specific formats

    def get_supported_message_types(self) -> list[str]:
        """Get list of supported message types."""
        return ["text"]  # Override to specify supported types

    def get_rate_limits(self) -> dict[str, Any]:
        """Get rate limiting information for this provider."""
        return {}  # Override to specify rate limits


class CommunicationAdapter:
    """
    Domain adapter for communication plugins.

    Provides high-level interface for managing communication plugins
    and routing messages to appropriate providers.
    """

    def __init__(self):
        self._plugins: dict[str, CommunicationPlugin] = {}
        self._default_providers: dict[str, str] = {}  # message_type -> plugin_name
        self._fallback_providers: dict[str, list[str]] = {}  # message_type -> [plugin_names]
        self._logger = logging.getLogger("plugins.communication_adapter")

    def register_plugin(self, plugin_name: str, plugin: CommunicationPlugin) -> None:
        """Register a communication plugin."""
        if not isinstance(plugin, CommunicationPlugin):
            raise PluginError(f"Plugin {plugin_name} is not a CommunicationPlugin")

        self._plugins[plugin_name] = plugin
        self._logger.info(f"Registered communication plugin: {plugin_name}")

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a communication plugin."""
        if plugin_name in self._plugins:
            del self._plugins[plugin_name]

            # Clean up default providers
            providers_to_remove = [k for k, v in self._default_providers.items() if v == plugin_name]
            for provider in providers_to_remove:
                del self._default_providers[provider]

            # Clean up fallback providers
            for _message_type, providers in self._fallback_providers.items():
                if plugin_name in providers:
                    providers.remove(plugin_name)

            self._logger.info(f"Unregistered communication plugin: {plugin_name}")

    def set_default_provider(self, message_type: str, plugin_name: str) -> None:
        """Set default provider for a message type."""
        if plugin_name not in self._plugins:
            raise PluginError(f"Plugin {plugin_name} is not registered")

        self._default_providers[message_type] = plugin_name
        self._logger.info(f"Set default provider for {message_type}: {plugin_name}")

    def add_fallback_provider(self, message_type: str, plugin_name: str) -> None:
        """Add fallback provider for a message type."""
        if plugin_name not in self._plugins:
            raise PluginError(f"Plugin {plugin_name} is not registered")

        if message_type not in self._fallback_providers:
            self._fallback_providers[message_type] = []

        if plugin_name not in self._fallback_providers[message_type]:
            self._fallback_providers[message_type].append(plugin_name)
            self._logger.info(f"Added fallback provider for {message_type}: {plugin_name}")

    async def send_message(
        self,
        message: Message,
        provider: Optional[str] = None,
        use_fallback: bool = True,
    ) -> MessageResult:
        """
        Send a message using specified or default provider.

        Args:
            message: Message to send
            provider: Specific provider to use (optional)
            use_fallback: Whether to use fallback providers on failure

        Returns:
            Message result
        """
        # Determine provider to use
        if provider:
            if provider not in self._plugins:
                raise PluginError(f"Communication provider {provider} not found")
            providers_to_try = [provider]
        else:
            providers_to_try = []

            # Add default provider
            default_provider = self._default_providers.get(message.message_type)
            if default_provider:
                providers_to_try.append(default_provider)

            # Add fallback providers if enabled
            if use_fallback:
                fallbacks = self._fallback_providers.get(message.message_type, [])
                providers_to_try.extend(fallbacks)

        if not providers_to_try:
            raise PluginError(f"No providers available for message type: {message.message_type}")

        # Try providers in order
        last_error = None

        for provider_name in providers_to_try:
            if provider_name not in self._plugins:
                continue

            plugin = self._plugins[provider_name]

            try:
                # Validate message for this provider
                if not await plugin.validate_recipient(message.recipient):
                    self._logger.warning(f"Invalid recipient for provider {provider_name}: {message.recipient}")
                    continue

                # Send message
                result = await plugin.send_message(message)

                if result.success:
                    self._logger.info(f"Message sent successfully using provider: {provider_name}")
                    return result
                else:
                    self._logger.warning(f"Message failed with provider {provider_name}: {result.error_message}")
                    last_error = result.error_message

            except Exception as e:
                self._logger.error(f"Error sending message with provider {provider_name}: {e}")
                last_error = str(e)
                continue

        # All providers failed
        return MessageResult(
            success=False,
            error_message=f"All providers failed. Last error: {last_error}",
            status=MessageStatus.FAILED,
        )

    async def send_bulk_messages(
        self,
        messages: list[Message],
        provider: Optional[str] = None,
        batch_size: int = 100,
    ) -> BulkMessageResult:
        """
        Send bulk messages with automatic batching.

        Args:
            messages: Messages to send
            provider: Specific provider to use
            batch_size: Maximum messages per batch

        Returns:
            Bulk message result
        """
        if not messages:
            return BulkMessageResult(total_messages=0, successful=0, failed=0, results=[])

        # Group messages by type and provider
        if provider:
            message_groups = {provider: messages}
        else:
            message_groups = {}
            for message in messages:
                provider_name = self._default_providers.get(message.message_type)
                if not provider_name:
                    provider_name = "default"

                if provider_name not in message_groups:
                    message_groups[provider_name] = []
                message_groups[provider_name].append(message)

        # Send messages in groups
        all_results = []
        total_successful = 0
        total_failed = 0

        for provider_name, group_messages in message_groups.items():
            if provider_name not in self._plugins:
                # Handle messages individually
                for message in group_messages:
                    result = await self.send_message(message)
                    all_results.append(result)
                    if result.success:
                        total_successful += 1
                    else:
                        total_failed += 1
                continue

            plugin = self._plugins[provider_name]

            # Process in batches
            for i in range(0, len(group_messages), batch_size):
                batch = group_messages[i : i + batch_size]

                try:
                    batch_result = await plugin.send_bulk_messages(batch)
                    all_results.extend(batch_result.results)
                    total_successful += batch_result.successful
                    total_failed += batch_result.failed

                except Exception as e:
                    self._logger.error(f"Bulk send failed for provider {provider_name}: {e}")

                    # Mark all messages in batch as failed
                    for message in batch:
                        all_results.append(
                            MessageResult(
                                success=False,
                                error_message=str(e),
                                status=MessageStatus.FAILED,
                            )
                        )
                        total_failed += 1

        return BulkMessageResult(
            total_messages=len(messages),
            successful=total_successful,
            failed=total_failed,
            results=all_results,
        )

    async def broadcast_message(
        self, message: Message, providers: Optional[list[str]] = None
    ) -> dict[str, MessageResult]:
        """
        Broadcast message to multiple providers.

        Args:
            message: Message to broadcast
            providers: List of providers to use (all if None)

        Returns:
            Dict mapping provider names to results
        """
        if providers is None:
            providers = list(self._plugins.keys())

        results = {}
        tasks = []

        for provider_name in providers:
            if provider_name in self._plugins:
                task = asyncio.create_task(
                    self.send_message(message, provider_name, use_fallback=False),
                    name=f"broadcast_{provider_name}",
                )
                tasks.append((provider_name, task))

        # Wait for all broadcasts to complete
        for provider_name, task in tasks:
            try:
                result = await task
                results[provider_name] = result
            except Exception as e:
                results[provider_name] = MessageResult(success=False, error_message=str(e), status=MessageStatus.FAILED)

        return results

    def get_available_providers(self, message_type: Optional[str] = None) -> list[str]:
        """Get list of available providers."""
        if message_type is None:
            return list(self._plugins.keys())

        # Filter providers that support the message type
        available = []
        for name, plugin in self._plugins.items():
            if message_type in plugin.get_supported_message_types():
                available.append(name)

        return available

    def get_provider_info(self, provider_name: str) -> Optional[dict[str, Any]]:
        """Get information about a provider."""
        if provider_name not in self._plugins:
            return None

        plugin = self._plugins[provider_name]

        return {
            "name": provider_name,
            "domain": plugin.domain,
            "version": plugin.version,
            "status": plugin.status.value,
            "supported_message_types": plugin.get_supported_message_types(),
            "rate_limits": plugin.get_rate_limits(),
            "is_active": plugin.is_active,
            "is_healthy": plugin.is_healthy,
        }

    def get_routing_config(self) -> dict[str, Any]:
        """Get current message routing configuration."""
        return {
            "default_providers": dict(self._default_providers),
            "fallback_providers": dict(self._fallback_providers),
            "available_providers": list(self._plugins.keys()),
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all communication providers."""
        health_results = {}

        for provider_name, plugin in self._plugins.items():
            try:
                health_data = await plugin.health_check()
                health_results[provider_name] = health_data
            except Exception as e:
                health_results[provider_name] = {"healthy": False, "error": str(e)}

        # Overall health summary
        total_providers = len(self._plugins)
        healthy_providers = sum(1 for result in health_results.values() if result.get("healthy", False))

        return {
            "total_providers": total_providers,
            "healthy_providers": healthy_providers,
            "health_percentage": (healthy_providers / max(1, total_providers)) * 100,
            "provider_health": health_results,
        }

    @staticmethod
    def create_email_message(
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs,
    ) -> Message:
        """Create an email message."""
        return Message(
            recipient=to,
            content=body,
            subject=subject,
            sender=from_email,
            message_type="email",
            priority=priority,
            metadata=kwargs,
        )

    @staticmethod
    def create_sms_message(
        to: str,
        text: str,
        from_number: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs,
    ) -> Message:
        """Create an SMS message."""
        return Message(
            recipient=to,
            content=text,
            sender=from_number,
            message_type="sms",
            priority=priority,
            metadata=kwargs,
        )

    @staticmethod
    def create_push_notification(
        device_token: str,
        title: str,
        body: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs,
    ) -> Message:
        """Create a push notification message."""
        return Message(
            recipient=device_token,
            content=body,
            subject=title,
            message_type="push",
            priority=priority,
            metadata=kwargs,
        )
