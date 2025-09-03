"""
Cross-Service Integration Tests - Complete User Journeys
Tests end-to-end workflows across ISP → Management → Customer services
"""
import asyncio
import pytest
import httpx
from typing import Dict, Any, List
from unittest.mock import AsyncMock
import uuid
from datetime import datetime, timedelta

from dotmac_shared.testing.integration_base import IntegrationTestBase
from dotmac_shared.testing.service_clients import ServiceClientManager
from dotmac_shared.testing.event_tracer import EventTracer
from dotmac_shared.models.customer import Customer, CustomerTier
from dotmac_shared.models.service_plan import ServicePlan, BandwidthTier


class TestCompleteUserJourneys(IntegrationTestBase):
    """Test complete user journeys across all services"""
    
    @pytest.fixture(autouse=True)
    async def setup_services(self):
        """Setup all required services for integration testing"""
        self.service_manager = ServiceClientManager()
        self.event_tracer = EventTracer()
        
        # Initialize service clients
        await self.service_manager.initialize_clients([
            'isp_service',
            'management_service', 
            'customer_service',
            'billing_service',
            'notification_service'
        ])
        
        # Start event tracing
        await self.event_tracer.start_tracing()
        
        yield
        
        # Cleanup
        await self.event_tracer.stop_tracing()
        await self.service_manager.cleanup()

    @pytest.mark.integration
    @pytest.mark.journey
    async def test_complete_customer_onboarding_journey(self):
        """
        Test complete customer onboarding journey:
        ISP Admin creates service plan → Customer signs up → Service provisioning → Billing setup
        """
        journey_id = str(uuid.uuid4())
        
        # Phase 1: ISP Admin creates service plan
        service_plan_data = {
            "name": f"Premium Fiber {journey_id[:8]}",
            "bandwidth_down": 1000,  # 1Gbps
            "bandwidth_up": 500,     # 500Mbps
            "monthly_price": 89.99,
            "setup_fee": 99.00,
            "tier": BandwidthTier.PREMIUM.value,
            "features": ["static_ip", "priority_support", "unlimited_data"]
        }
        
        service_plan = await self.service_manager.isp_service.create_service_plan(
            service_plan_data, journey_id=journey_id
        )
        assert service_plan["id"] is not None
        
        # Verify event propagation
        events = await self.event_tracer.get_events_by_journey(journey_id)
        assert any(e["type"] == "service_plan.created" for e in events)
        
        # Phase 2: Customer registration and service selection
        customer_data = {
            "email": f"test.customer.{journey_id[:8]}@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1-555-0123",
            "service_address": {
                "street": "123 Test Street",
                "city": "Test City",
                "state": "CA",
                "zip_code": "90210"
            }
        }
        
        customer = await self.service_manager.customer_service.register_customer(
            customer_data, journey_id=journey_id
        )
        assert customer["id"] is not None
        assert customer["status"] == "pending_verification"
        
        # Phase 3: Service plan subscription
        subscription_data = {
            "customer_id": customer["id"],
            "service_plan_id": service_plan["id"],
            "installation_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "billing_cycle": "monthly"
        }
        
        subscription = await self.service_manager.isp_service.create_subscription(
            subscription_data, journey_id=journey_id
        )
        assert subscription["id"] is not None
        assert subscription["status"] == "pending_installation"
        
        # Phase 4: Service provisioning workflow
        provisioning_result = await self.service_manager.isp_service.provision_service(
            subscription["id"], journey_id=journey_id
        )
        assert provisioning_result["status"] == "provisioned"
        assert provisioning_result["service_details"]["bandwidth_allocated"] >= service_plan_data["bandwidth_down"]
        
        # Phase 5: Billing setup and first invoice generation
        billing_account = await self.service_manager.billing_service.create_billing_account(
            {
                "customer_id": customer["id"],
                "subscription_id": subscription["id"],
                "payment_method": "credit_card",
                "billing_address": customer_data["service_address"]
            },
            journey_id=journey_id
        )
        assert billing_account["id"] is not None
        
        # Generate initial invoice
        initial_invoice = await self.service_manager.billing_service.generate_invoice(
            billing_account["id"], journey_id=journey_id
        )
        assert initial_invoice["total_amount"] == service_plan_data["setup_fee"] + service_plan_data["monthly_price"]
        
        # Phase 6: Notification dispatch verification
        notifications = await self.service_manager.notification_service.get_notifications_by_journey(
            journey_id
        )
        
        expected_notifications = [
            "welcome_email",
            "service_provisioned", 
            "invoice_generated"
        ]
        
        for expected in expected_notifications:
            assert any(n["type"] == expected for n in notifications), f"Missing notification: {expected}"
        
        # Phase 7: End-to-end event chain validation
        all_events = await self.event_tracer.get_events_by_journey(journey_id)
        
        expected_event_chain = [
            "service_plan.created",
            "customer.registered",
            "subscription.created", 
            "service.provisioned",
            "billing_account.created",
            "invoice.generated",
            "notification.dispatched"
        ]
        
        for expected_event in expected_event_chain:
            matching_events = [e for e in all_events if e["type"] == expected_event]
            assert len(matching_events) > 0, f"Missing event in chain: {expected_event}"
        
        # Validate event ordering and timing
        await self._validate_event_sequence(all_events, expected_event_chain)

    @pytest.mark.integration
    @pytest.mark.journey
    async def test_service_upgrade_journey(self):
        """
        Test service upgrade journey:
        Customer requests upgrade → Management approval → Service reconfiguration → Billing adjustment
        """
        journey_id = str(uuid.uuid4())
        
        # Setup: Create existing customer with basic service
        customer = await self._create_test_customer(journey_id, tier="basic")
        current_subscription = customer["active_subscription"]
        
        # Phase 1: Customer initiates service upgrade
        upgrade_request = await self.service_manager.customer_service.request_service_upgrade(
            {
                "customer_id": customer["id"],
                "current_plan_id": current_subscription["service_plan_id"],
                "requested_plan_id": await self._get_premium_plan_id(),
                "reason": "Need higher bandwidth for remote work"
            },
            journey_id=journey_id
        )
        assert upgrade_request["status"] == "pending_approval"
        
        # Phase 2: Management reviews and approves upgrade
        approval = await self.service_manager.management_service.approve_upgrade_request(
            upgrade_request["id"],
            {
                "approved_by": "admin@example.com",
                "approval_notes": "Customer has good payment history",
                "effective_date": (datetime.now() + timedelta(days=3)).isoformat()
            },
            journey_id=journey_id
        )
        assert approval["status"] == "approved"
        
        # Phase 3: Service reconfiguration
        reconfiguration = await self.service_manager.isp_service.reconfigure_service(
            current_subscription["id"],
            {
                "new_plan_id": await self._get_premium_plan_id(),
                "preserve_settings": True,
                "migration_type": "seamless"
            },
            journey_id=journey_id
        )
        assert reconfiguration["status"] == "completed"
        assert reconfiguration["downtime_seconds"] < 30  # Seamless upgrade
        
        # Phase 4: Billing adjustment and prorated invoice
        billing_adjustment = await self.service_manager.billing_service.process_plan_change(
            customer["billing_account_id"],
            {
                "old_plan_id": current_subscription["service_plan_id"],
                "new_plan_id": await self._get_premium_plan_id(),
                "change_date": approval["effective_date"],
                "proration_method": "daily"
            },
            journey_id=journey_id
        )
        assert billing_adjustment["prorated_amount"] > 0
        
        # Phase 5: Customer notification of successful upgrade
        notifications = await self.service_manager.notification_service.get_notifications_by_journey(
            journey_id
        )
        
        upgrade_complete_notification = next(
            (n for n in notifications if n["type"] == "service_upgraded"), None
        )
        assert upgrade_complete_notification is not None
        assert upgrade_complete_notification["status"] == "delivered"
        
        # Validate complete event chain
        events = await self.event_tracer.get_events_by_journey(journey_id)
        expected_events = [
            "upgrade.requested",
            "upgrade.approved", 
            "service.reconfigured",
            "billing.adjusted",
            "notification.sent"
        ]
        
        await self._validate_event_sequence(events, expected_events)

    @pytest.mark.integration 
    @pytest.mark.journey
    async def test_service_suspension_and_restoration_journey(self):
        """
        Test service suspension and restoration:
        Payment failure → Auto-suspension → Customer payment → Service restoration
        """
        journey_id = str(uuid.uuid4())
        
        # Setup: Customer with active service
        customer = await self._create_test_customer(journey_id, tier="standard")
        
        # Phase 1: Simulate payment failure
        payment_failure = await self.service_manager.billing_service.simulate_payment_failure(
            customer["billing_account_id"],
            {
                "reason": "insufficient_funds",
                "invoice_id": customer["current_invoice_id"],
                "retry_attempts": 3
            },
            journey_id=journey_id
        )
        assert payment_failure["status"] == "failed"
        
        # Phase 2: Automatic service suspension after grace period
        await asyncio.sleep(2)  # Simulate grace period
        
        suspension = await self.service_manager.isp_service.suspend_service(
            customer["active_subscription"]["id"],
            {
                "reason": "payment_failure",
                "suspension_type": "soft",  # Reduced bandwidth, not complete cutoff
                "grace_period_expired": True
            },
            journey_id=journey_id
        )
        assert suspension["status"] == "suspended"
        assert suspension["bandwidth_limit"] <= 1  # 1 Mbps grace bandwidth
        
        # Phase 3: Customer notification of suspension
        suspension_notifications = await self.service_manager.notification_service.get_notifications_by_customer(
            customer["id"], notification_type="service_suspended"
        )
        assert len(suspension_notifications) > 0
        
        # Phase 4: Customer makes payment
        payment_success = await self.service_manager.billing_service.process_payment(
            customer["billing_account_id"],
            {
                "amount": customer["outstanding_amount"],
                "payment_method": "credit_card",
                "payment_source": "customer_portal"
            },
            journey_id=journey_id
        )
        assert payment_success["status"] == "completed"
        
        # Phase 5: Automatic service restoration
        restoration = await self.service_manager.isp_service.restore_service(
            customer["active_subscription"]["id"],
            {
                "trigger": "payment_received",
                "restore_full_service": True
            },
            journey_id=journey_id
        )
        assert restoration["status"] == "active"
        assert restoration["bandwidth_restored"] == customer["active_subscription"]["allocated_bandwidth"]
        
        # Phase 6: Confirmation notifications
        restoration_notifications = await self.service_manager.notification_service.get_notifications_by_customer(
            customer["id"], notification_type="service_restored"
        )
        assert len(restoration_notifications) > 0
        
        # Validate event sequence and timing
        events = await self.event_tracer.get_events_by_journey(journey_id)
        expected_sequence = [
            "payment.failed",
            "service.suspended",
            "notification.suspension_sent",
            "payment.completed", 
            "service.restored",
            "notification.restoration_sent"
        ]
        
        await self._validate_event_sequence(events, expected_sequence)

    async def _validate_event_sequence(self, events: List[Dict], expected_sequence: List[str]):
        """Validate that events occurred in the expected sequence with proper timing"""
        events_by_type = {event["type"]: event for event in events}
        
        prev_timestamp = None
        for event_type in expected_sequence:
            assert event_type in events_by_type, f"Missing event: {event_type}"
            
            current_timestamp = events_by_type[event_type]["timestamp"]
            if prev_timestamp:
                assert current_timestamp >= prev_timestamp, f"Event {event_type} occurred out of sequence"
            prev_timestamp = current_timestamp

    async def _create_test_customer(self, journey_id: str, tier: str = "basic") -> Dict[str, Any]:
        """Helper to create a test customer with active subscription"""
        # Implementation would create customer, subscription, and billing account
        # This is a placeholder for the actual implementation
        pass
    
    async def _get_premium_plan_id(self) -> str:
        """Helper to get premium service plan ID"""
        # Implementation would fetch premium plan from database
        pass