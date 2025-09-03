"""
API Connection Manager - Centralized API connection management
Provides standardized API connection pooling and management following DRY patterns
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

import aiohttp
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.schemas.base_schemas import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseUpdateSchema,
)

logger = logging.getLogger(__name__)


class ConnectionCreateSchema(BaseCreateSchema):
    """Schema for creating API connections."""
    name: str
    base_url: str
    auth_type: str = "none"  # none, bearer, api_key, basic, oauth
    auth_config: Dict[str, Any] = {}
    headers: Dict[str, str] = {}
    timeout: int = 30
    max_retries: int = 3
    rate_limit: Optional[Dict[str, int]] = None
    enabled: bool = True
    description: Optional[str] = None


class ConnectionUpdateSchema(BaseUpdateSchema):
    """Schema for updating API connections."""
    name: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None
    max_retries: Optional[int] = None
    rate_limit: Optional[Dict[str, int]] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


class ConnectionResponseSchema(BaseResponseSchema):
    """Response schema for API connections."""
    name: str
    base_url: str
    auth_type: str
    timeout: int
    max_retries: int
    rate_limit: Optional[Dict[str, int]] = None
    enabled: bool
    description: Optional[str] = None
    status: str
    last_used: Optional[str] = None
    success_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0


class ConnectionPool:
    """Connection pool for managing HTTP sessions."""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.connection_stats: Dict[str, Dict[str, Any]] = {}
        
    async def get_session(
        self, 
        connection_id: str,
        connection_config: Dict[str, Any]
    ) -> aiohttp.ClientSession:
        """Get or create HTTP session for connection."""
        
        if connection_id not in self.sessions:
            # Create new session with connection-specific config
            timeout = aiohttp.ClientTimeout(total=connection_config.get("timeout", 30))
            headers = connection_config.get("headers", {})
            
            # Setup authentication headers
            auth_headers = await self._setup_auth_headers(connection_config)
            headers.update(auth_headers)
            
            session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=aiohttp.TCPConnector(limit=self.max_connections)
            )
            
            self.sessions[connection_id] = session
            self.connection_stats[connection_id] = {
                "created_at": datetime.now(timezone.utc),
                "requests_made": 0,
                "last_used": None
            }
            
            logger.info(f"Created new HTTP session for connection: {connection_id}")
        
        # Update last used timestamp
        self.connection_stats[connection_id]["last_used"] = datetime.now(timezone.utc)
        self.connection_stats[connection_id]["requests_made"] += 1
        
        return self.sessions[connection_id]
    
    async def _setup_auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Setup authentication headers based on auth type."""
        headers = {}
        auth_type = config.get("auth_type", "none")
        auth_config = config.get("auth_config", {})
        
        if auth_type == "bearer":
            token = auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
        elif auth_type == "api_key":
            api_key = auth_config.get("api_key")
            key_header = auth_config.get("key_header", "X-API-Key")
            if api_key:
                headers[key_header] = api_key
                
        elif auth_type == "basic":
            import base64
            username = auth_config.get("username")
            password = auth_config.get("password")
            if username and password:
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    async def close_session(self, connection_id: str):
        """Close specific session."""
        if connection_id in self.sessions:
            await self.sessions[connection_id].close()
            del self.sessions[connection_id]
            if connection_id in self.connection_stats:
                del self.connection_stats[connection_id]
            logger.info(f"Closed session for connection: {connection_id}")
    
    async def close_all(self):
        """Close all sessions."""
        for session in self.sessions.values():
            await session.close()
        self.sessions.clear()
        self.connection_stats.clear()
        logger.info("Closed all connection sessions")


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self):
        self.limits: Dict[str, Dict[str, Any]] = {}
    
    def set_limit(self, connection_id: str, requests: int, window_seconds: int):
        """Set rate limit for connection."""
        self.limits[connection_id] = {
            "requests": requests,
            "window_seconds": window_seconds,
            "request_times": []
        }
    
    async def check_rate_limit(self, connection_id: str) -> bool:
        """Check if request is within rate limit."""
        if connection_id not in self.limits:
            return True
        
        limit_config = self.limits[connection_id]
        current_time = datetime.now(timezone.utc)
        window_start = current_time - timedelta(seconds=limit_config["window_seconds"])
        
        # Remove old requests outside the window
        limit_config["request_times"] = [
            req_time for req_time in limit_config["request_times"]
            if req_time > window_start
        ]
        
        # Check if we're within the limit
        if len(limit_config["request_times"]) >= limit_config["requests"]:
            return False
        
        # Record this request
        limit_config["request_times"].append(current_time)
        return True


class ApiConnectionManager:
    """
    Central API connection management service following DRY patterns.
    Manages connection pools, authentication, and request routing.
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.pool = ConnectionPool()
        self.rate_limiter = RateLimiter()

    @standard_exception_handler
    async def create(
        self, 
        data: ConnectionCreateSchema, 
        user_id: UUID
    ) -> ConnectionResponseSchema:
        """Create a new API connection."""
        
        connection_id = str(uuid4())
        connection_config = {
            "id": connection_id,
            "name": data.name,
            "base_url": data.base_url.rstrip("/"),
            "auth_type": data.auth_type,
            "auth_config": data.auth_config,
            "headers": data.headers,
            "timeout": data.timeout,
            "max_retries": data.max_retries,
            "rate_limit": data.rate_limit,
            "enabled": data.enabled,
            "description": data.description,
            "status": "active" if data.enabled else "disabled",
            "last_used": None,
            "success_count": 0,
            "error_count": 0,
            "avg_response_time": 0.0,
            "created_by": str(user_id),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Setup rate limiting if configured
        if data.rate_limit:
            self.rate_limiter.set_limit(
                connection_id,
                data.rate_limit.get("requests", 100),
                data.rate_limit.get("window_seconds", 60)
            )
        
        self.connections[connection_id] = connection_config
        logger.info(f"Created API connection: {data.name} -> {data.base_url}")
        
        return self._connection_to_response(connection_config)

    @standard_exception_handler
    async def get_by_id(
        self, 
        connection_id: UUID, 
        user_id: UUID
    ) -> ConnectionResponseSchema:
        """Get API connection by ID."""
        connection_str = str(connection_id)
        
        if connection_str not in self.connections:
            raise ValueError(f"API connection not found: {connection_str}")
            
        connection_config = self.connections[connection_str]
        return self._connection_to_response(connection_config)

    @standard_exception_handler
    async def update(
        self, 
        connection_id: UUID, 
        data: ConnectionUpdateSchema, 
        user_id: UUID
    ) -> ConnectionResponseSchema:
        """Update API connection configuration."""
        connection_str = str(connection_id)
        
        if connection_str not in self.connections:
            raise ValueError(f"API connection not found: {connection_str}")
            
        connection_config = self.connections[connection_str]
        
        # Update fields if provided
        if data.name is not None:
            connection_config["name"] = data.name
        if data.base_url is not None:
            connection_config["base_url"] = data.base_url.rstrip("/")
        if data.auth_type is not None:
            connection_config["auth_type"] = data.auth_type
        if data.auth_config is not None:
            connection_config["auth_config"] = data.auth_config
        if data.headers is not None:
            connection_config["headers"] = data.headers
        if data.timeout is not None:
            connection_config["timeout"] = data.timeout
        if data.max_retries is not None:
            connection_config["max_retries"] = data.max_retries
        if data.rate_limit is not None:
            connection_config["rate_limit"] = data.rate_limit
            # Update rate limiter
            if data.rate_limit:
                self.rate_limiter.set_limit(
                    connection_str,
                    data.rate_limit.get("requests", 100),
                    data.rate_limit.get("window_seconds", 60)
                )
        if data.enabled is not None:
            connection_config["enabled"] = data.enabled
            connection_config["status"] = "active" if data.enabled else "disabled"
        if data.description is not None:
            connection_config["description"] = data.description
            
        connection_config["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Close existing session to force recreation with new config
        await self.pool.close_session(connection_str)
        
        logger.info(f"Updated API connection: {connection_str}")
        return self._connection_to_response(connection_config)

    @standard_exception_handler
    async def delete(
        self, 
        connection_id: UUID, 
        user_id: UUID, 
        soft_delete: bool = True
    ):
        """Delete/disable API connection."""
        connection_str = str(connection_id)
        
        if connection_str not in self.connections:
            raise ValueError(f"API connection not found: {connection_str}")
            
        # Close the session
        await self.pool.close_session(connection_str)
            
        if soft_delete:
            self.connections[connection_str]["enabled"] = False
            self.connections[connection_str]["status"] = "disabled"
            self.connections[connection_str]["disabled_at"] = datetime.now(timezone.utc).isoformat()
        else:
            del self.connections[connection_str]
            
        logger.info(f"{'Disabled' if soft_delete else 'Deleted'} API connection: {connection_str}")

    @standard_exception_handler
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        user_id: Optional[UUID] = None,
    ) -> List[ConnectionResponseSchema]:
        """List API connections with filtering."""
        connections = []
        
        for connection_config in self.connections.values():
            # Apply filters
            if filters:
                if "enabled" in filters and connection_config["enabled"] != filters["enabled"]:
                    continue
                if "auth_type" in filters and connection_config["auth_type"] != filters["auth_type"]:
                    continue
                    
            connections.append(self._connection_to_response(connection_config))
            
        # Apply pagination
        return connections[skip:skip + limit]

    @standard_exception_handler
    async def count(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> int:
        """Count API connections with filters."""
        count = 0
        for connection_config in self.connections.values():
            if filters:
                if "enabled" in filters and connection_config["enabled"] != filters["enabled"]:
                    continue
                if "auth_type" in filters and connection_config["auth_type"] != filters["auth_type"]:
                    continue
            count += 1
        return count

    def _connection_to_response(
        self, 
        connection_config: Dict[str, Any]
    ) -> ConnectionResponseSchema:
        """Convert connection config to response schema."""
        return ConnectionResponseSchema(
            id=UUID(connection_config["id"]),
            name=connection_config["name"],
            base_url=connection_config["base_url"],
            auth_type=connection_config["auth_type"],
            timeout=connection_config["timeout"],
            max_retries=connection_config["max_retries"],
            rate_limit=connection_config.get("rate_limit"),
            enabled=connection_config["enabled"],
            description=connection_config.get("description"),
            status=connection_config["status"],
            last_used=connection_config.get("last_used"),
            success_count=connection_config.get("success_count", 0),
            error_count=connection_config.get("error_count", 0),
            avg_response_time=connection_config.get("avg_response_time", 0.0),
            created_at=connection_config["created_at"],
            updated_at=connection_config.get("updated_at", connection_config["created_at"])
        )

    @standard_exception_handler
    async def make_request(
        self,
        connection_id: str,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make API request through managed connection."""
        
        if connection_id not in self.connections:
            raise ValueError(f"API connection not found: {connection_id}")
        
        connection_config = self.connections[connection_id]
        
        if not connection_config["enabled"]:
            raise ValueError(f"API connection is disabled: {connection_id}")
        
        # Check rate limit
        if not await self.rate_limiter.check_rate_limit(connection_id):
            raise ValueError(f"Rate limit exceeded for connection: {connection_id}")
        
        # Get session
        session = await self.pool.get_session(connection_id, connection_config)
        
        # Build URL
        base_url = connection_config["base_url"]
        url = f"{base_url}/{endpoint.lstrip('/')}"
        
        # Merge headers
        request_headers = {**connection_config.get("headers", {})}
        if headers:
            request_headers.update(headers)
        
        # Make request with retry logic
        max_retries = connection_config["max_retries"]
        
        for attempt in range(max_retries + 1):
            try:
                import time
                start_time = time.time()
                
                async with session.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers
                ) as response:
                    response_time = time.time() - start_time
                    
                    # Update metrics
                    self._update_metrics(connection_config, response_time, success=response.status < 400)
                    
                    if response.status < 400:
                        # Success
                        if response.content_type == 'application/json':
                            result = await response.json()
                        else:
                            result = await response.text()
                        
                        return {
                            "success": True,
                            "status_code": response.status,
                            "data": result,
                            "response_time": response_time,
                            "attempt": attempt + 1
                        }
                    else:
                        # HTTP error
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        if attempt == max_retries:
                            return {
                                "success": False,
                                "status_code": response.status,
                                "error": error_msg,
                                "response_time": response_time,
                                "attempt": attempt + 1
                            }
                        # Retry for server errors
                        if response.status >= 500:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            # Don't retry client errors
                            return {
                                "success": False,
                                "status_code": response.status,
                                "error": error_msg,
                                "response_time": response_time,
                                "attempt": attempt + 1
                            }
                            
            except Exception as e:
                response_time = time.time() - start_time if 'start_time' in locals() else 0
                self._update_metrics(connection_config, response_time, success=False)
                
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "response_time": response_time,
                        "attempt": attempt + 1
                    }
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)

    def _update_metrics(self, connection_config: Dict[str, Any], response_time: float, success: bool):
        """Update connection metrics."""
        if success:
            connection_config["success_count"] = connection_config.get("success_count", 0) + 1
        else:
            connection_config["error_count"] = connection_config.get("error_count", 0) + 1
        
        # Update average response time
        total_requests = connection_config.get("success_count", 0) + connection_config.get("error_count", 0)
        if total_requests > 1:
            current_avg = connection_config.get("avg_response_time", 0.0)
            connection_config["avg_response_time"] = ((current_avg * (total_requests - 1)) + response_time) / total_requests
        else:
            connection_config["avg_response_time"] = response_time
        
        connection_config["last_used"] = datetime.now(timezone.utc).isoformat()

    @standard_exception_handler
    async def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test API connection health."""
        try:
            result = await self.make_request(
                connection_id=connection_id,
                method="GET",
                endpoint="/",  # Most APIs have a root endpoint
                headers={"User-Agent": "DotMac-Connection-Test/1.0"}
            )
            
            return {
                "connection_id": connection_id,
                "status": "healthy" if result["success"] else "unhealthy",
                "test_result": result,
                "tested_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "connection_id": connection_id,
                "status": "error",
                "error": str(e),
                "tested_at": datetime.now(timezone.utc).isoformat()
            }


class ApiConnectionManagerRouter:
    """Router factory for API Connection Manager following DRY patterns."""

    @classmethod
    def create_router(cls) -> APIRouter:
        """Create API Connection Manager router using RouterFactory."""
        
        # Use RouterFactory for standard CRUD operations
        router = RouterFactory.create_crud_router(
            service_class=ApiConnectionManager,
            create_schema=ConnectionCreateSchema,
            update_schema=ConnectionUpdateSchema,
            response_schema=ConnectionResponseSchema,
            prefix="/api-connections",
            tags=["api-connections", "integrations"],
            enable_search=True,
            enable_bulk_operations=False,  # Connections managed individually
        )

        # Add custom connection-specific endpoints
        @router.post("/{connection_id}/test", response_model=Dict[str, Any])
        @standard_exception_handler
        async def test_api_connection(
            connection_id: str,
            deps: StandardDependencies = Depends(get_standard_deps) = Depends()
        ):
            """Test API connection health."""
            manager = ApiConnectionManager(deps.db, deps.tenant_id)
            return await manager.test_connection(connection_id)

        @router.post("/{connection_id}/request", response_model=Dict[str, Any])
        @standard_exception_handler
        async def make_api_request(
            connection_id: str,
            method: str,
            endpoint: str,
            data: Optional[Dict[str, Any]] = None,
            params: Optional[Dict[str, str]] = None,
            headers: Optional[Dict[str, str]] = None,
            deps: StandardDependencies = Depends(get_standard_deps) = Depends()
        ):
            """Make API request through managed connection."""
            manager = ApiConnectionManager(deps.db, deps.tenant_id)
            return await manager.make_request(
                connection_id=connection_id,
                method=method,
                endpoint=endpoint,
                data=data,
                params=params,
                headers=headers
            )

        @router.get("/pool/stats", response_model=Dict[str, Any])
        @standard_exception_handler
        async def get_pool_stats(deps: StandardDependencies = Depends(get_standard_deps) = Depends()):
            """Get connection pool statistics."""
            manager = ApiConnectionManager(deps.db, deps.tenant_id)
            
            return {
                "active_sessions": len(manager.pool.sessions),
                "max_connections": manager.pool.max_connections,
                "connection_stats": {
                    conn_id: {
                        "requests_made": stats["requests_made"],
                        "last_used": stats["last_used"].isoformat() if stats["last_used"] else None
                    }
                    for conn_id, stats in manager.pool.connection_stats.items()
                }
            }

        return router