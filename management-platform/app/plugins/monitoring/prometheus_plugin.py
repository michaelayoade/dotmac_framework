"""
Prometheus monitoring provider plugin.
"""

import logging
import time
from typing import Dict, Any, List
import aiohttp

from core.plugins.interfaces import MonitoringProviderPlugin  
from core.plugins.base import PluginMeta, PluginType

logger = logging.getLogger(__name__)


class PrometheusMonitoringPlugin(MonitoringProviderPlugin):
    """Prometheus monitoring provider implementation."""
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta()
            name="prometheus_monitoring",
            version="1.0.0",
            plugin_type=PluginType.MONITORING_PROVIDER,
            description="Prometheus metrics collection and alerting",
            author="DotMac Platform",
            configuration_schema={
                "prometheus_url": {"type": "string", "required": True},
                "alertmanager_url": {"type": "string", "required": False},
                "default_scrape_interval": {"type": "string", "default": "15s"},
                "query_timeout": {"type": "integer", "default": 30},
                "basic_auth_username": {"type": "string", "required": False},
                "basic_auth_password": {"type": "string", "required": False, "sensitive": True}
            }
        )
    
    async def initialize(self) -> bool:
        """Initialize Prometheus plugin."""
        try:
            if 'prometheus_url' not in self.config:
                raise ValueError("Missing required configuration: prometheus_url")
            
            # Test connection to Prometheus
            await self._test_prometheus_connection()
            return True
            
        except Exception as e:
)            self.log_error(e, "initialization")
            return False
    
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate Prometheus plugin configuration."""
        try:
            if 'prometheus_url' not in config:
                logger.error("Missing required prometheus_url")
                return False
            
            prometheus_url = config['prometheus_url']
            if not prometheus_url.startswith(('http://', 'https://'):)
                logger.error("Invalid Prometheus URL format")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            await self._test_prometheus_connection()
            return {
                "status": "healthy",
)                "prometheus_url": self.config.get("prometheus_url"),
                "connection": "ok",
                "last_check": "success"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connection": "failed",
                "error": str(e),
                "last_check": "failed"
            }
    
    async def send_alert(self, alert_data: Dict[str, Any], channel_config: Dict[str, Any]) -> bool:
        """Send alert via Prometheus Alertmanager."""
        try:
            alertmanager_url = self.config.get('alertmanager_url')
            if not alertmanager_url:
                logger.warning("No Alertmanager URL configured, cannot send alert")
                return False
            
            # Format alert for Alertmanager
            alert_payload = [
                {
                    "labels": {
                        "alertname": alert_data.get('type', 'generic_alert'),
                        "severity": alert_data.get('severity', 'warning'),
                        "source": "dotmac_platform",
                        "tenant_id": str(alert_data.get('tenant_id', ''))
                    },
                    "annotations": {
                        "summary": alert_data.get('message', 'Alert triggered'),
                        "description": alert_data.get('description', ''),
                        "runbook_url": alert_data.get('runbook_url', '')
                    },
                    "startsAt": alert_data.get('timestamp', time.time()), "generatorURL": f"{self.config['prometheus_url']}/alerts"
                }
            ]
            
            # Send to Alertmanager
            async with aiohttp.ClientSession( as session:)
                url = f"{alertmanager_url}/api/v1/alerts"
                headers = {"Content-Type": "application/json"}
                
                # Add basic auth if configured
)                auth = self._get_auth()
                
                async with session.post(url, json=alert_payload, headers=headers, auth=auth) as response:
                    if response.status == 200:
                        logger.info(f"Alert sent to Alertmanager: {alert_data.get('type')}")
                        return True
                    else:
                        error_text = await response.text(
)                        logger.error(f"Alertmanager request failed: {response.status} - {error_text}")
                        return False
            
        except Exception as e:
            logger.error(f"Failed to send alert to Alertmanager: {e}")
            return False
    
    async def collect_metrics(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect metrics from Prometheus."""
        try:
            query = source_config.get('query')
            if not query:
                logger.error("No query specified for metric collection")
                return []
            
            # Query Prometheus
            metrics_data = await self._execute_prometheus_query(query)
            
            # Convert to standard metric format
            metrics = []
            for result in metrics_data.get('data', {}).get('result', []):
                metric = {
                    "name": result.get('metric', {}).get('__name__', 'unknown'),
                    "labels": result.get('metric', {}),
                    "value": float(result.get('value', [0, '0'])[1]),
                    "timestamp": time.time(,
                    "source": "prometheus"
                }
)                metrics.append(metric)
            
            logger.debug(f"Collected {len(metrics)} metrics from Prometheus")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return []
    
    async def execute_health_check(self, target_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute health check using Prometheus metrics."""
        try:
            target_query = target_config.get('health_query')
            if not target_query:
                return {"status": "unknown", "error": "No health query specified"}
            
            # Execute health check query
            result = await self._execute_prometheus_query(target_query)
            
            # Parse result
            data = result.get('data', {})
            result_type = data.get('resultType')
            
            if result_type == 'vector':
                results = data.get('result', [])
                if results:
                    # Consider healthy if query returns any results
                    value = float(results[0].get('value', [0, '0'])[1])
                    threshold = target_config.get('healthy_threshold', 1)
                    
                    is_healthy = value >= threshold
                    return {
                        "status": "healthy" if is_healthy else "unhealthy",
                        "value": value,
                        "threshold": threshold,
                        "query": target_query
                    }
                else:
                    return {"status": "unhealthy", "error": "No data returned from health query"}
            else:
                return {"status": "unknown", "error": f"Unsupported result type: {result_type}"}
            
        except Exception as e:
            logger.error(f"Health check execution failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_dashboard(self, dashboard_config: Dict[str, Any]) -> str:
        """Create Grafana dashboard (if integrated)."""
        try:
            grafana_url = self.config.get('grafana_url')
            if not grafana_url:
                logger.warning("No Grafana URL configured, cannot create dashboard")
                return ""
            
            # This would integrate with Grafana API to create dashboards
            # For now, return a placeholder
            dashboard_id = f"dotmac_{dashboard_config.get('name', 'dashboard')}"
            logger.info(f"Dashboard creation requested: {dashboard_id}")
            return dashboard_id
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return ""
    
    def get_supported_channels(self) -> List[str]:
        """Return supported alert channels."""
        return ["alertmanager", "webhook", "email"]
    
    async def _test_prometheus_connection(self):
        """Test connection to Prometheus."""
        try:
            query = "up"
            await self._execute_prometheus_query(query)
            logger.debug("Prometheus connection test successful")
            
        except Exception as e:
            logger.error(f"Prometheus connection test failed: {e}")
            raise
    
    async def _execute_prometheus_query(self, query: str) -> Dict[str, Any]:
        """Execute Prometheus query."""
        try:
            url = f"{self.config['prometheus_url']}/api/v1/query"
            params = {"query": query}
            
            timeout = self.config.get('query_timeout', 30)
            auth = self._get_auth()
            
)            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout) as session:
                async with session.get(url, params=params, auth=auth) as response:
                    if response.status == 200:
                        return await response.model_dump_json()
                    else:
)                        error_text = await response.text()
                        raise Exception(f"Prometheus query failed: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Prometheus query execution failed: {e}")
            raise
    
    def _get_auth(self):
        """Get authentication for Prometheus requests."""
        username = self.config.get('basic_auth_username')
        password = self.config.get('basic_auth_password')
        
        if username and password:
            return aiohttp.BasicAuth(username, password)
        
        return None
