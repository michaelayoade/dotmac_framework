"""
OpenWISP API Proxy - Unified interface to all OpenWISP modules.
Exposes OpenWISP Controller, RADIUS, Monitoring, IPAM, etc. through DotMac API.
"""

import aiohttp
import asyncio
from typing import Any, Dict, List, Optional, Union
import json
import os
from urllib.parse import urljoin


class OpenWISPProxy:
    """
    Unified proxy for all OpenWISP modules.
    Provides a consistent interface to OpenWISP Controller, RADIUS, Monitoring, etc.
    """
    
    def __init__(self, 
                 controller_url: Optional[str] = None,
                 radius_url: Optional[str] = None,
                 monitoring_url: Optional[str] = None,
                 api_token: Optional[str] = None):
        
        # OpenWISP service URLs  
        self.controller_url = controller_url or os.getenv('OPENWISP_CONTROLLER_URL', 'http://openwisp-controller:8000/api/v1/')
        self.radius_url = radius_url or os.getenv('OPENWISP_RADIUS_URL', 'http://openwisp-radius:8000/api/v1/')
        self.monitoring_url = monitoring_url or os.getenv('OPENWISP_MONITORING_URL', 'http://openwisp-monitoring:8000/api/v1/')
        
        # API authentication
        self.api_token = api_token or os.getenv('OPENWISP_API_TOKEN', '')
        
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Ensure URLs end with /
        for url_attr in ['controller_url', 'radius_url', 'monitoring_url']:
            url = getattr(self, url_attr)
            if not url.endswith('/'):
                setattr(self, url_attr, url + '/')
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with OpenWISP authentication."""
        if self._session is None or self._session.closed:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'DotMac-Networking-Proxy/1.0'
            }
            
            if self.api_token:
                headers['Authorization'] = f'Bearer {self.api_token}'
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        
        return self._session
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(self, service: str, endpoint: str, method: str = 'GET', 
                      data: Optional[Dict[str, Any]] = None,
                      params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make request to OpenWISP service."""
        
        # Choose base URL based on service
        service_urls = {
            'controller': self.controller_url,
            'radius': self.radius_url, 
            'monitoring': self.monitoring_url
        }
        
        base_url = service_urls.get(service)
        if not base_url:
            raise OpenWISPProxyError(f"Unknown service: {service}")
        
        session = await self._get_session()
        url = urljoin(base_url, endpoint)
        
        kwargs = {}
        if data is not None:
            kwargs['json'] = data
        if params is not None:
            kwargs['params'] = params
        
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    response_data = await response.json()
                else:
                    # Handle non-JSON responses (e.g., file downloads)
                    response_data = {
                        'content': await response.read(),
                        'content_type': response.content_type,
                        'filename': response.headers.get('Content-Disposition', '').split('filename=')[-1].strip('"')
                    }
                
                if response.status >= 400:
                    error_msg = response_data.get('detail', f'HTTP {response.status}')
                    raise OpenWISPProxyError(f"{service.title()} API error: {error_msg}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            raise OpenWISPProxyError(f"{service.title()} API request failed: {str(e)}")


# =============================================================================
# DEVICE MANAGEMENT APIs (Controller)
# =============================================================================

class DeviceManagerProxy:
    """Proxy for OpenWISP Controller device management APIs."""
    
    def __init__(self, proxy: OpenWISPProxy):
        self.proxy = proxy
    
    async def list_devices(self, organization_id: Optional[str] = None, 
                          config_status: Optional[str] = None,
                          template_id: Optional[str] = None,
                          **filters) -> List[Dict[str, Any]]:
        """List devices with filtering options."""
        params = {}
        
        if organization_id:
            params['organization_id'] = organization_id
        if config_status:
            params['config__status'] = config_status  
        if template_id:
            params['config__templates'] = template_id
        
        # Add other filters
        params.update(filters)
        
        response = await self.proxy._request('controller', 'controller/device/', params=params)
        return response.get('results', [])
    
    async def get_device(self, device_id: str) -> Dict[str, Any]:
        """Get device by ID."""
        return await self.proxy._request('controller', f'controller/device/{device_id}/')
    
    async def create_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new device."""
        return await self.proxy._request('controller', 'controller/device/', 'POST', device_data)
    
    async def update_device(self, device_id: str, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update device."""
        return await self.proxy._request('controller', f'controller/device/{device_id}/', 'PATCH', device_data)
    
    async def delete_device(self, device_id: str) -> bool:
        """Delete device (must be deactivated first)."""
        try:
            await self.proxy._request('controller', f'controller/device/{device_id}/', 'DELETE')
            return True
        except OpenWISPProxyError:
            return False
    
    async def download_device_config(self, device_id: str) -> Dict[str, Any]:
        """Download device configuration as tar.gz."""
        return await self.proxy._request('controller', f'controller/device/{device_id}/config/')


class ConfigManagerProxy:
    """Proxy for OpenWISP Controller configuration template APIs."""
    
    def __init__(self, proxy: OpenWISPProxy):
        self.proxy = proxy
    
    async def list_templates(self, organization_id: Optional[str] = None, **filters) -> List[Dict[str, Any]]:
        """List configuration templates."""
        params = {}
        if organization_id:
            params['organization_id'] = organization_id
        params.update(filters)
        
        response = await self.proxy._request('controller', 'controller/template/', params=params)
        return response.get('results', [])
    
    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get configuration template by ID."""
        return await self.proxy._request('controller', f'controller/template/{template_id}/')
    
    async def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create configuration template."""
        return await self.proxy._request('controller', 'controller/template/', 'POST', template_data)
    
    async def update_template(self, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration template."""
        return await self.proxy._request('controller', f'controller/template/{template_id}/', 'PATCH', template_data)
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete configuration template."""
        try:
            await self.proxy._request('controller', f'controller/template/{template_id}/', 'DELETE')
            return True
        except OpenWISPProxyError:
            return False
    
    async def clone_template(self, template_id: str, new_name: str) -> Dict[str, Any]:
        """Clone configuration template."""
        template = await self.get_template(template_id)
        template.pop('id', None)
        template['name'] = new_name
        return await self.create_template(template)


class VPNManagerProxy:
    """Proxy for OpenWISP Controller VPN management APIs."""
    
    def __init__(self, proxy: OpenWISPProxy):
        self.proxy = proxy
    
    async def list_vpns(self, backend: Optional[str] = None, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List VPN configurations."""
        params = {}
        if backend:
            params['backend'] = backend  # OpenVpn, Wireguard
        if organization_id:
            params['organization_id'] = organization_id
            
        response = await self.proxy._request('controller', 'controller/vpn/', params=params)
        return response.get('results', [])
    
    async def get_vpn(self, vpn_id: str) -> Dict[str, Any]:
        """Get VPN configuration by ID."""
        return await self.proxy._request('controller', f'controller/vpn/{vpn_id}/')
    
    async def create_vpn(self, vpn_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create VPN configuration."""
        return await self.proxy._request('controller', 'controller/vpn/', 'POST', vpn_data)


# =============================================================================
# RADIUS APIs
# =============================================================================

class RadiusManagerProxy:
    """Proxy for OpenWISP RADIUS APIs."""
    
    def __init__(self, proxy: OpenWISPProxy):
        self.proxy = proxy
    
    async def list_users(self, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List RADIUS users."""
        params = {}
        if organization_id:
            params['organization_id'] = organization_id
            
        response = await self.proxy._request('radius', 'account/', params=params)
        return response.get('results', [])
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create RADIUS user."""
        return await self.proxy._request('radius', 'account/', 'POST', user_data)
    
    async def authenticate_user(self, username: str, password: str, **kwargs) -> Dict[str, Any]:
        """Authenticate RADIUS user."""
        auth_data = {
            'username': username,
            'password': password,
            **kwargs
        }
        return await self.proxy._request('radius', 'authorize/', 'POST', auth_data)
    
    async def start_accounting(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start RADIUS accounting session."""
        acct_data = {'acct_status_type': 'Start', **session_data}
        return await self.proxy._request('radius', 'accounting/', 'POST', acct_data)
    
    async def disconnect_user(self, username: str, reason: str = 'Admin-Disconnect') -> bool:
        """Disconnect user session."""
        data = {'username': username, 'action': 'disconnect', 'reason': reason}
        try:
            await self.proxy._request('radius', 'accounting/disconnect/', 'POST', data)
            return True
        except OpenWISPProxyError:
            return False


# =============================================================================
# MONITORING APIs
# =============================================================================

class MonitoringManagerProxy:
    """Proxy for OpenWISP Monitoring APIs."""
    
    def __init__(self, proxy: OpenWISPProxy):
        self.proxy = proxy
    
    async def get_device_metrics(self, device_id: str, metric_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get device monitoring metrics."""
        params = {'object_id': device_id}
        if metric_type:
            params['metric'] = metric_type
            
        response = await self.proxy._request('monitoring', 'monitoring/metric/', params=params)
        return response.get('results', [])
    
    async def get_device_alerts(self, device_id: str) -> List[Dict[str, Any]]:
        """Get device alerts."""
        params = {'object_id': device_id}
        response = await self.proxy._request('monitoring', 'monitoring/alert/', params=params)
        return response.get('results', [])


# =============================================================================
# Main OpenWISP Proxy with all managers
# =============================================================================

class OpenWISPProxy(OpenWISPProxy):
    """Extended OpenWISP proxy with all service managers."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize service managers
        self.devices = DeviceManagerProxy(self)
        self.configs = ConfigManagerProxy(self) 
        self.vpns = VPNManagerProxy(self)
        self.radius = RadiusManagerProxy(self)
        self.monitoring = MonitoringManagerProxy(self)
    
    async def get_api_schema(self, service: str = 'controller') -> Dict[str, Any]:
        """Get OpenAPI schema for service."""
        return await self._request(service, 'schema/')
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all OpenWISP services."""
        health_status = {}
        
        for service in ['controller', 'radius', 'monitoring']:
            try:
                # Try to get organization list as health check
                await self._request(service, 'organization/')
                health_status[service] = 'healthy'
            except OpenWISPProxyError:
                health_status[service] = 'unhealthy'
        
        return health_status


class OpenWISPProxyError(Exception):
    """OpenWISP proxy error."""
    pass