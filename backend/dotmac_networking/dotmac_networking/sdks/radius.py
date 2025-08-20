"""
RADIUS SDK - AAA sessions, CoA (Change of Authorization)
"""

from datetime import datetime
from dotmac_networking.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import CoAFailedError, RADIUSAuthenticationError, RADIUSError


class RADIUSService:
    """In-memory service for RADIUS AAA operations."""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._users: Dict[str, Dict[str, Any]] = {}
        self._accounting_records: List[Dict[str, Any]] = []
        self._active_sessions: Dict[str, str] = {}  # username -> session_id

    async def authenticate_user(self, **kwargs) -> Dict[str, Any]:
        """Authenticate user via RADIUS."""
        username = kwargs["username"]
        password = kwargs.get("password", "")
        nas_ip = kwargs.get("nas_ip", "")
        nas_port = kwargs.get("nas_port", "")

        # Simple authentication check (in real implementation, this would check against user database)
        user = self._users.get(username)
        if not user or user.get("password") != password:
            raise RADIUSAuthenticationError(username)

        if user.get("status") != "active":
            raise RADIUSAuthenticationError(username)

        session_id = str(uuid4())
        session = {
            "session_id": session_id,
            "username": username,
            "nas_ip": nas_ip,
            "nas_port": nas_port,
            "calling_station_id": kwargs.get("calling_station_id", ""),
            "called_station_id": kwargs.get("called_station_id", ""),
            "framed_ip": kwargs.get("framed_ip", ""),
            "session_timeout": kwargs.get("session_timeout", 3600),
            "idle_timeout": kwargs.get("idle_timeout", 600),
            "filter_id": user.get("filter_id", ""),
            "reply_attributes": user.get("reply_attributes", {}),
            "status": "active",
            "start_time": utc_now().isoformat(),
            "last_update": utc_now().isoformat(),
            "bytes_in": 0,
            "bytes_out": 0,
            "packets_in": 0,
            "packets_out": 0,
        }

        self._sessions[session_id] = session
        self._active_sessions[username] = session_id

        return {
            "session_id": session_id,
            "access_accept": True,
            "reply_attributes": session["reply_attributes"],
            "session_timeout": session["session_timeout"],
            "idle_timeout": session["idle_timeout"],
            "filter_id": session["filter_id"],
        }

    async def start_accounting(self, **kwargs) -> Dict[str, Any]:
        """Start RADIUS accounting session."""
        session_id = kwargs.get("session_id")
        username = kwargs["username"]

        if not session_id:
            session_id = self._active_sessions.get(username)

        if not session_id or session_id not in self._sessions:
            raise RADIUSError(f"Session not found for user: {username}")

        accounting_record = {
            "record_id": str(uuid4()),
            "session_id": session_id,
            "username": username,
            "acct_status_type": "Start",
            "nas_ip": kwargs.get("nas_ip", ""),
            "nas_port": kwargs.get("nas_port", ""),
            "framed_ip": kwargs.get("framed_ip", ""),
            "calling_station_id": kwargs.get("calling_station_id", ""),
            "called_station_id": kwargs.get("called_station_id", ""),
            "timestamp": utc_now().isoformat(),
        }

        self._accounting_records.append(accounting_record)
        return accounting_record

    async def update_accounting(self, **kwargs) -> Dict[str, Any]:
        """Update RADIUS accounting (interim update)."""
        session_id = kwargs.get("session_id")
        username = kwargs["username"]

        if not session_id:
            session_id = self._active_sessions.get(username)

        if not session_id or session_id not in self._sessions:
            raise RADIUSError(f"Session not found for user: {username}")

        session = self._sessions[session_id]
        session.update({
            "bytes_in": kwargs.get("bytes_in", session["bytes_in"]),
            "bytes_out": kwargs.get("bytes_out", session["bytes_out"]),
            "packets_in": kwargs.get("packets_in", session["packets_in"]),
            "packets_out": kwargs.get("packets_out", session["packets_out"]),
            "last_update": utc_now().isoformat(),
        })

        accounting_record = {
            "record_id": str(uuid4()),
            "session_id": session_id,
            "username": username,
            "acct_status_type": "Interim-Update",
            "bytes_in": session["bytes_in"],
            "bytes_out": session["bytes_out"],
            "packets_in": session["packets_in"],
            "packets_out": session["packets_out"],
            "session_time": kwargs.get("session_time", 0),
            "timestamp": utc_now().isoformat(),
        }

        self._accounting_records.append(accounting_record)
        return accounting_record

    async def stop_accounting(self, **kwargs) -> Dict[str, Any]:
        """Stop RADIUS accounting session."""
        session_id = kwargs.get("session_id")
        username = kwargs["username"]

        if not session_id:
            session_id = self._active_sessions.get(username)

        if not session_id or session_id not in self._sessions:
            raise RADIUSError(f"Session not found for user: {username}")

        session = self._sessions[session_id]
        session["status"] = "stopped"
        session["stop_time"] = utc_now().isoformat()
        session["terminate_cause"] = kwargs.get("terminate_cause", "User-Request")

        accounting_record = {
            "record_id": str(uuid4()),
            "session_id": session_id,
            "username": username,
            "acct_status_type": "Stop",
            "bytes_in": kwargs.get("bytes_in", session["bytes_in"]),
            "bytes_out": kwargs.get("bytes_out", session["bytes_out"]),
            "packets_in": kwargs.get("packets_in", session["packets_in"]),
            "packets_out": kwargs.get("packets_out", session["packets_out"]),
            "session_time": kwargs.get("session_time", 0),
            "terminate_cause": session["terminate_cause"],
            "timestamp": utc_now().isoformat(),
        }

        self._accounting_records.append(accounting_record)

        # Remove from active sessions
        if username in self._active_sessions:
            del self._active_sessions[username]

        return accounting_record

    async def send_coa(self, **kwargs) -> Dict[str, Any]:
        """Send Change of Authorization (CoA) request."""
        session_id = kwargs.get("session_id")
        username = kwargs.get("username")

        if not session_id and username:
            session_id = self._active_sessions.get(username)

        if not session_id or session_id not in self._sessions:
            raise CoAFailedError(session_id or "unknown", "Session not found")

        session = self._sessions[session_id]
        coa_type = kwargs.get("coa_type", "CoA-Request")

        # Apply CoA changes
        if "filter_id" in kwargs:
            session["filter_id"] = kwargs["filter_id"]

        if "session_timeout" in kwargs:
            session["session_timeout"] = kwargs["session_timeout"]

        if "idle_timeout" in kwargs:
            session["idle_timeout"] = kwargs["idle_timeout"]

        session["last_update"] = utc_now().isoformat()

        return {
            "session_id": session_id,
            "username": session["username"],
            "coa_type": coa_type,
            "status": "success",
            "applied_changes": {k: v for k, v in kwargs.items()
                              if k in ["filter_id", "session_timeout", "idle_timeout"]},
            "timestamp": utc_now().isoformat(),
        }


class RADIUSSDK:
    """Minimal, reusable SDK for RADIUS AAA operations."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = RADIUSService()

    async def create_user(
        self,
        username: str,
        password: str,
        filter_id: Optional[str] = None,
        reply_attributes: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create RADIUS user."""
        user = {
            "username": username,
            "password": password,
            "filter_id": filter_id,
            "reply_attributes": reply_attributes or {},
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._service._users[username] = user

        return {
            "username": user["username"],
            "filter_id": user["filter_id"],
            "reply_attributes": user["reply_attributes"],
            "status": user["status"],
            "created_at": user["created_at"],
        }

    async def authenticate(
        self,
        username: str,
        password: str,
        nas_ip: str,
        nas_port: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Authenticate user via RADIUS."""
        result = await self._service.authenticate_user(
            username=username,
            password=password,
            nas_ip=nas_ip,
            nas_port=nas_port,
            **kwargs
        )

        return {
            "session_id": result["session_id"],
            "access_accept": result["access_accept"],
            "reply_attributes": result["reply_attributes"],
            "session_timeout": result["session_timeout"],
            "idle_timeout": result["idle_timeout"],
            "filter_id": result["filter_id"],
        }

    async def start_session(
        self,
        username: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Start RADIUS accounting session."""
        record = await self._service.start_accounting(
            username=username,
            session_id=session_id,
            **kwargs
        )

        return {
            "record_id": record["record_id"],
            "session_id": record["session_id"],
            "username": record["username"],
            "acct_status_type": record["acct_status_type"],
            "timestamp": record["timestamp"],
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
        record = await self._service.update_accounting(
            username=username,
            session_id=session_id,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            session_time=session_time,
            **kwargs
        )

        return {
            "record_id": record["record_id"],
            "session_id": record["session_id"],
            "username": record["username"],
            "bytes_in": record["bytes_in"],
            "bytes_out": record["bytes_out"],
            "session_time": record["session_time"],
            "timestamp": record["timestamp"],
        }

    async def stop_session(
        self,
        username: str,
        terminate_cause: str = "User-Request",
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Stop RADIUS accounting session."""
        record = await self._service.stop_accounting(
            username=username,
            session_id=session_id,
            terminate_cause=terminate_cause,
            **kwargs
        )

        return {
            "record_id": record["record_id"],
            "session_id": record["session_id"],
            "username": record["username"],
            "terminate_cause": record["terminate_cause"],
            "bytes_in": record["bytes_in"],
            "bytes_out": record["bytes_out"],
            "timestamp": record["timestamp"],
        }

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
        result = await self._service.send_coa(
            username=username,
            session_id=session_id,
            filter_id=filter_id,
            session_timeout=session_timeout,
            idle_timeout=idle_timeout,
            **kwargs
        )

        return {
            "session_id": result["session_id"],
            "username": result["username"],
            "coa_type": result["coa_type"],
            "status": result["status"],
            "applied_changes": result["applied_changes"],
            "timestamp": result["timestamp"],
        }

    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active RADIUS sessions."""
        active_sessions = [
            session for session in self._service._sessions.values()
            if session["status"] == "active"
        ]

        return [
            {
                "session_id": session["session_id"],
                "username": session["username"],
                "nas_ip": session["nas_ip"],
                "nas_port": session["nas_port"],
                "framed_ip": session["framed_ip"],
                "start_time": session["start_time"],
                "last_update": session["last_update"],
                "bytes_in": session["bytes_in"],
                "bytes_out": session["bytes_out"],
            }
            for session in active_sessions
        ]

    async def get_user_session(self, username: str) -> Optional[Dict[str, Any]]:
        """Get active session for user."""
        session_id = self._service._active_sessions.get(username)
        if not session_id:
            return None

        session = self._service._sessions.get(session_id)
        if not session or session["status"] != "active":
            return None

        return {
            "session_id": session["session_id"],
            "username": session["username"],
            "nas_ip": session["nas_ip"],
            "nas_port": session["nas_port"],
            "framed_ip": session["framed_ip"],
            "start_time": session["start_time"],
            "last_update": session["last_update"],
            "bytes_in": session["bytes_in"],
            "bytes_out": session["bytes_out"],
            "filter_id": session["filter_id"],
        }

    async def disconnect_user(self, username: str, reason: str = "Admin-Disconnect") -> Dict[str, Any]:
        """Disconnect user session."""
        session_id = self._service._active_sessions.get(username)
        if not session_id:
            raise RADIUSError(f"No active session for user: {username}")

        # Send CoA disconnect
        result = await self._service.send_coa(
            username=username,
            session_id=session_id,
            coa_type="Disconnect-Request"
        )

        # Stop accounting
        await self._service.stop_accounting(
            username=username,
            session_id=session_id,
            terminate_cause=reason
        )

        return {
            "username": username,
            "session_id": session_id,
            "status": "disconnected",
            "reason": reason,
            "timestamp": utc_now().isoformat(),
        }
