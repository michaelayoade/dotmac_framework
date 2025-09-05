"""
Example usage of the DotMac Plugin System.

Demonstrates how to create plugins, configure the system, and use domain adapters.
"""

import asyncio
import logging

from ..adapters.communication import (
    CommunicationAdapter,
    CommunicationPlugin,
    Message,
    MessageResult,
    MessageStatus,
)
from ..core.manager import PluginManager
from ..core.plugin_base import BasePlugin, PluginMetadata
from ..middleware.metrics import MetricsMiddleware
from ..middleware.rate_limiting import RateLimit, RateLimitingMiddleware
from ..middleware.validation import (
    ValidationMiddleware,
    ValidationRule,
    ValidationSchema,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Example plugin implementations


class EmailPlugin(CommunicationPlugin):
    """Example email plugin implementation."""

    __plugin_name__ = "smtp_email"
    __plugin_version__ = "1.2.0"
    __plugin_domain__ = "communication"
    __plugin_description__ = "SMTP email sending plugin"
    __plugin_tags__ = ["email", "smtp", "communication"]
    __plugin_categories__ = ["messaging"]

    async def _initialize_plugin(self) -> None:
        """Initialize SMTP connection."""
        self.logger.info(f"Initializing SMTP email plugin with host: {self.config.get('smtp_host', 'localhost')}")
        # In real implementation, would establish SMTP connection

    async def _shutdown_plugin(self) -> None:
        """Shutdown SMTP connection."""
        self.logger.info("Shutting down SMTP email plugin")
        # In real implementation, would close SMTP connection

    async def send_message(self, message: Message) -> MessageResult:
        """Send email message via SMTP."""
        self.logger.info(f"Sending email to {message.recipient}: {message.subject}")

        # Simulate email sending
        await asyncio.sleep(0.1)  # Simulate network delay

        # In real implementation, would use smtplib or aiosmtplib
        return MessageResult(
            success=True,
            message_id=f"email_{hash(message.content)}",
            status=MessageStatus.SENT,
            sent_at="2024-01-01T12:00:00Z",
        )

    async def validate_recipient(self, recipient: str) -> bool:
        """Validate email address format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, recipient))

    def get_supported_message_types(self) -> list:
        return ["email", "html_email"]


class SMSPlugin(CommunicationPlugin):
    """Example SMS plugin implementation."""

    __plugin_name__ = "twilio_sms"
    __plugin_version__ = "1.0.0"
    __plugin_domain__ = "communication"
    __plugin_description__ = "Twilio SMS sending plugin"
    __plugin_tags__ = ["sms", "twilio", "mobile"]
    __plugin_categories__ = ["messaging"]

    async def _initialize_plugin(self) -> None:
        """Initialize Twilio client."""
        self.logger.info("Initializing Twilio SMS plugin")
        # In real implementation, would create Twilio client

    async def _shutdown_plugin(self) -> None:
        """Shutdown Twilio client."""
        self.logger.info("Shutting down Twilio SMS plugin")

    async def send_message(self, message: Message) -> MessageResult:
        """Send SMS message via Twilio."""
        self.logger.info(f"Sending SMS to {message.recipient}")

        # Simulate SMS sending
        await asyncio.sleep(0.2)  # Simulate API call

        # In real implementation, would use Twilio API
        return MessageResult(
            success=True,
            message_id=f"sms_{hash(message.content)}",
            status=MessageStatus.DELIVERED,
            sent_at="2024-01-01T12:00:00Z",
        )

    async def validate_recipient(self, recipient: str) -> bool:
        """Validate phone number format."""
        import re

        # Basic phone number validation
        pattern = r"^\+?[1-9]\d{1,14}$"
        return bool(re.match(pattern, recipient))

    def get_supported_message_types(self) -> list:
        return ["sms", "text"]


class UtilityPlugin(BasePlugin):
    """Example utility plugin."""

    __plugin_name__ = "text_processor"
    __plugin_version__ = "1.0.0"
    __plugin_domain__ = "utilities"
    __plugin_description__ = "Text processing utilities"

    async def _initialize_plugin(self) -> None:
        """Initialize text processor."""
        self.logger.info("Initializing text processor plugin")

    async def _shutdown_plugin(self) -> None:
        """Shutdown text processor."""
        self.logger.info("Shutting down text processor plugin")

    async def process_text(self, text: str, operation: str = "uppercase") -> str:
        """Process text with specified operation."""
        operations = {
            "uppercase": text.upper,
            "lowercase": text.lower,
            "reverse": lambda x: x[::-1],
            "title": text.title,
        }

        if operation not in operations:
            raise ValueError(f"Unsupported operation: {operation}")

        result = operations[operation]()
        self.logger.debug(f"Processed text: {operation}({text}) -> {result}")
        return result

    async def count_words(self, text: str) -> int:
        """Count words in text."""
        word_count = len(text.split())
        self.logger.debug(f"Counted {word_count} words in text")
        return word_count


async def main():
    """Main example demonstrating plugin system usage."""

    logger.info("🚀 Starting DotMac Plugin System Example")

    # Create and initialize plugin manager
    async with PluginManager() as manager:
        # Configure middleware
        logger.info("📋 Configuring middleware...")

        # Validation middleware
        validation = ValidationMiddleware()
        email_schema = ValidationSchema(
            method_name="send_message",
            input_rules=[
                ValidationRule(
                    field_name="recipient",
                    field_type=str,
                    required=True,
                    pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    error_message="Invalid email address format",
                ),
                ValidationRule(
                    field_name="content",
                    field_type=str,
                    required=True,
                    min_length=1,
                    max_length=10000,
                ),
            ],
        )
        validation.add_validation_schema("communication.smtp_email", email_schema)
        manager.add_middleware(validation)

        # Rate limiting middleware
        rate_limiting = RateLimitingMiddleware()
        conservative_limit = RateLimit(max_requests=10, time_window=60)  # 10 per minute
        rate_limiting.add_plugin_rate_limit("communication.smtp_email", conservative_limit)
        manager.add_middleware(rate_limiting)

        # Metrics middleware
        metrics = MetricsMiddleware()
        manager.add_middleware(metrics)

        # Create plugin instances
        logger.info("🔌 Creating and registering plugins...")

        email_config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "use_tls": True,
            "username": "user@example.com",
            "password": "secret",
        }

        sms_config = {
            "account_sid": "AC_test_sid",
            "auth_token": "test_token",
            "from_number": "+1234567890",
        }

        # Register plugins
        email_metadata = PluginMetadata(
            name="smtp_email",
            version="1.2.0",
            domain="communication",
            description="SMTP email sending plugin",
            tags={"email", "smtp"},
            categories={"messaging"},
        )
        email_plugin = EmailPlugin(email_metadata, email_config)
        await manager.register_plugin(email_plugin)

        sms_metadata = PluginMetadata(
            name="twilio_sms",
            version="1.0.0",
            domain="communication",
            description="Twilio SMS plugin",
            tags={"sms", "twilio"},
            categories={"messaging"},
        )
        sms_plugin = SMSPlugin(sms_metadata, sms_config)
        await manager.register_plugin(sms_plugin)

        utility_metadata = PluginMetadata(name="text_processor", version="1.0.0", domain="utilities")
        utility_plugin = UtilityPlugin(utility_metadata, {})
        await manager.register_plugin(utility_plugin)

        # Use communication adapter
        logger.info("📨 Setting up communication adapter...")
        comm_adapter = CommunicationAdapter()
        comm_adapter.register_plugin("email", email_plugin)
        comm_adapter.register_plugin("sms", sms_plugin)

        # Set default providers
        comm_adapter.set_default_provider("email", "email")
        comm_adapter.set_default_provider("sms", "sms")

        # Demonstrate plugin execution
        logger.info("⚡ Executing plugin operations...")

        # Send email using adapter
        email_message = Message(
            recipient="user@example.com",
            content="Hello from the DotMac Plugin System!",
            subject="Plugin System Demo",
            message_type="email",
        )

        email_result = await comm_adapter.send_message(email_message)
        logger.info(f"📧 Email result: {email_result.success} - {email_result.message_id}")

        # Send SMS using adapter
        sms_message = Message(
            recipient="+1234567890",
            content="Plugin system working great!",
            message_type="sms",
        )

        sms_result = await comm_adapter.send_message(sms_message)
        logger.info(f"📱 SMS result: {sms_result.success} - {sms_result.message_id}")

        # Use utility plugin directly
        text_result = await manager.execute_plugin(
            "utilities", "text_processor", "process_text", "hello world", "title"
        )
        logger.info(f"🔤 Text processing result: {text_result}")

        word_count = await manager.execute_plugin(
            "utilities", "text_processor", "count_words", "This is a test message"
        )
        logger.info(f"🔢 Word count result: {word_count}")

        # Demonstrate bulk messaging
        logger.info("📬 Sending bulk messages...")

        bulk_messages = [Message(f"user{i}@example.com", f"Bulk message {i}", "Bulk Test", "email") for i in range(5)]

        bulk_result = await comm_adapter.send_bulk_messages(bulk_messages)
        logger.info(f"📦 Bulk result: {bulk_result.successful}/{bulk_result.total_messages} successful")

        # Show system health
        logger.info("🏥 Checking system health...")
        system_health = await manager.get_system_health()
        logger.info(
            f"💚 System health: {system_health['plugins']['healthy_plugins']}/{system_health['plugins']['total_plugins']} plugins healthy"
        )

        # Show communication adapter health
        comm_health = await comm_adapter.health_check()
        logger.info(
            f"📡 Communication health: {comm_health['health_percentage']:.1f}.format({comm_health['healthy_providers']}/{comm_health['total_providers']})"
        )

        # Show metrics
        logger.info("📊 System metrics:")
        plugin_executions = metrics.get_metric_value("plugin_executions_total") or 0
        logger.info(f"   Total plugin executions: {plugin_executions}")

        execution_stats = metrics.get_metric_stats("plugin_execution_time")
        if execution_stats:
            logger.info(f"   Average execution time: {execution_stats['mean']:.3f}s")
            logger.info(f"   P95 execution time: {execution_stats['p95']:.3f}s")

        # Show plugin discovery
        logger.info("🔍 Plugin discovery:")
        all_plugins = await manager.list_plugins()
        for plugin in all_plugins:
            logger.info(f"   {plugin.domain}.{plugin.name} v{plugin.version} - {plugin.status.value}")

        communication_plugins = await manager.find_plugins(domain="communication")
        logger.info(f"📞 Communication plugins: {len(communication_plugins)}")

        # Show available domains
        domains = await manager.get_available_domains()
        logger.info(f"🏢 Available domains: {', '.join(domains)}")

        logger.info("✅ Plugin system example completed successfully!")


async def yaml_config_example():
    """Example using YAML configuration to load plugins."""

    logger.info("📄 YAML Configuration Example")

    # Create sample YAML config
    yaml_config = """
plugins:
  - name: file_logger
    version: "1.0.0"
    domain: logging
    description: "File-based logging plugin"
    module: "examples.sample_plugins"
    class: "FileLoggerPlugin"

    config:
      log_file: "/var/log/myapp.log"
      log_level: "INFO"
      max_size: 1048576  # 1MB

    tags:
      - logging
      - files
    categories:
      - utilities

  - name: memory_cache
    version: "2.0.0"
    domain: caching
    description: "In-memory caching plugin"
    module: "examples.sample_plugins"
    class: "MemoryCachePlugin"

    config:
      max_size: 1000
      ttl: 3600  # 1 hour

    dependencies: []
    optional_dependencies:
      - "logging.file_logger"

    tags:
      - cache
      - memory
    categories:
      - performance

settings:
  default_timeout: 30.0
  health_check_interval: 60.0
  enable_health_monitoring: true
"""

    # Save to temporary file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_config)
        config_file = f.name

    try:
        # Load plugins from YAML config
        async with PluginManager():
            logger.info(f"Loading plugins from config: {config_file}")

            # This would load plugins if the classes existed
            # results = await manager.load_plugins_from_config(config_file)
            # logger.info(f"Loaded {sum(results.values())} plugins from config")

            logger.info("YAML config structure demonstrated (plugins would load if classes existed)")

    finally:
        # Clean up temp file
        import os

        os.unlink(config_file)


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())

    # Run YAML example
    asyncio.run(yaml_config_example())
