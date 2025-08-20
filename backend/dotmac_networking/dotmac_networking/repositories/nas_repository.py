"""
PostgreSQL repository for NAS (Network Access Server) data.
"""

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4
import asyncpg

from .base_repository import BaseRepository


class NASRepository(BaseRepository):
    """PostgreSQL repository for NAS devices and service profiles."""
    
    @property
    def table_name(self) -> str:
        return "nas_devices"
    
    @property
    def id_field(self) -> str:
        return "nas_id"
    
    async def create_table_if_not_exists(self) -> None:
        """Create NAS tables."""
        async with self.db_pool.acquire() as conn:
            # NAS Devices table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS nas_devices (
                    nas_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    nas_name TEXT NOT NULL,
                    nas_type TEXT DEFAULT 'bng',
                    ip_address INET NOT NULL,
                    vendor TEXT,
                    model TEXT,
                    software_version TEXT,
                    radius_secret TEXT,
                    coa_port INTEGER DEFAULT 3799,
                    snmp_community TEXT DEFAULT 'public',
                    management_vlan INTEGER,
                    service_vlans JSONB DEFAULT '[]',
                    max_sessions INTEGER DEFAULT 10000,
                    current_sessions INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_nas_devices_tenant ON nas_devices(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_nas_devices_ip ON nas_devices(ip_address);
                CREATE INDEX IF NOT EXISTS idx_nas_devices_type ON nas_devices(nas_type);
            """)
            
            # Service Profiles table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS service_profiles (
                    profile_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    profile_name TEXT NOT NULL,
                    service_type TEXT DEFAULT 'broadband',
                    download_speed INTEGER DEFAULT 0,
                    upload_speed INTEGER DEFAULT 0,
                    burst_download INTEGER,
                    burst_upload INTEGER,
                    priority TEXT DEFAULT 'normal',
                    vlan_id INTEGER,
                    ip_pool TEXT,
                    dns_servers JSONB DEFAULT '[]',
                    filter_rules JSONB DEFAULT '[]',
                    qos_policy JSONB DEFAULT '{}',
                    session_timeout INTEGER DEFAULT 0,
                    idle_timeout INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_service_profiles_tenant ON service_profiles(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_service_profiles_type ON service_profiles(service_type);
            """)
            
            # NAS Sessions table (separate from RADIUS sessions for NAS-specific data)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS nas_sessions (
                    session_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    nas_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    calling_station_id TEXT,
                    called_station_id TEXT,
                    nas_port TEXT,
                    nas_port_type TEXT DEFAULT 'Ethernet',
                    framed_ip INET,
                    framed_netmask INET,
                    service_profile_id TEXT,
                    vlan_id INTEGER,
                    session_timeout INTEGER DEFAULT 0,
                    idle_timeout INTEGER DEFAULT 0,
                    acct_session_id TEXT,
                    status TEXT DEFAULT 'active',
                    start_time TIMESTAMPTZ DEFAULT NOW(),
                    stop_time TIMESTAMPTZ,
                    last_update TIMESTAMPTZ DEFAULT NOW(),
                    bytes_in BIGINT DEFAULT 0,
                    bytes_out BIGINT DEFAULT 0,
                    packets_in BIGINT DEFAULT 0,
                    packets_out BIGINT DEFAULT 0,
                    terminate_cause TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (nas_id) REFERENCES nas_devices(nas_id),
                    FOREIGN KEY (service_profile_id) REFERENCES service_profiles(profile_id)
                );
                CREATE INDEX IF NOT EXISTS idx_nas_sessions_tenant ON nas_sessions(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_nas_sessions_nas ON nas_sessions(nas_id);
                CREATE INDEX IF NOT EXISTS idx_nas_sessions_username ON nas_sessions(username);
                CREATE INDEX IF NOT EXISTS idx_nas_sessions_status ON nas_sessions(status);
            """)
    
    async def register_nas(self, nas_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register NAS device."""
        await self.create_table_if_not_exists()
        
        nas_id = nas_data.get('nas_id', str(uuid4()))
        
        async with self.db_pool.acquire() as conn:
            try:
                nas = await conn.fetchrow("""
                    INSERT INTO nas_devices (
                        nas_id, tenant_id, nas_name, nas_type, ip_address, vendor, model,
                        software_version, radius_secret, coa_port, snmp_community,
                        management_vlan, service_vlans, max_sessions, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    RETURNING *
                """, nas_id, self.tenant_id, nas_data.get('nas_name'), nas_data.get('nas_type', 'bng'),
                    nas_data['ip_address'], nas_data.get('vendor'), nas_data.get('model'),
                    nas_data.get('software_version'), nas_data.get('radius_secret'),
                    nas_data.get('coa_port', 3799), nas_data.get('snmp_community', 'public'),
                    nas_data.get('management_vlan'), json.dumps(nas_data.get('service_vlans', [])),
                    nas_data.get('max_sessions', 10000), nas_data.get('status', 'active'))
                
                nas_dict = dict(nas)
                nas_dict['service_vlans'] = json.loads(nas_dict['service_vlans'] or '[]')
                return nas_dict
                
            except asyncpg.UniqueViolationError:
                raise ValueError(f"NAS already registered: {nas_id}")
    
    async def create_service_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create service profile."""
        await self.create_table_if_not_exists()
        
        profile_id = profile_data.get('profile_id', str(uuid4()))
        
        async with self.db_pool.acquire() as conn:
            profile = await conn.fetchrow("""
                INSERT INTO service_profiles (
                    profile_id, tenant_id, profile_name, service_type, download_speed, upload_speed,
                    burst_download, burst_upload, priority, vlan_id, ip_pool, dns_servers,
                    filter_rules, qos_policy, session_timeout, idle_timeout, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                RETURNING *
            """, profile_id, self.tenant_id, profile_data['profile_name'], 
                profile_data.get('service_type', 'broadband'), profile_data.get('download_speed', 0),
                profile_data.get('upload_speed', 0), profile_data.get('burst_download'),
                profile_data.get('burst_upload'), profile_data.get('priority', 'normal'),
                profile_data.get('vlan_id'), profile_data.get('ip_pool'),
                json.dumps(profile_data.get('dns_servers', [])),
                json.dumps(profile_data.get('filter_rules', [])),
                json.dumps(profile_data.get('qos_policy', {})),
                profile_data.get('session_timeout', 0), profile_data.get('idle_timeout', 0),
                profile_data.get('status', 'active'))
            
            profile_dict = dict(profile)
            profile_dict['dns_servers'] = json.loads(profile_dict['dns_servers'] or '[]')
            profile_dict['filter_rules'] = json.loads(profile_dict['filter_rules'] or '[]')
            profile_dict['qos_policy'] = json.loads(profile_dict['qos_policy'] or '{}')
            return profile_dict
    
    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create NAS session."""
        await self.create_table_if_not_exists()
        
        session_id = session_data.get('session_id', str(uuid4()))
        
        # Increment session count for NAS
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE nas_devices SET 
                    current_sessions = current_sessions + 1,
                    updated_at = NOW()
                WHERE nas_id = $1 AND tenant_id = $2
            """, session_data['nas_id'], self.tenant_id)
            
            session = await conn.fetchrow("""
                INSERT INTO nas_sessions (
                    session_id, tenant_id, nas_id, username, calling_station_id, called_station_id,
                    nas_port, nas_port_type, framed_ip, framed_netmask, service_profile_id, vlan_id,
                    session_timeout, idle_timeout, acct_session_id, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING *
            """, session_id, self.tenant_id, session_data['nas_id'], session_data['username'],
                session_data.get('calling_station_id'), session_data.get('called_station_id'),
                session_data.get('nas_port'), session_data.get('nas_port_type', 'Ethernet'),
                session_data.get('framed_ip'), session_data.get('framed_netmask'),
                session_data.get('service_profile_id'), session_data.get('vlan_id'),
                session_data.get('session_timeout', 0), session_data.get('idle_timeout', 0),
                session_data.get('acct_session_id'), 'active')
            
            return dict(session)
    
    async def get_nas_sessions(self, nas_id: str, status: str = 'active') -> List[Dict[str, Any]]:
        """Get sessions for NAS device."""
        async with self.db_pool.acquire() as conn:
            sessions = await conn.fetch("""
                SELECT * FROM nas_sessions 
                WHERE tenant_id = $1 AND nas_id = $2 AND status = $3
                ORDER BY start_time DESC
            """, self.tenant_id, nas_id, status)
            
            return [dict(session) for session in sessions]
    
    async def update_session_stats(self, session_id: str, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update session statistics."""
        async with self.db_pool.acquire() as conn:
            session = await conn.fetchrow("""
                UPDATE nas_sessions SET
                    bytes_in = $3,
                    bytes_out = $4,
                    packets_in = $5,
                    packets_out = $6,
                    last_update = NOW(),
                    updated_at = NOW()
                WHERE session_id = $1 AND tenant_id = $2
                RETURNING *
            """, session_id, self.tenant_id, stats.get('bytes_in', 0), stats.get('bytes_out', 0),
                stats.get('packets_in', 0), stats.get('packets_out', 0))
            
            return dict(session) if session else None
    
    async def terminate_session(self, session_id: str, reason: str = "User-Request") -> Optional[Dict[str, Any]]:
        """Terminate NAS session."""
        async with self.db_pool.acquire() as conn:
            # Get session to find NAS ID
            session = await conn.fetchrow("""
                SELECT nas_id FROM nas_sessions 
                WHERE session_id = $1 AND tenant_id = $2
            """, session_id, self.tenant_id)
            
            if not session:
                return None
                
            # Update session and decrement NAS session count
            await conn.execute("""
                UPDATE nas_devices SET 
                    current_sessions = current_sessions - 1,
                    updated_at = NOW()
                WHERE nas_id = $1 AND tenant_id = $2
            """, session['nas_id'], self.tenant_id)
            
            updated_session = await conn.fetchrow("""
                UPDATE nas_sessions SET
                    status = 'terminated',
                    stop_time = NOW(),
                    terminate_cause = $3,
                    updated_at = NOW()
                WHERE session_id = $1 AND tenant_id = $2
                RETURNING *
            """, session_id, self.tenant_id, reason)
            
            return dict(updated_session) if updated_session else None
    
    async def list_service_profiles(self) -> List[Dict[str, Any]]:
        """List all service profiles."""
        async with self.db_pool.acquire() as conn:
            profiles = await conn.fetch("""
                SELECT * FROM service_profiles 
                WHERE tenant_id = $1 
                ORDER BY profile_name
            """, self.tenant_id)
            
            result = []
            for profile in profiles:
                profile_dict = dict(profile)
                profile_dict['dns_servers'] = json.loads(profile_dict['dns_servers'] or '[]')
                profile_dict['filter_rules'] = json.loads(profile_dict['filter_rules'] or '[]')
                profile_dict['qos_policy'] = json.loads(profile_dict['qos_policy'] or '{}')
                result.append(profile_dict)
            
            return result
    
    def _deserialize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON fields in NAS records."""
        json_fields = ['service_vlans', 'dns_servers', 'filter_rules', 'qos_policy']
        
        for field in json_fields:
            if field in record and isinstance(record[field], str):
                record[field] = json.loads(record[field] or '{}' if field == 'qos_policy' else '[]')
        
        return record