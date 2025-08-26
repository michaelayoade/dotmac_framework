"""
Universal Channel Provider Registry

Strategic architecture for eliminating all hardcoded communication channels
across the entire DotMac platform. This provides a single source of truth
for all communication providers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Protocol
from dataclasses import dataclass
from enum import Enum
import importlib
import os

logger = logging.getLogger(__name__)


class ChannelCapability(Enum):
    """Communication channel capabilities."""
    TEXT_MESSAGING = "text_messaging"
    RICH_MESSAGING = "rich_messaging"
    FILE_ATTACHMENTS = "file_attachments"
    DELIVERY_RECEIPTS = "delivery_receipts"
    READ_RECEIPTS = "read_receipts"
    TWO_WAY_MESSAGING = "two_way_messaging"
    BULK_MESSAGING = "bulk_messaging"
    TEMPLATE_MESSAGING = "template_messaging"
    WEBHOOK_SUPPORT = "webhook_support"
    REAL_TIME_DELIVERY = "real_time_delivery"


class MessageType(Enum):
    """Types of messages that can be sent."""
    NOTIFICATION = "notification"
    ALERT = "alert" 
    MARKETING = "marketing"
    TRANSACTIONAL = "transactional"
    VERIFICATION = "verification"
    SUPPORT = "support"
    DIGEST = "digest"


@dataclass
class ChannelConfiguration:
    """Configuration for a communication channel."""
    provider_name: str
    channel_type: str
    config: Dict[str, Any]
    is_active: bool = True
    priority: int = 1
    rate_limit_per_minute: Optional[int] = None
    supported_message_types: List[MessageType] = None
    
    def __post_init__(self):
        if self.supported_message_types is None:
            self.supported_message_types = [MessageType.NOTIFICATION]


@dataclass 
class Message:
    """Universal message format."""
    recipient: str
    content: str
    message_type: MessageType = MessageType.NOTIFICATION
    template_name: Optional[str] = None
    template_vars: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    priority: int = 1
    
    def __post_init__(self):
        if self.template_vars is None:
            self.template_vars = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DeliveryResult:
    """Result of message delivery attempt."""
    success: bool
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    delivery_time_ms: Optional[float] = None
    provider_response: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.provider_response is None:
            self.provider_response = {}


class BaseChannelProvider(ABC):
    """Abstract base class for all channel providers."""
    
    def __init__(self, config: ChannelConfiguration):
        """Initialize provider with configuration."""
        self.config = config
        self._capabilities: List[ChannelCapability] = []
        self._is_initialized = False
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider name (e.g., 'twilio_sms', 'sendgrid_email')."""
        pass
    
    @property
    @abstractmethod 
    def channel_type(self) -> str:
        """Channel type (e.g., 'sms', 'email', 'slack', 'webhook')."""
        pass
    
    @property
    def capabilities(self) -> List[ChannelCapability]:
        """List of capabilities this provider supports."""
        return self._capabilities
    
    @property
    def is_initialized(self) -> bool:
        """Whether the provider is initialized and ready."""
        return self._is_initialized
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider. Return True if successful."""
        pass
    
    @abstractmethod
    async def send_message(self, message: Message) -> DeliveryResult:
        """Send a message. Return delivery result."""
        pass
    
    @abstractmethod
    async def validate_configuration(self) -> bool:
        """Validate provider configuration. Return True if valid."""
        pass
    
    def supports_capability(self, capability: ChannelCapability) -> bool:
        """Check if provider supports a specific capability."""
        return capability in self._capabilities
    
    def supports_message_type(self, message_type: MessageType) -> bool:
        """Check if provider supports a specific message type."""
        return message_type in self.config.supported_message_types
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle webhook data from provider. Override if webhook support exists."""
        return None
    
    async def get_delivery_status(self, provider_message_id: str) -> Optional[str]:
        """Get delivery status for a message. Override if supported."""
        return None


class ChannelProviderRegistry:
    """Registry for managing all communication channel providers."""
    
    def __init__(self):
        """Initialize registry."""
        self._provider_classes: Dict[str, Type[BaseChannelProvider]] = {}
        self._active_providers: Dict[str, BaseChannelProvider] = {}
        self._configurations: Dict[str, ChannelConfiguration] = {}
        self._auto_discovery_enabled = True
    
    def register_provider_class(self, provider_class: Type[BaseChannelProvider]):
        """Register a provider class."""
        # Create temporary instance to get provider info
        temp_config = ChannelConfiguration(
            provider_name="temp",
            channel_type="temp", 
            config={}
        )
        
        try:
            temp_instance = provider_class(temp_config)
            provider_name = temp_instance.provider_name
            
            self._provider_classes[provider_name] = provider_class
            logger.info(f"Registered provider class: {provider_name}")
            
        except Exception as e:
            logger.error(f"Failed to register provider {provider_class.__name__}: {e}")
    
    def configure_provider(self, config: ChannelConfiguration) -> bool:
        """Configure and initialize a provider."""
        provider_name = config.provider_name
        
        if provider_name not in self._provider_classes:
            logger.error(f"Unknown provider: {provider_name}")
            return False
        
        try:
            provider_class = self._provider_classes[provider_name]
            provider_instance = provider_class(config)
            
            self._configurations[provider_name] = config
            self._active_providers[provider_name] = provider_instance
            
            logger.info(f"Configured provider: {provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure provider {provider_name}: {e}")
            return False
    
    async def initialize_provider(self, provider_name: str) -> bool:
        """Initialize a configured provider."""
        if provider_name not in self._active_providers:
            logger.error(f"Provider {provider_name} not configured")
            return False
        
        try:
            provider = self._active_providers[provider_name]
            success = await provider.initialize()
            
            if success:
                logger.info(f"Successfully initialized provider: {provider_name}")
            else:
                logger.error(f"Failed to initialize provider: {provider_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing provider {provider_name}: {e}")
            return False
    
    def get_provider(self, provider_name: str) -> Optional[BaseChannelProvider]:
        """Get an active provider instance."""
        return self._active_providers.get(provider_name)
    
    def get_providers_by_channel_type(self, channel_type: str) -> List[BaseChannelProvider]:
        """Get all active providers for a channel type."""
        providers = []
        for provider in self._active_providers.values():
            if provider.channel_type == channel_type and provider.is_initialized:
                providers.append(provider)
        return providers
    
    def get_providers_by_capability(self, capability: ChannelCapability) -> List[BaseChannelProvider]:
        """Get all providers that support a specific capability."""
        providers = []
        for provider in self._active_providers.values():
            if provider.supports_capability(capability) and provider.is_initialized:
                providers.append(provider)
        return providers
    
    async def send_message(self, 
                          channel_type: str, 
                          message: Message,
                          fallback: bool = True) -> DeliveryResult:
        """
        Send message via best available provider for channel type.
        
        Args:
            channel_type: Type of channel (sms, email, etc.)
            message: Message to send
            fallback: Whether to try fallback providers on failure
        """
        providers = self.get_providers_by_channel_type(channel_type)
        
        if not providers:
            return DeliveryResult(
                success=False,
                error_message=f"No active providers for channel type: {channel_type}"
            )
        
        # Sort by priority (lower number = higher priority)
        providers.sort(key=lambda p: p.config.priority)
        
        last_error = None
        
        for provider in providers:
            if not provider.supports_message_type(message.message_type):
                continue
                
            try:
                result = await provider.send_message(message)
                
                if result.success:
                    return result
                else:
                    last_error = result.error_message
                    if not fallback:
                        break
                        
            except Exception as e:
                last_error = str(e)
                logger.error(f"Provider {provider.provider_name} failed: {e}")
                if not fallback:
                    break
        
        return DeliveryResult(
            success=False,
            error_message=f"All providers failed. Last error: {last_error}"
        )
    
    def list_available_providers(self) -> List[str]:
        """List all registered provider classes."""
        return list(self._provider_classes.keys()
    
    def list_active_providers(self) -> List[str]:
        """List all active/configured providers."""
        return list(self._active_providers.keys()
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            return None
            
        return {
            "provider_name": provider.provider_name,
            "channel_type": provider.channel_type,
            "capabilities": [cap.value for cap in provider.capabilities],
            "is_initialized": provider.is_initialized,
            "configuration": {
                "is_active": provider.config.is_active,
                "priority": provider.config.priority,
                "rate_limit": provider.config.rate_limit_per_minute,
                "supported_message_types": [mt.value for mt in provider.config.supported_message_types]
            }
        }
    
    async def auto_discover_providers(self, discovery_paths: List[str] = None):
        """Auto-discover and register providers from specified paths."""
        if not self._auto_discovery_enabled:
            return
            
        if discovery_paths is None:
            discovery_paths = [
                "dotmac_isp.modules.omnichannel.channel_plugins",
                "shared.communication.providers",
                "templates.isp-communications.providers"
            ]
        
        for path in discovery_paths:
            await self._discover_providers_in_module(path)
    
    async def _discover_providers_in_module(self, module_path: str):
        """Discover providers in a specific module."""
        try:
            module = importlib.import_module(module_path)
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseChannelProvider) and 
                    attr != BaseChannelProvider):
                    
                    self.register_provider_class(attr)
                    
        except ImportError as e:
            logger.warning(f"Could not import module {module_path}: {e}")
        except Exception as e:
            logger.error(f"Error discovering providers in {module_path}: {e}")


# Global registry instance
global_channel_registry = ChannelProviderRegistry()


def register_provider(provider_class: Type[BaseChannelProvider]):
    """Decorator to automatically register provider classes."""
    global_channel_registry.register_provider_class(provider_class)
    return provider_class


# Utility functions for backward compatibility and easy migration
async def send_notification(channel_type: str, 
                           recipient: str, 
                           content: str,
                           template_name: str = None,
                           template_vars: Dict[str, Any] = None,
                           message_type: MessageType = MessageType.NOTIFICATION) -> bool:
    """
    Simplified interface for sending notifications.
    
    This function provides backward compatibility for existing code
    while using the new provider architecture underneath.
    """
    message = Message(
        recipient=recipient,
        content=content,
        message_type=message_type,
        template_name=template_name,
        template_vars=template_vars or {}
    )
    
    result = await global_channel_registry.send_message(channel_type, message)
    return result.success


async def get_available_channels() -> Dict[str, List[str]]:
    """Get all available communication channels grouped by type."""
    channels = {}
    
    for provider_name in global_channel_registry.list_active_providers():
        provider = global_channel_registry.get_provider(provider_name)
        if provider and provider.is_initialized:
            channel_type = provider.channel_type
            if channel_type not in channels:
                channels[channel_type] = []
            channels[channel_type].append(provider_name)
    
    return channels