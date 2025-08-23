"""Tests for plugin database models."""

import pytest
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from dotmac_isp.plugins.core.models import (
    PluginStatusDB,
    PluginCategoryDB,
    PluginRegistry,
    PluginConfiguration,
    PluginInstance,
    PluginEvent,
    PluginMetrics,
)


class TestPluginStatusDB:
    """Test PluginStatusDB enum."""
    
    def test_plugin_status_db_values(self):
        """Test PluginStatusDB enum values."""
        assert PluginStatusDB.REGISTERED.value == "registered"
        assert PluginStatusDB.INSTALLED.value == "installed"
        assert PluginStatusDB.ACTIVE.value == "active"
        assert PluginStatusDB.INACTIVE.value == "inactive"
        assert PluginStatusDB.ERROR.value == "error"
        assert PluginStatusDB.DISABLED.value == "disabled"
    
    def test_plugin_status_db_count(self):
        """Test expected number of status values."""
        assert len(PluginStatusDB) == 6


class TestPluginCategoryDB:
    """Test PluginCategoryDB enum."""
    
    def test_plugin_category_db_values(self):
        """Test PluginCategoryDB enum values."""
        assert PluginCategoryDB.NETWORK_AUTOMATION.value == "network_automation"
        assert PluginCategoryDB.GIS_LOCATION.value == "gis_location"
        assert PluginCategoryDB.BILLING_INTEGRATION.value == "billing_integration"
        assert PluginCategoryDB.CRM_INTEGRATION.value == "crm_integration"
        assert PluginCategoryDB.MONITORING.value == "monitoring"
        assert PluginCategoryDB.TICKETING.value == "ticketing"
        assert PluginCategoryDB.COMMUNICATION.value == "communication"
        assert PluginCategoryDB.REPORTING.value == "reporting"
        assert PluginCategoryDB.SECURITY.value == "security"
        assert PluginCategoryDB.CUSTOM.value == "custom"
    
    def test_plugin_category_db_count(self):
        """Test expected number of category values."""
        assert len(PluginCategoryDB) == 10


class TestPluginRegistryModel:
    """Test PluginRegistry database model."""
    
    def test_plugin_registry_creation(self):
        """Test basic PluginRegistry model creation."""
        tenant_id = uuid4()
        
        plugin_reg = PluginRegistry(
            tenant_id=tenant_id,
            plugin_id="test_plugin",
            plugin_name="Test Plugin",
            plugin_version="1.0.0",
            plugin_description="A test plugin",
            plugin_author="Test Author",
            category=PluginCategoryDB.CUSTOM,
            source_type="file",
            source_location="/path/to/plugin.py"
        )
        
        assert plugin_reg.tenant_id == tenant_id
        assert plugin_reg.plugin_id == "test_plugin"
        assert plugin_reg.plugin_name == "Test Plugin"
        assert plugin_reg.plugin_version == "1.0.0"
        assert plugin_reg.plugin_description == "A test plugin"
        assert plugin_reg.plugin_author == "Test Author"
        assert plugin_reg.category == PluginCategoryDB.CUSTOM
        assert plugin_reg.status == PluginStatusDB.REGISTERED  # Default
        assert plugin_reg.source_type == "file"
        assert plugin_reg.source_location == "/path/to/plugin.py"
        assert plugin_reg.python_requires == ">=3.11"  # Default
        assert plugin_reg.supports_multi_tenant is True  # Default
        assert plugin_reg.supports_hot_reload is False  # Default
        assert plugin_reg.requires_restart is False  # Default
        assert plugin_reg.security_level == "standard"  # Default
        assert plugin_reg.error_count == 0  # Default
        assert plugin_reg.load_count == 0  # Default
        assert plugin_reg.total_uptime_seconds == 0  # Default
    
    @patch('dotmac_isp.plugins.core.models.datetime')
    def test_record_load_success(self, mock_datetime):
        """Test record_load_success method."""
        mock_now = datetime(2023, 12, 15, 10, 30, 45)
        mock_datetime.utcnow.return_value = mock_now
        
        plugin_reg = PluginRegistry(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            plugin_name="Test Plugin",
            plugin_version="1.0.0",
            category=PluginCategoryDB.CUSTOM,
            source_type="file",
            source_location="/path/to/plugin.py",
            error_count=2,
            last_error="Previous error"
        )
        
        # Record successful load
        plugin_reg.record_load_success()
        
        assert plugin_reg.status == PluginStatusDB.ACTIVE
        assert plugin_reg.last_loaded == mock_now
        assert plugin_reg.load_count == 1
        assert plugin_reg.last_error is None
    
    def test_record_load_failure(self):
        """Test record_load_failure method."""
        plugin_reg = PluginRegistry(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            plugin_name="Test Plugin",
            plugin_version="1.0.0",
            category=PluginCategoryDB.CUSTOM,
            source_type="file",
            source_location="/path/to/plugin.py"
        )
        
        error_message = "Failed to import module"
        
        # Record load failure
        plugin_reg.record_load_failure(error_message)
        
        assert plugin_reg.status == PluginStatusDB.ERROR
        assert plugin_reg.last_error == error_message
        assert plugin_reg.error_count == 1
    
    def test_reset_error_state(self):
        """Test reset_error_state method."""
        plugin_reg = PluginRegistry(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            plugin_name="Test Plugin",
            plugin_version="1.0.0",
            category=PluginCategoryDB.CUSTOM,
            source_type="file",
            source_location="/path/to/plugin.py",
            status=PluginStatusDB.ERROR,
            last_error="Some error"
        )
        
        # Reset error state
        plugin_reg.reset_error_state()
        
        assert plugin_reg.status == PluginStatusDB.REGISTERED
        assert plugin_reg.last_error is None


class TestPluginConfigurationModel:
    """Test PluginConfiguration database model."""
    
    def test_plugin_configuration_creation(self):
        """Test basic PluginConfiguration model creation."""
        tenant_id = uuid4()
        
        config = PluginConfiguration(
            tenant_id=tenant_id,
            plugin_id="test_plugin",
            enabled=True,
            priority=150,
            config_data={"key": "value"},
            sandbox_enabled=False,
            resource_limits={"memory": "256MB"}
        )
        
        assert config.tenant_id == tenant_id
        assert config.plugin_id == "test_plugin"
        assert config.enabled is True
        assert config.priority == 150
        assert config.config_data == {"key": "value"}
        assert config.sandbox_enabled is False
        assert config.resource_limits == {"memory": "256MB"}
        assert config.metrics_enabled is True  # Default
        assert config.logging_enabled is True  # Default
        assert config.log_level == "INFO"  # Default
        assert config.auto_start is False  # Default
        assert config.restart_on_failure is True  # Default
        assert config.max_restart_attempts == 3  # Default
        assert config.is_valid is True  # Default
    
    def test_mark_invalid(self):
        """Test mark_invalid method."""
        config = PluginConfiguration(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            enabled=True,
            is_valid=True
        )
        
        errors = ["Invalid config parameter", "Missing required field"]
        
        # Mark as invalid
        config.mark_invalid(errors)
        
        assert config.is_valid is False
        assert config.validation_errors == errors
        assert config.enabled is False  # Auto-disabled
    
    @patch('dotmac_isp.plugins.core.models.datetime')
    def test_mark_valid(self, mock_datetime):
        """Test mark_valid method."""
        mock_now = datetime(2023, 12, 15, 10, 30, 45)
        mock_datetime.utcnow.return_value = mock_now
        
        config = PluginConfiguration(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            is_valid=False,
            validation_errors=["Some error"]
        )
        
        # Mark as valid
        config.mark_valid()
        
        assert config.is_valid is True
        assert config.validation_errors is None
        assert config.last_validated == mock_now


class TestPluginInstanceModel:
    """Test PluginInstance database model."""
    
    def test_plugin_instance_creation(self):
        """Test basic PluginInstance model creation."""
        tenant_id = uuid4()
        
        instance = PluginInstance(
            tenant_id=tenant_id,
            plugin_id="test_plugin",
            status=PluginStatusDB.ACTIVE,
            process_id=12345
        )
        
        assert instance.tenant_id == tenant_id
        assert instance.plugin_id == "test_plugin"
        assert instance.status == PluginStatusDB.ACTIVE
        assert instance.process_id == 12345
        assert len(instance.instance_id) == 36  # UUID string length
        assert instance.network_bytes_sent == 0  # Default
        assert instance.network_bytes_received == 0  # Default
        assert instance.health_status == "unknown"  # Default
        assert instance.error_count == 0  # Default
        assert instance.restart_count == 0  # Default
    
    def test_uptime_seconds_property_no_start_time(self):
        """Test uptime_seconds property with no start time."""
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.INACTIVE
        )
        
        assert instance.uptime_seconds == 0
    
    @patch('dotmac_isp.plugins.core.models.datetime')
    def test_uptime_seconds_property_with_times(self, mock_datetime):
        """Test uptime_seconds property with start/stop times."""
        start_time = datetime(2023, 12, 15, 10, 0, 0)
        stop_time = datetime(2023, 12, 15, 10, 5, 30)  # 5.5 minutes later
        mock_datetime.utcnow.return_value = stop_time
        
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.INACTIVE,
            started_at=start_time,
            stopped_at=stop_time
        )
        
        assert instance.uptime_seconds == 330  # 5.5 * 60 = 330 seconds
    
    @patch('dotmac_isp.plugins.core.models.datetime')
    def test_uptime_seconds_property_still_running(self, mock_datetime):
        """Test uptime_seconds property for still running instance."""
        start_time = datetime(2023, 12, 15, 10, 0, 0)
        current_time = datetime(2023, 12, 15, 10, 2, 0)  # 2 minutes later
        mock_datetime.utcnow.return_value = current_time
        
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.ACTIVE,
            started_at=start_time
            # No stopped_at - still running
        )
        
        assert instance.uptime_seconds == 120  # 2 * 60 = 120 seconds
    
    @patch('dotmac_isp.plugins.core.models.datetime')
    def test_record_start(self, mock_datetime):
        """Test record_start method."""
        mock_now = datetime(2023, 12, 15, 10, 30, 45)
        mock_datetime.utcnow.return_value = mock_now
        
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.INACTIVE
        )
        
        # Record start
        instance.record_start()
        
        assert instance.status == PluginStatusDB.ACTIVE
        assert instance.started_at == mock_now
        assert instance.stopped_at is None
        assert instance.last_heartbeat == mock_now
    
    @patch('dotmac_isp.plugins.core.models.datetime')
    def test_record_stop(self, mock_datetime):
        """Test record_stop method."""
        mock_now = datetime(2023, 12, 15, 10, 30, 45)
        mock_datetime.utcnow.return_value = mock_now
        
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.ACTIVE
        )
        
        # Record stop
        stop_reason = "User requested shutdown"
        instance.record_stop(stop_reason)
        
        assert instance.status == PluginStatusDB.INACTIVE
        assert instance.stopped_at == mock_now
        assert instance.last_error == stop_reason
    
    def test_record_stop_without_reason(self):
        """Test record_stop method without reason."""
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.ACTIVE,
            last_error="Previous error"
        )
        
        # Record stop without reason
        instance.record_stop()
        
        assert instance.status == PluginStatusDB.INACTIVE
        assert instance.last_error == "Previous error"  # Unchanged
    
    @patch('dotmac_isp.plugins.core.models.datetime')
    def test_record_heartbeat(self, mock_datetime):
        """Test record_heartbeat method."""
        mock_now = datetime(2023, 12, 15, 10, 30, 45)
        mock_datetime.utcnow.return_value = mock_now
        
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.ACTIVE
        )
        
        # Record heartbeat
        instance.record_heartbeat()
        
        assert instance.last_heartbeat == mock_now
    
    def test_record_error_below_threshold(self):
        """Test record_error method below error threshold."""
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.ACTIVE,
            error_count=2
        )
        
        error_message = "Some error occurred"
        
        # Record error
        instance.record_error(error_message)
        
        assert instance.error_count == 3
        assert instance.last_error == error_message
        assert instance.status == PluginStatusDB.ACTIVE  # Still active
    
    def test_record_error_at_threshold(self):
        """Test record_error method at error threshold."""
        instance = PluginInstance(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            status=PluginStatusDB.ACTIVE,
            error_count=4  # One below threshold
        )
        
        error_message = "Fatal error occurred"
        
        # Record error - should hit threshold
        instance.record_error(error_message)
        
        assert instance.error_count == 5
        assert instance.last_error == error_message
        assert instance.status == PluginStatusDB.ERROR  # Changed to error


class TestPluginEventModel:
    """Test PluginEvent database model."""
    
    def test_plugin_event_creation(self):
        """Test basic PluginEvent model creation."""
        tenant_id = uuid4()
        user_id = uuid4()
        
        event = PluginEvent(
            tenant_id=tenant_id,
            plugin_id="test_plugin",
            instance_id="test_instance",
            event_type="load",
            event_level="INFO",
            event_message="Plugin loaded successfully",
            event_data={"duration_ms": 150},
            user_id=user_id,
            source_ip="192.168.1.100",
            duration_ms=150,
            correlation_id="req_12345"
        )
        
        assert event.tenant_id == tenant_id
        assert event.plugin_id == "test_plugin"
        assert event.instance_id == "test_instance"
        assert event.event_type == "load"
        assert event.event_level == "INFO"
        assert event.event_message == "Plugin loaded successfully"
        assert event.event_data == {"duration_ms": 150}
        assert event.user_id == user_id
        assert event.source_ip == "192.168.1.100"
        assert event.duration_ms == 150
        assert event.correlation_id == "req_12345"
    
    def test_plugin_event_defaults(self):
        """Test PluginEvent model defaults."""
        event = PluginEvent(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            event_type="start",
            event_message="Plugin started"
        )
        
        assert event.event_level == "INFO"  # Default
        assert event.instance_id is None  # Optional
        assert event.event_data is None  # Optional
        assert event.user_id is None  # Optional
    
    def test_plugin_event_repr(self):
        """Test PluginEvent __repr__ method."""
        event = PluginEvent(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            event_type="error",
            event_level="ERROR",
            event_message="Plugin crashed"
        )
        
        repr_str = repr(event)
        
        assert "PluginEvent" in repr_str
        assert "plugin=test_plugin" in repr_str
        assert "type=error" in repr_str
        assert "level=ERROR" in repr_str


class TestPluginMetricsModel:
    """Test PluginMetrics database model."""
    
    def test_plugin_metrics_creation(self):
        """Test basic PluginMetrics model creation."""
        tenant_id = uuid4()
        timestamp = datetime(2023, 12, 15, 10, 30, 45)
        
        metric = PluginMetrics(
            tenant_id=tenant_id,
            plugin_id="test_plugin",
            instance_id="test_instance",
            metric_name="cpu_usage",
            metric_value="45.2",
            metric_type="gauge",
            metric_unit="percent",
            metric_timestamp=timestamp,
            labels={"host": "server1", "env": "production"}
        )
        
        assert metric.tenant_id == tenant_id
        assert metric.plugin_id == "test_plugin"
        assert metric.instance_id == "test_instance"
        assert metric.metric_name == "cpu_usage"
        assert metric.metric_value == "45.2"
        assert metric.metric_type == "gauge"
        assert metric.metric_unit == "percent"
        assert metric.metric_timestamp == timestamp
        assert metric.labels == {"host": "server1", "env": "production"}
    
    def test_plugin_metrics_defaults(self):
        """Test PluginMetrics model defaults."""
        metric = PluginMetrics(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            metric_name="request_count",
            metric_value="100",
            metric_type="counter"
        )
        
        assert metric.instance_id is None  # Optional
        assert metric.metric_unit is None  # Optional
        assert isinstance(metric.metric_timestamp, datetime)  # Default to now
        assert metric.labels is None  # Optional
    
    def test_plugin_metrics_repr(self):
        """Test PluginMetrics __repr__ method."""
        metric = PluginMetrics(
            tenant_id=uuid4(),
            plugin_id="test_plugin",
            metric_name="memory_usage",
            metric_value="512",
            metric_type="gauge"
        )
        
        repr_str = repr(metric)
        
        assert "PluginMetrics" in repr_str
        assert "plugin=test_plugin" in repr_str
        assert "name=memory_usage" in repr_str
        assert "value=512" in repr_str


class TestModelRelationshipsAndConstraints:
    """Test model relationships and database constraints."""
    
    def test_model_table_names(self):
        """Test that models have correct table names."""
        assert PluginRegistry.__tablename__ == "plugin_registry"
        assert PluginConfiguration.__tablename__ == "plugin_configurations"
        assert PluginInstance.__tablename__ == "plugin_instances"
        assert PluginEvent.__tablename__ == "plugin_events"
        assert PluginMetrics.__tablename__ == "plugin_metrics"
    
    def test_model_inheritance(self):
        """Test that models inherit from TenantModel."""
        from dotmac_isp.shared.models import TenantModel
        
        models = [
            PluginRegistry,
            PluginConfiguration,
            PluginInstance,
            PluginEvent,
            PluginMetrics,
        ]
        
        for model_class in models:
            assert issubclass(model_class, TenantModel)
    
    def test_unique_constraints_exist(self):
        """Test that unique constraints are properly defined."""
        # PluginRegistry should have tenant+plugin_id constraint
        registry_constraints = [constraint.name for constraint in PluginRegistry.__table_args__ 
                               if hasattr(constraint, 'name')]
        assert 'uq_tenant_plugin_id' in registry_constraints
        
        # PluginConfiguration should have tenant+plugin_id constraint
        config_constraints = [constraint.name for constraint in PluginConfiguration.__table_args__
                             if hasattr(constraint, 'name')]
        assert 'uq_tenant_plugin_config' in config_constraints
        
        # PluginInstance should have tenant+plugin_id+instance_id constraint
        instance_constraints = [constraint.name for constraint in PluginInstance.__table_args__
                               if hasattr(constraint, 'name')]
        assert 'uq_tenant_plugin_instance' in instance_constraints
    
    def test_indexes_exist(self):
        """Test that important indexes are defined."""
        # Check that indexes are defined in table args
        registry_indexes = PluginRegistry.__table_args__
        config_indexes = PluginConfiguration.__table_args__
        instance_indexes = PluginInstance.__table_args__
        event_indexes = PluginEvent.__table_args__
        metric_indexes = PluginMetrics.__table_args__
        
        # Should have multiple indexes defined
        assert len(registry_indexes) > 1
        assert len(config_indexes) > 1
        assert len(instance_indexes) > 1
        assert len(event_indexes) > 1
        assert len(metric_indexes) > 1