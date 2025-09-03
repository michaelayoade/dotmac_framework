"""
Tenant security boundary enforcement and validation.

Provides comprehensive security controls to ensure tenant isolation
and prevent cross-tenant data access or security violations.
"""

import time
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timedelta
from enum import Enum

from fastapi import Request
from pydantic import BaseModel
from loguru import logger

from .config import TenantConfig
from .identity import TenantContext, get_current_tenant
from .exceptions import TenantSecurityError, TenantContextError


class SecurityViolationType(str, Enum):
    """Types of tenant security violations."""
    
    CROSS_TENANT_ACCESS = "cross_tenant_access"
    UNAUTHORIZED_TENANT_SWITCH = "unauthorized_tenant_switch"
    MISSING_TENANT_CONTEXT = "missing_tenant_context"
    INVALID_TENANT_PERMISSIONS = "invalid_tenant_permissions"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    TENANT_ACCESS_DENIED = "tenant_access_denied"


class SecurityAuditEvent(BaseModel):
    """Security audit event record."""
    
    event_id: str
    timestamp: datetime
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    
    violation_type: SecurityViolationType
    severity: str = "medium"  # low, medium, high, critical
    
    # Context information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    
    # Violation details
    description: str
    details: Dict[str, Any] = {}
    
    # Security response
    action_taken: str = "logged"
    blocked: bool = False


class TenantAccessPolicy(BaseModel):
    """Access policy for tenant operations."""
    
    tenant_id: str
    
    # Access controls
    allowed_operations: Set[str] = set()
    denied_operations: Set[str] = set()
    
    # Rate limiting
    max_requests_per_minute: Optional[int] = None
    max_requests_per_hour: Optional[int] = None
    
    # Time-based restrictions
    allowed_hours: Optional[List[int]] = None  # Hours 0-23
    timezone: str = "UTC"
    
    # IP restrictions
    allowed_ips: Optional[List[str]] = None
    blocked_ips: Optional[List[str]] = None
    
    # Additional security settings
    require_mfa: bool = False
    require_secure_connection: bool = True
    max_session_duration: Optional[int] = None  # seconds
    
    # Custom policy fields
    custom_rules: Dict[str, Any] = {}


class TenantSecurityEnforcer:
    """
    Enforces tenant security boundaries and access policies.
    
    Provides comprehensive security controls including:
    - Cross-tenant access prevention
    - Rate limiting and abuse detection
    - Security audit logging
    - Access policy enforcement
    - Suspicious activity detection
    """
    
    def __init__(self, config: TenantConfig):
        self.config = config
        
        # Security state tracking
        self._access_logs: Dict[str, List[datetime]] = {}
        self._security_violations: List[SecurityAuditEvent] = []
        self._tenant_policies: Dict[str, TenantAccessPolicy] = {}
        self._blocked_ips: Set[str] = set()
        self._suspicious_activities: Dict[str, int] = {}
        
        # Rate limiting windows
        self._rate_limit_windows = {
            'minute': timedelta(minutes=1),
            'hour': timedelta(hours=1),
            'day': timedelta(days=1),
        }
        
        # Default security policies
        self._default_policies = {
            'max_requests_per_minute': 60,
            'max_requests_per_hour': 1000,
            'require_secure_connection': True,
        }
    
    async def validate_tenant_access(
        self, 
        tenant_context: TenantContext, 
        request: Request
    ) -> None:
        """
        Validate tenant access and enforce security boundaries.
        
        Args:
            tenant_context: Current tenant context
            request: FastAPI request object
            
        Raises:
            TenantSecurityError: If access is denied or violations detected
        """
        # Basic tenant context validation
        if not tenant_context:
            await self._log_security_violation(
                violation_type=SecurityViolationType.MISSING_TENANT_CONTEXT,
                description="No tenant context available for request",
                request=request,
                severity="high"
            )
            raise TenantSecurityError(
                "No tenant context available",
                "unknown",
                "missing_context"
            )
        
        tenant_id = tenant_context.tenant_id
        
        # Check if tenant is blocked
        if await self._is_tenant_blocked(tenant_id):
            raise TenantSecurityError(
                f"Tenant {tenant_id} is currently blocked",
                tenant_id,
                "tenant_blocked"
            )
        
        # Validate IP restrictions
        client_ip = self._get_client_ip(request)
        if not await self._validate_ip_access(tenant_id, client_ip):
            await self._log_security_violation(
                violation_type=SecurityViolationType.TENANT_ACCESS_DENIED,
                description=f"IP access denied for tenant {tenant_id}",
                tenant_id=tenant_id,
                request=request,
                details={"ip_address": client_ip}
            )
            raise TenantSecurityError(
                f"IP access denied for tenant {tenant_id}",
                tenant_id,
                "ip_blocked"
            )
        
        # Rate limiting validation
        if not await self._validate_rate_limits(tenant_id, request):
            await self._log_security_violation(
                violation_type=SecurityViolationType.RATE_LIMIT_EXCEEDED,
                description=f"Rate limit exceeded for tenant {tenant_id}",
                tenant_id=tenant_id,
                request=request,
                severity="medium"
            )
            raise TenantSecurityError(
                f"Rate limit exceeded for tenant {tenant_id}",
                tenant_id,
                "rate_limit"
            )
        
        # Validate HTTPS requirement
        if await self._should_require_secure_connection(tenant_id):
            if request.url.scheme != "https" and not self._is_local_request(request):
                await self._log_security_violation(
                    violation_type=SecurityViolationType.TENANT_ACCESS_DENIED,
                    description=f"Insecure connection for tenant {tenant_id}",
                    tenant_id=tenant_id,
                    request=request,
                    severity="high"
                )
                raise TenantSecurityError(
                    "Secure connection required",
                    tenant_id,
                    "insecure_connection"
                )
        
        # Check for suspicious activity patterns
        await self._check_suspicious_activity(tenant_id, request)
        
        # Log successful access
        await self._log_tenant_access(tenant_id, request)
    
    async def validate_cross_tenant_access(
        self,
        requesting_tenant_id: str,
        target_tenant_id: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate if cross-tenant access is allowed.
        
        Args:
            requesting_tenant_id: Tenant making the request
            target_tenant_id: Target tenant being accessed
            operation: Operation being performed
            context: Additional context for validation
            
        Returns:
            True if access is allowed
            
        Raises:
            TenantSecurityError: If cross-tenant access is denied
        """
        # Same tenant access is always allowed
        if requesting_tenant_id == target_tenant_id:
            return True
        
        # Check global cross-tenant access policy
        if not self.config.allow_cross_tenant_access:
            await self._log_security_violation(
                violation_type=SecurityViolationType.CROSS_TENANT_ACCESS,
                description=f"Cross-tenant access denied: {requesting_tenant_id} -> {target_tenant_id}",
                tenant_id=requesting_tenant_id,
                details={
                    "target_tenant_id": target_tenant_id,
                    "operation": operation,
                    "context": context or {}
                }
            )
            raise TenantSecurityError(
                f"Cross-tenant access denied: {requesting_tenant_id} -> {target_tenant_id}",
                requesting_tenant_id,
                "cross_tenant_denied"
            )
        
        # Check tenant-specific policies
        policy = self._tenant_policies.get(requesting_tenant_id)
        if policy and operation in policy.denied_operations:
            raise TenantSecurityError(
                f"Operation {operation} denied for tenant {requesting_tenant_id}",
                requesting_tenant_id,
                "operation_denied"
            )
        
        return True
    
    async def _validate_rate_limits(self, tenant_id: str, request: Request) -> bool:
        """Validate rate limiting policies."""
        current_time = datetime.now()
        
        # Initialize access log for tenant
        if tenant_id not in self._access_logs:
            self._access_logs[tenant_id] = []
        
        access_log = self._access_logs[tenant_id]
        
        # Clean old entries (keep last hour)
        cutoff_time = current_time - timedelta(hours=1)
        access_log[:] = [t for t in access_log if t > cutoff_time]
        
        # Get tenant policy or defaults
        policy = self._tenant_policies.get(tenant_id)
        max_per_minute = (policy.max_requests_per_minute if policy 
                         else self._default_policies['max_requests_per_minute'])
        max_per_hour = (policy.max_requests_per_hour if policy 
                       else self._default_policies['max_requests_per_hour'])
        
        # Check minute rate limit
        if max_per_minute:
            minute_ago = current_time - timedelta(minutes=1)
            recent_requests = [t for t in access_log if t > minute_ago]
            if len(recent_requests) >= max_per_minute:
                return False
        
        # Check hour rate limit
        if max_per_hour:
            if len(access_log) >= max_per_hour:
                return False
        
        # Add current request to log
        access_log.append(current_time)
        
        return True
    
    async def _validate_ip_access(self, tenant_id: str, client_ip: str) -> bool:
        """Validate IP-based access controls."""
        # Check global blocked IPs
        if client_ip in self._blocked_ips:
            return False
        
        # Check tenant-specific IP policies
        policy = self._tenant_policies.get(tenant_id)
        if not policy:
            return True
        
        # Check blocked IPs for tenant
        if policy.blocked_ips and client_ip in policy.blocked_ips:
            return False
        
        # Check allowed IPs for tenant (if specified, IP must be in list)
        if policy.allowed_ips and client_ip not in policy.allowed_ips:
            return False
        
        return True
    
    async def _check_suspicious_activity(self, tenant_id: str, request: Request):
        """Check for suspicious activity patterns."""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Track suspicious patterns
        suspicious_indicators = []
        
        # Check for unusual user agent patterns
        if not user_agent or len(user_agent) < 10:
            suspicious_indicators.append("minimal_user_agent")
        
        # Check for rapid requests from same IP
        ip_key = f"ip:{client_ip}"
        current_count = self._suspicious_activities.get(ip_key, 0)
        self._suspicious_activities[ip_key] = current_count + 1
        
        if current_count > 100:  # More than 100 requests from same IP
            suspicious_indicators.append("high_ip_frequency")
        
        # Log suspicious activity if detected
        if suspicious_indicators:
            await self._log_security_violation(
                violation_type=SecurityViolationType.SUSPICIOUS_ACTIVITY,
                description=f"Suspicious activity detected for tenant {tenant_id}",
                tenant_id=tenant_id,
                request=request,
                details={
                    "indicators": suspicious_indicators,
                    "ip_request_count": current_count + 1
                },
                severity="low"
            )
    
    async def _log_security_violation(
        self,
        violation_type: SecurityViolationType,
        description: str,
        tenant_id: Optional[str] = None,
        request: Optional[Request] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "medium"
    ):
        """Log security violation event."""
        import uuid
        
        event = SecurityAuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            tenant_id=tenant_id,
            violation_type=violation_type,
            description=description,
            details=details or {},
            severity=severity
        )
        
        # Add request context if available
        if request:
            event.ip_address = self._get_client_ip(request)
            event.user_agent = request.headers.get("user-agent")
            event.request_path = request.url.path
            event.request_method = request.method
            event.request_id = getattr(request.state, 'request_id', None)
        
        # Add to violations log
        self._security_violations.append(event)
        
        # Log to application logs
        logger.warning(
            f"Security violation: {violation_type} - {description}",
            extra={
                "event_id": event.event_id,
                "tenant_id": tenant_id,
                "violation_type": violation_type,
                "severity": severity,
                "details": details or {}
            }
        )
        
        # Keep only recent violations (last 1000)
        if len(self._security_violations) > 1000:
            self._security_violations = self._security_violations[-1000:]
    
    async def _log_tenant_access(self, tenant_id: str, request: Request):
        """Log successful tenant access."""
        if self.config.log_tenant_access:
            logger.debug(
                f"Tenant access validated: {tenant_id}",
                extra={
                    "tenant_id": tenant_id,
                    "ip_address": self._get_client_ip(request),
                    "path": request.url.path,
                    "method": request.method,
                }
            )
    
    async def _is_tenant_blocked(self, tenant_id: str) -> bool:
        """Check if tenant is currently blocked."""
        # Implementation would check blocking status
        # This could integrate with external systems or databases
        return False
    
    async def _should_require_secure_connection(self, tenant_id: str) -> bool:
        """Check if secure connection is required for tenant."""
        policy = self._tenant_policies.get(tenant_id)
        if policy:
            return policy.require_secure_connection
        return self._default_policies.get('require_secure_connection', True)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct connection IP
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"
    
    def _is_local_request(self, request: Request) -> bool:
        """Check if request is from local/development environment."""
        client_ip = self._get_client_ip(request)
        local_ips = ["127.0.0.1", "::1", "localhost"]
        return client_ip in local_ips or client_ip.startswith("192.168.")
    
    def set_tenant_policy(self, tenant_id: str, policy: TenantAccessPolicy):
        """Set access policy for a specific tenant."""
        self._tenant_policies[tenant_id] = policy
    
    def get_security_violations(
        self, 
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[SecurityAuditEvent]:
        """Get recent security violations."""
        violations = self._security_violations
        
        if tenant_id:
            violations = [v for v in violations if v.tenant_id == tenant_id]
        
        return violations[-limit:] if violations else []
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and statistics."""
        recent_violations = self._security_violations[-100:] if self._security_violations else []
        
        violation_counts = {}
        for violation in recent_violations:
            vtype = violation.violation_type
            violation_counts[vtype] = violation_counts.get(vtype, 0) + 1
        
        return {
            "total_violations": len(self._security_violations),
            "recent_violations": len(recent_violations),
            "violation_types": violation_counts,
            "blocked_ips": len(self._blocked_ips),
            "active_policies": len(self._tenant_policies),
            "monitored_tenants": len(self._access_logs),
        }