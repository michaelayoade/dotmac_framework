"""
TR-069 CWMP SDK - CPE WAN Management Protocol for device management
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import NetworkingError


class TR069CWMPService:
    """In-memory service for TR-069 CWMP operations."""

    def __init__(self):
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._parameters: Dict[str, Dict[str, Any]] = {}  # device_id -> parameters
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._events: List[Dict[str, Any]] = []

    async def register_device(self, **kwargs) -> Dict[str, Any]:
        """Register TR-069 CPE device."""
        device_id = kwargs.get("device_id") or str(uuid4())

        if device_id in self._devices:
            raise NetworkingError(f"Device already registered: {device_id}")

        device = {
            "device_id": device_id,
            "serial_number": kwargs.get("serial_number", ""),
            "product_class": kwargs.get("product_class", ""),
            "manufacturer": kwargs.get("manufacturer", ""),
            "model_name": kwargs.get("model_name", ""),
            "software_version": kwargs.get("software_version", ""),
            "hardware_version": kwargs.get("hardware_version", ""),
            "connection_url": kwargs.get("connection_url", ""),
            "username": kwargs.get("username", ""),
            "password": kwargs.get("password", ""),
            "periodic_inform_interval": kwargs.get("periodic_inform_interval", 3600),
            "last_inform": None,
            "status": kwargs.get("status", "online"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._devices[device_id] = device
        self._parameters[device_id] = {}

        return device

    async def create_session(self, **kwargs) -> Dict[str, Any]:
        """Create CWMP session."""
        session_id = kwargs.get("session_id") or str(uuid4())
        device_id = kwargs["device_id"]

        if device_id not in self._devices:
            raise NetworkingError(f"Device not found: {device_id}")

        session = {
            "session_id": session_id,
            "device_id": device_id,
            "session_type": kwargs.get("session_type", "inform"),
            "hold_requests": kwargs.get("hold_requests", False),
            "max_envelopes": kwargs.get("max_envelopes", 1),
            "retry_count": kwargs.get("retry_count", 3),
            "status": "active",
            "start_time": utc_now().isoformat(),
            "last_activity": utc_now().isoformat(),
        }

        self._sessions[session_id] = session
        return session

    async def set_parameter_values(
        self, device_id: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set parameter values on device."""
        if device_id not in self._devices:
            raise NetworkingError(f"Device not found: {device_id}")

        task_id = str(uuid4())
        task = {
            "task_id": task_id,
            "device_id": device_id,
            "task_type": "SetParameterValues",
            "parameters": parameters,
            "status": "pending",
            "created_at": utc_now().isoformat(),
            "retry_count": 0,
            "max_retries": 3,
        }

        self._tasks[task_id] = task

        # Simulate parameter setting (in real implementation, this would be sent to device)
        for param_name, param_value in parameters.items():
            self._parameters[device_id][param_name] = {
                "name": param_name,
                "value": param_value,
                "type": type(param_value).__name__,
                "writable": True,
                "last_updated": utc_now().isoformat(),
            }

        task["status"] = "completed"
        task["completed_at"] = utc_now().isoformat()

        return task

    async def get_parameter_values(
        self, device_id: str, parameter_names: List[str]
    ) -> Dict[str, Any]:
        """Get parameter values from device."""
        if device_id not in self._devices:
            raise NetworkingError(f"Device not found: {device_id}")

        device_params = self._parameters.get(device_id, {})

        result = {}
        for param_name in parameter_names:
            if param_name in device_params:
                result[param_name] = device_params[param_name]["value"]
            else:
                result[param_name] = None

        return result

    async def reboot_device(self, device_id: str) -> Dict[str, Any]:
        """Reboot TR-069 device."""
        if device_id not in self._devices:
            raise NetworkingError(f"Device not found: {device_id}")

        task_id = str(uuid4())
        task = {
            "task_id": task_id,
            "device_id": device_id,
            "task_type": "Reboot",
            "status": "pending",
            "created_at": utc_now().isoformat(),
        }

        self._tasks[task_id] = task

        # Simulate reboot
        self._devices[device_id]["status"] = "rebooting"
        task["status"] = "completed"
        task["completed_at"] = utc_now().isoformat()

        return task

    async def factory_reset(self, device_id: str) -> Dict[str, Any]:
        """Factory reset TR-069 device."""
        if device_id not in self._devices:
            raise NetworkingError(f"Device not found: {device_id}")

        task_id = str(uuid4())
        task = {
            "task_id": task_id,
            "device_id": device_id,
            "task_type": "FactoryReset",
            "status": "pending",
            "created_at": utc_now().isoformat(),
        }

        self._tasks[task_id] = task

        # Simulate factory reset - clear parameters
        self._parameters[device_id] = {}
        self._devices[device_id]["status"] = "factory_reset"
        task["status"] = "completed"
        task["completed_at"] = utc_now().isoformat()

        return task


class TR069CWMPSDK:
    """Minimal, reusable SDK for TR-069 CWMP device management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = TR069CWMPService()

    async def register_cpe_device(
        self,
        serial_number: str,
        product_class: str,
        manufacturer: str,
        model_name: str,
        connection_url: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Register TR-069 CPE device."""
        device = await self._service.register_device(
            serial_number=serial_number,
            product_class=product_class,
            manufacturer=manufacturer,
            model_name=model_name,
            connection_url=connection_url,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "device_id": device["device_id"],
            "serial_number": device["serial_number"],
            "product_class": device["product_class"],
            "manufacturer": device["manufacturer"],
            "model_name": device["model_name"],
            "software_version": device["software_version"],
            "hardware_version": device["hardware_version"],
            "connection_url": device["connection_url"],
            "periodic_inform_interval": device["periodic_inform_interval"],
            "status": device["status"],
            "created_at": device["created_at"],
        }

    async def set_device_parameters(
        self, device_id: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set parameter values on TR-069 device."""
        task = await self._service.set_parameter_values(device_id, parameters)

        return {
            "task_id": task["task_id"],
            "device_id": task["device_id"],
            "task_type": task["task_type"],
            "parameters": task["parameters"],
            "status": task["status"],
            "created_at": task["created_at"],
            "completed_at": task.get("completed_at"),
        }

    async def get_device_parameters(
        self, device_id: str, parameter_names: List[str]
    ) -> Dict[str, Any]:
        """Get parameter values from TR-069 device."""
        values = await self._service.get_parameter_values(device_id, parameter_names)

        return {
            "device_id": device_id,
            "parameters": values,
            "retrieved_at": utc_now().isoformat(),
        }

    async def reboot_device(self, device_id: str) -> Dict[str, Any]:
        """Reboot TR-069 device."""
        task = await self._service.reboot_device(device_id)

        return {
            "task_id": task["task_id"],
            "device_id": task["device_id"],
            "task_type": task["task_type"],
            "status": task["status"],
            "created_at": task["created_at"],
            "completed_at": task.get("completed_at"),
        }

    async def factory_reset_device(self, device_id: str) -> Dict[str, Any]:
        """Factory reset TR-069 device."""
        task = await self._service.factory_reset(device_id)

        return {
            "task_id": task["task_id"],
            "device_id": task["device_id"],
            "task_type": task["task_type"],
            "status": task["status"],
            "created_at": task["created_at"],
            "completed_at": task.get("completed_at"),
        }

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get TR-069 device by ID."""
        device = self._service._devices.get(device_id)
        if not device:
            return None

        return {
            "device_id": device["device_id"],
            "serial_number": device["serial_number"],
            "product_class": device["product_class"],
            "manufacturer": device["manufacturer"],
            "model_name": device["model_name"],
            "software_version": device["software_version"],
            "hardware_version": device["hardware_version"],
            "connection_url": device["connection_url"],
            "username": device["username"],
            "periodic_inform_interval": device["periodic_inform_interval"],
            "last_inform": device["last_inform"],
            "status": device["status"],
            "created_at": device["created_at"],
            "updated_at": device["updated_at"],
        }

    async def list_devices(self) -> List[Dict[str, Any]]:
        """List all TR-069 devices."""
        return [
            {
                "device_id": device["device_id"],
                "serial_number": device["serial_number"],
                "product_class": device["product_class"],
                "manufacturer": device["manufacturer"],
                "model_name": device["model_name"],
                "software_version": device["software_version"],
                "status": device["status"],
                "last_inform": device["last_inform"],
            }
            for device in self._service._devices.values()
        ]

    async def get_device_tasks(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all tasks for a device."""
        tasks = [
            task
            for task in self._service._tasks.values()
            if task["device_id"] == device_id
        ]

        return [
            {
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "status": task["status"],
                "created_at": task["created_at"],
                "completed_at": task.get("completed_at"),
                "retry_count": task.get("retry_count", 0),
            }
            for task in sorted(tasks, key=lambda t: t["created_at"], reverse=True)
        ]

    async def configure_wifi_settings(
        self,
        device_id: str,
        ssid: str,
        password: str,
        security_mode: str = "WPA2-PSK",
        channel: int = 6,
    ) -> Dict[str, Any]:
        """Configure WiFi settings on TR-069 device."""
        wifi_params = {
            "Device.WiFi.SSID.1.SSID": ssid,
            "Device.WiFi.AccessPoint.1.Security.ModeEnabled": security_mode,
            "Device.WiFi.AccessPoint.1.Security.KeyPassphrase": password,
            "Device.WiFi.Radio.1.Channel": channel,
            "Device.WiFi.Radio.1.Enable": True,
            "Device.WiFi.SSID.1.Enable": True,
            "Device.WiFi.AccessPoint.1.Enable": True,
        }

        return await self.set_device_parameters(device_id, wifi_params)

    async def configure_wan_settings(
        self,
        device_id: str,
        connection_type: str = "DHCP",
        ip_address: Optional[str] = None,
        subnet_mask: Optional[str] = None,
        gateway: Optional[str] = None,
        dns_servers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Configure WAN settings on TR-069 device."""
        wan_params = {
            "Device.IP.Interface.1.IPv4Address.1.AddressingType": connection_type,
        }

        if connection_type == "Static" and ip_address:
            wan_params.update(
                {
                    "Device.IP.Interface.1.IPv4Address.1.IPAddress": ip_address,
                    "Device.IP.Interface.1.IPv4Address.1.SubnetMask": subnet_mask
                    or "255.255.255.0",
                }
            )

            if gateway:
                wan_params[
                    "Device.Routing.Router.1.IPv4Forwarding.1.GatewayIPAddress"
                ] = gateway

        if dns_servers:
            for i, dns in enumerate(dns_servers[:2], 1):
                wan_params[f"Device.DNS.Client.Server.{i}.DNSServer"] = dns

        return await self.set_device_parameters(device_id, wan_params)
