"""
OpenWISP RADIUS API client for integration.
"""

import aiohttp
import asyncio
from typing import Any, Dict, List, Optional, Union
import json
import os


class OpenWISPRadiusClient:
    """HTTP client for OpenWISP RADIUS API."""
    
    def __init__(self, base_url: Optional[str] = None, api_token: Optional[str] = None):
        self.base_url = base_url or os.getenv('OPENWISP_RADIUS_API_URL', 'http://localhost:8010/api/v1/')
        self.api_token = api_token or os.getenv('OPENWISP_RADIUS_TOKEN', '')
        self._session: Optional[aiohttp.ClientSession] = None
        
        if not self.base_url.endswith('/'):
            self.base_url += '/'
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'DotMac-Networking/1.0'
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
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to OpenWISP API."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        kwargs = {}
        if data is not None:
            kwargs['json'] = data
        if params is not None:
            kwargs['params'] = params
        
        try:
            async with session.request(method, url, **kwargs) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    raise OpenWISPRadiusError(
                        f"HTTP {response.status}: {response_data.get('detail', 'Unknown error')}"
                    )
                
                return response_data
                
        except aiohttp.ClientError as e:
            raise OpenWISPRadiusError(f"Request failed: {str(e)}")
    
    # User Management
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str = '',
        last_name: str = '',
        **kwargs
    ) -> Dict[str, Any]:
        """Create user in OpenWISP RADIUS."""
        user_data = {
            'username': username,
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            **kwargs
        }
        
        return await self._request('POST', 'account/', user_data)
    
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            return await self._request('GET', f'account/{username}/')
        except OpenWISPRadiusError:
            return None
    
    async def update_user(self, username: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user."""
        return await self._request('PATCH', f'account/{username}/', user_data)
    
    async def delete_user(self, username: str) -> bool:
        """Delete user."""
        try:
            await self._request('DELETE', f'account/{username}/')
            return True
        except OpenWISPRadiusError:
            return False
    
    # RADIUS Client Management  
    async def create_radius_client(
        self,
        name: str,
        ip_address: str,
        secret: str,
        nas_type: str = 'other',
        **kwargs
    ) -> Dict[str, Any]:
        """Create RADIUS client (NAS)."""
        client_data = {
            'name': name,
            'ip_address': ip_address,
            'secret': secret,
            'type': nas_type,
            **kwargs
        }
        
        return await self._request('POST', 'nas/', client_data)
    
    async def list_radius_clients(self) -> List[Dict[str, Any]]:
        """List all RADIUS clients."""
        response = await self._request('GET', 'nas/')
        return response.get('results', [])
    
    async def get_radius_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get RADIUS client by ID."""
        try:
            return await self._request('GET', f'nas/{client_id}/')
        except OpenWISPRadiusError:
            return None
    
    async def update_radius_client(self, client_id: str, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update RADIUS client."""
        return await self._request('PATCH', f'nas/{client_id}/', client_data)
    
    async def delete_radius_client(self, client_id: str) -> bool:
        """Delete RADIUS client."""
        try:
            await self._request('DELETE', f'nas/{client_id}/')
            return True
        except OpenWISPRadiusError:
            return False
    
    # Session Management
    async def get_user_sessions(self, username: str) -> List[Dict[str, Any]]:
        """Get active sessions for user."""
        params = {'username': username}
        response = await self._request('GET', 'accounting/', params=params)
        return response.get('results', [])
    
    async def disconnect_user(self, username: str, reason: str = 'Admin-Disconnect') -> bool:
        """Disconnect user session."""
        data = {
            'username': username,
            'action': 'disconnect',
            'reason': reason
        }
        
        try:
            await self._request('POST', 'accounting/disconnect/', data)
            return True
        except OpenWISPRadiusError:
            return False
    
    # Authentication  
    async def authenticate_user(
        self,
        username: str,
        password: str,
        calling_station_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Authenticate user via RADIUS."""
        auth_data = {
            'username': username,
            'password': password,
            'calling_station_id': calling_station_id,
            **kwargs
        }
        
        return await self._request('POST', 'authorize/', auth_data)
    
    # Accounting
    async def start_accounting(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start RADIUS accounting session."""
        acct_data = {
            'acct_status_type': 'Start',
            **session_data
        }
        
        return await self._request('POST', 'accounting/', acct_data)
    
    async def update_accounting(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update RADIUS accounting session."""
        acct_data = {
            'acct_status_type': 'Interim-Update',
            **session_data
        }
        
        return await self._request('POST', 'accounting/', acct_data)
    
    async def stop_accounting(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Stop RADIUS accounting session."""
        acct_data = {
            'acct_status_type': 'Stop',
            **session_data
        }
        
        return await self._request('POST', 'accounting/', acct_data)
    
    # Group Management
    async def create_group(self, name: str, description: str = '', **kwargs) -> Dict[str, Any]:
        """Create user group."""
        group_data = {
            'name': name,
            'description': description,
            **kwargs
        }
        
        return await self._request('POST', 'group/', group_data)
    
    async def list_groups(self) -> List[Dict[str, Any]]:
        """List all groups."""
        response = await self._request('GET', 'group/')
        return response.get('results', [])
    
    async def add_user_to_group(self, username: str, group_name: str) -> bool:
        """Add user to group."""
        data = {
            'username': username,
            'group': group_name
        }
        
        try:
            await self._request('POST', 'group-users/', data)
            return True
        except OpenWISPRadiusError:
            return False
    
    # Health Check
    async def health_check(self) -> bool:
        """Check OpenWISP RADIUS API health."""
        try:
            await self._request('GET', 'organization/')
            return True
        except OpenWISPRadiusError:
            return False


class OpenWISPRadiusError(Exception):
    """OpenWISP RADIUS API error."""
    pass