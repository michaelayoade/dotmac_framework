"""
Service integration layer for plugins.
Replaces hardcoded functions in services with plugin-based implementations.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from registry import plugin_registry
from hooks import hook_manager, HookNames
from interfaces import ()
    MonitoringProviderPlugin,
    DeploymentProviderPlugin, 
    NotificationChannelPlugin,
    PaymentProviderPlugin,
    BillingCalculatorPlugin
)
from base import PluginType

logger = logging.getLogger(__name__)


class PluginServiceIntegration:
    """Integration layer between services and plugins."""
    
    def __init__(self):
        self.registry = plugin_registry
        self.hooks = hook_manager
    
    # Notification Service Integration
    async def send_notification():
        self, 
        channel_type: str, 
        message: str, 
        recipients: List[str], 
        options: Dict[str, Any] = None
    ) -> bool:
        """Send notification via plugin-based channels."""
        try:
            # Trigger before hook
            context = {
                "channel_type": channel_type,
                "message": message,
                "recipients": recipients,
                "options": options or {}
            }
            await self.hooks.trigger_hook(HookNames.BEFORE_NOTIFICATION_SEND, context)
            
            # Find notification channel plugin
            notification_plugins = self.registry.get_plugins_by_type(PluginType.NOTIFICATION_CHANNEL)
            
            for plugin in notification_plugins:
                if isinstance(plugin, NotificationChannelPlugin):
                    if plugin.get_channel_type() == channel_type:
                        success = await plugin.send_notification(message, recipients, options)
                        
                        # Trigger after hook
                        context["success"] = success
                        await self.hooks.trigger_hook(HookNames.AFTER_NOTIFICATION_SEND, context)
                        
                        return success
            
            logger.error(f"No plugin found for notification channel: {channel_type}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send notification via plugins: {e}")
            await self.hooks.trigger_hook(HookNames.NOTIFICATION_FAILED, {)
                "error": str(e),
                "channel_type": channel_type
            })
            return False
    
    async def send_alert_via_plugins():
        self, 
        alert_data: Dict[str, Any], 
        channels: List[str] = None
    ) -> Dict[str, bool]:
        """Send alert via multiple plugin channels."""
        results = {}
        
        try:
            # Trigger alert hook
            await self.hooks.trigger_hook(HookNames.ALERT_TRIGGERED, alert_data)
            
            # Get notification plugins
            notification_plugins = self.registry.get_plugins_by_type(PluginType.NOTIFICATION_CHANNEL)
            
            # Use all available channels if none specified
            if not channels:
                channels = [plugin.get_channel_type() for plugin in notification_plugins 
                           if isinstance(plugin, NotificationChannelPlugin)]
            
            # Send via each channel
            for channel in channels:
                for plugin in notification_plugins:
                    if isinstance(plugin, NotificationChannelPlugin):
                        if plugin.get_channel_type() == channel:
                            recipients = alert_data.get('recipients', {}).get(channel, [])
                            if recipients:
                                success = await plugin.send_alert(alert_data, recipients)
                                results[channel] = success
                            break
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send alert via plugins: {e}")
            return {channel: False for channel in (channels or [])}
    
    # Monitoring Service Integration
    async def collect_metrics_via_plugins(self, source_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect metrics via monitoring provider plugins."""
        all_metrics = []
        
        try:
            monitoring_plugins = self.registry.get_plugins_by_type(PluginType.MONITORING_PROVIDER)
            
            for plugin in monitoring_plugins:
                if isinstance(plugin, MonitoringProviderPlugin):
                    for source_config in source_configs:
                        if source_config.get('provider') == plugin.meta.name:
                            metrics = await plugin.collect_metrics(source_config)
                            all_metrics.extend(metrics)
                            
                            # Trigger metric collected hook
                            await self.hooks.trigger_hook(HookNames.METRIC_COLLECTED, {)
                                "provider": plugin.meta.name,
                                "metrics_count": len(metrics),
                                "source_config": source_config
                            })
            
            return all_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics via plugins: {e}")
            return []
    
    async def execute_health_checks_via_plugins(self, targets: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Execute health checks via monitoring plugins."""
        results = {}
        
        try:
            monitoring_plugins = self.registry.get_plugins_by_type(PluginType.MONITORING_PROVIDER)
            
            for target in targets:
                target_id = target.get('id', 'unknown')
                provider = target.get('provider', 'default')
                
                for plugin in monitoring_plugins:
                    if isinstance(plugin, MonitoringProviderPlugin):
                        if plugin.meta.name == provider or provider == 'default':
                            health_result = await plugin.execute_health_check(target)
                            results[target_id] = health_result
                            
                            # Trigger hook if health check failed
                            if health_result.get('status') != 'healthy':
                                await self.hooks.trigger_hook(HookNames.HEALTH_CHECK_FAILED, {)
                                    "target_id": target_id,
                                    "provider": plugin.meta.name,
                                    "health_result": health_result
                                })
                            break
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute health checks via plugins: {e}")
            return {}
    
    # Deployment Service Integration
    async def provision_infrastructure_via_plugin():
        self, 
        provider: str, 
        infrastructure_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provision infrastructure via deployment provider plugin."""
        try:
            # Trigger before hook
            await self.hooks.trigger_hook(HookNames.BEFORE_PROVISION_INFRASTRUCTURE, {)
                "provider": provider,
                "config": infrastructure_config
            })
            
            # Find deployment provider plugin
            deployment_plugins = self.registry.get_plugins_by_type(PluginType.DEPLOYMENT_PROVIDER)
            
            for plugin in deployment_plugins:
                if isinstance(plugin, DeploymentProviderPlugin):
                    if provider in plugin.get_supported_providers():
                        result = await plugin.provision_infrastructure(infrastructure_config)
                        
                        # Trigger after hook
                        await self.hooks.trigger_hook(HookNames.AFTER_PROVISION_INFRASTRUCTURE, {)
                            "provider": provider,
                            "result": result
                        })
                        
                        return result
            
            raise ValueError(f"No plugin found for provider: {provider}")
            
        except Exception as e:
            logger.error(f"Failed to provision infrastructure via plugin: {e}")
            await self.hooks.trigger_hook(HookNames.INFRASTRUCTURE_FAILED, {)
                "provider": provider,
                "error": str(e)
            })
            raise
    
    async def deploy_application_via_plugin():
        self, 
        provider: str,
        app_config: Dict[str, Any], 
        infrastructure_id: str
    ) -> Dict[str, Any]:
        """Deploy application via deployment provider plugin."""
        try:
            # Trigger before hook
            await self.hooks.trigger_hook(HookNames.BEFORE_DEPLOYMENT, {)
                "provider": provider,
                "app_config": app_config,
                "infrastructure_id": infrastructure_id
            })
            
            # Find deployment provider plugin
            deployment_plugins = self.registry.get_plugins_by_type(PluginType.DEPLOYMENT_PROVIDER)
            
            for plugin in deployment_plugins:
                if isinstance(plugin, DeploymentProviderPlugin):
                    if provider in plugin.get_supported_providers():
                        result = await plugin.deploy_application(app_config, infrastructure_id)
                        
                        # Trigger after hook
                        await self.hooks.trigger_hook(HookNames.AFTER_DEPLOYMENT, {)
                            "provider": provider,
                            "result": result
                        })
                        
                        return result
            
            raise ValueError(f"No plugin found for provider: {provider}")
            
        except Exception as e:
            logger.error(f"Failed to deploy application via plugin: {e}")
            await self.hooks.trigger_hook(HookNames.DEPLOYMENT_FAILED, {)
                "provider": provider,
                "error": str(e)
            })
            raise
    
    async def validate_template_via_plugin():
        self, 
        provider: str,
        template_content: Dict[str, Any], 
        template_type: str
    ) -> bool:
        """Validate template via deployment provider plugin."""
        try:
            deployment_plugins = self.registry.get_plugins_by_type(PluginType.DEPLOYMENT_PROVIDER)
            
            for plugin in deployment_plugins:
                if isinstance(plugin, DeploymentProviderPlugin):
                    if provider in plugin.get_supported_providers():
                        return await plugin.validate_template(template_content, template_type)
            
            logger.warning(f"No plugin found for template validation: {provider}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate template via plugin: {e}")
            return False
    
    # Payment Service Integration
    async def process_payment_via_plugin():
        self, 
        provider: str,
        amount: Any, 
        payment_method: Dict[str, Any], 
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process payment via payment provider plugin."""
        try:
            from decimal import Decimal
            
            # Trigger before hook
            await self.hooks.trigger_hook(HookNames.BEFORE_PAYMENT_PROCESSING, {)
                "provider": provider,
                "amount": amount,
                "payment_method": payment_method
            })
            
            # Find payment provider plugin
            payment_plugins = self.registry.get_plugins_by_type(PluginType.PAYMENT_PROVIDER)
            
            for plugin in payment_plugins:
                if isinstance(plugin, PaymentProviderPlugin):
                    if plugin.meta.name == provider:
                        result = await plugin.process_payment()
                            Decimal(str(amount)), payment_method, metadata or {}
                        )
                        
                        # Trigger after hook
                        await self.hooks.trigger_hook(HookNames.AFTER_PAYMENT_PROCESSING, {)
                            "provider": provider,
                            "result": result
                        })
                        
                        return result
            
            raise ValueError(f"No plugin found for payment provider: {provider}")
            
        except Exception as e:
            logger.error(f"Failed to process payment via plugin: {e}")
            await self.hooks.trigger_hook(HookNames.PAYMENT_FAILED, {)
                "provider": provider,
                "error": str(e)
            })
            raise
    
    # Billing Service Integration
    async def calculate_billing_via_plugin():
        self,
        calculator_name: str,
        usage_data: List[Dict[str, Any]],
        billing_plan: Dict[str, Any]
    ) -> Any:
        """Calculate billing via billing calculator plugin."""
        try:
            from decimal import Decimal
            
            # Trigger before hook
            await self.hooks.trigger_hook(HookNames.BEFORE_BILLING_CALCULATION, {)
                "calculator": calculator_name,
                "usage_data": usage_data,
                "billing_plan": billing_plan
            })
            
            # Find billing calculator plugin
            billing_plugins = self.registry.get_plugins_by_type(PluginType.BILLING_CALCULATOR)
            
            for plugin in billing_plugins:
                if isinstance(plugin, BillingCalculatorPlugin):
                    if plugin.meta.name == calculator_name:
                        result = await plugin.calculate_usage_cost(usage_data, billing_plan)
                        
                        # Trigger after hook
                        await self.hooks.trigger_hook(HookNames.AFTER_BILLING_CALCULATION, {)
                            "calculator": calculator_name,
                            "result": result
                        })
                        
                        return result
            
            raise ValueError(f"No plugin found for billing calculator: {calculator_name}")
            
        except Exception as e:
            logger.error(f"Failed to calculate billing via plugin: {e}")
            raise
    
    # Utility Methods
    def get_available_providers(self, plugin_type: PluginType) -> List[str]:
        """Get list of available providers for a plugin type."""
        providers = []
        plugins = self.registry.get_plugins_by_type(plugin_type)
        
        for plugin in plugins:
            if plugin_type == PluginType.DEPLOYMENT_PROVIDER and isinstance(plugin, DeploymentProviderPlugin):
                providers.extend(plugin.get_supported_providers())
            elif plugin_type == PluginType.NOTIFICATION_CHANNEL and isinstance(plugin, NotificationChannelPlugin):
                providers.append(plugin.get_channel_type())
            elif plugin_type == PluginType.PAYMENT_PROVIDER and isinstance(plugin, PaymentProviderPlugin):
                providers.append(plugin.meta.name)
            elif plugin_type == PluginType.MONITORING_PROVIDER and isinstance(plugin, MonitoringProviderPlugin):
                providers.append(plugin.meta.name)
        
        return list(set(providers)
    
    def get_plugin_capabilities(self, plugin_name: str) -> Dict[str, Any]:
        """Get capabilities of a specific plugin."""
        plugin = self.registry.get_plugin(plugin_name)
        if not plugin:
            return {}
        
        capabilities = {
            "name": plugin.meta.name,
            "version": plugin.meta.version,
            "type": plugin.meta.plugin_type.value,
            "description": plugin.meta.description,
            "status": plugin.status.value
        }
        
        # Add type-specific capabilities
        if isinstance(plugin, DeploymentProviderPlugin):
            capabilities.update({)
                "supported_providers": plugin.get_supported_providers(),
                "supported_orchestrators": plugin.get_supported_orchestrators()
            })
        elif isinstance(plugin, NotificationChannelPlugin):
            capabilities.update({)
                "channel_type": plugin.get_channel_type(),
                "supported_message_types": plugin.get_supported_message_types()
            })
        elif isinstance(plugin, MonitoringProviderPlugin):
            capabilities.update({)
                "supported_channels": plugin.get_supported_channels()
            })
        
        return capabilities
    
    async def get_all_plugin_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Get capabilities of all registered plugins."""
        capabilities = {}
        
        for plugin_name in self.registry._plugins:
            capabilities[plugin_name] = self.get_plugin_capabilities(plugin_name)
        
        return capabilities
    
    async def calculate_infrastructure_cost_via_plugin():
        self, 
        provider: str, 
        infrastructure_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate infrastructure cost via deployment provider plugin."""
        try:
            # Find deployment provider plugin
            deployment_plugins = self.registry.get_plugins_by_type(PluginType.DEPLOYMENT_PROVIDER)
            
            for plugin in deployment_plugins:
                if isinstance(plugin, DeploymentProviderPlugin):
                    if provider in plugin.get_supported_providers():
                        # Check if plugin has cost calculation capability
                        if hasattr(plugin, 'calculate_infrastructure_cost'):
                            cost = await plugin.calculate_infrastructure_cost(infrastructure_config)
                            return {"success": True, "monthly_cost": cost}
                        else:
                            logger.debug(f"Plugin {plugin.meta.name} does not support cost calculation")
                            break
            
            return {"success": False, "error": f"No cost calculation plugin found for provider: {provider}"}
            
        except Exception as e:
            logger.error(f"Failed to calculate cost via plugin: {e}")
            return {"success": False, "error": str(e)}


# Global service integration instance
service_integration = PluginServiceIntegration()