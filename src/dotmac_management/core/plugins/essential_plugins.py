"""
Essential plugins initialization for the management platform.
"""

import logging
from typing import Any

from config import settings
from plugins.deployment.aws_plugin import AWSDeploymentPlugin
from plugins.monitoring.prometheus_plugin import PrometheusMonitoringPlugin
from plugins.notifications.email_plugin import EmailNotificationPlugin
from plugins.notifications.slack_plugin import SlackNotificationPlugin
from plugins.notifications.webhook_plugin import WebhookNotificationPlugin

from .registry import plugin_registry

logger = logging.getLogger(__name__)


async def initialize_essential_plugins() -> dict[str, bool]:
    """Initialize the 5 implemented plugins for platform functionality."""

    results = {}

    try:
        # 1. Initialize Email Notification Plugin
        email_config = {
            "smtp_host": getattr(settings, "SMTP_HOST", "localhost"),
            "smtp_port": getattr(settings, "SMTP_PORT", 587),
            "smtp_username": getattr(settings, "SMTP_USERNAME", ""),
            "smtp_password": getattr(settings, "SMTP_PASSWORD", ""),
            "use_tls": getattr(settings, "SMTP_USE_TLS", True),
            "from_email": getattr(settings, "SMTP_FROM_EMAIL", "noreply@dotmac.com"),
            "from_name": getattr(settings, "SMTP_FROM_NAME", "DotMac Platform"),
        }

        email_plugin = EmailNotificationPlugin()
        email_plugin.config = email_config
        email_result = await plugin_registry.register_plugin(email_plugin)
        results["email_notification"] = email_result

        if email_result:
            logger.info("✅ EmailNotificationPlugin registered successfully")
        else:
            logger.error("❌ Failed to register EmailNotificationPlugin")

        # 2. Initialize Webhook Notification Plugin
        webhook_config = {
            "webhook_url": getattr(settings, "DEFAULT_WEBHOOK_URL", "http://localhost:3000/webhooks"),
            "http_method": "POST",
            "headers": {"Content-Type": "application/json"},
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 5,
            "verify_ssl": True,
        }

        # Add auth header if configured
        webhook_auth = getattr(settings, "WEBHOOK_AUTH_HEADER", None)
        if webhook_auth:
            webhook_config["auth_header"] = webhook_auth

        webhook_plugin = WebhookNotificationPlugin()
        webhook_plugin.config = webhook_config
        webhook_result = await plugin_registry.register_plugin(webhook_plugin)
        results["webhook_notification"] = webhook_result

        if webhook_result:
            logger.info("✅ WebhookNotificationPlugin registered successfully")
        else:
            logger.error("❌ Failed to register WebhookNotificationPlugin")

        # 3. Initialize AWS Deployment Plugin
        aws_config = {
            "aws_access_key_id": getattr(settings, "AWS_ACCESS_KEY_ID", ""),
            "aws_secret_access_key": getattr(settings, "AWS_SECRET_ACCESS_KEY", ""),
            "default_region": getattr(settings, "AWS_DEFAULT_REGION", "us-east-1"),
            "vpc_cidr": getattr(settings, "AWS_VPC_CIDR", "10.0.0.0/16"),
            "subnet_cidr": getattr(settings, "AWS_SUBNET_CIDR", "10.0.1.0/24"),
            "instance_type": getattr(settings, "AWS_INSTANCE_TYPE", "t3.medium"),
            "key_pair_name": getattr(settings, "AWS_KEY_PAIR_NAME", None),
            "security_group_rules": getattr(settings, "AWS_SECURITY_GROUP_RULES", []),
        }

        aws_plugin = AWSDeploymentPlugin()
        aws_plugin.config = aws_config
        aws_result = await plugin_registry.register_plugin(aws_plugin)
        results["aws_deployment"] = aws_result

        if aws_result:
            logger.info("✅ AWSDeploymentPlugin registered successfully")
        else:
            logger.error("❌ Failed to register AWSDeploymentPlugin")

        # 4. Initialize Slack Notification Plugin
        slack_config = {
            "webhook_url": getattr(settings, "SLACK_WEBHOOK_URL", ""),
            "default_channel": getattr(settings, "SLACK_DEFAULT_CHANNEL", "#alerts"),
            "username": getattr(settings, "SLACK_USERNAME", "DotMac Platform"),
            "icon_emoji": getattr(settings, "SLACK_ICON_EMOJI", ":robot_face:"),
            "mention_users": getattr(settings, "SLACK_MENTION_USERS", []),
            "thread_replies": getattr(settings, "SLACK_THREAD_REPLIES", False),
        }

        # Only initialize if Slack webhook is configured
        if slack_config["webhook_url"]:
            slack_plugin = SlackNotificationPlugin()
            slack_plugin.config = slack_config
            slack_result = await plugin_registry.register_plugin(slack_plugin)
            results["slack_notification"] = slack_result

            if slack_result:
                logger.info("✅ SlackNotificationPlugin registered successfully")
            else:
                logger.error("❌ Failed to register SlackNotificationPlugin")
        else:
            results["slack_notification"] = False
            logger.info("⚠️ SlackNotificationPlugin skipped - no webhook URL configured")

        # 5. Initialize Prometheus Monitoring Plugin (deprecated)
        prometheus_config = {
            "prometheus_url": getattr(settings, "PROMETHEUS_URL", ""),
            "alertmanager_url": getattr(settings, "PROMETHEUS_ALERTMANAGER_URL", ""),
            "default_scrape_interval": getattr(settings, "PROMETHEUS_SCRAPE_INTERVAL", "15s"),
            "query_timeout": getattr(settings, "PROMETHEUS_QUERY_TIMEOUT", 30),
            "basic_auth_username": getattr(settings, "PROMETHEUS_AUTH_USERNAME", ""),
            "basic_auth_password": getattr(settings, "PROMETHEUS_AUTH_PASSWORD", ""),
        }

        # Deprecated: prefer SigNoz/OTLP stack
        results["prometheus_monitoring"] = False
        logger.info("ℹ️ PrometheusMonitoringPlugin disabled (SigNoz-only stack)")

        # Log summary
        successful_plugins = sum(1 for success in results.values() if success)
        total_plugins = len(results)

        logger.info(f"Plugin initialization complete: {successful_plugins}/{total_plugins} successful")

        return results

    except (ImportError, OSError, RuntimeError):
        logger.exception("Failed to initialize essential plugins")
        return results


async def shutdown_essential_plugins() -> None:
    """Shutdown essential plugins gracefully."""
    try:
        essential_plugin_names = [
            "email_notification",
            "webhook_notification",
            "aws_deployment",
        ]

        for plugin_name in essential_plugin_names:
            try:
                await plugin_registry.unregister_plugin(plugin_name)
                logger.info(f"✅ Plugin {plugin_name} shutdown successfully")
            except (OSError, RuntimeError):
                logger.exception("❌ Failed to shutdown plugin %s", plugin_name)

        logger.info("Essential plugins shutdown complete")

    except (OSError, RuntimeError):
        logger.exception("Error during essential plugins shutdown")


def get_essential_plugin_status() -> dict[str, dict[str, Any]]:
    """Get status of essential plugins."""
    essential_plugin_names = [
        "email_notification",
        "webhook_notification",
        "aws_deployment",
    ]
    status = {}

    for plugin_name in essential_plugin_names:
        plugin = plugin_registry.get_plugin(plugin_name)
        if plugin:
            status[plugin_name] = {
                "registered": True,
                "status": plugin.status.value,
                "version": plugin.meta.version,
                "type": plugin.meta.plugin_type.value,
            }
        else:
            status[plugin_name] = {"registered": False, "status": "not_found"}

    return status
