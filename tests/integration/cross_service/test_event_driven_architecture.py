"""
Event-Driven Architecture Integration Tests
Tests message passing, event ordering, and system resilience
"""
import asyncio
import uuid
from datetime import datetime, timedelta

import pytest

from dotmac.communications.events.message import Event as EventType
from dotmac_shared.messaging.reliability_tester import ReliabilityTester
from dotmac_shared.testing.event_simulator import EventSimulator
from dotmac_shared.testing.integration_base import IntegrationTestBase
from dotmac_shared.testing.message_bus_tester import MessageBusTester


class TestEventDrivenArchitecture(IntegrationTestBase):
    """Test event-driven architecture patterns and reliability"""

    @pytest.fixture(autouse=True)
    async def setup_event_infrastructure(self):
        """Setup event testing infrastructure"""
        self.event_simulator = EventSimulator()
        self.message_bus_tester = MessageBusTester()
        self.reliability_tester = ReliabilityTester()

        # Initialize message bus connections
        await self.message_bus_tester.connect_to_all_queues([
            'customer_events',
            'billing_events',
            'service_events',
            'notification_events',
            'audit_events'
        ])

        yield

        await self.message_bus_tester.cleanup()

    @pytest.mark.integration
    @pytest.mark.event_driven
    async def test_event_ordering_and_causality(self):
        """Test that events are processed in correct order and maintain causality"""
        test_id = str(uuid.uuid4())

        # Define a sequence of causally related events
        event_sequence = [
            {
                "type": EventType.CUSTOMER_CREATED,
                "payload": {
                    "customer_id": f"cust_{test_id}",
                    "email": f"test_{test_id}@example.com",
                    "created_at": datetime.utcnow().isoformat()
                },
                "expected_downstream": ["billing_account_creation_requested", "welcome_email_queued"]
            },
            {
                "type": EventType.BILLING_ACCOUNT_CREATED,
                "payload": {
                    "customer_id": f"cust_{test_id}",
                    "billing_account_id": f"billing_{test_id}",
                    "created_at": datetime.utcnow().isoformat()
                },
                "expected_downstream": ["payment_method_setup_requested"]
            },
            {
                "type": EventType.SERVICE_PROVISIONING_STARTED,
                "payload": {
                    "customer_id": f"cust_{test_id}",
                    "service_id": f"service_{test_id}",
                    "started_at": datetime.utcnow().isoformat()
                },
                "expected_downstream": ["network_configuration_requested", "equipment_assignment_requested"]
            },
            {
                "type": EventType.SERVICE_PROVISIONING_COMPLETED,
                "payload": {
                    "customer_id": f"cust_{test_id}",
                    "service_id": f"service_{test_id}",
                    "completed_at": datetime.utcnow().isoformat()
                },
                "expected_downstream": ["service_activation_notification", "first_invoice_generation_requested"]
            }
        ]

        # Publish events with small delays to ensure ordering
        published_events = []
        for event_spec in event_sequence:
            event_id = await self.event_simulator.publish_event(
                event_spec["type"],
                event_spec["payload"],
                correlation_id=test_id
            )
            published_events.append({
                "id": event_id,
                "spec": event_spec,
                "published_at": datetime.utcnow()
            })
            await asyncio.sleep(0.1)  # Small delay to ensure ordering

        # Wait for all events to propagate
        await asyncio.sleep(2)

        # Collect all downstream events generated
        all_downstream_events = await self.message_bus_tester.collect_events_by_correlation(
            test_id, timeout=30
        )

        # Validate causality: downstream events should only appear after their triggers
        for published_event in published_events:
            for expected_downstream in published_event["spec"]["expected_downstream"]:
                downstream_events = [
                    e for e in all_downstream_events
                    if e["type"] == expected_downstream
                ]

                assert len(downstream_events) > 0, f"Missing downstream event: {expected_downstream}"

                # Check timing - downstream should be after upstream
                downstream_event = downstream_events[0]
                assert downstream_event["timestamp"] >= published_event["published_at"].isoformat()

    @pytest.mark.integration
    @pytest.mark.event_driven
    async def test_event_deduplication_and_idempotency(self):
        """Test that duplicate events are handled correctly and operations are idempotent"""
        test_id = str(uuid.uuid4())

        # Create a customer creation event
        customer_event = {
            "type": EventType.CUSTOMER_CREATED,
            "payload": {
                "customer_id": f"cust_{test_id}",
                "email": f"test_{test_id}@example.com",
                "idempotency_key": f"customer_create_{test_id}"
            }
        }

        # Publish the same event multiple times (simulating network retries)
        event_ids = []
        for _i in range(5):
            event_id = await self.event_simulator.publish_event(
                customer_event["type"],
                customer_event["payload"],
                correlation_id=test_id
            )
            event_ids.append(event_id)
            await asyncio.sleep(0.1)

        # Wait for processing
        await asyncio.sleep(3)

        # Verify only one customer was created despite multiple events
        customers = await self.message_bus_tester.query_downstream_state(
            "customer_service",
            {"email": customer_event["payload"]["email"]}
        )

        assert len(customers) == 1, "Duplicate events should result in only one customer"

        # Verify billing account was created only once
        billing_accounts = await self.message_bus_tester.query_downstream_state(
            "billing_service",
            {"customer_id": customer_event["payload"]["customer_id"]}
        )

        assert len(billing_accounts) == 1, "Duplicate events should result in only one billing account"

        # Check that duplicate event warnings were logged
        event_logs = await self.message_bus_tester.get_event_processing_logs(test_id)
        duplicate_warnings = [
            log for log in event_logs
            if "duplicate_event_detected" in log.get("message", "")
        ]

        assert len(duplicate_warnings) >= 4, "Should have warnings for duplicate events"

    @pytest.mark.integration
    @pytest.mark.event_driven
    async def test_dead_letter_queue_handling(self):
        """Test handling of failed events and dead letter queue processing"""
        test_id = str(uuid.uuid4())

        # Create an event that will intentionally fail processing
        poison_event = {
            "type": EventType.SERVICE_PROVISIONING_STARTED,
            "payload": {
                "customer_id": f"cust_{test_id}",
                "service_id": "invalid_service_id",  # This will cause processing to fail
                "invalid_field": "this_will_break_validation"
            }
        }

        # Publish the poison event
        event_id = await self.event_simulator.publish_event(
            poison_event["type"],
            poison_event["payload"],
            correlation_id=test_id
        )

        # Wait for retry attempts and eventual dead letter queue routing
        await asyncio.sleep(10)

        # Check that event was retried the expected number of times
        retry_logs = await self.message_bus_tester.get_retry_logs(event_id)
        assert len(retry_logs) >= 3, "Event should be retried at least 3 times"

        # Verify event ended up in dead letter queue
        dead_letter_events = await self.message_bus_tester.get_dead_letter_events(test_id)
        assert len(dead_letter_events) == 1, "Failed event should be in dead letter queue"

        dead_letter_event = dead_letter_events[0]
        assert dead_letter_event["original_event_id"] == event_id
        assert dead_letter_event["failure_reason"] is not None
        assert dead_letter_event["retry_count"] >= 3

    @pytest.mark.integration
    @pytest.mark.event_driven
    async def test_saga_pattern_implementation(self):
        """Test distributed transaction using saga pattern"""
        test_id = str(uuid.uuid4())

        # Start a complex multi-service transaction (customer onboarding saga)
        saga_id = await self.event_simulator.start_saga(
            "customer_onboarding_saga",
            {
                "customer_data": {
                    "email": f"saga_test_{test_id}@example.com",
                    "service_plan": "premium"
                },
                "correlation_id": test_id
            }
        )

        # Wait for saga to progress through steps
        await asyncio.sleep(5)

        # Inject a failure in the middle of the saga (billing setup fails)
        await self.event_simulator.inject_saga_failure(
            saga_id,
            step="billing_setup",
            failure_type="payment_method_declined"
        )

        # Wait for compensation actions
        await asyncio.sleep(3)

        # Verify saga compensation occurred
        saga_state = await self.message_bus_tester.get_saga_state(saga_id)
        assert saga_state["status"] == "compensated"

        # Check that compensating actions were executed in reverse order
        compensation_events = await self.message_bus_tester.get_saga_compensation_events(saga_id)
        expected_compensations = [
            "service_provisioning_rollback",
            "customer_account_rollback"
        ]

        for compensation in expected_compensations:
            assert any(e["type"] == compensation for e in compensation_events)

        # Verify system is in consistent state (no partial data left)
        customers = await self.message_bus_tester.query_downstream_state(
            "customer_service",
            {"email": f"saga_test_{test_id}@example.com"}
        )
        assert len(customers) == 0, "Customer should be rolled back"

    @pytest.mark.integration
    @pytest.mark.event_driven
    async def test_event_store_and_replay(self):
        """Test event store functionality and event replay capabilities"""
        test_id = str(uuid.uuid4())

        # Generate a series of business events
        business_events = [
            {
                "type": EventType.CUSTOMER_CREATED,
                "payload": {"customer_id": f"cust_{test_id}", "tier": "basic"}
            },
            {
                "type": EventType.SERVICE_PLAN_UPGRADED,
                "payload": {"customer_id": f"cust_{test_id}", "new_tier": "premium"}
            },
            {
                "type": EventType.PAYMENT_PROCESSED,
                "payload": {"customer_id": f"cust_{test_id}", "amount": 99.99}
            },
            {
                "type": EventType.SERVICE_SUSPENDED,
                "payload": {"customer_id": f"cust_{test_id}", "reason": "non_payment"}
            }
        ]

        # Publish events and store in event store
        event_ids = []
        for event in business_events:
            event_id = await self.event_simulator.publish_and_store_event(
                event["type"],
                event["payload"],
                correlation_id=test_id,
                store_in_event_store=True
            )
            event_ids.append(event_id)
            await asyncio.sleep(0.2)

        # Wait for processing
        await asyncio.sleep(2)

        # Capture current system state
        initial_state = await self.message_bus_tester.capture_system_state(f"cust_{test_id}")

        # Simulate system failure and recovery by replaying events
        await self.event_simulator.simulate_system_restart()

        # Replay events from event store
        replayed_events = await self.event_simulator.replay_events_from_store(
            correlation_id=test_id,
            from_timestamp=datetime.utcnow() - timedelta(minutes=5)
        )

        assert len(replayed_events) == len(business_events)

        # Wait for replay to complete
        await asyncio.sleep(3)

        # Verify system state is restored correctly
        restored_state = await self.message_bus_tester.capture_system_state(f"cust_{test_id}")

        # Compare key aspects of state (customer tier, payment status, service status)
        assert restored_state["customer"]["tier"] == initial_state["customer"]["tier"]
        assert restored_state["service"]["status"] == initial_state["service"]["status"]
        assert restored_state["billing"]["last_payment"] == initial_state["billing"]["last_payment"]

    @pytest.mark.integration
    @pytest.mark.event_driven
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern in event processing"""
        test_id = str(uuid.uuid4())

        # Configure circuit breaker for billing service
        await self.reliability_tester.configure_circuit_breaker(
            service="billing_service",
            failure_threshold=3,
            recovery_timeout=5,
            test_id=test_id
        )

        # Simulate billing service failures
        for i in range(5):
            await self.event_simulator.publish_event(
                EventType.PAYMENT_PROCESSING_REQUESTED,
                {
                    "customer_id": f"cust_{test_id}_{i}",
                    "amount": 50.00,
                    "force_failure": True  # This will cause billing service to fail
                },
                correlation_id=test_id
            )
            await asyncio.sleep(0.5)

        # Verify circuit breaker opened after threshold failures
        circuit_state = await self.reliability_tester.get_circuit_breaker_state(
            "billing_service", test_id
        )
        assert circuit_state["status"] == "OPEN"
        assert circuit_state["failure_count"] >= 3

        # Try to send more events - they should be rejected immediately
        rejected_event_id = await self.event_simulator.publish_event(
            EventType.PAYMENT_PROCESSING_REQUESTED,
            {"customer_id": f"cust_{test_id}_rejected", "amount": 25.00},
            correlation_id=test_id
        )

        # Check that event was rejected due to open circuit
        event_status = await self.message_bus_tester.get_event_status(rejected_event_id)
        assert event_status["status"] == "rejected"
        assert "circuit_breaker_open" in event_status["rejection_reason"]

        # Wait for recovery timeout
        await asyncio.sleep(6)

        # Send a success event to close the circuit
        await self.reliability_tester.simulate_service_recovery("billing_service")

        success_event_id = await self.event_simulator.publish_event(
            EventType.PAYMENT_PROCESSING_REQUESTED,
            {"customer_id": f"cust_{test_id}_recovery", "amount": 30.00},
            correlation_id=test_id
        )

        await asyncio.sleep(2)

        # Verify circuit breaker is now closed
        final_circuit_state = await self.reliability_tester.get_circuit_breaker_state(
            "billing_service", test_id
        )
        assert final_circuit_state["status"] == "CLOSED"

        # Verify the recovery event was processed successfully
        recovery_event_status = await self.message_bus_tester.get_event_status(success_event_id)
        assert recovery_event_status["status"] == "completed"
