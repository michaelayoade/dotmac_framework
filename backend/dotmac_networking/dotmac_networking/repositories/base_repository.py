"""
Base repository pattern for PostgreSQL persistence.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
import asyncpg
import json
from datetime import datetime, timezone

T = TypeVar('T')


class BaseRepository(ABC):
    """Base repository with PostgreSQL persistence."""
    
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool
    
    @property
    @abstractmethod
    def table_name(self) -> str:
        """Table name for this repository."""
        pass
        
    @property
    @abstractmethod
    def id_field(self) -> str:
        """Primary key field name."""
        pass
    
    async def create_table_if_not_exists(self) -> None:
        """Create table if it doesn't exist. Override in subclasses."""
        pass
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new record."""
        await self.create_table_if_not_exists()
        
        # Add tenant_id and timestamps
        data = data.copy()
        data['tenant_id'] = self.tenant_id
        data['created_at'] = datetime.now(timezone.utc)
        data['updated_at'] = datetime.now(timezone.utc)
        
        # Convert complex objects to JSON
        data = self._serialize_data(data)
        
        # Build INSERT query
        fields = list(data.keys())
        placeholders = [f'${i+1}' for i in range(len(fields))]
        values = list(data.values())
        
        query = f"""
            INSERT INTO {self.table_name} ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        
        async with self.db_pool.acquire() as conn:
            record = await conn.fetchrow(query, *values)
            return dict(record) if record else {}
    
    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get record by ID."""
        query = f"""
            SELECT * FROM {self.table_name} 
            WHERE {self.id_field} = $1 AND tenant_id = $2
        """
        
        async with self.db_pool.acquire() as conn:
            record = await conn.fetchrow(query, record_id, self.tenant_id)
            return self._deserialize_record(dict(record)) if record else None
    
    async def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all records for tenant."""
        base_query = f"SELECT * FROM {self.table_name} WHERE tenant_id = $1"
        params = [self.tenant_id]
        
        if status:
            base_query += " AND status = $2"
            params.append(status)
            
        base_query += " ORDER BY created_at DESC"
        
        async with self.db_pool.acquire() as conn:
            records = await conn.fetch(base_query, *params)
            return [self._deserialize_record(dict(record)) for record in records]
    
    async def update(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update record."""
        data = data.copy()
        data['updated_at'] = datetime.now(timezone.utc)
        data = self._serialize_data(data)
        
        # Build UPDATE query
        set_clauses = [f"{field} = ${i+2}" for i, field in enumerate(data.keys())]
        values = [record_id, self.tenant_id] + list(data.values())
        
        query = f"""
            UPDATE {self.table_name} 
            SET {', '.join(set_clauses)}
            WHERE {self.id_field} = $1 AND tenant_id = $2
            RETURNING *
        """
        
        async with self.db_pool.acquire() as conn:
            record = await conn.fetchrow(query, *values)
            return self._deserialize_record(dict(record)) if record else None
    
    async def delete(self, record_id: str) -> bool:
        """Delete record."""
        query = f"""
            DELETE FROM {self.table_name} 
            WHERE {self.id_field} = $1 AND tenant_id = $2
        """
        
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(query, record_id, self.tenant_id)
            return result.split()[-1] == '1'  # Check if 1 row affected
    
    async def count(self, status: Optional[str] = None) -> int:
        """Count records."""
        base_query = f"SELECT COUNT(*) FROM {self.table_name} WHERE tenant_id = $1"
        params = [self.tenant_id]
        
        if status:
            base_query += " AND status = $2"
            params.append(status)
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(base_query, *params)
            return result or 0
    
    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert complex objects to JSON for storage."""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                serialized[key] = json.dumps(value)
            elif isinstance(value, datetime):
                serialized[key] = value
            else:
                serialized[key] = value
        return serialized
    
    def _deserialize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON fields back to objects."""
        # Override in subclasses to handle specific JSON fields
        return record
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute custom query."""
        async with self.db_pool.acquire() as conn:
            records = await conn.fetch(query, *args)
            return [dict(record) for record in records]
    
    async def execute_single_query(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute query that returns single record."""
        async with self.db_pool.acquire() as conn:
            record = await conn.fetchrow(query, *args)
            return dict(record) if record else None