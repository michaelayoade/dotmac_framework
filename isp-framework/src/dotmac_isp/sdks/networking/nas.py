"""
NAS SDK - BNG/BRAS/NAS endpoints management
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import NetworkingError


class NASService:
    """In-memory service for NAS (Network Access Server) operations."""

    def __init__(self):
        """  Init   operation."""
        self._nas_devices: Dict[str, Dict[str, Any]] = {}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._service_profiles: Dict[str, Dict[str, Any]] = {}

    async def register_nas(self, **kwargs) -> Dict[str, Any]:
        """Register NAS device."""
        nas_id = kwargs.get("nas_id") or str(uuid4())

        if nas_id in self._nas_devices:
            raise NetworkingError(f"NAS already registered: {nas_id}")

        nas = {
            "nas_id": nas_id,
            "nas_name": kwargs.get("nas_name", ""),
            "nas_type": kwargs.get("nas_type", "bng"),  # bng, bras, nas, olt
            "ip_address": kwargs["ip_address"],
            "vendor": kwargs.get("vendor", ""),
            "model": kwargs.get("model", ""),
            "software_version": kwargs.get("software_version", ""),
            "radius_secret": kwargs.get("radius_secret", ""),
            "coa_port": kwargs.get("coa_port", 3799),
            "snmp_community": kwargs.get("snmp_community", "public"),
            "management_vlan": kwargs.get("management_vlan"),
            "service_vlans": kwargs.get("service_vlans", []),
            "max_sessions": kwargs.get("max_sessions", 10000),
            "current_sessions": 0,
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._nas_devices[nas_id] = nas
        return nas

    async def create_service_profile(self, **kwargs) -> Dict[str, Any]:
        """Create service profile for NAS."""
        profile_id = kwargs.get("profile_id") or str(uuid4())

        profile = {
            "profile_id": profile_id,
            "profile_name": kwargs["profile_name"],
            "service_type": kwargs.get("service_type", "broadband"),
            "download_speed": kwargs.get("download_speed", 0),
            "upload_speed": kwargs.get("upload_speed", 0),
            "burst_download": kwargs.get("burst_download"),
            "burst_upload": kwargs.get("burst_upload"),
            "priority": kwargs.get("priority", "normal"),
            "vlan_id": kwargs.get("vlan_id"),
            "ip_pool": kwargs.get("ip_pool", ""),
            "dns_servers": kwargs.get("dns_servers", []),
            "filter_rules": kwargs.get("filter_rules", []),
            "qos_policy": kwargs.get("qos_policy", {}),
            "session_timeout": kwargs.get("session_timeout", 0),
            "idle_timeout": kwargs.get("idle_timeout", 0),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._service_profiles[profile_id] = profile
        return profile

    async def create_session(self, **kwargs) -> Dict[str, Any]:
        """Create NAS session."""
        session_id = kwargs.get("session_id") or str(uuid4())
        nas_id = kwargs["nas_id"]

        if nas_id not in self._nas_devices:
            raise NetworkingError(f"NAS not found: {nas_id}")

        session = {
            "session_id": session_id,
            "nas_id": nas_id,
            "username": kwargs["username"],
            "calling_station_id": kwargs.get("calling_station_id", ""),
            "called_station_id": kwargs.get("called_station_id", ""),
            "nas_port": kwargs.get("nas_port", ""),
            "nas_port_type": kwargs.get("nas_port_type", "Ethernet"),
            "framed_ip": kwargs.get("framed_ip", ""),
            "framed_netmask": kwargs.get("framed_netmask", "255.255.255.255"),
            "service_profile_id": kwargs.get("service_profile_id"),
            "vlan_id": kwargs.get("vlan_id"),
            "session_timeout": kwargs.get("session_timeout", 0),
            "idle_timeout": kwargs.get("idle_timeout", 0),
            "acct_session_id": kwargs.get("acct_session_id", ""),
            "status": "active",
            "start_time": utc_now().isoformat(),
            "last_update": utc_now().isoformat(),
            "bytes_in": 0,
            "bytes_out": 0,
            "packets_in": 0,
            "packets_out": 0,
        }

        self._sessions[session_id] = session

        # Update NAS session count
        self._nas_devices[nas_id]["current_sessions"] += 1

        return session


class NASSDK:
    """Minimal, reusable SDK for NAS management."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = NASService()

    async def register_nas_device(
        self,
        nas_name: str,
        nas_type: str,
        ip_address: str,
        vendor: str,
        model: str,
        radius_secret: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Register NAS device."""
        nas = await self._service.register_nas(
            nas_name=nas_name,
            nas_type=nas_type,
            ip_address=ip_address,
            vendor=vendor,
            model=model,
            radius_secret=radius_secret,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "nas_id": nas["nas_id"],
            "nas_name": nas["nas_name"],
            "nas_type": nas["nas_type"],
            "ip_address": nas["ip_address"],
            "vendor": nas["vendor"],
            "model": nas["model"],
            "software_version": nas["software_version"],
            "coa_port": nas["coa_port"],
            "max_sessions": nas["max_sessions"],
            "current_sessions": nas["current_sessions"],
            "status": nas["status"],
            "created_at": nas["created_at"],
        }

    async def create_service_profile(
        self,
        profile_name: str,
        service_type: str = "broadband",
        download_speed: int = 0,
        upload_speed: int = 0,
        vlan_id: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create service profile."""
        profile = await self._service.create_service_profile(
            profile_name=profile_name,
            service_type=service_type,
            download_speed=download_speed,
            upload_speed=upload_speed,
            vlan_id=vlan_id,
            **kwargs,
        )

        return {
            "profile_id": profile["profile_id"],
            "profile_name": profile["profile_name"],
            "service_type": profile["service_type"],
            "download_speed": profile["download_speed"],
            "upload_speed": profile["upload_speed"],
            "burst_download": profile["burst_download"],
            "burst_upload": profile["burst_upload"],
            "priority": profile["priority"],
            "vlan_id": profile["vlan_id"],
            "ip_pool": profile["ip_pool"],
            "session_timeout": profile["session_timeout"],
            "idle_timeout": profile["idle_timeout"],
            "status": profile["status"],
            "created_at": profile["created_at"],
        }

    async def create_session(
        self,
        nas_id: str,
        username: str,
        calling_station_id: Optional[str] = None,
        service_profile_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create NAS session."""
        session = await self._service.create_session(
            nas_id=nas_id,
            username=username,
            calling_station_id=calling_station_id,
            service_profile_id=service_profile_id,
            **kwargs,
        )

        return {
            "session_id": session["session_id"],
            "nas_id": session["nas_id"],
            "username": session["username"],
            "calling_station_id": session["calling_station_id"],
            "nas_port": session["nas_port"],
            "framed_ip": session["framed_ip"],
            "service_profile_id": session["service_profile_id"],
            "vlan_id": session["vlan_id"],
            "status": session["status"],
            "start_time": session["start_time"],
        }

    async def get_nas_device(self, nas_id: str) -> Optional[Dict[str, Any]]:
        """Get NAS device by ID."""
        nas = self._service._nas_devices.get(nas_id)
        if not nas:
            return None

        return {
            "nas_id": nas["nas_id"],
            "nas_name": nas["nas_name"],
            "nas_type": nas["nas_type"],
            "ip_address": nas["ip_address"],
            "vendor": nas["vendor"],
            "model": nas["model"],
            "software_version": nas["software_version"],
            "coa_port": nas["coa_port"],
            "snmp_community": nas["snmp_community"],
            "management_vlan": nas["management_vlan"],
            "service_vlans": nas["service_vlans"],
            "max_sessions": nas["max_sessions"],
            "current_sessions": nas["current_sessions"],
            "status": nas["status"],
            "created_at": nas["created_at"],
            "updated_at": nas["updated_at"],
        }

    async def get_nas_sessions(self, nas_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a NAS device."""
        sessions = [
            session
            for session in self._service._sessions.values()
            if session["nas_id"] == nas_id and session["status"] == "active"
        ]

        return [
            {
                "session_id": session["session_id"],
                "username": session["username"],
                "calling_station_id": session["calling_station_id"],
                "nas_port": session["nas_port"],
                "framed_ip": session["framed_ip"],
                "vlan_id": session["vlan_id"],
                "start_time": session["start_time"],
                "bytes_in": session["bytes_in"],
                "bytes_out": session["bytes_out"],
            }
            for session in sessions
        ]

    async def update_session_stats(
        self,
        session_id: str,
        bytes_in: int,
        bytes_out: int,
        packets_in: int = 0,
        packets_out: int = 0,
    ) -> Dict[str, Any]:
        """Update session statistics."""
        if session_id not in self._service._sessions:
            raise NetworkingError(f"Session not found: {session_id}")

        session = self._service._sessions[session_id]
        session.update(
            {
                "bytes_in": bytes_in,
                "bytes_out": bytes_out,
                "packets_in": packets_in,
                "packets_out": packets_out,
                "last_update": utc_now().isoformat(),
            }
        )

        return {
            "session_id": session_id,
            "bytes_in": session["bytes_in"],
            "bytes_out": session["bytes_out"],
            "packets_in": session["packets_in"],
            "packets_out": session["packets_out"],
            "last_update": session["last_update"],
        }

    async def terminate_session(
        self, session_id: str, reason: str = "User-Request"
    ) -> Dict[str, Any]:
        """Terminate NAS session."""
        if session_id not in self._service._sessions:
            raise NetworkingError(f"Session not found: {session_id}")

        session = self._service._sessions[session_id]
        nas_id = session["nas_id"]

        session.update(
            {
                "status": "terminated",
                "stop_time": utc_now().isoformat(),
                "terminate_cause": reason,
            }
        )

        # Update NAS session count
        if nas_id in self._service._nas_devices:
            self._service._nas_devices[nas_id]["current_sessions"] -= 1

        return {
            "session_id": session_id,
            "username": session["username"],
            "status": "terminated",
            "terminate_cause": reason,
            "stop_time": session["stop_time"],
            "session_duration": session.get("session_duration", 0),
            "bytes_in": session["bytes_in"],
            "bytes_out": session["bytes_out"],
        }

    async def list_nas_devices(self) -> List[Dict[str, Any]]:
        """List all NAS devices."""
        return [
            {
                "nas_id": nas["nas_id"],
                "nas_name": nas["nas_name"],
                "nas_type": nas["nas_type"],
                "ip_address": nas["ip_address"],
                "vendor": nas["vendor"],
                "model": nas["model"],
                "current_sessions": nas["current_sessions"],
                "max_sessions": nas["max_sessions"],
                "status": nas["status"],
            }
            for nas in self._service._nas_devices.values()
        ]

    async def get_service_profiles(self) -> List[Dict[str, Any]]:
        """Get all service profiles."""
        return [
            {
                "profile_id": profile["profile_id"],
                "profile_name": profile["profile_name"],
                "service_type": profile["service_type"],
                "download_speed": profile["download_speed"],
                "upload_speed": profile["upload_speed"],
                "priority": profile["priority"],
                "status": profile["status"],
            }
            for profile in self._service._service_profiles.values()
        ]
