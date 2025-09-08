"""
Monitoring service integrations for platform observability.

Provides standardized interfaces for integrating with various monitoring
and observability platforms including SigNoz, Prometheus, and Grafana.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx
import structlog

logger = structlog.get_logger(__name__)


class IntegrationStatus(str, Enum):
    """Integration status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class IntegrationConfig:
    """Configuration for monitoring integrations."""
    name: str
    endpoint: str
    api_key: Optional[str] = None
    timeout: int = 30
    retry_count: int = 3
    enabled: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MetricData:
    """Structured metric data for integrations."""
    name: str
    value: Union[int, float]
    timestamp: Optional[datetime] = None
    labels: Dict[str, str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.labels is None:
            self.labels = {}
        if self.metadata is None:
            self.metadata = {}


class MonitoringIntegration(ABC):
    """Abstract base class for monitoring service integrations."""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.status = IntegrationStatus.PENDING
        self.client: Optional[httpx.AsyncClient] = None
        self.logger = logger.bind(integration=config.name)

    async def initialize(self) -> bool:
        """Initialize the integration connection."""
        try:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers=self._get_headers()
            )

            if await self.health_check():
                self.status = IntegrationStatus.ACTIVE
                self.logger.info("Integration initialized successfully")
                return True
            else:
                self.status = IntegrationStatus.ERROR
                self.logger.error("Integration health check failed")
                return False

        except Exception as e:
            self.status = IntegrationStatus.ERROR
            self.logger.error("Integration initialization failed", error=str(e))
            return False

    async def shutdown(self):
        """Shutdown the integration and clean up resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self.status = IntegrationStatus.INACTIVE
        self.logger.info("Integration shutdown complete")

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the integration service is healthy."""
        pass

    @abstractmethod
    async def send_metrics(self, metrics: List[MetricData]) -> bool:
        """Send metrics to the monitoring service."""
        pass

    @abstractmethod
    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send alert to the monitoring service."""
        pass

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request with error handling and retries."""
        if not self.client:
            self.logger.error("Client not initialized")
            return None

        url = urljoin(self.config.endpoint, endpoint)

        for attempt in range(self.config.retry_count):
            try:
                response = await self.client.request(method, url, json=data)
                response.raise_for_status()
                return response.json() if response.content else {}

            except httpx.HTTPStatusError as e:
                self.logger.warning(
                    "HTTP error on attempt",
                    attempt=attempt + 1,
                    status_code=e.response.status_code,
                    error=str(e)
                )
                if attempt == self.config.retry_count - 1:
                    raise

            except Exception as e:
                self.logger.error(
                    "Request failed on attempt",
                    attempt=attempt + 1,
                    error=str(e)
                )
                if attempt == self.config.retry_count - 1:
                    raise

            await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return None


class SigNozIntegration(MonitoringIntegration):
    """SigNoz monitoring integration."""

    async def health_check(self) -> bool:
        """Check SigNoz service health."""
        try:
            response = await self._make_request("GET", "/api/v1/health")
            return response is not None and response.get("status") == "ok"
        except Exception as e:
            self.logger.error("SigNoz health check failed", error=str(e))
            return False

    async def send_metrics(self, metrics: List[MetricData]) -> bool:
        """Send metrics to SigNoz."""
        try:
            metric_payload = {
                "metrics": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "timestamp": int(metric.timestamp.timestamp()),
                        "labels": metric.labels,
                        **metric.metadata
                    }
                    for metric in metrics
                ]
            }

            response = await self._make_request("POST", "/api/v1/metrics", metric_payload)
            return response is not None

        except Exception as e:
            self.logger.error("Failed to send metrics to SigNoz", error=str(e))
            return False

    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send alert to SigNoz."""
        try:
            response = await self._make_request("POST", "/api/v1/alerts", alert_data)
            return response is not None
        except Exception as e:
            self.logger.error("Failed to send alert to SigNoz", error=str(e))
            return False


class PrometheusIntegration(MonitoringIntegration):
    """Prometheus monitoring integration."""

    async def health_check(self) -> bool:
        """Check Prometheus service health."""
        try:
            response = await self._make_request("GET", "/-/healthy")
            return response is not None
        except Exception as e:
            self.logger.error("Prometheus health check failed", error=str(e))
            return False

    async def send_metrics(self, metrics: List[MetricData]) -> bool:
        """Send metrics to Prometheus (via push gateway)."""
        try:
            # Format metrics in Prometheus exposition format
            metric_lines = []
            for metric in metrics:
                labels_str = ",".join([f'{k}="{v}"' for k, v in metric.labels.items()])
                if labels_str:
                    labels_str = f"{{{labels_str}}}"
                metric_lines.append(f"{metric.name}{labels_str} {metric.value}")

            payload = "\n".join(metric_lines)

            # Send to push gateway
            response = await self.client.post(
                f"{self.config.endpoint}/metrics/job/dotmac",
                content=payload,
                headers={"Content-Type": "text/plain"}
            )
            response.raise_for_status()
            return True

        except Exception as e:
            self.logger.error("Failed to send metrics to Prometheus", error=str(e))
            return False

    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send alert to Prometheus Alertmanager."""
        try:
            alerts_payload = [alert_data]
            response = await self._make_request("POST", "/api/v1/alerts", alerts_payload)
            return response is not None
        except Exception as e:
            self.logger.error("Failed to send alert to Prometheus", error=str(e))
            return False


class GrafanaIntegration(MonitoringIntegration):
    """Grafana integration for dashboards and annotations."""

    async def health_check(self) -> bool:
        """Check Grafana service health."""
        try:
            response = await self._make_request("GET", "/api/health")
            return response is not None and response.get("database") == "ok"
        except Exception as e:
            self.logger.error("Grafana health check failed", error=str(e))
            return False

    async def send_metrics(self, metrics: List[MetricData]) -> bool:
        """Send metrics to Grafana (as annotations)."""
        try:
            for metric in metrics:
                annotation = {
                    "time": int(metric.timestamp.timestamp() * 1000),
                    "text": f"{metric.name}: {metric.value}",
                    "tags": list(metric.labels.keys()),
                }
                await self._make_request("POST", "/api/annotations", annotation)
            return True
        except Exception as e:
            self.logger.error("Failed to send metrics to Grafana", error=str(e))
            return False

    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send alert annotation to Grafana."""
        try:
            annotation = {
                "time": int(datetime.utcnow().timestamp() * 1000),
                "text": alert_data.get("message", "Alert triggered"),
                "tags": ["alert", alert_data.get("severity", "info")],
                "alertId": alert_data.get("id")
            }
            response = await self._make_request("POST", "/api/annotations", annotation)
            return response is not None
        except Exception as e:
            self.logger.error("Failed to send alert to Grafana", error=str(e))
            return False


class IntegrationManager:
    """Manages multiple monitoring integrations."""

    def __init__(self):
        self.integrations: Dict[str, MonitoringIntegration] = {}
        self.logger = logger.bind(component="integration_manager")

    async def add_integration(self, integration: MonitoringIntegration) -> bool:
        """Add and initialize a monitoring integration."""
        try:
            success = await integration.initialize()
            if success:
                self.integrations[integration.config.name] = integration
                self.logger.info(
                    "Integration added successfully",
                    integration=integration.config.name
                )
            return success
        except Exception as e:
            self.logger.error(
                "Failed to add integration",
                integration=integration.config.name,
                error=str(e)
            )
            return False

    async def remove_integration(self, name: str) -> bool:
        """Remove and shutdown a monitoring integration."""
        if name in self.integrations:
            try:
                await self.integrations[name].shutdown()
                del self.integrations[name]
                self.logger.info("Integration removed successfully", integration=name)
                return True
            except Exception as e:
                self.logger.error(
                    "Failed to remove integration",
                    integration=name,
                    error=str(e)
                )
                return False
        return False

    async def broadcast_metrics(self, metrics: List[MetricData]) -> Dict[str, bool]:
        """Broadcast metrics to all active integrations."""
        results = {}

        for name, integration in self.integrations.items():
            if integration.status == IntegrationStatus.ACTIVE:
                try:
                    success = await integration.send_metrics(metrics)
                    results[name] = success
                except Exception as e:
                    self.logger.error(
                        "Failed to send metrics to integration",
                        integration=name,
                        error=str(e)
                    )
                    results[name] = False
            else:
                results[name] = False

        return results

    async def broadcast_alert(self, alert_data: Dict[str, Any]) -> Dict[str, bool]:
        """Broadcast alert to all active integrations."""
        results = {}

        for name, integration in self.integrations.items():
            if integration.status == IntegrationStatus.ACTIVE:
                try:
                    success = await integration.send_alert(alert_data)
                    results[name] = success
                except Exception as e:
                    self.logger.error(
                        "Failed to send alert to integration",
                        integration=name,
                        error=str(e)
                    )
                    results[name] = False
            else:
                results[name] = False

        return results

    async def get_integration_status(self) -> Dict[str, IntegrationStatus]:
        """Get status of all integrations."""
        return {name: integration.status for name, integration in self.integrations.items()}

    async def health_check_all(self) -> Dict[str, bool]:
        """Run health check on all integrations."""
        results = {}

        for name, integration in self.integrations.items():
            try:
                healthy = await integration.health_check()
                results[name] = healthy

                # Update status based on health check
                if healthy and integration.status == IntegrationStatus.ERROR:
                    integration.status = IntegrationStatus.ACTIVE
                elif not healthy and integration.status == IntegrationStatus.ACTIVE:
                    integration.status = IntegrationStatus.ERROR

            except Exception as e:
                self.logger.error(
                    "Health check failed for integration",
                    integration=name,
                    error=str(e)
                )
                results[name] = False
                integration.status = IntegrationStatus.ERROR

        return results

    async def shutdown_all(self):
        """Shutdown all integrations."""
        for name, integration in self.integrations.items():
            try:
                await integration.shutdown()
                self.logger.info("Integration shutdown", integration=name)
            except Exception as e:
                self.logger.error(
                    "Failed to shutdown integration",
                    integration=name,
                    error=str(e)
                )

        self.integrations.clear()
        self.logger.info("All integrations shutdown complete")
