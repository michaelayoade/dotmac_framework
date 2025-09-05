"""
Plugin interfaces for extending management platform services.
"""

from abc import abstractmethod
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from .base import BasePlugin, BillablePlugin, PluginMeta, PluginType, TenantAwarePlugin


class MonitoringProviderPlugin(BasePlugin):
    """Interface for monitoring and alerting provider plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.MONITORING_PROVIDER,
            description="Monitoring provider plugin",
            author="DotMac",
        )

    @abstractmethod
    async def send_alert(self, alert_data: dict[str, Any], channel_config: dict[str, Any]) -> bool:
        """Send alert via this monitoring provider."""
        pass

    @abstractmethod
    async def collect_metrics(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Collect metrics from external monitoring system."""
        pass

    @abstractmethod
    async def execute_health_check(self, target_config: dict[str, Any]) -> dict[str, Any]:
        """Execute health check against target system."""
        pass

    @abstractmethod
    async def create_dashboard(self, dashboard_config: dict[str, Any]) -> str:
        """Create monitoring dashboard. Return dashboard ID."""
        pass

    @abstractmethod
    def get_supported_channels(self) -> list[str]:
        """Return list of supported alert channels."""
        pass


class DeploymentProviderPlugin(TenantAwarePlugin):
    """Interface for deployment and infrastructure provider plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.DEPLOYMENT_PROVIDER,
            description="Deployment provider plugin",
            author="DotMac",
        )

    @abstractmethod
    async def provision_infrastructure(self, infrastructure_config: dict[str, Any]) -> dict[str, Any]:
        """Provision infrastructure. Return infrastructure details."""
        pass

    @abstractmethod
    async def deploy_application(self, app_config: dict[str, Any], infrastructure_id: str) -> dict[str, Any]:
        """Deploy application to infrastructure. Return deployment details."""
        pass

    @abstractmethod
    async def scale_application(self, deployment_id: str, scaling_config: dict[str, Any]) -> bool:
        """Scale deployed application."""
        pass

    @abstractmethod
    async def rollback_deployment(self, deployment_id: str, target_version: str) -> bool:
        """Rollback deployment to previous version."""
        pass

    @abstractmethod
    async def validate_template(self, template_content: dict[str, Any], template_type: str) -> bool:
        """Validate deployment template format."""
        pass

    @abstractmethod
    async def get_deployment_status(self, deployment_id: str) -> dict[str, Any]:
        """Get current deployment status and health."""
        pass

    @abstractmethod
    async def calculate_deployment_cost(self, deployment_config: dict[str, Any]) -> Decimal:
        """Calculate estimated deployment cost."""
        pass

    @abstractmethod
    def get_supported_providers(self) -> list[str]:
        """Return list of supported cloud/infrastructure providers."""
        pass

    @abstractmethod
    def get_supported_orchestrators(self) -> list[str]:
        """Return list of supported orchestration platforms."""
        pass

    async def calculate_infrastructure_cost(self, infrastructure_config: dict[str, Any]) -> float:
        """Calculate monthly infrastructure cost. Optional method."""
        return 0.0


class NotificationChannelPlugin(BasePlugin):
    """Interface for notification delivery channel plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.NOTIFICATION_CHANNEL,
            description="Notification channel plugin",
            author="DotMac",
        )

    @abstractmethod
    async def send_notification(
        self, message: str, recipients: list[str], options: Optional[dict[str, Any]] = None
    ) -> bool:
        """Send notification via this channel."""
        pass

    @abstractmethod
    async def send_alert(self, alert_data: dict[str, Any], recipients: list[str]) -> bool:
        """Send alert notification."""
        pass

    @abstractmethod
    async def send_digest(self, digest_data: dict[str, Any], recipients: list[str]) -> bool:
        """Send digest notification."""
        pass

    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient format for this channel."""
        pass

    @abstractmethod
    def get_channel_type(self) -> str:
        """Return channel identifier (email, slack, sms, etc)."""
        pass

    @abstractmethod
    def get_supported_message_types(self) -> list[str]:
        """Return supported message types (text, html, markdown, etc)."""
        pass


class PaymentProviderPlugin(BillablePlugin):
    """Interface for payment processing provider plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.PAYMENT_PROVIDER,
            description="Payment provider plugin",
            author="DotMac",
            requires_license=True,
        )

    @abstractmethod
    async def process_payment(
        self,
        amount: Decimal,
        payment_method: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Process payment. Return transaction details."""
        pass

    @abstractmethod
    async def create_subscription(self, plan_config: dict[str, Any], customer_data: dict[str, Any]) -> str:
        """Create subscription. Return subscription ID."""
        pass

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str, reason: Optional[str] = None) -> bool:
        """Cancel subscription."""
        pass

    @abstractmethod
    async def handle_webhook(self, event_data: dict[str, Any]) -> bool:
        """Handle provider webhook events."""
        pass

    @abstractmethod
    async def refund_payment(
        self, transaction_id: str, amount: Decimal, reason: Optional[str] = None
    ) -> dict[str, Any]:
        """Process refund. Return refund details."""
        pass

    @abstractmethod
    def get_supported_currencies(self) -> list[str]:
        """Return supported currency codes."""
        pass

    @abstractmethod
    def get_supported_payment_methods(self) -> list[str]:
        """Return supported payment methods."""
        pass


class BillingCalculatorPlugin(BillablePlugin):
    """Interface for custom billing calculation plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.BILLING_CALCULATOR,
            description="Billing calculator plugin",
            author="DotMac",
            requires_license=True,
        )

    @abstractmethod
    async def calculate_usage_cost(self, usage_data: list[dict[str, Any]], billing_plan: dict[str, Any]) -> Decimal:
        """Calculate cost based on usage data and billing plan."""
        pass

    @abstractmethod
    async def calculate_tax(self, amount: Decimal, tax_config: dict[str, Any]) -> Decimal:
        """Calculate tax amount."""
        pass

    @abstractmethod
    async def calculate_commission(
        self, transaction_data: dict[str, Any], commission_config: dict[str, Any]
    ) -> Decimal:
        """Calculate commission for resellers."""
        pass

    @abstractmethod
    async def apply_discounts(self, amount: Decimal, discount_rules: list[dict[str, Any]]) -> Decimal:
        """Apply discount rules to amount."""
        pass

    @abstractmethod
    def get_supported_billing_models(self) -> list[str]:
        """Return supported billing models (flat_rate, usage_based, tiered, etc)."""
        pass


class SecurityScannerPlugin(BasePlugin):
    """Interface for security scanning plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.SECURITY_SCANNER,
            description="Security scanner plugin",
            author="DotMac",
        )

    @abstractmethod
    async def scan_plugin_code(self, plugin_path: str) -> dict[str, Any]:
        """Scan plugin code for security vulnerabilities."""
        pass

    @abstractmethod
    async def scan_dependencies(self, dependencies: list[str]) -> dict[str, Any]:
        """Scan plugin dependencies for vulnerabilities."""
        pass

    @abstractmethod
    async def validate_plugin_permissions(self, plugin_config: dict[str, Any]) -> bool:
        """Validate plugin requested permissions."""
        pass

    @abstractmethod
    def get_supported_scan_types(self) -> list[str]:
        """Return supported scan types."""
        pass


class BackupProviderPlugin(TenantAwarePlugin):
    """Interface for backup and disaster recovery plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.BACKUP_PROVIDER,
            description="Backup provider plugin",
            author="DotMac",
        )

    @abstractmethod
    async def create_backup(self, backup_config: dict[str, Any]) -> str:
        """Create backup. Return backup ID."""
        pass

    @abstractmethod
    async def restore_backup(self, backup_id: str, restore_config: dict[str, Any]) -> bool:
        """Restore from backup."""
        pass

    @abstractmethod
    async def list_backups(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """List available backups for tenant."""
        pass

    @abstractmethod
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete backup."""
        pass

    @abstractmethod
    async def test_restore(self, backup_id: str) -> dict[str, Any]:
        """Test restore process without actually restoring."""
        pass

    @abstractmethod
    def get_supported_backup_types(self) -> list[str]:
        """Return supported backup types (database, filesystem, application, etc)."""
        pass


class AnalyticsProviderPlugin(TenantAwarePlugin):
    """Interface for analytics and reporting plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.ANALYTICS_PROVIDER,
            description="Analytics provider plugin",
            author="DotMac",
        )

    @abstractmethod
    async def generate_report(self, report_config: dict[str, Any]) -> dict[str, Any]:
        """Generate analytics report."""
        pass

    @abstractmethod
    async def track_event(self, event_name: str, properties: dict[str, Any], tenant_id: UUID) -> bool:
        """Track analytics event."""
        pass

    @abstractmethod
    async def get_tenant_analytics(self, tenant_id: UUID, time_range: str) -> dict[str, Any]:
        """Get analytics data for tenant."""
        pass

    @abstractmethod
    def get_supported_report_types(self) -> list[str]:
        """Return supported report types."""
        pass


class DNSProviderPlugin(BasePlugin):
    """Interface for DNS management and validation provider plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.DNS_PROVIDER,
            description="DNS provider plugin",
            author="DotMac",
        )

    @abstractmethod
    async def validate_subdomain_available(self, subdomain: str, base_domain: str) -> dict[str, Any]:
        """Check if a subdomain is available for provisioning."""
        pass

    @abstractmethod
    async def validate_ssl_certificate(self, domain: str) -> dict[str, Any]:
        """Validate SSL certificate for domain."""
        pass

    @abstractmethod
    async def create_dns_record(self, domain: str, record_type: str, value: str, ttl: int = 300) -> dict[str, Any]:
        """Create DNS record."""
        pass

    @abstractmethod
    async def delete_dns_record(self, domain: str, record_id: str) -> bool:
        """Delete DNS record."""
        pass

    @abstractmethod
    async def check_dns_propagation(self, domain: str, expected_value: str) -> dict[str, Any]:
        """Check DNS propagation status."""
        pass

    @abstractmethod
    async def get_ssl_certificate_info(self, domain: str) -> dict[str, Any]:
        """Get SSL certificate information."""
        pass

    @abstractmethod
    def get_supported_record_types(self) -> list[str]:
        """Return supported DNS record types."""
        pass


class InfrastructureProviderPlugin(BasePlugin):
    """Base interface for general infrastructure provider plugins."""

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.INFRASTRUCTURE_PROVIDER,
            description="Infrastructure provider plugin",
            author="DotMac",
        )

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check infrastructure provider health."""
        pass

    @abstractmethod
    async def get_provider_info(self) -> dict[str, Any]:
        """Get infrastructure provider information."""
        pass

    @abstractmethod
    async def validate_configuration(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate provider configuration."""
        pass

    @abstractmethod
    def get_supported_services(self) -> list[str]:
        """Return list of supported services."""
        pass
