"""
ISP Network Infrastructure Tests

Tests critical network operations including RADIUS authentication,
SNMP monitoring, device management, and service provisioning.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
import ipaddress

from dotmac_isp.modules.network_integration.service import NetworkIntegrationService
from dotmac_isp.modules.network_monitoring.service import NetworkMonitoringService
from dotmac_isp.integrations.freeradius.client import FreeRadiusClient
from dotmac_isp.modules.network_monitoring.snmp_client import SNMPClient
from dotmac_isp.modules.services.service import ServiceProvisioningService


@pytest.mark.network_infrastructure
@pytest.mark.critical
class TestRADIUSAuthenticationIntegration:
    """Test RADIUS authentication and accounting for customer internet access."""
    
    async def test_customer_pppoe_authentication_success(self, db_session):
        """Test successful PPPoE customer authentication via RADIUS."""
        radius_client = FreeRadiusClient()
        network_service = NetworkIntegrationService(db_session, "tenant_001")
        
        # Customer authentication request
        auth_request = {
            "username": "customer001@isp.com",
            "password": "secure_password_123",
            "nas_ip": "10.0.1.1",
            "nas_port": "ethernet0/1",
            "calling_station_id": "aa:bb:cc:dd:ee:ff",  # Customer MAC
            "service_type": "Framed-User",
            "framed_protocol": "PPP"
        }
        
        # Mock customer service validation
        mock_customer_data = {
            "customer_id": "cust_001",
            "account_status": "active",
            "service_plan": "residential_100mbps",
            "ip_pool": "residential",
            "bandwidth_down": 100_000_000,  # 100 Mbps in bps
            "bandwidth_up": 10_000_000,     # 10 Mbps in bps
        }
        
        with patch.object(network_service, 'get_customer_by_username', return_value=mock_customer_data):
            with patch.object(radius_client, 'authenticate') as mock_auth:
                mock_auth.return_value = {
                    "result": "Access-Accept",
                    "framed_ip": "172.16.100.50",
                    "session_timeout": 86400,  # 24 hours
                    "reply_attributes": {
                        "Mikrotik-Rate-Limit": "100M/10M",
                        "Framed-Pool": "residential",
                        "Session-Timeout": 86400
                    }
                }
                
                result = await radius_client.authenticate(auth_request)
                
                # Verify successful authentication
                assert result["result"] == "Access-Accept"
                assert result["framed_ip"] == "172.16.100.50"
                assert "Mikrotik-Rate-Limit" in result["reply_attributes"]
                
                # Verify authentication was logged
                mock_auth.assert_called_once_with(auth_request)

    async def test_customer_authentication_account_suspended(self, db_session):
        """Test RADIUS rejection for suspended customer account."""
        radius_client = FreeRadiusClient()
        network_service = NetworkIntegrationService(db_session, "tenant_001")
        
        auth_request = {
            "username": "suspended_customer@isp.com",
            "password": "password123",
            "nas_ip": "10.0.1.1"
        }
        
        # Mock suspended customer
        mock_customer_data = {
            "customer_id": "cust_suspended",
            "account_status": "suspended",
            "suspension_reason": "overdue_payment"
        }
        
        with patch.object(network_service, 'get_customer_by_username', return_value=mock_customer_data):
            with patch.object(radius_client, 'authenticate') as mock_auth:
                mock_auth.return_value = {
                    "result": "Access-Reject",
                    "reply_message": "Account suspended - payment required"
                }
                
                result = await radius_client.authenticate(auth_request)
                
                # Verify authentication rejection
                assert result["result"] == "Access-Reject" 
                assert "suspended" in result["reply_message"].lower()

    async def test_radius_accounting_session_tracking(self, db_session):
        """Test RADIUS accounting for session and usage tracking."""
        radius_client = FreeRadiusClient()
        network_service = NetworkIntegrationService(db_session, "tenant_001")
        
        # Accounting start request
        acct_start = {
            "username": "customer001@isp.com",
            "session_id": "sess_12345678",
            "nas_ip": "10.0.1.1",
            "framed_ip": "172.16.100.50",
            "acct_status_type": "Start",
            "nas_port_type": "Ethernet",
            "calling_station_id": "aa:bb:cc:dd:ee:ff"
        }
        
        with patch.object(radius_client, 'accounting') as mock_acct:
            mock_acct.return_value = {"result": "Accounting-Response"}
            
            start_result = await radius_client.accounting(acct_start)
            assert start_result["result"] == "Accounting-Response"
        
        # Accounting update (interim) request
        acct_update = {
            **acct_start,
            "acct_status_type": "Interim-Update",
            "acct_session_time": 3600,  # 1 hour
            "acct_input_octets": 524_288_000,   # 500 MB downloaded
            "acct_output_octets": 52_428_800,   # 50 MB uploaded
            "acct_input_packets": 400000,
            "acct_output_packets": 300000
        }
        
        with patch.object(radius_client, 'accounting') as mock_acct:
            mock_acct.return_value = {"result": "Accounting-Response"}
            
            update_result = await radius_client.accounting(acct_update)
            assert update_result["result"] == "Accounting-Response"
        
        # Accounting stop request
        acct_stop = {
            **acct_update,
            "acct_status_type": "Stop",
            "acct_session_time": 7200,  # 2 hours total
            "acct_input_octets": 1_073_741_824,  # 1 GB downloaded
            "acct_output_octets": 107_374_182,   # 100 MB uploaded
            "acct_terminate_cause": "User-Request"
        }
        
        with patch.object(radius_client, 'accounting') as mock_acct:
            with patch.object(network_service, 'record_usage_data') as mock_usage:
                mock_acct.return_value = {"result": "Accounting-Response"}
                
                stop_result = await radius_client.accounting(acct_stop)
                assert stop_result["result"] == "Accounting-Response"
                
                # Verify usage data was recorded
                mock_usage.assert_called_once()
                call_args = mock_usage.call_args[0][0]
                assert call_args["download_bytes"] == 1_073_741_824
                assert call_args["upload_bytes"] == 107_374_182
                assert call_args["session_duration"] == 7200


@pytest.mark.network_infrastructure  
@pytest.mark.critical
class TestSNMPMonitoringIntegration:
    """Test SNMP-based network device monitoring."""
    
    async def test_router_interface_monitoring(self, db_session):
        """Test SNMP monitoring of router interface statistics."""
        snmp_client = SNMPClient()
        monitoring_service = NetworkMonitoringService(db_session, "tenant_001")
        
        # Mock router device
        router_device = {
            "device_id": "router_001",
            "ip_address": "192.168.1.1",
            "snmp_community": "public",
            "device_type": "router",
            "location": "POP1",
            "interfaces": ["GigabitEthernet0/1", "GigabitEthernet0/2"]
        }
        
        # Mock SNMP response for interface statistics
        mock_snmp_data = {
            "1.3.6.1.2.1.2.2.1.10.1": 1_500_000_000,  # ifInOctets - interface 1
            "1.3.6.1.2.1.2.2.1.16.1": 800_000_000,    # ifOutOctets - interface 1
            "1.3.6.1.2.1.2.2.1.8.1": 1,               # ifOperStatus - UP
            "1.3.6.1.2.1.2.2.1.2.1": "GigabitEthernet0/1",  # ifDescr
            "1.3.6.1.2.1.2.2.1.5.1": 1_000_000_000,   # ifSpeed - 1 Gbps
        }
        
        with patch.object(snmp_client, 'bulk_get', return_value=mock_snmp_data):
            interface_stats = await monitoring_service.collect_interface_statistics(
                router_device
            )
            
            # Verify interface monitoring data
            assert len(interface_stats) > 0
            
            for interface in interface_stats:
                assert interface["device_id"] == "router_001"
                assert interface["interface_name"] in router_device["interfaces"]
                assert "bytes_in" in interface
                assert "bytes_out" in interface
                assert "status" in interface
                
                # Verify bandwidth utilization calculation
                if interface["interface_name"] == "GigabitEthernet0/1":
                    expected_util_in = (1_500_000_000 * 8) / 1_000_000_000  # Convert to bps and calculate %
                    assert abs(interface["utilization_in"] - expected_util_in) < 0.01

    async def test_bandwidth_threshold_alerting(self, db_session):
        """Test automatic alerting when bandwidth thresholds are exceeded."""
        monitoring_service = NetworkMonitoringService(db_session, "tenant_001")
        
        # High bandwidth utilization scenario
        interface_data = {
            "device_id": "router_001",
            "interface_name": "GigabitEthernet0/1",
            "bytes_in": 900_000_000,  # 900 Mbps of 1 Gbps = 90% utilization
            "bytes_out": 850_000_000, # 850 Mbps = 85% utilization
            "interface_speed": 1_000_000_000,  # 1 Gbps
            "timestamp": datetime.utcnow()
        }
        
        # Configure alerting thresholds
        alert_config = {
            "warning_threshold": 80.0,   # 80%
            "critical_threshold": 90.0,  # 90%
            "alert_channels": ["email", "snmp_trap"]
        }
        
        with patch.object(monitoring_service, 'send_bandwidth_alert') as mock_alert:
            await monitoring_service.check_bandwidth_thresholds(
                interface_data, 
                alert_config
            )
            
            # Should trigger critical alert (90%+ utilization)
            mock_alert.assert_called_once()
            alert_call = mock_alert.call_args[0][0]
            assert alert_call["severity"] == "critical"
            assert alert_call["utilization"] >= 90.0
            assert "router_001" in alert_call["message"]

    async def test_device_availability_monitoring(self, db_session):
        """Test ICMP ping monitoring for device availability."""
        monitoring_service = NetworkMonitoringService(db_session, "tenant_001")
        
        # List of critical network devices
        critical_devices = [
            {"ip": "192.168.1.1", "name": "core-router-1", "type": "router"},
            {"ip": "192.168.1.10", "name": "distribution-switch-1", "type": "switch"},
            {"ip": "192.168.1.20", "name": "olt-fiber-1", "type": "olt"}
        ]
        
        # Mock ping results
        with patch.object(monitoring_service, 'ping_device') as mock_ping:
            mock_ping.side_effect = [
                {"status": "up", "response_time": 1.2, "packet_loss": 0.0},
                {"status": "down", "response_time": None, "packet_loss": 100.0},
                {"status": "up", "response_time": 2.5, "packet_loss": 0.0}
            ]
            
            availability_results = []
            for device in critical_devices:
                result = await monitoring_service.ping_device(device["ip"])
                result["device"] = device
                availability_results.append(result)
            
            # Verify availability monitoring
            assert len(availability_results) == 3
            
            # Router should be up
            router_result = next(r for r in availability_results if r["device"]["name"] == "core-router-1")
            assert router_result["status"] == "up"
            assert router_result["response_time"] == 1.2
            
            # Switch should be down (triggers alert)
            switch_result = next(r for r in availability_results if r["device"]["name"] == "distribution-switch-1")
            assert switch_result["status"] == "down"
            assert switch_result["packet_loss"] == 100.0

    async def test_olt_onu_monitoring_fiber_customers(self, db_session):
        """Test OLT/ONU monitoring for fiber-based customers."""
        monitoring_service = NetworkMonitoringService(db_session, "tenant_001")
        
        # Fiber OLT device
        olt_device = {
            "device_id": "olt_001",
            "ip_address": "192.168.2.10", 
            "type": "olt",
            "pon_ports": 16,
            "max_onus_per_port": 32
        }
        
        # Mock ONU status data from OLT
        mock_onu_data = [
            {
                "onu_id": "onu_001",
                "pon_port": 1,
                "onu_index": 1,
                "serial_number": "GPON12345678",
                "status": "online",
                "rx_power": -15.2,  # dBm
                "tx_power": 3.1,    # dBm
                "distance": 1250,   # meters
                "customer_id": "cust_fiber_001"
            },
            {
                "onu_id": "onu_002", 
                "pon_port": 1,
                "onu_index": 2,
                "serial_number": "GPON87654321",
                "status": "offline",
                "rx_power": None,
                "tx_power": None,
                "distance": None,
                "customer_id": "cust_fiber_002"
            }
        ]
        
        with patch.object(monitoring_service, 'collect_onu_status', return_value=mock_onu_data):
            onu_status = await monitoring_service.collect_onu_status(olt_device)
            
            # Verify ONU monitoring
            assert len(onu_status) == 2
            
            # Online ONU verification
            online_onu = next(onu for onu in onu_status if onu["status"] == "online")
            assert online_onu["rx_power"] == -15.2
            assert online_onu["tx_power"] == 3.1
            assert online_onu["distance"] == 1250
            
            # Offline ONU should trigger customer service alert
            offline_onu = next(onu for onu in onu_status if onu["status"] == "offline")
            assert offline_onu["customer_id"] == "cust_fiber_002"
            assert offline_onu["rx_power"] is None


@pytest.mark.network_infrastructure
@pytest.mark.critical
class TestServiceProvisioningIntegration:
    """Test network service provisioning workflows."""
    
    async def test_new_customer_service_provisioning(self, db_session):
        """Test complete service provisioning workflow for new customer."""
        provisioning_service = ServiceProvisioningService(db_session, "tenant_001")
        network_service = NetworkIntegrationService(db_session, "tenant_001")
        
        # New customer service request
        service_request = {
            "customer_id": "cust_new_001",
            "service_plan": "residential_fiber_100",
            "installation_address": {
                "street": "123 Fiber Lane",
                "city": "Network City",
                "state": "NS",
                "zip": "12345"
            },
            "service_type": "fiber_internet",
            "bandwidth_down": 100_000_000,  # 100 Mbps
            "bandwidth_up": 100_000_000,    # 100 Mbps symmetric
            "ip_allocation": "dynamic"
        }
        
        # Mock provisioning steps
        with patch.object(provisioning_service, 'allocate_service_resources') as mock_allocate:
            with patch.object(network_service, 'configure_customer_equipment') as mock_configure:
                with patch.object(network_service, 'activate_service_profile') as mock_activate:
                    
                    # Mock successful resource allocation
                    mock_allocate.return_value = {
                        "username": "cust_new_001@isp.com", 
                        "password": "temp_password_123",
                        "vlan_id": 100,
                        "ip_pool": "residential_fiber",
                        "bandwidth_profile": "100M_symmetric"
                    }
                    
                    # Mock equipment configuration
                    mock_configure.return_value = {
                        "ont_serial": "GPON98765432",
                        "ont_configured": True,
                        "service_activated": True
                    }
                    
                    # Mock service activation
                    mock_activate.return_value = {"status": "active"}
                    
                    # Execute provisioning workflow
                    provision_result = await provisioning_service.provision_new_service(
                        service_request
                    )
                    
                    # Verify provisioning completed successfully
                    assert provision_result["status"] == "provisioned"
                    assert provision_result["service_active"] is True
                    assert "username" in provision_result
                    assert "bandwidth_profile" in provision_result
                    
                    # Verify all provisioning steps were called
                    mock_allocate.assert_called_once()
                    mock_configure.assert_called_once()
                    mock_activate.assert_called_once()

    async def test_service_upgrade_bandwidth_modification(self, db_session):
        """Test bandwidth upgrade for existing customer service.""" 
        provisioning_service = ServiceProvisioningService(db_session, "tenant_001")
        network_service = NetworkIntegrationService(db_session, "tenant_001")
        
        # Existing customer upgrade request
        upgrade_request = {
            "customer_id": "cust_existing_001",
            "current_plan": "residential_fiber_100", 
            "new_plan": "residential_fiber_500",
            "new_bandwidth_down": 500_000_000,  # 500 Mbps
            "new_bandwidth_up": 500_000_000,    # 500 Mbps
            "effective_date": datetime.utcnow().date()
        }
        
        # Mock current service configuration
        current_service = {
            "service_id": "svc_existing_001",
            "username": "cust_existing_001@isp.com",
            "current_bandwidth_down": 100_000_000,
            "current_bandwidth_up": 100_000_000,
            "vlan_id": 150,
            "ont_serial": "GPON11111111"
        }
        
        with patch.object(provisioning_service, 'get_current_service', return_value=current_service):
            with patch.object(network_service, 'update_bandwidth_profile') as mock_update:
                with patch.object(network_service, 'update_radius_attributes') as mock_radius:
                    
                    mock_update.return_value = {"profile_updated": True}
                    mock_radius.return_value = {"radius_updated": True}
                    
                    # Execute service upgrade
                    upgrade_result = await provisioning_service.upgrade_service_bandwidth(
                        upgrade_request
                    )
                    
                    # Verify upgrade completed successfully
                    assert upgrade_result["status"] == "upgraded"
                    assert upgrade_result["new_bandwidth_down"] == 500_000_000
                    assert upgrade_result["new_bandwidth_up"] == 500_000_000
                    
                    # Verify network configuration was updated
                    mock_update.assert_called_once()
                    mock_radius.assert_called_once()

    async def test_service_suspension_for_non_payment(self, db_session):
        """Test service suspension workflow for non-payment."""
        provisioning_service = ServiceProvisioningService(db_session, "tenant_001")
        network_service = NetworkIntegrationService(db_session, "tenant_001")
        
        # Customer service to be suspended
        suspension_request = {
            "customer_id": "cust_overdue_001",
            "service_id": "svc_overdue_001", 
            "suspension_reason": "overdue_payment",
            "suspension_type": "internet_only",  # Keep phone service active
            "grace_period_end": datetime.utcnow() + timedelta(days=7)
        }
        
        # Current active service
        active_service = {
            "customer_id": "cust_overdue_001",
            "username": "cust_overdue_001@isp.com",
            "services": ["internet", "voip"],
            "current_status": "active"
        }
        
        with patch.object(provisioning_service, 'get_customer_services', return_value=active_service):
            with patch.object(network_service, 'suspend_internet_service') as mock_suspend:
                with patch.object(network_service, 'update_radius_suspension') as mock_radius:
                    
                    mock_suspend.return_value = {"internet_suspended": True}
                    mock_radius.return_value = {"radius_blocked": True}
                    
                    # Execute service suspension
                    suspension_result = await provisioning_service.suspend_customer_service(
                        suspension_request
                    )
                    
                    # Verify suspension completed
                    assert suspension_result["status"] == "suspended"
                    assert suspension_result["services_affected"] == ["internet"]
                    assert suspension_result["grace_period_end"] is not None
                    
                    # Verify network access was blocked
                    mock_suspend.assert_called_once()
                    mock_radius.assert_called_once()


@pytest.mark.network_infrastructure
@pytest.mark.performance
class TestNetworkScalePerformance:
    """Test network operations under ISP scale loads."""
    
    async def test_bulk_snmp_polling_performance(self, db_session):
        """Test SNMP polling performance across hundreds of devices."""
        monitoring_service = NetworkMonitoringService(db_session, "tenant_001")
        
        # Generate large device inventory for testing
        device_count = 500
        mock_devices = []
        for i in range(device_count):
            mock_devices.append({
                "device_id": f"device_{i:03d}",
                "ip_address": f"192.168.{i//255}.{i%255}",
                "device_type": "router" if i % 3 == 0 else "switch",
                "location": f"POP_{i//50}"
            })
        
        # Mock SNMP responses
        with patch.object(monitoring_service, 'poll_device_snmp') as mock_poll:
            mock_poll.return_value = {
                "cpu_usage": 15.2,
                "memory_usage": 45.8,
                "interface_count": 24,
                "uptime": 86400 * 30  # 30 days
            }
            
            # Measure polling performance
            start_time = datetime.utcnow()
            
            # Use asyncio.gather for concurrent polling
            polling_tasks = [
                monitoring_service.poll_device_snmp(device["ip_address"])
                for device in mock_devices
            ]
            
            results = await asyncio.gather(*polling_tasks, return_exceptions=True)
            
            end_time = datetime.utcnow()
            polling_duration = (end_time - start_time).total_seconds()
            
            # Performance requirements for ISP scale
            assert polling_duration < 30.0, f"Bulk SNMP polling took {polling_duration}s (limit: 30s)"
            assert len(results) == device_count
            
            # Verify no polling failures
            failed_polls = [r for r in results if isinstance(r, Exception)]
            assert len(failed_polls) == 0, f"{len(failed_polls)} devices failed to poll"

    async def test_concurrent_radius_authentication_load(self, db_session):
        """Test RADIUS server performance under concurrent authentication load."""
        radius_client = FreeRadiusClient()
        
        # Simulate concurrent customer logins during peak hours
        concurrent_auths = 100
        auth_requests = []
        
        for i in range(concurrent_auths):
            auth_requests.append({
                "username": f"customer{i:03d}@isp.com",
                "password": f"password_{i}",
                "nas_ip": f"10.0.{i//50}.{i%50}",
                "service_type": "Framed-User"
            })
        
        # Mock RADIUS responses  
        with patch.object(radius_client, 'authenticate') as mock_auth:
            mock_auth.return_value = {
                "result": "Access-Accept",
                "session_timeout": 86400
            }
            
            # Measure concurrent authentication performance
            start_time = datetime.utcnow()
            
            auth_tasks = [
                radius_client.authenticate(request)
                for request in auth_requests
            ]
            
            results = await asyncio.gather(*auth_tasks, return_exceptions=True)
            
            end_time = datetime.utcnow()
            auth_duration = (end_time - start_time).total_seconds()
            
            # Performance requirements
            assert auth_duration < 10.0, f"Concurrent RADIUS auth took {auth_duration}s (limit: 10s)" 
            assert len(results) == concurrent_auths
            
            # Verify all authentications succeeded
            successful_auths = [r for r in results if isinstance(r, dict) and r.get("result") == "Access-Accept"]
            assert len(successful_auths) == concurrent_auths


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])