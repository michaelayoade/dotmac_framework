"""
Unified API Router - Exposes OpenWISP APIs through DotMac networking endpoints.
Single API for both DotMac and OpenWISP functionality.
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import asyncio

from .device_manager import UnifiedDeviceManager, DeviceNotFoundError, ConfigDeploymentError
from .openwisp_proxy import OpenWISPProxy, OpenWISPProxyError


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DeviceRegistration(BaseModel):
    device_id: str
    device_type: str
    vendor: str
    model: str
    site_id: str
    management_ip: Optional[str] = None
    mac_address: Optional[str] = None
    is_openwisp_managed: bool = False
    description: Optional[str] = None


class ConfigTemplate(BaseModel):
    template_name: str
    device_type: str
    vendor: str
    template_content: Any  # Can be string or dict for OpenWrt
    is_openwisp_template: bool = False
    description: Optional[str] = None
    variables: Optional[List[str]] = []


class ConfigDeployment(BaseModel):
    template_id: str
    parameters: Optional[Dict[str, Any]] = None


class RadiusUser(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    is_active: bool = True


class RadiusAuth(BaseModel):
    username: str
    password: str
    calling_station_id: Optional[str] = None
    nas_ip_address: Optional[str] = None


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_tenant_id() -> str:
    """Get tenant ID from request context. In production, extract from JWT."""
    # TODO: Extract from authenticated user context
    return "default-tenant"


async def get_device_manager(tenant_id: str = Depends(get_tenant_id)) -> UnifiedDeviceManager:
    """Get unified device manager for tenant."""
    return UnifiedDeviceManager(tenant_id)


async def get_openwisp_proxy() -> OpenWISPProxy:
    """Get OpenWISP proxy."""
    return OpenWISPProxy()


# =============================================================================
# API ROUTER
# =============================================================================

unified_api_router = APIRouter(prefix="/api/v1/unified", tags=["Unified ISP Management"])


# =============================================================================
# DEVICE MANAGEMENT ENDPOINTS
# =============================================================================

@unified_api_router.post("/devices", response_model=Dict[str, Any])
async def register_device(
    device: DeviceRegistration,
    manager: UnifiedDeviceManager = Depends(get_device_manager)
):
    """Register device in unified registry (DotMac + OpenWISP if applicable)."""
    try:
        result = await manager.register_device(
            device_id=device.device_id,
            device_type=device.device_type,
            vendor=device.vendor,
            model=device.model,
            site_id=device.site_id,
            management_ip=device.management_ip,
            mac_address=device.mac_address,
            is_openwisp_managed=device.is_openwisp_managed,
            description=device.description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@unified_api_router.get("/devices/{device_id}", response_model=Dict[str, Any])
async def get_device(
    device_id: str = Path(..., description="Device ID"),
    include_openwisp: bool = Query(True, description="Include OpenWISP data"),
    manager: UnifiedDeviceManager = Depends(get_device_manager)
):
    """Get device from unified registry."""
    device = await manager.get_device(device_id, include_openwisp=include_openwisp)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    return device


@unified_api_router.get("/devices", response_model=List[Dict[str, Any]])
async def list_devices(
    site_id: Optional[str] = Query(None, description="Filter by site"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    include_openwisp: bool = Query(False, description="Include OpenWISP data"),
    manager: UnifiedDeviceManager = Depends(get_device_manager)
):
    """List devices from unified registry."""
    return await manager.list_devices(
        site_id=site_id,
        device_type=device_type,
        vendor=vendor,
        include_openwisp=include_openwisp
    )


@unified_api_router.get("/devices/{device_id}/status", response_model=Dict[str, Any])
async def get_device_status(
    device_id: str = Path(..., description="Device ID"),
    manager: UnifiedDeviceManager = Depends(get_device_manager)
):
    """Get comprehensive device status."""
    try:
        return await manager.get_device_status(device_id)
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@unified_api_router.get("/devices/{device_id}/config", response_model=Dict[str, Any])
async def get_device_config(
    device_id: str = Path(..., description="Device ID"),
    manager: UnifiedDeviceManager = Depends(get_device_manager)
):
    """Get device configuration."""
    try:
        return await manager.get_device_config(device_id)
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# CONFIGURATION MANAGEMENT ENDPOINTS
# =============================================================================

@unified_api_router.post("/config/templates", response_model=Dict[str, Any])
async def create_config_template(
    template: ConfigTemplate,
    manager: UnifiedDeviceManager = Depends(get_device_manager)
):
    """Create configuration template (routes to appropriate system)."""
    try:
        return await manager.create_config_template(
            template_name=template.template_name,
            device_type=template.device_type,
            vendor=template.vendor,
            template_content=template.template_content,
            is_openwisp_template=template.is_openwisp_template,
            description=template.description,
            variables=template.variables
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@unified_api_router.post("/devices/{device_id}/deploy-config", response_model=Dict[str, Any])
async def deploy_config(
    device_id: str = Path(..., description="Device ID"),
    deployment: ConfigDeployment = ...,
    manager: UnifiedDeviceManager = Depends(get_device_manager)
):
    """Deploy configuration to device (smart routing)."""
    try:
        return await manager.deploy_config(
            device_id=device_id,
            template_id=deployment.template_id,
            parameters=deployment.parameters
        )
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConfigDeploymentError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DIRECT OPENWISP API PROXYING
# =============================================================================

@unified_api_router.get("/openwisp/devices", response_model=List[Dict[str, Any]])
async def list_openwisp_devices(
    organization_id: Optional[str] = Query(None, description="Organization filter"),
    config_status: Optional[str] = Query(None, description="Config status filter"),
    template_id: Optional[str] = Query(None, description="Template filter"),
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Direct proxy to OpenWISP Controller device list."""
    try:
        return await proxy.devices.list_devices(
            organization_id=organization_id,
            config_status=config_status,
            template_id=template_id
        )
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@unified_api_router.get("/openwisp/templates", response_model=List[Dict[str, Any]])
async def list_openwisp_templates(
    organization_id: Optional[str] = Query(None, description="Organization filter"),
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Direct proxy to OpenWISP Controller template list."""
    try:
        return await proxy.configs.list_templates(organization_id=organization_id)
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@unified_api_router.get("/openwisp/vpns", response_model=List[Dict[str, Any]])
async def list_openwisp_vpns(
    backend: Optional[str] = Query(None, description="VPN backend (OpenVpn, Wireguard)"),
    organization_id: Optional[str] = Query(None, description="Organization filter"),
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Direct proxy to OpenWISP Controller VPN list."""
    try:
        return await proxy.vpns.list_vpns(backend=backend, organization_id=organization_id)
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RADIUS API PROXYING
# =============================================================================

@unified_api_router.post("/radius/users", response_model=Dict[str, Any])
async def create_radius_user(
    user: RadiusUser,
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Create RADIUS user via OpenWISP."""
    try:
        user_data = {
            'username': user.username,
            'email': user.email,
            'password': user.password,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active
        }
        return await proxy.radius.create_user(user_data)
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=400, detail=str(e))


@unified_api_router.get("/radius/users", response_model=List[Dict[str, Any]])
async def list_radius_users(
    organization_id: Optional[str] = Query(None, description="Organization filter"),
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """List RADIUS users via OpenWISP."""
    try:
        return await proxy.radius.list_users(organization_id=organization_id)
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@unified_api_router.post("/radius/authenticate", response_model=Dict[str, Any])
async def authenticate_radius_user(
    auth: RadiusAuth,
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Authenticate RADIUS user via OpenWISP."""
    try:
        return await proxy.radius.authenticate_user(
            username=auth.username,
            password=auth.password,
            calling_station_id=auth.calling_station_id,
            nas_ip_address=auth.nas_ip_address
        )
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=401, detail=str(e))


@unified_api_router.post("/radius/disconnect/{username}", response_model=Dict[str, Any])
async def disconnect_radius_user(
    username: str = Path(..., description="Username to disconnect"),
    reason: str = Query("Admin-Disconnect", description="Disconnect reason"),
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Disconnect RADIUS user via OpenWISP."""
    try:
        success = await proxy.radius.disconnect_user(username, reason)
        return {'username': username, 'disconnected': success, 'reason': reason}
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MONITORING API PROXYING  
# =============================================================================

@unified_api_router.get("/monitoring/devices/{device_id}/metrics", response_model=List[Dict[str, Any]])
async def get_device_metrics(
    device_id: str = Path(..., description="Device ID"),
    metric_type: Optional[str] = Query(None, description="Metric type filter"),
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Get device metrics via OpenWISP Monitoring."""
    try:
        return await proxy.monitoring.get_device_metrics(device_id, metric_type)
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@unified_api_router.get("/monitoring/devices/{device_id}/alerts", response_model=List[Dict[str, Any]])
async def get_device_alerts(
    device_id: str = Path(..., description="Device ID"),
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Get device alerts via OpenWISP Monitoring."""
    try:
        return await proxy.monitoring.get_device_alerts(device_id)
    except OpenWISPProxyError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SYSTEM HEALTH AND STATUS
# =============================================================================

@unified_api_router.get("/health", response_model=Dict[str, Any])
async def health_check(
    manager: UnifiedDeviceManager = Depends(get_device_manager),
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Check health of unified system."""
    try:
        dotmac_health = await manager.health_check()
        openwisp_health = await proxy.health_check()
        
        return {
            'dotmac': dotmac_health,
            'openwisp': openwisp_health,
            'overall_status': 'healthy' if dotmac_health.get('status') == 'healthy' else 'degraded'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@unified_api_router.get("/api-schema", response_model=Dict[str, Any])
async def get_api_schemas(
    proxy: OpenWISPProxy = Depends(get_openwisp_proxy)
):
    """Get API schemas from all OpenWISP services."""
    try:
        schemas = {}
        for service in ['controller', 'radius', 'monitoring']:
            try:
                schemas[service] = await proxy.get_api_schema(service)
            except Exception as e:
                schemas[service] = {'error': str(e)}
        
        return {
            'dotmac_unified_api': '/docs',  # This API's schema
            'openwisp_schemas': schemas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))