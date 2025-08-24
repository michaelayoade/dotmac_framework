"""Network Integration service layer for business logic."""

import asyncio
import hashlib
import ipaddress
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from dotmac_isp.shared.base_service import BaseTenantService
from .models import (
    NetworkDevice,
    NetworkInterface,
    NetworkLocation,
    NetworkMetric,
    NetworkAlert,
    DeviceConfiguration,
    NetworkTopology,
    DeviceStatus,
    DeviceType,
    InterfaceStatus,
    AlertSeverity,
    AlertType,
)
from . import schemas
from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
    ServiceError
)


class NetworkDeviceService(BaseTenantService[NetworkDevice, schemas.NetworkDeviceCreate, schemas.NetworkDeviceUpdate, schemas.NetworkDeviceResponse]):
    """Service for network device management."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=NetworkDevice,
            create_schema=schemas.NetworkDeviceCreate,
            update_schema=schemas.NetworkDeviceUpdate,
            response_schema=schemas.NetworkDeviceResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.NetworkDeviceCreate) -> None:
        """Validate business rules for network device creation."""
        # Validate IP address format
        if data.management_ip:
            try:
                ipaddress.ip_address(data.management_ip)
            except ValueError:
                raise ValidationError("Invalid management IP address format")
        
        # Check for duplicate management IP
        if data.management_ip and await self.repository.exists({'management_ip': data.management_ip}):
            raise BusinessRuleError(
                f"Device with management IP {data.management_ip} already exists",
                rule_name="unique_management_ip"
            )
        
        # Validate SNMP configuration
        if data.snmp_enabled and not data.snmp_community:
            raise ValidationError("SNMP community is required when SNMP is enabled")

    async def _validate_update_rules(self, entity: NetworkDevice, data: schemas.NetworkDeviceUpdate) -> None:
        """Validate business rules for network device updates."""
        # Validate IP address if being changed
        if data.management_ip and data.management_ip != entity.management_ip:
            try:
                ipaddress.ip_address(data.management_ip)
            except ValueError:
                raise ValidationError("Invalid management IP address format")
            
            # Check for duplicate
            if await self.repository.exists({'management_ip': data.management_ip}):
                raise BusinessRuleError(
                    f"Device with management IP {data.management_ip} already exists",
                    rule_name="unique_management_ip"
                )

    async def _post_create_hook(self, entity: NetworkDevice, data: schemas.NetworkDeviceCreate) -> None:
        """Initialize device monitoring after creation."""
        try:
            # Start SNMP monitoring if enabled
            if entity.snmp_enabled:
                from .tasks import start_device_monitoring
                start_device_monitoring.delay(str(entity.id), str(self.tenant_id))
                
        except Exception as e:
            self._logger.error(f"Failed to start monitoring for device {entity.id}: {e}")


class NetworkInterfaceService(BaseTenantService[NetworkInterface, schemas.NetworkInterfaceCreate, schemas.NetworkInterfaceUpdate, schemas.NetworkInterfaceResponse]):
    """Service for network interface management."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=NetworkInterface,
            create_schema=schemas.NetworkInterfaceCreate,
            update_schema=schemas.NetworkInterfaceUpdate,
            response_schema=schemas.NetworkInterfaceResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.NetworkInterfaceCreate) -> None:
        """Validate business rules for network interface creation."""
        # Ensure device exists
        if not data.device_id:
            raise ValidationError("Device ID is required for network interface")
        
        # Check for duplicate interface name on same device
        if await self.repository.exists({'device_id': data.device_id, 'name': data.name}):
            raise BusinessRuleError(
                f"Interface '{data.name}' already exists on device",
                rule_name="unique_interface_name_per_device"
            )

    async def _validate_update_rules(self, entity: NetworkInterface, data: schemas.NetworkInterfaceUpdate) -> None:
        """Validate business rules for network interface updates."""
        # Prevent changes to critical interfaces
        if entity.is_critical and data.status == InterfaceStatus.DOWN:
            raise BusinessRuleError(
                "Cannot disable critical network interface",
                rule_name="critical_interface_protection"
            )


class NetworkMetricService(BaseTenantService[NetworkMetric, schemas.NetworkMetricCreate, schemas.NetworkMetricUpdate, schemas.NetworkMetricResponse]):
    """Service for network metrics management."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=NetworkMetric,
            create_schema=schemas.NetworkMetricCreate,
            update_schema=schemas.NetworkMetricUpdate,
            response_schema=schemas.NetworkMetricResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.NetworkMetricCreate) -> None:
        """Validate business rules for network metric creation."""
        if not data.device_id:
            raise ValidationError("Device ID is required for network metric")
        
        # Validate metric value ranges
        if data.cpu_usage and (data.cpu_usage < 0 or data.cpu_usage > 100):
            raise ValidationError("CPU usage must be between 0 and 100")
        
        if data.memory_usage and (data.memory_usage < 0 or data.memory_usage > 100):
            raise ValidationError("Memory usage must be between 0 and 100")


class NetworkAlertService(BaseTenantService[NetworkAlert, schemas.NetworkAlertCreate, schemas.NetworkAlertUpdate, schemas.NetworkAlertResponse]):
    """Service for network alert management."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=NetworkAlert,
            create_schema=schemas.NetworkAlertCreate,
            update_schema=schemas.NetworkAlertUpdate,
            response_schema=schemas.NetworkAlertResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.NetworkAlertCreate) -> None:
        """Validate business rules for network alert creation."""
        if not data.device_id:
            raise ValidationError("Device ID is required for network alert")

    async def _post_create_hook(self, entity: NetworkAlert, data: schemas.NetworkAlertCreate) -> None:
        """Send alert notifications after creation."""
        try:
            if entity.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                from .tasks import send_alert_notification
                send_alert_notification.delay(str(entity.id), str(self.tenant_id))
                
        except Exception as e:
            self._logger.error(f"Failed to send notification for alert {entity.id}: {e}")


# Legacy service for backward compatibility
class NetworkIntegrationService:
    """Legacy network integration service - use individual services instead."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.device_service = NetworkDeviceService(db, tenant_id)
        self.interface_service = NetworkInterfaceService(db, tenant_id)
        self.metric_service = NetworkMetricService(db, tenant_id)
        self.alert_service = NetworkAlertService(db, tenant_id)

    async def create_device(self, device_data: Dict[str, Any]) -> NetworkDevice:
        """Create a new network device."""
        # Validate IP address if provided
        if device_data.get("management_ip"):
            try:
                ipaddress.ip_address(device_data["management_ip"])
            except ValueError:
                raise ValidationError("Invalid management IP address format")

        # Validate SNMP configuration
        if device_data.get("snmp_enabled", True):
            if not device_data.get("snmp_community"):
                device_data["snmp_community"] = "public"  # Default community

            if device_data.get("snmp_port", 161) not in range(1, 65536):
                raise ValidationError("SNMP port must be between 1 and 65535")

        device = self.device_repo.create(device_data)

        # Start monitoring if enabled
        if device_data.get("monitoring_enabled", True):
            await self._setup_device_monitoring(device.id)

        return device

    async def get_device(self, device_id: UUID) -> NetworkDevice:
        """Get device by ID."""
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise NotFoundError(f"Device with ID {device_id} not found")
        return device

    async def get_device_by_hostname(self, hostname: str) -> NetworkDevice:
        """Get device by hostname."""
        device = self.device_repo.get_by_hostname(hostname)
        if not device:
            raise NotFoundError(f"Device with hostname {hostname} not found")
        return device

    async def list_devices(
        self,
        device_type: Optional[DeviceType] = None,
        status: Optional[DeviceStatus] = None,
        location_id: Optional[UUID] = None,
        monitoring_enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[NetworkDevice]:
        """List devices with filtering."""
        return self.device_repo.list_devices(
            device_type=device_type,
            status=status,
            location_id=location_id,
            monitoring_enabled=monitoring_enabled,
            skip=skip,
            limit=limit,
        )

    async def update_device_status(
        self, device_id: UUID, status: DeviceStatus, notes: Optional[str] = None
    ) -> NetworkDevice:
        """Update device status."""
        device = self.device_repo.update_status(device_id, status, notes)
        if not device:
            raise NotFoundError(f"Device with ID {device_id} not found")

        # Create alert for status changes
        if status in [DeviceStatus.FAILED, DeviceStatus.INACTIVE]:
            await self._create_device_alert(
                device_id=device_id,
                alert_type=AlertType.DEVICE_DOWN,
                severity=AlertSeverity.CRITICAL,
                title=f"Device {device.name} is {status.value}",
                message=f"Device {device.name} status changed to {status.value}. {notes or ''}",
            )

        return device

    async def provision_device(
        self, device_id: UUID, configuration: Dict[str, Any]
    ) -> NetworkDevice:
        """Provision a network device with configuration."""
        device = await self.get_device(device_id)

        if device.status != DeviceStatus.PROVISIONING:
            raise ValidationError("Device must be in provisioning status")

        try:
            # Apply configuration
            await self._apply_device_configuration(device, configuration)

            # Test connectivity
            if await self._test_device_connectivity(device):
                # Update status to active
                device = self.device_repo.update_status(
                    device_id, DeviceStatus.ACTIVE, "Device provisioned successfully"
                )

                # Start monitoring
                await self._setup_device_monitoring(device_id)
            else:
                raise ServiceError("Device connectivity test failed")

        except Exception as e:
            # Mark as failed
            self.device_repo.update_status(
                device_id, DeviceStatus.FAILED, f"Provisioning failed: {str(e)}"
            )
            raise ServiceError(f"Device provisioning failed: {str(e)}")

        return device

    async def backup_device_configuration(self, device_id: UUID) -> DeviceConfiguration:
        """Backup device configuration."""
        device = await self.get_device(device_id)

        # Get current configuration from device
        config_data = await self._retrieve_device_configuration(device)

        # Create configuration backup
        config_repo = DeviceConfigurationRepository(self.db, self.tenant_id)
        config = config_repo.create(
            {
                "device_id": device_id,
                "name": f"Backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "version": f"backup_{int(datetime.utcnow().timestamp())}",
                "configuration_data": config_data,
                "configuration_hash": hashlib.sha256(config_data.encode()).hexdigest(),
                "source": "automatic",
                "is_backup": True,
            }
        )

        # Update device backup timestamp
        self.device_repo.backup_configuration(device_id)

        return config

    async def _setup_device_monitoring(self, device_id: UUID) -> None:
        """Setup monitoring for device."""
        # This would integrate with monitoring systems like Prometheus, Zabbix, etc.
        # For now, just mark monitoring as enabled
        pass

    async def _apply_device_configuration(
        self, device: NetworkDevice, configuration: Dict[str, Any]
    ) -> None:
        """Apply configuration to device."""
        # This would use vendor-specific APIs or configuration management tools
        # Like Ansible, NETCONF, SSH, etc.
        pass

    async def _test_device_connectivity(self, device: NetworkDevice) -> bool:
        """Test device connectivity."""
        if not device.management_ip:
            return False

        # Simple ping test (in production would use more sophisticated tests)
        import subprocess

        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "5", str(device.management_ip)],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def _retrieve_device_configuration(self, device: NetworkDevice) -> str:
        """Retrieve current configuration from device."""
        # This would connect to device and retrieve configuration
        # Using SSH, SNMP, API, etc.
        return (
            f"# Configuration for {device.name}\n# Retrieved at {datetime.utcnow()}\n"
        )

    async def _create_device_alert(
        self,
        device_id: UUID,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
    ) -> NetworkAlert:
        """Create device alert."""
        return self.alert_repo.create(
            {
                "device_id": device_id,
                "alert_type": alert_type,
                "severity": severity,
                "title": title,
                "message": message,
            }
        )


class NetworkInterfaceService:
    """Service for network interface management."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.interface_repo = NetworkInterfaceRepository(db, self.tenant_id)
        self.device_repo = NetworkDeviceRepository(db, self.tenant_id)

    async def create_interface(
        self, interface_data: Dict[str, Any]
    ) -> NetworkInterface:
        """Create a new network interface."""
        # Validate device exists
        device = self.device_repo.get_by_id(interface_data["device_id"])
        if not device:
            raise ValidationError("Device not found")

        # Validate IP address if provided
        if interface_data.get("ip_address"):
            try:
                ipaddress.ip_address(interface_data["ip_address"])
            except ValueError:
                raise ValidationError("Invalid IP address format")

        # Validate MAC address format
        if interface_data.get("mac_address"):
            mac = interface_data["mac_address"].replace(":", "").replace("-", "")
            if len(mac) != 12 or not all(c in "0123456789abcdefABCDEF" for c in mac):
                raise ValidationError("Invalid MAC address format")

        return self.interface_repo.create(interface_data)

    async def get_device_interfaces(self, device_id: UUID) -> List[NetworkInterface]:
        """Get all interfaces for a device."""
        return self.interface_repo.list_by_device(device_id)

    async def update_interface_status(
        self,
        interface_id: UUID,
        admin_status: InterfaceStatus,
        operational_status: InterfaceStatus,
    ) -> NetworkInterface:
        """Update interface status."""
        interface = self.interface_repo.update_status(
            interface_id, admin_status, operational_status
        )
        if not interface:
            raise NotFoundError(f"Interface with ID {interface_id} not found")

        # Create alert if interface goes down
        if operational_status == InterfaceStatus.DOWN:
            alert_repo = NetworkAlertRepository(self.db, self.tenant_id)
            alert_repo.create(
                {
                    "device_id": interface.device_id,
                    "interface_id": interface_id,
                    "alert_type": AlertType.INTERFACE_DOWN,
                    "severity": AlertSeverity.HIGH,
                    "title": f"Interface {interface.name} is down",
                    "message": f"Interface {interface.name} on device {interface.device.name} has gone down",
                }
            )

        return interface


class NetworkMonitoringService:
    """Service for network monitoring and metrics."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.metric_repo = NetworkMetricRepository(db, self.tenant_id)
        self.alert_repo = NetworkAlertRepository(db, self.tenant_id)
        self.device_repo = NetworkDeviceRepository(db, self.tenant_id)

    async def collect_device_metrics(self, device_id: UUID) -> List[NetworkMetric]:
        """Collect metrics from a device."""
        device = self.device_repo.get_by_id(device_id)
        if not device or not device.monitoring_enabled:
            raise ValidationError("Device not found or monitoring not enabled")

        # Collect various metrics
        metrics_data = []

        # CPU utilization
        cpu_usage = await self._get_cpu_utilization(device)
        if cpu_usage is not None:
            metrics_data.append(
                {
                    "device_id": device_id,
                    "metric_name": "cpu_utilization",
                    "metric_type": "gauge",
                    "value": cpu_usage,
                    "unit": "percent",
                }
            )

        # Memory utilization
        memory_usage = await self._get_memory_utilization(device)
        if memory_usage is not None:
            metrics_data.append(
                {
                    "device_id": device_id,
                    "metric_name": "memory_utilization",
                    "metric_type": "gauge",
                    "value": memory_usage,
                    "unit": "percent",
                }
            )

        # Temperature
        temperature = await self._get_device_temperature(device)
        if temperature is not None:
            metrics_data.append(
                {
                    "device_id": device_id,
                    "metric_name": "temperature",
                    "metric_type": "gauge",
                    "value": temperature,
                    "unit": "celsius",
                }
            )

        # Create metrics in bulk
        metrics = self.metric_repo.create_bulk(metrics_data)

        # Check for threshold violations and create alerts
        await self._check_metric_thresholds(device_id, metrics)

        return metrics

    async def get_device_metrics(
        self, device_id: UUID, metric_names: Optional[List[str]] = None, hours: int = 24
    ) -> List[NetworkMetric]:
        """Get recent metrics for a device."""
        return self.metric_repo.get_latest_metrics(device_id, metric_names, hours)

    async def _get_cpu_utilization(self, device: NetworkDevice) -> Optional[float]:
        """Get CPU utilization from device."""
        # This would use SNMP, SSH, or device API
        # For now, return a mock value
        import random

        return random.uniform(10, 90)

    async def _get_memory_utilization(self, device: NetworkDevice) -> Optional[float]:
        """Get memory utilization from device."""
        # This would use SNMP, SSH, or device API
        import random

        return random.uniform(20, 80)

    async def _get_device_temperature(self, device: NetworkDevice) -> Optional[float]:
        """Get device temperature."""
        # This would use SNMP or device API
        import random

        return random.uniform(35, 65)

    async def _check_metric_thresholds(
        self, device_id: UUID, metrics: List[NetworkMetric]
    ) -> None:
        """Check metrics against thresholds and create alerts."""
        threshold_rules = {
            "cpu_utilization": {"warning": 80, "critical": 95},
            "memory_utilization": {"warning": 85, "critical": 95},
            "temperature": {"warning": 60, "critical": 70},
        }

        for metric in metrics:
            if metric.metric_name in threshold_rules:
                thresholds = threshold_rules[metric.metric_name]

                if metric.value >= thresholds["critical"]:
                    severity = AlertSeverity.CRITICAL
                elif metric.value >= thresholds["warning"]:
                    severity = AlertSeverity.HIGH
                else:
                    continue

                # Check if similar alert already exists
                existing_alerts = self.alert_repo.list_active_alerts(
                    device_id=device_id,
                    alert_type=(
                        AlertType.HIGH_CPU
                        if metric.metric_name == "cpu_utilization"
                        else (
                            AlertType.HIGH_MEMORY
                            if metric.metric_name == "memory_utilization"
                            else AlertType.HIGH_TEMPERATURE
                        )
                    ),
                )

                if not existing_alerts:
                    self.alert_repo.create(
                        {
                            "device_id": device_id,
                            "alert_type": (
                                AlertType.HIGH_CPU
                                if metric.metric_name == "cpu_utilization"
                                else (
                                    AlertType.HIGH_MEMORY
                                    if metric.metric_name == "memory_utilization"
                                    else AlertType.HIGH_TEMPERATURE
                                )
                            ),
                            "severity": severity,
                            "title": f"High {metric.metric_name.replace('_', ' ').title()}",
                            "message": f"{metric.metric_name.replace('_', ' ').title()} is {metric.value}% (threshold: {thresholds['warning']}%)",
                            "metric_name": metric.metric_name,
                            "current_value": metric.value,
                            "threshold_value": thresholds["warning"],
                        }
                    )


class NetworkTopologyService:
    """Service for network topology management."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.topology_repo = NetworkTopologyRepository(db, self.tenant_id)
        self.device_repo = NetworkDeviceRepository(db, self.tenant_id)

    async def create_connection(
        self, connection_data: Dict[str, Any]
    ) -> NetworkTopology:
        """Create a topology connection between devices."""
        # Validate devices exist
        parent_device = self.device_repo.get_by_id(connection_data["parent_device_id"])
        child_device = self.device_repo.get_by_id(connection_data["child_device_id"])

        if not parent_device or not child_device:
            raise ValidationError("One or both devices not found")

        return self.topology_repo.create(connection_data)

    async def get_device_connections(self, device_id: UUID) -> List[NetworkTopology]:
        """Get all connections for a device."""
        return self.topology_repo.get_device_connections(device_id)

    async def get_network_topology(self) -> Dict[str, Any]:
        """Get complete network topology as a graph structure."""
        connections = self.topology_repo.get_topology_map()
        devices = self.device_repo.list_devices(limit=1000)  # Get all devices

        # Build graph structure
        nodes = []
        edges = []

        for device in devices:
            nodes.append(
                {
                    "id": str(device.id),
                    "name": device.name,
                    "type": device.device_type.value,
                    "status": device.status.value,
                    "management_ip": (
                        str(device.management_ip) if device.management_ip else None
                    ),
                }
            )

        for connection in connections:
            edges.append(
                {
                    "source": str(connection.parent_device_id),
                    "target": str(connection.child_device_id),
                    "type": connection.connection_type,
                    "bandwidth": connection.bandwidth_mbps,
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "last_updated": datetime.utcnow().isoformat(),
        }


class NetworkIntegrationService:
    """Main service orchestrating network integration operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.device_service = NetworkDeviceService(db, tenant_id)
        self.interface_service = NetworkInterfaceService(db, tenant_id)
        self.monitoring_service = NetworkMonitoringService(db, tenant_id)
        self.topology_service = NetworkTopologyService(db, tenant_id)
        self.alert_repo = NetworkAlertRepository(db, UUID(tenant_id))

    async def provision_network_device(
        self, device_data: schemas.NetworkDeviceCreate
    ) -> NetworkDevice:
        """Provision a complete network device with interfaces."""
        # Create device
        device = await self.device_service.create_device(device_data.dict())

        # Auto-discover interfaces if device is reachable
        if device.management_ip and device.snmp_enabled:
            try:
                await self._discover_device_interfaces(device.id)
            except Exception as e:
                # Log error but don't fail provisioning
                pass

        return device

    async def get_network_health_summary(self) -> Dict[str, Any]:
        """Get network health summary."""
        # Get device counts by status
        devices = await self.device_service.list_devices(limit=1000)
        device_status_counts = {}
        for status in DeviceStatus:
            device_status_counts[status.value] = len(
                [d for d in devices if d.status == status]
            )

        # Get active alerts by severity
        active_alerts = self.alert_repo.list_active_alerts(limit=1000)
        alert_severity_counts = {}
        for severity in AlertSeverity:
            alert_severity_counts[severity.value] = len(
                [a for a in active_alerts if a.severity == severity]
            )

        # Calculate uptime percentage (mock for now)
        total_devices = len(devices)
        active_devices = len([d for d in devices if d.status == DeviceStatus.ACTIVE])
        uptime_percentage = (
            (active_devices / total_devices * 100) if total_devices > 0 else 0
        )

        return {
            "device_counts": device_status_counts,
            "alert_counts": alert_severity_counts,
            "network_uptime_percentage": round(uptime_percentage, 2),
            "total_devices": total_devices,
            "total_active_alerts": len(active_alerts),
            "last_updated": datetime.utcnow().isoformat(),
        }

    async def _discover_device_interfaces(
        self, device_id: UUID
    ) -> List[NetworkInterface]:
        """Auto-discover device interfaces via SNMP."""
        # This would use SNMP to discover interfaces
        # For now, create some standard interfaces based on device type
        device = await self.device_service.get_device(device_id)
        interfaces = []

        # Create standard interfaces based on device type
        if device.device_type == DeviceType.ROUTER:
            interface_names = [
                "GigabitEthernet0/0",
                "GigabitEthernet0/1",
                "Serial0/0/0",
            ]
        elif device.device_type == DeviceType.SWITCH:
            interface_names = [f"FastEthernet0/{i}" for i in range(1, 25)]
        elif device.device_type == DeviceType.ACCESS_POINT:
            interface_names = ["wlan0", "eth0"]
        else:
            interface_names = ["eth0"]

        for i, name in enumerate(interface_names):
            interface_data = {
                "device_id": device_id,
                "name": name,
                "interface_type": "ethernet",
                "interface_index": i + 1,
            }

            try:
                interface = await self.interface_service.create_interface(
                    interface_data
                )
                interfaces.append(interface)
            except Exception:
                # Skip if interface creation fails
                continue

        return interfaces
