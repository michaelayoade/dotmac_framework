"""
Network Operations Integration Tests.

Comprehensive tests for NOC, orchestration, and event-driven architecture
integration to validate end-to-end network operations functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the modules we've implemented
from dotmac_isp.modules.noc.services.noc_dashboard_service import NOCDashboardService
from dotmac_isp.modules.noc.services.alarm_management_service import AlarmManagementService
from dotmac_isp.modules.noc.services.event_correlation_service import EventCorrelationService
from dotmac_isp.modules.orchestration.services.network_orchestrator import NetworkOrchestrationService
from dotmac_isp.modules.events.services.event_bus import EventBusService
from dotmac_isp.modules.events.handlers.device_event_handlers import DeviceEventHandlers


# Mock database setup for testing
@pytest.fixture
def test_db():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables (in real implementation, this would use Alembic migrations)
    # For now, we'll mock the database interactions
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def tenant_id():
    """Test tenant ID."""
    return "test-tenant-123"


class TestNOCDashboardService:
    """Test NOC Dashboard Service functionality."""

    @pytest.mark.asyncio
    async def test_get_network_status_overview(self, test_db, tenant_id):
        """Test network status overview retrieval."""
        service = NOCDashboardService(test_db, tenant_id)
        
        # Mock database queries
        test_db.query = MagicMock()
        test_db.query.return_value.filter.return_value.count.return_value = 10  # Total devices
        
        result = await service.get_network_status_overview()
        
        assert "network_health" in result
        assert "device_summary" in result
        assert "alarm_summary" in result
        assert "activity_summary" in result
        
        assert "overall_score" in result["network_health"]
        assert "total_devices" in result["device_summary"]

    @pytest.mark.asyncio
    async def test_get_device_status_summary(self, test_db, tenant_id):
        """Test device status summary retrieval."""
        service = NOCDashboardService(test_db, tenant_id)
        
        # Mock device query
        mock_device = MagicMock()
        mock_device.device_id = "device-123"
        mock_device.hostname = "router-01"
        mock_device.device_type = "router"
        mock_device.status = "active"
        mock_device.site_id = "site-01"
        mock_device.management_ip = "192.168.1.1"
        mock_device.updated_at = datetime.utcnow()
        
        test_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_device]
        
        result = await service.get_device_status_summary(limit=10, include_metrics=False)
        
        assert "devices" in result
        assert len(result["devices"]) > 0
        assert result["devices"][0]["device_id"] == "device-123"
        assert result["devices"][0]["hostname"] == "router-01"

    @pytest.mark.asyncio
    async def test_get_network_performance_metrics(self, test_db, tenant_id):
        """Test network performance metrics calculation."""
        service = NOCDashboardService(test_db, tenant_id)
        
        # Mock metrics queries
        test_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            avg_cpu=25.5, max_cpu=85.0, sample_count=100, avg_memory=45.2, max_memory=78.3,
            monitored_devices=10, total_interfaces_up=50, total_interfaces_down=2
        )
        
        result = await service.get_network_performance_metrics()
        
        assert "cpu_utilization" in result
        assert "memory_utilization" in result
        assert "interface_summary" in result
        assert result["cpu_utilization"]["average_percent"] == 25.5
        assert result["interface_summary"]["availability_percentage"] > 0


class TestAlarmManagementService:
    """Test Alarm Management Service functionality."""

    @pytest.mark.asyncio
    async def test_create_alarm(self, test_db, tenant_id):
        """Test alarm creation."""
        service = AlarmManagementService(test_db, tenant_id)
        
        # Mock database operations
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        test_db.query.return_value.filter.return_value.first.return_value = None  # No existing alarm
        
        alarm_data = {
            "alarm_type": "device_down",
            "severity": "critical",
            "title": "Device router-01 is down",
            "description": "Device router-01 is not responding",
            "device_id": "device-123",
            "source_system": "monitoring"
        }
        
        result = await service.create_alarm(alarm_data)
        
        assert "alarm_id" in result
        assert result["alarm_type"] == "device_down"
        assert result["severity"] == "critical"
        assert result["title"] == "Device router-01 is down"

    @pytest.mark.asyncio
    async def test_acknowledge_alarm(self, test_db, tenant_id):
        """Test alarm acknowledgment."""
        service = AlarmManagementService(test_db, tenant_id)
        
        # Mock existing alarm
        mock_alarm = MagicMock()
        mock_alarm.alarm_id = "alarm-123"
        mock_alarm.status = "active"
        mock_alarm.to_dict.return_value = {"alarm_id": "alarm-123", "status": "acknowledged"}
        
        test_db.query.return_value.filter.return_value.first.return_value = mock_alarm
        test_db.commit = MagicMock()
        
        result = await service.acknowledge_alarm("alarm-123", "operator-01", "Investigating issue")
        
        assert result["alarm_id"] == "alarm-123"
        assert result["status"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_create_alarm_rule(self, test_db, tenant_id):
        """Test alarm rule creation."""
        service = AlarmManagementService(test_db, tenant_id)
        
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        
        rule_data = {
            "name": "High CPU Alert",
            "metric_name": "cpu_usage",
            "threshold_value": 90,
            "threshold_operator": ">",
            "alarm_type": "high_cpu",
            "alarm_severity": "major"
        }
        
        result = await service.create_alarm_rule(rule_data)
        
        assert "rule_id" in result
        assert result["name"] == "High CPU Alert"
        assert result["alarm_type"] == "high_cpu"

    @pytest.mark.asyncio
    async def test_evaluate_alarm_rules(self, test_db, tenant_id):
        """Test alarm rule evaluation against metrics."""
        service = AlarmManagementService(test_db, tenant_id)
        
        # Mock alarm rule
        mock_rule = MagicMock()
        mock_rule.rule_id = "rule-123"
        mock_rule.metric_name = "cpu_usage"
        mock_rule.threshold_value = "85"
        mock_rule.threshold_operator = ">"
        mock_rule.alarm_type = "high_cpu"
        mock_rule.alarm_severity = "major"
        mock_rule.alarm_title_template = "High CPU: {value}%"
        mock_rule.alarm_description_template = "CPU usage is {value}%, threshold: {threshold}%"
        
        test_db.query.return_value.filter.return_value.all.return_value = [mock_rule]
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        
        metrics = {
            "device_id": "device-123",
            "cpu_usage": 92.5  # Above threshold
        }
        
        result = await service.evaluate_alarm_rules(metrics)
        
        assert len(result) > 0
        assert result[0]["alarm_type"] == "high_cpu"


class TestEventCorrelationService:
    """Test Event Correlation Service functionality."""

    @pytest.mark.asyncio
    async def test_process_incoming_event(self, test_db, tenant_id):
        """Test event processing and correlation."""
        service = EventCorrelationService(test_db, tenant_id)
        
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        test_db.query.return_value.filter.return_value.all.return_value = []  # No related events
        
        event_data = {
            "event_type": "device_state_change",
            "severity": "high",
            "title": "Device router-01 went down",
            "description": "Device router-01 changed state to down",
            "device_id": "device-123",
            "current_state": "down",
            "previous_state": "up"
        }
        
        result = await service.process_incoming_event(event_data)
        
        assert "event_id" in result
        assert "correlation_results" in result
        assert "event_data" in result

    @pytest.mark.asyncio
    async def test_analyze_event_patterns(self, test_db, tenant_id):
        """Test event pattern analysis."""
        service = EventCorrelationService(test_db, tenant_id)
        
        # Mock events for pattern analysis
        mock_events = []
        for i in range(15):  # Create enough events for pattern detection
            mock_event = MagicMock()
            mock_event.device_id = "device-123" if i < 12 else f"device-{i}"
            mock_event.event_type = "interface_state_change"
            mock_event.event_timestamp = datetime.utcnow() - timedelta(hours=i)
            mock_events.append(mock_event)
        
        test_db.query.return_value.filter.return_value.all.return_value = mock_events
        
        result = await service.analyze_event_patterns(time_window_hours=24, min_event_count=5)
        
        assert "total_events" in result
        assert "patterns" in result
        assert "anomalies" in result
        assert result["total_events"] == 15


class TestNetworkOrchestrationService:
    """Test Network Orchestration Service functionality."""

    @pytest.mark.asyncio
    async def test_provision_customer_service(self, test_db, tenant_id):
        """Test customer service provisioning workflow."""
        service = NetworkOrchestrationService(test_db, tenant_id)
        
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        
        result = await service.provision_customer_service(
            customer_id="cust-123",
            service_plan_id="plan-456",
            service_address="123 Main St",
            installation_options={"fiber_type": "single_mode"}
        )
        
        assert "workflow_id" in result
        assert result["workflow_type"] == "customer_provisioning"
        assert result["customer_id"] == "cust-123"

    @pytest.mark.asyncio
    async def test_modify_service_bandwidth(self, test_db, tenant_id):
        """Test service bandwidth modification workflow."""
        service = NetworkOrchestrationService(test_db, tenant_id)
        
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        
        result = await service.modify_service_bandwidth(
            service_id="svc-789",
            new_bandwidth="100M",
            effective_date=datetime.utcnow() + timedelta(days=1)
        )
        
        assert "workflow_id" in result
        assert result["workflow_type"] == "service_modification"
        assert result["service_id"] == "svc-789"

    @pytest.mark.asyncio
    async def test_create_workflow_execution(self, test_db, tenant_id):
        """Test workflow execution creation."""
        service = NetworkOrchestrationService(test_db, tenant_id)
        
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        
        workflow_data = {
            "workflow_type": "test_workflow",
            "workflow_name": "Test Workflow",
            "input_parameters": {"param1": "value1"}
        }
        
        result = await service.create_workflow_execution(workflow_data)
        
        assert "workflow_id" in result
        assert result["workflow_type"] == "test_workflow"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_add_workflow_steps(self, test_db, tenant_id):
        """Test adding steps to workflow."""
        service = NetworkOrchestrationService(test_db, tenant_id)
        
        # Mock existing workflow
        mock_workflow = MagicMock()
        mock_workflow.workflow_id = "workflow-123"
        test_db.query.return_value.filter.return_value.first.return_value = mock_workflow
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        
        steps_data = [
            {
                "step_name": "Test Step 1",
                "step_type": "validation",
                "service_method": "_test_method",
                "step_order": 1
            },
            {
                "step_name": "Test Step 2",
                "step_type": "execution",
                "service_method": "_test_method_2",
                "step_order": 2
            }
        ]
        
        result = await service.add_workflow_steps("workflow-123", steps_data)
        
        assert len(result) == 2
        assert result[0]["step_name"] == "Test Step 1"
        assert result[1]["step_name"] == "Test Step 2"


class TestEventBusService:
    """Test Event Bus Service functionality."""

    @pytest.mark.asyncio
    async def test_publish_event(self, test_db, tenant_id):
        """Test event publishing."""
        service = EventBusService(test_db, tenant_id)
        
        event_id = await service.publish_event(
            event_type="test.event",
            data={"test_key": "test_value"},
            source="test_system"
        )
        
        assert event_id is not None
        assert len(event_id) > 0

    @pytest.mark.asyncio
    async def test_subscribe_and_dispatch(self, test_db, tenant_id):
        """Test event subscription and dispatching."""
        service = EventBusService(test_db, tenant_id)
        
        # Create mock handler
        handler_called = False
        received_event = None
        
        async def test_handler(event):
            nonlocal handler_called, received_event
            handler_called = True
            received_event = event
        
        # Subscribe to event
        subscription_id = await service.subscribe("test.event", test_handler)
        
        # Publish event
        await service.publish_event(
            event_type="test.event",
            data={"message": "hello world"}
        )
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify handler was called
        assert handler_called
        assert received_event is not None
        assert received_event["event_type"] == "test.event"
        assert received_event["data"]["message"] == "hello world"

    @pytest.mark.asyncio
    async def test_device_health_event(self, test_db, tenant_id):
        """Test device health event publishing."""
        service = EventBusService(test_db, tenant_id)
        
        event_id = await service.publish_device_health_event(
            device_id="device-123",
            health_status="critical",
            health_score=25.5,
            metrics={"cpu_usage": 95, "memory_usage": 87}
        )
        
        assert event_id is not None


class TestDeviceEventHandlers:
    """Test Device Event Handlers functionality."""

    @pytest.mark.asyncio
    async def test_handle_device_health_changed(self, test_db, tenant_id):
        """Test device health change event handling."""
        handler = DeviceEventHandlers(test_db, tenant_id)
        
        # Mock services
        handler.alarm_service = AsyncMock()
        handler.correlation_service = AsyncMock()
        handler.alarm_service.create_alarm = AsyncMock(return_value={"alarm_id": "alarm-123"})
        handler.correlation_service.process_incoming_event = AsyncMock(return_value={"event_id": "event-123"})
        handler.alarm_service.evaluate_alarm_rules = AsyncMock(return_value=[])
        
        event = {
            "event_id": "event-123",
            "event_type": "device.health.changed",
            "data": {
                "device_id": "device-123",
                "health_status": "critical",
                "health_score": 25.0,
                "metrics": {"cpu_usage": 95, "memory_usage": 87}
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await handler.handle_device_health_changed(event)
        
        # Verify correlation service was called
        handler.correlation_service.process_incoming_event.assert_called_once()
        
        # Verify alarm was created for critical health
        handler.alarm_service.evaluate_alarm_rules.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_device_state_change(self, test_db, tenant_id):
        """Test device state change event handling."""
        handler = DeviceEventHandlers(test_db, tenant_id)
        
        # Mock services
        handler.alarm_service = AsyncMock()
        handler.correlation_service = AsyncMock()
        handler.alarm_service.create_alarm = AsyncMock(return_value={"alarm_id": "alarm-123"})
        handler.correlation_service.process_incoming_event = AsyncMock(return_value={"event_id": "event-123"})
        
        event = {
            "event_id": "event-123",
            "event_type": "device.state.changed",
            "data": {
                "device_id": "device-123",
                "current_state": "down",
                "previous_state": "up"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await handler.handle_device_state_change(event)
        
        # Verify correlation event was created
        handler.correlation_service.process_incoming_event.assert_called_once()
        
        # Verify device down alarm was created
        handler.alarm_service.create_alarm.assert_called_once()
        alarm_call_args = handler.alarm_service.create_alarm.call_args[0][0]
        assert alarm_call_args["alarm_type"] == "device_down"
        assert alarm_call_args["severity"] == "critical"


class TestIntegrationEndToEnd:
    """Test end-to-end integration scenarios."""

    @pytest.mark.asyncio
    async def test_device_failure_to_alarm_workflow(self, test_db, tenant_id):
        """Test complete workflow from device failure detection to alarm creation."""
        # Initialize services
        event_bus = EventBusService(test_db, tenant_id)
        device_handler = DeviceEventHandlers(test_db, tenant_id)
        
        # Mock dependent services
        device_handler.alarm_service = AsyncMock()
        device_handler.correlation_service = AsyncMock()
        device_handler.alarm_service.create_alarm = AsyncMock(return_value={"alarm_id": "alarm-123"})
        device_handler.correlation_service.process_incoming_event = AsyncMock(return_value={"event_id": "event-123"})
        
        # Subscribe device handler to health events
        await event_bus.subscribe("device.health.changed", device_handler.handle_device_health_changed)
        
        # Publish device health change event
        await event_bus.publish_device_health_event(
            device_id="device-123",
            health_status="critical",
            health_score=15.0,
            metrics={"cpu_usage": 98, "memory_usage": 95, "interface_errors": 150}
        )
        
        # Wait for event processing
        await asyncio.sleep(0.2)
        
        # Verify the complete workflow executed
        device_handler.correlation_service.process_incoming_event.assert_called()
        device_handler.alarm_service.evaluate_alarm_rules.assert_called()

    @pytest.mark.asyncio
    async def test_service_provisioning_workflow(self, test_db, tenant_id):
        """Test complete service provisioning workflow."""
        orchestrator = NetworkOrchestrationService(test_db, tenant_id)
        
        # Mock database operations
        test_db.add = MagicMock()
        test_db.commit = MagicMock()
        
        # Start provisioning workflow
        result = await orchestrator.provision_customer_service(
            customer_id="cust-123",
            service_plan_id="plan-fiber-100",
            service_address="123 Tech Street",
            installation_options={"priority": "high"}
        )
        
        # Verify workflow was created
        assert result["workflow_type"] == "customer_provisioning"
        assert result["status"] == "pending"
        assert "workflow_id" in result


# Integration test configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])