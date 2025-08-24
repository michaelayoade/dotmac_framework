"""
Provider Architecture Initialization

Strategic initialization of communication providers to replace all
hardcoded channel checks throughout the platform.
"""

import os
import logging
from typing import Dict, Any, List

from .channel_provider_registry import (
    global_channel_registry,
    ChannelConfiguration,
    MessageType
)

logger = logging.getLogger(__name__)


async def initialize_communication_providers():
    """
    Initialize all communication providers based on environment configuration.
    
    This replaces the need for hardcoded channel checks throughout the codebase.
    Providers are loaded dynamically based on available configuration.
    """
    
    logger.info("🚀 Initializing Universal Communication Provider Architecture")
    
    providers_configured = 0
    providers_failed = 0
    
    # Auto-discover all available providers
    await global_channel_registry.auto_discover_providers()
    
    # Configure providers based on environment variables
    await _configure_email_providers()
    await _configure_sms_providers() 
    await _configure_webhook_providers()
    await _configure_chat_providers()
    
    # Initialize all configured providers
    for provider_name in global_channel_registry.list_active_providers():
        try:
            success = await global_channel_registry.initialize_provider(provider_name)
            if success:
                providers_configured += 1
                logger.info(f"✅ Provider initialized: {provider_name}")
            else:
                providers_failed += 1
                logger.error(f"❌ Provider failed to initialize: {provider_name}")
        except Exception as e:
            providers_failed += 1
            logger.error(f"❌ Provider initialization error {provider_name}: {e}")
    
    logger.info(f"📊 Provider initialization complete: {providers_configured} successful, {providers_failed} failed")
    
    if providers_configured == 0:
        logger.warning("⚠️ No communication providers initialized - notifications will not work")
    else:
        logger.info("🎉 Communication provider architecture ready - no more hardcoded channels!")
    
    return providers_configured > 0


async def _configure_email_providers():
    """Configure email providers based on available configuration."""
    
    # SMTP Email Provider
    if all(os.getenv(key) for key in ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"]):
        config = ChannelConfiguration(
            provider_name="smtp_email",
            channel_type="email",
            config={
                "backend": "smtp",
                "smtp_host": os.getenv("SMTP_HOST"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_user": os.getenv("SMTP_USER"),
                "smtp_password": os.getenv("SMTP_PASSWORD"),
                "from_email": os.getenv("FROM_EMAIL"),
                "from_name": os.getenv("FROM_NAME", "DotMac Platform"),
                "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true"
            },
            priority=1,
            supported_message_types=[
                MessageType.NOTIFICATION,
                MessageType.ALERT,
                MessageType.TRANSACTIONAL,
                MessageType.VERIFICATION,
                MessageType.DIGEST
            ]
        )
        global_channel_registry.configure_provider(config)
        logger.info("Configured SMTP email provider")
    
    # SendGrid Email Provider
    if os.getenv("SENDGRID_API_KEY"):
        config = ChannelConfiguration(
            provider_name="sendgrid_email",
            channel_type="email",
            config={
                "backend": "sendgrid",
                "sendgrid_api_key": os.getenv("SENDGRID_API_KEY"),
                "from_email": os.getenv("FROM_EMAIL"),
                "from_name": os.getenv("FROM_NAME", "DotMac Platform")
            },
            priority=2,  # Lower priority than SMTP
            supported_message_types=[
                MessageType.NOTIFICATION,
                MessageType.ALERT,
                MessageType.MARKETING,
                MessageType.TRANSACTIONAL
            ]
        )
        global_channel_registry.configure_provider(config)
        logger.info("Configured SendGrid email provider")


async def _configure_sms_providers():
    """Configure SMS providers based on available configuration."""
    
    # Twilio SMS Provider
    if all(os.getenv(key) for key in ["TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM_NUMBER"]):
        config = ChannelConfiguration(
            provider_name="twilio_sms",
            channel_type="sms",
            config={
                "account_sid": os.getenv("TWILIO_SID"),
                "auth_token": os.getenv("TWILIO_TOKEN"),
                "from_number": os.getenv("TWILIO_FROM_NUMBER")
            },
            priority=1,
            rate_limit_per_minute=100,  # Twilio rate limits
            supported_message_types=[
                MessageType.NOTIFICATION,
                MessageType.ALERT,
                MessageType.VERIFICATION,
                MessageType.TRANSACTIONAL
            ]
        )
        global_channel_registry.configure_provider(config)
        logger.info("Configured Twilio SMS provider")
    
    # Vonage SMS Provider  
    if all(os.getenv(key) for key in ["VONAGE_API_KEY", "VONAGE_API_SECRET"]):
        config = ChannelConfiguration(
            provider_name="vonage_sms",
            channel_type="sms", 
            config={
                "api_key": os.getenv("VONAGE_API_KEY"),
                "api_secret": os.getenv("VONAGE_API_SECRET"),
                "from_number": os.getenv("VONAGE_FROM_NUMBER", "DotMac")
            },
            priority=2,  # Fallback to Vonage if Twilio fails
            supported_message_types=[
                MessageType.NOTIFICATION,
                MessageType.ALERT,
                MessageType.VERIFICATION
            ]
        )
        global_channel_registry.configure_provider(config)
        logger.info("Configured Vonage SMS provider")


async def _configure_webhook_providers():
    """Configure webhook providers for generic HTTP notifications."""
    
    # Generic Webhook Provider
    config = ChannelConfiguration(
        provider_name="generic_webhook",
        channel_type="webhook",
        config={
            "default_timeout": 30,
            "retry_attempts": 3,
            "verify_ssl": True
        },
        priority=1,
        supported_message_types=[
            MessageType.NOTIFICATION,
            MessageType.ALERT,
            MessageType.SUPPORT
        ]
    )
    global_channel_registry.configure_provider(config)
    logger.info("Configured generic webhook provider")


async def _configure_chat_providers():
    """Configure chat providers (Slack, Teams, etc.) based on configuration."""
    
    # Slack Webhook Provider
    if os.getenv("SLACK_WEBHOOK_URL"):
        config = ChannelConfiguration(
            provider_name="slack_webhook",
            channel_type="slack",
            config={
                "webhook_url": os.getenv("SLACK_WEBHOOK_URL"),
                "channel": os.getenv("SLACK_DEFAULT_CHANNEL", "#alerts"),
                "username": os.getenv("SLACK_USERNAME", "DotMac Bot")
            },
            priority=1,
            supported_message_types=[
                MessageType.ALERT,
                MessageType.NOTIFICATION,
                MessageType.SUPPORT
            ]
        )
        global_channel_registry.configure_provider(config)
        logger.info("Configured Slack webhook provider")
    
    # Microsoft Teams Provider
    if os.getenv("TEAMS_WEBHOOK_URL"):
        config = ChannelConfiguration(
            provider_name="teams_webhook", 
            channel_type="teams",
            config={
                "webhook_url": os.getenv("TEAMS_WEBHOOK_URL")
            },
            priority=1,
            supported_message_types=[
                MessageType.ALERT,
                MessageType.NOTIFICATION
            ]
        )
        global_channel_registry.configure_provider(config)
        logger.info("Configured Teams webhook provider")


async def get_provider_architecture_status() -> Dict[str, Any]:
    """Get status of the provider architecture for monitoring/debugging."""
    
    status = {
        "architecture_initialized": len(global_channel_registry.list_active_providers()) > 0,
        "total_providers_registered": len(global_channel_registry.list_available_providers()),
        "active_providers": len(global_channel_registry.list_active_providers()),
        "providers_by_type": {},
        "provider_details": {}
    }
    
    # Group providers by channel type
    for provider_name in global_channel_registry.list_active_providers():
        provider = global_channel_registry.get_provider(provider_name)
        if provider:
            channel_type = provider.channel_type
            if channel_type not in status["providers_by_type"]:
                status["providers_by_type"][channel_type] = []
            status["providers_by_type"][channel_type].append(provider_name)
            
            # Get provider details
            status["provider_details"][provider_name] = global_channel_registry.get_provider_info(provider_name)
    
    return status


async def validate_provider_architecture() -> Dict[str, Any]:
    """Validate that the provider architecture is working correctly."""
    
    validation_results = {
        "architecture_healthy": True,
        "issues": [],
        "warnings": [],
        "recommendations": []
    }
    
    # Check if any providers are active
    active_providers = global_channel_registry.list_active_providers()
    if not active_providers:
        validation_results["architecture_healthy"] = False
        validation_results["issues"].append("No active communication providers found")
        validation_results["recommendations"].append("Configure at least one provider for notifications")
        return validation_results
    
    # Test each provider
    for provider_name in active_providers:
        provider = global_channel_registry.get_provider(provider_name)
        
        if not provider:
            validation_results["issues"].append(f"Provider {provider_name} not accessible")
            continue
            
        if not provider.is_initialized:
            validation_results["warnings"].append(f"Provider {provider_name} not initialized")
            continue
        
        # Test provider configuration
        try:
            config_valid = await provider.validate_configuration()
            if not config_valid:
                validation_results["issues"].append(f"Provider {provider_name} configuration invalid")
        except Exception as e:
            validation_results["issues"].append(f"Provider {provider_name} validation error: {e}")
    
    # Set overall health status
    if validation_results["issues"]:
        validation_results["architecture_healthy"] = False
    elif validation_results["warnings"]:
        validation_results["recommendations"].append("Address warnings for optimal performance")
    else:
        validation_results["recommendations"].append("Provider architecture is healthy and ready")
    
    return validation_results


# Environment-based configuration loading
def load_provider_config_from_env() -> Dict[str, Any]:
    """Load provider configuration from environment variables."""
    
    config = {
        "email_providers": {},
        "sms_providers": {},
        "webhook_providers": {},
        "chat_providers": {}
    }
    
    # Email providers
    if os.getenv("SMTP_HOST"):
        config["email_providers"]["smtp"] = {
            "host": os.getenv("SMTP_HOST"),
            "port": os.getenv("SMTP_PORT", "587"),
            "user": os.getenv("SMTP_USER"),
            "password": os.getenv("SMTP_PASSWORD")
        }
    
    if os.getenv("SENDGRID_API_KEY"):
        config["email_providers"]["sendgrid"] = {
            "api_key": os.getenv("SENDGRID_API_KEY")
        }
    
    # SMS providers
    if os.getenv("TWILIO_SID"):
        config["sms_providers"]["twilio"] = {
            "account_sid": os.getenv("TWILIO_SID"),
            "auth_token": os.getenv("TWILIO_TOKEN"),
            "from_number": os.getenv("TWILIO_FROM_NUMBER")
        }
    
    # Chat providers
    if os.getenv("SLACK_WEBHOOK_URL"):
        config["chat_providers"]["slack"] = {
            "webhook_url": os.getenv("SLACK_WEBHOOK_URL")
        }
    
    return config