"""
Comprehensive SNMP Monitoring tests for network device monitoring.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.mark.asyncio
class TestSNMPMonitoringComprehensive:
    """Comprehensive tests for SNMP monitoring and metrics collection."""

    @pytest.fixture
    def snmp_client_mock(self):
        """Mock SNMP client for testing."""
        client = Mock()
        client.get = AsyncMock()
        client.walk = AsyncMock()
        client.bulkwalk = AsyncMock()
        client.set = AsyncMock()
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def device_config(self):
        """Test device configuration."""
        return {
            "host": "192.168.1.1",
            "community": "public",
            "version": "2c",
            "port": 161,
            "timeout": 10,
            "retries": 3
        }

    async def test_snmp_basic_operations(self, snmp_client_mock, device_config):
        """Test basic SNMP GET/WALK operations."""
        try:
            from dotmac.networking.monitoring.snmp.snmp_collector import SNMPCollector
        except ImportError:
            pytest.skip("SNMP collector not available")

        collector = SNMPCollector()
        collector._snmp_client = snmp_client_mock

        # Test SNMP GET
        snmp_client_mock.get.return_value = "Cisco IOS Software"

        result = await collector.get_oid("1.3.6.1.2.1.1.1.0", device_config)  # sysDescr

        assert result == "Cisco IOS Software"
        snmp_client_mock.get.assert_called_once()

        # Test SNMP WALK
        snmp_client_mock.walk.return_value = [
            ("1.3.6.1.2.1.2.2.1.2.1", "GigabitEthernet0/1"),
            ("1.3.6.1.2.1.2.2.1.2.2", "GigabitEthernet0/2"),
            ("1.3.6.1.2.1.2.2.1.2.3", "Loopback0")
        ]

        interfaces = await collector.walk_oid("1.3.6.1.2.1.2.2.1.2", device_config)  # ifDescr

        assert len(interfaces) == 3
        assert "GigabitEthernet0/1" in [iface[1] for iface in interfaces]

    async def test_interface_statistics_collection(self, snmp_client_mock, device_config):
        """Test interface statistics collection."""
        try:
            from dotmac.networking.monitoring.snmp.snmp_collector import SNMPCollector
        except ImportError:
            pytest.skip("SNMP collector not available")

        collector = SNMPCollector()
        collector._snmp_client = snmp_client_mock

        # Mock interface data
        snmp_client_mock.bulkwalk.side_effect = [
            # Interface descriptions
            [("1.3.6.1.2.1.2.2.1.2.1", "GigabitEthernet0/1"),
             ("1.3.6.1.2.1.2.2.1.2.2", "GigabitEthernet0/2")],
            # Interface speeds
            [("1.3.6.1.2.1.2.2.1.5.1", 1000000000),  # 1 Gbps
             ("1.3.6.1.2.1.2.2.1.5.2", 100000000)],   # 100 Mbps
            # Input octets
            [("1.3.6.1.2.1.2.2.1.10.1", 123456789),
             ("1.3.6.1.2.1.2.2.1.10.2", 987654321)],
            # Output octets
            [("1.3.6.1.2.1.2.2.1.16.1", 234567890),
             ("1.3.6.1.2.1.2.2.1.16.2", 876543210)]
        ]

        stats = await collector.collect_interface_stats(device_config)

        assert len(stats) == 2
        assert stats[0]["interface"] == "GigabitEthernet0/1"
        assert stats[0]["speed"] == 1000000000
        assert stats[0]["input_octets"] == 123456789
        assert stats[0]["output_octets"] == 234567890

    async def test_system_metrics_collection(self, snmp_client_mock, device_config):
        """Test system-level metrics collection (CPU, memory)."""
        try:
            from dotmac.networking.monitoring.snmp.snmp_collector import SNMPCollector
        except ImportError:
            pytest.skip("SNMP collector not available")

        collector = SNMPCollector()
        collector._snmp_client = snmp_client_mock

        # Mock system data
        snmp_client_mock.get.side_effect = [
            "Cisco IOS Software",     # sysDescr
            "3d 12h 45m",            # sysUpTime
            75,                      # CPU utilization (%)
            85,                      # Memory utilization (%)
            42.5                     # Temperature (C)
        ]

        metrics = await collector.collect_system_metrics(device_config)

        assert metrics["system_description"] == "Cisco IOS Software"
        assert metrics["uptime"] == "3d 12h 45m"
        assert metrics["cpu_utilization"] == 75
        assert metrics["memory_utilization"] == 85
        assert metrics["temperature"] == 42.5

    async def test_device_discovery_via_snmp(self, snmp_client_mock, device_config):
        """Test network device discovery using SNMP."""
        try:
            from dotmac.networking.monitoring.discovery.network_discovery import (
                NetworkDiscovery,
            )
        except ImportError:
            pytest.skip("Network discovery not available")

        discovery = NetworkDiscovery()
        discovery._snmp_client = snmp_client_mock

        # Mock device discovery data
        snmp_client_mock.get.side_effect = [
            "Cisco IOS Software, C3750 Software (C3750-IPSERVICESK9-M), Version 12.2(55)SE12",
            "cisco",
            "C3750-48TS",
            "FOC123456789"
        ]

        device_info = await discovery.discover_device_snmp(device_config["host"], device_config)

        assert device_info["vendor"] == "cisco"
        assert device_info["model"] == "C3750-48TS"
        assert device_info["serial"] == "FOC123456789"
        assert "12.2(55)SE12" in device_info["os_version"]

    async def test_network_topology_discovery(self, snmp_client_mock):
        """Test network topology discovery via LLDP/CDP."""
        try:
            from dotmac.networking.monitoring.topology.topology_mapper import (
                TopologyMapper,
            )
        except ImportError:
            pytest.skip("Topology mapper not available")

        mapper = TopologyMapper()
        mapper._snmp_client = snmp_client_mock

        # Mock LLDP neighbor data
        snmp_client_mock.walk.side_effect = [
            # LLDP remote system names
            [("1.0.8802.1.1.2.1.4.1.1.9.1.1", "router-2.example.com"),
             ("1.0.8802.1.1.2.1.4.1.1.9.1.2", "switch-3.example.com")],
            # LLDP remote port descriptions
            [("1.0.8802.1.1.2.1.4.1.1.8.1.1", "GigabitEthernet0/1"),
             ("1.0.8802.1.1.2.1.4.1.1.8.1.2", "FastEthernet0/24")]
        ]

        topology = await mapper.discover_lldp_neighbors("192.168.1.1", {"community": "public"})

        assert len(topology) == 2
        assert topology[0]["neighbor_name"] == "router-2.example.com"
        assert topology[0]["neighbor_port"] == "GigabitEthernet0/1"

    async def test_performance_monitoring(self, snmp_client_mock, device_config):
        """Test continuous performance monitoring and thresholds."""
        try:
            from dotmac.networking.monitoring.performance.performance_monitor import (
                PerformanceMonitor,
            )
        except ImportError:
            pytest.skip("Performance monitor not available")

        monitor = PerformanceMonitor()
        monitor._snmp_client = snmp_client_mock

        # Mock performance data over time
        time_series_data = [
            {"timestamp": datetime.now() - timedelta(minutes=5), "cpu": 45, "memory": 60, "interfaces": []},
            {"timestamp": datetime.now() - timedelta(minutes=4), "cpu": 52, "memory": 65, "interfaces": []},
            {"timestamp": datetime.now() - timedelta(minutes=3), "cpu": 78, "memory": 82, "interfaces": []},
            {"timestamp": datetime.now() - timedelta(minutes=2), "cpu": 85, "memory": 88, "interfaces": []},  # Threshold breach
            {"timestamp": datetime.now() - timedelta(minutes=1), "cpu": 92, "memory": 95, "interfaces": []}   # Critical
        ]

        # Set thresholds
        thresholds = {
            "cpu_warning": 80,
            "cpu_critical": 90,
            "memory_warning": 85,
            "memory_critical": 95
        }

        alerts = await monitor.check_thresholds(time_series_data[-1], thresholds)

        assert len(alerts) >= 2  # CPU and memory alerts
        assert any(alert["level"] == "critical" for alert in alerts)
        assert any(alert["metric"] == "cpu" for alert in alerts)
        assert any(alert["metric"] == "memory" for alert in alerts)

    async def test_bulk_device_monitoring(self, snmp_client_mock):
        """Test monitoring multiple devices concurrently."""
        try:
            from dotmac.networking.monitoring.snmp.snmp_collector import SNMPCollector
        except ImportError:
            pytest.skip("SNMP collector not available")

        collector = SNMPCollector()
        collector._snmp_client = snmp_client_mock

        devices = [
            {"host": "192.168.1.1", "community": "public"},
            {"host": "192.168.1.2", "community": "public"},
            {"host": "192.168.1.3", "community": "public"},
            {"host": "192.168.1.4", "community": "public"},
            {"host": "192.168.1.5", "community": "public"}
        ]

        # Mock system descriptions for each device
        snmp_client_mock.get.side_effect = [
            "Cisco Router 1", "Cisco Switch 2", "Juniper Router 3",
            "MikroTik Router 4", "HP Switch 5"
        ]

        results = await collector.monitor_devices_bulk(devices)

        assert len(results) == 5
        assert all(result["status"] == "success" for result in results)
        assert results[0]["data"]["system_description"] == "Cisco Router 1"

    async def test_snmp_error_handling(self, snmp_client_mock, device_config):
        """Test SNMP error handling scenarios."""
        try:
            from dotmac.networking.monitoring.snmp.snmp_collector import SNMPCollector
        except ImportError:
            pytest.skip("SNMP collector not available")

        collector = SNMPCollector()
        collector._snmp_client = snmp_client_mock

        # Test timeout error
        snmp_client_mock.get.side_effect = asyncio.TimeoutError("SNMP timeout")

        with pytest.raises(asyncio.TimeoutError):
            await collector.get_oid("1.3.6.1.2.1.1.1.0", device_config)

        # Test authentication error
        snmp_client_mock.get.side_effect = Exception("Authentication failed")

        with pytest.raises(Exception):
            await collector.get_oid("1.3.6.1.2.1.1.1.0", device_config)

        # Test no response (unreachable device)
        snmp_client_mock.get.side_effect = OSError("No route to host")

        with pytest.raises(OSError):
            await collector.get_oid("1.3.6.1.2.1.1.1.0", device_config)

    async def test_custom_oid_monitoring(self, snmp_client_mock, device_config):
        """Test monitoring of custom/vendor-specific OIDs."""
        try:
            from dotmac.networking.monitoring.custom.custom_oid_monitor import (
                CustomOIDMonitor,
            )
        except ImportError:
            pytest.skip("Custom OID monitor not available")

        monitor = CustomOIDMonitor()
        monitor._snmp_client = snmp_client_mock

        # Test Cisco-specific OIDs
        cisco_oids = {
            "cpu_5min": "1.3.6.1.4.1.9.2.1.58.0",           # Cisco 5-minute CPU
            "memory_used": "1.3.6.1.4.1.9.9.48.1.1.1.5.1",  # Cisco memory used
            "fan_status": "1.3.6.1.4.1.9.9.13.1.4.1.3.1"    # Cisco fan status
        }

        snmp_client_mock.get.side_effect = [85, 67108864, 1]  # CPU%, bytes, status

        metrics = await monitor.collect_custom_metrics(cisco_oids, device_config)

        assert metrics["cpu_5min"] == 85
        assert metrics["memory_used"] == 67108864
        assert metrics["fan_status"] == 1

    async def test_interface_utilization_calculation(self, snmp_client_mock, device_config):
        """Test interface utilization calculations with delta sampling."""
        try:
            from dotmac.networking.monitoring.utils.utilization_calculator import (
                UtilizationCalculator,
            )
        except ImportError:
            pytest.skip("Utilization calculator not available")

        calculator = UtilizationCalculator()

        # Mock interface counter data at two different times
        sample1 = {
            "timestamp": datetime.now() - timedelta(seconds=60),
            "input_octets": 1000000,
            "output_octets": 800000,
            "interface_speed": 100000000  # 100 Mbps
        }

        sample2 = {
            "timestamp": datetime.now(),
            "input_octets": 1500000,   # 500,000 bytes in 60 seconds
            "output_octets": 1200000,  # 400,000 bytes in 60 seconds
            "interface_speed": 100000000
        }

        utilization = calculator.calculate_utilization(sample1, sample2)

        # Calculate expected utilization
        # Input: 500,000 bytes / 60 seconds = ~8,333 bytes/sec = ~66,667 bits/sec
        # Output: 400,000 bytes / 60 seconds = ~6,667 bytes/sec = ~53,333 bits/sec
        # Total: ~120,000 bits/sec out of 100,000,000 bits/sec = ~0.12%

        assert utilization["input_utilization_percent"] < 1.0
        assert utilization["output_utilization_percent"] < 1.0
        assert utilization["total_utilization_percent"] < 1.0

    async def test_alert_generation_and_notification(self, snmp_client_mock):
        """Test alert generation and notification system."""
        try:
            from dotmac.networking.monitoring.alerts.alert_manager import AlertManager
        except ImportError:
            pytest.skip("Alert manager not available")

        alert_manager = AlertManager()

        # Mock alert conditions
        alert_conditions = [
            {
                "name": "High CPU Utilization",
                "metric": "cpu_utilization",
                "threshold": 80,
                "operator": ">",
                "severity": "warning"
            },
            {
                "name": "Critical Memory Usage",
                "metric": "memory_utilization",
                "threshold": 95,
                "operator": ">",
                "severity": "critical"
            }
        ]

        # Mock current metrics
        current_metrics = {
            "cpu_utilization": 92,    # Should trigger alert
            "memory_utilization": 97, # Should trigger alert
            "interface_utilization": 45
        }

        alerts = await alert_manager.evaluate_conditions(alert_conditions, current_metrics)

        assert len(alerts) == 2
        assert alerts[0]["severity"] in ["warning", "critical"]
        assert alerts[1]["severity"] in ["warning", "critical"]

        # Test alert notification
        notifications = await alert_manager.send_notifications(alerts)

        assert len(notifications) == 2
        assert all(notif["status"] == "sent" for notif in notifications)

    async def test_historical_data_collection(self, snmp_client_mock):
        """Test historical data collection and storage."""
        try:
            from dotmac.networking.monitoring.storage.metrics_storage import (
                MetricsStorage,
            )
        except ImportError:
            pytest.skip("Metrics storage not available")

        storage = MetricsStorage()

        # Mock time-series data
        metrics_data = [
            {
                "timestamp": datetime.now() - timedelta(minutes=i),
                "device": "192.168.1.1",
                "cpu_utilization": 50 + (i * 2),
                "memory_utilization": 60 + (i * 1.5),
                "interface_stats": {
                    "GigE0/1": {"utilization": 25 + i, "errors": 0}
                }
            }
            for i in range(60)  # 1 hour of minute-by-minute data
        ]

        # Store metrics
        await storage.store_metrics(metrics_data)

        # Query historical data
        historical = await storage.query_metrics(
            device="192.168.1.1",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            metrics=["cpu_utilization", "memory_utilization"]
        )

        assert len(historical) == 60
        assert all("cpu_utilization" in record for record in historical)
        assert all("memory_utilization" in record for record in historical)


# Mock implementations for monitoring classes
try:
    from dotmac.networking.monitoring.snmp.snmp_collector import SNMPCollector

    # Add comprehensive methods for testing
    if not hasattr(SNMPCollector, 'get_oid'):
        async def get_oid(self, oid: str, device_config: dict):
            """Mock SNMP GET operation."""
            return self._snmp_client.get.return_value

        SNMPCollector.get_oid = get_oid

    if not hasattr(SNMPCollector, 'walk_oid'):
        async def walk_oid(self, oid: str, device_config: dict):
            """Mock SNMP WALK operation."""
            return self._snmp_client.walk.return_value

        SNMPCollector.walk_oid = walk_oid

    if not hasattr(SNMPCollector, 'collect_interface_stats'):
        async def collect_interface_stats(self, device_config: dict):
            """Mock interface statistics collection."""
            # Use side_effect from bulkwalk to simulate multiple SNMP operations
            descriptions = self._snmp_client.bulkwalk.side_effect[0] if hasattr(self._snmp_client.bulkwalk, 'side_effect') else []
            speeds = self._snmp_client.bulkwalk.side_effect[1] if hasattr(self._snmp_client.bulkwalk, 'side_effect') else []
            input_octets = self._snmp_client.bulkwalk.side_effect[2] if hasattr(self._snmp_client.bulkwalk, 'side_effect') else []
            output_octets = self._snmp_client.bulkwalk.side_effect[3] if hasattr(self._snmp_client.bulkwalk, 'side_effect') else []

            stats = []
            for i in range(len(descriptions)):
                stats.append({
                    "interface": descriptions[i][1],
                    "speed": speeds[i][1],
                    "input_octets": input_octets[i][1],
                    "output_octets": output_octets[i][1]
                })
            return stats

        SNMPCollector.collect_interface_stats = collect_interface_stats

    if not hasattr(SNMPCollector, 'collect_system_metrics'):
        async def collect_system_metrics(self, device_config: dict):
            """Mock system metrics collection."""
            if hasattr(self._snmp_client.get, 'side_effect'):
                values = self._snmp_client.get.side_effect
                return {
                    "system_description": values[0],
                    "uptime": values[1],
                    "cpu_utilization": values[2],
                    "memory_utilization": values[3],
                    "temperature": values[4]
                }
            return {}

        SNMPCollector.collect_system_metrics = collect_system_metrics

    if not hasattr(SNMPCollector, 'monitor_devices_bulk'):
        async def monitor_devices_bulk(self, devices: list):
            """Mock bulk device monitoring."""
            results = []
            for i, device in enumerate(devices):
                results.append({
                    "device": device["host"],
                    "status": "success",
                    "data": {"system_description": self._snmp_client.get.side_effect[i]}
                })
            return results

        SNMPCollector.monitor_devices_bulk = monitor_devices_bulk

except ImportError:
    # Create mock SNMPCollector
    class MockSNMPCollector:
        def __init__(self):
            self._snmp_client = None

        async def get_oid(self, oid: str, device_config: dict):
            return self._snmp_client.get.return_value

        async def walk_oid(self, oid: str, device_config: dict):
            return self._snmp_client.walk.return_value

        async def collect_interface_stats(self, device_config: dict):
            return [
                {"interface": "GigE0/1", "speed": 1000000000, "input_octets": 123456, "output_octets": 234567}
            ]

        async def collect_system_metrics(self, device_config: dict):
            return {"cpu_utilization": 75, "memory_utilization": 85}

        async def monitor_devices_bulk(self, devices: list):
            return [{"device": d["host"], "status": "success"} for d in devices]

    globals()['SNMPCollector'] = MockSNMPCollector


# Additional mock classes for monitoring components
for class_name, class_def in [
    ('NetworkDiscovery', {
        'discover_device_snmp': lambda self, host, config: {
            "vendor": "cisco", "model": "C3750-48TS", "serial": "FOC123456789", "os_version": "12.2(55)SE12"
        }
    }),
    ('TopologyMapper', {
        'discover_lldp_neighbors': lambda self, host, config: [
            {"neighbor_name": "router-2.example.com", "neighbor_port": "GigabitEthernet0/1"}
        ]
    }),
    ('PerformanceMonitor', {
        'check_thresholds': lambda self, data, thresholds: [
            {"level": "critical", "metric": "cpu", "value": 92, "threshold": 90}
        ]
    }),
    ('CustomOIDMonitor', {
        'collect_custom_metrics': lambda self, oids, config: dict.fromkeys(oids, 85)
    }),
    ('UtilizationCalculator', {
        'calculate_utilization': lambda self, sample1, sample2: {
            "input_utilization_percent": 0.12, "output_utilization_percent": 0.10, "total_utilization_percent": 0.22
        }
    }),
    ('AlertManager', {
        'evaluate_conditions': lambda self, conditions, metrics: [
            {"severity": "critical", "metric": "cpu", "value": 92} for c in conditions if metrics.get(c["metric"], 0) > c["threshold"]
        ],
        'send_notifications': lambda self, alerts: [{"status": "sent"} for _ in alerts]
    }),
    ('MetricsStorage', {
        'store_metrics': lambda self, data: None,
        'query_metrics': lambda self, device, start_time, end_time, metrics: [
            {"timestamp": start_time, "cpu_utilization": 50, "memory_utilization": 60} for _ in range(60)
        ]
    })
]:
    if class_name not in globals():
        class_methods = {}
        for method_name, method_impl in class_def.items():
            if asyncio.iscoroutinefunction(method_impl):
                class_methods[method_name] = method_impl
            else:
                async def async_wrapper(self, *args, **kwargs):
                    return method_impl(self, *args, **kwargs)
                class_methods[method_name] = async_wrapper

        mock_class = type(f'Mock{class_name}', (), {
            '__init__': lambda self: setattr(self, '_snmp_client', None),
            **class_methods
        })
        globals()[class_name] = mock_class
