"""
Comprehensive Device Management tests for lifecycle and automation workflows.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.mark.asyncio
class TestDeviceManagementComprehensive:
    """Comprehensive tests for device management and automation workflows."""

    @pytest.fixture
    def device_inventory_data(self):
        """Sample device inventory data."""
        return [
            {
                "device_id": "router-001",
                "hostname": "core-router-1",
                "ip_address": "192.168.1.1",
                "device_type": "router",
                "vendor": "cisco",
                "model": "ISR4321",
                "os_version": "16.09.04",
                "location": "datacenter-1",
                "status": "active",
                "last_seen": datetime.now(timezone.utc),
                "credentials": {
                    "username": "admin",
                    "password_hash": "hashed_password",
                    "enable_password": "enable_pass"
                }
            },
            {
                "device_id": "switch-001",
                "hostname": "access-switch-1",
                "ip_address": "192.168.1.2",
                "device_type": "switch",
                "vendor": "cisco",
                "model": "C2960X-48TS",
                "os_version": "15.2(4)E7",
                "location": "floor-1",
                "status": "active",
                "last_seen": datetime.now(timezone.utc) - timedelta(minutes=5),
                "credentials": {
                    "username": "admin",
                    "password_hash": "hashed_password"
                }
            }
        ]

    @pytest.fixture
    def configuration_templates(self):
        """Sample configuration templates."""
        return {
            "customer_router": """
hostname {{ hostname }}
!
interface {{ wan_interface }}
 description WAN to {{ isp_name }}
 ip address {{ wan_ip }} {{ wan_mask }}
 no shutdown
!
interface {{ lan_interface }}
 description LAN - Customer Network
 ip address {{ lan_ip }} {{ lan_mask }}
 no shutdown
!
router ospf 1
 network {{ lan_network }} {{ lan_wildcard }} area 0
!
""",
            "vlan_config": """
vlan {{ vlan_id }}
 name {{ vlan_name }}
!
interface vlan{{ vlan_id }}
 description {{ vlan_description }}
 ip address {{ vlan_ip }} {{ vlan_mask }}
!
"""
        }

    async def test_device_inventory_management(self, device_inventory_data):
        """Test device inventory CRUD operations."""
        try:
            from dotmac.networking.automation.inventory.device_inventory import (
                DeviceInventory,
            )
        except ImportError:
            pytest.skip("Device inventory not available")

        inventory = DeviceInventory()

        # Test adding devices
        for device in device_inventory_data:
            await inventory.add_device(device)

        # Test getting all devices
        all_devices = await inventory.get_all_devices()
        assert len(all_devices) == 2

        # Test getting device by ID
        router = await inventory.get_device("router-001")
        assert router["hostname"] == "core-router-1"
        assert router["vendor"] == "cisco"

        # Test device search/filtering
        cisco_devices = await inventory.search_devices(vendor="cisco")
        assert len(cisco_devices) == 2

        routers = await inventory.search_devices(device_type="router")
        assert len(routers) == 1
        assert routers[0]["device_id"] == "router-001"

        # Test device update
        await inventory.update_device("router-001", {"status": "maintenance"})
        updated_router = await inventory.get_device("router-001")
        assert updated_router["status"] == "maintenance"

        # Test device deletion
        await inventory.remove_device("switch-001")
        remaining_devices = await inventory.get_all_devices()
        assert len(remaining_devices) == 1

    async def test_configuration_template_management(self, configuration_templates):
        """Test configuration template management and rendering."""
        try:
            from dotmac.networking.automation.templates.template_manager import (
                TemplateManager,
            )
        except ImportError:
            pytest.skip("Template manager not available")

        template_manager = TemplateManager()

        # Test template storage
        for name, template in configuration_templates.items():
            await template_manager.save_template(name, template)

        # Test template retrieval
        customer_template = await template_manager.get_template("customer_router")
        assert "hostname {{ hostname }}" in customer_template

        # Test template rendering
        variables = {
            "hostname": "customer-router-1",
            "wan_interface": "GigabitEthernet0/1",
            "isp_name": "ISP-Corp",
            "wan_ip": "203.0.113.10",
            "wan_mask": "255.255.255.252",
            "lan_interface": "GigabitEthernet0/2",
            "lan_ip": "192.168.100.1",
            "lan_mask": "255.255.255.0",
            "lan_network": "192.168.100.0",
            "lan_wildcard": "0.0.0.255"
        }

        rendered_config = await template_manager.render_template("customer_router", variables)

        assert "hostname customer-router-1" in rendered_config
        assert "ip address 203.0.113.10 255.255.255.252" in rendered_config
        assert "network 192.168.100.0 0.0.0.255 area 0" in rendered_config

        # Test template validation
        is_valid = await template_manager.validate_template("customer_router", variables)
        assert is_valid == True

        # Test template listing
        all_templates = await template_manager.list_templates()
        assert "customer_router" in all_templates
        assert "vlan_config" in all_templates

    async def test_device_lifecycle_workflows(self, device_inventory_data):
        """Test complete device lifecycle management workflows."""
        try:
            from dotmac.networking.automation.workflows.device_lifecycle import (
                DeviceLifecycleManager,
            )
        except ImportError:
            pytest.skip("Device lifecycle manager not available")

        lifecycle_manager = DeviceLifecycleManager()

        # Test device onboarding workflow
        new_device = {
            "hostname": "new-router-1",
            "ip_address": "192.168.1.10",
            "device_type": "router",
            "vendor": "cisco",
            "credentials": {"username": "admin", "password": "temp123"}
        }

        onboarding_result = await lifecycle_manager.onboard_device(new_device)

        assert onboarding_result["status"] == "success"
        assert onboarding_result["device_id"] is not None
        assert onboarding_result["discovery_data"]["vendor"] == "cisco"

        # Test device provisioning workflow
        provisioning_config = {
            "template": "customer_router",
            "variables": {
                "hostname": "provisioned-router",
                "wan_interface": "GigE0/1",
                "lan_interface": "GigE0/2"
            }
        }

        provisioning_result = await lifecycle_manager.provision_device(
            onboarding_result["device_id"],
            provisioning_config
        )

        assert provisioning_result["status"] == "success"
        assert "configuration_applied" in provisioning_result

        # Test device health monitoring workflow
        health_check = await lifecycle_manager.check_device_health(onboarding_result["device_id"])

        assert "connectivity" in health_check
        assert "system_metrics" in health_check
        assert "interface_status" in health_check

        # Test device retirement workflow
        retirement_result = await lifecycle_manager.retire_device(
            onboarding_result["device_id"],
            reason="end_of_life"
        )

        assert retirement_result["status"] == "success"
        assert retirement_result["backup_created"] == True

    async def test_bulk_device_operations(self, device_inventory_data):
        """Test bulk operations across multiple devices."""
        try:
            from dotmac.networking.automation.bulk.bulk_operations import (
                BulkOperationsManager,
            )
        except ImportError:
            pytest.skip("Bulk operations manager not available")

        bulk_manager = BulkOperationsManager()

        device_targets = [
            {"device_id": "router-001", "ip_address": "192.168.1.1"},
            {"device_id": "switch-001", "ip_address": "192.168.1.2"}
        ]

        # Test bulk configuration deployment
        bulk_config = {
            "template": "security_hardening",
            "variables": {
                "admin_user": "secadmin",
                "banner_text": "Authorized access only",
                "timeout_minutes": 5
            }
        }

        deployment_results = await bulk_manager.deploy_configuration(device_targets, bulk_config)

        assert len(deployment_results) == 2
        assert all(result["status"] in ["success", "failed"] for result in deployment_results)

        # Test bulk firmware upgrade
        firmware_config = {
            "firmware_url": "tftp://192.168.1.100/firmware/c2960x-universalk9-mz.152-4.E7.bin",
            "reboot_required": True,
            "backup_config": True
        }

        upgrade_results = await bulk_manager.upgrade_firmware(device_targets, firmware_config)

        assert len(upgrade_results) == 2
        assert all("backup_id" in result for result in upgrade_results if result["status"] == "success")

        # Test bulk health check
        health_results = await bulk_manager.bulk_health_check(device_targets)

        assert len(health_results) == 2
        assert all("device_id" in result for result in health_results)
        assert all("health_status" in result for result in health_results)

    async def test_configuration_compliance_checking(self):
        """Test configuration compliance and policy enforcement."""
        try:
            from dotmac.networking.automation.compliance.compliance_checker import (
                ComplianceChecker,
            )
        except ImportError:
            pytest.skip("Compliance checker not available")

        compliance_checker = ComplianceChecker()

        # Define compliance policies
        security_policies = [
            {
                "name": "Strong Authentication",
                "rule": "aaa new-model",
                "required": True,
                "category": "security"
            },
            {
                "name": "SSH Version 2",
                "rule": "ip ssh version 2",
                "required": True,
                "category": "security"
            },
            {
                "name": "No HTTP Server",
                "rule": "no ip http server",
                "required": True,
                "category": "security"
            }
        ]

        # Mock device configuration
        device_config = """
hostname test-router
!
aaa new-model
aaa authentication login default local
!
ip ssh version 2
no ip http server
no ip http secure-server
!
interface GigabitEthernet0/1
 ip address 192.168.1.1 255.255.255.0
!
"""

        # Test compliance checking
        compliance_result = await compliance_checker.check_compliance(device_config, security_policies)

        assert compliance_result["overall_compliance"] == True
        assert compliance_result["total_policies"] == 3
        assert compliance_result["passed_policies"] == 3
        assert compliance_result["failed_policies"] == 0

        # Test with non-compliant configuration
        non_compliant_config = """
hostname test-router
!
interface GigabitEthernet0/1
 ip address 192.168.1.1 255.255.255.0
!
ip http server
!
"""

        non_compliant_result = await compliance_checker.check_compliance(non_compliant_config, security_policies)

        assert non_compliant_result["overall_compliance"] == False
        assert non_compliant_result["failed_policies"] > 0

    async def test_device_backup_and_restore(self):
        """Test device configuration backup and restore operations."""
        try:
            from dotmac.networking.automation.backup.backup_scheduler import (
                BackupScheduler,
            )
        except ImportError:
            pytest.skip("Backup scheduler not available")

        backup_scheduler = BackupScheduler()

        # Test scheduled backup creation
        backup_job = {
            "schedule": "0 2 * * *",  # Daily at 2 AM
            "devices": ["router-001", "switch-001"],
            "retention_days": 30,
            "storage_location": "/backups/"
        }

        job_id = await backup_scheduler.schedule_backup(backup_job)
        assert job_id is not None

        # Test immediate backup
        backup_result = await backup_scheduler.create_backup_now("router-001")

        assert backup_result["status"] == "success"
        assert backup_result["backup_id"] is not None
        assert backup_result["size_bytes"] > 0

        # Test backup listing
        backups = await backup_scheduler.list_backups("router-001", limit=10)

        assert len(backups) >= 1
        assert all("backup_id" in backup for backup in backups)
        assert all("created_at" in backup for backup in backups)

        # Test backup restoration
        restore_result = await backup_scheduler.restore_backup(
            "router-001",
            backup_result["backup_id"]
        )

        assert restore_result["status"] == "success"
        assert restore_result["configuration_applied"] == True

    async def test_device_monitoring_integration(self):
        """Test device management integration with monitoring systems."""
        try:
            from dotmac.networking.automation.monitoring.device_monitor import (
                DeviceMonitor,
            )
        except ImportError:
            pytest.skip("Device monitor not available")

        monitor = DeviceMonitor()

        # Test device connectivity monitoring
        connectivity_status = await monitor.check_connectivity(
            ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        )

        assert len(connectivity_status) == 3
        assert all("host" in status for status in connectivity_status)
        assert all("reachable" in status for status in connectivity_status)

        # Test performance metrics collection
        performance_metrics = await monitor.collect_performance_metrics("192.168.1.1")

        assert "cpu_utilization" in performance_metrics
        assert "memory_utilization" in performance_metrics
        assert "interface_utilization" in performance_metrics

        # Test alerting integration
        alert_conditions = [
            {"metric": "cpu_utilization", "threshold": 80, "operator": ">"},
            {"metric": "memory_utilization", "threshold": 90, "operator": ">"}
        ]

        alerts = await monitor.evaluate_alerts("192.168.1.1", alert_conditions)

        assert isinstance(alerts, list)
        # May have alerts based on mock data

    async def test_network_change_management(self):
        """Test network change management and approval workflows."""
        try:
            from dotmac.networking.automation.change.change_manager import ChangeManager
        except ImportError:
            pytest.skip("Change manager not available")

        change_manager = ChangeManager()

        # Test change request creation
        change_request = {
            "title": "Update OSPF Configuration",
            "description": "Update OSPF area configuration on core routers",
            "devices": ["router-001", "router-002"],
            "configuration_changes": {
                "template": "ospf_update",
                "variables": {"area": 1, "network": "10.0.0.0/16"}
            },
            "maintenance_window": {
                "start": datetime.now() + timedelta(hours=24),
                "duration_minutes": 60
            },
            "rollback_plan": "Revert to previous OSPF configuration",
            "risk_level": "medium"
        }

        change_id = await change_manager.create_change_request(change_request)
        assert change_id is not None

        # Test change approval workflow
        approval_result = await change_manager.approve_change(
            change_id,
            approved_by="network_manager",
            approval_notes="Approved for next maintenance window"
        )

        assert approval_result["status"] == "approved"

        # Test change execution
        execution_result = await change_manager.execute_change(change_id)

        assert execution_result["status"] in ["success", "partial_success", "failed"]
        assert "execution_log" in execution_result

        # Test rollback capability
        if execution_result["status"] != "success":
            rollback_result = await change_manager.rollback_change(change_id)
            assert rollback_result["status"] == "success"

    async def test_device_discovery_automation(self):
        """Test automated device discovery and inventory population."""
        try:
            from dotmac.networking.automation.discovery.network_scanner import (
                NetworkScanner,
            )
        except ImportError:
            pytest.skip("Network scanner not available")

        scanner = NetworkScanner()

        # Test network range scanning
        scan_results = await scanner.scan_network_range("192.168.1.0/24")

        assert len(scan_results) > 0
        assert all("ip_address" in device for device in scan_results)
        assert all("reachable" in device for device in scan_results)

        # Test device identification
        reachable_devices = [d for d in scan_results if d["reachable"]]

        for device in reachable_devices[:3]:  # Test first 3 devices
            device_info = await scanner.identify_device(device["ip_address"])

            assert "vendor" in device_info
            assert "device_type" in device_info
            assert device_info["discovery_method"] in ["snmp", "ssh", "http"]

        # Test auto-inventory population
        inventory_updates = await scanner.populate_inventory(scan_results)

        assert len(inventory_updates) >= len(reachable_devices)
        assert all("device_id" in update for update in inventory_updates)


# Mock implementations for device management classes
mock_classes = {
    'DeviceInventory': {
        'add_device': lambda self, device: device.update({"created_at": datetime.now()}),
        'get_all_devices': lambda self: getattr(self, '_devices', []),
        'get_device': lambda self, device_id: next((d for d in getattr(self, '_devices', []) if d.get('device_id') == device_id), None),
        'search_devices': lambda self, **filters: [d for d in getattr(self, '_devices', []) if all(d.get(k) == v for k, v in filters.items())],
        'update_device': lambda self, device_id, updates: None,
        'remove_device': lambda self, device_id: setattr(self, '_devices', [d for d in getattr(self, '_devices', []) if d.get('device_id') != device_id])
    },
    'TemplateManager': {
        'save_template': lambda self, name, template: getattr(self, '_templates', {}).update({name: template}) or setattr(self, '_templates', getattr(self, '_templates', {name: template})),
        'get_template': lambda self, name: getattr(self, '_templates', {}).get(name),
        'render_template': lambda self, name, variables: self.mock_render(getattr(self, '_templates', {}).get(name, ''), variables),
        'validate_template': lambda self, name, variables: True,
        'list_templates': lambda self: list(getattr(self, '_templates', {}).keys())
    },
    'DeviceLifecycleManager': {
        'onboard_device': lambda self, device: {"status": "success", "device_id": f"dev-{len(str(device))}", "discovery_data": {"vendor": device.get("vendor", "unknown")}},
        'provision_device': lambda self, device_id, config: {"status": "success", "configuration_applied": True},
        'check_device_health': lambda self, device_id: {"connectivity": True, "system_metrics": {"cpu": 45}, "interface_status": "up"},
        'retire_device': lambda self, device_id, reason: {"status": "success", "backup_created": True}
    },
    'BulkOperationsManager': {
        'deploy_configuration': lambda self, devices, config: [{"device_id": d["device_id"], "status": "success"} for d in devices],
        'upgrade_firmware': lambda self, devices, config: [{"device_id": d["device_id"], "status": "success", "backup_id": f"backup-{d['device_id']}"} for d in devices],
        'bulk_health_check': lambda self, devices: [{"device_id": d["device_id"], "health_status": "healthy"} for d in devices]
    },
    'ComplianceChecker': {
        'check_compliance': lambda self, config, policies: {
            "overall_compliance": all(policy["rule"] in config for policy in policies if policy["required"]),
            "total_policies": len(policies),
            "passed_policies": sum(1 for p in policies if p["rule"] in config),
            "failed_policies": sum(1 for p in policies if p["rule"] not in config)
        }
    },
    'BackupScheduler': {
        'schedule_backup': lambda self, job: f"job-{hash(str(job)) % 10000}",
        'create_backup_now': lambda self, device_id: {"status": "success", "backup_id": f"backup-{device_id}-{datetime.now().strftime('%Y%m%d')}", "size_bytes": 4096},
        'list_backups': lambda self, device_id, limit: [{"backup_id": f"backup-{device_id}-{i}", "created_at": datetime.now() - timedelta(days=i)} for i in range(min(limit, 5))],
        'restore_backup': lambda self, device_id, backup_id: {"status": "success", "configuration_applied": True}
    },
    'DeviceMonitor': {
        'check_connectivity': lambda self, hosts: [{"host": host, "reachable": True, "response_time": 1.2} for host in hosts],
        'collect_performance_metrics': lambda self, host: {"cpu_utilization": 45, "memory_utilization": 60, "interface_utilization": {"GigE0/1": 25}},
        'evaluate_alerts': lambda self, host, conditions: []
    },
    'ChangeManager': {
        'create_change_request': lambda self, request: f"change-{hash(str(request)) % 10000}",
        'approve_change': lambda self, change_id, approved_by, approval_notes: {"status": "approved"},
        'execute_change': lambda self, change_id: {"status": "success", "execution_log": ["Step 1: Success", "Step 2: Success"]},
        'rollback_change': lambda self, change_id: {"status": "success"}
    },
    'NetworkScanner': {
        'scan_network_range': lambda self, cidr: [{"ip_address": f"192.168.1.{i}", "reachable": i % 3 != 0} for i in range(1, 11)],
        'identify_device': lambda self, ip: {"vendor": "cisco", "device_type": "router", "discovery_method": "snmp"},
        'populate_inventory': lambda self, scan_results: [{"device_id": f"auto-{r['ip_address']}"} for r in scan_results if r["reachable"]]
    }
}

# Special handling for TemplateManager mock render method
def mock_render(template, variables):
    """Mock Jinja2-like template rendering."""
    if not template:
        return ""

    result = template
    # Simple variable substitution
    for key, value in variables.items():
        result = result.replace(f"{{{{ {key} }}}}", str(value))
    return result

# Create and register mock classes
for class_name, methods in mock_classes.items():
    if class_name not in globals():
        class_attrs = {'__init__': lambda self: None}

        for method_name, method_impl in methods.items():
            if method_name == 'render_template':
                # Special case for template rendering
                async def render_method(self, name, variables):
                    template = getattr(self, '_templates', {}).get(name, '')
                    return mock_render(template, variables)
                class_attrs[method_name] = render_method
            else:
                # Convert sync methods to async
                def make_async_method(impl):
                    async def async_method(self, *args, **kwargs):
                        # Initialize storage if needed
                        if not hasattr(self, '_devices'):
                            self._devices = []
                        if not hasattr(self, '_templates'):
                            self._templates = {}
                        return impl(self, *args, **kwargs)
                    return async_method

                class_attrs[method_name] = make_async_method(method_impl)

        mock_class = type(f'Mock{class_name}', (), class_attrs)
        globals()[class_name] = mock_class
