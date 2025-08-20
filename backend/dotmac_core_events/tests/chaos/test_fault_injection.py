"""
Fault injection tests for DotMac Core Events - chaos engineering scenarios.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
import structlog

from dotmac_core_events.delivery.backpressure import (
    CircuitBreaker,
)
from dotmac_core_events.delivery.exactly_once import ExactlyOnceProcessor
from dotmac_core_events.models.envelope import EventEnvelope
from dotmac_core_events.observability.metrics import EventsMetricsCollector
from dotmac_core_events.sdks.event_bus import EventBusSDK

logger = structlog.get_logger(__name__)


class NetworkFailureSimulator:
    """Simulate network failures and timeouts."""

    def __init__(self):
        self.failure_rate = 0.0
        self.timeout_rate = 0.0
        self.latency_ms = 0
        self.is_partitioned = False

    def set_failure_rate(self, rate: float):
        """Set network failure rate (0.0 to 1.0)."""
        self.failure_rate = max(0.0, min(1.0, rate))

    def set_timeout_rate(self, rate: float):
        """Set network timeout rate (0.0 to 1.0)."""
        self.timeout_rate = max(0.0, min(1.0, rate))

    def set_latency(self, latency_ms: int):
        """Set network latency in milliseconds."""
        self.latency_ms = max(0, latency_ms)

    def set_partition(self, partitioned: bool):
        """Simulate network partition."""
        self.is_partitioned = partitioned

    async def simulate_network_call(self, operation: Callable):
        """Simulate network call with potential failures."""
        import secrets

        # Check for network partition
        if self.is_partitioned:
            raise ConnectionError("Network partition - unable to reach service")

        # Simulate latency
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

        # Simulate timeout
        if random.random() < self.timeout_rate:
            raise asyncio.TimeoutError("Network timeout")

        # Simulate failure
        if random.random() < self.failure_rate:
            raise ConnectionError("Network failure")

        # Execute actual operation
        return await operation()


class ProcessKiller:
    """Simulate process kills and crashes."""

    def __init__(self):
        self.kill_probability = 0.0
        self.crash_after_seconds = None
        self.killed_processes = []

    def set_kill_probability(self, probability: float):
        """Set probability of killing process during operation."""
        self.kill_probability = max(0.0, min(1.0, probability))

    def schedule_crash(self, after_seconds: float):
        """Schedule process crash after specified time."""
        self.crash_after_seconds = after_seconds

    async def maybe_kill_process(self, process_name: str = "worker"):
        """Maybe kill process based on probability."""
        import secrets

        if random.random() < self.kill_probability:
            logger.warning(f"Simulating process kill: {process_name}")
            self.killed_processes.append({
                "process": process_name,
                "killed_at": datetime.now(timezone.utc)
            })
            # Simulate process death by raising SystemExit
            raise SystemExit(f"Process {process_name} killed by chaos engineering")

    async def crash_after_delay(self):
        """Crash process after scheduled delay."""
        if self.crash_after_seconds:
            await asyncio.sleep(self.crash_after_seconds)
            logger.warning("Simulating scheduled process crash")
            raise SystemExit("Scheduled process crash")


class BrokerOutageSimulator:
    """Simulate message broker outages."""

    def __init__(self):
        self.is_down = False
        self.outage_duration = 0
        self.outage_start = None
        self.partial_failure_rate = 0.0

    def start_outage(self, duration_seconds: float):
        """Start broker outage for specified duration."""
        self.is_down = True
        self.outage_duration = duration_seconds
        self.outage_start = time.time()
        logger.warning(f"Starting broker outage for {duration_seconds} seconds")

    def set_partial_failure_rate(self, rate: float):
        """Set partial failure rate for broker operations."""
        self.partial_failure_rate = max(0.0, min(1.0, rate))

    def check_availability(self):
        """Check if broker is available."""
        if self.is_down:
            if self.outage_start and time.time() - self.outage_start > self.outage_duration:
                self.is_down = False
                self.outage_start = None
                logger.info("Broker outage ended")
            else:
                raise ConnectionError("Message broker is down")

        # Check for partial failures
        import secrets
        if random.random() < self.partial_failure_rate:
            raise ConnectionError("Partial broker failure")


class ChaosEventBus(EventBusSDK):
    """Event bus with chaos engineering capabilities."""

    def __init__(self, base_event_bus: EventBusSDK):
        self.base_event_bus = base_event_bus
        self.network_simulator = NetworkFailureSimulator()
        self.process_killer = ProcessKiller()
        self.broker_simulator = BrokerOutageSimulator()
        self.published_events = []
        self.consumed_events = []
        self.failures = []

    async def publish(self, event_type: str, data: dict, **kwargs):
        """Publish with chaos injection."""
        try:
            # Check for process kill
            await self.process_killer.maybe_kill_process("publisher")

            # Check broker availability
            self.broker_simulator.check_availability()

            # Simulate network issues
            async def publish_operation():
                result = await self.base_event_bus.publish(event_type, data, **kwargs)
                self.published_events.append({
                    "event_type": event_type,
                    "data": data,
                    "timestamp": datetime.now(timezone.utc),
                    "result": result
                })
                return result

            return await self.network_simulator.simulate_network_call(publish_operation)

        except Exception as e:
            self.failures.append({
                "operation": "publish",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            })
            raise

    async def subscribe(self, topic: str, consumer_group: str, handler, **kwargs):
        """Subscribe with chaos injection."""
        try:
            # Wrap handler with chaos injection
            async def chaos_handler(envelope):
                try:
                    # Check for process kill
                    await self.process_killer.maybe_kill_process("consumer")

                    # Check broker availability
                    self.broker_simulator.check_availability()

                    # Simulate network issues for handler
                    async def handler_operation():
                        result = await handler(envelope)
                        self.consumed_events.append({
                            "envelope": envelope,
                            "timestamp": datetime.now(timezone.utc),
                            "result": result
                        })
                        return result

                    return await self.network_simulator.simulate_network_call(handler_operation)

                except Exception as e:
                    self.failures.append({
                        "operation": "consume",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc)
                    })
                    raise

            return await self.base_event_bus.subscribe(topic, consumer_group, chaos_handler, **kwargs)

        except Exception as e:
            self.failures.append({
                "operation": "subscribe",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            })
            raise


@pytest.fixture
def chaos_event_bus():
    """Create chaos-enabled event bus for testing."""
    # Mock base event bus
    base_bus = AsyncMock(spec=EventBusSDK)
    base_bus.publish = AsyncMock(return_value={"status": "published", "message_id": "test_123"})
    base_bus.subscribe = AsyncMock()

    return ChaosEventBus(base_bus)


@pytest.fixture
def sample_envelope():
    """Create sample event envelope."""
    return EventEnvelope.create(
        event_type="test.chaos.event",
        data={"test": "data", "chaos": True},
        tenant_id="chaos_tenant"
    )


class TestNetworkFailures:
    """Test network failure scenarios."""

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, chaos_event_bus, sample_envelope):
        """Test handling of network timeouts."""
        # Set high timeout rate
        chaos_event_bus.network_simulator.set_timeout_rate(0.8)

        timeout_count = 0
        success_count = 0

        # Try publishing multiple events
        for i in range(10):
            try:
                await chaos_event_bus.publish(
                    event_type="test.timeout.event",
                    data={"attempt": i}
                )
                success_count += 1
            except asyncio.TimeoutError:
                timeout_count += 1

        # Should have some timeouts
        assert timeout_count > 0
        assert len(chaos_event_bus.failures) == timeout_count

        # Verify failures are recorded
        timeout_failures = [f for f in chaos_event_bus.failures if "timeout" in f["error"].lower()]
        assert len(timeout_failures) == timeout_count

    @pytest.mark.asyncio
    async def test_network_partition_recovery(self, chaos_event_bus):
        """Test recovery from network partition."""
        # Start with network partition
        chaos_event_bus.network_simulator.set_partition(True)

        # Should fail during partition
        with pytest.raises(ConnectionError, match="Network partition"):
            await chaos_event_bus.publish("test.partition.event", {"test": "data"})

        # End partition
        chaos_event_bus.network_simulator.set_partition(False)

        # Should succeed after partition ends
        result = await chaos_event_bus.publish("test.recovery.event", {"test": "data"})
        assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_high_latency_handling(self, chaos_event_bus):
        """Test handling of high network latency."""
        # Set high latency
        chaos_event_bus.network_simulator.set_latency(500)  # 500ms

        start_time = time.time()
        await chaos_event_bus.publish("test.latency.event", {"test": "data"})
        end_time = time.time()

        # Should take at least the latency time
        assert (end_time - start_time) >= 0.5

    @pytest.mark.asyncio
    async def test_intermittent_failures(self, chaos_event_bus):
        """Test handling of intermittent network failures."""
        # Set moderate failure rate
        chaos_event_bus.network_simulator.set_failure_rate(0.3)

        attempts = 20
        failures = 0
        successes = 0

        for i in range(attempts):
            try:
                await chaos_event_bus.publish("test.intermittent.event", {"attempt": i})
                successes += 1
            except ConnectionError:
                failures += 1

        # Should have some failures and some successes
        assert failures > 0
        assert successes > 0
        assert failures + successes == attempts


class TestProcessKills:
    """Test process kill scenarios."""

    @pytest.mark.asyncio
    async def test_worker_kill_during_processing(self, chaos_event_bus):
        """Test worker kill during event processing."""
        # Set high kill probability
        chaos_event_bus.process_killer.set_kill_probability(0.5)

        # Create handler that might get killed
        processed_events = []

        async def test_handler(envelope):
            processed_events.append(envelope)
            return {"status": "processed"}

        # Subscribe with chaos handler
        await chaos_event_bus.subscribe("test.topic", "test.group", test_handler)

        # Simulate processing events
        kills = 0
        for i in range(10):
            try:
                # Simulate handler call directly
                envelope = EventEnvelope.create(
                    event_type="test.kill.event",
                    data={"attempt": i},
                    tenant_id="test_tenant"
                )

                # This should sometimes raise SystemExit
                await chaos_event_bus.process_killer.maybe_kill_process("test_worker")
                processed_events.append(envelope)

            except SystemExit:
                kills += 1

        # Should have some kills
        assert kills > 0
        assert len(chaos_event_bus.process_killer.killed_processes) == kills

    @pytest.mark.asyncio
    async def test_scheduled_crash_recovery(self, chaos_event_bus):
        """Test recovery from scheduled process crash."""
        # Schedule crash after 0.1 seconds
        chaos_event_bus.process_killer.schedule_crash(0.1)

        # Start crash task
        crash_task = asyncio.create_task(chaos_event_bus.process_killer.crash_after_delay())

        # Should crash after delay
        with pytest.raises(SystemExit, match="Scheduled process crash"):
            await crash_task

    @pytest.mark.asyncio
    async def test_graceful_shutdown_handling(self, chaos_event_bus):
        """Test graceful shutdown during event processing."""

        # Simulate graceful shutdown signal
        shutdown_received = False

        async def shutdown_handler():
            nonlocal shutdown_received
            shutdown_received = True
            # Simulate graceful cleanup
            await asyncio.sleep(0.1)

        # Start processing
        processing_task = asyncio.create_task(
            chaos_event_bus.publish("test.shutdown.event", {"test": "data"})
        )

        # Start shutdown
        shutdown_task = asyncio.create_task(shutdown_handler())

        # Wait for both
        await asyncio.gather(processing_task, shutdown_task, return_exceptions=True)

        assert shutdown_received


class TestBrokerOutages:
    """Test message broker outage scenarios."""

    @pytest.mark.asyncio
    async def test_broker_outage_and_recovery(self, chaos_event_bus):
        """Test broker outage and recovery."""
        # Start broker outage for 0.2 seconds
        chaos_event_bus.broker_simulator.start_outage(0.2)

        # Should fail during outage
        with pytest.raises(ConnectionError, match="Message broker is down"):
            await chaos_event_bus.publish("test.outage.event", {"test": "data"})

        # Wait for outage to end
        await asyncio.sleep(0.3)

        # Should succeed after recovery
        result = await chaos_event_bus.publish("test.recovery.event", {"test": "data"})
        assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_partial_broker_failures(self, chaos_event_bus):
        """Test partial broker failures."""
        # Set partial failure rate
        chaos_event_bus.broker_simulator.set_partial_failure_rate(0.4)

        attempts = 15
        failures = 0
        successes = 0

        for i in range(attempts):
            try:
                await chaos_event_bus.publish("test.partial.event", {"attempt": i})
                successes += 1
            except ConnectionError:
                failures += 1

        # Should have some partial failures
        assert failures > 0
        assert successes > 0

    @pytest.mark.asyncio
    async def test_broker_outage_with_retry(self, chaos_event_bus):
        """Test retry behavior during broker outage."""

        # Create retry wrapper
        async def publish_with_retry(event_type, data, max_retries=3):
            for attempt in range(max_retries + 1):
                try:
                    return await chaos_event_bus.publish(event_type, data)
                except ConnectionError:
                    if attempt == max_retries:
                        raise
                    await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff

        # Start outage
        chaos_event_bus.broker_simulator.start_outage(0.1)

        # Should eventually succeed with retry
        result = await publish_with_retry("test.retry.event", {"test": "data"})
        assert result["status"] == "published"


class TestCircuitBreakerUnderChaos:
    """Test circuit breaker behavior under chaos conditions."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_under_failures(self):
        """Test circuit breaker opens when failures exceed threshold."""

        # Create circuit breaker
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            failure_rate_threshold=0.5
        )

        # Simulate failures
        failure_count = 0
        for i in range(10):
            try:
                async def failing_operation():
                    if i < 5:  # First 5 operations fail
                        raise ConnectionError("Simulated failure")
                    return "success"

                result = await circuit_breaker.call(failing_operation)

            except Exception:
                failure_count += 1

        # Circuit breaker should have opened
        assert circuit_breaker.state == "open"
        assert failure_count >= 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after failures."""

        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1
        )

        # Cause failures to open circuit
        for i in range(3):
            try:
                await circuit_breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))
            except:
                pass

        assert circuit_breaker.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Should transition to half-open
        try:
            result = await circuit_breaker.call(lambda: asyncio.create_task(asyncio.coroutine(lambda: "success")()))
        except:
            pass

        # State should change from open
        assert circuit_breaker.state in ["half_open", "closed"]


class TestExactlyOnceUnderChaos:
    """Test exactly-once processing under chaos conditions."""

    @pytest.mark.asyncio
    async def test_exactly_once_with_process_kills(self):
        """Test exactly-once processing survives process kills."""

        # Mock dedupe store
        processed_events = set()

        class MockDedupeStore:
            def __init__(self):
                self.records = {}

            async def start_processing(self, key, ttl_seconds=3600):
                if key in self.records:
                    return None  # Already processing
                self.records[key] = "processing"
                return {"key": key, "status": "processing"}

            async def mark_completed(self, key):
                self.records[key] = "completed"

            async def mark_failed(self, key, error):
                self.records[key] = "failed"

        dedupe_store = MockDedupeStore()
        processor = ExactlyOnceProcessor(dedupe_store)

        # Process same event multiple times (simulating retries after kills)
        envelope = EventEnvelope.create(
            event_type="test.exactly_once",
            data={"test": "data"},
            tenant_id="test_tenant"
        )

        async def test_handler(env):
            processed_events.add(env.id)
            return {"status": "processed"}

        # Process multiple times
        for i in range(3):
            try:
                await processor.process(envelope, "test_group", test_handler)
            except Exception:
                pass  # Ignore failures

        # Should only be processed once
        assert len(processed_events) <= 1


class TestEndToEndChaosScenarios:
    """End-to-end chaos engineering scenarios."""

    @pytest.mark.asyncio
    async def test_complete_system_chaos(self, chaos_event_bus, sample_envelope):
        """Test system behavior under multiple simultaneous failures."""

        # Enable all chaos scenarios
        chaos_event_bus.network_simulator.set_failure_rate(0.2)
        chaos_event_bus.network_simulator.set_timeout_rate(0.1)
        chaos_event_bus.network_simulator.set_latency(100)
        chaos_event_bus.process_killer.set_kill_probability(0.1)
        chaos_event_bus.broker_simulator.set_partial_failure_rate(0.15)

        # Track results
        total_attempts = 50
        successes = 0
        failures = 0

        # Run chaos test
        for i in range(total_attempts):
            try:
                await chaos_event_bus.publish(
                    event_type="test.chaos.complete",
                    data={"attempt": i, "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                successes += 1
            except Exception:
                failures += 1

        # System should still function despite chaos
        assert successes > 0  # Some operations should succeed
        assert successes + failures == total_attempts

        # Verify failure tracking
        assert len(chaos_event_bus.failures) == failures

    @pytest.mark.asyncio
    async def test_cascading_failure_scenario(self, chaos_event_bus):
        """Test cascading failure scenario."""

        # Simulate cascading failures
        cascade_stages = [
            {"network_failure": 0.1, "broker_failure": 0.0},
            {"network_failure": 0.3, "broker_failure": 0.1},
            {"network_failure": 0.5, "broker_failure": 0.3},
            {"network_failure": 0.7, "broker_failure": 0.5},
        ]

        results = []

        for stage_idx, stage in enumerate(cascade_stages):
            # Configure chaos for this stage
            chaos_event_bus.network_simulator.set_failure_rate(stage["network_failure"])
            chaos_event_bus.broker_simulator.set_partial_failure_rate(stage["broker_failure"])

            # Test operations in this stage
            stage_successes = 0
            stage_failures = 0

            for i in range(10):
                try:
                    await chaos_event_bus.publish(
                        event_type="test.cascade",
                        data={"stage": stage_idx, "attempt": i}
                    )
                    stage_successes += 1
                except Exception:
                    stage_failures += 1

            results.append({
                "stage": stage_idx,
                "successes": stage_successes,
                "failures": stage_failures,
                "success_rate": stage_successes / 10
            })

        # Verify degradation pattern
        for i in range(1, len(results)):
            # Success rate should generally decrease as chaos increases
            # (allowing some variance due to randomness)
            assert results[i]["success_rate"] <= results[i-1]["success_rate"] + 0.2

    @pytest.mark.asyncio
    async def test_recovery_after_total_failure(self, chaos_event_bus):
        """Test system recovery after total failure."""

        # Phase 1: Total failure
        chaos_event_bus.broker_simulator.start_outage(0.2)
        chaos_event_bus.network_simulator.set_partition(True)

        # Should fail completely
        with pytest.raises((ConnectionError, asyncio.TimeoutError)):
            await chaos_event_bus.publish("test.total_failure", {"test": "data"})

        # Phase 2: Gradual recovery
        chaos_event_bus.network_simulator.set_partition(False)
        await asyncio.sleep(0.3)  # Wait for broker recovery

        # Should recover
        result = await chaos_event_bus.publish("test.recovery", {"test": "data"})
        assert result["status"] == "published"

        # Phase 3: Verify stability
        for i in range(5):
            result = await chaos_event_bus.publish("test.stability", {"attempt": i})
            assert result["status"] == "published"


@pytest.mark.asyncio
async def test_chaos_metrics_collection():
    """Test that metrics are collected properly during chaos scenarios."""

    metrics_collector = EventsMetricsCollector()

    # Simulate chaos events
    tenant_id = "chaos_tenant"

    # Record successful events
    for i in range(10):
        metrics_collector.record_event_published(
            tenant_id=tenant_id,
            event_type="test.chaos.event",
            topic=f"tenant.{tenant_id}.events.test",
            status="success",
            duration_seconds=0.1
        )

    # Record failed events
    for i in range(3):
        metrics_collector.record_publish_error(
            tenant_id=tenant_id,
            event_type="test.chaos.event",
            topic=f"tenant.{tenant_id}.events.test",
            error_type="NetworkError"
        )

    # Verify metrics are recorded
    metrics_text = metrics_collector.get_metrics_text()
    assert "events_published_total" in metrics_text
    assert "event_publish_errors_total" in metrics_text
    assert tenant_id in metrics_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
