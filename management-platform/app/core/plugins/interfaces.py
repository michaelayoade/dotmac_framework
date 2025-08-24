"""
Plugin interfaces for extending management platform services.
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal

from .base import BasePlugin, TenantAwarePlugin, BillablePlugin, PluginMeta, PluginType


class MonitoringProviderPlugin(BasePlugin):
    """Interface for monitoring and alerting provider plugins."""
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.MONITORING_PROVIDER,
            description="Monitoring provider plugin",
            author="DotMac"
        )
    
    @abstractmethod
    async def send_alert(self, alert_data: Dict[str, Any], channel_config: Dict[str, Any]) -> bool:
        """Send alert via this monitoring provider."""
        pass
    
    @abstractmethod
    async def collect_metrics(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect metrics from external monitoring system."""
        pass
    
    @abstractmethod
    async def execute_health_check(self, target_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute health check against target system."""
        pass
    
    @abstractmethod
    async def create_dashboard(self, dashboard_config: Dict[str, Any]) -> str:
        """Create monitoring dashboard. Return dashboard ID."""
        pass
    
    @abstractmethod
    def get_supported_channels(self) -> List[str]:
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
            author="DotMac"
        )
    
    @abstractmethod
    async def provision_infrastructure(self, infrastructure_config: Dict[str, Any]) -> Dict[str, Any]:
        """Provision infrastructure. Return infrastructure details."""
        pass
    
    @abstractmethod
    async def deploy_application(self, app_config: Dict[str, Any], infrastructure_id: str) -> Dict[str, Any]:
        """Deploy application to infrastructure. Return deployment details."""
        pass
    
    @abstractmethod
    async def scale_application(self, deployment_id: str, scaling_config: Dict[str, Any]) -> bool:
        """Scale deployed application."""
        pass
    
    @abstractmethod
    async def rollback_deployment(self, deployment_id: str, target_version: str) -> bool:
        """Rollback deployment to previous version."""
        pass
    
    @abstractmethod
    async def validate_template(self, template_content: Dict[str, Any], template_type: str) -> bool:
        """Validate deployment template format."""
        pass
    
    @abstractmethod
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get current deployment status and health."""
        pass
    
    @abstractmethod
    async def calculate_deployment_cost(self, deployment_config: Dict[str, Any]) -> Decimal:
        """Calculate estimated deployment cost."""
        pass
    
    @abstractmethod
    def get_supported_providers(self) -> List[str]:
        """Return list of supported cloud/infrastructure providers."""
        pass
    
    @abstractmethod
    def get_supported_orchestrators(self) -> List[str]:
        """Return list of supported orchestration platforms."""
        pass
    
    async def calculate_infrastructure_cost(self, infrastructure_config: Dict[str, Any]) -> float:
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
            author="DotMac"
        )
    
    @abstractmethod
    async def send_notification(self, message: str, recipients: List[str], options: Dict[str, Any] = None) -> bool:
        """Send notification via this channel."""
        pass
    
    @abstractmethod
    async def send_alert(self, alert_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send alert notification."""
        pass
    
    @abstractmethod
    async def send_digest(self, digest_data: Dict[str, Any], recipients: List[str]) -> bool:
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
    def get_supported_message_types(self) -> List[str]:
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
            requires_license=True
        )
    
    @abstractmethod
    async def process_payment(self, amount: Decimal, payment_method: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process payment. Return transaction details."""
        pass
    
    @abstractmethod
    async def create_subscription(self, plan_config: Dict[str, Any], customer_data: Dict[str, Any]) -> str:
        """Create subscription. Return subscription ID."""
        pass
    
    @abstractmethod
    async def cancel_subscription(self, subscription_id: str, reason: str = None) -> bool:
        """Cancel subscription."""
        pass
    
    @abstractmethod
    async def handle_webhook(self, event_data: Dict[str, Any]) -> bool:
        """Handle provider webhook events."""
        pass
    
    @abstractmethod
    async def refund_payment(self, transaction_id: str, amount: Decimal, reason: str = None) -> Dict[str, Any]:
        """Process refund. Return refund details."""
        pass
    
    @abstractmethod
    def get_supported_currencies(self) -> List[str]:
        """Return supported currency codes."""
        pass
    
    @abstractmethod
    def get_supported_payment_methods(self) -> List[str]:
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
            requires_license=True
        )
    
    @abstractmethod
    async def calculate_usage_cost(self, usage_data: List[Dict[str, Any]], billing_plan: Dict[str, Any]) -> Decimal:
        """Calculate cost based on usage data and billing plan."""
        pass
    
    @abstractmethod
    async def calculate_tax(self, amount: Decimal, tax_config: Dict[str, Any]) -> Decimal:
        """Calculate tax amount."""
        pass
    
    @abstractmethod
    async def calculate_commission(self, transaction_data: Dict[str, Any], commission_config: Dict[str, Any]) -> Decimal:
        """Calculate commission for resellers."""
        pass
    
    @abstractmethod
    async def apply_discounts(self, amount: Decimal, discount_rules: List[Dict[str, Any]]) -> Decimal:
        """Apply discount rules to amount."""
        pass
    
    @abstractmethod
    def get_supported_billing_models(self) -> List[str]:
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
            author="DotMac"
        )
    
    @abstractmethod
    async def scan_plugin_code(self, plugin_path: str) -> Dict[str, Any]:
        """Scan plugin code for security vulnerabilities."""
        pass
    
    @abstractmethod
    async def scan_dependencies(self, dependencies: List[str]) -> Dict[str, Any]:
        """Scan plugin dependencies for vulnerabilities."""
        pass
    
    @abstractmethod
    async def validate_plugin_permissions(self, plugin_config: Dict[str, Any]) -> bool:
        """Validate plugin requested permissions."""
        pass
    
    @abstractmethod
    def get_supported_scan_types(self) -> List[str]:
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
            author="DotMac"
        )
    
    @abstractmethod
    async def create_backup(self, backup_config: Dict[str, Any]) -> str:
        """Create backup. Return backup ID."""
        pass
    
    @abstractmethod
    async def restore_backup(self, backup_id: str, restore_config: Dict[str, Any]) -> bool:
        """Restore from backup."""
        pass
    
    @abstractmethod
    async def list_backups(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """List available backups for tenant."""
        pass
    
    @abstractmethod
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete backup."""
        pass
    
    @abstractmethod
    async def test_restore(self, backup_id: str) -> Dict[str, Any]:
        """Test restore process without actually restoring."""
        pass
    
    @abstractmethod
    def get_supported_backup_types(self) -> List[str]:
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
            author="DotMac"
        )
    
    @abstractmethod
    async def generate_report(self, report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytics report."""
        pass
    
    @abstractmethod
    async def track_event(self, event_name: str, properties: Dict[str, Any], tenant_id: UUID) -> bool:
        """Track analytics event."""
        pass
    
    @abstractmethod
    async def get_tenant_analytics(self, tenant_id: UUID, time_range: str) -> Dict[str, Any]:
        """Get analytics data for tenant."""
        pass
    
    @abstractmethod
    def get_supported_report_types(self) -> List[str]:
        """Return supported report types."""
        pass