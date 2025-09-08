"""
Chaos Engineering Framework for DotMac

Provides comprehensive chaos testing capabilities including:
- Failure injection mechanisms
- Service disruption scenarios
- Network partitioning
- Resource exhaustion simulation
- Recovery validation
- Resilience metrics collection

Key Features:
- Configurable chaos experiments
- Safe rollback mechanisms
- Observability and monitoring
- Multi-service coordination
- Gradual failure introduction
"""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from dotmac_shared.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class ChaosExperimentState(Enum):
    """States of a chaos experiment."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class FailureType(Enum):
    """Types of failures that can be injected."""

    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_CONNECTION_LOSS = "database_connection_loss"
    NETWORK_PARTITION = "network_partition"
    HIGH_LATENCY = "high_latency"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    MESSAGE_LOSS = "message_loss"
    CORRUPTION = "corruption"
    TIMEOUT = "timeout"
    AUTHENTICATION_FAILURE = "authentication_failure"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


@dataclass
class ChaosMetrics:
    """Metrics collected during chaos experiments."""

    experiment_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    failures_injected: int = 0
    recovery_time: Optional[float] = None
    error_rate: float = 0.0
    throughput_impact: float = 0.0
    availability_percentage: float = 100.0
    custom_metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate experiment duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class FailureInjection:
    """Configuration for a specific failure injection."""

    failure_type: FailureType
    target_service: str
    target_component: Optional[str] = None
    probability: float = 1.0  # 0.0 to 1.0
    duration: Optional[timedelta] = None
    parameters: dict[str, Any] = field(default_factory=dict)
    conditions: list[Callable[[], bool]] = field(default_factory=list)

    def should_inject(self) -> bool:
        """Determine if failure should be injected based on conditions and probability."""
        # Check conditions
        if self.conditions and not all(condition() for condition in self.conditions):
            return False

        # Check probability
        return random.random() < self.probability


class FailureInjector(ABC):
    """Abstract base class for failure injectors."""

    def __init__(self, name: str):
        self.name = name
        self.active_failures: set[str] = set()

    @abstractmethod
    async def inject_failure(self, injection: FailureInjection) -> str:
        """Inject a failure and return injection ID."""
        pass

    @abstractmethod
    async def remove_failure(self, injection_id: str) -> bool:
        """Remove an injected failure."""
        pass

    @abstractmethod
    def supports_failure_type(self, failure_type: FailureType) -> bool:
        """Check if injector supports this failure type."""
        pass


class NetworkFailureInjector(FailureInjector):
    """Injector for network-related failures."""

    def __init__(self):
        super().__init__("network")
        self._network_rules: dict[str, dict[str, Any]] = {}

    def supports_failure_type(self, failure_type: FailureType) -> bool:
        return failure_type in {
            FailureType.NETWORK_PARTITION,
            FailureType.HIGH_LATENCY,
            FailureType.MESSAGE_LOSS,
        }

    async def inject_failure(self, injection: FailureInjection) -> str:
        """Inject network failure."""
        injection_id = str(uuid4())

        if injection.failure_type == FailureType.NETWORK_PARTITION:
            await self._inject_network_partition(injection_id, injection)
        elif injection.failure_type == FailureType.HIGH_LATENCY:
            await self._inject_latency(injection_id, injection)
        elif injection.failure_type == FailureType.MESSAGE_LOSS:
            await self._inject_message_loss(injection_id, injection)

        self.active_failures.add(injection_id)
        logger.info(f"Injected {injection.failure_type.value} for {injection.target_service}")
        return injection_id

    async def remove_failure(self, injection_id: str) -> bool:
        """Remove network failure."""
        if injection_id not in self.active_failures:
            return False

        if injection_id in self._network_rules:
            rule = self._network_rules[injection_id]
            await self._remove_network_rule(rule)
            del self._network_rules[injection_id]

        self.active_failures.discard(injection_id)
        logger.info(f"Removed network failure injection {injection_id}")
        return True

    async def _inject_network_partition(self, injection_id: str, injection: FailureInjection):
        """Simulate network partition."""
        rule = {
            "type": "partition",
            "source": injection.target_service,
            "target": injection.parameters.get("partition_target", "database"),
            "block_percentage": injection.parameters.get("block_percentage", 100),
        }
        self._network_rules[injection_id] = rule
        # In real implementation, this would configure network rules

    async def _inject_latency(self, injection_id: str, injection: FailureInjection):
        """Inject network latency."""
        rule = {
            "type": "latency",
            "target": injection.target_service,
            "delay_ms": injection.parameters.get("delay_ms", 1000),
            "jitter_ms": injection.parameters.get("jitter_ms", 100),
        }
        self._network_rules[injection_id] = rule

    async def _inject_message_loss(self, injection_id: str, injection: FailureInjection):
        """Inject message loss."""
        rule = {
            "type": "message_loss",
            "target": injection.target_service,
            "loss_percentage": injection.parameters.get("loss_percentage", 10),
        }
        self._network_rules[injection_id] = rule

    async def _remove_network_rule(self, rule: dict[str, Any]):
        """Remove network rule (implementation would interact with actual network layer)."""
        pass


class ServiceFailureInjector(FailureInjector):
    """Injector for service-level failures."""

    def __init__(self, service_registry: Optional[dict[str, Any]] = None):
        super().__init__("service")
        self.service_registry = service_registry or {}
        self._service_overrides: dict[str, dict[str, Any]] = {}

    def supports_failure_type(self, failure_type: FailureType) -> bool:
        return failure_type in {
            FailureType.SERVICE_UNAVAILABLE,
            FailureType.TIMEOUT,
            FailureType.AUTHENTICATION_FAILURE,
            FailureType.PERMISSION_DENIED,
            FailureType.RATE_LIMIT_EXCEEDED,
            FailureType.CIRCUIT_BREAKER_OPEN,
        }

    async def inject_failure(self, injection: FailureInjection) -> str:
        """Inject service failure."""
        injection_id = str(uuid4())

        if injection.failure_type == FailureType.SERVICE_UNAVAILABLE:
            await self._make_service_unavailable(injection_id, injection)
        elif injection.failure_type == FailureType.TIMEOUT:
            await self._inject_timeout(injection_id, injection)
        elif injection.failure_type == FailureType.AUTHENTICATION_FAILURE:
            await self._inject_auth_failure(injection_id, injection)
        elif injection.failure_type == FailureType.RATE_LIMIT_EXCEEDED:
            await self._inject_rate_limit(injection_id, injection)

        self.active_failures.add(injection_id)
        logger.info(f"Injected {injection.failure_type.value} for {injection.target_service}")
        return injection_id

    async def remove_failure(self, injection_id: str) -> bool:
        """Remove service failure."""
        if injection_id not in self.active_failures:
            return False

        if injection_id in self._service_overrides:
            override = self._service_overrides[injection_id]
            await self._remove_service_override(override)
            del self._service_overrides[injection_id]

        self.active_failures.discard(injection_id)
        logger.info(f"Removed service failure injection {injection_id}")
        return True

    async def _make_service_unavailable(self, injection_id: str, injection: FailureInjection):
        """Make service unavailable."""
        override = {
            "service": injection.target_service,
            "type": "unavailable",
            "status_code": injection.parameters.get("status_code", 503),
            "error_message": injection.parameters.get("error_message", "Service Unavailable"),
        }
        self._service_overrides[injection_id] = override

    async def _inject_timeout(self, injection_id: str, injection: FailureInjection):
        """Inject timeout errors."""
        override = {
            "service": injection.target_service,
            "type": "timeout",
            "timeout_ms": injection.parameters.get("timeout_ms", 30000),
        }
        self._service_overrides[injection_id] = override

    async def _inject_auth_failure(self, injection_id: str, injection: FailureInjection):
        """Inject authentication failures."""
        override = {
            "service": injection.target_service,
            "type": "auth_failure",
            "status_code": 401,
            "error_message": "Authentication Failed",
        }
        self._service_overrides[injection_id] = override

    async def _inject_rate_limit(self, injection_id: str, injection: FailureInjection):
        """Inject rate limit errors."""
        override = {
            "service": injection.target_service,
            "type": "rate_limit",
            "status_code": 429,
            "retry_after": injection.parameters.get("retry_after", 60),
        }
        self._service_overrides[injection_id] = override

    async def _remove_service_override(self, override: dict[str, Any]):
        """Remove service override (implementation would restore normal behavior)."""
        pass


class DatabaseFailureInjector(FailureInjector):
    """Injector for database-related failures."""

    def __init__(self):
        super().__init__("database")
        self._db_overrides: dict[str, dict[str, Any]] = {}

    def supports_failure_type(self, failure_type: FailureType) -> bool:
        return failure_type in {
            FailureType.DATABASE_CONNECTION_LOSS,
            FailureType.HIGH_LATENCY,
            FailureType.CORRUPTION,
        }

    async def inject_failure(self, injection: FailureInjection) -> str:
        """Inject database failure."""
        injection_id = str(uuid4())

        if injection.failure_type == FailureType.DATABASE_CONNECTION_LOSS:
            await self._inject_connection_loss(injection_id, injection)
        elif injection.failure_type == FailureType.HIGH_LATENCY:
            await self._inject_db_latency(injection_id, injection)
        elif injection.failure_type == FailureType.CORRUPTION:
            await self._inject_corruption(injection_id, injection)

        self.active_failures.add(injection_id)
        return injection_id

    async def remove_failure(self, injection_id: str) -> bool:
        """Remove database failure."""
        if injection_id not in self.active_failures:
            return False

        if injection_id in self._db_overrides:
            del self._db_overrides[injection_id]

        self.active_failures.discard(injection_id)
        return True

    async def _inject_connection_loss(self, injection_id: str, injection: FailureInjection):
        """Inject database connection loss."""
        override = {
            "type": "connection_loss",
            "target_db": injection.target_service,
            "error_message": "Connection to database lost",
        }
        self._db_overrides[injection_id] = override

    async def _inject_db_latency(self, injection_id: str, injection: FailureInjection):
        """Inject database latency."""
        override = {
            "type": "latency",
            "target_db": injection.target_service,
            "delay_ms": injection.parameters.get("delay_ms", 2000),
        }
        self._db_overrides[injection_id] = override

    async def _inject_corruption(self, injection_id: str, injection: FailureInjection):
        """Inject data corruption."""
        override = {
            "type": "corruption",
            "target_db": injection.target_service,
            "corruption_rate": injection.parameters.get("corruption_rate", 0.01),
        }
        self._db_overrides[injection_id] = override


class ChaosExperiment:
    """Represents a chaos engineering experiment."""

    def __init__(
        self,
        name: str,
        description: str,
        hypothesis: str,
        failure_injections: list[FailureInjection],
        duration: timedelta,
        steady_state_validators: Optional[list[Callable[[], bool]]] = None,
        rollback_conditions: Optional[list[Callable[[], bool]]] = None,
    ):
        self.id = str(uuid4())
        self.name = name
        self.description = description
        self.hypothesis = hypothesis
        self.failure_injections = failure_injections
        self.duration = duration
        self.steady_state_validators = steady_state_validators or []
        self.rollback_conditions = rollback_conditions or []

        self.state = ChaosExperimentState.PENDING
        self.metrics = ChaosMetrics(experiment_id=self.id, start_time=utc_now())
        self.injector_registry: dict[str, FailureInjector] = {}
        self.active_injections: list[str] = []

    def add_injector(self, injector: FailureInjector):
        """Add a failure injector to the experiment."""
        self.injector_registry[injector.name] = injector

    async def run(self) -> ChaosMetrics:
        """Execute the chaos experiment."""
        try:
            self.state = ChaosExperimentState.RUNNING
            self.metrics.start_time = utc_now()

            logger.info(f"Starting chaos experiment: {self.name}")
            logger.info(f"Hypothesis: {self.hypothesis}")

            # Validate steady state before experiment
            if not await self._validate_steady_state():
                raise Exception("System not in steady state before experiment")

            # Inject failures
            await self._inject_failures()

            # Monitor system during experiment
            await self._monitor_experiment()

            # Validate system behavior
            await self._validate_experiment_results()

            self.state = ChaosExperimentState.COMPLETED

        except Exception as e:
            logger.error(f"Chaos experiment failed: {e}")
            self.state = ChaosExperimentState.FAILED
            await self._emergency_rollback()

        finally:
            # Clean up all injections
            await self._cleanup_injections()
            self.metrics.end_time = utc_now()

        return self.metrics

    async def _validate_steady_state(self) -> bool:
        """Validate system is in steady state."""
        for validator in self.steady_state_validators:
            try:
                if not validator():
                    return False
            except Exception as e:
                logger.warning(f"Steady state validator failed: {e}")
                return False
        return True

    async def _inject_failures(self):
        """Inject all configured failures."""
        for injection in self.failure_injections:
            if injection.should_inject():
                # Find appropriate injector
                injector = self._find_injector(injection.failure_type)
                if injector:
                    injection_id = await injector.inject_failure(injection)
                    self.active_injections.append(injection_id)
                    self.metrics.failures_injected += 1

                    # Schedule removal if duration specified
                    if injection.duration:
                        asyncio.create_task(
                            self._schedule_injection_removal(injector, injection_id, injection.duration)
                        )

    def _find_injector(self, failure_type: FailureType) -> Optional[FailureInjector]:
        """Find injector that supports the failure type."""
        for injector in self.injector_registry.values():
            if injector.supports_failure_type(failure_type):
                return injector
        return None

    async def _schedule_injection_removal(self, injector: FailureInjector, injection_id: str, duration: timedelta):
        """Schedule removal of injection after specified duration."""
        await asyncio.sleep(duration.total_seconds())
        await injector.remove_failure(injection_id)

    async def _monitor_experiment(self):
        """Monitor experiment during execution."""
        start_time = time.time()

        while (time.time() - start_time) < self.duration.total_seconds():
            # Check rollback conditions
            if await self._should_rollback():
                logger.warning("Rollback conditions met, aborting experiment")
                self.state = ChaosExperimentState.ABORTED
                return

            # Collect metrics
            await self._collect_metrics()

            await asyncio.sleep(1)  # Monitor every second

    async def _should_rollback(self) -> bool:
        """Check if experiment should be rolled back."""
        for condition in self.rollback_conditions:
            try:
                if condition():
                    return True
            except Exception as e:
                logger.warning(f"Rollback condition check failed: {e}")
        return False

    async def _collect_metrics(self):
        """Collect experiment metrics."""
        # This would integrate with actual monitoring systems
        # For now, simulate metric collection
        pass

    async def _validate_experiment_results(self):
        """Validate experiment results against hypothesis."""
        # Validate that system behaved as expected
        if not await self._validate_steady_state():
            logger.warning("System not in steady state after experiment")

    async def _emergency_rollback(self):
        """Emergency rollback of all changes."""
        logger.warning("Performing emergency rollback")
        await self._cleanup_injections()

    async def _cleanup_injections(self):
        """Clean up all active injections."""
        for injector in self.injector_registry.values():
            for injection_id in list(injector.active_failures):
                await injector.remove_failure(injection_id)


class ChaosEngineeringFramework:
    """Main framework for chaos engineering experiments."""

    def __init__(self):
        self.experiments: dict[str, ChaosExperiment] = {}
        self.injectors: list[FailureInjector] = []
        self.metrics_history: list[ChaosMetrics] = []

        # Initialize default injectors
        self._initialize_default_injectors()

    def _initialize_default_injectors(self):
        """Initialize default failure injectors."""
        self.injectors = [
            NetworkFailureInjector(),
            ServiceFailureInjector(),
            DatabaseFailureInjector(),
        ]

    def create_experiment(
        self,
        name: str,
        description: str,
        hypothesis: str,
        failure_injections: list[FailureInjection],
        duration: timedelta,
        **kwargs,
    ) -> ChaosExperiment:
        """Create a new chaos experiment."""
        experiment = ChaosExperiment(
            name=name,
            description=description,
            hypothesis=hypothesis,
            failure_injections=failure_injections,
            duration=duration,
            **kwargs,
        )

        # Add injectors to experiment
        for injector in self.injectors:
            experiment.add_injector(injector)

        self.experiments[experiment.id] = experiment
        return experiment

    async def run_experiment(self, experiment_id: str) -> ChaosMetrics:
        """Run a chaos experiment."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        metrics = await experiment.run()
        self.metrics_history.append(metrics)
        return metrics

    def add_injector(self, injector: FailureInjector):
        """Add a custom failure injector."""
        self.injectors.append(injector)

    def get_experiment_results(self, experiment_id: str) -> Optional[ChaosMetrics]:
        """Get results of a completed experiment."""
        experiment = self.experiments.get(experiment_id)
        return experiment.metrics if experiment else None

    @asynccontextmanager
    async def safe_experiment(self, experiment: ChaosExperiment):
        """Context manager for safe experiment execution with automatic cleanup."""
        try:
            yield experiment
        finally:
            # Ensure cleanup even if experiment fails
            await experiment._cleanup_injections()


# Convenience functions for common chaos patterns
def create_service_disruption_experiment(
    service_name: str,
    failure_type: FailureType = FailureType.SERVICE_UNAVAILABLE,
    duration: Optional[timedelta] = None,
) -> list[FailureInjection]:
    """Create failure injections for service disruption testing."""
    if duration is None:
        duration = timedelta(minutes=5)
    return [
        FailureInjection(
            failure_type=failure_type,
            target_service=service_name,
            duration=duration,
            probability=1.0,
        )
    ]


def create_network_partition_experiment(
    source_service: str, target_service: str, duration: Optional[timedelta] = None
) -> list[FailureInjection]:
    """Create failure injections for network partition testing."""
    if duration is None:
        duration = timedelta(minutes=3)
    return [
        FailureInjection(
            failure_type=FailureType.NETWORK_PARTITION,
            target_service=source_service,
            duration=duration,
            parameters={"partition_target": target_service},
        )
    ]


def create_database_failure_experiment(
    database_service: str,
    failure_type: FailureType = FailureType.DATABASE_CONNECTION_LOSS,
    duration: Optional[timedelta] = None,
) -> list[FailureInjection]:
    """Create failure injections for database failure testing."""
    if duration is None:
        duration = timedelta(minutes=2)
    return [
        FailureInjection(
            failure_type=failure_type,
            target_service=database_service,
            duration=duration,
        )
    ]
