"""
Security validation and dependency guards for the ticketing system.
"""

import logging
from typing import Any
from functools import wraps

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


class TenantIsolationError(SecurityError):
    """Raised when tenant isolation is violated."""
    pass


class InputValidationError(SecurityError):
    """Raised when input validation fails."""
    pass


def validate_tenant_id(tenant_id: str | None) -> str:
    """Validate and sanitize tenant ID."""
    if not tenant_id:
        raise TenantIsolationError("Tenant ID is required")
    
    if not isinstance(tenant_id, str):
        raise TenantIsolationError("Tenant ID must be a string")
    
    # Basic sanitization - remove control characters and limit length
    sanitized = ''.join(c for c in tenant_id if c.isprintable()).strip()
    
    if not sanitized:
        raise TenantIsolationError("Tenant ID cannot be empty after sanitization")
    
    if len(sanitized) > 255:
        raise TenantIsolationError("Tenant ID too long (max 255 characters)")
    
    # Check for suspicious patterns
    suspicious_patterns = ['..', '//', '\\', '<', '>', '&', '"', "'"]
    for pattern in suspicious_patterns:
        if pattern in sanitized:
            raise TenantIsolationError(f"Tenant ID contains suspicious pattern: {pattern}")
    
    return sanitized


def validate_user_id(user_id: str | None) -> str | None:
    """Validate and sanitize user ID."""
    if not user_id:
        return None
    
    if not isinstance(user_id, str):
        raise InputValidationError("User ID must be a string")
    
    # Basic sanitization
    sanitized = ''.join(c for c in user_id if c.isprintable()).strip()
    
    if len(sanitized) > 255:
        raise InputValidationError("User ID too long (max 255 characters)")
    
    # Check for suspicious patterns
    suspicious_patterns = ['..', '//', '\\', '<script', '<iframe', 'javascript:']
    for pattern in suspicious_patterns:
        if pattern.lower() in sanitized.lower():
            raise InputValidationError(f"User ID contains suspicious pattern: {pattern}")
    
    return sanitized if sanitized else None


def validate_ticket_id(ticket_id: str | None) -> str:
    """Validate and sanitize ticket ID."""
    if not ticket_id:
        raise InputValidationError("Ticket ID is required")
    
    if not isinstance(ticket_id, str):
        raise InputValidationError("Ticket ID must be a string")
    
    sanitized = ticket_id.strip()
    
    if not sanitized:
        raise InputValidationError("Ticket ID cannot be empty")
    
    if len(sanitized) > 255:
        raise InputValidationError("Ticket ID too long (max 255 characters)")
    
    # Allow alphanumeric, hyphens, and underscores
    if not all(c.isalnum() or c in '-_' for c in sanitized):
        raise InputValidationError("Ticket ID contains invalid characters")
    
    return sanitized


def validate_email(email: str | None) -> str | None:
    """Validate and sanitize email address."""
    if not email:
        return None
    
    if not isinstance(email, str):
        raise InputValidationError("Email must be a string")
    
    sanitized = email.strip().lower()
    
    if not sanitized:
        return None
    
    if len(sanitized) > 320:  # RFC 5321 limit
        raise InputValidationError("Email address too long")
    
    # Basic email validation
    if '@' not in sanitized or sanitized.count('@') != 1:
        raise InputValidationError("Invalid email format")
    
    local, domain = sanitized.split('@')
    
    if not local or not domain:
        raise InputValidationError("Invalid email format")
    
    if len(local) > 64:  # RFC 5321 limit
        raise InputValidationError("Email local part too long")
    
    if '.' not in domain:
        raise InputValidationError("Email domain must contain at least one dot")
    
    # Check for suspicious patterns
    suspicious_patterns = ['<', '>', '"', '\\', ' ', '\t', '\n', '\r']
    for pattern in suspicious_patterns:
        if pattern in sanitized:
            raise InputValidationError(f"Email contains invalid character: {pattern}")
    
    return sanitized


def validate_string_field(value: Any, field_name: str, max_length: int = 1000, allow_empty: bool = False) -> str | None:
    """Validate and sanitize string fields."""
    if value is None:
        return None if allow_empty else ""
    
    if not isinstance(value, str):
        raise InputValidationError(f"{field_name} must be a string")
    
    # Remove null bytes and control characters (except newlines and tabs for content fields)
    if field_name.lower() in ['description', 'content', 'comment']:
        # Allow newlines and tabs in content fields
        sanitized = ''.join(c for c in value if c == '\n' or c == '\t' or (c.isprintable() and c != '\x00'))
    else:
        # Strip all control characters for other fields
        sanitized = ''.join(c for c in value if c.isprintable() and c != '\x00')
    
    sanitized = sanitized.strip()
    
    if not sanitized and not allow_empty:
        raise InputValidationError(f"{field_name} cannot be empty")
    
    if len(sanitized) > max_length:
        raise InputValidationError(f"{field_name} too long (max {max_length} characters)")
    
    return sanitized if sanitized else None


def require_tenant_isolation(func):
    """Decorator to ensure tenant isolation in service methods."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check for tenant_id parameter
        if 'tenant_id' not in kwargs:
            raise TenantIsolationError(f"Method {func.__name__} requires tenant_id parameter")
        
        # Validate tenant_id
        kwargs['tenant_id'] = validate_tenant_id(kwargs['tenant_id'])
        
        return await func(*args, **kwargs)
    
    return wrapper


def validate_dependencies(*required_deps):
    """Decorator to validate required dependencies are available."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for dep_name in required_deps:
                dep_value = getattr(self, dep_name, None)
                if dep_value is None:
                    logger.warning(f"Required dependency {dep_name} not available in {func.__name__}")
                    raise SecurityError(f"Required dependency {dep_name} not configured")
            
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


class SecurityAuditLog:
    """Security audit logging for sensitive operations."""
    
    def __init__(self, logger_name: str = "ticketing.security"):
        self.logger = logging.getLogger(logger_name)
    
    def log_tenant_access(self, operation: str, tenant_id: str, user_id: str | None = None, 
                         ticket_id: str | None = None, success: bool = True):
        """Log tenant access operations."""
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            f"TENANT_ACCESS: {operation} - tenant:{tenant_id} user:{user_id} ticket:{ticket_id} success:{success}"
        )
    
    def log_validation_error(self, error_type: str, details: str, tenant_id: str | None = None):
        """Log validation errors."""
        self.logger.warning(
            f"VALIDATION_ERROR: {error_type} - {details} - tenant:{tenant_id}"
        )
    
    def log_security_event(self, event_type: str, details: dict[str, Any]):
        """Log general security events."""
        self.logger.info(f"SECURITY_EVENT: {event_type} - {details}")


# Global security audit logger
security_audit = SecurityAuditLog()


def audit_tenant_access(operation: str):
    """Decorator to audit tenant access operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_id = kwargs.get('tenant_id')
            user_id = kwargs.get('user_id') or kwargs.get('customer_id')
            ticket_id = kwargs.get('ticket_id')
            
            try:
                result = await func(*args, **kwargs)
                security_audit.log_tenant_access(operation, tenant_id, user_id, ticket_id, True)
                return result
            except Exception as e:
                security_audit.log_tenant_access(operation, tenant_id, user_id, ticket_id, False)
                security_audit.log_validation_error(type(e).__name__, str(e), tenant_id)
                raise
        
        return wrapper
    return decorator


class RateLimitError(SecurityError):
    """Raised when rate limit is exceeded."""
    pass


class SimpleRateLimit:
    """Simple in-memory rate limiter for basic protection."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}
        import time
        self.time = time
    
    def check_rate_limit(self, identifier: str) -> dict[str, Any]:
        """Check if identifier is within rate limit.
        
        Returns:
            Dict with 'allowed' boolean and rate limit info for headers
        """
        now = self.time.time()
        minute_bucket = int(now // 60)
        
        # Clean old buckets
        old_buckets = [bucket for bucket in self.requests.keys() if bucket < minute_bucket - 1]
        for bucket in old_buckets:
            del self.requests[bucket]
        
        # Check current requests
        current_requests = self.requests.get(minute_bucket, {})
        user_requests = current_requests.get(identifier, 0)
        
        if user_requests >= self.requests_per_minute:
            return {
                'allowed': False,
                'limit': self.requests_per_minute,
                'remaining': 0,
                'reset': (minute_bucket + 1) * 60,
                'used': user_requests
            }
        
        # Increment counter
        if minute_bucket not in self.requests:
            self.requests[minute_bucket] = {}
        self.requests[minute_bucket][identifier] = user_requests + 1
        
        return {
            'allowed': True,
            'limit': self.requests_per_minute,
            'remaining': self.requests_per_minute - (user_requests + 1),
            'reset': (minute_bucket + 1) * 60,
            'used': user_requests + 1
        }


# Global rate limiter
rate_limiter = SimpleRateLimit()


def rate_limit(identifier_key: str = 'tenant_id'):
    """Decorator to apply rate limiting with proper headers."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            identifier = kwargs.get(identifier_key, 'unknown')
            
            rate_result = rate_limiter.check_rate_limit(str(identifier))
            
            if not rate_result['allowed']:
                raise RateLimitError(
                    f"Rate limit exceeded for {identifier}. "
                    f"Limit: {rate_result['limit']}/min, "
                    f"Reset: {rate_result['reset']}"
                )
            
            # Add rate limit info to kwargs for response headers
            kwargs['_rate_limit_info'] = rate_result
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def add_rate_limit_headers(response, rate_info: dict[str, Any]):
    """Add rate limit headers to HTTP response."""
    if not rate_info:
        return response
        
    response.headers["X-RateLimit-Limit"] = str(rate_info['limit'])
    response.headers["X-RateLimit-Remaining"] = str(rate_info['remaining'])
    response.headers["X-RateLimit-Reset"] = str(int(rate_info['reset']))
    response.headers["X-RateLimit-Used"] = str(rate_info['used'])
    
    return response


def sanitize_search_query(query: str | None) -> str | None:
    """Sanitize search query to prevent injection attacks."""
    if not query:
        return None
    
    if not isinstance(query, str):
        return None
    
    # Remove null bytes and control characters
    sanitized = ''.join(c for c in query if c.isprintable() or c in ' \t').strip()
    
    if not sanitized:
        return None
    
    if len(sanitized) > 500:
        sanitized = sanitized[:500]
    
    # Remove SQL-like patterns
    dangerous_patterns = [
        'UNION', 'SELECT', 'INSERT', 'DELETE', 'UPDATE', 'DROP', 'CREATE',
        'ALTER', 'EXEC', 'EXECUTE', '--', '/*', '*/', ';', 'xp_', 'sp_'
    ]
    
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern.upper(), '').replace(pattern.lower(), '')
    
    return sanitized if sanitized.strip() else None


class TenantContext:
    """Context object for tenant isolation checks."""
    
    def __init__(self, tenant_id: str, user_id: str | None = None):
        self.tenant_id = validate_tenant_id(tenant_id)
        self.user_id = validate_user_id(user_id) if user_id else None


class TenantEntity:
    """Base class for entities that belong to a tenant."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id


def assert_tenant(ctx: TenantContext, entity: Any) -> None:
    """Assert that an entity belongs to the correct tenant (defense-in-depth).
    
    Args:
        ctx: Tenant context with validated tenant_id
        entity: Entity to check (must have tenant_id attribute)
        
    Raises:
        TenantIsolationError: If entity doesn't belong to the tenant
        SecurityError: If entity doesn't have tenant_id attribute
    """
    if not hasattr(entity, 'tenant_id'):
        raise SecurityError(f"Entity {type(entity).__name__} does not have tenant_id attribute")
    
    entity_tenant = getattr(entity, 'tenant_id')
    
    if not entity_tenant:
        raise TenantIsolationError(f"Entity {type(entity).__name__} has no tenant_id")
    
    if entity_tenant != ctx.tenant_id:
        security_audit.log_tenant_access(
            "tenant_violation",
            ctx.tenant_id,
            ctx.user_id,
            getattr(entity, 'id', None),
            success=False
        )
        raise TenantIsolationError(
            f"Tenant isolation violation: entity belongs to '{entity_tenant}' "
            f"but context expects '{ctx.tenant_id}'"
        )


def assert_tenant_list(ctx: TenantContext, entities: list[Any]) -> None:
    """Assert that all entities in a list belong to the correct tenant.
    
    Args:
        ctx: Tenant context with validated tenant_id
        entities: List of entities to check
        
    Raises:
        TenantIsolationError: If any entity doesn't belong to the tenant
    """
    for i, entity in enumerate(entities):
        try:
            assert_tenant(ctx, entity)
        except TenantIsolationError as e:
            raise TenantIsolationError(f"Entity at index {i}: {str(e)}")


def create_tenant_context(tenant_id: str, user_id: str | None = None) -> TenantContext:
    """Create and validate a tenant context.
    
    Args:
        tenant_id: Tenant identifier
        user_id: Optional user identifier
        
    Returns:
        Validated tenant context
        
    Raises:
        TenantIsolationError: If tenant_id is invalid
        InputValidationError: If user_id is invalid
    """
    return TenantContext(tenant_id=tenant_id, user_id=user_id)