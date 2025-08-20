"""
VOLTHA Integration SDK - Enterprise OLT/ONU management via VOLTHA platform
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime, timedelta

from ..core.datetime_utils import utc_now
from ..core.exceptions import NetworkingError


class VOLTHAClient:
    """Client for VOLTHA gRPC API (mock implementation)"""
    
    def __init__(self, voltha_endpoint: str):
        self.endpoint = voltha_endpoint
        self.connected = False
        
        # Mock VOLTHA device database
        self._mock_devices = {
            "olt_001": {
                "id": "olt_001",
                "type": "openolt",
                "vendor": "adtran",
                "model": "622-01",
                "firmware_version": "4.7.0",
                "hardware_version": "1.0",
                "serial_number": "ADTN12345678",
                "mac_address": "00:1A:2B:3C:4D:5E",
                "ipv4_address": "192.168.1.100",
                "admin_state": "ENABLED",
                "oper_status": "ACTIVE",
                "connect_status": "REACHABLE",
                "reason": "",
                "ports": [
                    {"port_no": 1, "type": "PON_OLT", "admin_state": "ENABLED", "oper_status": "ACTIVE"},
                    {"port_no": 2, "type": "PON_OLT", "admin_state": "ENABLED", "oper_status": "ACTIVE"},
                    {"port_no": 3, "type": "PON_OLT", "admin_state": "ENABLED", "oper_status": "ACTIVE"},
                    {"port_no": 4, "type": "PON_OLT", "admin_state": "ENABLED", "oper_status": "ACTIVE"}
                ]
            },
            "olt_002": {
                "id": "olt_002", 
                "type": "openolt",
                "vendor": "zyxel",
                "model": "OLT2412-A1",
                "firmware_version": "2.1.0",
                "hardware_version": "1.0",
                "serial_number": "ZYXL87654321",
                "mac_address": "00:5F:6A:7B:8C:9D",
                "ipv4_address": "192.168.1.101",
                "admin_state": "ENABLED",
                "oper_status": "ACTIVE",
                "connect_status": "REACHABLE",
                "ports": [
                    {"port_no": 1, "type": "PON_OLT", "admin_state": "ENABLED", "oper_status": "ACTIVE"},
                    {"port_no": 2, "type": "PON_OLT", "admin_state": "ENABLED", "oper_status": "ACTIVE"}
                ]
            }
        }
        
        self._mock_onus = {
            "onu_001": {
                "id": "onu_001",
                "type": "brcm_openomci_onu",
                "vendor": "alphion",
                "model": "ASFvOLT16",
                "firmware_version": "1.0.0",
                "serial_number": "ALCL12345678",
                "parent_id": "olt_001",
                "parent_port_no": 1,
                "vlan": 100,
                "admin_state": "ENABLED",
                "oper_status": "ACTIVE",
                "connect_status": "REACHABLE"
            },
            "onu_002": {
                "id": "onu_002", 
                "type": "brcm_openomci_onu",
                "vendor": "alphion",
                "model": "ASFvOLT16", 
                "firmware_version": "1.0.0",
                "serial_number": "ALCL87654321",
                "parent_id": "olt_001",
                "parent_port_no": 2,
                "vlan": 101,
                "admin_state": "ENABLED",
                "oper_status": "ACTIVE", 
                "connect_status": "REACHABLE"
            }
        }
        
        self._mock_flows = {}
        self._mock_alarms = []
        
    async def connect(self) -> bool:
        """Connect to VOLTHA gRPC endpoint"""
        # Simulate connection
        await asyncio.sleep(0.1)
        self.connected = True
        return True
        
    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices from VOLTHA"""
        if not self.connected:
            await self.connect()
        
        devices = list(self._mock_devices.values()) + list(self._mock_onus.values())
        return devices
    
    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get specific device by ID"""
        if device_id in self._mock_devices:
            return self._mock_devices[device_id]
        elif device_id in self._mock_onus:
            return self._mock_onus[device_id]
        return None
    
    async def get_device_ports(self, device_id: str) -> List[Dict[str, Any]]:
        """Get ports for a device"""
        device = await self.get_device(device_id)
        return device.get("ports", []) if device else []
    
    async def get_device_metrics(self, device_id: str) -> Dict[str, Any]:
        """Get real-time device metrics"""
        device = await self.get_device(device_id)
        if not device:
            return {}
        
        # Mock metrics based on device type
        if device["type"] == "openolt":
            return {
                "tx_optical_power": -2.5,
                "rx_optical_power": -8.2,
                "tx_bytes": 1024000000,  # 1GB
                "rx_bytes": 2048000000,  # 2GB
                "tx_packets": 1000000,
                "rx_packets": 2000000,
                "cpu_usage": 45.2,
                "memory_usage": 62.8,
                "temperature": 42.5
            }
        else:  # ONU
            return {
                "tx_optical_power": 2.1,
                "rx_optical_power": -12.3,
                "tx_bytes": 50000000,   # 50MB
                "rx_bytes": 200000000,  # 200MB
                "tx_packets": 50000,
                "rx_packets": 200000,
                "fec_codewords_corrected": 12,
                "ber": 1.2e-9
            }
    
    async def get_device_port_metrics(self, device_id: str) -> List[Dict[str, Any]]:
        """Get per-port metrics"""
        ports = await self.get_device_ports(device_id)
        port_metrics = []
        
        for port in ports:
            if port["type"] == "PON_OLT":
                port_metrics.append({
                    "port_no": port["port_no"],
                    "type": port["type"],
                    "tx_bytes": 100000000 * port["port_no"],
                    "rx_bytes": 150000000 * port["port_no"],
                    "tx_packets": 100000 * port["port_no"],
                    "rx_packets": 150000 * port["port_no"],
                    "capacity": 10000000000,  # 10Gbps
                    "utilization": (port["port_no"] * 10) % 80  # Mock utilization
                })
        
        return port_metrics
    
    async def provision_subscriber(self, olt_id: str, onu_serial: str, 
                                 service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Provision subscriber service via VOLTHA"""
        
        # Find ONU by serial number
        onu_device = None
        for onu_id, onu in self._mock_onus.items():
            if onu["serial_number"] == onu_serial and onu["parent_id"] == olt_id:
                onu_device = onu
                break
        
        if not onu_device:
            return {
                "success": False,
                "error": f"ONU with serial {onu_serial} not found on OLT {olt_id}"
            }
        
        # Create flow configuration
        flow_id = str(uuid4())
        flow_config = {
            "flow_id": flow_id,
            "device_id": onu_device["id"],
            "olt_id": olt_id,
            "onu_serial": onu_serial,
            "vlan": onu_device["vlan"],
            "service_config": service_config,
            "flows": [
                {
                    "direction": "downstream",
                    "match": {"vlan_id": onu_device["vlan"]},
                    "actions": {
                        "set_vlan": service_config.get("customer_vlan", 100),
                        "bandwidth_profile": {
                            "cir": service_config.get("downstream_bw", 100) * 1000000,  # Mbps to bps
                            "pir": service_config.get("downstream_bw", 100) * 1000000,
                            "cbs": 1000000,
                            "pbs": 1000000
                        }
                    }
                },
                {
                    "direction": "upstream", 
                    "match": {"customer_vlan": service_config.get("customer_vlan", 100)},
                    "actions": {
                        "set_vlan": onu_device["vlan"],
                        "bandwidth_profile": {
                            "cir": service_config.get("upstream_bw", 50) * 1000000,
                            "pir": service_config.get("upstream_bw", 50) * 1000000,
                            "cbs": 500000,
                            "pbs": 500000
                        }
                    }
                }
            ],
            "provisioned_at": utc_now().isoformat()
        }
        
        self._mock_flows[flow_id] = flow_config
        
        return {
            "success": True,
            "flow_id": flow_id,
            "onu_device_id": onu_device["id"],
            "provisioned_services": len(flow_config["flows"])
        }
    
    async def delete_subscriber_flows(self, device_id: str) -> Dict[str, Any]:
        """Delete subscriber flows (for service suspension)"""
        
        # Find flows for this device
        device_flows = [f for f in self._mock_flows.values() if f["device_id"] == device_id]
        
        if not device_flows:
            return {
                "success": False,
                "error": f"No flows found for device {device_id}"
            }
        
        # Remove flows
        flows_removed = 0
        for flow_id, flow in list(self._mock_flows.items()):
            if flow["device_id"] == device_id:
                del self._mock_flows[flow_id]
                flows_removed += 1
        
        return {
            "success": True,
            "flows_removed": flows_removed,
            "suspended_at": utc_now().isoformat()
        }
    
    async def add_subscriber_flows(self, device_id: str, service_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Restore subscriber flows (for service restoration)"""
        
        # Find the ONU device
        onu_device = None
        for onu in self._mock_onus.values():
            if onu["id"] == device_id:
                onu_device = onu
                break
        
        if not onu_device:
            return {
                "success": False,
                "error": f"Device {device_id} not found"
            }
        
        # Re-provision flows
        provision_result = await self.provision_subscriber(
            onu_device["parent_id"],
            onu_device["serial_number"], 
            service_profile
        )
        
        if provision_result["success"]:
            return {
                "success": True,
                "flow_id": provision_result["flow_id"],
                "restored_at": utc_now().isoformat()
            }
        else:
            return provision_result
    
    async def get_device_alarms(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get device alarms"""
        
        # Mock some alarms
        mock_alarms = [
            {
                "id": "alarm_001",
                "device_id": "olt_001",
                "alarm_type": "POWER_SUPPLY_FAILURE",
                "severity": "MAJOR",
                "status": "ACTIVE",
                "description": "Power supply 1 failure",
                "raised_at": (utc_now() - timedelta(hours=2)).isoformat()
            },
            {
                "id": "alarm_002", 
                "device_id": "onu_001",
                "alarm_type": "LOW_RX_OPTICAL_POWER",
                "severity": "MINOR",
                "status": "ACTIVE", 
                "description": "Low RX optical power detected",
                "raised_at": (utc_now() - timedelta(minutes=30)).isoformat()
            }
        ]
        
        if device_id:
            return [alarm for alarm in mock_alarms if alarm["device_id"] == device_id]
        
        return mock_alarms
    
    async def acknowledge_alarm(self, alarm_id: str) -> Dict[str, Any]:
        """Acknowledge an alarm"""
        return {
            "alarm_id": alarm_id,
            "acknowledged": True,
            "acknowledged_at": utc_now().isoformat()
        }


class VOLTHAIntegrationSDK:
    """Main SDK for VOLTHA integration with DotMac"""
    
    def __init__(self, voltha_endpoint: str, tenant_id: str):
        self.voltha_client = VOLTHAClient(voltha_endpoint)
        self.tenant_id = tenant_id
        self.device_cache: Dict[str, Dict[str, Any]] = {}
        self.last_discovery: Optional[datetime] = None
        
    async def initialize(self) -> Dict[str, Any]:
        """Initialize VOLTHA connection and discovery"""
        
        connection_result = await self.voltha_client.connect()
        
        if connection_result:
            discovery_result = await self.discover_network()
            
            return {
                "voltha_connected": True,
                "devices_discovered": len(discovery_result["devices"]),
                "olts_found": len(discovery_result["olts"]),
                "onus_found": len(discovery_result["onus"]),
                "initialized_at": utc_now().isoformat()
            }
        else:
            return {
                "voltha_connected": False,
                "error": "Failed to connect to VOLTHA"
            }
    
    async def discover_network(self) -> Dict[str, Any]:
        """Discover all network devices via VOLTHA"""
        
        devices = await self.voltha_client.get_devices()
        
        olts = []
        onus = []
        
        for device in devices:
            if device["type"] == "openolt":
                olt_info = {
                    "device_id": device["id"],
                    "vendor": device["vendor"],
                    "model": device["model"],
                    "serial_number": device["serial_number"],
                    "ip_address": device["ipv4_address"],
                    "firmware_version": device["firmware_version"],
                    "admin_state": device["admin_state"],
                    "oper_status": device["oper_status"],
                    "connect_status": device["connect_status"],
                    "discovery_method": "VOLTHA",
                    "discovered_at": utc_now().isoformat()
                }
                olts.append(olt_info)
                self.device_cache[device["id"]] = device
                
            elif device["type"] == "brcm_openomci_onu":
                onu_info = {
                    "device_id": device["id"],
                    "olt_id": device["parent_id"], 
                    "port_no": device["parent_port_no"],
                    "serial_number": device["serial_number"],
                    "vendor": device["vendor"],
                    "model": device["model"],
                    "firmware_version": device["firmware_version"],
                    "vlan": device.get("vlan"),
                    "admin_state": device["admin_state"],
                    "oper_status": device["oper_status"],
                    "connect_status": device["connect_status"],
                    "discovery_method": "VOLTHA",
                    "discovered_at": utc_now().isoformat()
                }
                onus.append(onu_info)
                self.device_cache[device["id"]] = device
        
        self.last_discovery = utc_now()
        
        return {
            "devices": devices,
            "olts": olts,
            "onus": onus,
            "discovery_completed": utc_now().isoformat()
        }
    
    async def provision_subscriber_service(self, 
                                         olt_id: str,
                                         onu_serial: str, 
                                         customer_id: str,
                                         service_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Provision subscriber service via VOLTHA with DotMac integration"""
        
        provisioning_id = str(uuid4())
        
        try:
            # 1. Provision via VOLTHA
            voltha_result = await self.voltha_client.provision_subscriber(
                olt_id, onu_serial, service_profile
            )
            
            if not voltha_result["success"]:
                return {
                    "provisioning_id": provisioning_id,
                    "success": False,
                    "error": voltha_result["error"],
                    "stage": "voltha_provisioning"
                }
            
            # 2. Record in DotMac format
            provisioning_record = {
                "provisioning_id": provisioning_id,
                "customer_id": customer_id,
                "olt_id": olt_id,
                "onu_serial": onu_serial,
                "voltha_device_id": voltha_result["onu_device_id"],
                "voltha_flow_id": voltha_result["flow_id"],
                "service_profile": service_profile,
                "bandwidth_downstream": service_profile.get("downstream_bw", 100),
                "bandwidth_upstream": service_profile.get("upstream_bw", 50),
                "customer_vlan": service_profile.get("customer_vlan", 100),
                "status": "active",
                "provisioned_at": utc_now().isoformat(),
                "tenant_id": self.tenant_id
            }
            
            return {
                "provisioning_id": provisioning_id,
                "success": True,
                "voltha_device_id": voltha_result["onu_device_id"],
                "voltha_flow_id": voltha_result["flow_id"],
                "service_activated": True,
                "provisioning_details": provisioning_record
            }
            
        except Exception as e:
            return {
                "provisioning_id": provisioning_id,
                "success": False,
                "error": str(e),
                "stage": "exception_handling"
            }
    
    async def suspend_subscriber_service(self, customer_id: str, onu_device_id: str) -> Dict[str, Any]:
        """Suspend subscriber service instantly via VOLTHA"""
        
        suspension_result = await self.voltha_client.delete_subscriber_flows(onu_device_id)
        
        if suspension_result["success"]:
            return {
                "customer_id": customer_id,
                "onu_device_id": onu_device_id,
                "service_suspended": True,
                "flows_removed": suspension_result["flows_removed"],
                "suspended_at": suspension_result["suspended_at"]
            }
        else:
            return {
                "customer_id": customer_id,
                "service_suspended": False,
                "error": suspension_result["error"]
            }
    
    async def restore_subscriber_service(self, customer_id: str, onu_device_id: str,
                                       service_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Restore subscriber service via VOLTHA"""
        
        restoration_result = await self.voltha_client.add_subscriber_flows(
            onu_device_id, service_profile
        )
        
        if restoration_result["success"]:
            return {
                "customer_id": customer_id,
                "onu_device_id": onu_device_id,
                "service_restored": True,
                "voltha_flow_id": restoration_result["flow_id"],
                "restored_at": restoration_result["restored_at"]
            }
        else:
            return {
                "customer_id": customer_id,
                "service_restored": False,
                "error": restoration_result["error"]
            }
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status"""
        
        devices = await self.voltha_client.get_devices()
        
        network_stats = {
            "total_olts": 0,
            "healthy_olts": 0,
            "total_onus": 0,
            "active_onus": 0,
            "total_alarms": 0,
            "critical_alarms": 0,
            "network_utilization": {"average": 0, "peak": 0},
            "device_summary": {}
        }
        
        total_utilization = 0
        max_utilization = 0
        
        for device in devices:
            if device["type"] == "openolt":
                network_stats["total_olts"] += 1
                if device["oper_status"] == "ACTIVE":
                    network_stats["healthy_olts"] += 1
                
                # Get port metrics for utilization
                port_metrics = await self.voltha_client.get_device_port_metrics(device["id"])
                for port_metric in port_metrics:
                    utilization = port_metric.get("utilization", 0)
                    total_utilization += utilization
                    max_utilization = max(max_utilization, utilization)
                
                network_stats["device_summary"][device["id"]] = {
                    "vendor": device["vendor"],
                    "model": device["model"],
                    "status": device["oper_status"],
                    "ports": len(port_metrics)
                }
                
            elif device["type"] == "brcm_openomci_onu":
                network_stats["total_onus"] += 1
                if device["oper_status"] == "ACTIVE":
                    network_stats["active_onus"] += 1
        
        # Calculate average utilization
        total_ports = sum(len(await self.voltha_client.get_device_port_metrics(d["id"])) 
                         for d in devices if d["type"] == "openolt")
        
        if total_ports > 0:
            network_stats["network_utilization"]["average"] = total_utilization / total_ports
        network_stats["network_utilization"]["peak"] = max_utilization
        
        # Get alarm summary
        alarms = await self.voltha_client.get_device_alarms()
        network_stats["total_alarms"] = len(alarms)
        network_stats["critical_alarms"] = len([a for a in alarms if a["severity"] in ["CRITICAL", "MAJOR"]])
        
        network_stats["status_collected"] = utc_now().isoformat()
        
        return network_stats
    
    async def get_device_analytics(self, device_id: str, 
                                 time_window_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive device analytics"""
        
        device = await self.voltha_client.get_device(device_id)
        if not device:
            return {"error": f"Device {device_id} not found"}
        
        # Get current metrics
        current_metrics = await self.voltha_client.get_device_metrics(device_id)
        
        # Get port metrics if it's an OLT
        port_metrics = []
        if device["type"] == "openolt":
            port_metrics = await self.voltha_client.get_device_port_metrics(device_id)
        
        # Get device alarms
        device_alarms = await self.voltha_client.get_device_alarms(device_id)
        
        analytics = {
            "device_info": {
                "device_id": device_id,
                "type": device["type"],
                "vendor": device["vendor"],
                "model": device["model"],
                "serial_number": device["serial_number"],
                "status": device["oper_status"]
            },
            "current_metrics": current_metrics,
            "port_analytics": port_metrics,
            "alarm_summary": {
                "total_alarms": len(device_alarms),
                "active_alarms": len([a for a in device_alarms if a["status"] == "ACTIVE"]),
                "severity_breakdown": {
                    "critical": len([a for a in device_alarms if a["severity"] == "CRITICAL"]),
                    "major": len([a for a in device_alarms if a["severity"] == "MAJOR"]),
                    "minor": len([a for a in device_alarms if a["severity"] == "MINOR"])
                },
                "recent_alarms": device_alarms[:5]  # Last 5 alarms
            },
            "health_score": self._calculate_device_health_score(device, current_metrics, device_alarms),
            "analytics_time_window": f"{time_window_hours} hours",
            "generated_at": utc_now().isoformat()
        }
        
        return analytics
    
    async def bulk_provision_services(self, 
                                    provisioning_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk provision multiple subscriber services"""
        
        bulk_id = str(uuid4())
        results = []
        
        # Process provisions in parallel (limited concurrency)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent provisions
        
        async def provision_single(request):
            async with semaphore:
                return await self.provision_subscriber_service(
                    olt_id=request["olt_id"],
                    onu_serial=request["onu_serial"],
                    customer_id=request["customer_id"],
                    service_profile=request["service_profile"]
                )
        
        tasks = [provision_single(req) for req in provisioning_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = 0
        failed = 0
        processed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "request_index": i,
                    "success": False,
                    "error": str(result),
                    "customer_id": provisioning_requests[i].get("customer_id")
                })
                failed += 1
            else:
                processed_results.append(result)
                if result.get("success"):
                    successful += 1
                else:
                    failed += 1
        
        return {
            "bulk_id": bulk_id,
            "total_requests": len(provisioning_requests),
            "successful_provisions": successful,
            "failed_provisions": failed,
            "success_rate": (successful / len(provisioning_requests)) * 100,
            "detailed_results": processed_results,
            "bulk_completed": utc_now().isoformat()
        }
    
    async def get_subscriber_status(self, customer_id: str, onu_device_id: str) -> Dict[str, Any]:
        """Get current subscriber service status"""
        
        device = await self.voltha_client.get_device(onu_device_id)
        if not device:
            return {
                "customer_id": customer_id,
                "status": "device_not_found",
                "error": f"ONU device {onu_device_id} not found in VOLTHA"
            }
        
        # Get device metrics
        metrics = await self.voltha_client.get_device_metrics(onu_device_id)
        
        # Get device alarms
        alarms = await self.voltha_client.get_device_alarms(onu_device_id)
        
        # Analyze service status
        service_status = "active" if device["oper_status"] == "ACTIVE" else "inactive"
        
        # Check for service-affecting alarms
        service_affecting_alarms = [
            alarm for alarm in alarms 
            if alarm["severity"] in ["CRITICAL", "MAJOR"] and alarm["status"] == "ACTIVE"
        ]
        
        if service_affecting_alarms:
            service_status = "degraded"
        
        return {
            "customer_id": customer_id,
            "onu_device_id": onu_device_id,
            "service_status": service_status,
            "device_status": {
                "admin_state": device["admin_state"],
                "oper_status": device["oper_status"],
                "connect_status": device["connect_status"]
            },
            "performance_metrics": {
                "tx_optical_power": metrics.get("tx_optical_power"),
                "rx_optical_power": metrics.get("rx_optical_power"),
                "tx_bytes": metrics.get("tx_bytes", 0),
                "rx_bytes": metrics.get("rx_bytes", 0),
                "error_rate": metrics.get("ber", 0)
            },
            "active_alarms": len([a for a in alarms if a["status"] == "ACTIVE"]),
            "service_affecting_alarms": len(service_affecting_alarms),
            "last_checked": utc_now().isoformat()
        }
    
    def _calculate_device_health_score(self, device: Dict[str, Any], 
                                     metrics: Dict[str, Any], 
                                     alarms: List[Dict[str, Any]]) -> float:
        """Calculate device health score (0-100)"""
        
        health_score = 100.0
        
        # Device status impact
        if device["oper_status"] != "ACTIVE":
            health_score -= 50
        elif device["connect_status"] != "REACHABLE":
            health_score -= 30
        
        # Optical power impact (for ONUs)
        if device["type"] == "brcm_openomci_onu":
            rx_power = metrics.get("rx_optical_power", 0)
            if rx_power < -25:  # Very low power
                health_score -= 20
            elif rx_power < -20:  # Low power
                health_score -= 10
        
        # CPU/Memory impact (for OLTs) 
        if device["type"] == "openolt":
            cpu_usage = metrics.get("cpu_usage", 0)
            memory_usage = metrics.get("memory_usage", 0)
            
            if cpu_usage > 90:
                health_score -= 15
            elif cpu_usage > 80:
                health_score -= 10
                
            if memory_usage > 90:
                health_score -= 15
            elif memory_usage > 80:
                health_score -= 10
        
        # Alarm impact
        active_alarms = [a for a in alarms if a["status"] == "ACTIVE"]
        for alarm in active_alarms:
            if alarm["severity"] == "CRITICAL":
                health_score -= 25
            elif alarm["severity"] == "MAJOR":
                health_score -= 15
            elif alarm["severity"] == "MINOR":
                health_score -= 5
        
        return max(health_score, 0.0)
    
    async def cleanup(self):
        """Cleanup resources"""
        # Close VOLTHA connection if needed
        self.device_cache.clear()
        self.last_discovery = None