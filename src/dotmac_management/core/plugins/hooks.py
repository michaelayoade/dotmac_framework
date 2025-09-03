"""
Plugin hook system for event-driven plugin execution.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from .base import BasePlugin, PluginError

logger = logging.getLogger(__name__)


class PluginHooks:
    """Event-driven plugin hook system."""

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = defaultdict(list)
        self._plugin_hooks: Dict[str, List[str]] = defaultdict(
            list
        )  # plugin_name -> hook_names
        self._lock = asyncio.Lock()

    async def register_hook(
        self, hook_name: str, plugin: BasePlugin, handler: Callable
    ) -> bool:
        """Register a plugin hook for an event."""
        async with self._lock:
            try:
                if not callable(handler):
                    raise PluginError(f"Hook handler must be callable: {hook_name}")

                self._hooks[hook_name].append(handler)
                self._plugin_hooks[plugin.meta.name].append(hook_name)

                logger.debug(
                    f"Hook registered: {hook_name} for plugin {plugin.meta.name}"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to register hook {hook_name}: {e}")
                return False

    async def unregister_plugin_hooks(self, plugin_name: str) -> bool:
        """Unregister all hooks for a plugin."""
        async with self._lock:
            try:
                hook_names = self._plugin_hooks.get(plugin_name, [])

                for hook_name in hook_names:
                    # Remove handlers for this plugin from each hook
                    if hook_name in self._hooks:
                        # This is simplified - in practice you'd need to track which handler belongs to which plugin
                        self._hooks[hook_name] = []

                if plugin_name in self._plugin_hooks:
                    del self._plugin_hooks[plugin_name]

                logger.info(f"Unregistered all hooks for plugin: {plugin_name}")
                return True

            except Exception as e:
                logger.error(
                    f"Failed to unregister hooks for plugin {plugin_name}: {e}"
                )
                return False

    async def trigger_hook(
        self, hook_name: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Trigger all handlers for a specific hook."""
        handlers = self._hooks.get(hook_name, [])
        if not handlers:
            logger.debug(f"No handlers registered for hook: {hook_name}")
            return []

        results = []

        for handler in handlers:
            try:
                # Execute handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(context)
                else:
                    result = handler(context)

                results.append(
                    {
                        "handler": getattr(handler, "__name__", str(handler)),
                        "success": True,
                        "result": result,
                    }
                )

            except Exception as e:
                logger.error(f"Hook handler failed for {hook_name}: {e}")
                results.append(
                    {
                        "handler": getattr(handler, "__name__", str(handler)),
                        "success": False,
                        "error": str(e),
                    }
                )

        logger.debug(f"Triggered hook {hook_name}: {len(results)} handlers executed")
        return results

    async def trigger_hook_first_success(
        self, hook_name: str, context: Dict[str, Any]
    ) -> Optional[Any]:
        """Trigger handlers until one succeeds, return the result."""
        handlers = self._hooks.get(hook_name, [])
        if not handlers:
            return None

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(context)
                else:
                    result = handler(context)

                logger.debug(
                    f"Hook {hook_name} succeeded with handler {getattr(handler, '__name__', str(handler))}"
                )
                return result

            except Exception as e:
                logger.debug(f"Hook handler failed for {hook_name}: {e}")
                continue

        logger.warning(f"No handlers succeeded for hook: {hook_name}")
        return None

    def list_hooks(self) -> Dict[str, int]:
        """List all registered hooks and handler counts."""
        return {hook_name: len(handlers) for hook_name, handlers in self._hooks.items()}

    def get_plugin_hooks(self, plugin_name: str) -> List[str]:
        """Get all hooks registered by a plugin."""
        return self._plugin_hooks.get(plugin_name, [])


# Predefined hook names for management platform events
class HookNames:
    """Standard hook names for management platform events."""

    # Tenant lifecycle hooks
    BEFORE_TENANT_CREATE = "before_tenant_create"
    AFTER_TENANT_CREATE = "after_tenant_create"
    BEFORE_TENANT_DELETE = "before_tenant_delete"
    AFTER_TENANT_DELETE = "after_tenant_delete"

    # Deployment hooks
    BEFORE_DEPLOYMENT = "before_deployment"
    AFTER_DEPLOYMENT = "after_deployment"
    DEPLOYMENT_FAILED = "deployment_failed"
    BEFORE_ROLLBACK = "before_rollback"
    AFTER_ROLLBACK = "after_rollback"

    # Infrastructure hooks
    BEFORE_PROVISION_INFRASTRUCTURE = "before_provision_infrastructure"
    AFTER_PROVISION_INFRASTRUCTURE = "after_provision_infrastructure"
    INFRASTRUCTURE_FAILED = "infrastructure_failed"

    # Plugin lifecycle hooks
    BEFORE_PLUGIN_INSTALL = "before_plugin_install"
    AFTER_PLUGIN_INSTALL = "after_plugin_install"
    BEFORE_PLUGIN_UPDATE = "before_plugin_update"
    AFTER_PLUGIN_UPDATE = "after_plugin_update"
    BEFORE_PLUGIN_UNINSTALL = "before_plugin_uninstall"
    AFTER_PLUGIN_UNINSTALL = "after_plugin_uninstall"

    # Billing hooks
    BEFORE_BILLING_CALCULATION = "before_billing_calculation"
    AFTER_BILLING_CALCULATION = "after_billing_calculation"
    BEFORE_PAYMENT_PROCESSING = "before_payment_processing"
    AFTER_PAYMENT_PROCESSING = "after_payment_processing"
    PAYMENT_FAILED = "payment_failed"

    # Monitoring hooks
    ALERT_TRIGGERED = "alert_triggered"
    METRIC_COLLECTED = "metric_collected"
    HEALTH_CHECK_FAILED = "health_check_failed"

    # Notification hooks
    BEFORE_NOTIFICATION_SEND = "before_notification_send"
    AFTER_NOTIFICATION_SEND = "after_notification_send"
    NOTIFICATION_FAILED = "notification_failed"

    # Security hooks
    SECURITY_SCAN_COMPLETED = "security_scan_completed"
    VULNERABILITY_DETECTED = "vulnerability_detected"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"


# Global hook manager instance
hook_manager = PluginHooks()
