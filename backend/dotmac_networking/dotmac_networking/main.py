"""
Enhanced DotMac Networking Service Main Module
Integrates Paramiko SSH automation, NetworkX graph analysis, and VOLTHA OLT/ONU management
"""

import asyncio
import logging
import sys
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import config
from .core.exceptions import NetworkingError

# Enhanced SDKs
from .sdks.ssh_automation import SSHAutomationSDK
from .sdks.networkx_topology import NetworkXTopologySDK
from .sdks.voltha_integration import VOLTHAIntegrationSDK

# Existing SDKs
from .sdks.netjson_support import NetJSONRenderer
from .sdks.captive_portal import CaptivePortalSDK


# Global SDK instances
ssh_sdk: SSHAutomationSDK = None
topology_sdk: NetworkXTopologySDK = None
voltha_sdk: VOLTHAIntegrationSDK = None
netjson_renderer: NetJSONRenderer = None
captive_portal_sdk: CaptivePortalSDK = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global ssh_sdk, topology_sdk, voltha_sdk, netjson_renderer, captive_portal_sdk
    
    # Initialize SDKs
    tenant_id = config.tenant_id or "default"
    
    # SSH Automation SDK
    ssh_sdk = SSHAutomationSDK(tenant_id)
    logging.info("SSH Automation SDK initialized")
    
    # NetworkX Topology SDK
    topology_sdk = NetworkXTopologySDK(tenant_id)
    logging.info("NetworkX Topology SDK initialized")
    
    # VOLTHA Integration SDK (if enabled)
    if config.voltha_enabled:
        voltha_sdk = VOLTHAIntegrationSDK(config.voltha_endpoint, tenant_id)
        try:
            init_result = await voltha_sdk.initialize()
            if init_result["voltha_connected"]:
                logging.info(f"VOLTHA SDK initialized: {init_result['devices_discovered']} devices discovered")
            else:
                logging.warning("VOLTHA SDK failed to connect, running in degraded mode")
        except Exception as e:
            logging.warning(f"VOLTHA initialization failed: {e}, running without VOLTHA")
            voltha_sdk = None
    
    # NetJSON Renderer
    netjson_renderer = NetJSONRenderer()
    logging.info("NetJSON Renderer initialized")
    
    # Captive Portal SDK
    captive_portal_sdk = CaptivePortalSDK(tenant_id)
    logging.info("Captive Portal SDK initialized")
    
    yield
    
    # Cleanup
    if ssh_sdk:
        await ssh_sdk.cleanup()
    if voltha_sdk:
        await voltha_sdk.cleanup()
    
    logging.info("Enhanced DotMac Networking service shutdown complete")


# FastAPI application
app = FastAPI(
    title="Enhanced DotMac Networking Service",
    description="Advanced ISP network management with SSH automation, graph analysis, and VOLTHA integration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
def get_ssh_sdk() -> SSHAutomationSDK:
    if ssh_sdk is None:
        raise HTTPException(status_code=503, detail="SSH Automation SDK not available")
    return ssh_sdk


def get_topology_sdk() -> NetworkXTopologySDK:
    if topology_sdk is None:
        raise HTTPException(status_code=503, detail="NetworkX Topology SDK not available")
    return topology_sdk


def get_voltha_sdk() -> VOLTHAIntegrationSDK:
    if voltha_sdk is None:
        raise HTTPException(status_code=503, detail="VOLTHA SDK not available")
    return voltha_sdk


def get_netjson_renderer() -> NetJSONRenderer:
    if netjson_renderer is None:
        raise HTTPException(status_code=503, detail="NetJSON Renderer not available")
    return netjson_renderer


def get_captive_portal_sdk() -> CaptivePortalSDK:
    if captive_portal_sdk is None:
        raise HTTPException(status_code=503, detail="Captive Portal SDK not available")
    return captive_portal_sdk


# Health check endpoint
@app.get("/health")
async def health_check():
    """Enhanced health check with all components"""
    health_status = {
        "status": "healthy",
        "service": "dotmac-networking-enhanced",
        "version": "2.0.0",
        "components": {}
    }
    
    # Check SSH SDK
    try:
        stats = await ssh_sdk.ssh_manager.get_execution_stats()
        health_status["components"]["ssh_automation"] = {
            "status": "healthy",
            "total_executions": stats.get("total_executions", 0)
        }
    except Exception as e:
        health_status["components"]["ssh_automation"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check NetworkX Topology
    try:
        metrics = await topology_sdk.topology.calculate_network_metrics()
        health_status["components"]["networkx_topology"] = {
            "status": "healthy",
            "total_nodes": metrics["basic_stats"]["total_nodes"],
            "total_edges": metrics["basic_stats"]["total_edges"]
        }
    except Exception as e:
        health_status["components"]["networkx_topology"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check VOLTHA (if enabled)
    if voltha_sdk:
        try:
            network_status = await voltha_sdk.get_network_status()
            health_status["components"]["voltha_integration"] = {
                "status": "healthy",
                "total_olts": network_status["total_olts"],
                "total_onus": network_status["total_onus"]
            }
        except Exception as e:
            health_status["components"]["voltha_integration"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        health_status["components"]["voltha_integration"] = {
            "status": "disabled",
            "reason": "VOLTHA not enabled in configuration"
        }
    
    # Check overall health
    failed_components = [comp for comp in health_status["components"].values() if comp["status"] == "error"]
    if failed_components:
        health_status["status"] = "degraded"
    
    return health_status


# SSH Automation Endpoints
@app.post("/ssh/deploy-configuration")
async def deploy_configuration(
    device_list: list[str],
    uci_commands: list[str],
    credentials: dict = None,
    ssh_sdk: SSHAutomationSDK = Depends(get_ssh_sdk)
):
    """Deploy UCI configuration to multiple devices via SSH"""
    try:
        result = await ssh_sdk.deploy_configuration(device_list, uci_commands, credentials)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ssh/network-discovery")
async def network_discovery(
    ip_range: str,
    credentials: dict,
    ssh_sdk: SSHAutomationSDK = Depends(get_ssh_sdk)
):
    """Discover network devices via SSH"""
    try:
        result = await ssh_sdk.network_discovery(ip_range, credentials)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ssh/firmware-upgrade")
async def mass_firmware_upgrade(
    device_list: list[str],
    firmware_url: str,
    credentials: dict,
    ssh_sdk: SSHAutomationSDK = Depends(get_ssh_sdk)
):
    """Perform mass firmware upgrade"""
    try:
        result = await ssh_sdk.mass_firmware_upgrade(device_list, firmware_url, credentials)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ssh/execution-stats")
async def get_ssh_execution_stats(ssh_sdk: SSHAutomationSDK = Depends(get_ssh_sdk)):
    """Get SSH execution statistics"""
    try:
        result = await ssh_sdk.ssh_manager.get_execution_stats()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# NetworkX Topology Endpoints
@app.post("/topology/add-device")
async def add_network_device(
    device_id: str,
    device_type: str,
    attributes: dict = None,
    topology_sdk: NetworkXTopologySDK = Depends(get_topology_sdk)
):
    """Add network device to topology"""
    try:
        result = await topology_sdk.add_device(device_id, device_type, **(attributes or {}))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/topology/add-link")
async def add_network_link(
    device1: str,
    device2: str,
    attributes: dict = None,
    topology_sdk: NetworkXTopologySDK = Depends(get_topology_sdk)
):
    """Add network link between devices"""
    try:
        result = await topology_sdk.add_link(device1, device2, **(attributes or {}))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topology/analysis")
async def get_network_analysis(topology_sdk: NetworkXTopologySDK = Depends(get_topology_sdk)):
    """Get comprehensive network analysis"""
    try:
        result = await topology_sdk.get_network_analysis()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topology/shortest-path/{source}/{target}")
async def find_shortest_path(
    source: str,
    target: str,
    topology_sdk: NetworkXTopologySDK = Depends(get_topology_sdk)
):
    """Find shortest path between devices"""
    try:
        result = await topology_sdk.topology.find_shortest_path(source, target)
        return {"source": source, "target": target, "path": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/topology/simulate-failure")
async def simulate_device_failure(
    device_id: str,
    topology_sdk: NetworkXTopologySDK = Depends(get_topology_sdk)
):
    """Simulate device failure and analyze impact"""
    try:
        result = await topology_sdk.topology.simulate_node_failure(device_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topology/optimization")
async def get_network_optimization(topology_sdk: NetworkXTopologySDK = Depends(get_topology_sdk)):
    """Get network optimization recommendations"""
    try:
        result = await topology_sdk.plan_network_optimization()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# VOLTHA Integration Endpoints
@app.get("/voltha/network-status")
async def get_voltha_network_status(voltha_sdk: VOLTHAIntegrationSDK = Depends(get_voltha_sdk)):
    """Get VOLTHA network status"""
    try:
        result = await voltha_sdk.get_network_status()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voltha/provision-subscriber")
async def provision_subscriber_service(
    olt_id: str,
    onu_serial: str,
    customer_id: str,
    service_profile: dict,
    voltha_sdk: VOLTHAIntegrationSDK = Depends(get_voltha_sdk)
):
    """Provision subscriber service via VOLTHA"""
    try:
        result = await voltha_sdk.provision_subscriber_service(
            olt_id, onu_serial, customer_id, service_profile
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voltha/suspend-service")
async def suspend_subscriber_service(
    customer_id: str,
    onu_device_id: str,
    voltha_sdk: VOLTHAIntegrationSDK = Depends(get_voltha_sdk)
):
    """Suspend subscriber service"""
    try:
        result = await voltha_sdk.suspend_subscriber_service(customer_id, onu_device_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voltha/restore-service")
async def restore_subscriber_service(
    customer_id: str,
    onu_device_id: str,
    service_profile: dict,
    voltha_sdk: VOLTHAIntegrationSDK = Depends(get_voltha_sdk)
):
    """Restore subscriber service"""
    try:
        result = await voltha_sdk.restore_subscriber_service(customer_id, onu_device_id, service_profile)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voltha/device-analytics/{device_id}")
async def get_device_analytics(
    device_id: str,
    time_window_hours: int = 24,
    voltha_sdk: VOLTHAIntegrationSDK = Depends(get_voltha_sdk)
):
    """Get device analytics"""
    try:
        result = await voltha_sdk.get_device_analytics(device_id, time_window_hours)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voltha/subscriber-status/{customer_id}/{onu_device_id}")
async def get_subscriber_status(
    customer_id: str,
    onu_device_id: str,
    voltha_sdk: VOLTHAIntegrationSDK = Depends(get_voltha_sdk)
):
    """Get subscriber service status"""
    try:
        result = await voltha_sdk.get_subscriber_status(customer_id, onu_device_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# NetJSON Endpoints
@app.post("/netjson/render-uci")
async def render_netjson_to_uci(
    netjson_config: dict,
    netjson_renderer: NetJSONRenderer = Depends(get_netjson_renderer)
):
    """Convert NetJSON configuration to UCI commands"""
    try:
        result = netjson_renderer.render_openwrt_config(netjson_config)
        return {"uci_commands": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Captive Portal Endpoints
@app.post("/captive-portal/create-hotspot")
async def create_hotspot(
    name: str,
    ssid: str,
    location: str = None,
    auth_method: str = "radius",
    captive_portal_sdk: CaptivePortalSDK = Depends(get_captive_portal_sdk)
):
    """Create WiFi hotspot with captive portal"""
    try:
        result = await captive_portal_sdk.create_hotspot(name, ssid, location, auth_method)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/captive-portal/authenticate-user")
async def authenticate_portal_user(
    hotspot_id: str,
    username: str = None,
    email: str = None,
    password: str = None,
    captive_portal_sdk: CaptivePortalSDK = Depends(get_captive_portal_sdk)
):
    """Authenticate user for hotspot access"""
    try:
        result = await captive_portal_sdk.authenticate_user(
            hotspot_id, username, email, password=password
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/captive-portal/hotspots")
async def list_hotspots(captive_portal_sdk: CaptivePortalSDK = Depends(get_captive_portal_sdk)):
    """List all hotspots"""
    try:
        result = await captive_portal_sdk.list_hotspots()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Integrated Workflow Endpoints
@app.post("/integrated/customer-onboarding")
async def integrated_customer_onboarding(
    customer_data: dict,
    service_profile: dict,
    device_config: dict,
    ssh_sdk: SSHAutomationSDK = Depends(get_ssh_sdk),
    topology_sdk: NetworkXTopologySDK = Depends(get_topology_sdk),
    voltha_sdk: VOLTHAIntegrationSDK = Depends(get_voltha_sdk)
):
    """Integrated customer onboarding workflow"""
    try:
        workflow_result = {
            "workflow_id": f"onboard_{customer_data.get('customer_id')}",
            "customer_id": customer_data.get("customer_id"),
            "steps": [],
            "overall_success": True
        }
        
        # Step 1: Network topology analysis
        if customer_data.get("preferred_olt"):
            # Find best path to customer location
            paths = await topology_sdk.topology.find_all_simple_paths(
                "core_router", customer_data["preferred_olt"]
            )
            workflow_result["steps"].append({
                "step": "topology_analysis",
                "success": True,
                "paths_found": len(paths),
                "optimal_path": paths[0] if paths else None
            })
        
        # Step 2: VOLTHA service provisioning
        if voltha_sdk and customer_data.get("olt_id") and customer_data.get("onu_serial"):
            provision_result = await voltha_sdk.provision_subscriber_service(
                customer_data["olt_id"],
                customer_data["onu_serial"],
                customer_data["customer_id"],
                service_profile
            )
            workflow_result["steps"].append({
                "step": "voltha_provisioning",
                "success": provision_result["success"],
                "voltha_flow_id": provision_result.get("voltha_flow_id"),
                "details": provision_result
            })
            
            if not provision_result["success"]:
                workflow_result["overall_success"] = False
        
        # Step 3: Device configuration via SSH
        if device_config.get("device_ip") and device_config.get("uci_commands"):
            netjson_config = device_config.get("netjson_config", {})
            if netjson_config:
                uci_commands = netjson_renderer.render_openwrt_config(netjson_config)
                deploy_result = await ssh_sdk.deploy_configuration(
                    [device_config["device_ip"]],
                    uci_commands.split('\n'),
                    device_config.get("credentials")
                )
                workflow_result["steps"].append({
                    "step": "device_configuration",
                    "success": deploy_result["successful_deployments"] > 0,
                    "details": deploy_result
                })
                
                if deploy_result["successful_deployments"] == 0:
                    workflow_result["overall_success"] = False
        
        return workflow_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/integrated/network-health-dashboard")
async def network_health_dashboard(
    ssh_sdk: SSHAutomationSDK = Depends(get_ssh_sdk),
    topology_sdk: NetworkXTopologySDK = Depends(get_topology_sdk),
    voltha_sdk: VOLTHAIntegrationSDK = Depends(get_voltha_sdk)
):
    """Comprehensive network health dashboard"""
    try:
        dashboard = {
            "overall_health_score": 0.0,
            "ssh_automation": {},
            "network_topology": {},
            "voltha_status": {},
            "recommendations": [],
            "generated_at": ""
        }
        
        # SSH automation health
        ssh_stats = await ssh_sdk.ssh_manager.get_execution_stats()
        dashboard["ssh_automation"] = {
            "total_executions": ssh_stats.get("total_executions", 0),
            "success_rate": ssh_stats.get("success_rate", 100),
            "average_execution_time": ssh_stats.get("average_execution_time", 0),
            "unique_devices": ssh_stats.get("unique_devices", 0)
        }
        
        # Network topology health
        topology_analysis = await topology_sdk.get_network_analysis()
        dashboard["network_topology"] = {
            "total_devices": topology_analysis["network_metrics"]["basic_stats"]["total_nodes"],
            "network_density": topology_analysis["network_metrics"]["basic_stats"]["density"],
            "resilience_score": topology_analysis["resilience_analysis"]["overall_score"],
            "critical_devices": len(topology_analysis["critical_infrastructure"]["critical_nodes"])
        }
        
        # VOLTHA status (if available)
        if voltha_sdk:
            voltha_status = await voltha_sdk.get_network_status()
            dashboard["voltha_status"] = {
                "total_olts": voltha_status["total_olts"],
                "healthy_olts": voltha_status["healthy_olts"],
                "total_onus": voltha_status["total_onus"],
                "active_onus": voltha_status["active_onus"],
                "network_utilization": voltha_status["network_utilization"]["average"]
            }
        
        # Calculate overall health score
        ssh_health = min(ssh_stats.get("success_rate", 100) / 100, 1.0)
        topology_health = topology_analysis["resilience_analysis"]["overall_score"]
        voltha_health = 1.0 if not voltha_sdk else (voltha_status["healthy_olts"] / max(voltha_status["total_olts"], 1))
        
        dashboard["overall_health_score"] = (ssh_health * 0.3 + topology_health * 0.4 + voltha_health * 0.3)
        
        # Generate recommendations
        if dashboard["overall_health_score"] < 0.7:
            dashboard["recommendations"].append("Network health is below optimal - investigate critical issues")
        if ssh_stats.get("success_rate", 100) < 90:
            dashboard["recommendations"].append("SSH automation success rate is low - check device connectivity")
        if topology_analysis["resilience_analysis"]["overall_score"] < 0.6:
            dashboard["recommendations"].append("Network resilience is poor - add redundant connections")
        
        from datetime import datetime
        dashboard["generated_at"] = datetime.utcnow().isoformat()
        
        return dashboard
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Start the server
    uvicorn.run(
        "dotmac_networking.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.environment == "development",
        log_level=config.log_level.lower()
    )