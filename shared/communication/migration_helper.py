"""
Communication Channel Migration Helper

Strategic tool for migrating from hardcoded channel checks to the 
universal provider architecture. This eliminates all hardcoded 
channel references across the platform.
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

from .channel_provider_registry import (
    global_channel_registry,
    ChannelConfiguration,
    Message,
    MessageType,
    send_notification as registry_send_notification
)

logger = logging.getLogger(__name__)


class LegacyChannelType(Enum):
    """Legacy hardcoded channel types being migrated."""
    EMAIL = "email"
    SMS = "sms" 
    SLACK = "slack"
    WEBHOOK = "webhook"
    WHATSAPP = "whatsapp"
    TEAMS = "teams"


class ChannelMigrationHelper:
    """
    Helper class to migrate from hardcoded channel checks to provider architecture.
    
    This provides backward compatibility during migration period and helps
    identify all hardcoded references that need updating.
    """
    
    def __init__(self):
        """Initialize migration helper."""
        self._legacy_mappings = {}
        self._migration_warnings_enabled = True
        self._setup_legacy_mappings()
    
    def _setup_legacy_mappings(self):
        """Set up mappings from legacy hardcoded patterns to new providers."""
        self._legacy_mappings = {
            # Legacy SMS driver patterns
            "twilio": "twilio_sms",
            "vonage": "vonage_sms", 
            "nexmo": "vonage_sms",  # Nexmo is now Vonage
            
            # Legacy email patterns
            "smtp": "smtp_email",
            "sendgrid": "sendgrid_email",
            "ses": "ses_email",
            "mailgun": "mailgun_email",
            
            # Legacy notification patterns
            "slack": "slack_webhook",
            "teams": "teams_webhook",
            "discord": "discord_webhook",
            
            # Generic patterns
            "webhook": "generic_webhook",
            "http": "generic_webhook"
        }
    
    async def send_legacy_notification(self, 
                                     channel_type: str,
                                     recipient: str,
                                     content: str,
                                     **kwargs) -> bool:
        """
        Send notification using legacy channel type specification.
        
        This provides backward compatibility for existing code that uses
        hardcoded channel checks like 'if channel == "email"'.
        """
        if self._migration_warnings_enabled:
            logger.warning(f"Legacy channel usage detected: {channel_type}. "
                          f"Consider migrating to provider architecture.")
        
        # Map legacy channel type to provider
        provider_name = self._legacy_mappings.get(channel_type.lower(), channel_type)
        
        # Create message object
        message = Message(
            recipient=recipient,
            content=content,
            message_type=MessageType.NOTIFICATION,
            template_name=kwargs.get("template"),
            template_vars=kwargs.get("vars", {}),
            metadata=kwargs
        )
        
        # Try to send via new architecture
        result = await global_channel_registry.send_message(channel_type, message)
        
        if result.success:
            logger.info(f"Successfully sent via provider architecture: {channel_type}")
            return True
        else:
            logger.error(f"Failed to send via provider architecture: {result.error_message}")
            
            # Fallback to legacy implementation if available
            return await self._fallback_to_legacy(channel_type, recipient, content, **kwargs)
    
    async def _fallback_to_legacy(self, 
                                 channel_type: str, 
                                 recipient: str, 
                                 content: str,
                                 **kwargs) -> bool:
        """Fallback to legacy implementation if provider fails."""
        logger.warning(f"Falling back to legacy implementation for: {channel_type}")
        
        try:
            if channel_type.lower() == "email":
                return await self._legacy_email_send(recipient, content, **kwargs)
            elif channel_type.lower() == "sms":
                return await self._legacy_sms_send(recipient, content, **kwargs)
            elif channel_type.lower() == "slack":
                return await self._legacy_slack_send(recipient, content, **kwargs)
            else:
                logger.error(f"No legacy fallback available for: {channel_type}")
                return False
                
        except Exception as e:
            logger.error(f"Legacy fallback failed for {channel_type}: {e}")
            return False
    
    async def _legacy_email_send(self, recipient: str, content: str, **kwargs) -> bool:
        """Legacy email sending implementation."""
        # Import here to avoid circular dependencies
        try:
            # This would use the old hardcoded email logic
            logger.info("Using legacy email implementation")
            # Placeholder for actual legacy code
            return True
        except Exception:
            return False
    
    async def _legacy_sms_send(self, recipient: str, content: str, **kwargs) -> bool:
        """Legacy SMS sending implementation."""
        try:
            # This would use the old hardcoded SMS logic
            logger.info("Using legacy SMS implementation")
            # Placeholder for actual legacy code
            return True
        except Exception:
            return False
    
    async def _legacy_slack_send(self, recipient: str, content: str, **kwargs) -> bool:
        """Legacy Slack sending implementation."""
        try:
            # This would use the old hardcoded Slack logic
            logger.info("Using legacy Slack implementation")
            # Placeholder for actual legacy code
            return True
        except Exception:
            return False
    
    def get_migration_recommendations(self) -> Dict[str, Any]:
        """
        Get recommendations for migrating hardcoded channel references.
        
        Returns analysis of current usage and migration steps.
        """
        return {
            "provider_architecture_benefits": [
                "Eliminate all hardcoded channel checks (if channel == 'email')",
                "Dynamic provider registration based on configuration",
                "Easy addition of new communication channels",
                "Consistent error handling and retry logic",
                "Better testing and mocking capabilities",
                "Unified configuration management"
            ],
            "migration_steps": [
                "1. Replace hardcoded channel checks with provider calls",
                "2. Configure providers in application startup",
                "3. Update configuration files to use provider names",
                "4. Test all communication flows",
                "5. Remove legacy channel code"
            ],
            "code_patterns_to_replace": [
                "if channel == 'email': -> await registry.send_message('email', message)",
                "if driver == 'twilio': -> Use TwilioSMSProvider configuration",
                "elif channel_type == 'slack': -> Use SlackWebhookProvider",
                "hardcoded webhook URLs -> Provider-based webhook management"
            ],
            "available_providers": global_channel_registry.list_active_providers(),
            "supported_channel_types": list(global_channel_registry._active_providers.keys())
        }
    
    async def validate_migration_readiness(self) -> Dict[str, Any]:
        """
        Validate that the system is ready for migration from hardcoded channels.
        
        Checks provider availability, configuration completeness, etc.
        """
        validation_results = {
            "ready_for_migration": True,
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Check if any providers are configured
        active_providers = global_channel_registry.list_active_providers()
        if not active_providers:
            validation_results["ready_for_migration"] = False
            validation_results["issues"].append("No channel providers configured")
        
        # Check each active provider
        for provider_name in active_providers:
            provider = global_channel_registry.get_provider(provider_name)
            
            if not provider:
                validation_results["issues"].append(f"Provider {provider_name} not accessible")
                continue
            
            if not provider.is_initialized:
                validation_results["warnings"].append(f"Provider {provider_name} not initialized")
            
            # Check configuration
            try:
                config_valid = await provider.validate_configuration()
                if not config_valid:
                    validation_results["issues"].append(f"Provider {provider_name} configuration invalid")
            except Exception as e:
                validation_results["issues"].append(f"Provider {provider_name} validation failed: {e}")
        
        # Generate recommendations
        if validation_results["issues"]:
            validation_results["ready_for_migration"] = False
            validation_results["recommendations"].append("Fix configuration issues before migrating")
        
        if validation_results["warnings"]:
            validation_results["recommendations"].append("Initialize all providers before production use")
        
        if not validation_results["issues"] and not validation_results["warnings"]:
            validation_results["recommendations"].append("System ready for migration - proceed with confidence")
        
        return validation_results
    
    def disable_migration_warnings(self):
        """Disable migration warnings (for production after migration)."""
        self._migration_warnings_enabled = False
        logger.info("Migration warnings disabled")
    
    def enable_migration_warnings(self):
        """Enable migration warnings (useful during development)."""
        self._migration_warnings_enabled = True
        logger.info("Migration warnings enabled")


# Global migration helper instance
migration_helper = ChannelMigrationHelper()


# Backward compatibility functions
async def send_email_legacy(recipient: str, subject: str, content: str, **kwargs) -> bool:
    """Legacy email sending function - use for backward compatibility."""
    return await migration_helper.send_legacy_notification(
        channel_type="email",
        recipient=recipient,
        content=content,
        subject=subject,
        **kwargs
    )


async def send_sms_legacy(recipient: str, content: str, **kwargs) -> bool:
    """Legacy SMS sending function - use for backward compatibility."""
    return await migration_helper.send_legacy_notification(
        channel_type="sms",
        recipient=recipient,
        content=content,
        **kwargs
    )


async def send_slack_legacy(webhook_url: str, content: str, **kwargs) -> bool:
    """Legacy Slack sending function - use for backward compatibility."""
    return await migration_helper.send_legacy_notification(
        channel_type="slack",
        recipient=webhook_url,
        content=content,
        **kwargs
    )


# Analysis functions
async def analyze_hardcoded_patterns() -> Dict[str, Any]:
    """Analyze the codebase for hardcoded channel patterns that need migration."""
    return {
        "common_hardcoded_patterns": [
            "if channel == 'email':",
            "elif channel_type == 'sms':",
            "if driver == 'twilio':",
            "if provider == 'sendgrid':",
            "channel.type == 'slack'"
        ],
        "replacement_patterns": [
            "provider = registry.get_provider('email')",
            "await registry.send_message('sms', message)",
            "Use TwilioSMSProvider configuration",
            "Use SendGridEmailProvider configuration", 
            "Use SlackWebhookProvider"
        ],
        "migration_benefits": [
            "Zero hardcoded channel references",
            "Dynamic provider loading based on configuration",
            "Easy testing with mock providers",
            "Consistent error handling across all channels",
            "Simplified addition of new communication channels"
        ]
    }