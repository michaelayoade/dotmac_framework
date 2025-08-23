"""Comprehensive business logic tests for Network Integration.

Tests cover:
- Device discovery and provisioning  
- SNMP monitoring and alerting
- Ansible playbook execution
- VOLTHA GPON operations
- FreeRADIUS authentication flows
- Network automation workflows
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
from typing import Dict, Any, List
import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.network
@pytest.mark.integration
class TestDeviceDiscoveryAndProvisioning:
    """Test network device discovery and provisioning workflows."""
    
    @pytest.mark.asyncio
    async def test_snmp_device_discovery(self, db_session: AsyncSession, mock_snmp_client):
        """Test SNMP-based device discovery process."""
        from dotmac_isp.modules.network_integration.services import DeviceDiscoveryService
        
        # Mock SNMP responses for device discovery
        mock_snmp_client.get.side_effect = [
            "1.3.6.1.4.1.9.1.1234",  # sysObjectID (Cisco device)
            "Cisco IOS Software",     # sysDescr 
            "Router-Lab-01",         # sysName
            "Main Lab",              # sysLocation
            "Admin Contact",         # sysContact
        ]
        
        discovery_service = DeviceDiscoveryService(db_session, mock_snmp_client)
        
        # Discover device at IP address
        discovered_device = await discovery_service.discover_device("192.168.1.1")
        
        assert discovered_device is not None
        assert discovered_device["ip_address"] == "192.168.1.1"
        assert discovered_device["device_type"] == "router"
        assert discovered_device["vendor"] == "cisco" 
        assert discovered_device["model"] == "IOS"
        assert discovered_device["hostname"] == "Router-Lab-01"
        assert discovered_device["location"] == "Main Lab"
        
        # Verify SNMP calls were made
        expected_oids = [
            "1.3.6.1.2.1.1.2.0",  # sysObjectID
            "1.3.6.1.2.1.1.1.0",  # sysDescr
            "1.3.6.1.2.1.1.5.0",  # sysName
            "1.3.6.1.2.1.1.6.0",  # sysLocation  
            "1.3.6.1.2.1.1.4.0",  # sysContact
        ]
        
        for oid in expected_oids:
            mock_snmp_client.get.assert_any_call("192.168.1.1", oid)
    
    @pytest.mark.asyncio
    async def test_device_provisioning_workflow(self, async_client, auth_headers, sample_network_device_data, mock_ansible_runner):
        """Test complete device provisioning workflow."""
        
        # Mock successful Ansible playbook execution
        mock_ansible_runner.run.return_value = MagicMock(
            status="successful",
            stdout="Device configured successfully",
            rc=0,
            stats={"ok": 5, "changed": 3, "unreachable": 0, "failed": 0}
        )
        
        # Create device provisioning request
        provisioning_request = {
            **sample_network_device_data,
            "config_template": "basic_router_config",
            "vlans": [
                {"vlan_id": 100, "name": "MGMT", "subnet": "10.0.100.0/24"},
                {"vlan_id": 200, "name": "GUEST", "subnet": "10.0.200.0/24"},
            ],
            "interfaces": [
                {
                    "interface": "GigabitEthernet0/1",
                    "description": "Uplink to ISP",
                    "vlan": 100,
                    "ip_address": "192.168.1.1/30"
                }
            ]
        }
        
        # Submit provisioning request
        response = await async_client.post(
            "/api/v1/network/devices/provision",
            json=provisioning_request,
            headers=auth_headers
        )
        
        assert response.status_code == 202  # Accepted for async processing
        result = response.json()
        
        assert "job_id" in result
        assert result["status"] == "pending"
        
        # Check provisioning job status
        job_id = result["job_id"]
        status_response = await async_client.get(
            f"/api/v1/network/jobs/{job_id}/status",
            headers=auth_headers
        )
        
        assert status_response.status_code == 200
        job_status = status_response.json()
        
        # Verify Ansible playbook was executed
        mock_ansible_runner.run.assert_called_once()
        call_args = mock_ansible_runner.run.call_args
        assert call_args[0][0] == "basic_router_config"  # playbook name
        assert call_args[1]["inventory"]["all"]["hosts"]["192.168.1.1"] is not None
    
    @pytest.mark.asyncio 
    async def test_device_configuration_validation(self, async_client, auth_headers, mock_snmp_client):
        """Test device configuration validation after provisioning."""
        
        # Mock SNMP responses for configuration validation
        mock_snmp_client.walk.return_value = [
            ("1.3.6.1.2.1.2.2.1.2.1", "GigabitEthernet0/1"),  # Interface name
            ("1.3.6.1.2.1.2.2.1.8.1", "1"),                   # Interface up
            ("1.3.6.1.2.1.4.20.1.1.192.168.1.1", "192.168.1.1"),  # IP address
        ]
        
        # Request configuration validation
        validation_response = await async_client.post(
            "/api/v1/network/devices/validate-config",
            json={
                "device_ip": "192.168.1.1",
                "expected_config": {
                    "interfaces": ["GigabitEthernet0/1"],
                    "ip_addresses": ["192.168.1.1"],
                    "interface_status": {"GigabitEthernet0/1": "up"}
                }
            },
            headers=auth_headers
        )
        
        assert validation_response.status_code == 200
        validation_result = validation_response.json()
        
        assert validation_result["is_valid"] == True
        assert validation_result["validated_items"]["interfaces"] == True
        assert validation_result["validated_items"]["ip_addresses"] == True 
        assert validation_result["validated_items"]["interface_status"] == True
    
    @pytest.mark.asyncio
    async def test_multi_vendor_device_support(self, db_session, mock_snmp_client):
        """Test device discovery for multiple vendor devices."""
        from dotmac_isp.modules.network_integration.services import DeviceDiscoveryService
        
        discovery_service = DeviceDiscoveryService(db_session, mock_snmp_client)
        
        # Test different vendor devices
        vendor_test_cases = [
            {
                "ip": "192.168.1.10",
                "sys_object_id": "1.3.6.1.4.1.9.1.1234",    # Cisco
                "sys_descr": "Cisco IOS Software",
                "expected_vendor": "cisco",
                "expected_type": "router"
            },
            {
                "ip": "192.168.1.11", 
                "sys_object_id": "1.3.6.1.4.1.2636.1.1.1",  # Juniper
                "sys_descr": "Juniper Networks",
                "expected_vendor": "juniper",
                "expected_type": "router"
            },
            {
                "ip": "192.168.1.12",
                "sys_object_id": "1.3.6.1.4.1.11.1.3.1.1.1", # HP/HPE
                "sys_descr": "HP ProCurve Switch",
                "expected_vendor": "hpe",
                "expected_type": "switch"
            }
        ]
        
        for test_case in vendor_test_cases:
            # Configure mock responses for this device
            mock_snmp_client.get.side_effect = [
                test_case["sys_object_id"],
                test_case["sys_descr"],
                f"Device-{test_case['ip']}",
                "Test Location",
                "Test Contact"
            ]
            
            discovered = await discovery_service.discover_device(test_case["ip"])
            
            assert discovered["vendor"] == test_case["expected_vendor"]
            assert discovered["device_type"] == test_case["expected_type"]
            assert discovered["ip_address"] == test_case["ip"]


@pytest.mark.network
@pytest.mark.monitoring 
class TestSNMPMonitoringAndAlerting:
    """Test SNMP monitoring and alerting system."""
    
    @pytest.mark.asyncio
    async def test_interface_monitoring_workflow(self, db_session, mock_snmp_client):
        """Test interface monitoring with threshold alerting."""
        from dotmac_isp.modules.network_monitoring.services import MonitoringService
        
        # Mock SNMP responses for interface monitoring
        mock_snmp_client.walk.return_value = [
            # Interface descriptions
            ("1.3.6.1.2.1.2.2.1.2.1", "GigabitEthernet0/1"),
            ("1.3.6.1.2.1.2.2.1.2.2", "GigabitEthernet0/2"), 
            
            # Interface status (1=up, 2=down)
            ("1.3.6.1.2.1.2.2.1.8.1", "1"),
            ("1.3.6.1.2.1.2.2.1.8.2", "1"),
            
            # Interface utilization (bytes in/out)
            ("1.3.6.1.2.1.2.2.1.10.1", "1000000000"),  # bytes in
            ("1.3.6.1.2.1.2.2.1.16.1", "500000000"),   # bytes out
            ("1.3.6.1.2.1.2.2.1.10.2", "2000000000"),  # bytes in  
            ("1.3.6.1.2.1.2.2.1.16.2", "1800000000"),  # bytes out
        ]
        
        monitoring_service = MonitoringService(db_session, mock_snmp_client)
        
        # Monitor device interfaces
        monitoring_result = await monitoring_service.monitor_device_interfaces("192.168.1.1")
        
        assert monitoring_result["device_ip"] == "192.168.1.1"
        assert len(monitoring_result["interfaces"]) == 2
        
        # Verify interface data
        interface1 = monitoring_result["interfaces"][0] 
        assert interface1["name"] == "GigabitEthernet0/1"
        assert interface1["status"] == "up"
        assert interface1["bytes_in"] == 1000000000
        assert interface1["bytes_out"] == 500000000
        
        # Check for alerts based on thresholds
        alerts = monitoring_result["alerts"]
        
        # Interface 2 should trigger high utilization alert
        high_util_alerts = [a for a in alerts if a["alert_type"] == "high_utilization"]
        assert len(high_util_alerts) > 0
        
        high_util_alert = high_util_alerts[0]
        assert high_util_alert["interface"] == "GigabitEthernet0/2"
        assert high_util_alert["severity"] == "warning"
    
    @pytest.mark.asyncio
    async def test_device_availability_monitoring(self, async_client, auth_headers, mock_snmp_client):
        """Test device availability monitoring and alerting."""
        
        # Configure monitoring for device
        monitoring_config = {
            "device_ip": "192.168.1.1",
            "monitoring_interval": 60,  # seconds
            "thresholds": {
                "availability": 95.0,  # percent uptime
                "response_time": 100,  # milliseconds
            },
            "alert_recipients": ["network-ops@example.com"]
        }
        
        config_response = await async_client.post(
            "/api/v1/network/monitoring/configure",
            json=monitoring_config,
            headers=auth_headers
        )
        
        assert config_response.status_code == 201
        
        # Simulate monitoring checks
        monitoring_checks = [
            {"timestamp": "2024-01-01T10:00:00Z", "available": True, "response_time": 25},
            {"timestamp": "2024-01-01T10:01:00Z", "available": True, "response_time": 30},
            {"timestamp": "2024-01-01T10:02:00Z", "available": False, "response_time": None},  # Down
            {"timestamp": "2024-01-01T10:03:00Z", "available": False, "response_time": None},  # Still down
            {"timestamp": "2024-01-01T10:04:00Z", "available": True, "response_time": 45},    # Back up
        ]
        
        for check in monitoring_checks:
            check_response = await async_client.post(
                f"/api/v1/network/monitoring/devices/{monitoring_config['device_ip']}/check",
                json=check,
                headers=auth_headers
            )
            assert check_response.status_code == 200
        
        # Get monitoring statistics
        stats_response = await async_client.get(
            f"/api/v1/network/monitoring/devices/{monitoring_config['device_ip']}/stats",
            params={"period": "1h"},
            headers=auth_headers
        )
        
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        assert stats["total_checks"] == 5
        assert stats["successful_checks"] == 3
        assert stats["availability_percent"] == 60.0  # 3/5 * 100
        assert stats["average_response_time"] == 33.33  # (25+30+45)/3
        
        # Check for availability alerts
        alerts_response = await async_client.get(
            f"/api/v1/network/monitoring/devices/{monitoring_config['device_ip']}/alerts",
            headers=auth_headers
        )
        
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()
        
        # Should have availability alert (60% < 95% threshold)
        availability_alerts = [a for a in alerts if a["alert_type"] == "availability"]
        assert len(availability_alerts) > 0
        assert availability_alerts[0]["severity"] in ["critical", "major"]
    
    @pytest.mark.asyncio
    async def test_bandwidth_utilization_alerting(self, db_session, mock_snmp_client):
        """Test bandwidth utilization monitoring and alerting."""
        from dotmac_isp.modules.network_monitoring.services import BandwidthMonitoringService
        
        # Mock high bandwidth utilization
        mock_snmp_client.get.side_effect = [
            "1000000000",  # Interface speed (1 Gbps)
            "800000000",   # Bytes in (80% utilization)
            "750000000",   # Bytes out (75% utilization)
        ]
        
        bandwidth_service = BandwidthMonitoringService(db_session, mock_snmp_client)
        
        utilization_data = await bandwidth_service.check_interface_utilization(
            device_ip="192.168.1.1",
            interface_index=1,
            warning_threshold=70.0,
            critical_threshold=90.0
        )
        
        assert utilization_data["device_ip"] == "192.168.1.1"
        assert utilization_data["interface_index"] == 1
        assert utilization_data["utilization_in_percent"] == 80.0
        assert utilization_data["utilization_out_percent"] == 75.0
        
        # Should trigger warning alert for inbound traffic
        assert utilization_data["alert_level"] == "warning" 
        assert "inbound utilization" in utilization_data["alert_message"].lower()
    
    @pytest.mark.asyncio
    async def test_custom_oid_monitoring(self, async_client, auth_headers, mock_snmp_client):
        """Test monitoring of custom SNMP OIDs."""
        
        # Configure custom OID monitoring
        custom_oid_config = {
            "device_ip": "192.168.1.1",
            "custom_oids": [
                {
                    "oid": "1.3.6.1.4.1.9.2.1.58.0",  # Cisco CPU utilization
                    "name": "cpu_utilization", 
                    "unit": "percent",
                    "warning_threshold": 80,
                    "critical_threshold": 95
                },
                {
                    "oid": "1.3.6.1.4.1.9.2.1.8.0",   # Cisco memory utilization
                    "name": "memory_utilization",
                    "unit": "percent", 
                    "warning_threshold": 85,
                    "critical_threshold": 95
                }
            ]
        }
        
        # Configure monitoring
        config_response = await async_client.post(
            "/api/v1/network/monitoring/custom-oids",
            json=custom_oid_config,
            headers=auth_headers
        )
        
        assert config_response.status_code == 201
        
        # Mock SNMP responses
        mock_snmp_client.get.side_effect = [
            "85",  # CPU utilization (warning level)
            "92",  # Memory utilization (critical level)
        ]
        
        # Trigger monitoring check
        monitor_response = await async_client.post(
            f"/api/v1/network/monitoring/devices/{custom_oid_config['device_ip']}/check-custom-oids",
            headers=auth_headers
        )
        
        assert monitor_response.status_code == 200
        results = monitor_response.json()
        
        # Verify CPU monitoring
        cpu_result = next(r for r in results if r["oid_name"] == "cpu_utilization")
        assert cpu_result["value"] == 85
        assert cpu_result["alert_level"] == "warning"
        
        # Verify memory monitoring  
        memory_result = next(r for r in results if r["oid_name"] == "memory_utilization")
        assert memory_result["value"] == 92
        assert memory_result["alert_level"] == "critical"


@pytest.mark.network
@pytest.mark.automation
class TestAnsiblePlaybookExecution:
    """Test Ansible automation and playbook execution."""
    
    @pytest.mark.asyncio
    async def test_basic_playbook_execution(self, async_client, auth_headers, mock_ansible_runner):
        """Test basic Ansible playbook execution."""
        
        # Mock successful playbook execution
        mock_ansible_runner.run.return_value = MagicMock(
            status="successful",
            stdout="PLAY RECAP: Router-01 ok=10 changed=5 unreachable=0 failed=0",
            stderr="",
            rc=0,
            stats={"Router-01": {"ok": 10, "changed": 5, "unreachable": 0, "failed": 0}}
        )
        
        playbook_request = {
            "playbook_name": "configure_basic_router",
            "inventory": {
                "routers": {
                    "hosts": {
                        "Router-01": {
                            "ansible_host": "192.168.1.1",
                            "ansible_user": "admin",
                            "device_type": "ios"
                        }
                    }
                }
            },
            "variables": {
                "hostname": "Router-Lab-01",
                "domain_name": "lab.local",
                "ntp_servers": ["pool.ntp.org"],
                "snmp_community": "readonly123"
            }
        }
        
        # Execute playbook
        response = await async_client.post(
            "/api/v1/network/ansible/execute",
            json=playbook_request,
            headers=auth_headers
        )
        
        assert response.status_code == 202  # Accepted for async execution
        result = response.json()
        
        assert "execution_id" in result
        assert result["status"] == "running"
        
        # Check execution status
        execution_id = result["execution_id"]
        status_response = await async_client.get(
            f"/api/v1/network/ansible/executions/{execution_id}",
            headers=auth_headers
        )
        
        assert status_response.status_code == 200
        execution_status = status_response.json()
        
        assert execution_status["status"] == "successful"
        assert execution_status["stats"]["Router-01"]["changed"] == 5
        assert execution_status["stats"]["Router-01"]["failed"] == 0
    
    @pytest.mark.asyncio 
    async def test_playbook_execution_with_failure_handling(self, async_client, auth_headers, mock_ansible_runner):
        """Test playbook execution with failure scenarios."""
        
        # Mock failed playbook execution
        mock_ansible_runner.run.return_value = MagicMock(
            status="failed",
            stdout="TASK [Configure SNMP] FAILED",
            stderr="Authentication failed",
            rc=1,
            stats={"Router-01": {"ok": 3, "changed": 2, "unreachable": 0, "failed": 1}}
        )
        
        playbook_request = {
            "playbook_name": "configure_snmp",
            "inventory": {
                "routers": {
                    "hosts": {
                        "Router-01": {"ansible_host": "192.168.1.1"}
                    }
                }
            },
            "failure_handling": {
                "retry_count": 3,
                "retry_delay": 30,  # seconds
                "continue_on_error": False
            }
        }
        
        # Execute playbook
        response = await async_client.post(
            "/api/v1/network/ansible/execute", 
            json=playbook_request,
            headers=auth_headers
        )
        
        execution_id = response.json()["execution_id"]
        
        # Wait for completion and check results
        await asyncio.sleep(0.1)  # Simulate async execution time
        
        status_response = await async_client.get(
            f"/api/v1/network/ansible/executions/{execution_id}",
            headers=auth_headers
        )
        
        execution_result = status_response.json()
        
        assert execution_result["status"] == "failed"
        assert execution_result["error_message"] == "Authentication failed"
        assert execution_result["stats"]["Router-01"]["failed"] == 1
        
        # Verify retry attempts were made
        assert execution_result["retry_attempts"] == 3
    
    @pytest.mark.asyncio
    async def test_dynamic_inventory_generation(self, async_client, auth_headers, db_session):
        """Test dynamic inventory generation for playbook execution."""
        
        # Create test devices in database
        from dotmac_isp.modules.network_integration.models import NetworkDevice
        
        test_devices = [
            {
                "device_id": "DEV001",
                "hostname": "Router-01", 
                "ip_address": "192.168.1.1",
                "device_type": "router",
                "vendor": "cisco",
                "location": "Lab-A",
                "tenant_id": "tenant_001"
            },
            {
                "device_id": "DEV002", 
                "hostname": "Switch-01",
                "ip_address": "192.168.1.2",
                "device_type": "switch",
                "vendor": "cisco",
                "location": "Lab-A", 
                "tenant_id": "tenant_001"
            },
            {
                "device_id": "DEV003",
                "hostname": "Router-02",
                "ip_address": "192.168.1.3", 
                "device_type": "router",
                "vendor": "juniper",
                "location": "Lab-B",
                "tenant_id": "tenant_001"
            }
        ]
        
        # Add devices to database (mocked)
        for device_data in test_devices:
            # In real implementation, this would create database records
            pass
        
        # Request dynamic inventory generation
        inventory_request = {
            "filters": {
                "device_type": "router",
                "location": ["Lab-A", "Lab-B"],
                "tenant_id": "tenant_001"
            },
            "group_by": ["location", "vendor"]
        }
        
        inventory_response = await async_client.post(
            "/api/v1/network/ansible/inventory/generate",
            json=inventory_request,
            headers=auth_headers
        )
        
        assert inventory_response.status_code == 200
        inventory = inventory_response.json()
        
        # Verify inventory structure
        assert "lab_a_cisco" in inventory
        assert "lab_b_juniper" in inventory
        
        # Verify device groupings
        lab_a_cisco = inventory["lab_a_cisco"]["hosts"]
        assert "Router-01" in lab_a_cisco
        assert lab_a_cisco["Router-01"]["ansible_host"] == "192.168.1.1"
        
        lab_b_juniper = inventory["lab_b_juniper"]["hosts"] 
        assert "Router-02" in lab_b_juniper
        assert lab_b_juniper["Router-02"]["ansible_host"] == "192.168.1.3"
    
    @pytest.mark.asyncio
    async def test_playbook_template_management(self, async_client, auth_headers):
        """Test playbook template creation and management."""
        
        # Create custom playbook template
        template_data = {
            "name": "custom_vlan_config",
            "description": "Configure VLANs on Cisco switches",
            "category": "switching",
            "template_content": '''
---
- name: Configure VLANs
  hosts: switches
  gather_facts: no
  tasks:
    - name: Create VLANs
      ios_vlans:
        config:
          - vlan_id: "{{ item.id }}"
            name: "{{ item.name }}"
        state: merged
      loop: "{{ vlans }}"
    
    - name: Configure access ports
      ios_l2_interfaces:
        config:
          - name: "{{ item.interface }}"
            access:
              vlan: "{{ item.vlan }}"
        state: merged
      loop: "{{ access_ports }}"
            ''',
            "parameters": [
                {
                    "name": "vlans",
                    "type": "list",
                    "required": True,
                    "description": "List of VLANs to configure"
                },
                {
                    "name": "access_ports", 
                    "type": "list",
                    "required": False,
                    "description": "List of access port configurations"
                }
            ]
        }
        
        # Create template
        create_response = await async_client.post(
            "/api/v1/network/ansible/templates",
            json=template_data,
            headers=auth_headers
        )
        
        assert create_response.status_code == 201
        template_result = create_response.json()
        
        assert template_result["name"] == "custom_vlan_config"
        assert "template_id" in template_result
        
        # List templates
        list_response = await async_client.get(
            "/api/v1/network/ansible/templates",
            headers=auth_headers
        )
        
        assert list_response.status_code == 200
        templates = list_response.json()
        
        # Verify our template is listed
        custom_template = next(t for t in templates if t["name"] == "custom_vlan_config")
        assert custom_template["category"] == "switching"
        assert len(custom_template["parameters"]) == 2
        
        # Execute template
        execution_request = {
            "template_id": template_result["template_id"],
            "inventory": {
                "switches": {
                    "hosts": {
                        "Switch-01": {"ansible_host": "192.168.1.10"}
                    }
                }
            },
            "parameters": {
                "vlans": [
                    {"id": 100, "name": "MGMT"},
                    {"id": 200, "name": "GUEST"}
                ],
                "access_ports": [
                    {"interface": "GigabitEthernet1/1", "vlan": 100}
                ]
            }
        }
        
        exec_response = await async_client.post(
            "/api/v1/network/ansible/templates/execute",
            json=execution_request, 
            headers=auth_headers
        )
        
        assert exec_response.status_code == 202
        assert "execution_id" in exec_response.json()


@pytest.mark.network
@pytest.mark.voltha
class TestVOLTHAGPONOperations:
    """Test VOLTHA GPON operations and management."""
    
    @pytest.mark.asyncio
    async def test_olt_device_management(self, async_client, auth_headers):
        """Test OLT device provisioning and management."""
        
        # Add OLT device to VOLTHA
        olt_data = {
            "device_type": "openolt",
            "host_and_port": "192.168.1.100:9191",
            "device_id": "OLT-001",
            "description": "Main Lab OLT"
        }
        
        response = await async_client.post(
            "/api/v1/network/voltha/devices/olt",
            json=olt_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["device_id"] == "OLT-001"
        assert result["admin_state"] == "PREPROVISIONED"
        
        # Enable OLT device
        enable_response = await async_client.post(
            f"/api/v1/network/voltha/devices/{result['device_id']}/enable",
            headers=auth_headers
        )
        
        assert enable_response.status_code == 200
        enabled_result = enable_response.json()
        
        assert enabled_result["admin_state"] == "ENABLED"
        assert enabled_result["oper_status"] == "ACTIVE"
    
    @pytest.mark.asyncio
    async def test_onu_provisioning_workflow(self, async_client, auth_headers):
        """Test ONU device provisioning and activation."""
        
        # Discover ONU devices
        discover_response = await async_client.post(
            "/api/v1/network/voltha/devices/OLT-001/discover-onus",
            headers=auth_headers
        )
        
        assert discover_response.status_code == 200
        discovered_onus = discover_response.json()["onus"]
        
        # Should find at least one ONU
        assert len(discovered_onus) > 0
        
        discovered_onu = discovered_onus[0]
        assert "serial_number" in discovered_onu
        assert "pon_port" in discovered_onu
        
        # Provision discovered ONU
        provision_data = {
            "serial_number": discovered_onu["serial_number"],
            "pon_port": discovered_onu["pon_port"],
            "customer_id": "CUST001",
            "service_profile": "residential_100mbps",
            "vlan_id": 100
        }
        
        provision_response = await async_client.post(
            "/api/v1/network/voltha/devices/onus/provision",
            json=provision_data,
            headers=auth_headers
        )
        
        assert provision_response.status_code == 201
        provisioned_onu = provision_response.json()
        
        assert provisioned_onu["serial_number"] == discovered_onu["serial_number"]
        assert provisioned_onu["admin_state"] == "ENABLED"
        assert provisioned_onu["customer_id"] == "CUST001"
    
    @pytest.mark.asyncio
    async def test_service_flow_configuration(self, async_client, auth_headers):
        """Test service flow configuration for ONU devices."""
        
        # Configure downstream service flow
        downstream_flow = {
            "onu_serial": "ALCL12345678",
            "direction": "downstream",
            "service_type": "internet",
            "bandwidth_profile": {
                "guaranteed_info_rate": 100000000,  # 100 Mbps
                "peak_info_rate": 100000000,
                "maximum_burst_size": 1000000,
                "priority": 1
            },
            "vlan_config": {
                "c_vlan": 100,
                "s_vlan": 2000
            }
        }
        
        ds_response = await async_client.post(
            "/api/v1/network/voltha/flows/configure",
            json=downstream_flow,
            headers=auth_headers
        )
        
        assert ds_response.status_code == 201
        ds_result = ds_response.json()
        
        assert ds_result["flow_id"] is not None
        assert ds_result["status"] == "active"
        
        # Configure upstream service flow
        upstream_flow = {
            "onu_serial": "ALCL12345678",
            "direction": "upstream",
            "service_type": "internet",
            "bandwidth_profile": {
                "guaranteed_info_rate": 20000000,   # 20 Mbps
                "peak_info_rate": 20000000,
                "maximum_burst_size": 500000,
                "priority": 1
            },
            "vlan_config": {
                "c_vlan": 100,
                "s_vlan": 2000
            }
        }
        
        us_response = await async_client.post(
            "/api/v1/network/voltha/flows/configure",
            json=upstream_flow,
            headers=auth_headers
        )
        
        assert us_response.status_code == 201
        us_result = us_response.json()
        
        assert us_result["flow_id"] is not None
        assert us_result["status"] == "active"
        
        # Verify flows are configured correctly
        flows_response = await async_client.get(
            f"/api/v1/network/voltha/devices/onus/ALCL12345678/flows",
            headers=auth_headers
        )
        
        assert flows_response.status_code == 200
        flows = flows_response.json()["flows"]
        
        assert len(flows) == 2  # Downstream and upstream
        
        ds_flow = next(f for f in flows if f["direction"] == "downstream")
        us_flow = next(f for f in flows if f["direction"] == "upstream")
        
        assert ds_flow["bandwidth_profile"]["guaranteed_info_rate"] == 100000000
        assert us_flow["bandwidth_profile"]["guaranteed_info_rate"] == 20000000
    
    @pytest.mark.asyncio
    async def test_pon_port_statistics(self, async_client, auth_headers):
        """Test PON port statistics and monitoring."""
        
        # Get PON port statistics
        stats_response = await async_client.get(
            "/api/v1/network/voltha/devices/OLT-001/pon-ports/statistics",
            headers=auth_headers
        )
        
        assert stats_response.status_code == 200
        stats = stats_response.json()["pon_ports"]
        
        # Verify statistics structure
        assert len(stats) > 0
        
        pon_port = stats[0]
        assert "port_number" in pon_port
        assert "rx_power" in pon_port
        assert "tx_power" in pon_port
        assert "bias_current" in pon_port
        assert "voltage" in pon_port
        assert "temperature" in pon_port
        
        # Verify reasonable values
        assert -40 <= pon_port["rx_power"] <= 10  # dBm range
        assert -10 <= pon_port["tx_power"] <= 10  # dBm range


@pytest.mark.network
@pytest.mark.radius
class TestFreeRADIUSAuthenticationFlows:
    """Test FreeRADIUS authentication and authorization."""
    
    @pytest.mark.asyncio
    async def test_customer_authentication_flow(self, async_client, auth_headers, sample_customer_data):
        """Test customer authentication through FreeRADIUS."""
        
        # Create customer with network access
        customer_data = {
            **sample_customer_data,
            "network_access": {
                "username": "customer001",
                "password": "netpass123",
                "service_type": "internet",
                "bandwidth_limit": "100Mbps/20Mbps",
                "vlan_id": 100,
                "static_ip": "192.168.100.10"
            }
        }
        
        # Create customer account
        customer_response = await async_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=auth_headers
        )
        
        assert customer_response.status_code == 201
        customer_id = customer_response.json()["customer_id"]
        
        # Simulate RADIUS authentication request
        radius_auth_request = {
            "username": "customer001",
            "password": "netpass123",
            "nas_ip": "192.168.1.1",
            "nas_port": "1/1/1",
            "calling_station_id": "00:11:22:33:44:55",
            "service_type": "Framed-User"
        }
        
        auth_response = await async_client.post(
            "/api/v1/network/radius/authenticate", 
            json=radius_auth_request,
            headers=auth_headers
        )
        
        assert auth_response.status_code == 200
        auth_result = auth_response.json()
        
        assert auth_result["result"] == "Access-Accept"
        
        # Verify returned RADIUS attributes
        attributes = auth_result["attributes"]
        assert attributes["Framed-IP-Address"] == "192.168.100.10"
        assert attributes["Tunnel-Private-Group-Id"] == "100"  # VLAN ID
        
        # Verify bandwidth attributes (Mikrotik format)
        assert attributes["Mikrotik-Rate-Limit"] == "20M/100M"
    
    @pytest.mark.asyncio
    async def test_mac_address_authentication(self, async_client, auth_headers):
        """Test MAC address-based authentication."""
        
        # Configure MAC address authentication
        mac_auth_config = {
            "mac_address": "00:11:22:33:44:55",
            "customer_id": "CUST001",
            "device_description": "Customer Router",
            "vlan_id": 200,
            "bandwidth_profile": "basic_50mbps",
            "status": "active"
        }
        
        config_response = await async_client.post(
            "/api/v1/network/radius/mac-auth",
            json=mac_auth_config,
            headers=auth_headers
        )
        
        assert config_response.status_code == 201
        
        # Simulate MAC authentication request
        mac_auth_request = {
            "username": "001122334455",  # MAC as username
            "password": "001122334455",  # MAC as password
            "nas_ip": "192.168.1.2",
            "calling_station_id": "00:11:22:33:44:55",
            "service_type": "Framed-User"
        }
        
        auth_response = await async_client.post(
            "/api/v1/network/radius/authenticate",
            json=mac_auth_request,
            headers=auth_headers
        )
        
        assert auth_response.status_code == 200
        result = auth_response.json()
        
        assert result["result"] == "Access-Accept"
        assert result["attributes"]["Tunnel-Private-Group-Id"] == "200"
    
    @pytest.mark.asyncio 
    async def test_accounting_and_session_management(self, async_client, auth_headers):
        """Test RADIUS accounting and session management."""
        
        # Start accounting session
        accounting_start = {
            "username": "customer001",
            "session_id": "session_12345",
            "nas_ip": "192.168.1.1",
            "nas_port": "1/1/1",
            "framed_ip": "192.168.100.10",
            "calling_station_id": "00:11:22:33:44:55",
            "acct_status_type": "Start"
        }
        
        start_response = await async_client.post(
            "/api/v1/network/radius/accounting",
            json=accounting_start,
            headers=auth_headers
        )
        
        assert start_response.status_code == 200
        
        # Send interim updates
        accounting_interim = {
            **accounting_start,
            "acct_status_type": "Interim-Update",
            "acct_input_octets": 1000000,    # 1MB received
            "acct_output_octets": 5000000,   # 5MB sent
            "acct_session_time": 300,        # 5 minutes
        }
        
        interim_response = await async_client.post(
            "/api/v1/network/radius/accounting",
            json=accounting_interim,
            headers=auth_headers
        )
        
        assert interim_response.status_code == 200
        
        # Get session information
        session_response = await async_client.get(
            f"/api/v1/network/radius/sessions/{accounting_start['session_id']}",
            headers=auth_headers
        )
        
        assert session_response.status_code == 200
        session_info = session_response.json()
        
        assert session_info["username"] == "customer001"
        assert session_info["session_id"] == "session_12345"
        assert session_info["input_octets"] == 1000000
        assert session_info["output_octets"] == 5000000
        assert session_info["session_time"] == 300
        assert session_info["status"] == "active"
        
        # Stop accounting session
        accounting_stop = {
            **accounting_interim,
            "acct_status_type": "Stop",
            "acct_input_octets": 10000000,   # 10MB total received
            "acct_output_octets": 50000000,  # 50MB total sent
            "acct_session_time": 1800,       # 30 minutes total
            "acct_terminate_cause": "User-Request"
        }
        
        stop_response = await async_client.post(
            "/api/v1/network/radius/accounting",
            json=accounting_stop,
            headers=auth_headers
        )
        
        assert stop_response.status_code == 200
        
        # Verify session is closed
        final_session_response = await async_client.get(
            f"/api/v1/network/radius/sessions/{accounting_start['session_id']}",
            headers=auth_headers
        )
        
        final_session = final_session_response.json()
        assert final_session["status"] == "closed"
        assert final_session["terminate_cause"] == "User-Request"
    
    @pytest.mark.asyncio
    async def test_radius_server_failover(self, async_client, auth_headers):
        """Test RADIUS server failover and high availability."""
        
        # Configure multiple RADIUS servers
        radius_config = {
            "primary_server": {
                "host": "radius1.example.com",
                "port": 1812,
                "secret": "shared_secret_123",
                "timeout": 3,
                "retries": 2
            },
            "secondary_server": {
                "host": "radius2.example.com", 
                "port": 1812,
                "secret": "shared_secret_123",
                "timeout": 3,
                "retries": 2
            },
            "failover_policy": {
                "mode": "active-passive",
                "health_check_interval": 60,
                "failback_delay": 300
            }
        }
        
        config_response = await async_client.put(
            "/api/v1/network/radius/configuration",
            json=radius_config,
            headers=auth_headers
        )
        
        assert config_response.status_code == 200
        
        # Test server health check
        health_response = await async_client.get(
            "/api/v1/network/radius/health",
            headers=auth_headers
        )
        
        assert health_response.status_code == 200
        health_status = health_response.json()
        
        assert "primary_server" in health_status
        assert "secondary_server" in health_status
        
        # At least one server should be healthy
        primary_healthy = health_status["primary_server"]["status"] == "healthy"
        secondary_healthy = health_status["secondary_server"]["status"] == "healthy"
        assert primary_healthy or secondary_healthy
        
        # Test failover scenario (simulate primary server down)
        failover_response = await async_client.post(
            "/api/v1/network/radius/simulate-failover",
            json={"server": "primary", "action": "disable"},
            headers=auth_headers
        )
        
        assert failover_response.status_code == 200
        
        # Verify secondary server becomes active
        await asyncio.sleep(0.1)  # Brief wait for failover
        
        status_response = await async_client.get(
            "/api/v1/network/radius/status",
            headers=auth_headers
        )
        
        status = status_response.json()
        assert status["active_server"] == "secondary"
        assert status["failover_reason"] == "primary_server_unavailable"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])