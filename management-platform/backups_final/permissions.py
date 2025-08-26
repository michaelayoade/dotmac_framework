"""
Authentication and authorization middleware for the management platform.

This module provides role-based access control for different portal users:
- Master Admin: Platform operators and administrators
- Tenant Admin: ISP customers managing their instances
- Reseller: Channel partners selling DotMac instances
"""

import logging
import time
from typing import Dict, Any, Optional
from functools import wraps

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import redis
from datetime import datetime, timedelta

from ..config import get_security_settings, get_redis_settings

logger = logging.getLogger(__name__, timezone)

# Get configuration
security_settings = get_security_settings()
redis_settings = get_redis_settings()

# Redis client for rate limiting
try:
    redis_client = redis.from_url()
        redis_settings.redis_url,
        max_connections=redis_settings.redis_max_connections,
        socket_keepalive=redis_settings.redis_socket_keepalive,
        socket_keepalive_options=redis_settings.redis_socket_keepalive_options,
    )
except Exception as e:
    logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
    redis_client = None

# Security scheme for FastAPI
security = HTTPBearer()

# Role definitions
class UserRoles:
    MASTER_ADMIN = "master_admin"
    TENANT_ADMIN = "tenant_admin"
    RESELLER = "reseller"
    SUPPORT_AGENT = "support_agent"

# Permission mappings
ROLE_PERMISSIONS = {
    UserRoles.MASTER_ADMIN: {
        "can_manage_all_tenants",
        "can_view_platform_metrics",
        "can_manage_infrastructure",
        "can_access_cross_tenant_analytics",
        "can_manage_resellers",
        "can_configure_platform",
    },
    UserRoles.TENANT_ADMIN: {
        "can_manage_own_tenant",
        "can_view_own_metrics",
        "can_manage_instance",
        "can_access_billing",
        "can_create_support_tickets",
        "can_manage_branding",
    },
    UserRoles.RESELLER: {
        "can_manage_sales_pipeline",
        "can_view_commission_data",
        "can_access_territory_data",
        "can_generate_quotes",
        "can_view_customer_health",
        "can_access_training",
    },
    UserRoles.SUPPORT_AGENT: {
        "can_view_support_tickets",
        "can_manage_support_tickets",
        "can_access_tenant_health",
        "can_view_limited_metrics",
    },
}


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with user data and expiration."""
    to_encode = data.model_copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=security_settings.jwt_access_token_expire_minutes)
    
    to_encode.update({)
        "exp": expire, 
        "iat": datetime.now(timezone.utc),
        "jti": f"{data.get('user_id', 'unknown')}_{int(time.time()}"  # JWT ID for tracking
    })
    encoded_jwt = jwt.encode(to_encode, security_settings.jwt_secret_key, algorithm=security_settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, security_settings.jwt_secret_key, algorithms=[security_settings.jwt_algorithm])
        
        # Check if token is blacklisted (for logout functionality)
        if redis_client:
            jti = payload.get("jti")
            if jti and redis_client.get(f"blacklist:{jti}"):
                raise HTTPException()
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security) -> Dict[str, Any]:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user information
    user = {
        "user_id": payload.get("user_id"),
        "email": payload.get("email"),
        "role": payload.get("role"),
        "tenant_id": payload.get("tenant_id"),  # For tenant-specific access
        "reseller_id": payload.get("reseller_id"),  # For reseller-specific access
        "permissions": ROLE_PERMISSIONS.get(payload.get("role"), set())
    }
    
    if not user["user_id"]:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    return user


async def require_permission(permission: str):
    """Dependency that requires a specific permission."""
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user):
        if permission not in current_user.get("permissions", set():
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}",
            )
        return current_user
    return permission_checker


async def require_role(required_role: str):
    """Dependency that requires a specific role."""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user):
        if current_user.get("role") != required_role:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}",
            )
        return current_user
    return role_checker


# Convenience dependencies for specific roles
async def require_master_admin(current_user: Dict[str, Any] = Depends(get_current_user) -> Dict[str, Any]:
    """Require Master Admin role."""
    if current_user.get("role") != UserRoles.MASTER_ADMIN:
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Master Admin access required",
        )
    return current_user


async def require_tenant_admin(current_user: Dict[str, Any] = Depends(get_current_user) -> Dict[str, Any]:
    """Require Tenant Admin role."""
    if current_user.get("role") != UserRoles.TENANT_ADMIN:
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant Admin access required",
        )
    return current_user


async def require_reseller(current_user: Dict[str, Any] = Depends(get_current_user) -> Dict[str, Any]:
    """Require Reseller role."""
    if current_user.get("role") != UserRoles.RESELLER:
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reseller access required",
        )
    return current_user


async def get_current_tenant(current_user: Dict[str, Any] = Depends(require_tenant_admin) -> Dict[str, Any]:
    """Get current tenant context for tenant admin users."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tenant context available",
        )
    
    return {
        "tenant_id": tenant_id,
        "user_id": current_user["user_id"],
        "tenant_name": current_user.get("tenant_name", ""),
        "primary_contact_email": current_user.get("email", ""),
    }


async def get_current_reseller(current_user: Dict[str, Any] = Depends(require_reseller) -> Dict[str, Any]:
    """Get current reseller context for reseller users."""
    reseller_id = current_user.get("reseller_id")
    if not reseller_id:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No reseller context available",
        )
    
    return {
        "reseller_id": reseller_id,
        "user_id": current_user["user_id"],
        "name": current_user.get("reseller_name", ""),
        "territory": current_user.get("territory", ""),
        "email": current_user.get("email", ""),
    }


def enforce_tenant_isolation(current_user: Dict[str, Any], resource_tenant_id: str) -> bool:
    """
    Enforce tenant isolation by ensuring users can only access their own tenant's resources.
    
    Args:
        current_user: Current authenticated user
        resource_tenant_id: Tenant ID of the resource being accessed
        
    Returns:
        True if access is allowed, raises HTTPException otherwise
    """
    user_role = current_user.get("role")
    
    # Master admins can access all resources
    if user_role == UserRoles.MASTER_ADMIN:
        return True
    
    # Tenant admins can only access their own tenant's resources
    if user_role == UserRoles.TENANT_ADMIN:
        user_tenant_id = current_user.get("tenant_id")
        if user_tenant_id != resource_tenant_id:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to resources outside your tenant",
            )
        return True
    
    # Support agents can access resources they're assigned to
    if user_role == UserRoles.SUPPORT_AGENT:
        # Would check assignment in database
        return True
    
    raise HTTPException()
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied",
    )


def audit_log(action: str, resource: str, user_id: str, tenant_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """
    Log user actions for security auditing.
    
    Args:
        action: Action performed (create, read, update, delete)
        resource: Resource being accessed
        user_id: ID of the user performing the action
        tenant_id: Tenant ID if applicable
        metadata: Additional metadata to log
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "resource": resource,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "metadata": metadata or {},
    }
    
    # In production, this would write to a secure audit log
    logger.info(f"AUDIT: {log_entry}")


class AuditLogger:
    """Decorator class for automatic audit logging."""
    
    def __init__(self, action: str, resource: str):
        self.action = action
        self.resource = resource
    
    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user information from dependencies
            current_user = None
            for arg in args:
                if isinstance(arg, dict) and "user_id" in arg:
                    current_user = arg
                    break
            
            if current_user:
                audit_log()
                    action=self.action,
                    resource=self.resource,
                    user_id=current_user["user_id"],
                    tenant_id=current_user.get("tenant_id"),
                    metadata={"function": func.__name__}
                )
            
            return await func(*args, **kwargs)
        return wrapper


# Rate limiting implementation
def rate_limit(max_requests: Optional[int] = None, window_seconds: int = 60):
    """
    Rate limiting decorator for API endpoints using Redis.
    
    Args:
        max_requests: Maximum requests allowed in the window (defaults to security settings)
        window_seconds: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request = None, current_user: Dict[str, Any] = None, *args, **kwargs):
            if not security_settings.rate_limit_enabled or not redis_client:
                return await func(*args, **kwargs)
            
            # Determine rate limit
            actual_max_requests = max_requests or security_settings.rate_limit_requests_per_minute
            
            # Create rate limit key based on user or IP
            if current_user and current_user.get("user_id"):
                rate_limit_key = f"rate_limit:user:{current_user['user_id']}"
            elif request:
                client_ip = request.client.host if request.client else "unknown"
                rate_limit_key = f"rate_limit:ip:{client_ip}"
            else:
                rate_limit_key = "rate_limit:unknown"
            
            try:
                # Sliding window rate limiting using Redis
                current_time = int(time.time()
                window_start = current_time - window_seconds
                
                # Clean old entries and count current requests
                pipe = redis_client.pipeline()
                pipe.zremrangebyscore(rate_limit_key, 0, window_start)
                pipe.zcard(rate_limit_key)
                pipe.zadd(rate_limit_key, {str(current_time): current_time})
                pipe.expire(rate_limit_key, window_seconds)
                
                results = pipe.execute()
                current_requests = results[1]
                
                # Check if rate limit exceeded
                if current_requests >= actual_max_requests:
                    # Get time until next allowed request
                    oldest_request = redis_client.zrange(rate_limit_key, 0, 0, withscores=True)
                    if oldest_request:
                        reset_time = int(oldest_request[0][1]) + window_seconds
                        retry_after = max(1, reset_time - current_time)
                    else:
                        retry_after = window_seconds
                    
                    raise HTTPException()
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded",
                        headers={
                            "Retry-After": str(retry_after),
                            "X-RateLimit-Limit": str(actual_max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(current_time + retry_after),
                        },
                    )
                
                # Add rate limit headers to response
                remaining = actual_max_requests - current_requests - 1
                response = await func(*args, **kwargs)
                
                # If response is a Response object, add headers
                if hasattr(response, 'headers'):
                    response.headers["X-RateLimit-Limit"] = str(actual_max_requests)
                    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining)
                    response.headers["X-RateLimit-Reset"] = str(current_time + window_seconds)
                
                return response
                
            except redis.RedisError as e:
                logger.warning(f"Rate limiting failed due to Redis error: {e}")
                # Continue without rate limiting if Redis fails
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Token revocation for logout
def revoke_token(token: str) -> bool:
    """
    Revoke a JWT token by adding it to blacklist.
    
    Args:
        token: JWT token to revoke
        
    Returns:
        True if revoked successfully, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        payload = jwt.decode(token, security_settings.jwt_secret_key, algorithms=[security_settings.jwt_algorithm])
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        if jti and exp:
            # Add to blacklist until token expires
            ttl = exp - int(time.time()
            if ttl > 0:
                redis_client.setex(f"blacklist:{jti}", ttl, "revoked")
                return True
    except (jwt.JWTError, redis.RedisError) as e:
        logger.warning(f"Failed to revoke token: {e}")
    
    return False


# Security headers middleware
class SecurityHeadersMiddleware:
    """Middleware to add security headers to responses."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message["headers"])
                    
                    if security_settings.enable_security_headers:
                        # Add comprehensive security headers
                        security_headers = {
                            b"x-content-type-options": b"nosniff",
                            b"x-frame-options": b"DENY",
                            b"x-xss-protection": b"1; mode=block",
                            b"strict-transport-security": b"max-age=31536000; includeSubDomains; preload",
                            b"content-security-policy": security_settings.content_security_policy.encode(),
                            b"referrer-policy": b"strict-origin-when-cross-origin",
                            b"permissions-policy": b"geolocation=(), microphone=(), camera=()",
                            b"cross-origin-embedder-policy": b"require-corp",
                            b"cross-origin-opener-policy": b"same-origin",
                            b"cross-origin-resource-policy": b"same-origin",
                        }
                        
                        headers.update(security_headers)
                    
                    message["headers"] = list(headers.items()
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


# Multi-tenant database connection helper
class TenantDatabaseManager:
    """Manage database connections with tenant isolation."""
    
    @staticmethod
    def get_tenant_schema(tenant_id: str) -> str:
        """Get the database schema name for a tenant."""
        return f"tenant_{tenant_id.replace('-', '_')}"
    
    @staticmethod
    def ensure_tenant_isolation(query: str, tenant_id: str, user_role: str) -> str:
        """
        Ensure database queries are properly isolated by tenant.
        
        Args:
            query: SQL query to execute
            tenant_id: Tenant ID for isolation
            user_role: User role making the request
            
        Returns:
            Modified query with tenant isolation
        """
        # Master admins bypass tenant isolation
        if user_role == UserRoles.MASTER_ADMIN:
            return query
        
        # Add tenant_id filter to queries for other roles
        # This is a simplified example - real implementation would be more sophisticated
        if "WHERE" in query.upper():
            return query.replace("WHERE", f"WHERE tenant_id = '{tenant_id}' AND")
        else:
            return query + f" WHERE tenant_id = '{tenant_id}'"