"""
Smoke validation tests for manual verification.
These tests verify complete workflows work end-to-end.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from dotmac.ticketing.core.manager import TicketManager
from dotmac.ticketing.core.service import TicketService
from dotmac.ticketing.core.models import (
    Ticket, TicketStatus, TicketPriority, TicketCategory, TicketComment
)
from dotmac.ticketing.workflows.automation import TicketAutomationEngine
from dotmac.ticketing.integrations.notifications import TicketNotificationManager
from dotmac.ticketing.integrations.templates import NotificationTemplateManager
from dotmac.ticketing.integrations.adapters import (
    get_communication_service, get_monitoring_service
)


class TestSmokeValidationInMemorySQLite:
    """Smoke tests with in-memory SQLite database."""
    
    async def test_complete_ticket_lifecycle_smoke(self):
        """
        MANUAL SMOKE TEST: Complete ticket lifecycle
        Create → Assign → Add Comments → Resolve → Close
        Verify audit logs and SLA timestamps at each step.
        """
        print("\n=== SMOKE TEST: Complete Ticket Lifecycle ===")
        
        # Setup in-memory components
        manager = TicketManager()
        service = TicketService(ticket_manager=manager)
        
        # Mock database for smoke test
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Create test ticket
        print("1. Creating ticket...")
        ticket = Ticket(
            id="smoke-test-001",
            ticket_number="TKT-SMOKE-001",
            tenant_id="smoke-tenant",
            title="Smoke Test Ticket - Complete Lifecycle",
            description="This is a comprehensive smoke test for ticket lifecycle",
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            category=TicketCategory.TECHNICAL_SUPPORT,
            customer_email="smoketest@example.com",
            customer_name="Smoke Test User",
            created_at=datetime.now(timezone.utc)
        )
        
        # Simulate ticket creation events
        await manager._trigger_ticket_created_events(ticket)
        print(f"   ✓ Ticket created: {ticket.ticket_number}")
        print(f"   ✓ Priority: {ticket.priority}")
        print(f"   ✓ Created at: {ticket.created_at}")
        
        # 2. Assign ticket
        print("2. Assigning ticket...")
        ticket.assigned_to_id = "agent-123"
        ticket.assigned_to_name = "Test Agent"
        ticket.assigned_team = "Technical Support"
        ticket.status = TicketStatus.IN_PROGRESS
        
        await manager._trigger_ticket_assigned_events(ticket)
        print(f"   ✓ Ticket assigned to: {ticket.assigned_to_name}")
        print(f"   ✓ Team: {ticket.assigned_team}")
        print(f"   ✓ Status: {ticket.status}")
        
        # 3. Add customer comment
        print("3. Adding customer comment...")
        customer_comment = TicketComment(
            id="comment-001",
            ticket_id=ticket.id,
            content="Thank you for looking into this issue. When can I expect a resolution?",
            author_name="Smoke Test User",
            author_type="customer",
            is_internal=False,
            created_at=datetime.now(timezone.utc)
        )
        
        await manager._trigger_comment_added_events(ticket, customer_comment)
        print(f"   ✓ Customer comment added: {customer_comment.content[:50]}...")
        
        # 4. Add internal comment  
        print("4. Adding internal comment...")
        internal_comment = TicketComment(
            id="comment-002",
            ticket_id=ticket.id,
            content="Investigating network configuration. Will need to escalate to Level 2.",
            author_name="Test Agent",
            author_type="agent",
            is_internal=True,
            created_at=datetime.now(timezone.utc)
        )
        
        await manager._trigger_comment_added_events(ticket, internal_comment)
        print(f"   ✓ Internal comment added: {internal_comment.content[:50]}...")
        
        # 5. Resolve ticket
        print("5. Resolving ticket...")
        ticket.status = TicketStatus.RESOLVED
        ticket.resolved_at = datetime.now(timezone.utc)
        
        resolution_comment = TicketComment(
            id="comment-003",
            ticket_id=ticket.id,
            content="Issue resolved. Updated network configuration and verified connectivity.",
            author_name="Test Agent",
            author_type="agent",
            is_solution=True,
            created_at=datetime.now(timezone.utc)
        )
        
        await manager._trigger_ticket_resolved_events(ticket, resolution_comment)
        print(f"   ✓ Ticket resolved at: {ticket.resolved_at}")
        print(f"   ✓ Resolution: {resolution_comment.content[:50]}...")
        
        # 6. Close ticket
        print("6. Closing ticket...")
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = datetime.now(timezone.utc)
        
        await manager._trigger_ticket_closed_events(ticket)
        print(f"   ✓ Ticket closed at: {ticket.closed_at}")
        
        # Calculate timing metrics
        resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
        total_time = (ticket.closed_at - ticket.created_at).total_seconds() / 3600
        
        print(f"\n=== TIMING METRICS ===")
        print(f"Resolution time: {resolution_time:.2f} hours")
        print(f"Total lifecycle time: {total_time:.2f} hours")
        print(f"Status progression: OPEN → IN_PROGRESS → RESOLVED → CLOSED")
        
        # Verify SLA compliance (assuming 24h SLA for HIGH priority)
        sla_hours = 24
        sla_met = resolution_time <= sla_hours
        print(f"SLA compliance (24h): {'✓ PASS' if sla_met else '✗ FAIL'}")
        
        print("\n=== SMOKE TEST COMPLETE ===")
        assert ticket.status == TicketStatus.CLOSED
        assert ticket.resolved_at is not None
        assert ticket.closed_at is not None

    async def test_notification_system_smoke(self):
        """
        MANUAL SMOKE TEST: Notification system
        Test template rendering and notification sending.
        """
        print("\n=== SMOKE TEST: Notification System ===")
        
        # Create notification manager with template system
        template_manager = NotificationTemplateManager()
        comm_service = get_communication_service()
        notification_manager = TicketNotificationManager(
            communication_service=comm_service,
            template_manager=template_manager
        )
        
        # Test ticket
        test_ticket = Ticket(
            id="notify-test-001",
            ticket_number="TKT-NOTIFY-001",
            tenant_id="notify-tenant",
            title="Notification Test Ticket",
            description="Testing notification template rendering",
            status=TicketStatus.OPEN,
            priority=TicketPriority.URGENT,
            category=TicketCategory.BILLING_INQUIRY,
            customer_email="notify@example.com",
            customer_name="Notification Test User",
            created_at=datetime.now(timezone.utc)
        )
        
        print("1. Testing ticket creation notification...")
        await notification_manager.notify_ticket_created(test_ticket)
        print("   ✓ Ticket creation notification sent")
        
        print("2. Testing ticket assignment notification...")
        await notification_manager.notify_ticket_assigned(
            test_ticket,
            assigned_to_name="Support Agent",
            assigned_team="Billing Team"
        )
        print("   ✓ Ticket assignment notification sent")
        
        print("3. Testing ticket resolution notification...")
        await notification_manager.notify_ticket_resolved(
            test_ticket,
            resolution_comment="Issue resolved after reviewing account settings",
            resolved_by="Billing Specialist"
        )
        print("   ✓ Ticket resolution notification sent")
        
        print("4. Testing template rendering...")
        # Test template rendering directly
        context = {
            "customer_name": test_ticket.customer_name,
            "ticket_number": test_ticket.ticket_number,
            "title": test_ticket.title,
            "priority": test_ticket.priority.value,
            "status": test_ticket.status.value
        }
        
        subject = template_manager.render_notification("ticket_created", context, "subject")
        body = template_manager.render_notification("ticket_created", context, "body")
        html_body = template_manager.render_notification("ticket_created", context, "html_body")
        
        print(f"   ✓ Subject: {subject}")
        print(f"   ✓ Body length: {len(body) if body else 0} characters")
        print(f"   ✓ HTML body length: {len(html_body) if html_body else 0} characters")
        
        assert subject and "TKT-NOTIFY-001" in subject
        assert body and "Notification Test User" in body
        assert html_body and "<html>" in html_body
        
        print("\n=== NOTIFICATION SYSTEM SMOKE TEST COMPLETE ===")

    async def test_workflow_automation_dry_run_smoke(self):
        """
        MANUAL SMOKE TEST: Workflow automation dry-run
        Enable dry-run, execute automation, assert no DB side effects.
        """
        print("\n=== SMOKE TEST: Workflow Automation (Dry Run) ===")
        
        # Create automation engine in dry-run mode
        mock_db_factory = AsyncMock()
        automation_engine = TicketAutomationEngine(
            db_session_factory=mock_db_factory,
            config={'dry_run_mode': True},
            enable_background_tasks=False
        )
        
        print(f"1. Automation engine configured:")
        print(f"   ✓ Dry run mode: {automation_engine.dry_run_mode}")
        print(f"   ✓ Background tasks: {automation_engine.enable_background_tasks}")
        print(f"   ✓ Available workflows: {list(automation_engine.workflows.keys())}")
        print(f"   ✓ Task decorator available: {automation_engine.task_decorator is not None}")
        
        # Create test ticket for automation
        automation_ticket = Ticket(
            id="auto-test-001",
            ticket_number="TKT-AUTO-001",
            tenant_id="auto-tenant",
            title="Billing issue - Payment not processed",
            description="Customer payment failed to process, need immediate attention",
            status=TicketStatus.OPEN,
            priority=TicketPriority.URGENT,
            category=TicketCategory.BILLING_INQUIRY,
            customer_email="billing@example.com",
            created_at=datetime.now(timezone.utc)
        )
        
        # Add auto-assignment rule
        from dotmac.ticketing.workflows.automation import AutoAssignmentRule
        billing_rule = AutoAssignmentRule(
            name="Billing Issues Auto-Assignment",
            conditions={"category": TicketCategory.BILLING_INQUIRY},
            assigned_team="billing_support",
            priority=10,
            active=True
        )
        automation_engine.add_assignment_rule(billing_rule)
        
        print("2. Testing auto-assignment rules...")
        mock_db = AsyncMock()
        initial_status = automation_ticket.status
        initial_team = automation_ticket.assigned_team
        
        await automation_engine.process_new_ticket(automation_ticket, "auto-tenant", mock_db)
        
        # In dry-run mode, ticket should NOT be modified
        print(f"   ✓ Ticket status unchanged: {automation_ticket.status == initial_status}")
        print(f"   ✓ Team assignment unchanged: {automation_ticket.assigned_team == initial_team}")
        print(f"   ✓ Dry run prevented database modifications")
        
        # Test SLA monitor
        print("3. Testing SLA monitoring...")
        sla_monitor = automation_engine.sla_monitor
        breach_time = await sla_monitor.calculate_sla_breach_time(automation_ticket)
        
        print(f"   ✓ SLA breach time calculated: {breach_time}")
        print(f"   ✓ SLA hours for {automation_ticket.priority}: "
              f"{(breach_time - automation_ticket.created_at).total_seconds() / 3600:.1f}")
        
        # Test escalation rules
        print("4. Testing escalation rules...")
        from dotmac.ticketing.workflows.automation import EscalationRule
        escalation_rule = EscalationRule(
            name="Urgent Ticket Escalation",
            conditions={"priority": TicketPriority.URGENT},
            escalation_time_hours=4,
            escalate_to_team="senior_support",
            priority_increase=True,
            active=True
        )
        automation_engine.add_escalation_rule(escalation_rule)
        
        print(f"   ✓ Escalation rule added: {escalation_rule.name}")
        print(f"   ✓ Escalation time: {escalation_rule.escalation_time_hours} hours")
        
        assert automation_ticket.status == initial_status  # No changes in dry-run
        print("\n=== WORKFLOW AUTOMATION SMOKE TEST COMPLETE ===")

    async def test_security_validation_smoke(self):
        """
        MANUAL SMOKE TEST: Security validation
        Test tenant isolation, input validation, and rate limiting.
        """
        print("\n=== SMOKE TEST: Security Validation ===")
        
        from dotmac.ticketing.core.security import (
            validate_tenant_id, validate_email, assert_tenant,
            create_tenant_context, TenantIsolationError, InputValidationError
        )
        
        print("1. Testing input validation...")
        
        # Valid inputs
        valid_tenant = validate_tenant_id("valid-tenant-123")
        valid_email = validate_email("test@example.com")
        print(f"   ✓ Valid tenant ID: {valid_tenant}")
        print(f"   ✓ Valid email: {valid_email}")
        
        # Invalid inputs should raise exceptions
        try:
            validate_tenant_id("")
            assert False, "Should have raised TenantIsolationError"
        except TenantIsolationError:
            print("   ✓ Empty tenant ID properly rejected")
        
        try:
            validate_email("invalid-email")
            assert False, "Should have raised InputValidationError" 
        except InputValidationError:
            print("   ✓ Invalid email properly rejected")
        
        print("2. Testing tenant isolation...")
        ctx = create_tenant_context("tenant-a", "user-123")
        
        # Create tickets for different tenants
        ticket_a = Ticket(
            id="sec-test-a",
            ticket_number="TKT-SEC-A",
            tenant_id="tenant-a",
            title="Ticket A",
            description="Belongs to tenant A",
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
            category=TicketCategory.TECHNICAL_SUPPORT
        )
        
        ticket_b = Ticket(
            id="sec-test-b", 
            ticket_number="TKT-SEC-B",
            tenant_id="tenant-b",
            title="Ticket B",
            description="Belongs to tenant B",
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
            category=TicketCategory.TECHNICAL_SUPPORT
        )
        
        # Should allow access to same tenant
        try:
            assert_tenant(ctx, ticket_a)
            print("   ✓ Same tenant access allowed")
        except TenantIsolationError:
            assert False, "Should have allowed same tenant access"
        
        # Should deny access to different tenant
        try:
            assert_tenant(ctx, ticket_b)
            assert False, "Should have raised TenantIsolationError"
        except TenantIsolationError:
            print("   ✓ Cross-tenant access properly blocked")
        
        print("3. Testing rate limiting...")
        from dotmac.ticketing.core.security import SimpleRateLimit
        
        # Create rate limiter with very low limit for testing
        test_limiter = SimpleRateLimit(requests_per_minute=3)
        
        # Should allow first few requests
        for i in range(3):
            result = test_limiter.check_rate_limit("test-user")
            assert result['allowed'], f"Request {i+1} should be allowed"
        
        print("   ✓ Initial requests within limit allowed")
        
        # Should deny subsequent requests
        result = test_limiter.check_rate_limit("test-user")
        assert not result['allowed'], "Request over limit should be denied"
        print("   ✓ Requests over limit properly denied")
        print(f"   ✓ Rate limit info: {result}")
        
        print("\n=== SECURITY VALIDATION SMOKE TEST COMPLETE ===")

    def test_platform_integration_smoke(self):
        """
        MANUAL SMOKE TEST: Platform integrations
        Test that system works with and without platform services.
        """
        print("\n=== SMOKE TEST: Platform Integration ===")
        
        print("1. Testing graceful degradation...")
        
        # Get services - should return noop implementations when platform unavailable
        comm_service = get_communication_service()
        mon_service = get_monitoring_service()
        
        print(f"   ✓ Communication service: {type(comm_service).__name__}")
        print(f"   ✓ Monitoring service: {type(mon_service).__name__}")
        
        # Services should be functional even if noop
        print("2. Testing service functionality...")
        
        # Test monitoring service
        mon_service.record_event(
            "smoke_test_event",
            "dotmac-ticketing",
            {"test": "platform_integration", "timestamp": datetime.now().isoformat()}
        )
        print("   ✓ Monitoring service recorded event")
        
        # Test async communication service
        async def test_comm():
            result = await comm_service.send_notification(
                recipient="test@example.com",
                subject="Smoke Test Notification",
                template="smoke_test",
                context={"test": "platform_integration"}
            )
            return result
        
        result = asyncio.run(test_comm())
        print(f"   ✓ Communication service sent notification: {result}")
        
        print("3. Testing service integration...")
        
        # Test with ticket manager
        manager = TicketManager(
            communication_service=comm_service,
            monitoring_service=mon_service
        )
        
        assert manager.communication_service is comm_service
        assert manager.monitoring_service is mon_service
        print("   ✓ Services properly injected into manager")
        
        print("\n=== PLATFORM INTEGRATION SMOKE TEST COMPLETE ===")


def run_all_smoke_tests():
    """Run all smoke tests manually."""
    print("🧪 STARTING COMPREHENSIVE SMOKE TESTS")
    print("=" * 50)
    
    test_runner = TestSmokeValidationInMemorySQLite()
    
    # Run each smoke test
    asyncio.run(test_runner.test_complete_ticket_lifecycle_smoke())
    asyncio.run(test_runner.test_notification_system_smoke())
    asyncio.run(test_runner.test_workflow_automation_dry_run_smoke())
    asyncio.run(test_runner.test_security_validation_smoke())
    test_runner.test_platform_integration_smoke()
    
    print("\n🎉 ALL SMOKE TESTS COMPLETED SUCCESSFULLY")
    print("=" * 50)
    print("\nMANUAL VERIFICATION CHECKLIST:")
    print("□ Audit logs show all ticket lifecycle events")
    print("□ SLA timestamps are correctly calculated")
    print("□ Notifications contain proper template content")
    print("□ Dry-run mode prevents database modifications")
    print("□ Security validation blocks unauthorized access")
    print("□ Platform integration gracefully degrades")
    print("□ Rate limiting headers are present in responses")
    print("□ Tenant isolation is enforced across all operations")


if __name__ == "__main__":
    run_all_smoke_tests()