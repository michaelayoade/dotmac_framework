"""
End-to-end test for service activation saga workflow.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import structlog

from dotmac_core_events.models.envelope import EventEnvelope
from dotmac_core_events.sdks.event_bus import EventBusSDK

logger = structlog.get_logger(__name__)


class ServiceActivationSaga:
    """Service activation saga orchestrator."""

    def __init__(self, event_bus: EventBusSDK):
        self.event_bus = event_bus
        self.saga_state = {}
        self.completed_sagas = set()
        self.failed_sagas = set()

    async def start_activation(self, customer_id: str, service_id: str, plan_id: str) -> str:
        """Start service activation saga."""
        saga_id = f"saga_{customer_id}_{service_id}_{int(datetime.now(timezone.utc).timestamp())}"

        # Initialize saga state
        self.saga_state[saga_id] = {
            "saga_id": saga_id,
            "customer_id": customer_id,
            "service_id": service_id,
            "plan_id": plan_id,
            "status": "started",
            "steps_completed": [],
            "started_at": datetime.now(timezone.utc),
            "current_step": "validate_customer"
        }

        # Publish saga started event
        await self.event_bus.publish(
            event_type="saga.service_activation.started",
            data={
                "saga_id": saga_id,
                "customer_id": customer_id,
                "service_id": service_id,
                "plan_id": plan_id
            },
            partition_key=customer_id
        )

        logger.info("Service activation saga started", saga_id=saga_id, customer_id=customer_id)
        return saga_id

    async def handle_customer_validated(self, envelope: EventEnvelope):
        """Handle customer validation completed."""
        saga_id = envelope.correlation_id
        if saga_id not in self.saga_state:
            return

        saga = self.saga_state[saga_id]
        saga["steps_completed"].append("validate_customer")
        saga["current_step"] = "provision_service"

        # Publish service provisioning command
        await self.event_bus.publish(
            event_type="command.service.provision",
            data={
                "saga_id": saga_id,
                "customer_id": saga["customer_id"],
                "service_id": saga["service_id"],
                "plan_id": saga["plan_id"]
            },
            partition_key=saga["customer_id"]
        )

        logger.info("Customer validated, provisioning service", saga_id=saga_id)

    async def handle_service_provisioned(self, envelope: EventEnvelope):
        """Handle service provisioning completed."""
        saga_id = envelope.correlation_id
        if saga_id not in self.saga_state:
            return

        saga = self.saga_state[saga_id]
        saga["steps_completed"].append("provision_service")
        saga["current_step"] = "configure_billing"

        # Publish billing configuration command
        await self.event_bus.publish(
            event_type="command.billing.configure",
            data={
                "saga_id": saga_id,
                "customer_id": saga["customer_id"],
                "service_id": saga["service_id"],
                "plan_id": saga["plan_id"]
            },
            partition_key=saga["customer_id"]
        )

        logger.info("Service provisioned, configuring billing", saga_id=saga_id)

    async def handle_billing_configured(self, envelope: EventEnvelope):
        """Handle billing configuration completed."""
        saga_id = envelope.correlation_id
        if saga_id not in self.saga_state:
            return

        saga = self.saga_state[saga_id]
        saga["steps_completed"].append("configure_billing")
        saga["current_step"] = "activate_service"

        # Publish service activation command
        await self.event_bus.publish(
            event_type="command.service.activate",
            data={
                "saga_id": saga_id,
                "customer_id": saga["customer_id"],
                "service_id": saga["service_id"]
            },
            partition_key=saga["customer_id"]
        )

        logger.info("Billing configured, activating service", saga_id=saga_id)

    async def handle_service_activated(self, envelope: EventEnvelope):
        """Handle service activation completed."""
        saga_id = envelope.correlation_id
        if saga_id not in self.saga_state:
            return

        saga = self.saga_state[saga_id]
        saga["steps_completed"].append("activate_service")
        saga["current_step"] = "completed"
        saga["status"] = "completed"
        saga["completed_at"] = datetime.now(timezone.utc)

        # Publish saga completed event
        await self.event_bus.publish(
            event_type="saga.service_activation.completed",
            data={
                "saga_id": saga_id,
                "customer_id": saga["customer_id"],
                "service_id": saga["service_id"],
                "duration_seconds": (saga["completed_at"] - saga["started_at"]).total_seconds()
            },
            partition_key=saga["customer_id"]
        )

        self.completed_sagas.add(saga_id)
        logger.info("Service activation saga completed", saga_id=saga_id)

    async def handle_step_failed(self, envelope: EventEnvelope):
        """Handle saga step failure."""
        saga_id = envelope.correlation_id
        if saga_id not in self.saga_state:
            return

        saga = self.saga_state[saga_id]
        failed_step = envelope.data.get("failed_step")
        error = envelope.data.get("error")

        saga["status"] = "failed"
        saga["failed_step"] = failed_step
        saga["error"] = error
        saga["failed_at"] = datetime.now(timezone.utc)

        # Start compensation
        await self._start_compensation(saga_id, failed_step)

        self.failed_sagas.add(saga_id)
        logger.error("Service activation saga failed", saga_id=saga_id, step=failed_step, error=error)

    async def _start_compensation(self, saga_id: str, failed_step: str):
        """Start compensation for failed saga."""
        saga = self.saga_state[saga_id]

        # Compensate completed steps in reverse order
        compensation_steps = []

        if "activate_service" in saga["steps_completed"]:
            compensation_steps.append("deactivate_service")
        if "configure_billing" in saga["steps_completed"]:
            compensation_steps.append("remove_billing")
        if "provision_service" in saga["steps_completed"]:
            compensation_steps.append("deprovision_service")

        # Execute compensation steps
        for step in compensation_steps:
            await self.event_bus.publish(
                event_type=f"command.compensation.{step}",
                data={
                    "saga_id": saga_id,
                    "customer_id": saga["customer_id"],
                    "service_id": saga["service_id"],
                    "original_failure": failed_step
                },
                partition_key=saga["customer_id"]
            )

        logger.info("Started compensation", saga_id=saga_id, steps=compensation_steps)


@pytest.fixture
async def event_bus():
    """Create mock event bus."""
    bus = AsyncMock(spec=EventBusSDK)
    bus.published_events = []

    async def mock_publish(event_type, data, **kwargs):
        envelope = EventEnvelope.create(
            event_type=event_type,
            data=data,
            tenant_id=data.get("tenant_id", "test_tenant"),
            correlation_id=data.get("saga_id")
        )
        bus.published_events.append(envelope)
        return {"status": "published", "message_id": f"msg_{len(bus.published_events)}"}

    bus.publish = mock_publish
    return bus


@pytest.fixture
async def saga_orchestrator(event_bus):
    """Create service activation saga orchestrator."""
    return ServiceActivationSaga(event_bus)


class TestServiceActivationSaga:
    """Test service activation saga end-to-end flow."""

    @pytest.mark.asyncio
    async def test_successful_service_activation(self, saga_orchestrator, event_bus):
        """Test successful service activation saga."""

        # Start saga
        customer_id = "customer_123"
        service_id = "service_456"
        plan_id = "plan_premium"

        saga_id = await saga_orchestrator.start_activation(customer_id, service_id, plan_id)

        # Verify saga started
        assert saga_id in saga_orchestrator.saga_state
        saga = saga_orchestrator.saga_state[saga_id]
        assert saga["status"] == "started"
        assert saga["current_step"] == "validate_customer"

        # Simulate customer validation
        validation_envelope = EventEnvelope.create(
            event_type="event.customer.validated",
            data={"customer_id": customer_id, "validation_result": "approved"},
            tenant_id=f"tenant_{customer_id}",
            correlation_id=saga_id
        )
        await saga_orchestrator.handle_customer_validated(validation_envelope)

        # Verify step progression
        assert "validate_customer" in saga["steps_completed"]
        assert saga["current_step"] == "provision_service"

        # Simulate service provisioning
        provisioning_envelope = EventEnvelope.create(
            event_type="event.service.provisioned",
            data={"service_id": service_id, "customer_id": customer_id},
            tenant_id=f"tenant_{customer_id}",
            correlation_id=saga_id
        )
        await saga_orchestrator.handle_service_provisioned(provisioning_envelope)

        # Verify step progression
        assert "provision_service" in saga["steps_completed"]
        assert saga["current_step"] == "configure_billing"

        # Simulate billing configuration
        billing_envelope = EventEnvelope.create(
            event_type="event.billing.configured",
            data={"customer_id": customer_id, "service_id": service_id, "plan_id": plan_id},
            tenant_id=f"tenant_{customer_id}",
            correlation_id=saga_id
        )
        await saga_orchestrator.handle_billing_configured(billing_envelope)

        # Verify step progression
        assert "configure_billing" in saga["steps_completed"]
        assert saga["current_step"] == "activate_service"

        # Simulate service activation
        activation_envelope = EventEnvelope.create(
            event_type="event.service.activated",
            data={"service_id": service_id, "customer_id": customer_id, "status": "active"},
            tenant_id=f"tenant_{customer_id}",
            correlation_id=saga_id
        )
        await saga_orchestrator.handle_service_activated(activation_envelope)

        # Verify saga completion
        assert saga["status"] == "completed"
        assert saga["current_step"] == "completed"
        assert "activate_service" in saga["steps_completed"]
        assert saga_id in saga_orchestrator.completed_sagas

        # Verify events were published
        assert len(event_bus.published_events) >= 5  # Start + 4 commands + completion

    @pytest.mark.asyncio
    async def test_saga_failure_and_compensation(self, saga_orchestrator, event_bus):
        """Test saga failure and compensation."""

        # Start saga
        customer_id = "customer_789"
        service_id = "service_101"
        plan_id = "plan_basic"

        saga_id = await saga_orchestrator.start_activation(customer_id, service_id, plan_id)

        # Complete first two steps
        validation_envelope = EventEnvelope.create(
            event_type="event.customer.validated",
            data={"customer_id": customer_id, "validation_result": "approved"},
            tenant_id=f"tenant_{customer_id}",
            correlation_id=saga_id
        )
        await saga_orchestrator.handle_customer_validated(validation_envelope)

        provisioning_envelope = EventEnvelope.create(
            event_type="event.service.provisioned",
            data={"service_id": service_id, "customer_id": customer_id},
            tenant_id=f"tenant_{customer_id}",
            correlation_id=saga_id
        )
        await saga_orchestrator.handle_service_provisioned(provisioning_envelope)

        # Simulate billing configuration failure
        failure_envelope = EventEnvelope.create(
            event_type="event.saga.step.failed",
            data={
                "failed_step": "configure_billing",
                "error": "Billing system unavailable",
                "original_command": "command.billing.configure"
            },
            tenant_id=f"tenant_{customer_id}",
            correlation_id=saga_id
        )
        await saga_orchestrator.handle_step_failed(failure_envelope)

        # Verify saga failure
        saga = saga_orchestrator.saga_state[saga_id]
        assert saga["status"] == "failed"
        assert saga["failed_step"] == "configure_billing"
        assert saga_id in saga_orchestrator.failed_sagas

        # Verify compensation was triggered
        compensation_events = [e for e in event_bus.published_events if "compensation" in e.type]
        assert len(compensation_events) > 0

    @pytest.mark.asyncio
    async def test_concurrent_sagas(self, saga_orchestrator, event_bus):
        """Test multiple concurrent sagas."""

        # Start multiple sagas
        saga_ids = []
        for i in range(3):
            saga_id = await saga_orchestrator.start_activation(
                customer_id=f"customer_{i}",
                service_id=f"service_{i}",
                plan_id="plan_standard"
            )
            saga_ids.append(saga_id)

        # Verify all sagas started
        assert len(saga_orchestrator.saga_state) == 3
        for saga_id in saga_ids:
            assert saga_id in saga_orchestrator.saga_state

        # Complete all sagas
        for i, saga_id in enumerate(saga_ids):
            customer_id = f"customer_{i}"
            service_id = f"service_{i}"

            # Complete all steps for this saga
            steps = [
                ("event.customer.validated", {"customer_id": customer_id}),
                ("event.service.provisioned", {"service_id": service_id, "customer_id": customer_id}),
                ("event.billing.configured", {"customer_id": customer_id, "service_id": service_id}),
                ("event.service.activated", {"service_id": service_id, "customer_id": customer_id})
            ]

            for event_type, data in steps:
                envelope = EventEnvelope.create(
                    event_type=event_type,
                    data=data,
                    tenant_id=f"tenant_{customer_id}",
                    correlation_id=saga_id
                )

                if event_type == "event.customer.validated":
                    await saga_orchestrator.handle_customer_validated(envelope)
                elif event_type == "event.service.provisioned":
                    await saga_orchestrator.handle_service_provisioned(envelope)
                elif event_type == "event.billing.configured":
                    await saga_orchestrator.handle_billing_configured(envelope)
                elif event_type == "event.service.activated":
                    await saga_orchestrator.handle_service_activated(envelope)

        # Verify all sagas completed
        assert len(saga_orchestrator.completed_sagas) == 3
        for saga_id in saga_ids:
            assert saga_id in saga_orchestrator.completed_sagas


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
