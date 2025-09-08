"""
Advanced Rollout Strategies

Provides sophisticated deployment rollout strategies including
progressive delivery, feature flags integration, automated rollback,
and traffic management for safe deployments.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .monitoring import MonitoringStack
from .automation import DeploymentAutomation, DeploymentSpec, DeploymentStatus


class RolloutStrategy(str, Enum):
    """Rollout strategy types."""

    PROGRESSIVE = "progressive"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    A_B_TEST = "a_b_test"
    RING = "ring"
    FEATURE_FLAG = "feature_flag"


class RolloutPhase(str, Enum):
    """Rollout phase states."""

    INITIALIZING = "initializing"
    DEPLOYING = "deploying"
    MONITORING = "monitoring"
    VALIDATING = "validating"
    PROMOTING = "promoting"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"


class TrafficSplit(str, Enum):
    """Traffic split methods."""

    PERCENTAGE = "percentage"
    USER_ATTRIBUTE = "user_attribute"
    GEOGRAPHIC = "geographic"
    DEVICE_TYPE = "device_type"
    RANDOM = "random"


@dataclass
class RolloutMetrics:
    """Metrics for rollout validation."""

    error_rate_threshold: float = 0.05  # 5%
    response_time_p95_threshold: float = 500.0  # 500ms
    success_rate_threshold: float = 0.95  # 95%
    cpu_threshold: float = 80.0  # 80%
    memory_threshold: float = 90.0  # 90%
    custom_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class RolloutConfig:
    """Configuration for rollout strategy."""

    strategy: RolloutStrategy
    service_name: str
    deployment_spec: DeploymentSpec
    phases: list[int] = field(
        default_factory=lambda: [10, 25, 50, 100]
    )  # Traffic percentages
    phase_duration_minutes: int = 15
    validation_duration_minutes: int = 5
    metrics_thresholds: RolloutMetrics = field(default_factory=RolloutMetrics)
    auto_promote: bool = True
    auto_rollback: bool = True
    traffic_split_method: TrafficSplit = TrafficSplit.PERCENTAGE
    target_groups: list[str] = field(default_factory=list)
    feature_flags: dict[str, Any] = field(default_factory=dict)
    notification_webhooks: list[str] = field(default_factory=list)


@dataclass
class RolloutState:
    """Current state of a rollout."""

    rollout_id: str
    config: RolloutConfig
    current_phase: RolloutPhase
    current_traffic_percentage: int
    phase_index: int
    start_time: datetime
    phase_start_time: Optional[datetime] = None
    deployment_ids: dict[str, str] = field(
        default_factory=dict
    )  # version -> deployment_id
    metrics_history: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rollback_reason: Optional[str] = None


class MetricsCollector(ABC):
    """Abstract base class for collecting rollout metrics."""

    @abstractmethod
    async def collect_metrics(
        self, service_name: str, version: str, duration_minutes: int
    ) -> dict[str, float]:
        """Collect metrics for a service version."""
        pass


class PrometheusMetricsCollector(MetricsCollector):
    """Legacy Prometheus-based metrics collector (deprecated; use SigNoz/OTLP)."""

    def __init__(self, prometheus_url: str, monitoring: MonitoringStack):
        self.prometheus_url = prometheus_url
        self.monitoring = monitoring
        self.logger = logging.getLogger(__name__)

    async def collect_metrics(
        self, service_name: str, version: str, duration_minutes: int
    ) -> dict[str, float]:
        """Collect metrics from Prometheus (deprecated)."""
        try:
            import aiohttp

            metrics = {}
            queries = {
                "error_rate": (
                    f'rate(http_requests_total{{{{service="{service_name}",version="{version}",status=~"5.."}}}}'
                    f"[{duration_minutes}m]) / "
                    f'rate(http_requests_total{{{{service="{service_name}",version="{version}"}}}}'
                    f"[{duration_minutes}m])"
                ),
                "response_time_p95": (
                    f"histogram_quantile(0.95, "
                    f'rate(http_request_duration_seconds_bucket{{{{service="{service_name}",version="{version}"}}}}'
                    f"[{duration_minutes}m]))"
                ),
                "success_rate": (
                    f'rate(http_requests_total{{{{service="{service_name}",version="{version}",status=~"2.."}}}}'
                    f"[{duration_minutes}m]) / "
                    f'rate(http_requests_total{{{{service="{service_name}",version="{version}"}}}}'
                    f"[{duration_minutes}m])"
                ),
                "cpu_usage": (
                    f'avg(rate(container_cpu_usage_seconds_total{{{{service="{service_name}",version="{version}"}}}}'
                    f"[{duration_minutes}m])) * 100"
                ),
                "memory_usage": (
                    f'avg(container_memory_usage_bytes{{{{service="{service_name}",version="{version}"}}}}) / '
                    f'avg(container_spec_memory_limit_bytes{{{{service="{service_name}",version="{version}"}}}}) * 100'
                ),
            }

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                for metric_name, query in queries.items():
                    try:
                        params = {"query": query}
                        async with session.get(
                            f"{self.prometheus_url}/api/v1/query", params=params
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                result = data.get("data", {}).get("result", [])
                                if result and result[0].get("value"):
                                    metrics[metric_name] = float(result[0]["value"][1])
                                else:
                                    metrics[metric_name] = 0.0
                            else:
                                self.logger.warning(
                                    f"Failed to query {metric_name}: HTTP {response.status}"
                                )
                                metrics[metric_name] = 0.0
                    except Exception as e:
                        self.logger.error(f"Error collecting {metric_name}: {str(e)}")
                        metrics[metric_name] = 0.0

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {str(e)}")
            return {}


class TrafficManager(ABC):
    """Abstract base class for managing traffic splits."""

    @abstractmethod
    async def set_traffic_split(
        self, service_name: str, version_weights: dict[str, int]
    ):
        """Set traffic split between service versions."""
        pass

    @abstractmethod
    async def get_current_split(self, service_name: str) -> dict[str, int]:
        """Get current traffic split for a service."""
        pass


class IstioTrafficManager(TrafficManager):
    """Istio-based traffic manager."""

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.logger = logging.getLogger(__name__)

    async def set_traffic_split(
        self, service_name: str, version_weights: dict[str, int]
    ):
        """Set traffic split using Istio VirtualService."""
        try:
            # Generate Istio VirtualService manifest
            virtual_service = {
                "apiVersion": "networking.istio.io/v1beta1",
                "kind": "VirtualService",
                "metadata": {
                    "name": f"{service_name}-traffic-split",
                    "namespace": self.namespace,
                },
                "spec": {
                    "hosts": [service_name],
                    "http": [
                        {
                            "route": [
                                {
                                    "destination": {
                                        "host": service_name,
                                        "subset": version,
                                    },
                                    "weight": weight,
                                }
                                for version, weight in version_weights.items()
                            ]
                        }
                    ],
                },
            }

            # Apply the VirtualService
            import tempfile

            import yaml

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
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

                self.logger.info(
                    f"Traffic split applied for {service_name}: {version_weights}"
                )

            finally:
                import os

                os.unlink(manifest_file)

        except Exception as e:
            self.logger.error(
                f"Failed to set traffic split for {service_name}: {str(e)}"
            )
            raise

    async def get_current_split(self, service_name: str) -> dict[str, int]:
        """Get current traffic split from Istio VirtualService."""
        try:
            cmd = [
                "kubectl",
                "get",
                "virtualservice",
                f"{service_name}-traffic-split",
                "-n",
                self.namespace,
                "-o",
                "json",
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return {}

            import json

            vs_data = json.loads(stdout.decode())

            splits = {}
            http_routes = vs_data.get("spec", {}).get("http", [])
            if http_routes:
                for route in http_routes[0].get("route", []):
                    subset = route.get("destination", {}).get("subset")
                    weight = route.get("weight", 0)
                    if subset:
                        splits[subset] = weight

            return splits

        except Exception as e:
            self.logger.error(
                f"Failed to get current split for {service_name}: {str(e)}"
            )
            return {}


class FeatureFlagManager(ABC):
    """Abstract base class for feature flag management."""

    @abstractmethod
    async def enable_flag(
        self, flag_name: str, percentage: int, filters: Optional[dict[str, Any]] = None
    ):
        """Enable feature flag for specified percentage of users."""
        pass

    @abstractmethod
    async def disable_flag(self, flag_name: str):
        """Disable feature flag."""
        pass

    @abstractmethod
    async def get_flag_status(self, flag_name: str) -> dict[str, Any]:
        """Get feature flag status."""
        pass


class LaunchDarklyFeatureFlagManager(FeatureFlagManager):
    """LaunchDarkly-based feature flag manager."""

    def __init__(self, api_token: str, project_key: str, environment_key: str):
        self.api_token = api_token
        self.project_key = project_key
        self.environment_key = environment_key
        self.logger = logging.getLogger(__name__)

    async def enable_flag(
        self, flag_name: str, percentage: int, filters: Optional[dict[str, Any]] = None
    ):
        """Enable feature flag via LaunchDarkly API."""
        try:
            import aiohttp

            url = f"https://app.launchdarkly.com/api/v2/flags/{self.project_key}/{flag_name}"
            headers = {
                "Authorization": self.api_token,
                "Content-Type": "application/json",
            }

            # Construct flag update payload
            payload = {
                "environments": {
                    self.environment_key: {
                        "on": True,
                        "rules": [
                            {
                                "variation": 1,  # Enabled variation
                                "rollout": {
                                    "variations": [
                                        {
                                            "variation": 0,
                                            "weight": 100000 - (percentage * 1000),
                                        },
                                        {"variation": 1, "weight": percentage * 1000},
                                    ]
                                },
                            }
                        ],
                    }
                }
            }

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                async with session.patch(
                    url, json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        self.logger.info(
                            f"Feature flag {flag_name} enabled at {percentage}%"
                        )
                    else:
                        raise Exception(f"API request failed: HTTP {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to enable feature flag {flag_name}: {str(e)}")
            raise

    async def disable_flag(self, flag_name: str):
        """Disable feature flag."""
        try:
            import aiohttp

            url = f"https://app.launchdarkly.com/api/v2/flags/{self.project_key}/{flag_name}"
            headers = {
                "Authorization": self.api_token,
                "Content-Type": "application/json",
            }

            payload = {"environments": {self.environment_key: {"on": False}}}

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                async with session.patch(
                    url, json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Feature flag {flag_name} disabled")
                    else:
                        raise Exception(f"API request failed: HTTP {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to disable feature flag {flag_name}: {str(e)}")
            raise

    async def get_flag_status(self, flag_name: str) -> dict[str, Any]:
        """Get feature flag status."""
        try:
            import aiohttp

            url = f"https://app.launchdarkly.com/api/v2/flags/{self.project_key}/{flag_name}"
            headers = {"Authorization": self.api_token}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"API request failed: HTTP {response.status}")

        except Exception as e:
            self.logger.error(
                f"Failed to get feature flag status {flag_name}: {str(e)}"
            )
            return {}


class RolloutOrchestrator:
    """Main orchestrator for advanced rollout strategies."""

    def __init__(
        self,
        deployment: DeploymentAutomation,
        monitoring: MonitoringStack,
        metrics_collector: MetricsCollector,
        traffic_manager: Optional[TrafficManager] = None,
        feature_flag_manager: Optional[FeatureFlagManager] = None,
    ):
        self.deployment = deployment
        self.monitoring = monitoring
        self.metrics_collector = metrics_collector
        self.traffic_manager = traffic_manager
        self.feature_flag_manager = feature_flag_manager
        self.logger = logging.getLogger(__name__)
        self.active_rollouts: dict[str, RolloutState] = {}
        self._rollout_tasks: dict[str, asyncio.Task] = {}

    async def start_rollout(self, config: RolloutConfig) -> str:
        """Start a new rollout."""
        rollout_id = f"{config.service_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        state = RolloutState(
            rollout_id=rollout_id,
            config=config,
            current_phase=RolloutPhase.INITIALIZING,
            current_traffic_percentage=0,
            phase_index=0,
            start_time=datetime.now(),
        )

        self.active_rollouts[rollout_id] = state

        # Start rollout execution
        task = asyncio.create_task(self._execute_rollout(state))
        self._rollout_tasks[rollout_id] = task

        self.logger.info(f"Started rollout {rollout_id} for {config.service_name}")
        return rollout_id

    async def get_rollout_status(self, rollout_id: str) -> Optional[RolloutState]:
        """Get rollout status."""
        return self.active_rollouts.get(rollout_id)

    async def abort_rollout(self, rollout_id: str, reason: str = "") -> bool:
        """Abort an active rollout."""
        if rollout_id not in self.active_rollouts:
            return False

        try:
            state = self.active_rollouts[rollout_id]
            state.current_phase = RolloutPhase.ROLLING_BACK
            state.rollback_reason = reason or "Manual abort"

            # Cancel the rollout task
            if rollout_id in self._rollout_tasks:
                self._rollout_tasks[rollout_id].cancel()

            # Trigger rollback
            await self._rollback_rollout(state)

            self.logger.info(f"Rollout {rollout_id} aborted: {reason}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to abort rollout {rollout_id}: {str(e)}")
            return False

    async def list_active_rollouts(self) -> list[RolloutState]:
        """List all active rollouts."""
        return list(self.active_rollouts.values())

    async def _execute_rollout(self, state: RolloutState):
        """Execute the complete rollout process."""
        try:
            with self.monitoring.create_span(
                "rollout_execution", state.config.service_name
            ) as span:
                span.set_tag("rollout_id", state.rollout_id)
                span.set_tag("strategy", state.config.strategy)

                # Phase 1: Deploy new version
                await self._deploy_new_version(state)

                # Phase 2: Execute rollout strategy
                if state.config.strategy == RolloutStrategy.PROGRESSIVE:
                    await self._execute_progressive_rollout(state)
                elif state.config.strategy == RolloutStrategy.CANARY:
                    await self._execute_canary_rollout(state)
                elif state.config.strategy == RolloutStrategy.BLUE_GREEN:
                    await self._execute_blue_green_rollout(state)
                elif state.config.strategy == RolloutStrategy.A_B_TEST:
                    await self._execute_ab_test_rollout(state)
                elif state.config.strategy == RolloutStrategy.FEATURE_FLAG:
                    await self._execute_feature_flag_rollout(state)

                state.current_phase = RolloutPhase.COMPLETED

                # Record success metrics
                duration = (datetime.now() - state.start_time).total_seconds()
                self.monitoring.record_histogram(
                    "rollout_duration_seconds",
                    duration,
                    {
                        "service": state.config.service_name,
                        "strategy": state.config.strategy,
                        "status": "success",
                    },
                )

                self.logger.info(f"Rollout {state.rollout_id} completed successfully")

        except Exception as e:
            state.current_phase = RolloutPhase.FAILED
            state.errors.append(str(e))

            self.logger.error(f"Rollout {state.rollout_id} failed: {str(e)}")

            # Auto-rollback if configured
            if state.config.auto_rollback:
                try:
                    await self._rollback_rollout(state)
                except Exception as rollback_error:
                    self.logger.error(
                        f"Rollback failed for {state.rollout_id}: {str(rollback_error)}"
                    )

            # Record failure metrics
            duration = (datetime.now() - state.start_time).total_seconds()
            self.monitoring.record_histogram(
                "rollout_duration_seconds",
                duration,
                {
                    "service": state.config.service_name,
                    "strategy": state.config.strategy,
                    "status": "failure",
                },
            )

        finally:
            # Cleanup
            if state.rollout_id in self._rollout_tasks:
                del self._rollout_tasks[state.rollout_id]

    async def _deploy_new_version(self, state: RolloutState):
        """Deploy the new version with zero traffic initially."""
        state.current_phase = RolloutPhase.DEPLOYING

        try:
            # Deploy new version
            new_deployment = await self.deployment.deploy_service(
                state.config.deployment_spec
            )

            new_version = f"v{state.config.deployment_spec.tag}"
            state.deployment_ids[new_version] = new_deployment.deployment_id

            self.logger.info(
                f"Deployed new version {new_version} for rollout {state.rollout_id}"
            )

        except Exception as e:
            raise Exception(f"Failed to deploy new version: {str(e)}") from e

    async def _execute_progressive_rollout(self, state: RolloutState):
        """Execute progressive rollout strategy."""
        for phase_index, target_percentage in enumerate(state.config.phases):
            state.phase_index = phase_index
            state.current_traffic_percentage = target_percentage
            state.phase_start_time = datetime.now()
            state.current_phase = RolloutPhase.MONITORING

            self.logger.info(
                f"Rollout {state.rollout_id} phase {phase_index + 1}: {target_percentage}% traffic"
            )

            # Update traffic split
            if self.traffic_manager:
                await self._update_traffic_split(state, target_percentage)

            # Monitor phase
            await self._monitor_phase(state)

            # Validate metrics
            if not await self._validate_phase_metrics(state):
                raise Exception(f"Phase {phase_index + 1} validation failed")

            # Wait for phase duration (except for final phase)
            if phase_index < len(state.config.phases) - 1:
                await asyncio.sleep(state.config.phase_duration_minutes * 60)

    async def _execute_canary_rollout(self, state: RolloutState):
        """Execute canary rollout strategy."""
        # Deploy canary with small percentage
        canary_percentage = state.config.phases[0] if state.config.phases else 5

        state.current_traffic_percentage = canary_percentage
        state.phase_start_time = datetime.now()
        state.current_phase = RolloutPhase.MONITORING

        self.logger.info(
            f"Rollout {state.rollout_id} canary phase: {canary_percentage}% traffic"
        )

        # Update traffic split
        if self.traffic_manager:
            await self._update_traffic_split(state, canary_percentage)

        # Extended monitoring for canary
        monitoring_duration = (
            state.config.phase_duration_minutes * 2
        )  # Double the monitoring time
        for _ in range(monitoring_duration):
            await asyncio.sleep(60)  # Check every minute

            if not await self._validate_phase_metrics(state):
                raise Exception("Canary validation failed")

        # If canary is successful, promote to full traffic
        state.current_phase = RolloutPhase.PROMOTING
        if self.traffic_manager:
            await self._update_traffic_split(state, 100)

        state.current_traffic_percentage = 100

    async def _execute_blue_green_rollout(self, state: RolloutState):
        """Execute blue-green rollout strategy."""
        state.current_phase = RolloutPhase.VALIDATING

        # Run validation tests on green (new) environment
        if not await self._validate_deployment(state):
            raise Exception("Green environment validation failed")

        # Switch all traffic to green
        state.current_phase = RolloutPhase.PROMOTING
        state.current_traffic_percentage = 100

        if self.traffic_manager:
            await self._update_traffic_split(state, 100)

        # Monitor for a short period after switch
        await asyncio.sleep(state.config.validation_duration_minutes * 60)

        if not await self._validate_phase_metrics(state):
            raise Exception("Blue-green validation failed after traffic switch")

    async def _execute_ab_test_rollout(self, state: RolloutState):
        """Execute A/B test rollout strategy."""
        # Split traffic 50/50 for A/B testing
        ab_split = 50

        state.current_traffic_percentage = ab_split
        state.phase_start_time = datetime.now()
        state.current_phase = RolloutPhase.MONITORING

        if self.traffic_manager:
            await self._update_traffic_split(state, ab_split)

        # Run A/B test for extended period
        test_duration = state.config.phase_duration_minutes * 4  # 4x normal duration
        await asyncio.sleep(test_duration * 60)

        # Analyze A/B test results
        winner_version = await self._analyze_ab_results(state)

        if winner_version == "new":
            # Promote new version to 100%
            state.current_phase = RolloutPhase.PROMOTING
            if self.traffic_manager:
                await self._update_traffic_split(state, 100)
            state.current_traffic_percentage = 100
        else:
            # Rollback to old version
            raise Exception("A/B test showed old version performing better")

    async def _execute_feature_flag_rollout(self, state: RolloutState):
        """Execute feature flag-based rollout."""
        if not self.feature_flag_manager:
            raise Exception("Feature flag manager not configured")

        flag_name = f"{state.config.service_name}_rollout"

        for phase_index, target_percentage in enumerate(state.config.phases):
            state.phase_index = phase_index
            state.current_traffic_percentage = target_percentage
            state.phase_start_time = datetime.now()
            state.current_phase = RolloutPhase.MONITORING

            # Update feature flag
            await self.feature_flag_manager.enable_flag(flag_name, target_percentage)

            # Monitor phase
            await self._monitor_phase(state)

            # Validate metrics
            if not await self._validate_phase_metrics(state):
                # Disable flag and rollback
                await self.feature_flag_manager.disable_flag(flag_name)
                raise Exception(
                    f"Feature flag phase {phase_index + 1} validation failed"
                )

            # Wait for phase duration
            if phase_index < len(state.config.phases) - 1:
                await asyncio.sleep(state.config.phase_duration_minutes * 60)

    async def _update_traffic_split(self, state: RolloutState, new_percentage: int):
        """Update traffic split between versions."""
        if not self.traffic_manager:
            return

        old_percentage = 100 - new_percentage

        version_weights = {"old": old_percentage, "new": new_percentage}

        await self.traffic_manager.set_traffic_split(
            state.config.service_name, version_weights
        )

        self.logger.info(
            f"Updated traffic split for {state.config.service_name}: {version_weights}"
        )

    async def _monitor_phase(self, state: RolloutState):
        """Monitor current rollout phase."""
        try:
            # Collect metrics for validation duration
            for minute in range(state.config.validation_duration_minutes):
                # Get metrics for both versions
                metrics = await self._collect_rollout_metrics(state)

                # Store metrics in history
                metrics["timestamp"] = datetime.now()
                metrics["phase_index"] = state.phase_index
                metrics["traffic_percentage"] = state.current_traffic_percentage
                state.metrics_history.append(metrics)

                # Emit monitoring metrics
                self.monitoring.record_gauge(
                    "rollout_phase_progress",
                    minute / state.config.validation_duration_minutes * 100,
                    {"rollout_id": state.rollout_id, "phase": str(state.phase_index)},
                )

                if minute < state.config.validation_duration_minutes - 1:
                    await asyncio.sleep(60)  # Wait 1 minute between collections

        except Exception as e:
            state.errors.append(f"Monitoring error: {str(e)}")
            raise

    async def _collect_rollout_metrics(self, state: RolloutState) -> dict[str, Any]:
        """Collect metrics for rollout validation."""
        try:
            new_version = f"v{state.config.deployment_spec.tag}"

            # Collect metrics for new version
            new_metrics = await self.metrics_collector.collect_metrics(
                state.config.service_name,
                new_version,
                state.config.validation_duration_minutes,
            )

            # Also collect metrics for old version if traffic is split
            old_metrics = {}
            if state.current_traffic_percentage < 100:
                old_metrics = await self.metrics_collector.collect_metrics(
                    state.config.service_name,
                    "old",
                    state.config.validation_duration_minutes,
                )

            return {
                "new_version": new_metrics,
                "old_version": old_metrics,
                "traffic_percentage": state.current_traffic_percentage,
            }

        except Exception as e:
            self.logger.error(f"Failed to collect rollout metrics: {str(e)}")
            return {}

    async def _validate_phase_metrics(self, state: RolloutState) -> bool:
        """Validate metrics against thresholds."""
        if not state.metrics_history:
            self.logger.warning("No metrics available for validation")
            return True  # Allow if no metrics available

        try:
            # Get latest metrics
            latest_metrics = state.metrics_history[-1]
            new_version_metrics = latest_metrics.get("new_version", {})

            thresholds = state.config.metrics_thresholds

            # Validate error rate
            if "error_rate" in new_version_metrics:
                if new_version_metrics["error_rate"] > thresholds.error_rate_threshold:
                    self.logger.error(
                        f"Error rate too high: {new_version_metrics['error_rate']} > {thresholds.error_rate_threshold}"
                    )
                    return False

            # Validate response time
            if "response_time_p95" in new_version_metrics:
                if (
                    new_version_metrics["response_time_p95"]
                    > thresholds.response_time_p95_threshold
                ):
                    self.logger.error(
                        f"Response time too high: {new_version_metrics['response_time_p95']} > {thresholds.response_time_p95_threshold}"
                    )
                    return False

            # Validate success rate
            if "success_rate" in new_version_metrics:
                if (
                    new_version_metrics["success_rate"]
                    < thresholds.success_rate_threshold
                ):
                    self.logger.error(
                        f"Success rate too low: {new_version_metrics['success_rate']} < {thresholds.success_rate_threshold}"
                    )
                    return False

            # Validate resource usage
            if "cpu_usage" in new_version_metrics:
                if new_version_metrics["cpu_usage"] > thresholds.cpu_threshold:
                    self.logger.error(
                        f"CPU usage too high: {new_version_metrics['cpu_usage']} > {thresholds.cpu_threshold}"
                    )
                    return False

            if "memory_usage" in new_version_metrics:
                if new_version_metrics["memory_usage"] > thresholds.memory_threshold:
                    self.logger.error(
                        f"Memory usage too high: {new_version_metrics['memory_usage']} > {thresholds.memory_threshold}"
                    )
                    return False

            # Validate custom metrics
            for metric_name, threshold in thresholds.custom_metrics.items():
                if metric_name in new_version_metrics:
                    if new_version_metrics[metric_name] > threshold:
                        self.logger.error(
                            f"Custom metric {metric_name} exceeded threshold: {new_version_metrics[metric_name]} > {threshold}"
                        )
                        return False

            self.logger.info(f"Phase validation passed for rollout {state.rollout_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Validation error for rollout {state.rollout_id}: {str(e)}"
            )
            return False

    async def _validate_deployment(self, state: RolloutState) -> bool:
        """Validate deployment health before traffic switch."""
        try:
            new_version = f"v{state.config.deployment_spec.tag}"
            deployment_id = state.deployment_ids.get(new_version)

            if not deployment_id:
                return False

            # Check deployment status
            deployment_result = await self.deployment.get_deployment_status(
                deployment_id
            )
            if (
                not deployment_result
                or deployment_result.status != DeploymentStatus.SUCCEEDED
            ):
                return False

            # Run health checks
            if state.config.deployment_spec.health_checks:
                for health_check in state.config.deployment_spec.health_checks:
                    try:
                        if health_check.type.value == "http":
                            import aiohttp

                            async with aiohttp.ClientSession(
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as session:
                                async with session.get(
                                    health_check.endpoint,
                                    timeout=health_check.timeout_seconds,
                                ) as response:
                                    if response.status != health_check.expected_status:
                                        return False
                    except Exception:
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Deployment validation failed: {str(e)}")
            return False

    async def _analyze_ab_results(self, state: RolloutState) -> str:
        """Analyze A/B test results to determine winner."""
        try:
            if not state.metrics_history:
                return "old"  # Default to old if no data

            # Aggregate metrics across the test period
            new_version_metrics = []
            old_version_metrics = []

            for metrics_snapshot in state.metrics_history[-10:]:  # Last 10 snapshots
                new_metrics = metrics_snapshot.get("new_version", {})
                old_metrics = metrics_snapshot.get("old_version", {})

                if new_metrics:
                    new_version_metrics.append(new_metrics)
                if old_metrics:
                    old_version_metrics.append(old_metrics)

            if not new_version_metrics or not old_version_metrics:
                return "old"

            # Compare key metrics
            new_avg_error_rate = sum(
                m.get("error_rate", 0) for m in new_version_metrics
            ) / len(new_version_metrics)
            old_avg_error_rate = sum(
                m.get("error_rate", 0) for m in old_version_metrics
            ) / len(old_version_metrics)

            new_avg_response_time = sum(
                m.get("response_time_p95", 0) for m in new_version_metrics
            ) / len(new_version_metrics)
            old_avg_response_time = sum(
                m.get("response_time_p95", 0) for m in old_version_metrics
            ) / len(old_version_metrics)

            # Simple scoring: new version wins if it has lower error rate AND lower response time
            if (
                new_avg_error_rate < old_avg_error_rate
                and new_avg_response_time < old_avg_response_time
            ):
                self.logger.info(
                    f"A/B test winner: new version (error_rate: {new_avg_error_rate:.4f} vs {old_avg_error_rate:.4f}, response_time: {new_avg_response_time:.2f} vs {old_avg_response_time:.2f})"
                )
                return "new"
            else:
                self.logger.info(
                    f"A/B test winner: old version (error_rate: {new_avg_error_rate:.4f} vs {old_avg_error_rate:.4f}, response_time: {new_avg_response_time:.2f} vs {old_avg_response_time:.2f})"
                )
                return "old"

        except Exception as e:
            self.logger.error(f"A/B analysis failed: {str(e)}")
            return "old"  # Default to old on error

    async def _rollback_rollout(self, state: RolloutState):
        """Rollback a failed rollout."""
        try:
            state.current_phase = RolloutPhase.ROLLING_BACK

            self.logger.info(f"Rolling back rollout {state.rollout_id}")

            # Revert traffic to old version
            if self.traffic_manager:
                await self.traffic_manager.set_traffic_split(
                    state.config.service_name, {"old": 100, "new": 0}
                )

            # Disable feature flags if used
            if (
                state.config.strategy == RolloutStrategy.FEATURE_FLAG
                and self.feature_flag_manager
            ):
                flag_name = f"{state.config.service_name}_rollout"
                await self.feature_flag_manager.disable_flag(flag_name)

            # Rollback deployment
            new_version = f"v{state.config.deployment_spec.tag}"
            deployment_id = state.deployment_ids.get(new_version)
            if deployment_id:
                await self.deployment.rollback_service(
                    deployment_id, state.rollback_reason or "Rollout validation failed"
                )

            state.current_phase = RolloutPhase.FAILED

            self.logger.info(f"Rollback completed for rollout {state.rollout_id}")

        except Exception as e:
            self.logger.error(
                f"Rollback failed for rollout {state.rollout_id}: {str(e)}"
            )
            raise


class RolloutFactory:
    """Factory for creating rollout orchestrator instances."""

    @staticmethod
    def create_prometheus_based_rollout(
        deployment: DeploymentAutomation,
        monitoring: MonitoringStack,
        prometheus_url: str,
        traffic_manager: Optional[TrafficManager] = None,
        feature_flag_manager: Optional[FeatureFlagManager] = None,
    ) -> RolloutOrchestrator:
        """Create rollout orchestrator with Prometheus metrics collection."""
        metrics_collector = PrometheusMetricsCollector(prometheus_url, monitoring)
        return RolloutOrchestrator(
            deployment=deployment,
            monitoring=monitoring,
            metrics_collector=metrics_collector,
            traffic_manager=traffic_manager,
            feature_flag_manager=feature_flag_manager,
        )

    @staticmethod
    def create_istio_integrated_rollout(
        deployment: DeploymentAutomation,
        monitoring: MonitoringStack,
        prometheus_url: str,
        namespace: str = "default",
        feature_flag_manager: Optional[FeatureFlagManager] = None,
    ) -> RolloutOrchestrator:
        """Create rollout orchestrator with Istio traffic management."""
        metrics_collector = PrometheusMetricsCollector(prometheus_url, monitoring)
        traffic_manager = IstioTrafficManager(namespace)
        return RolloutOrchestrator(
            deployment=deployment,
            monitoring=monitoring,
            metrics_collector=metrics_collector,
            traffic_manager=traffic_manager,
            feature_flag_manager=feature_flag_manager,
        )


# Convenience function for easy setup
async def setup_advanced_rollout(
    deployment: DeploymentAutomation,
    monitoring: MonitoringStack,
    prometheus_url: str,
    use_istio: bool = False,
    namespace: str = "default",
) -> RolloutOrchestrator:
    """Setup advanced rollout orchestrator with sensible defaults."""
    factory = RolloutFactory()

    if use_istio:
        return factory.create_istio_integrated_rollout(
            deployment, monitoring, prometheus_url, namespace
        )
    else:
        return factory.create_prometheus_based_rollout(
            deployment, monitoring, prometheus_url
        )
