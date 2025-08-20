"""
Captive Portal SDK - WiFi hotspot management with authentication.
Provides the key captive portal functionality that OpenWISP offers.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timedelta
from ..core.datetime_utils import utc_now
from ..core.exceptions import NetworkingError


class CaptivePortalService:
    """In-memory service for captive portal operations."""
    
    def __init__(self):
        self._hotspots: Dict[str, Dict[str, Any]] = {}
        self._portal_users: Dict[str, Dict[str, Any]] = {}
        self._user_sessions: Dict[str, Dict[str, Any]] = {}
        self._auth_methods: Dict[str, Dict[str, Any]] = {}
    
    async def create_hotspot(self, **kwargs) -> Dict[str, Any]:
        """Create WiFi hotspot with captive portal."""
        hotspot_id = kwargs.get("hotspot_id") or str(uuid4())
        
        hotspot = {
            "hotspot_id": hotspot_id,
            "name": kwargs["name"],
            "ssid": kwargs["ssid"],
            "location": kwargs.get("location", ""),
            "description": kwargs.get("description", ""),
            "auth_method": kwargs.get("auth_method", "radius"),  # radius, voucher, free, social
            "radius_server": kwargs.get("radius_server", ""),
            "captive_portal_url": kwargs.get("captive_portal_url", f"http://portal.local/{hotspot_id}"),
            "session_timeout": kwargs.get("session_timeout", 3600),  # 1 hour
            "bandwidth_limit_down": kwargs.get("bandwidth_limit_down", 0),  # 0 = unlimited
            "bandwidth_limit_up": kwargs.get("bandwidth_limit_up", 0),
            "max_concurrent_users": kwargs.get("max_concurrent_users", 100),
            "terms_of_service": kwargs.get("terms_of_service", ""),
            "privacy_policy": kwargs.get("privacy_policy", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }
        
        self._hotspots[hotspot_id] = hotspot
        return hotspot
    
    async def create_portal_user(self, **kwargs) -> Dict[str, Any]:
        """Create user for captive portal access."""
        user_id = kwargs.get("user_id") or str(uuid4())
        
        user = {
            "user_id": user_id,
            "username": kwargs.get("username", ""),
            "email": kwargs.get("email", ""),
            "phone_number": kwargs.get("phone_number", ""),
            "first_name": kwargs.get("first_name", ""),
            "last_name": kwargs.get("last_name", ""),
            "auth_method": kwargs.get("auth_method", "email"),  # email, sms, social, voucher
            "social_provider": kwargs.get("social_provider", ""),  # facebook, google, twitter
            "social_id": kwargs.get("social_id", ""),
            "password": kwargs.get("password", ""),
            "is_verified": kwargs.get("is_verified", False),
            "verification_code": kwargs.get("verification_code", ""),
            "verification_expires": kwargs.get("verification_expires", ""),
            "data_limit_mb": kwargs.get("data_limit_mb", 0),  # 0 = unlimited
            "time_limit_minutes": kwargs.get("time_limit_minutes", 0),  # 0 = unlimited
            "valid_until": kwargs.get("valid_until", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "last_login": None,
        }
        
        self._portal_users[user_id] = user
        return user
    
    async def authenticate_portal_user(self, **kwargs) -> Dict[str, Any]:
        """Authenticate user for captive portal access."""
        username = kwargs.get("username")
        email = kwargs.get("email")
        phone_number = kwargs.get("phone_number")
        password = kwargs.get("password", "")
        
        # Find user by username, email, or phone
        user = None
        for portal_user in self._portal_users.values():
            if (username and portal_user.get("username") == username) or \
               (email and portal_user.get("email") == email) or \
               (phone_number and portal_user.get("phone_number") == phone_number):
                user = portal_user
                break
        
        if not user:
            raise NetworkingError("User not found")
        
        if user["status"] != "active":
            raise NetworkingError("User account is not active")
        
        # Verify password if required
        if user.get("password") and user["password"] != password:
            raise NetworkingError("Invalid password")
        
        # Check if user needs verification
        if not user["is_verified"] and user["auth_method"] in ["email", "sms"]:
            raise NetworkingError("User account not verified")
        
        # Check validity period
        if user.get("valid_until"):
            valid_until = datetime.fromisoformat(user["valid_until"].replace('Z', '+00:00'))
            if utc_now() > valid_until:
                raise NetworkingError("User account has expired")
        
        # Update last login
        user["last_login"] = utc_now().isoformat()
        
        return {
            "user_id": user["user_id"],
            "username": user.get("username"),
            "email": user.get("email"),
            "auth_method": user["auth_method"],
            "data_limit_mb": user["data_limit_mb"],
            "time_limit_minutes": user["time_limit_minutes"],
            "authenticated": True,
            "authenticated_at": utc_now().isoformat()
        }
    
    async def create_user_session(self, **kwargs) -> Dict[str, Any]:
        """Create captive portal user session."""
        session_id = kwargs.get("session_id") or str(uuid4())
        
        session = {
            "session_id": session_id,
            "user_id": kwargs["user_id"],
            "hotspot_id": kwargs["hotspot_id"],
            "client_mac": kwargs.get("client_mac", ""),
            "client_ip": kwargs.get("client_ip", ""),
            "user_agent": kwargs.get("user_agent", ""),
            "start_time": utc_now().isoformat(),
            "last_activity": utc_now().isoformat(),
            "bytes_downloaded": 0,
            "bytes_uploaded": 0,
            "status": "active",
            "session_timeout": kwargs.get("session_timeout", 3600),
        }
        
        # Calculate session expiry
        start_time = utc_now()
        timeout_seconds = session["session_timeout"]
        session["expires_at"] = (start_time + timedelta(seconds=timeout_seconds)).isoformat()
        
        self._user_sessions[session_id] = session
        return session
    
    async def terminate_session(self, session_id: str, reason: str = "User logout") -> Dict[str, Any]:
        """Terminate user session."""
        if session_id not in self._user_sessions:
            raise NetworkingError(f"Session not found: {session_id}")
        
        session = self._user_sessions[session_id]
        session.update({
            "status": "terminated",
            "end_time": utc_now().isoformat(),
            "termination_reason": reason
        })
        
        return {
            "session_id": session_id,
            "status": "terminated",
            "reason": reason,
            "terminated_at": session["end_time"]
        }


class CaptivePortalSDK:
    """Minimal SDK for captive portal and WiFi hotspot management."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = CaptivePortalService()
    
    async def create_hotspot(
        self,
        name: str,
        ssid: str,
        location: Optional[str] = None,
        auth_method: str = "radius",
        **kwargs
    ) -> Dict[str, Any]:
        """Create WiFi hotspot with captive portal."""
        hotspot = await self._service.create_hotspot(
            name=name,
            ssid=ssid,
            location=location,
            auth_method=auth_method,
            tenant_id=self.tenant_id,
            **kwargs
        )
        
        return {
            "hotspot_id": hotspot["hotspot_id"],
            "name": hotspot["name"],
            "ssid": hotspot["ssid"],
            "location": hotspot["location"],
            "auth_method": hotspot["auth_method"],
            "captive_portal_url": hotspot["captive_portal_url"],
            "session_timeout": hotspot["session_timeout"],
            "max_concurrent_users": hotspot["max_concurrent_users"],
            "status": hotspot["status"],
            "created_at": hotspot["created_at"]
        }
    
    async def register_user(
        self,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        auth_method: str = "email",
        **kwargs
    ) -> Dict[str, Any]:
        """Register new user for captive portal access."""
        user = await self._service.create_portal_user(
            email=email,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            auth_method=auth_method,
            **kwargs
        )
        
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "phone_number": user["phone_number"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "auth_method": user["auth_method"],
            "is_verified": user["is_verified"],
            "created_at": user["created_at"]
        }
    
    async def authenticate_user(
        self,
        hotspot_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Authenticate user for hotspot access."""
        auth_result = await self._service.authenticate_portal_user(
            username=username,
            email=email,
            phone_number=phone_number,
            password=password
        )
        
        # Create session if authentication successful
        if auth_result["authenticated"]:
            session = await self._service.create_user_session(
                user_id=auth_result["user_id"],
                hotspot_id=hotspot_id,
                **kwargs
            )
            
            auth_result["session_id"] = session["session_id"]
            auth_result["session_expires"] = session["expires_at"]
        
        return auth_result
    
    async def get_hotspot(self, hotspot_id: str) -> Optional[Dict[str, Any]]:
        """Get hotspot configuration."""
        hotspot = self._service._hotspots.get(hotspot_id)
        if not hotspot:
            return None
        
        return {
            "hotspot_id": hotspot["hotspot_id"],
            "name": hotspot["name"],
            "ssid": hotspot["ssid"],
            "location": hotspot["location"],
            "auth_method": hotspot["auth_method"],
            "captive_portal_url": hotspot["captive_portal_url"],
            "session_timeout": hotspot["session_timeout"],
            "bandwidth_limit_down": hotspot["bandwidth_limit_down"],
            "bandwidth_limit_up": hotspot["bandwidth_limit_up"],
            "max_concurrent_users": hotspot["max_concurrent_users"],
            "status": hotspot["status"]
        }
    
    async def list_hotspots(self) -> List[Dict[str, Any]]:
        """List all hotspots."""
        return [
            {
                "hotspot_id": hotspot["hotspot_id"],
                "name": hotspot["name"],
                "ssid": hotspot["ssid"],
                "location": hotspot["location"],
                "auth_method": hotspot["auth_method"],
                "status": hotspot["status"],
                "created_at": hotspot["created_at"]
            }
            for hotspot in self._service._hotspots.values()
        ]
    
    async def get_active_sessions(self, hotspot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active user sessions."""
        sessions = [
            session for session in self._service._user_sessions.values()
            if session["status"] == "active" and
            (not hotspot_id or session["hotspot_id"] == hotspot_id)
        ]
        
        return [
            {
                "session_id": session["session_id"],
                "user_id": session["user_id"],
                "hotspot_id": session["hotspot_id"],
                "client_mac": session["client_mac"],
                "client_ip": session["client_ip"],
                "start_time": session["start_time"],
                "last_activity": session["last_activity"],
                "bytes_downloaded": session["bytes_downloaded"],
                "bytes_uploaded": session["bytes_uploaded"],
                "expires_at": session["expires_at"]
            }
            for session in sessions
        ]
    
    async def disconnect_user(self, session_id: str, reason: str = "Admin disconnect") -> Dict[str, Any]:
        """Disconnect user session."""
        return await self._service.terminate_session(session_id, reason)
    
    async def generate_voucher(
        self,
        hotspot_id: str,
        duration_minutes: int = 60,
        data_limit_mb: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate access voucher for hotspot."""
        voucher_code = str(uuid4())[:8].upper()  # 8-character voucher code
        
        # Create voucher user
        valid_until = utc_now() + timedelta(minutes=duration_minutes)
        user = await self._service.create_portal_user(
            username=f"voucher_{voucher_code}",
            auth_method="voucher",
            data_limit_mb=data_limit_mb,
            time_limit_minutes=duration_minutes,
            valid_until=valid_until.isoformat(),
            is_verified=True,  # Vouchers are pre-verified
            **kwargs
        )
        
        return {
            "voucher_code": voucher_code,
            "user_id": user["user_id"],
            "hotspot_id": hotspot_id,
            "duration_minutes": duration_minutes,
            "data_limit_mb": data_limit_mb,
            "valid_until": valid_until.isoformat(),
            "created_at": user["created_at"]
        }
    
    async def redeem_voucher(
        self,
        voucher_code: str,
        hotspot_id: str,
        client_mac: str,
        client_ip: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Redeem voucher for hotspot access."""
        # Find voucher user
        voucher_user = None
        for user in self._service._portal_users.values():
            if user.get("username") == f"voucher_{voucher_code}":
                voucher_user = user
                break
        
        if not voucher_user:
            raise NetworkingError("Invalid voucher code")
        
        # Authenticate and create session
        auth_result = await self.authenticate_user(
            hotspot_id=hotspot_id,
            username=voucher_user["username"],
            client_mac=client_mac,
            client_ip=client_ip,
            **kwargs
        )
        
        return {
            "voucher_code": voucher_code,
            "redeemed": True,
            "session_id": auth_result["session_id"],
            "session_expires": auth_result["session_expires"],
            "data_limit_mb": auth_result["data_limit_mb"],
            "time_limit_minutes": auth_result["time_limit_minutes"]
        }