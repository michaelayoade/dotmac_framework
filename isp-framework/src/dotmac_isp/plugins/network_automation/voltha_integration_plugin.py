"""VOLTHA Integration Plugin for Fiber Network Management."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp
from dataclasses import dataclass

from ...core.secrets.enterprise_secrets_manager import create_enterprise_secrets_manager, SecurityError

from ..core.base import (
    NetworkAutomationPlugin,
    PluginInfo,
    PluginCategory,
    PluginContext,
    PluginConfig,
    PluginAPI,
)
from ..core.exceptions import PluginError, PluginConfigError


@dataclass
class VolthaDevice:
    """VOLTHA device representation."""
    
    device_id: str
    device_type: str
    host_and_port: str
    admin_state: str = "ENABLED"
    oper_status: str = "UNKNOWN"
    connect_status: str = "UNREACHABLE"
    serial_number: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None


@dataclass
class OLTDevice(VolthaDevice):
    """OLT device specific data."""
    
    pon_ports: List[Dict[str, Any]] = None
    flows: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.pon_ports is None:
            self.pon_ports = []
        if self.flows is None:
            self.flows = []


@dataclass
class ONUDevice(VolthaDevice):
    """ONU device specific data."""
    
    parent_device_id: str = None
    pon_port: int = None
    onu_id: int = None
    uni_ports: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.uni_ports is None:
            self.uni_ports = []


class VolthaIntegrationPlugin(NetworkAutomationPlugin):
    """
    VOLTHA Integration Plugin.
    
    Provides integration with VOLTHA (Virtual OLT Hardware Abstraction) for:
    - Fiber network device management
    - OLT (Optical Line Terminal) operations
    - ONU (Optical Network Unit) provisioning and monitoring
    - Flow management for subscriber services
    - Alarm and event handling
    - Performance monitoring and statistics
    """
    
    def __init__(self, config: PluginConfig, api: PluginAPI):
        """Initialize VOLTHA plugin with enterprise secrets management."""
        super().__init__(config, api)
        
        # Initialize enterprise secrets manager
        vault_url = os.getenv("VAULT_URL")
        vault_token = os.getenv("VAULT_TOKEN")
        self.secrets_manager = create_enterprise_secrets_manager(vault_url, vault_token)
        
        # Basic configuration
        self.voltha_host = os.getenv("VOLTHA_HOST", "localhost")
        self.voltha_port = int(os.getenv("VOLTHA_PORT", "50057"))
        self.voltha_rest_port = int(os.getenv("VOLTHA_REST_PORT", "8881"))
        
        # Get secure credentials
        try:
            self.voltha_username = self.secrets_manager.get_secure_secret(
                secret_id="voltha-username",
                env_var="VOLTHA_USERNAME",
                default_error="VOLTHA username not configured"
            )
            self.voltha_password = self.secrets_manager.get_secure_secret(
                secret_id="voltha-password", 
                env_var="VOLTHA_PASSWORD",
                default_error="VOLTHA password not configured"
            )
        except (ValueError, SecurityError) as e:
            raise ValueError(f"CRITICAL SECURITY ERROR: {e}")
            
        self.session = None
        self._logger = None
        self.background_tasks = set()
        
    @property
    def plugin_info(self) -> PluginInfo:
        """Return plugin information."""
        return PluginInfo(
            id="voltha_integration",
            name="VOLTHA Integration",
            version="1.0.0", 
            description="VOLTHA (Virtual OLT Hardware Abstraction) integration for fiber network management",
            author="DotMac ISP Framework",
            category=PluginCategory.NETWORK_AUTOMATION,
            dependencies=["grpc", "protobuf"],
            supports_multi_tenant=True,
            supports_hot_reload=True,
            security_level="elevated",
            permissions_required=[
                "network.fiber.manage", 
                "network.olt.configure",
                "network.onu.provision"
            ],
        )
        
    async def initialize(self) -> None:
        """Initialize VOLTHA plugin."""
        try:
            # Get configuration
            config_data = self.config.config_data or {}
            
            # Override with environment if available
            self.voltha_host = os.getenv("VOLTHA_HOST", config_data.get("voltha_host", "localhost"))
            self.voltha_port = int(os.getenv("VOLTHA_PORT", str(config_data.get("voltha_port", 50057))))
            self.voltha_rest_port = int(os.getenv("VOLTHA_REST_PORT", str(config_data.get("voltha_rest_port", 8881))))
            
            # Re-validate credentials during initialization
            if not hasattr(self, 'voltha_username') or not self.voltha_username:
                try:
                    self.voltha_username = self.secrets_manager.get_secure_secret(
                        secret_id="voltha-username",
                        env_var="VOLTHA_USERNAME", 
                        default_error="VOLTHA username not configured"
                    )
                    self.voltha_password = self.secrets_manager.get_secure_secret(
                        secret_id="voltha-password",
                        env_var="VOLTHA_PASSWORD",
                        default_error="VOLTHA password not configured"
                    )
                except (ValueError, SecurityError) as e:
                    raise ValueError(f"CRITICAL SECURITY ERROR during initialization: {e}")
            
            # Setup logging
            self._logger = logging.getLogger(f"{__name__}.{self.plugin_info.id}")
            
            # Initialize HTTP session for REST API
            self.session = aiohttp.ClientSession()
            
            # Test connectivity
            await self._test_connectivity()
            
            self._logger.info("VOLTHA plugin initialized successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize VOLTHA plugin: {e}")
            raise PluginError(f"VOLTHA plugin initialization failed: {e}")
            
    async def activate(self) -> None:
        """Activate VOLTHA plugin."""
        try:
            # Start background monitoring tasks
            self._start_background_tasks()
            
            self._logger.info("VOLTHA plugin activated")
            
        except Exception as e:
            self._logger.error(f"Failed to activate VOLTHA plugin: {e}")
            raise PluginError(f"VOLTHA plugin activation failed: {e}")
            
    async def deactivate(self) -> None:
        """Deactivate VOLTHA plugin."""
        try:
            # Stop background tasks
            await self._stop_background_tasks()
            
            self._logger.info("VOLTHA plugin deactivated")
            
        except Exception as e:
            self._logger.error(f"Failed to deactivate VOLTHA plugin: {e}")
            
    async def cleanup(self) -> None:
        """Clean up VOLTHA plugin resources."""
        try:
            if self.session:
                await self.session.close()
                
            self._logger.info("VOLTHA plugin cleaned up")
            
        except Exception as e:
            self._logger.error(f"Failed to cleanup VOLTHA plugin: {e}")
            
    # Network Automation Plugin Interface
    
    async def discover_devices(self, context: PluginContext) -> List[Dict[str, Any]]:
        """Discover VOLTHA managed devices."""
        try:
            devices = await self._get_voltha_devices()
            
            discovered_devices = []
            for device in devices:
                discovered_devices.append({
                    "device_id": device.device_id,
                    "device_type": device.device_type,
                    "host_and_port": device.host_and_port,
                    "admin_state": device.admin_state,
                    "oper_status": device.oper_status,
                    "connect_status": device.connect_status,
                    "serial_number": device.serial_number,
                    "vendor": device.vendor,
                    "model": device.model,
                    "firmware_version": device.firmware_version,
                    "discovered_at": datetime.utcnow().isoformat(),
                })
                
            return discovered_devices
            
        except Exception as e:
            self._logger.error(f"Failed to discover VOLTHA devices: {e}")
            raise PluginError(f"Device discovery failed: {e}")
            
    async def configure_device(
        self, device_id: str, config: Dict[str, Any], context: PluginContext
    ) -> bool:
        """Configure VOLTHA device."""
        try:
            device_type = config.get("device_type", "openolt")
            
            if device_type == "openolt":
                # Configure OLT device
                success = await self._configure_olt_device(device_id, config)
            elif device_type == "brcm_openonu_adapter":
                # Configure ONU device  
                success = await self._configure_onu_device(device_id, config)
            else:
                raise PluginError(f"Unsupported device type: {device_type}")
                
            if success:
                self._logger.info(f"Successfully configured VOLTHA device: {device_id}")
                
            return success
            
        except Exception as e:
            self._logger.error(f"Failed to configure VOLTHA device {device_id}: {e}")
            return False
            
    async def get_device_status(
        self, device_id: str, context: PluginContext
    ) -> Dict[str, Any]:
        """Get VOLTHA device status."""
        try:
            device = await self._get_voltha_device(device_id)
            if not device:
                return {"status": "not_found", "error": "Device not found"}
                
            # Get additional status information
            ports = await self._get_device_ports(device_id)
            flows = await self._get_device_flows(device_id)
            alarms = await self._get_device_alarms(device_id)
            
            return {
                "status": device.oper_status.lower(),
                "admin_state": device.admin_state.lower(), 
                "connect_status": device.connect_status.lower(),
                "device_type": device.device_type,
                "serial_number": device.serial_number,
                "vendor": device.vendor,
                "model": device.model,
                "firmware_version": device.firmware_version,
                "port_count": len(ports),
                "flow_count": len(flows),
                "active_alarms": len(alarms),
                "last_checked": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            self._logger.error(f"Failed to get status for VOLTHA device {device_id}: {e}")
            return {"status": "error", "error": str(e)}
            
    # VOLTHA Specific Methods
    
    async def provision_olt(
        self, 
        host_and_port: str,
        device_type: str = "openolt",
        context: PluginContext = None
    ) -> Dict[str, Any]:
        """
        Provision new OLT device in VOLTHA.
        
        Args:
            host_and_port: OLT device address (e.g., "192.168.1.10:9191")
            device_type: Device adapter type
            context: Plugin context
            
        Returns:
            Provisioning result
        """
        try:
            device_data = {
                "type": device_type,
                "host_and_port": host_and_port,
                "admin_state": "PREPROVISIONED"
            }
            
            device_id = await self._create_voltha_device(device_data)
            
            if device_id:
                # Enable the device
                await self._enable_voltha_device(device_id)
                
                self._logger.info(f"Successfully provisioned OLT device: {device_id}")
                
                return {
                    "device_id": device_id,
                    "status": "provisioned",
                    "host_and_port": host_and_port,
                    "device_type": device_type,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
        except Exception as e:
            self._logger.error(f"Failed to provision OLT {host_and_port}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "host_and_port": host_and_port,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    async def provision_onu(
        self,
        parent_device_id: str,
        pon_port: int,
        onu_id: int,
        serial_number: str,
        context: PluginContext = None
    ) -> Dict[str, Any]:
        """
        Provision ONU device.
        
        Args:
            parent_device_id: Parent OLT device ID
            pon_port: PON port number
            onu_id: ONU ID on the PON port
            serial_number: ONU serial number
            context: Plugin context
            
        Returns:
            Provisioning result
        """
        try:
            onu_data = {
                "parent_device_id": parent_device_id,
                "pon_port": pon_port,
                "onu_id": onu_id,
                "serial_number": serial_number
            }
            
            success = await self._provision_voltha_onu(onu_data)
            
            if success:
                self._logger.info(
                    f"Successfully provisioned ONU: {serial_number} on {parent_device_id}:{pon_port}:{onu_id}"
                )
                
                return {
                    "status": "provisioned",
                    "serial_number": serial_number,
                    "parent_device_id": parent_device_id,
                    "pon_port": pon_port,
                    "onu_id": onu_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
        except Exception as e:
            self._logger.error(f"Failed to provision ONU {serial_number}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "serial_number": serial_number,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    async def delete_device(self, device_id: str, context: PluginContext = None) -> bool:
        """Delete VOLTHA device."""
        try:
            # First disable the device
            await self._disable_voltha_device(device_id)
            
            # Then delete it
            success = await self._delete_voltha_device(device_id)
            
            if success:
                self._logger.info(f"Successfully deleted VOLTHA device: {device_id}")
                
            return success
            
        except Exception as e:
            self._logger.error(f"Failed to delete VOLTHA device {device_id}: {e}")
            return False
            
    async def add_subscriber_flow(
        self,
        device_id: str,
        subscriber_id: str,
        onu_device_id: str,
        service_config: Dict[str, Any],
        context: PluginContext = None
    ) -> bool:
        """Add subscriber service flows."""
        try:
            flow_config = {
                "device_id": device_id,
                "subscriber_id": subscriber_id,
                "onu_device_id": onu_device_id,
                "cvlan": service_config.get("cvlan"),
                "svlan": service_config.get("svlan"),
                "upstream_bw": service_config.get("upstream_bandwidth", 10000),
                "downstream_bw": service_config.get("downstream_bandwidth", 100000),
                "service_type": service_config.get("service_type", "internet")
            }
            
            success = await self._add_voltha_flows(flow_config)
            
            if success:
                self._logger.info(f"Successfully added flows for subscriber: {subscriber_id}")
                
            return success
            
        except Exception as e:
            self._logger.error(f"Failed to add flows for subscriber {subscriber_id}: {e}")
            return False
            
    async def get_device_statistics(
        self, device_id: str, context: PluginContext = None
    ) -> Dict[str, Any]:
        """Get device performance statistics."""
        try:
            stats = await self._get_voltha_device_stats(device_id)
            return stats
            
        except Exception as e:
            self._logger.error(f"Failed to get statistics for device {device_id}: {e}")
            return {}
            
    # Private Helper Methods
    
    async def _test_connectivity(self) -> None:
        """Test connectivity to VOLTHA core."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/health"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    self._logger.debug(f"Successfully connected to VOLTHA at {self.voltha_host}:{self.voltha_rest_port}")
                else:
                    raise Exception(f"VOLTHA health check failed with status {response.status}")
                    
        except Exception as e:
            raise PluginError(f"Cannot connect to VOLTHA: {e}")
            
    async def _get_voltha_devices(self) -> List[VolthaDevice]:
        """Get all VOLTHA devices."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    devices = []
                    
                    for device_data in data.get("items", []):
                        device = VolthaDevice(
                            device_id=device_data.get("id", ""),
                            device_type=device_data.get("type", ""),
                            host_and_port=device_data.get("host_and_port", ""),
                            admin_state=device_data.get("admin_state", "UNKNOWN"),
                            oper_status=device_data.get("oper_status", "UNKNOWN"),
                            connect_status=device_data.get("connect_status", "UNREACHABLE"),
                            serial_number=device_data.get("serial_number"),
                            vendor=device_data.get("vendor"),
                            model=device_data.get("model"),
                            firmware_version=device_data.get("firmware_version")
                        )
                        devices.append(device)
                        
                    return devices
                else:
                    self._logger.error(f"Failed to get VOLTHA devices: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            self._logger.error(f"Error getting VOLTHA devices: {e}")
            return []
            
    async def _get_voltha_device(self, device_id: str) -> Optional[VolthaDevice]:
        """Get specific VOLTHA device."""
        devices = await self._get_voltha_devices()
        for device in devices:
            if device.device_id == device_id:
                return device
        return None
        
    async def _create_voltha_device(self, device_data: Dict[str, Any]) -> Optional[str]:
        """Create new VOLTHA device."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices"
            async with self.session.post(url, json=device_data) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("id")
                else:
                    self._logger.error(f"Failed to create VOLTHA device: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            self._logger.error(f"Error creating VOLTHA device: {e}")
            return None
            
    async def _enable_voltha_device(self, device_id: str) -> bool:
        """Enable VOLTHA device."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices/{device_id}/enable"
            async with self.session.post(url) as response:
                return response.status == 200
                
        except Exception as e:
            self._logger.error(f"Error enabling VOLTHA device {device_id}: {e}")
            return False
            
    async def _disable_voltha_device(self, device_id: str) -> bool:
        """Disable VOLTHA device."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices/{device_id}/disable"
            async with self.session.post(url) as response:
                return response.status == 200
                
        except Exception as e:
            self._logger.error(f"Error disabling VOLTHA device {device_id}: {e}")
            return False
            
    async def _delete_voltha_device(self, device_id: str) -> bool:
        """Delete VOLTHA device."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices/{device_id}"
            async with self.session.delete(url) as response:
                return response.status == 200
                
        except Exception as e:
            self._logger.error(f"Error deleting VOLTHA device {device_id}: {e}")
            return False
            
    async def _configure_olt_device(self, device_id: str, config: Dict[str, Any]) -> bool:
        """Configure OLT device specific settings."""
        # Placeholder for OLT-specific configuration
        self._logger.info(f"Configuring OLT device: {device_id}")
        return True
        
    async def _configure_onu_device(self, device_id: str, config: Dict[str, Any]) -> bool:
        """Configure ONU device specific settings."""
        # Placeholder for ONU-specific configuration
        self._logger.info(f"Configuring ONU device: {device_id}")
        return True
        
    async def _get_device_ports(self, device_id: str) -> List[Dict[str, Any]]:
        """Get device port information."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices/{device_id}/ports"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("items", [])
                return []
                
        except Exception as e:
            self._logger.error(f"Error getting ports for device {device_id}: {e}")
            return []
            
    async def _get_device_flows(self, device_id: str) -> List[Dict[str, Any]]:
        """Get device flow information."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices/{device_id}/flows"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("items", [])
                return []
                
        except Exception as e:
            self._logger.error(f"Error getting flows for device {device_id}: {e}")
            return []
            
    async def _get_device_alarms(self, device_id: str) -> List[Dict[str, Any]]:
        """Get device alarms."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices/{device_id}/alarms"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("items", [])
                return []
                
        except Exception as e:
            self._logger.error(f"Error getting alarms for device {device_id}: {e}")
            return []
            
    async def _provision_voltha_onu(self, onu_data: Dict[str, Any]) -> bool:
        """Provision ONU in VOLTHA."""
        # Placeholder for ONU provisioning
        self._logger.info(f"Provisioning ONU: {onu_data}")
        return True
        
    async def _add_voltha_flows(self, flow_config: Dict[str, Any]) -> bool:
        """Add flows to VOLTHA device."""
        # Placeholder for flow provisioning
        self._logger.info(f"Adding flows: {flow_config}")
        return True
        
    async def _get_voltha_device_stats(self, device_id: str) -> Dict[str, Any]:
        """Get VOLTHA device statistics."""
        try:
            url = f"http://{self.voltha_host}:{self.voltha_rest_port}/api/v1/devices/{device_id}/stats"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                return {}
                
        except Exception as e:
            self._logger.error(f"Error getting stats for device {device_id}: {e}")
            return {}
            
    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks."""
        # Start device monitoring task
        task = asyncio.create_task(self._device_monitoring_loop())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
    async def _stop_background_tasks(self) -> None:
        """Stop background tasks."""
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
        self.background_tasks.clear()
        
    async def _device_monitoring_loop(self) -> None:
        """Background device monitoring loop."""
        while True:
            try:
                # Monitor device health and collect statistics
                devices = await self._get_voltha_devices()
                
                for device in devices:
                    try:
                        # Collect device statistics
                        stats = await self._get_voltha_device_stats(device.device_id)
                        
                        # Check for alarms
                        alarms = await self._get_device_alarms(device.device_id)
                        
                        # Log any critical alarms
                        critical_alarms = [
                            alarm for alarm in alarms 
                            if alarm.get("severity") in ["CRITICAL", "MAJOR"]
                        ]
                        
                        if critical_alarms:
                            self._logger.warning(
                                f"Device {device.device_id} has {len(critical_alarms)} critical alarms"
                            )
                            
                    except Exception as e:
                        self._logger.error(f"Error monitoring device {device.device_id}: {e}")
                        
                # Sleep for 60 seconds before next monitoring cycle
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in device monitoring loop: {e}")
                await asyncio.sleep(60)
                
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        health_data = await super().health_check()
        
        try:
            # Test VOLTHA connectivity
            await self._test_connectivity()
            
            # Get device counts
            devices = await self._get_voltha_devices()
            olt_count = len([d for d in devices if "olt" in d.device_type.lower()])
            onu_count = len([d for d in devices if "onu" in d.device_type.lower()])
            
            health_data.update({
                "voltha_reachable": True,
                "total_devices": len(devices),
                "olt_devices": olt_count,
                "onu_devices": onu_count,
                "details": {
                    "voltha_host": self.voltha_host,
                    "voltha_rest_port": self.voltha_rest_port,
                },
            })
            
        except Exception as e:
            health_data.update({
                "healthy": False,
                "voltha_reachable": False,
                "error": str(e)
            })
            
        return health_data
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get plugin metrics."""
        metrics = await super().get_metrics()
        
        try:
            # Get VOLTHA-specific metrics
            devices = await self._get_voltha_devices()
            
            enabled_devices = len([d for d in devices if d.admin_state == "ENABLED"])
            active_devices = len([d for d in devices if d.oper_status == "ACTIVE"])
            connected_devices = len([d for d in devices if d.connect_status == "REACHABLE"])
            
            metrics.update({
                "voltha_total_devices": len(devices),
                "voltha_enabled_devices": enabled_devices,
                "voltha_active_devices": active_devices,
                "voltha_connected_devices": connected_devices,
                "voltha_host": self.voltha_host,
                "voltha_rest_port": self.voltha_rest_port,
            })
            
        except Exception as e:
            metrics["metrics_error"] = str(e)
            
        return metrics