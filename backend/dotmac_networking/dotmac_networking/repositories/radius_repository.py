"""
PostgreSQL repository for RADIUS data.
Replaces in-memory RADIUS storage with persistent database.
"""

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4
import asyncpg

from .base_repository import BaseRepository


class RadiusRepository(BaseRepository):
    """PostgreSQL repository for RADIUS users, sessions, and accounting."""
    
    @property
    def table_name(self) -> str:
        return "radius_sessions"
    
    @property 
    def id_field(self) -> str:
        return "session_id"
    
    async def create_table_if_not_exists(self) -> None:
        """Create RADIUS tables."""
        async with self.db_pool.acquire() as conn:
            # RADIUS Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS radius_users (
                    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    filter_id TEXT,
                    reply_attributes JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(tenant_id, username)
                );
                CREATE INDEX IF NOT EXISTS idx_radius_users_tenant ON radius_users(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_radius_users_username ON radius_users(tenant_id, username);
            """)
            
            # RADIUS Sessions table  
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS radius_sessions (
                    session_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    nas_ip TEXT,
                    nas_port TEXT,
                    calling_station_id TEXT,
                    called_station_id TEXT,
                    framed_ip TEXT,
                    session_timeout INTEGER DEFAULT 3600,
                    idle_timeout INTEGER DEFAULT 600,
                    filter_id TEXT,
                    reply_attributes JSONB DEFAULT '{}',
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
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_radius_sessions_tenant ON radius_sessions(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_radius_sessions_username ON radius_sessions(tenant_id, username);
                CREATE INDEX IF NOT EXISTS idx_radius_sessions_status ON radius_sessions(status);
                CREATE INDEX IF NOT EXISTS idx_radius_sessions_active ON radius_sessions(tenant_id, status) WHERE status = 'active';
            """)
            
            # RADIUS Accounting Records table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS radius_accounting (
                    record_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    acct_status_type TEXT NOT NULL,
                    nas_ip TEXT,
                    nas_port TEXT,
                    framed_ip TEXT,
                    calling_station_id TEXT,
                    called_station_id TEXT,
                    bytes_in BIGINT DEFAULT 0,
                    bytes_out BIGINT DEFAULT 0,
                    packets_in BIGINT DEFAULT 0,
                    packets_out BIGINT DEFAULT 0,
                    session_time INTEGER DEFAULT 0,
                    terminate_cause TEXT,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_radius_accounting_tenant ON radius_accounting(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_radius_accounting_session ON radius_accounting(session_id);
                CREATE INDEX IF NOT EXISTS idx_radius_accounting_username ON radius_accounting(tenant_id, username);
                CREATE INDEX IF NOT EXISTS idx_radius_accounting_type ON radius_accounting(acct_status_type);
            """)
    
    async def create_user(self, username: str, password: str, **kwargs) -> Dict[str, Any]:
        """Create RADIUS user."""
        await self.create_table_if_not_exists()
        
        data = {
            'username': username,
            'password': password,
            'status': kwargs.get('status', 'active'),
            'filter_id': kwargs.get('filter_id'),
            'reply_attributes': kwargs.get('reply_attributes', {}),
            'tenant_id': self.tenant_id,
            'created_at': kwargs.get('created_at'),
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        async with self.db_pool.acquire() as conn:
            try:
                user = await conn.fetchrow("""
                    INSERT INTO radius_users (tenant_id, username, password, status, filter_id, reply_attributes)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                """, self.tenant_id, username, password, data.get('status'), data.get('filter_id'), 
                    json.dumps(data.get('reply_attributes', {})))
                
                return dict(user)
            except asyncpg.UniqueViolationError:
                raise ValueError(f"User already exists: {username}")
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user data if valid."""
        async with self.db_pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT * FROM radius_users 
                WHERE tenant_id = $1 AND username = $2 AND password = $3 AND status = 'active'
            """, self.tenant_id, username, password)
            
            if user:
                user_dict = dict(user)
                # Parse JSON fields
                user_dict['reply_attributes'] = json.loads(user_dict['reply_attributes'] or '{}')
                return user_dict
            return None
    
    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create RADIUS session."""
        session_id = session_data.get('session_id', str(uuid4()))
        
        async with self.db_pool.acquire() as conn:
            session = await conn.fetchrow("""
                INSERT INTO radius_sessions (
                    session_id, tenant_id, username, nas_ip, nas_port,
                    calling_station_id, called_station_id, framed_ip,
                    session_timeout, idle_timeout, filter_id, reply_attributes, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING *
            """, session_id, self.tenant_id, session_data['username'],
                session_data.get('nas_ip'), session_data.get('nas_port'),
                session_data.get('calling_station_id'), session_data.get('called_station_id'),
                session_data.get('framed_ip'), session_data.get('session_timeout', 3600),
                session_data.get('idle_timeout', 600), session_data.get('filter_id'),
                json.dumps(session_data.get('reply_attributes', {})), 'active')
            
            session_dict = dict(session)
            session_dict['reply_attributes'] = json.loads(session_dict['reply_attributes'] or '{}')
            return session_dict
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active RADIUS sessions."""
        async with self.db_pool.acquire() as conn:
            sessions = await conn.fetch("""
                SELECT * FROM radius_sessions 
                WHERE tenant_id = $1 AND status = 'active'
                ORDER BY start_time DESC
            """, self.tenant_id)
            
            result = []
            for session in sessions:
                session_dict = dict(session)
                session_dict['reply_attributes'] = json.loads(session_dict['reply_attributes'] or '{}')
                result.append(session_dict)
            return result
    
    async def get_user_session(self, username: str) -> Optional[Dict[str, Any]]:
        """Get active session for user."""
        async with self.db_pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT * FROM radius_sessions 
                WHERE tenant_id = $1 AND username = $2 AND status = 'active'
                ORDER BY start_time DESC LIMIT 1
            """, self.tenant_id, username)
            
            if session:
                session_dict = dict(session)
                session_dict['reply_attributes'] = json.loads(session_dict['reply_attributes'] or '{}')
                return session_dict
            return None
    
    async def update_session(self, session_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update session with accounting data."""
        async with self.db_pool.acquire() as conn:
            session = await conn.fetchrow("""
                UPDATE radius_sessions SET
                    bytes_in = COALESCE($3, bytes_in),
                    bytes_out = COALESCE($4, bytes_out),
                    packets_in = COALESCE($5, packets_in),
                    packets_out = COALESCE($6, packets_out),
                    last_update = NOW(),
                    updated_at = NOW()
                WHERE session_id = $1 AND tenant_id = $2
                RETURNING *
            """, session_id, self.tenant_id,
                update_data.get('bytes_in'),
                update_data.get('bytes_out'),
                update_data.get('packets_in'),
                update_data.get('packets_out'))
            
            if session:
                session_dict = dict(session)
                session_dict['reply_attributes'] = json.loads(session_dict['reply_attributes'] or '{}')
                return session_dict
            return None
    
    async def stop_session(self, session_id: str, terminate_cause: str = "User-Request") -> Optional[Dict[str, Any]]:
        """Stop RADIUS session."""
        async with self.db_pool.acquire() as conn:
            session = await conn.fetchrow("""
                UPDATE radius_sessions SET
                    status = 'stopped',
                    stop_time = NOW(),
                    terminate_cause = $3,
                    updated_at = NOW()
                WHERE session_id = $1 AND tenant_id = $2
                RETURNING *
            """, session_id, self.tenant_id, terminate_cause)
            
            if session:
                session_dict = dict(session)
                session_dict['reply_attributes'] = json.loads(session_dict['reply_attributes'] or '{}')
                return session_dict
            return None
    
    async def add_accounting_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add accounting record."""
        record_id = record_data.get('record_id', str(uuid4()))
        
        async with self.db_pool.acquire() as conn:
            record = await conn.fetchrow("""
                INSERT INTO radius_accounting (
                    record_id, tenant_id, session_id, username, acct_status_type,
                    nas_ip, nas_port, framed_ip, calling_station_id, called_station_id,
                    bytes_in, bytes_out, packets_in, packets_out, session_time, terminate_cause
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING *
            """, record_id, self.tenant_id, record_data['session_id'], record_data['username'],
                record_data['acct_status_type'], record_data.get('nas_ip'), record_data.get('nas_port'),
                record_data.get('framed_ip'), record_data.get('calling_station_id'), 
                record_data.get('called_station_id'), record_data.get('bytes_in', 0),
                record_data.get('bytes_out', 0), record_data.get('packets_in', 0),
                record_data.get('packets_out', 0), record_data.get('session_time', 0),
                record_data.get('terminate_cause'))
            
            return dict(record)
    
    def _deserialize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON fields in RADIUS records."""
        if 'reply_attributes' in record and isinstance(record['reply_attributes'], str):
            record['reply_attributes'] = json.loads(record['reply_attributes'] or '{}')
        return record