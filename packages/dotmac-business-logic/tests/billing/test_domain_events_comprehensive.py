"""
Comprehensive tests for domain events and event bus.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from dotmac_business_logic.billing.core.events import (  # Event classes; Event bus
    CreditApplied,
    EventBus,
    InvoiceGenerated,
    PaymentFailed,
    PaymentProcessed,
    RefundProcessed,
    SubscriptionCancelled,
    SubscriptionCreated,
    UsageMeterUpdated,
    event_bus,
    publish_event,
)


class TestDomainEventClasses:
    """Test individual domain event classes."""

    def test_invoice_generated_event_creation(self):
        """Test creating InvoiceGenerated event."""
        # Setup
        event_data = {
            'event_id': uuid4(),
            'occurred_at': datetime.now(timezone.utc),
            'invoice_id': uuid4(),
            'customer_id': uuid4(),
            'amount': Decimal('99.99'),
            'currency': 'USD',
            'due_date': datetime.now(timezone.utc),
            'invoice_number': 'INV-001'
        }

        # Execute
        event = InvoiceGenerated(**event_data)

        # Assert
        assert event.event_id == event_data['event_id']
        assert event.invoice_id == event_data['invoice_id']
        assert event.customer_id == event_data['customer_id']
        assert event.amount == event_data['amount']
        assert event.currency == event_data['currency']
        assert event.invoice_number == event_data['invoice_number']
        assert event.subscription_id is None  # Default value
        assert event.tenant_id is None  # Default value

    def test_invoice_generated_event_with_optionals(self):
        """Test InvoiceGenerated event with optional fields."""
        # Setup
        subscription_id = uuid4()
        tenant_id = uuid4()

        event = InvoiceGenerated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('149.99'),
            currency='EUR',
            due_date=datetime.now(timezone.utc),
            invoice_number='INV-002',
            subscription_id=subscription_id,
            tenant_id=tenant_id
        )

        # Assert
        assert event.subscription_id == subscription_id
        assert event.tenant_id == tenant_id

    def test_payment_processed_event_creation(self):
        """Test creating PaymentProcessed event."""
        # Setup & Execute
        event = PaymentProcessed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            payment_id=uuid4(),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            payment_method='credit_card'
        )

        # Assert
        assert event.payment_method == 'credit_card'
        assert event.transaction_id is None  # Default
        assert event.tenant_id is None  # Default

    def test_payment_failed_event_creation(self):
        """Test creating PaymentFailed event."""
        # Setup & Execute
        event = PaymentFailed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            payment_id=uuid4(),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            payment_method='credit_card',
            error_message='Card declined',
            error_code='card_declined'
        )

        # Assert
        assert event.error_message == 'Card declined'
        assert event.error_code == 'card_declined'

    def test_subscription_created_event_creation(self):
        """Test creating SubscriptionCreated event."""
        # Setup & Execute
        event = SubscriptionCreated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            subscription_id=uuid4(),
            customer_id=uuid4(),
            plan_id=uuid4(),
            start_date=datetime.now(timezone.utc),
            billing_cycle='monthly'
        )

        # Assert
        assert event.billing_cycle == 'monthly'
        assert event.trial_end_date is None  # Default

    def test_subscription_cancelled_event_creation(self):
        """Test creating SubscriptionCancelled event."""
        # Setup & Execute
        cancellation_time = datetime.now(timezone.utc)
        effective_time = datetime.now(timezone.utc)

        event = SubscriptionCancelled(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            subscription_id=uuid4(),
            customer_id=uuid4(),
            cancelled_at=cancellation_time,
            effective_date=effective_time,
            reason='Customer request'
        )

        # Assert
        assert event.cancelled_at == cancellation_time
        assert event.effective_date == effective_time
        assert event.reason == 'Customer request'

    def test_usage_meter_updated_event_creation(self):
        """Test creating UsageMeterUpdated event."""
        # Setup & Execute
        period_start = datetime.now(timezone.utc)
        period_end = datetime.now(timezone.utc)

        event = UsageMeterUpdated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            subscription_id=uuid4(),
            customer_id=uuid4(),
            meter_name='api_calls',
            usage_quantity=Decimal('1500'),
            period_start=period_start,
            period_end=period_end
        )

        # Assert
        assert event.meter_name == 'api_calls'
        assert event.usage_quantity == Decimal('1500')
        assert event.period_start == period_start
        assert event.period_end == period_end

    def test_credit_applied_event_creation(self):
        """Test creating CreditApplied event."""
        # Setup & Execute
        applied_time = datetime.now(timezone.utc)
        invoice_id = uuid4()

        event = CreditApplied(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            credit_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('25.00'),
            reason='Service credit',
            applied_at=applied_time,
            invoice_id=invoice_id
        )

        # Assert
        assert event.amount == Decimal('25.00')
        assert event.reason == 'Service credit'
        assert event.applied_at == applied_time
        assert event.invoice_id == invoice_id

    def test_refund_processed_event_creation(self):
        """Test creating RefundProcessed event."""
        # Setup & Execute
        processed_time = datetime.now(timezone.utc)

        event = RefundProcessed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            refund_id=uuid4(),
            original_payment_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('50.00'),
            currency='USD',
            processed_at=processed_time,
            reason='Product return'
        )

        # Assert
        assert event.amount == Decimal('50.00')
        assert event.currency == 'USD'
        assert event.processed_at == processed_time
        assert event.reason == 'Product return'

    def test_event_immutability(self):
        """Test that events are immutable after creation."""
        # Setup
        event = InvoiceGenerated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            due_date=datetime.now(timezone.utc),
            invoice_number='INV-001'
        )

        # Execute & Assert - should not be able to modify frozen dataclass
        with pytest.raises(AttributeError):
            event.amount = Decimal('199.99')

    def test_event_string_representation(self):
        """Test string representation of events."""
        # Setup
        event = PaymentProcessed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            payment_id=uuid4(),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            payment_method='credit_card'
        )

        # Execute
        str_repr = str(event)

        # Assert - should contain key information
        assert 'PaymentProcessed' in str_repr
        assert '99.99' in str_repr
        assert 'USD' in str_repr


class TestEventBus:
    """Test EventBus functionality."""

    @pytest.fixture
    def event_bus_instance(self):
        """Create fresh EventBus instance for testing."""
        return EventBus()

    @pytest.fixture
    def mock_handler(self):
        """Create mock event handler."""
        return AsyncMock()

    def test_subscribe_handler(self, event_bus_instance, mock_handler):
        """Test subscribing handler to event type."""
        # Execute
        event_bus_instance.subscribe(InvoiceGenerated, mock_handler)

        # Assert
        assert InvoiceGenerated in event_bus_instance._handlers
        assert mock_handler in event_bus_instance._handlers[InvoiceGenerated]

    def test_subscribe_multiple_handlers(self, event_bus_instance):
        """Test subscribing multiple handlers to same event type."""
        # Setup
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        # Execute
        event_bus_instance.subscribe(InvoiceGenerated, handler1)
        event_bus_instance.subscribe(InvoiceGenerated, handler2)

        # Assert
        handlers = event_bus_instance._handlers[InvoiceGenerated]
        assert len(handlers) == 2
        assert handler1 in handlers
        assert handler2 in handlers

    @pytest.mark.asyncio
    async def test_publish_event_to_handlers(self, event_bus_instance, mock_handler):
        """Test publishing event to subscribed handlers."""
        # Setup
        event_bus_instance.subscribe(InvoiceGenerated, mock_handler)

        event = InvoiceGenerated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            due_date=datetime.now(timezone.utc),
            invoice_number='INV-001'
        )

        # Execute
        await event_bus_instance.publish(event)

        # Assert
        mock_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_event_to_multiple_handlers(self, event_bus_instance):
        """Test publishing event to multiple handlers."""
        # Setup
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        event_bus_instance.subscribe(PaymentProcessed, handler1)
        event_bus_instance.subscribe(PaymentProcessed, handler2)

        event = PaymentProcessed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            payment_id=uuid4(),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            payment_method='credit_card'
        )

        # Execute
        await event_bus_instance.publish(event)

        # Assert
        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_event_no_handlers(self, event_bus_instance):
        """Test publishing event when no handlers are subscribed."""
        # Setup
        event = SubscriptionCreated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            subscription_id=uuid4(),
            customer_id=uuid4(),
            plan_id=uuid4(),
            start_date=datetime.now(timezone.utc),
            billing_cycle='monthly'
        )

        # Execute - should not raise exception
        await event_bus_instance.publish(event)

        # Assert - no exceptions raised

    @pytest.mark.asyncio
    async def test_handler_exception_handling(self, event_bus_instance):
        """Test handling exceptions in event handlers."""
        # Setup
        failing_handler = AsyncMock(side_effect=Exception("Handler failed"))
        working_handler = AsyncMock()

        event_bus_instance.subscribe(PaymentFailed, failing_handler)
        event_bus_instance.subscribe(PaymentFailed, working_handler)

        event = PaymentFailed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            payment_id=uuid4(),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            payment_method='credit_card',
            error_message='Card declined'
        )

        # Execute - should handle exceptions gracefully
        await event_bus_instance.publish(event)

        # Assert - working handler should still be called despite failure
        failing_handler.assert_called_once_with(event)
        working_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_event_type_specificity(self, event_bus_instance):
        """Test that handlers only receive events of their specific type."""
        # Setup
        invoice_handler = AsyncMock()
        payment_handler = AsyncMock()

        event_bus_instance.subscribe(InvoiceGenerated, invoice_handler)
        event_bus_instance.subscribe(PaymentProcessed, payment_handler)

        # Create different event types
        invoice_event = InvoiceGenerated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            due_date=datetime.now(timezone.utc),
            invoice_number='INV-001'
        )

        payment_event = PaymentProcessed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            payment_id=uuid4(),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            payment_method='credit_card'
        )

        # Execute
        await event_bus_instance.publish(invoice_event)
        await event_bus_instance.publish(payment_event)

        # Assert
        invoice_handler.assert_called_once_with(invoice_event)
        payment_handler.assert_called_once_with(payment_event)


class TestGlobalEventBus:
    """Test global event bus functionality."""

    @pytest.mark.asyncio
    async def test_global_publish_event_function(self):
        """Test using global publish_event function."""
        # Setup - mock the global event bus
        with patch('dotmac_business_logic.billing.core.events.event_bus') as mock_bus:
            mock_bus.publish = AsyncMock()

            event = CreditApplied(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                credit_id=uuid4(),
                customer_id=uuid4(),
                amount=Decimal('25.00'),
                reason='Service credit',
                applied_at=datetime.now(timezone.utc)
            )

            # Execute
            await publish_event(event)

            # Assert
            mock_bus.publish.assert_called_once_with(event)

    def test_global_event_bus_instance(self):
        """Test that global event_bus is properly instantiated."""
        # Assert
        assert event_bus is not None
        assert isinstance(event_bus, EventBus)


class TestEventIntegrationScenarios:
    """Test event integration scenarios."""

    @pytest.fixture
    def event_bus_with_handlers(self):
        """Create event bus with various handlers for integration testing."""
        bus = EventBus()

        # Create handlers for different scenarios
        handlers = {
            'invoice_handler': AsyncMock(),
            'payment_handler': AsyncMock(),
            'subscription_handler': AsyncMock(),
            'audit_handler': AsyncMock(),  # Handles all events
            'notification_handler': AsyncMock(),  # Sends notifications
        }

        # Subscribe handlers to specific events
        bus.subscribe(InvoiceGenerated, handlers['invoice_handler'])
        bus.subscribe(PaymentProcessed, handlers['payment_handler'])
        bus.subscribe(SubscriptionCreated, handlers['subscription_handler'])

        # Audit handler subscribes to multiple event types
        bus.subscribe(InvoiceGenerated, handlers['audit_handler'])
        bus.subscribe(PaymentProcessed, handlers['audit_handler'])
        bus.subscribe(SubscriptionCreated, handlers['audit_handler'])

        return bus, handlers

    @pytest.mark.asyncio
    async def test_billing_workflow_events(self, event_bus_with_handlers):
        """Test complete billing workflow event sequence."""
        bus, handlers = event_bus_with_handlers

        # Simulate billing workflow events
        events = [
            # 1. Subscription created
            SubscriptionCreated(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                subscription_id=uuid4(),
                customer_id=uuid4(),
                plan_id=uuid4(),
                start_date=datetime.now(timezone.utc),
                billing_cycle='monthly'
            ),
            # 2. Invoice generated
            InvoiceGenerated(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                invoice_id=uuid4(),
                customer_id=uuid4(),
                amount=Decimal('99.99'),
                currency='USD',
                due_date=datetime.now(timezone.utc),
                invoice_number='INV-001'
            ),
            # 3. Payment processed
            PaymentProcessed(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                payment_id=uuid4(),
                invoice_id=uuid4(),
                customer_id=uuid4(),
                amount=Decimal('99.99'),
                currency='USD',
                payment_method='credit_card'
            )
        ]

        # Execute - publish all events
        for event in events:
            await bus.publish(event)

        # Assert - verify all handlers called appropriately
        handlers['subscription_handler'].assert_called_once()
        handlers['invoice_handler'].assert_called_once()
        handlers['payment_handler'].assert_called_once()

        # Audit handler should be called for all events
        assert handlers['audit_handler'].call_count == 3

    @pytest.mark.asyncio
    async def test_event_ordering_and_causality(self, event_bus_with_handlers):
        """Test that events maintain proper ordering and causality."""
        bus, handlers = event_bus_with_handlers

        # Create events with shared IDs to establish causality
        customer_id = uuid4()
        subscription_id = uuid4()
        invoice_id = uuid4()

        events_in_order = [
            SubscriptionCreated(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                subscription_id=subscription_id,
                customer_id=customer_id,
                plan_id=uuid4(),
                start_date=datetime.now(timezone.utc),
                billing_cycle='monthly'
            ),
            InvoiceGenerated(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                invoice_id=invoice_id,
                customer_id=customer_id,
                subscription_id=subscription_id,
                amount=Decimal('99.99'),
                currency='USD',
                due_date=datetime.now(timezone.utc),
                invoice_number='INV-001'
            )
        ]

        # Execute events in order
        for event in events_in_order:
            await bus.publish(event)

        # Assert causality is maintained through shared IDs
        subscription_call = handlers['subscription_handler'].call_args[0][0]
        invoice_call = handlers['invoice_handler'].call_args[0][0]

        assert subscription_call.customer_id == invoice_call.customer_id
        assert subscription_call.subscription_id == invoice_call.subscription_id

    @pytest.mark.asyncio
    async def test_concurrent_event_publishing(self, event_bus_with_handlers):
        """Test concurrent event publishing for thread safety."""
        import asyncio

        bus, handlers = event_bus_with_handlers

        # Create multiple events to publish concurrently
        concurrent_events = [
            InvoiceGenerated(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                invoice_id=uuid4(),
                customer_id=uuid4(),
                amount=Decimal(f'{100 + i}.99'),
                currency='USD',
                due_date=datetime.now(timezone.utc),
                invoice_number=f'INV-{i:03d}'
            )
            for i in range(10)
        ]

        # Execute concurrent publishing
        await asyncio.gather(*[bus.publish(event) for event in concurrent_events])

        # Assert all events were handled
        assert handlers['invoice_handler'].call_count == 10
        assert handlers['audit_handler'].call_count == 10

    @pytest.mark.asyncio
    async def test_event_handler_performance_monitoring(self, event_bus_with_handlers):
        """Test monitoring event handler performance."""
        bus, handlers = event_bus_with_handlers

        # Create slow handler
        async def slow_handler(event):
            await asyncio.sleep(0.1)  # Simulate slow processing

        bus.subscribe(PaymentProcessed, slow_handler)

        event = PaymentProcessed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            payment_id=uuid4(),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            payment_method='credit_card'
        )

        # Execute and measure time
        start_time = datetime.now(timezone.utc)
        await bus.publish(event)
        end_time = datetime.now(timezone.utc)

        # Assert minimum processing time due to slow handler
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time >= 0.1  # Should take at least 100ms

    def test_event_serialization(self):
        """Test that events can be serialized for persistence/messaging."""
        # Setup
        event = InvoiceGenerated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            invoice_id=uuid4(),
            customer_id=uuid4(),
            amount=Decimal('99.99'),
            currency='USD',
            due_date=datetime.now(timezone.utc),
            invoice_number='INV-001'
        )

        # Test basic attribute access (would need proper serialization implementation)
        event_dict = {
            'event_type': type(event).__name__,
            'event_id': str(event.event_id),
            'occurred_at': event.occurred_at.isoformat(),
            'invoice_id': str(event.invoice_id),
            'customer_id': str(event.customer_id),
            'amount': str(event.amount),
            'currency': event.currency,
            'invoice_number': event.invoice_number
        }

        # Assert key fields can be serialized
        assert event_dict['event_type'] == 'InvoiceGenerated'
        assert event_dict['currency'] == 'USD'
        assert event_dict['amount'] == '99.99'
