"""
Tests for main NetworkingService class - Unified networking service.
"""

from unittest.mock import Mock, patch

from dotmac.networking import (
    DEFAULT_CONFIG,
    NetworkingService,
    create_networking_service,
    get_default_config,
)


class TestDefaultConfiguration:
    """Test default configuration functionality."""

    def test_default_config_structure(self):
        """Test DEFAULT_CONFIG has expected structure."""
        assert isinstance(DEFAULT_CONFIG, dict)
        assert "ipam" in DEFAULT_CONFIG
        assert "automation" in DEFAULT_CONFIG
        assert "monitoring" in DEFAULT_CONFIG
        assert "radius" in DEFAULT_CONFIG

    def test_default_config_ipam_settings(self):
        """Test default IPAM configuration."""
        ipam_config = DEFAULT_CONFIG["ipam"]

        assert ipam_config["default_subnet_size"] == 24
        assert ipam_config["dhcp_lease_time"] == 86400
        assert ipam_config["dns_ttl"] == 300
        assert ipam_config["enable_ptr_records"] is True
        assert ipam_config["conflict_detection"] is True

    def test_default_config_automation_settings(self):
        """Test default automation configuration."""
        automation_config = DEFAULT_CONFIG["automation"]

        assert automation_config["ssh_timeout"] == 30
        assert automation_config["config_backup_enabled"] is True
        assert automation_config["rollback_on_failure"] is True
        assert automation_config["concurrent_operations"] == 10
        assert automation_config["retry_attempts"] == 3

    def test_default_config_monitoring_settings(self):
        """Test default monitoring configuration."""
        monitoring_config = DEFAULT_CONFIG["monitoring"]

        assert monitoring_config["snmp_timeout"] == 10
        assert monitoring_config["collection_interval"] == 60
        assert monitoring_config["community"] == "public"
        assert "alert_thresholds" in monitoring_config

        thresholds = monitoring_config["alert_thresholds"]
        assert thresholds["cpu_utilization"] == 80
        assert thresholds["memory_utilization"] == 85
        assert thresholds["interface_utilization"] == 90

    def test_default_config_radius_settings(self):
        """Test default RADIUS configuration."""
        radius_config = DEFAULT_CONFIG["radius"]

        assert radius_config["auth_port"] == 1812
        assert radius_config["acct_port"] == 1813
        assert radius_config["coa_port"] == 3799
        assert radius_config["session_timeout"] == 3600
        assert radius_config["enable_accounting"] is True

    def test_get_default_config_returns_copy(self):
        """Test get_default_config returns a copy, not reference."""
        config1 = get_default_config()
        config2 = get_default_config()

        # Should be equal but different objects
        assert config1 == config2
        assert config1 is not config2

        # Modifying one shouldn't affect the other
        config1["ipam"]["default_subnet_size"] = 16
        assert config2["ipam"]["default_subnet_size"] == 24


class TestNetworkingServiceInitialization:
    """Test NetworkingService initialization."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        service = NetworkingService()

        assert service.config == DEFAULT_CONFIG
        assert service._ipam is None
        assert service._automation is None
        assert service._monitoring is None
        assert service._radius is None

    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        custom_config = {
            "ipam": {"default_subnet_size": 16},
            "automation": {"ssh_timeout": 60},
            "custom_section": {"custom_value": "test"}
        }

        service = NetworkingService(config=custom_config)

        assert service.config == custom_config
        assert service.config["ipam"]["default_subnet_size"] == 16
        assert service.config["automation"]["ssh_timeout"] == 60
        assert service.config["custom_section"]["custom_value"] == "test"

    def test_init_none_config_uses_default(self):
        """Test initialization with None config uses default."""
        service = NetworkingService(config=None)

        assert service.config == DEFAULT_CONFIG


class TestNetworkingServiceIPAMProperty:
    """Test IPAM service property."""

    @patch('dotmac.networking.IPAMService')
    def test_ipam_property_first_access(self, mock_ipam_service):
        """Test IPAM property on first access."""
        mock_instance = Mock()
        mock_ipam_service.return_value = mock_instance

        service = NetworkingService()
        ipam = service.ipam

        assert ipam == mock_instance
        mock_ipam_service.assert_called_once_with({})

        # Should cache the instance
        assert service._ipam == mock_instance

    @patch('dotmac.networking.IPAMService')
    def test_ipam_property_cached_access(self, mock_ipam_service):
        """Test IPAM property returns cached instance on subsequent access."""
        mock_instance = Mock()
        mock_ipam_service.return_value = mock_instance

        service = NetworkingService()

        # First access
        ipam1 = service.ipam
        # Second access
        ipam2 = service.ipam

        assert ipam1 == ipam2
        # Should only create instance once
        mock_ipam_service.assert_called_once()

    @patch('dotmac.networking.IPAMService')
    def test_ipam_property_with_config(self, mock_ipam_service):
        """Test IPAM property passes configuration."""
        mock_instance = Mock()
        mock_ipam_service.return_value = mock_instance

        config = {"ipam": {"default_subnet_size": 16, "dhcp_lease_time": 3600}}
        service = NetworkingService(config=config)

        ipam = service.ipam

        mock_ipam_service.assert_called_once_with(config["ipam"])

    @patch('dotmac.networking.IPAMService', None)
    def test_ipam_property_when_unavailable(self):
        """Test IPAM property when service is unavailable."""
        service = NetworkingService()

        ipam = service.ipam

        assert ipam is None


class TestNetworkingServiceAutomationProperty:
    """Test automation service property."""

    @patch('dotmac.networking.DeviceManager')
    def test_automation_property_first_access(self, mock_device_manager):
        """Test automation property on first access."""
        mock_instance = Mock()
        mock_device_manager.return_value = mock_instance

        service = NetworkingService()
        automation = service.automation

        assert automation == mock_instance
        mock_device_manager.assert_called_once_with({})
        assert service._automation == mock_instance

    @patch('dotmac.networking.DeviceManager')
    def test_automation_property_with_config(self, mock_device_manager):
        """Test automation property passes configuration."""
        mock_instance = Mock()
        mock_device_manager.return_value = mock_instance

        config = {"automation": {"ssh_timeout": 60, "retry_attempts": 5}}
        service = NetworkingService(config=config)

        automation = service.automation

        mock_device_manager.assert_called_once_with(config["automation"])

    @patch('dotmac.networking.DeviceManager', None)
    def test_automation_property_when_unavailable(self):
        """Test automation property when service is unavailable."""
        service = NetworkingService()

        automation = service.automation

        assert automation is None


class TestNetworkingServiceMonitoringProperty:
    """Test monitoring service property."""

    @patch('dotmac.networking.NetworkMonitor')
    def test_monitoring_property_first_access(self, mock_network_monitor):
        """Test monitoring property on first access."""
        mock_instance = Mock()
        mock_network_monitor.return_value = mock_instance

        service = NetworkingService()
        monitoring = service.monitoring

        assert monitoring == mock_instance
        mock_network_monitor.assert_called_once_with({})
        assert service._monitoring == mock_instance

    @patch('dotmac.networking.NetworkMonitor')
    def test_monitoring_property_with_config(self, mock_network_monitor):
        """Test monitoring property passes configuration."""
        mock_instance = Mock()
        mock_network_monitor.return_value = mock_instance

        config = {"monitoring": {"snmp_timeout": 20, "community": "private"}}
        service = NetworkingService(config=config)

        monitoring = service.monitoring

        mock_network_monitor.assert_called_once_with(config["monitoring"])

    @patch('dotmac.networking.NetworkMonitor', None)
    def test_monitoring_property_when_unavailable(self):
        """Test monitoring property when service is unavailable."""
        service = NetworkingService()

        monitoring = service.monitoring

        assert monitoring is None


class TestNetworkingServiceRADIUSProperty:
    """Test RADIUS service property."""

    @patch('dotmac.networking.RADIUSServer')
    def test_radius_property_first_access(self, mock_radius_server):
        """Test RADIUS property on first access."""
        mock_instance = Mock()
        mock_radius_server.return_value = mock_instance

        service = NetworkingService()
        radius = service.radius

        assert radius == mock_instance
        mock_radius_server.assert_called_once_with({})
        assert service._radius == mock_instance

    @patch('dotmac.networking.RADIUSServer')
    def test_radius_property_with_config(self, mock_radius_server):
        """Test RADIUS property passes configuration."""
        mock_instance = Mock()
        mock_radius_server.return_value = mock_instance

        config = {"radius": {"auth_port": 1812, "enable_accounting": False}}
        service = NetworkingService(config=config)

        radius = service.radius

        mock_radius_server.assert_called_once_with(config["radius"])

    @patch('dotmac.networking.RADIUSServer', None)
    def test_radius_property_when_unavailable(self):
        """Test RADIUS property when service is unavailable."""
        service = NetworkingService()

        radius = service.radius

        assert radius is None


class TestNetworkingServiceFactoryFunction:
    """Test create_networking_service factory function."""

    def test_create_networking_service_default(self):
        """Test factory function with default configuration."""
        service = create_networking_service()

        assert isinstance(service, NetworkingService)
        assert service.config == DEFAULT_CONFIG

    def test_create_networking_service_custom_config(self):
        """Test factory function with custom configuration."""
        custom_config = {"test": "value"}

        service = create_networking_service(config=custom_config)

        assert isinstance(service, NetworkingService)
        assert service.config == custom_config

    def test_create_networking_service_none_config(self):
        """Test factory function with None configuration."""
        service = create_networking_service(config=None)

        assert isinstance(service, NetworkingService)
        assert service.config == DEFAULT_CONFIG


class TestNetworkingServiceIntegration:
    """Test integration scenarios for NetworkingService."""

    @patch('dotmac.networking.IPAMService')
    @patch('dotmac.networking.DeviceManager')
    @patch('dotmac.networking.NetworkMonitor')
    @patch('dotmac.networking.RADIUSServer')
    def test_all_services_available(self, mock_radius, mock_monitor, mock_device, mock_ipam):
        """Test when all services are available."""
        # Setup mocks
        mock_ipam_instance = Mock()
        mock_device_instance = Mock()
        mock_monitor_instance = Mock()
        mock_radius_instance = Mock()

        mock_ipam.return_value = mock_ipam_instance
        mock_device.return_value = mock_device_instance
        mock_monitor.return_value = mock_monitor_instance
        mock_radius.return_value = mock_radius_instance

        service = NetworkingService()

        # Access all services
        ipam = service.ipam
        automation = service.automation
        monitoring = service.monitoring
        radius = service.radius

        # Verify all services are available
        assert ipam == mock_ipam_instance
        assert automation == mock_device_instance
        assert monitoring == mock_monitor_instance
        assert radius == mock_radius_instance

        # Verify each service was initialized with correct config
        mock_ipam.assert_called_once_with(DEFAULT_CONFIG["ipam"])
        mock_device.assert_called_once_with(DEFAULT_CONFIG["automation"])
        mock_monitor.assert_called_once_with(DEFAULT_CONFIG["monitoring"])
        mock_radius.assert_called_once_with(DEFAULT_CONFIG["radius"])

    @patch('dotmac.networking.IPAMService', None)
    @patch('dotmac.networking.DeviceManager', None)
    @patch('dotmac.networking.NetworkMonitor', None)
    @patch('dotmac.networking.RADIUSServer', None)
    def test_all_services_unavailable(self):
        """Test when all services are unavailable."""
        service = NetworkingService()

        # Access all services
        ipam = service.ipam
        automation = service.automation
        monitoring = service.monitoring
        radius = service.radius

        # All should be None
        assert ipam is None
        assert automation is None
        assert monitoring is None
        assert radius is None

    @patch('dotmac.networking.IPAMService')
    def test_partial_service_availability(self, mock_ipam):
        """Test when only some services are available."""
        mock_ipam_instance = Mock()
        mock_ipam.return_value = mock_ipam_instance

        # Other services are unavailable (default behavior when not mocked)
        service = NetworkingService()

        ipam = service.ipam
        automation = service.automation

        # Only IPAM should be available
        assert ipam == mock_ipam_instance
        assert automation is None

    def test_service_property_caching(self):
        """Test that service properties are properly cached."""
        with patch('dotmac.networking.IPAMService') as mock_ipam:
            mock_instance = Mock()
            mock_ipam.return_value = mock_instance

            service = NetworkingService()

            # Access IPAM multiple times
            ipam1 = service.ipam
            ipam2 = service.ipam
            ipam3 = service.ipam

            # Should be same instance
            assert ipam1 is ipam2 is ipam3
            # Should only create once
            mock_ipam.assert_called_once()

    def test_config_propagation_to_services(self):
        """Test configuration is properly propagated to services."""
        custom_config = {
            "ipam": {"default_subnet_size": 16, "conflict_detection": False},
            "automation": {"ssh_timeout": 120, "retry_attempts": 2},
            "monitoring": {"snmp_timeout": 5, "community": "private"},
            "radius": {"auth_port": 1645, "enable_accounting": False},
        }

        with patch('dotmac.networking.IPAMService') as mock_ipam, \
             patch('dotmac.networking.DeviceManager') as mock_device, \
             patch('dotmac.networking.NetworkMonitor') as mock_monitor, \
             patch('dotmac.networking.RADIUSServer') as mock_radius:

            service = NetworkingService(config=custom_config)

            # Access all services to trigger initialization
            _ = service.ipam
            _ = service.automation
            _ = service.monitoring
            _ = service.radius

            # Verify each service received correct config section
            mock_ipam.assert_called_once_with(custom_config["ipam"])
            mock_device.assert_called_once_with(custom_config["automation"])
            mock_monitor.assert_called_once_with(custom_config["monitoring"])
            mock_radius.assert_called_once_with(custom_config["radius"])

    def test_missing_config_sections(self):
        """Test behavior when config sections are missing."""
        incomplete_config = {
            "ipam": {"default_subnet_size": 16},
            # Missing automation, monitoring, radius sections
        }

        with patch('dotmac.networking.IPAMService') as mock_ipam, \
             patch('dotmac.networking.DeviceManager') as mock_device:

            service = NetworkingService(config=incomplete_config)

            # Access services
            _ = service.ipam
            _ = service.automation

            # IPAM should get its config
            mock_ipam.assert_called_once_with(incomplete_config["ipam"])
            # Automation should get empty dict for missing config
            mock_device.assert_called_once_with({})
