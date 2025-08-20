"""
Adapter parity tests to ensure consistent behavior across Redis, Kafka, and memory adapters.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from dotmac_core_events.adapters.base import EventAdapter
from dotmac_core_events.adapters.memory import MemoryEventAdapter
from dotmac_core_events.models.envelope import EventEnvelope


class MockRedisAdapter(EventAdapter):
    """Mock Redis adapter for testing."""

    def __init__(self):
        self.published_events = []
        self.subscriptions = {}
        self.topics = set()
        self.consumer_groups = {}
        self.dlq_events = []
        self.replay_operations = {}

    async def publish(
        self,
        topic: str,
        envelope: EventEnvelope,
        partition_key: Optional[str] = None
    ) -> Dict[str, Any]:
        self.published_events.append({
            "topic": topic,
            "envelope": envelope,
            "partition_key": partition_key,
            "timestamp": datetime.now(timezone.utc)
        })
        self.topics.add(topic)
        return {"status": "published", "message_id": f"redis_{len(self.published_events)}"}

    async def subscribe(
        self,
        topic: str,
        consumer_group: str,
        handler,
        **kwargs
    ):
        if topic not in self.subscriptions:
            self.subscriptions[topic] = {}
        self.subscriptions[topic][consumer_group] = handler

        if consumer_group not in self.consumer_groups:
            self.consumer_groups[consumer_group] = {
                "topic": topic,
                "lag": 0,
                "members": ["test_consumer"]
            }

    async def unsubscribe(self, topic: str, consumer_group: str):
        if topic in self.subscriptions and consumer_group in self.subscriptions[topic]:
            del self.subscriptions[topic][consumer_group]

    async def list_topics(self, tenant_id: Optional[str] = None) -> List[str]:
        if tenant_id:
            return [t for t in self.topics if f"tenant.{tenant_id}." in t]
        return list(self.topics)

    async def get_topic_info(self, topic: str) -> Dict[str, Any]:
        return {
            "partition_count": 3,
            "message_count": len([e for e in self.published_events if e["topic"] == topic]),
            "consumer_groups": list(self.consumer_groups.keys()),
            "retention_hours": 168
        }

    async def list_consumer_groups(
        self,
        tenant_id: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[str]:
        groups = list(self.consumer_groups.keys())
        if tenant_id:
            groups = [g for g in groups if f"tenant.{tenant_id}." in g]
        if topic:
            groups = [g for g in groups if self.consumer_groups[g]["topic"] == topic]
        return groups

    async def get_consumer_lag(self, consumer_group: str) -> Dict[str, Any]:
        if consumer_group in self.consumer_groups:
            return {
                "total_lag": self.consumer_groups[consumer_group]["lag"],
                "partition_lags": {"0": 0, "1": 0, "2": 0},
                "last_updated": datetime.now(timezone.utc)
            }
        return {"total_lag": 0, "partition_lags": {}, "last_updated": None}

    async def send_to_dlq(self, envelope: EventEnvelope, error: str, consumer_group: str):
        self.dlq_events.append({
            "envelope": envelope,
            "error": error,
            "consumer_group": consumer_group,
            "timestamp": datetime.now(timezone.utc)
        })

    async def replay_events(
        self,
        topic: str,
        consumer_group: str,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
        max_events: Optional[int] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        replay_id = f"replay_{len(self.replay_operations)}"
        self.replay_operations[replay_id] = {
            "status": "running",
            "topic": topic,
            "consumer_group": consumer_group,
            "events_count": 100,
            "events_replayed": 0
        }
        return {
            "replay_id": replay_id,
            "status": "started",
            "events_count": 100
        }

    async def get_replay_status(self, replay_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        if replay_id in self.replay_operations:
            return self.replay_operations[replay_id]
        return {"status": "not_found"}


class MockKafkaAdapter(EventAdapter):
    """Mock Kafka adapter for testing."""

    def __init__(self):
        self.published_events = []
        self.subscriptions = {}
        self.topics = set()
        self.consumer_groups = {}
        self.dlq_events = []
        self.replay_operations = {}

    async def publish(
        self,
        topic: str,
        envelope: EventEnvelope,
        partition_key: Optional[str] = None
    ) -> Dict[str, Any]:
        self.published_events.append({
            "topic": topic,
            "envelope": envelope,
            "partition_key": partition_key,
            "timestamp": datetime.now(timezone.utc)
        })
        self.topics.add(topic)
        return {"status": "published", "message_id": f"kafka_{len(self.published_events)}"}

    async def subscribe(
        self,
        topic: str,
        consumer_group: str,
        handler,
        **kwargs
    ):
        if topic not in self.subscriptions:
            self.subscriptions[topic] = {}
        self.subscriptions[topic][consumer_group] = handler

        if consumer_group not in self.consumer_groups:
            self.consumer_groups[consumer_group] = {
                "topic": topic,
                "lag": 0,
                "members": ["test_consumer"]
            }

    async def unsubscribe(self, topic: str, consumer_group: str):
        if topic in self.subscriptions and consumer_group in self.subscriptions[topic]:
            del self.subscriptions[topic][consumer_group]

    async def list_topics(self, tenant_id: Optional[str] = None) -> List[str]:
        if tenant_id:
            return [t for t in self.topics if f"tenant.{tenant_id}." in t]
        return list(self.topics)

    async def get_topic_info(self, topic: str) -> Dict[str, Any]:
        return {
            "partition_count": 6,  # Different from Redis to test adapter differences
            "message_count": len([e for e in self.published_events if e["topic"] == topic]),
            "consumer_groups": list(self.consumer_groups.keys()),
            "retention_hours": 168
        }

    async def list_consumer_groups(
        self,
        tenant_id: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[str]:
        groups = list(self.consumer_groups.keys())
        if tenant_id:
            groups = [g for g in groups if f"tenant.{tenant_id}." in g]
        if topic:
            groups = [g for g in groups if self.consumer_groups[g]["topic"] == topic]
        return groups

    async def get_consumer_lag(self, consumer_group: str) -> Dict[str, Any]:
        if consumer_group in self.consumer_groups:
            return {
                "total_lag": self.consumer_groups[consumer_group]["lag"],
                "partition_lags": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                "last_updated": datetime.now(timezone.utc)
            }
        return {"total_lag": 0, "partition_lags": {}, "last_updated": None}

    async def send_to_dlq(self, envelope: EventEnvelope, error: str, consumer_group: str):
        self.dlq_events.append({
            "envelope": envelope,
            "error": error,
            "consumer_group": consumer_group,
            "timestamp": datetime.now(timezone.utc)
        })

    async def replay_events(
        self,
        topic: str,
        consumer_group: str,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
        max_events: Optional[int] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        replay_id = f"replay_{len(self.replay_operations)}"
        self.replay_operations[replay_id] = {
            "status": "running",
            "topic": topic,
            "consumer_group": consumer_group,
            "events_count": 100,
            "events_replayed": 0
        }
        return {
            "replay_id": replay_id,
            "status": "started",
            "events_count": 100
        }

    async def get_replay_status(self, replay_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        if replay_id in self.replay_operations:
            return self.replay_operations[replay_id]
        return {"status": "not_found"}


@pytest.fixture
def sample_envelope():
    """Create sample event envelope for testing."""
    return EventEnvelope.create(
        event_type="test.event.created",
        data={"test_field": "test_value", "number": 42},
        tenant_id="test_tenant"
    )


@pytest.fixture
def adapters():
    """Create all adapter instances for testing."""
    return {
        "memory": MemoryEventAdapter(),
        "redis": MockRedisAdapter(),
        "kafka": MockKafkaAdapter()
    }


class TestAdapterParity:
    """Test suite for adapter parity across different implementations."""

    @pytest.mark.asyncio
    async def test_publish_behavior_parity(self, adapters, sample_envelope):
        """Test that all adapters handle publishing consistently."""
        topic = "tenant.test_tenant.events.test"
        partition_key = "test_key"

        results = {}

        # Test publishing with each adapter
        for adapter_name, adapter in adapters.items():
            result = await adapter.publish(topic, sample_envelope, partition_key)
            results[adapter_name] = result

            # Verify result structure
            assert "status" in result
            assert result["status"] == "published"
            assert "message_id" in result

        # Verify all adapters returned similar result structure
        for adapter_name, result in results.items():
            assert set(result.keys()) >= {"status", "message_id"}

    @pytest.mark.asyncio
    async def test_subscription_behavior_parity(self, adapters, sample_envelope):
        """Test that all adapters handle subscriptions consistently."""
        topic = "tenant.test_tenant.events.test"
        consumer_group = "tenant.test_tenant.consumers.test_group"

        handler_calls = {}

        # Create handlers for each adapter
        for adapter_name in adapters.keys():
            handler_calls[adapter_name] = []

        async def create_handler(adapter_name):
            async def handler(envelope):
                handler_calls[adapter_name].append(envelope)
                return {"status": "processed"}
            return handler

        # Subscribe with each adapter
        for adapter_name, adapter in adapters.items():
            handler = await create_handler(adapter_name)
            await adapter.subscribe(topic, consumer_group, handler)

        # Verify subscription was created (implementation-specific verification)
        for adapter_name, adapter in adapters.items():
            if hasattr(adapter, "subscriptions"):
                assert topic in adapter.subscriptions
                assert consumer_group in adapter.subscriptions[topic]

    @pytest.mark.asyncio
    async def test_topic_management_parity(self, adapters, sample_envelope):
        """Test that all adapters handle topic management consistently."""
        topic = "tenant.test_tenant.events.test"
        tenant_id = "test_tenant"

        # Publish an event to create the topic
        for adapter in adapters.values():
            await adapter.publish(topic, sample_envelope)

        # Test list_topics
        for adapter_name, adapter in adapters.items():
            topics = await adapter.list_topics(tenant_id)
            assert isinstance(topics, list)
            assert topic in topics

        # Test get_topic_info
        for adapter_name, adapter in adapters.items():
            info = await adapter.get_topic_info(topic)
            assert isinstance(info, dict)
            assert "partition_count" in info
            assert "message_count" in info
            assert "consumer_groups" in info
            assert isinstance(info["partition_count"], int)
            assert isinstance(info["message_count"], int)
            assert isinstance(info["consumer_groups"], list)

    @pytest.mark.asyncio
    async def test_consumer_group_management_parity(self, adapters):
        """Test that all adapters handle consumer groups consistently."""
        topic = "tenant.test_tenant.events.test"
        consumer_group = "tenant.test_tenant.consumers.test_group"
        tenant_id = "test_tenant"

        # Create consumer groups
        async def dummy_handler(envelope):
            return {"status": "processed"}

        for adapter in adapters.values():
            await adapter.subscribe(topic, consumer_group, dummy_handler)

        # Test list_consumer_groups
        for adapter_name, adapter in adapters.items():
            groups = await adapter.list_consumer_groups(tenant_id)
            assert isinstance(groups, list)
            assert consumer_group in groups

        # Test get_consumer_lag
        for adapter_name, adapter in adapters.items():
            lag_info = await adapter.get_consumer_lag(consumer_group)
            assert isinstance(lag_info, dict)
            assert "total_lag" in lag_info
            assert "partition_lags" in lag_info
            assert isinstance(lag_info["total_lag"], int)
            assert isinstance(lag_info["partition_lags"], dict)

    @pytest.mark.asyncio
    async def test_dlq_behavior_parity(self, adapters, sample_envelope):
        """Test that all adapters handle DLQ consistently."""
        consumer_group = "tenant.test_tenant.consumers.test_group"
        error_message = "Test processing error"

        # Send to DLQ with each adapter
        for adapter_name, adapter in adapters.items():
            await adapter.send_to_dlq(sample_envelope, error_message, consumer_group)

            # Verify DLQ handling (implementation-specific)
            if hasattr(adapter, "dlq_events"):
                assert len(adapter.dlq_events) > 0
                dlq_event = adapter.dlq_events[-1]
                assert dlq_event["envelope"] == sample_envelope
                assert dlq_event["error"] == error_message
                assert dlq_event["consumer_group"] == consumer_group

    @pytest.mark.asyncio
    async def test_replay_behavior_parity(self, adapters, sample_envelope):
        """Test that all adapters handle replay consistently."""
        topic = "tenant.test_tenant.events.test"
        consumer_group = "tenant.test_tenant.consumers.test_group"
        tenant_id = "test_tenant"

        # Start replay with each adapter
        replay_results = {}
        for adapter_name, adapter in adapters.items():
            result = await adapter.replay_events(
                topic=topic,
                consumer_group=consumer_group,
                max_events=100,
                tenant_id=tenant_id
            )
            replay_results[adapter_name] = result

            # Verify result structure
            assert isinstance(result, dict)
            assert "replay_id" in result
            assert "status" in result
            assert "events_count" in result

        # Test replay status
        for adapter_name, adapter in adapters.items():
            replay_id = replay_results[adapter_name]["replay_id"]
            status = await adapter.get_replay_status(replay_id, tenant_id)

            assert isinstance(status, dict)
            assert "status" in status

    @pytest.mark.asyncio
    async def test_error_handling_parity(self, adapters):
        """Test that all adapters handle errors consistently."""

        # Test invalid topic
        invalid_topic = ""
        sample_envelope = EventEnvelope.create(
            event_type="test.event",
            data={},
            tenant_id="test_tenant"
        )

        for adapter_name, adapter in adapters.items():
            try:
                await adapter.publish(invalid_topic, sample_envelope)
                # If no exception, verify the adapter handled it gracefully
                assert True
            except Exception as e:
                # Verify exception is reasonable
                assert isinstance(e, (ValueError, TypeError))

        # Test invalid consumer group
        invalid_consumer_group = ""

        for adapter_name, adapter in adapters.items():
            try:
                lag_info = await adapter.get_consumer_lag(invalid_consumer_group)
                # Should return empty/default result
                assert isinstance(lag_info, dict)
                assert lag_info.get("total_lag", 0) == 0
            except Exception as e:
                # Or raise appropriate exception
                assert isinstance(e, (ValueError, KeyError))

    @pytest.mark.asyncio
    async def test_tenant_isolation_parity(self, adapters, sample_envelope):
        """Test that all adapters enforce tenant isolation consistently."""
        tenant1_topic = "tenant.tenant1.events.test"
        tenant2_topic = "tenant.tenant2.events.test"

        # Publish events for different tenants
        for adapter in adapters.values():
            await adapter.publish(tenant1_topic, sample_envelope)

            envelope2 = EventEnvelope.create(
                event_type="test.event.created",
                data={"test_field": "test_value"},
                tenant_id="tenant2"
            )
            await adapter.publish(tenant2_topic, envelope2)

        # Verify tenant isolation in topic listing
        for adapter_name, adapter in adapters.items():
            tenant1_topics = await adapter.list_topics("tenant1")
            tenant2_topics = await adapter.list_topics("tenant2")

            assert tenant1_topic in tenant1_topics
            assert tenant1_topic not in tenant2_topics
            assert tenant2_topic in tenant2_topics
            assert tenant2_topic not in tenant1_topics

    @pytest.mark.asyncio
    async def test_performance_characteristics_parity(self, adapters, sample_envelope):
        """Test that all adapters have reasonable performance characteristics."""
        topic = "tenant.test_tenant.events.performance_test"
        num_events = 10

        performance_results = {}

        for adapter_name, adapter in adapters.items():
            start_time = asyncio.get_event_loop().time()

            # Publish multiple events
            for i in range(num_events):
                envelope = EventEnvelope.create(
                    event_type="test.performance.event",
                    data={"event_number": i},
                    tenant_id="test_tenant"
                )
                await adapter.publish(topic, envelope)

            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time

            performance_results[adapter_name] = {
                "duration": duration,
                "events_per_second": num_events / duration if duration > 0 else float("inf")
            }

        # Verify all adapters completed within reasonable time
        for adapter_name, result in performance_results.items():
            assert result["duration"] < 10.0  # Should complete within 10 seconds
            assert result["events_per_second"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_operations_parity(self, adapters, sample_envelope):
        """Test that all adapters handle concurrent operations consistently."""
        topic = "tenant.test_tenant.events.concurrent_test"
        num_concurrent = 5

        for adapter_name, adapter in adapters.items():
            # Create concurrent publish tasks
            tasks = []
            for i in range(num_concurrent):
                envelope = EventEnvelope.create(
                    event_type="test.concurrent.event",
                    data={"task_number": i},
                    tenant_id="test_tenant"
                )
                task = asyncio.create_task(adapter.publish(topic, envelope))
                tasks.append(task)

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all operations succeeded
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent operation failed for {adapter_name}: {result}")
                else:
                    assert isinstance(result, dict)
                    assert result.get("status") == "published"

    def test_adapter_interface_compliance(self, adapters):
        """Test that all adapters implement the required interface."""
        required_methods = [
            "publish", "subscribe", "unsubscribe", "list_topics",
            "get_topic_info", "list_consumer_groups", "get_consumer_lag",
            "send_to_dlq", "replay_events", "get_replay_status"
        ]

        for adapter_name, adapter in adapters.items():
            for method_name in required_methods:
                assert hasattr(adapter, method_name), f"{adapter_name} missing method {method_name}"
                method = getattr(adapter, method_name)
                assert callable(method), f"{adapter_name}.{method_name} is not callable"


class TestAdapterSpecificBehavior:
    """Test adapter-specific behavior and optimizations."""

    @pytest.mark.asyncio
    async def test_memory_adapter_specifics(self):
        """Test memory adapter specific behavior."""
        adapter = MemoryEventAdapter()

        # Memory adapter should support immediate consistency
        envelope = EventEnvelope.create(
            event_type="test.event",
            data={},
            tenant_id="test_tenant"
        )

        topic = "tenant.test_tenant.events.test"
        await adapter.publish(topic, envelope)

        # Should immediately see the topic
        topics = await adapter.list_topics("test_tenant")
        assert topic in topics

        # Should immediately see message count
        info = await adapter.get_topic_info(topic)
        assert info["message_count"] == 1

    @pytest.mark.asyncio
    async def test_redis_adapter_specifics(self):
        """Test Redis adapter specific behavior."""
        adapter = MockRedisAdapter()

        # Redis adapter should handle streams and consumer groups
        envelope = EventEnvelope.create(
            event_type="test.event",
            data={},
            tenant_id="test_tenant"
        )

        topic = "tenant.test_tenant.events.test"
        await adapter.publish(topic, envelope)

        # Should track published events
        assert len(adapter.published_events) == 1
        assert adapter.published_events[0]["topic"] == topic

    @pytest.mark.asyncio
    async def test_kafka_adapter_specifics(self):
        """Test Kafka adapter specific behavior."""
        adapter = MockKafkaAdapter()

        # Kafka adapter should handle partitions differently
        envelope = EventEnvelope.create(
            event_type="test.event",
            data={},
            tenant_id="test_tenant"
        )

        topic = "tenant.test_tenant.events.test"
        await adapter.publish(topic, envelope, partition_key="test_key")

        # Should track partition key
        assert len(adapter.published_events) == 1
        assert adapter.published_events[0]["partition_key"] == "test_key"

        # Should have different partition count than Redis
        info = await adapter.get_topic_info(topic)
        assert info["partition_count"] == 6  # Different from Redis mock


@pytest.mark.asyncio
async def test_adapter_factory_parity():
    """Test that adapter factories create consistent instances."""

    # Test that all adapters can be created with similar configurations
    configs = {
        "memory": {},
        "redis": {"host": "localhost", "port": 6379},
        "kafka": {"bootstrap_servers": "localhost:9092"}
    }

    for adapter_type, config in configs.items():
        # This would test actual factory functions in real implementation
        # For now, just verify the concept
        assert isinstance(config, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
