"""
Channel Orchestrator for Omnichannel Service

Provides unified channel management and message orchestration across:
- Email, SMS, WhatsApp, social media, voice, chat
- Template-based messaging with personalization
- Channel-specific formatting and delivery
- Message tracking and delivery confirmation
- Cross-channel conversation continuity
- Channel preference management

Author: DotMac Framework Team
License: MIT
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac_plugins.adapters.communication import (
    MessagePriority as PluginMessagePriority,
)
from jinja2 import BaseLoader, Environment, select_autoescape
from pydantic import BaseModel, ConfigDict, Field

from ..integrations.plugin_system_integration import (
    OmnichannelPluginManager,
    plugin_to_omnichannel_message_status,
)
from ..models.enums import ChannelType, MessageStatus

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Message content types"""

    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"
    RICH_TEXT = "rich_text"
    ATTACHMENT = "attachment"
    TEMPLATE = "template"


class DeliveryPriority(str, Enum):
    """Message delivery priority"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ChannelConfig:
    """Channel configuration settings"""

    channel_type: ChannelType
    provider: str
    config: dict[str, Any]
    enabled: bool = True
    rate_limit: Optional[int] = None  # messages per minute
    retry_attempts: int = 3
    timeout: int = 30  # seconds


@dataclass
class MessageTemplate:
    """Message template definition"""

    template_id: str
    channel_type: ChannelType
    name: str
    subject: Optional[str] = None
    content: str = ""
    content_type: MessageType = MessageType.TEXT
    variables: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageAttachment:
    """Message attachment definition"""

    filename: str
    content_type: str
    content: bytes
    size: int
    url: Optional[str] = None


class OutboundMessage(BaseModel):
    """Outbound message model"""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    interaction_id: Optional[UUID] = None
    customer_id: UUID
    agent_id: Optional[UUID] = None

    # Channel and delivery
    channel: ChannelType
    recipient: str  # email, phone, username, etc.
    sender: Optional[str] = None

    # Content
    subject: Optional[str] = None
    content: str
    content_type: MessageType = MessageType.TEXT
    template_id: Optional[str] = None
    template_variables: dict[str, Any] = Field(default_factory=dict)

    # Delivery settings
    priority: DeliveryPriority = DeliveryPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Attachments
    attachments: list[dict[str, Any]] = Field(default_factory=list)

    # Status and tracking
    status: MessageStatus = MessageStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    external_id: Optional[str] = None  # Provider message ID

    # Retry handling
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    extra_data: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(use_enum_values=True)


class InboundMessage(BaseModel):
    """Inbound message model"""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    customer_id: Optional[UUID] = None
    interaction_id: Optional[UUID] = None

    # Channel and origin
    channel: ChannelType
    sender: str  # email, phone, username, etc.
    recipient: str  # our channel identifier

    # Content
    subject: Optional[str] = None
    content: str
    content_type: MessageType = MessageType.TEXT

    # Attachments
    attachments: list[dict[str, Any]] = Field(default_factory=list)

    # Processing status
    processed: bool = False
    processed_at: Optional[datetime] = None
    assigned_agent_id: Optional[UUID] = None

    # Source tracking
    external_id: Optional[str] = None
    thread_id: Optional[str] = None
    in_reply_to: Optional[UUID] = None

    # Metadata
    received_at: datetime = Field(default_factory=datetime.utcnow)
    extra_data: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(use_enum_values=True)


class ChannelOrchestrator:
    """
    Central orchestrator for multi-channel communication

    Manages message routing, template rendering, delivery tracking,
    and channel-specific adaptations across all communication channels.
    """

    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id

        # Plugin system integration
        self.plugin_manager = OmnichannelPluginManager(tenant_id)

        # Channel configurations
        self.channel_configs: dict[ChannelType, ChannelConfig] = {}

        # Template management
        self.templates: dict[str, MessageTemplate] = {}
        self.template_engine = Environment(
            loader=BaseLoader(), autoescape=select_autoescape(["html", "xml"])
        )

        # Message queues and tracking
        self.outbound_queue: list[OutboundMessage] = []
        self.message_tracking: dict[UUID, OutboundMessage] = {}
        self.delivery_callbacks: dict[ChannelType, list[Callable]] = {}

        # Rate limiting
        self.rate_limiters: dict[ChannelType, dict[str, list[datetime]]] = {}

        # Retry management
        self.retry_queue: list[OutboundMessage] = []
        self.max_retry_delay = timedelta(hours=24)

    async def configure_channel(
        self, channel_type: ChannelType, provider: str, config: dict[str, Any]
    ):
        """Configure a communication channel"""
        try:
            channel_config = ChannelConfig(
                channel_type=channel_type,
                provider=provider,
                config=config,
                enabled=config.get("enabled", True),
                rate_limit=config.get("rate_limit"),
                retry_attempts=config.get("retry_attempts", 3),
                timeout=config.get("timeout", 30),
            )

            self.channel_configs[channel_type] = channel_config

            # Initialize rate limiter
            self.rate_limiters[channel_type] = {}

            logger.info(f"Configured {channel_type} channel with {provider}")

        except Exception as e:
            logger.error(f"Failed to configure channel {channel_type}: {e}")
            raise

    async def initialize(self) -> bool:
        """Initialize the channel orchestrator and plugin system"""
        try:
            # Initialize plugin manager first
            await self.plugin_manager.initialize()

            logger.info(f"Channel orchestrator initialized for tenant {self.tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize channel orchestrator: {e}")
            return False

    async def register_template(self, template: MessageTemplate):
        """Register a message template"""
        try:
            self.templates[template.template_id] = template
            logger.info(
                f"Registered template {template.template_id} for {template.channel_type}"
            )

        except Exception as e:
            logger.error(f"Failed to register template: {e}")
            raise

    async def send_message(
        self,
        interaction_id: UUID,
        channel: ChannelType,
        recipient: str,
        content: str,
        agent_id: Optional[UUID] = None,
        customer_id: Optional[UUID] = None,
        template_id: Optional[str] = None,
        template_vars: Optional[dict[str, Any]] = None,
        attachments: Optional[list[MessageAttachment]] = None,
        priority: DeliveryPriority = DeliveryPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
    ) -> OutboundMessage:
        """Send a message through specified channel"""
        try:
            # Create outbound message
            message = OutboundMessage(
                tenant_id=self.tenant_id,
                interaction_id=interaction_id,
                customer_id=customer_id or UUID("00000000-0000-0000-0000-000000000000"),
                agent_id=agent_id,
                channel=channel,
                recipient=recipient,
                content=content,
                template_id=template_id,
                template_variables=template_vars or {},
                priority=priority,
                scheduled_at=scheduled_at,
                attachments=[
                    att.__dict__ if hasattr(att, "__dict__") else att
                    for att in (attachments or [])
                ],
            )

            # Render template if specified
            if template_id and template_id in self.templates:
                rendered_content = await self._render_template(
                    template_id, template_vars or {}
                )
                message.content = rendered_content

                template = self.templates[template_id]
                if template.subject:
                    message.subject = await self._render_text(
                        template.subject, template_vars or {}
                    )

            # Validate channel is configured and enabled
            if not await self._validate_channel(channel):
                raise ValueError(f"Channel {channel} not configured or disabled")

            # Check rate limits
            if not await self._check_rate_limit(channel, recipient):
                message.status = MessageStatus.QUEUED
                message.next_retry_at = datetime.now(timezone.utc) + timedelta(
                    minutes=5
                )
                self.retry_queue.append(message)
                logger.warning(f"Message queued due to rate limit: {message.id}")
                return message

            # Queue for immediate delivery or schedule
            if scheduled_at and scheduled_at > datetime.now(timezone.utc):
                message.status = MessageStatus.QUEUED
                self.outbound_queue.append(message)
            else:
                await self._deliver_message(message)

            # Track message
            self.message_tracking[message.id] = message

            return message

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def handle_incoming_message(
        self,
        channel: ChannelType,
        sender: str,
        content: str,
        recipient: str = "",
        subject: Optional[str] = None,
        external_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        attachments: Optional[list[dict]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> InboundMessage:
        """Handle incoming message from any channel"""
        try:
            # Create inbound message
            message = InboundMessage(
                tenant_id=self.tenant_id,
                channel=channel,
                sender=sender,
                recipient=recipient,
                subject=subject,
                content=content,
                external_id=external_id,
                thread_id=thread_id,
                attachments=attachments or [],
                metadata=metadata or {},
            )

            # Try to identify customer and interaction
            await self._identify_customer_and_interaction(message)

            # Trigger processing workflow
            await self._process_incoming_message(message)

            return message

        except Exception as e:
            logger.error(f"Failed to handle incoming message: {e}")
            raise

    async def get_message_status(self, message_id: UUID) -> Optional[dict[str, Any]]:
        """Get message delivery status"""
        try:
            message = self.message_tracking.get(message_id)
            if not message:
                return None

            return {
                "message_id": message_id,
                "status": message.status,
                "sent_at": message.sent_at,
                "delivered_at": message.delivered_at,
                "read_at": message.read_at,
                "failed_at": message.failed_at,
                "failure_reason": message.failure_reason,
                "retry_count": message.retry_count,
                "next_retry_at": message.next_retry_at,
                "external_id": message.external_id,
            }

        except Exception as e:
            logger.error(f"Failed to get message status: {e}")
            return None

    async def update_message_status(
        self,
        message_id: UUID,
        status: MessageStatus,
        external_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ):
        """Update message delivery status"""
        try:
            message = self.message_tracking.get(message_id)
            if not message:
                return False

            message.status = status
            message.updated_at = datetime.now(timezone.utc)

            if external_id:
                message.external_id = external_id

            if status == MessageStatus.SENT:
                message.sent_at = datetime.now(timezone.utc)
            elif status == MessageStatus.DELIVERED:
                message.delivered_at = datetime.now(timezone.utc)
            elif status == MessageStatus.READ:
                message.read_at = datetime.now(timezone.utc)
            elif status in [MessageStatus.FAILED, MessageStatus.BOUNCED]:
                message.failed_at = datetime.now(timezone.utc)
                message.failure_reason = failure_reason

            # Trigger callbacks
            await self._trigger_delivery_callbacks(message)

            logger.info(f"Updated message {message_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update message status: {e}")
            return False

    async def retry_failed_messages(self):
        """Retry failed messages that are eligible for retry"""
        try:
            now = datetime.now(timezone.utc)
            retry_messages = []

            # Find messages ready for retry
            for message in list(self.retry_queue):
                if (
                    message.next_retry_at
                    and message.next_retry_at <= now
                    and message.retry_count < message.max_retries
                ):
                    retry_messages.append(message)
                    self.retry_queue.remove(message)

            # Retry eligible messages
            for message in retry_messages:
                try:
                    message.retry_count += 1
                    await self._deliver_message(message)
                    logger.info(
                        f"Retried message {message.id} (attempt {message.retry_count})"
                    )

                except Exception as e:
                    logger.error(f"Failed to retry message {message.id}: {e}")

                    # Schedule next retry with exponential backoff
                    if message.retry_count < message.max_retries:
                        delay = min(
                            timedelta(minutes=2**message.retry_count),
                            self.max_retry_delay,
                        )
                        message.next_retry_at = now + delay
                        self.retry_queue.append(message)
                    else:
                        message.status = MessageStatus.FAILED
                        message.failure_reason = "Max retries exceeded"
                        message.failed_at = now

        except Exception as e:
            logger.error(f"Failed to retry messages: {e}")

    async def get_available_channels(self) -> dict[ChannelType, list[dict[str, Any]]]:
        """Get all available channels from plugin system"""
        try:
            return await self.plugin_manager.get_available_channels()
        except Exception as e:
            logger.error(f"Failed to get available channels: {e}")
            return {}

    async def get_plugin_status(
        self, plugin_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Get status of specific plugin or all plugins"""
        try:
            if plugin_id:
                status = await self.plugin_manager.get_plugin_status(plugin_id)
                return {plugin_id: status} if status else {}
            else:
                # Get status of all plugins
                all_channels = await self.get_available_channels()
                all_status = {}

                for _channel_type, plugins in all_channels.items():
                    for plugin_info in plugins:
                        plugin_id = plugin_info["plugin_id"]
                        all_status[plugin_id] = plugin_info

                return all_status

        except Exception as e:
            logger.error(f"Failed to get plugin status: {e}")
            return {}

    async def get_channel_statistics(self) -> dict[ChannelType, dict[str, Any]]:
        """Get statistics for all channels"""
        try:
            stats = {}

            for channel_type in self.channel_configs.keys():
                channel_messages = [
                    msg
                    for msg in self.message_tracking.values()
                    if msg.channel == channel_type
                ]

                stats[channel_type] = {
                    "total_messages": len(channel_messages),
                    "sent": len(
                        [m for m in channel_messages if m.status == MessageStatus.SENT]
                    ),
                    "delivered": len(
                        [
                            m
                            for m in channel_messages
                            if m.status == MessageStatus.DELIVERED
                        ]
                    ),
                    "failed": len(
                        [
                            m
                            for m in channel_messages
                            if m.status == MessageStatus.FAILED
                        ]
                    ),
                    "pending": len(
                        [
                            m
                            for m in channel_messages
                            if m.status == MessageStatus.PENDING
                        ]
                    ),
                    "avg_delivery_time": await self._calculate_avg_delivery_time(
                        channel_messages
                    ),
                    "success_rate": await self._calculate_success_rate(
                        channel_messages
                    ),
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get channel statistics: {e}")
            return {}

    # Private helper methods

    async def _validate_channel(self, channel: ChannelType) -> bool:
        """Validate channel is configured and enabled"""
        config = self.channel_configs.get(channel)
        return config is not None and config.enabled

    async def _check_rate_limit(self, channel: ChannelType, recipient: str) -> bool:
        """Check if message can be sent within rate limits"""
        try:
            config = self.channel_configs.get(channel)
            if not config or not config.rate_limit:
                return True

            now = datetime.now(timezone.utc)
            window_start = now - timedelta(minutes=1)

            # Clean old entries
            if channel not in self.rate_limiters:
                self.rate_limiters[channel] = {}

            if recipient not in self.rate_limiters[channel]:
                self.rate_limiters[channel][recipient] = []

            recent_messages = [
                ts for ts in self.rate_limiters[channel][recipient] if ts > window_start
            ]
            self.rate_limiters[channel][recipient] = recent_messages

            # Check limit
            if len(recent_messages) >= config.rate_limit:
                return False

            # Record this message
            self.rate_limiters[channel][recipient].append(now)
            return True

        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return True  # Allow on error

    async def _deliver_message(self, message: OutboundMessage):
        """Deliver message through appropriate channel"""
        try:
            # Update status
            message.status = MessageStatus.QUEUED
            message.updated_at = datetime.now(timezone.utc)

            # Send via plugin system
            plugin_priority = self._convert_to_plugin_priority(message.priority)

            delivery_result = await self.plugin_manager.send_message(
                channel_type=message.channel,
                recipient=message.recipient,
                content=message.content,
                subject=message.subject,
                interaction_id=message.interaction_id,
                agent_id=message.agent_id,
                priority=plugin_priority,
                metadata=message.metadata,
            )

            # Update based on plugin system result
            if delivery_result.success:
                message.status = plugin_to_omnichannel_message_status(
                    delivery_result.status
                )
                if message.status == MessageStatus.SENT:
                    message.sent_at = datetime.now(timezone.utc)
                elif message.status == MessageStatus.DELIVERED:
                    message.sent_at = datetime.now(timezone.utc)
                    message.delivered_at = datetime.now(timezone.utc)
                message.external_id = delivery_result.message_id
            else:
                message.status = MessageStatus.FAILED
                message.failed_at = datetime.now(timezone.utc)
                message.failure_reason = delivery_result.error_message

            message.updated_at = datetime.now(timezone.utc)

        except Exception as e:
            message.status = MessageStatus.FAILED
            message.failed_at = datetime.now(timezone.utc)
            message.failure_reason = str(e)
            message.updated_at = datetime.now(timezone.utc)
            logger.error(f"Failed to deliver message {message.id}: {e}")

    async def _render_template(
        self, template_id: str, variables: dict[str, Any]
    ) -> str:
        """Render message template with variables"""
        try:
            template = self.templates.get(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")

            jinja_template = self.template_engine.from_string(template.content)
            return jinja_template.render(**variables)

        except Exception as e:
            logger.error(f"Failed to render template {template_id}: {e}")
            raise

    async def _render_text(self, text: str, variables: dict[str, Any]) -> str:
        """Render text with template variables"""
        try:
            jinja_template = self.template_engine.from_string(text)
            return jinja_template.render(**variables)

        except Exception as e:
            logger.error(f"Failed to render text: {e}")
            return text

    async def _identify_customer_and_interaction(self, message: InboundMessage):
        """Identify customer and interaction for incoming message"""
        try:
            # This would integrate with your customer database
            # and interaction tracking system

            # Simplified implementation - in production, you'd:
            # 1. Look up customer by sender (email, phone, etc.)
            # 2. Find active interaction or create new one
            # 3. Link message to conversation thread

            # For now, just log the identification attempt
            logger.info(
                f"Identifying customer for {message.channel} message from {message.sender}"
            )

        except Exception as e:
            logger.error(f"Failed to identify customer: {e}")

    async def _process_incoming_message(self, message: InboundMessage):
        """Process incoming message for routing and response"""
        try:
            # This would trigger the interaction manager and routing engine
            # Simplified implementation for now
            message.processed = True
            message.processed_at = datetime.now(timezone.utc)

            logger.info(f"Processed incoming message {message.id}")

        except Exception as e:
            logger.error(f"Failed to process incoming message: {e}")

    async def _trigger_delivery_callbacks(self, message: OutboundMessage):
        """Trigger registered delivery callbacks"""
        try:
            callbacks = self.delivery_callbacks.get(message.channel, [])
            for callback in callbacks:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Delivery callback failed: {e}")

        except Exception as e:
            logger.error(f"Failed to trigger callbacks: {e}")

    async def _calculate_avg_delivery_time(
        self, messages: list[OutboundMessage]
    ) -> float:
        """Calculate average delivery time for messages"""
        try:
            delivered_messages = [m for m in messages if m.sent_at and m.delivered_at]

            if not delivered_messages:
                return 0.0

            total_time = sum(
                (m.delivered_at - m.sent_at).total_seconds() for m in delivered_messages
            )

            return total_time / len(delivered_messages)

        except Exception as e:
            logger.error(f"Failed to calculate avg delivery time: {e}")
            return 0.0

    async def _calculate_success_rate(self, messages: list[OutboundMessage]) -> float:
        """Calculate message success rate"""
        try:
            if not messages:
                return 0.0

            successful = len(
                [
                    m
                    for m in messages
                    if m.status
                    in [MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ]
                ]
            )

            return (successful / len(messages)) * 100.0

        except Exception as e:
            logger.error(f"Failed to calculate success rate: {e}")
            return 0.0

    def register_delivery_callback(self, channel: ChannelType, callback: Callable):
        """Register callback for delivery status updates"""
        if channel not in self.delivery_callbacks:
            self.delivery_callbacks[channel] = []
        self.delivery_callbacks[channel].append(callback)

    def _convert_to_plugin_priority(
        self, priority: DeliveryPriority
    ) -> PluginMessagePriority:
        """Convert omnichannel priority to plugin system priority"""
        priority_mapping = {
            DeliveryPriority.LOW: PluginMessagePriority.LOW,
            DeliveryPriority.NORMAL: PluginMessagePriority.NORMAL,
            DeliveryPriority.HIGH: PluginMessagePriority.HIGH,
            DeliveryPriority.URGENT: PluginMessagePriority.URGENT,
        }

        return priority_mapping.get(priority, PluginMessagePriority.NORMAL)
