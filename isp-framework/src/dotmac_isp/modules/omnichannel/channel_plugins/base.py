"""Base class for communication channel plugins."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum


class ChannelCapability(str, Enum):
    """Channel capabilities."""

    SEND_MESSAGE = "send_message"
    RECEIVE_MESSAGE = "receive_message"
    FILE_ATTACHMENT = "file_attachment"
    RICH_CONTENT = "rich_content"
    READ_RECEIPTS = "read_receipts"
    TYPING_INDICATORS = "typing_indicators"
    PRESENCE_STATUS = "presence_status"
    GROUP_MESSAGING = "group_messaging"
    VIDEO_CALL = "video_call"
    VOICE_CALL = "voice_call"
    SCREEN_SHARING = "screen_sharing"
    WEBHOOK_SUPPORT = "webhook_support"


class ChannelMessage(BaseModel):
    """Standard message format for all channels."""

    content: str
    message_type: str = "text"
    sender_id: str
    recipient_id: str
    channel_specific_data: Dict[str, Any] = {}
    attachments: List[Dict[str, str]] = []
    metadata: Dict[str, Any] = {}


class ChannelConfig(BaseModel):
    """Channel configuration schema."""

    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    webhook_url: Optional[str] = None
    base_url: Optional[str] = None
    additional_settings: Dict[str, Any] = {}


class BaseChannelPlugin(ABC):
    """Base class for all communication channel plugins."""

    def __init__(self, config: ChannelConfig, skip_validation: bool = False):
        self.config = config
        self.is_initialized = False
        self._skip_validation = skip_validation
        if not skip_validation:
            self._validate_config()

    @property
    @abstractmethod
    def channel_id(self) -> str:
        """Unique channel identifier (e.g., 'email', 'whatsapp')."""
        pass

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Human-readable channel name (e.g., 'Email', 'WhatsApp')."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[ChannelCapability]:
        """List of capabilities this channel supports."""
        pass

    @property
    @abstractmethod
    def required_config_fields(self) -> List[str]:
        """List of required configuration fields."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the channel plugin. Return True if successful."""
        pass

    @abstractmethod
    async def send_message(self, message: ChannelMessage) -> Dict[str, Any]:
        """Send a message through this channel."""
        pass

    @abstractmethod
    async def receive_message(
        self, webhook_data: Dict[str, Any]
    ) -> Optional[ChannelMessage]:
        """Process incoming webhook data and return a standardized message."""
        pass

    @abstractmethod
    async def get_delivery_status(self, message_id: str) -> str:
        """Get delivery status of a sent message."""
        pass

    def _validate_config(self):
        """Validate that required configuration fields are present."""
        # Skip validation during plugin registration/discovery
        if hasattr(self, "_skip_validation") and self._skip_validation:
            return

        missing_fields = []
        for field in self.required_config_fields:
            if not getattr(self.config, field, None):
                if field not in self.config.additional_settings:
                    missing_fields.append(field)

        if missing_fields:
            raise ValueError(
                f"Missing required config fields for {self.channel_id}: {missing_fields}"
            )

    async def health_check(self) -> bool:
        """Perform a health check on the channel."""
        return self.is_initialized

    def get_webhook_endpoint(self) -> str:
        """Get the webhook endpoint for this channel."""
        return f"/omnichannel/webhooks/{self.channel_id}"

    async def validate_recipient(self, recipient_id: str) -> bool:
        """Validate that the recipient ID is valid for this channel."""
        return True  # Default implementation

    def supports_capability(self, capability: ChannelCapability) -> bool:
        """Check if the channel supports a specific capability."""
        return capability in self.capabilities
