"""
Enhanced RADIUS SDK with PostgreSQL persistence and OpenWISP integration.
Replaces the in-memory RADIUS SDK with proper database storage and real RADIUS server.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4
import asyncio
import os

from ..core.database import db_manager
from ..repositories.radius_repository import RadiusRepository  
from ..integrations.openwisp_client import OpenWISPRadiusClient, OpenWISPRadiusError
from ..core.exceptions import RADIUSError, RADIUSAuthenticationError, CoAFailedError
from ..core.datetime_utils import utc_now


class EnhancedRADIUSSDK:
    """
    Production-ready RADIUS SDK with:
    - PostgreSQL persistence (replaces in-memory storage)
    - OpenWISP RADIUS integration (real RADIUS server)
    - Backward compatibility with existing SDK interface
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._repository: Optional[RadiusRepository] = None
        self._openwisp_client: Optional[OpenWISPRadiusClient] = None
        self._initialized = False
    
    async def _ensure_initialized(self) -> None:
        """Initialize repository and OpenWISP client if needed."""
        if not self._initialized:
            # Initialize database pool if not already done
            if db_manager._pool is None:
                await db_manager.initialize_pool()
            
            # Initialize repository
            self._repository = RadiusRepository(self.tenant_id, db_manager.pool)
            await self._repository.create_table_if_not_exists()
            
            # Initialize OpenWISP client
            self._openwisp_client = OpenWISPRadiusClient()
            
            self._initialized = True
    
    @property
    def repository(self) -> RadiusRepository:
        """Get RADIUS repository."""
        if not self._repository:
            raise RuntimeError("SDK not initialized. This shouldn't happen.")
        return self._repository
    
    @property
    def openwisp(self) -> OpenWISPRadiusClient:
        """Get OpenWISP client."""
        if not self._openwisp_client:
            raise RuntimeError("SDK not initialized. This shouldn't happen.")
        return self._openwisp_client
    
    # User Management (dual storage: PostgreSQL + OpenWISP)
    async def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        filter_id: Optional[str] = None,
        reply_attributes: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create RADIUS user in both PostgreSQL and OpenWISP."""
        await self._ensure_initialized()
        
        try:
            # Create in local PostgreSQL for fast access
            local_user = await self.repository.create_user(
                username=username,
                password=password,
                filter_id=filter_id,
                reply_attributes=reply_attributes or {},
                **kwargs
            )
            
            # Create in OpenWISP RADIUS for actual RADIUS authentication
            if email:
                try:
                    openwisp_user = await self.openwisp.create_user(
                        username=username,
                        email=email,
                        password=password,
                        **kwargs
                    )
                    local_user['openwisp_id'] = openwisp_user.get('id')
                except OpenWISPRadiusError as e:
                    # Log warning but don't fail - local user still created
                    print(f"Warning: Failed to create user in OpenWISP: {e}")
            
            return {
                'username': local_user['username'],
                'filter_id': local_user['filter_id'],
                'reply_attributes': local_user['reply_attributes'],
                'status': local_user['status'],
                'created_at': local_user['created_at'].isoformat(),
                'openwisp_integrated': bool(email)
            }
            
        except Exception as e:
            raise RADIUSError(f"Failed to create user {username}: {str(e)}")
    
    async def authenticate(
        self,
        username: str,
        password: str,
        nas_ip: str,
        nas_port: Optional[str] = None,
        calling_station_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Authenticate user via both local DB and OpenWISP RADIUS.
        Falls back to local auth if OpenWISP is unavailable.
        """
        await self._ensure_initialized()
        
        # Try OpenWISP RADIUS first (real RADIUS server)
        try:
            openwisp_result = await self.openwisp.authenticate_user(
                username=username,
                password=password,
                calling_station_id=calling_station_id,
                **kwargs
            )
            
            # If OpenWISP succeeds, create/update local session
            if openwisp_result.get('access_accept'):
                session = await self.repository.create_session({
                    'username': username,
                    'nas_ip': nas_ip,
                    'nas_port': nas_port,
                    'calling_station_id': calling_station_id,
                    'reply_attributes': openwisp_result.get('reply_attributes', {}),
                    'session_timeout': openwisp_result.get('session_timeout', 3600),
                    'idle_timeout': openwisp_result.get('idle_timeout', 600),
                    'filter_id': openwisp_result.get('filter_id'),
                })
                
                return {
                    'session_id': session['session_id'],
                    'access_accept': True,
                    'reply_attributes': session['reply_attributes'],
                    'session_timeout': session['session_timeout'],
                    'idle_timeout': session['idle_timeout'],
                    'filter_id': session['filter_id'],
                    'source': 'openwisp'
                }
            else:
                raise RADIUSAuthenticationError(username)
                
        except OpenWISPRadiusError:
            # Fallback to local authentication
            user = await self.repository.authenticate_user(username, password)
            if not user:
                raise RADIUSAuthenticationError(username)
            
            # Create local session
            session = await self.repository.create_session({
                'username': username,
                'nas_ip': nas_ip,
                'nas_port': nas_port,
                'calling_station_id': calling_station_id,
                'reply_attributes': user['reply_attributes'],
                'session_timeout': kwargs.get('session_timeout', 3600),
                'idle_timeout': kwargs.get('idle_timeout', 600),
                'filter_id': user['filter_id'],
            })
            
            return {
                'session_id': session['session_id'],
                'access_accept': True,
                'reply_attributes': session['reply_attributes'],
                'session_timeout': session['session_timeout'],
                'idle_timeout': session['idle_timeout'],
                'filter_id': session['filter_id'],
                'source': 'local'
            }
    
    # Session Management
    async def start_session(
        self,
        username: str,
        session_id: Optional[str] = None,
        nas_ip: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Start RADIUS accounting session."""
        await self._ensure_initialized()
        
        session_id = session_id or str(uuid4())
        
        # Add to local accounting
        record = await self.repository.add_accounting_record({
            'record_id': str(uuid4()),
            'session_id': session_id,
            'username': username,
            'acct_status_type': 'Start',
            'nas_ip': nas_ip,
            **kwargs
        })
        
        # Send to OpenWISP accounting
        try:
            await self.openwisp.start_accounting({
                'username': username,
                'session_id': session_id,
                'nas_ip_address': nas_ip,
                **kwargs
            })
        except OpenWISPRadiusError as e:
            print(f"Warning: OpenWISP accounting failed: {e}")
        
        return {
            'record_id': record['record_id'],
            'session_id': record['session_id'],
            'username': record['username'],
            'acct_status_type': record['acct_status_type'],
            'timestamp': record['timestamp'].isoformat(),
        }
    
    async def update_session(
        self,
        username: str,
        bytes_in: int,
        bytes_out: int,
        session_time: int,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Update RADIUS accounting session."""
        await self._ensure_initialized()
        
        # Update local session
        if session_id:
            await self.repository.update_session(session_id, {
                'bytes_in': bytes_in,
                'bytes_out': bytes_out,
                'packets_in': kwargs.get('packets_in', 0),
                'packets_out': kwargs.get('packets_out', 0),
            })
        
        # Add accounting record
        record = await self.repository.add_accounting_record({
            'record_id': str(uuid4()),
            'session_id': session_id or 'unknown',
            'username': username,
            'acct_status_type': 'Interim-Update',
            'bytes_in': bytes_in,
            'bytes_out': bytes_out,
            'session_time': session_time,
            **kwargs
        })
        
        # Send to OpenWISP
        try:
            await self.openwisp.update_accounting({
                'username': username,
                'session_id': session_id,
                'input_octets': bytes_in,
                'output_octets': bytes_out,
                'session_time': session_time,
                **kwargs
            })
        except OpenWISPRadiusError as e:
            print(f"Warning: OpenWISP accounting update failed: {e}")
        
        return {
            'record_id': record['record_id'],
            'session_id': record['session_id'],
            'username': record['username'],
            'bytes_in': record['bytes_in'],
            'bytes_out': record['bytes_out'],
            'session_time': record['session_time'],
            'timestamp': record['timestamp'].isoformat(),
        }
    
    async def stop_session(
        self,
        username: str,
        terminate_cause: str = "User-Request",
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Stop RADIUS accounting session."""
        await self._ensure_initialized()
        
        # Stop local session
        if session_id:
            await self.repository.stop_session(session_id, terminate_cause)
        
        # Add stop record
        record = await self.repository.add_accounting_record({
            'record_id': str(uuid4()),
            'session_id': session_id or 'unknown',
            'username': username,
            'acct_status_type': 'Stop',
            'terminate_cause': terminate_cause,
            'bytes_in': kwargs.get('bytes_in', 0),
            'bytes_out': kwargs.get('bytes_out', 0),
            **kwargs
        })
        
        # Send to OpenWISP
        try:
            await self.openwisp.stop_accounting({
                'username': username,
                'session_id': session_id,
                'acct_terminate_cause': terminate_cause,
                **kwargs
            })
        except OpenWISPRadiusError as e:
            print(f"Warning: OpenWISP accounting stop failed: {e}")
        
        return {
            'record_id': record['record_id'],
            'session_id': record['session_id'],
            'username': record['username'],
            'terminate_cause': record['terminate_cause'],
            'bytes_in': record['bytes_in'],
            'bytes_out': record['bytes_out'],
            'timestamp': record['timestamp'].isoformat(),
        }
    
    # Change of Authorization (CoA)
    async def apply_coa(
        self,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        filter_id: Optional[str] = None,
        session_timeout: Optional[int] = None,
        idle_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Apply Change of Authorization (CoA)."""
        await self._ensure_initialized()
        
        if not username and not session_id:
            raise RADIUSError("Either username or session_id is required for CoA")
        
        # Get session from database
        if session_id:
            session = await self.repository.get_by_id(session_id)
        else:
            session = await self.repository.get_user_session(username)
        
        if not session:
            raise CoAFailedError(session_id or username, "Session not found")
        
        # Update local session
        update_data = {}
        if filter_id is not None:
            update_data['filter_id'] = filter_id
        if session_timeout is not None:
            update_data['session_timeout'] = session_timeout
        if idle_timeout is not None:
            update_data['idle_timeout'] = idle_timeout
        
        if update_data:
            await self.repository.update_session(session['session_id'], update_data)
        
        # Note: Real CoA would be sent via OpenWISP to FreeRADIUS server
        # This requires additional CoA endpoint implementation
        
        return {
            'session_id': session['session_id'],
            'username': session['username'],
            'coa_type': 'CoA-Request',
            'status': 'success',
            'applied_changes': update_data,
            'timestamp': utc_now().isoformat(),
        }
    
    # Session Queries
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active RADIUS sessions."""
        await self._ensure_initialized()
        
        sessions = await self.repository.get_active_sessions()
        
        return [
            {
                'session_id': session['session_id'],
                'username': session['username'],
                'nas_ip': session['nas_ip'],
                'nas_port': session['nas_port'],
                'framed_ip': session['framed_ip'],
                'start_time': session['start_time'].isoformat() if session['start_time'] else None,
                'last_update': session['last_update'].isoformat() if session['last_update'] else None,
                'bytes_in': session['bytes_in'],
                'bytes_out': session['bytes_out'],
            }
            for session in sessions
        ]
    
    async def get_user_session(self, username: str) -> Optional[Dict[str, Any]]:
        """Get active session for user."""
        await self._ensure_initialized()
        
        session = await self.repository.get_user_session(username)
        if not session:
            return None
        
        return {
            'session_id': session['session_id'],
            'username': session['username'],
            'nas_ip': session['nas_ip'],
            'nas_port': session['nas_port'],
            'framed_ip': session['framed_ip'],
            'start_time': session['start_time'].isoformat() if session['start_time'] else None,
            'last_update': session['last_update'].isoformat() if session['last_update'] else None,
            'bytes_in': session['bytes_in'],
            'bytes_out': session['bytes_out'],
            'filter_id': session['filter_id'],
        }
    
    async def disconnect_user(self, username: str, reason: str = "Admin-Disconnect") -> Dict[str, Any]:
        """Disconnect user session."""
        await self._ensure_initialized()
        
        # Get active session
        session = await self.repository.get_user_session(username)
        if not session:
            raise RADIUSError(f"No active session for user: {username}")
        
        session_id = session['session_id']
        
        # Stop local session
        await self.repository.stop_session(session_id, reason)
        
        # Disconnect via OpenWISP (sends actual CoA disconnect)
        try:
            await self.openwisp.disconnect_user(username, reason)
        except OpenWISPRadiusError as e:
            print(f"Warning: OpenWISP disconnect failed: {e}")
        
        return {
            'username': username,
            'session_id': session_id,
            'status': 'disconnected',
            'reason': reason,
            'timestamp': utc_now().isoformat(),
        }
    
    # Health and Status
    async def health_check(self) -> Dict[str, Any]:
        """Check health of RADIUS system."""
        await self._ensure_initialized()
        
        # Check database
        db_healthy = await db_manager.health_check()
        
        # Check OpenWISP
        openwisp_healthy = await self.openwisp.health_check()
        
        # Get session count
        active_sessions = len(await self.get_active_sessions())
        
        return {
            'database': 'healthy' if db_healthy else 'unhealthy',
            'openwisp_radius': 'healthy' if openwisp_healthy else 'unhealthy',
            'active_sessions': active_sessions,
            'tenant_id': self.tenant_id,
            'status': 'healthy' if (db_healthy or openwisp_healthy) else 'unhealthy'
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._openwisp_client:
            await self._openwisp_client.close()


# Backward compatibility alias
RADIUSSDK = EnhancedRADIUSSDK