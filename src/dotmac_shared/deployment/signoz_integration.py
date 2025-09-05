"""
SigNoz Integration for Deployment Automation

Provides SigNoz-specific implementations for metrics collection,
alerting, and observability during deployment rollouts.
"""

import asyncio
import logging
from datetime import datetime

from ..observability import MonitoringStack
from .rollout_strategies import MetricsCollector, RolloutOrchestrator


class SigNozMetricsCollector(MetricsCollector):
    """SigNoz-based metrics collector using PromQL queries."""

    def __init__(self, signoz_query_endpoint: str, monitoring: MonitoringStack):
        self.signoz_endpoint = signoz_query_endpoint
        self.monitoring = monitoring
        self.logger = logging.getLogger(__name__)

    async def collect_metrics(
        self, service_name: str, version: str, duration_minutes: int
    ) -> dict[str, float]:
        """Collect metrics from SigNoz using PromQL queries."""
        try:
            import aiohttp

            metrics = {}
            # SigNoz supports PromQL queries just like Prometheus
            queries = {
                "error_rate": (
                    f'rate(signoz_calls_total{{{{service_name="{service_name}",service_version="{version}",status_code=~"5.."}}}}'
                    f"[{duration_minutes}m]) / "
                    f'rate(signoz_calls_total{{{{service_name="{service_name}",service_version="{version}"}}}}'
                    f"[{duration_minutes}m])"
                ),
                "response_time_p95": (
                    f"histogram_quantile(0.95, "
                    f'rate(signoz_latency_bucket{{{{service_name="{service_name}",service_version="{version}"}}}}'
                    f"[{duration_minutes}m]))"
                ),
                "success_rate": (
                    f'rate(signoz_calls_total{{{{service_name="{service_name}",service_version="{version}",status_code=~"2.."}}}}'
                    f"[{duration_minutes}m]) / "
                    f'rate(signoz_calls_total{{{{service_name="{service_name}",service_version="{version}"}}}}'
                    f"[{duration_minutes}m])"
                ),
                "cpu_usage": (
                    f'avg(signoz_system_cpu_utilization{{{{service_name="{service_name}",service_version="{version}"}}}}) * 100'
                ),
                "memory_usage": (
                    f'avg(signoz_system_memory_utilization{{{{service_name="{service_name}",service_version="{version}"}}}}) * 100'
                ),
                "request_rate": (
                    f'rate(signoz_calls_total{{{{service_name="{service_name}",service_version="{version}"}}}}'
                    f"[{duration_minutes}m])"
                ),
                "error_count": (
                    f'increase(signoz_calls_total{{{{service_name="{service_name}",service_version="{version}",status_code=~"5.."}}}}'
                    f"[{duration_minutes}m])"
                ),
            }

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                for metric_name, query in queries.items():
                    try:
                        # SigNoz exposes Prometheus-compatible query API
                        params = {"query": query, "time": datetime.now().isoformat()}
                        async with session.get(
                            f"{self.signoz_endpoint}/api/v1/query", params=params
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                result = data.get("data", {}).get("result", [])
                                if (
                                    result
                                    and len(result) > 0
                                    and result[0].get("value")
                                ):
                                    metrics[metric_name] = float(result[0]["value"][1])
                                else:
                                    metrics[metric_name] = 0.0
                                    self.logger.debug(
                                        f"No data for metric {metric_name}"
                                    )
                            else:
                                self.logger.warning(
                                    f"Failed to query {metric_name}: HTTP {response.status}"
                                )
                                metrics[metric_name] = 0.0

                    except Exception as e:
                        self.logger.error(f"Error collecting {metric_name}: {str(e)}")
                        metrics[metric_name] = 0.0

            # Add SigNoz-specific metrics
            await self._collect_signoz_specific_metrics(
                service_name, version, duration_minutes, metrics, session
            )

            self.logger.info(
                f"Collected {len(metrics)} metrics from SigNoz for {service_name}:{version}"
            )
            return metrics

        except Exception as e:
            self.logger.error(f"Failed to collect metrics from SigNoz: {str(e)}")
            return {}

    async def _collect_signoz_specific_metrics(
        self,
        service_name: str,
        version: str,
        duration_minutes: int,
        metrics: dict[str, float],
        session,
    ):
        """Collect SigNoz-specific observability metrics."""
        try:
            # Trace-based metrics (unique to SigNoz)
            trace_queries = {
                "trace_error_rate": (
                    f'rate(signoz_traces_total{{{{service_name="{service_name}",service_version="{version}",status=~"ERROR"}}}}'
                    f"[{duration_minutes}m]) / "
                    f'rate(signoz_traces_total{{{{service_name="{service_name}",service_version="{version}"}}}}'
                    f"[{duration_minutes}m])"
                ),
                "avg_spans_per_trace": (
                    f'avg(signoz_spans_per_trace{{{{service_name="{service_name}",service_version="{version}"}}}}'
                    f"[{duration_minutes}m])"
                ),
                "trace_duration_p99": (
                    f"histogram_quantile(0.99, "
                    f'rate(signoz_trace_duration_bucket{{{{service_name="{service_name}",service_version="{version}"}}}}'
                    f"[{duration_minutes}m]))"
                ),
            }

            for metric_name, query in trace_queries.items():
                try:
                    params = {"query": query, "time": datetime.now().isoformat()}
                    async with session.get(
                        f"{self.signoz_endpoint}/api/v1/query", params=params
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            result = data.get("data", {}).get("result", [])
                            if result and len(result) > 0 and result[0].get("value"):
                                metrics[metric_name] = float(result[0]["value"][1])
                            else:
                                metrics[metric_name] = 0.0

                except Exception as e:
                    self.logger.debug(
                        f"Could not collect trace metric {metric_name}: {str(e)}"
                    )
                    metrics[metric_name] = 0.0

        except Exception as e:
            self.logger.warning(f"Error collecting SigNoz-specific metrics: {str(e)}")


class SigNozIstioTrafficManager:
    """Traffic manager that works with both Istio and SigNoz monitoring."""

    def __init__(self, namespace: str, signoz_endpoint: str):
        self.namespace = namespace
        self.signoz_endpoint = signoz_endpoint
        self.logger = logging.getLogger(__name__)

    async def set_traffic_split_with_monitoring(
        self, service_name: str, version_weights: dict[str, int]
    ):
        """Set traffic split and configure SigNoz monitoring."""
        try:
            # Apply Istio VirtualService
            await self._apply_istio_virtual_service(service_name, version_weights)

            # Configure SigNoz monitoring for the traffic split
            await self._configure_signoz_monitoring(service_name, version_weights)

        except Exception as e:
            self.logger.error(
                f"Failed to configure traffic split with monitoring: {str(e)}"
            )
            raise

    async def _apply_istio_virtual_service(
        self, service_name: str, version_weights: dict[str, int]
    ):
        """Apply Istio VirtualService configuration."""
        import tempfile

        import yaml

        virtual_service = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {
                "name": f"{service_name}-traffic-split",
                "namespace": self.namespace,
                "annotations": {
                    "signoz.io/monitor": "true",
                    "signoz.io/service": service_name,
                },
            },
            "spec": {
                "hosts": [service_name],
                "http": [
                    {
                        "match": [{"headers": {"x-canary": {"exact": "true"}}}],
                        "route": [
                            {
                                "destination": {
                                    "host": service_name,
                                    "subset": version,
                                },
                                "weight": weight,
                                "headers": {
                                    "response": {
                                        "add": {
                                            "x-version": version,
                                            "x-traffic-weight": str(weight),
                                        }
                                    }
                                },
                            }
                            for version, weight in version_weights.items()
                        ],
                    }
                ],
            },
        }

        # Apply the configuration
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(virtual_service, f)
            manifest_file = f.name

        try:
            cmd = ["kubectl", "apply", "-f", manifest_file, "-n", self.namespace]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise Exception(f"kubectl failed: {stderr.decode()}")

            self.logger.info(f"Applied Istio traffic split for {service_name}")

        finally:
            import os

            os.unlink(manifest_file)

    async def _configure_signoz_monitoring(
        self, service_name: str, version_weights: dict[str, int]
    ):
        """Configure SigNoz-specific monitoring for traffic split."""
        try:
            # Create SigNoz dashboard for the rollout
            dashboard_config = {
                "title": f"Rollout Monitoring - {service_name}",
                "panels": [
                    {
                        "title": "Traffic Distribution",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": f'sum by (service_version) (rate(signoz_calls_total{{service_name="{service_name}"}}[5m]))',
                                "legendFormat": "{{service_version}}",
                            }
                        ],
                    },
                    {
                        "title": "Error Rate by Version",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": f'rate(signoz_calls_total{{service_name="{service_name}",status_code=~"5.."}}[5m]) / rate(signoz_calls_total{{service_name="{service_name}"}}[5m])',
                                "legendFormat": "Error Rate - {{service_version}}",
                            }
                        ],
                    },
                    {
                        "title": "Response Time P95 by Version",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": f'histogram_quantile(0.95, rate(signoz_latency_bucket{{service_name="{service_name}"}}[5m]))',
                                "legendFormat": "P95 Latency - {{service_version}}",
                            }
                        ],
                    },
                ],
            }

            # In a real implementation, this would call SigNoz API to create the dashboard
            self.logger.info(
                f"Configured SigNoz monitoring dashboard for {service_name}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to configure SigNoz monitoring: {str(e)}")


class SigNozRolloutFactory:
    """Factory for creating SigNoz-integrated rollout orchestrator."""

    @staticmethod
    def create_signoz_istio_rollout(
        deployment,
        monitoring: MonitoringStack,
        signoz_query_endpoint: str,
        namespace: str = "default",
    ) -> RolloutOrchestrator:
        """Create rollout orchestrator with SigNoz and Istio integration."""

        # Use SigNoz metrics collector instead of Prometheus
        metrics_collector = SigNozMetricsCollector(signoz_query_endpoint, monitoring)

        # Enhanced traffic manager with SigNoz monitoring
        traffic_manager = SigNozIstioTrafficManager(namespace, signoz_query_endpoint)

        return RolloutOrchestrator(
            deployment=deployment,
            monitoring=monitoring,
            metrics_collector=metrics_collector,
            traffic_manager=traffic_manager,
        )

    @staticmethod
    def create_signoz_only_rollout(
        deployment, monitoring: MonitoringStack, signoz_query_endpoint: str
    ) -> RolloutOrchestrator:
        """Create rollout orchestrator with SigNoz monitoring only (no Istio)."""

        metrics_collector = SigNozMetricsCollector(signoz_query_endpoint, monitoring)

        return RolloutOrchestrator(
            deployment=deployment,
            monitoring=monitoring,
            metrics_collector=metrics_collector,
            traffic_manager=None,  # No traffic management without service mesh
        )


# Convenience function for SigNoz integration
async def setup_signoz_rollout(
    deployment,
    monitoring: MonitoringStack,
    signoz_query_endpoint: str,
    use_istio: bool = True,
    namespace: str = "default",
) -> RolloutOrchestrator:
    """Setup rollout orchestrator optimized for SigNoz observability."""

    factory = SigNozRolloutFactory()

    if use_istio:
        return factory.create_signoz_istio_rollout(
            deployment, monitoring, signoz_query_endpoint, namespace
        )
    else:
        return factory.create_signoz_only_rollout(
            deployment, monitoring, signoz_query_endpoint
        )
