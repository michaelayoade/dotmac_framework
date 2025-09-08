"""
Integration tests for workflow automation engine and task decorator integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from dotmac.ticketing.workflows.automation import (
    TicketAutomationEngine,
    AutoAssignmentRule,
    EscalationRule,
    SLAMonitor,
    get_task_decorator
)
from dotmac.ticketing.workflows.base import WorkflowResult
from dotmac.ticketing.core.models import Ticket, TicketStatus, TicketPriority, TicketCategory


@pytest.fixture
def mock_db_session_factory():
    """Mock database session factory."""
    mock_session = AsyncMock()
    mock_factory = AsyncMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_factory


@pytest.fixture
def sample_ticket():
    """Sample ticket for testing."""
    return Ticket(
        id="ticket-123",
        ticket_number="TKT-123",
        tenant_id="test-tenant",
        title="Network Issue",
        description="Internet connectivity problem",
        status=TicketStatus.OPEN,
        priority=TicketPriority.NORMAL,
        category=TicketCategory.TECHNICAL_SUPPORT,
        customer_email="user@example.com",
        created_at=datetime.now(timezone.utc)
    )


class TestTaskDecoratorIntegration:
    """Test task decorator integration functionality."""

    def test_get_task_decorator_with_dotmac_tasks_available(self):
        """Test get_task_decorator returns decorator when dotmac.tasks available."""
        mock_task_decorator = MagicMock()
        
        with patch.dict('sys.modules', {
            'dotmac.tasks.decorators': MagicMock(task=mock_task_decorator)
        }):
            result = get_task_decorator()
            assert result is mock_task_decorator

    @patch('dotmac.ticketing.workflows.automation.logger')
    def test_get_task_decorator_fallback(self, mock_logger):
        """Test get_task_decorator returns None when dotmac.tasks unavailable."""
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            result = get_task_decorator()
            
            assert result is None
            mock_logger.debug.assert_called_once_with(
                "dotmac.tasks.decorators not available, using direct execution"
            )


class TestTicketAutomationEngineIntegration:
    """Test TicketAutomationEngine integration features."""

    def test_automation_engine_initialization(self, mock_db_session_factory):
        """Test automation engine initializes with correct configuration."""
        config = {
            'dry_run_mode': True,
            'custom_setting': 'test_value'
        }
        
        engine = TicketAutomationEngine(
            db_session_factory=mock_db_session_factory,
            config=config,
            enable_background_tasks=False
        )
        
        assert engine.dry_run_mode is True
        assert engine.enable_background_tasks is False
        assert engine.config['custom_setting'] == 'test_value'
        assert len(engine.workflows) == 3  # Default workflows
        assert 'customer_support' in engine.workflows
        assert 'technical_support' in engine.workflows
        assert 'billing_issue' in engine.workflows

    def test_automation_engine_with_task_decorator(self, mock_db_session_factory):
        """Test automation engine with task decorator available."""
        mock_task_decorator = MagicMock()
        
        with patch('dotmac.ticketing.workflows.automation.get_task_decorator', 
                   return_value=mock_task_decorator):
            engine = TicketAutomationEngine(
                db_session_factory=mock_db_session_factory,
                enable_background_tasks=True
            )
            
            assert engine.task_decorator is mock_task_decorator

    def test_automation_engine_without_task_decorator(self, mock_db_session_factory):
        """Test automation engine without task decorator."""
        with patch('dotmac.ticketing.workflows.automation.get_task_decorator', 
                   return_value=None):
            engine = TicketAutomationEngine(
                db_session_factory=mock_db_session_factory,
                enable_background_tasks=True
            )
            
            assert engine.task_decorator is None

    async def test_process_new_ticket_with_dry_run(self, mock_db_session_factory, sample_ticket):
        """Test processing new ticket in dry run mode."""
        engine = TicketAutomationEngine(
            db_session_factory=mock_db_session_factory,
            config={'dry_run_mode': True}
        )
        
        # Add assignment rule
        rule = AutoAssignmentRule(
            name="Technical Support Rule",
            conditions={"category": TicketCategory.TECHNICAL_SUPPORT},
            assigned_team="tech_support",
            priority=10
        )
        engine.add_assignment_rule(rule)
        
        mock_db = AsyncMock()
        
        with patch('dotmac.ticketing.workflows.automation.logger') as mock_logger:
            await engine.process_new_ticket(sample_ticket, "test-tenant", mock_db)
            
            # Should log dry run action
            mock_logger.info.assert_any_call(
                f"DRY RUN: Would auto-assign ticket {sample_ticket.id} to tech_support "
                f"using rule 'Technical Support Rule'"
            )

    async def test_workflow_execution_with_task_decorator(
        self, mock_db_session_factory, sample_ticket
    ):
        """Test workflow execution uses task decorator when available."""
        mock_task_decorator = MagicMock()
        mock_workflow = AsyncMock()
        mock_workflow.should_trigger.return_value = True
        mock_workflow.workflow_type = "test_workflow"
        mock_workflow.execute.return_value = [
            WorkflowResult(step_name="test_step", success=True, result="completed")
        ]
        
        with patch('dotmac.ticketing.workflows.automation.get_task_decorator', 
                   return_value=mock_task_decorator):
            engine = TicketAutomationEngine(
                db_session_factory=mock_db_session_factory,
                enable_background_tasks=True
            )
            engine.register_workflow("test_workflow", mock_workflow)
            
            mock_db = AsyncMock()
            await engine._trigger_workflows(sample_ticket, "test-tenant", mock_db)
            
            # Should have used task decorator
            mock_task_decorator.assert_called_once()

    async def test_workflow_execution_with_asyncio_task(
        self, mock_db_session_factory, sample_ticket
    ):
        """Test workflow execution uses asyncio when task decorator unavailable."""
        mock_workflow = AsyncMock()
        mock_workflow.should_trigger.return_value = True
        mock_workflow.workflow_type = "test_workflow"
        mock_workflow.execute.return_value = [
            WorkflowResult(step_name="test_step", success=True, result="completed")
        ]
        
        with patch('dotmac.ticketing.workflows.automation.get_task_decorator', 
                   return_value=None):
            with patch('asyncio.create_task') as mock_create_task:
                engine = TicketAutomationEngine(
                    db_session_factory=mock_db_session_factory,
                    enable_background_tasks=True
                )
                engine.register_workflow("test_workflow", mock_workflow)
                
                mock_db = AsyncMock()
                await engine._trigger_workflows(sample_ticket, "test-tenant", mock_db)
                
                # Should have used asyncio.create_task
                mock_create_task.assert_called_once()

    async def test_workflow_execution_synchronous(
        self, mock_db_session_factory, sample_ticket
    ):
        """Test workflow execution runs synchronously when background tasks disabled."""
        mock_workflow = AsyncMock()
        mock_workflow.should_trigger.return_value = True
        mock_workflow.workflow_type = "test_workflow"
        mock_workflow.execute.return_value = [
            WorkflowResult(step_name="test_step", success=True, result="completed")
        ]
        
        engine = TicketAutomationEngine(
            db_session_factory=mock_db_session_factory,
            enable_background_tasks=False
        )
        engine.register_workflow("test_workflow", mock_workflow)
        
        mock_db = AsyncMock()
        await engine._trigger_workflows(sample_ticket, "test-tenant", mock_db)
        
        # Should have executed workflow directly
        mock_workflow.execute.assert_called_once()

    async def test_assignment_rule_matching(self, mock_db_session_factory, sample_ticket):
        """Test assignment rule matching logic."""
        engine = TicketAutomationEngine(mock_db_session_factory)
        
        # Test exact match
        rule1 = AutoAssignmentRule(
            name="Exact Match Rule",
            conditions={"category": TicketCategory.TECHNICAL_SUPPORT},
            assigned_team="tech_team"
        )
        
        # Test list match
        rule2 = AutoAssignmentRule(
            name="List Match Rule", 
            conditions={"priority": [TicketPriority.HIGH, TicketPriority.URGENT]},
            assigned_team="priority_team"
        )
        
        # Test complex condition
        rule3 = AutoAssignmentRule(
            name="Complex Rule",
            conditions={"title": {"operator": "contains", "value": "network"}},
            assigned_team="network_team"
        )
        
        # Rule1 should match
        assert await engine._rule_matches_ticket(rule1.conditions, sample_ticket)
        
        # Rule2 should not match (normal priority)
        assert not await engine._rule_matches_ticket(rule2.conditions, sample_ticket)
        
        # Rule3 should match (title contains "Network")
        assert await engine._rule_matches_ticket(rule3.conditions, sample_ticket)

    async def test_escalation_rule_processing(self, mock_db_session_factory):
        """Test escalation rule processing."""
        engine = TicketAutomationEngine(mock_db_session_factory)
        
        # Create old ticket that should be escalated
        old_ticket = Ticket(
            id="old-ticket",
            ticket_number="TKT-OLD",
            tenant_id="test-tenant", 
            title="Old Issue",
            description="Long running issue",
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
            category=TicketCategory.TECHNICAL_SUPPORT,
            created_at=datetime.now(timezone.utc) - timedelta(hours=25)
        )
        
        # Add escalation rule
        escalation_rule = EscalationRule(
            name="24 Hour Escalation",
            conditions={"status": TicketStatus.OPEN},
            escalation_time_hours=24,
            escalate_to_team="senior_support",
            priority_increase=True
        )
        engine.add_escalation_rule(escalation_rule)
        
        mock_db = AsyncMock()
        current_time = datetime.now(timezone.utc)
        
        await engine._check_ticket_escalation(old_ticket, current_time, mock_db)
        
        # Ticket should be escalated
        assert old_ticket.status == TicketStatus.ESCALATED
        assert old_ticket.assigned_team == "senior_support"
        assert old_ticket.priority == TicketPriority.HIGH  # Increased from NORMAL


class TestSLAMonitorIntegration:
    """Test SLA Monitor integration functionality."""

    def test_sla_monitor_initialization(self, mock_db_session_factory):
        """Test SLA Monitor initializes with correct configuration."""
        monitor = SLAMonitor(mock_db_session_factory)
        
        assert monitor.db_session_factory is mock_db_session_factory
        assert TicketPriority.CRITICAL in monitor.sla_config
        assert TicketPriority.LOW in monitor.sla_config
        
        # Check critical priority has shortest times
        critical_config = monitor.sla_config[TicketPriority.CRITICAL]
        assert critical_config["response"] == 0.25  # 15 minutes
        assert critical_config["resolution"] == 4    # 4 hours

    async def test_sla_breach_time_calculation(self, mock_db_session_factory, sample_ticket):
        """Test SLA breach time calculation."""
        monitor = SLAMonitor(mock_db_session_factory)
        
        # Test normal priority
        breach_time = await monitor.calculate_sla_breach_time(sample_ticket, "resolution")
        expected_time = sample_ticket.created_at + timedelta(hours=72)
        assert breach_time == expected_time
        
        # Test response time
        response_breach = await monitor.calculate_sla_breach_time(sample_ticket, "response")
        expected_response = sample_ticket.created_at + timedelta(hours=24)
        assert response_breach == expected_response

    async def test_sla_breach_detection(self, mock_db_session_factory):
        """Test SLA breach detection."""
        monitor = SLAMonitor(mock_db_session_factory)
        
        # Create ticket that has breached SLA
        breached_ticket = Ticket(
            id="breached-123",
            ticket_number="TKT-BREACHED",
            tenant_id="test-tenant",
            title="Breached Ticket",
            description="This ticket breached SLA",
            status=TicketStatus.OPEN,
            priority=TicketPriority.CRITICAL,
            sla_breach_time=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [breached_ticket]
        
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        
        mock_factory = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        monitor.db_session_factory = mock_factory
        
        breached_tickets = await monitor.check_sla_breaches("test-tenant")
        
        assert len(breached_tickets) == 1
        assert breached_tickets[0].id == "breached-123"

    async def test_update_ticket_sla(self, mock_db_session_factory, sample_ticket):
        """Test updating ticket SLA breach time."""
        monitor = SLAMonitor(mock_db_session_factory)
        mock_db = AsyncMock()
        
        await monitor.update_ticket_sla(sample_ticket, mock_db)
        
        # Should have set SLA breach time
        assert sample_ticket.sla_breach_time is not None
        mock_db.commit.assert_called_once()


class TestWorkflowErrorHandling:
    """Test workflow error handling and recovery."""

    async def test_workflow_execution_error_handling(self, mock_db_session_factory):
        """Test workflow execution handles errors gracefully."""
        mock_workflow = AsyncMock()
        mock_workflow.should_trigger.return_value = True
        mock_workflow.workflow_type = "failing_workflow"
        mock_workflow.execute.side_effect = Exception("Workflow failed")
        
        engine = TicketAutomationEngine(
            db_session_factory=mock_db_session_factory,
            enable_background_tasks=False
        )
        engine.register_workflow("failing_workflow", mock_workflow)
        
        with patch('dotmac.ticketing.workflows.automation.logger') as mock_logger:
            await engine._execute_workflow_safe(mock_workflow)
            
            # Should log error
            mock_logger.error.assert_called_once_with(
                "Workflow failing_workflow failed: Workflow failed"
            )

    async def test_process_new_ticket_error_handling(
        self, mock_db_session_factory, sample_ticket
    ):
        """Test process_new_ticket handles errors and re-raises."""
        engine = TicketAutomationEngine(mock_db_session_factory)
        
        # Mock SLA monitor to raise exception
        engine.sla_monitor.update_ticket_sla = AsyncMock(
            side_effect=Exception("SLA update failed")
        )
        
        mock_db = AsyncMock()
        
        with pytest.raises(Exception) as exc_info:
            await engine.process_new_ticket(sample_ticket, "test-tenant", mock_db)
        
        assert "SLA update failed" in str(exc_info.value)