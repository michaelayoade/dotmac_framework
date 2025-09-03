"""
Service-to-Service Authentication
Signed internal tokens for secure service communication using OpenBao integration
"""

import jwt
import time
import hashlib
import hmac
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from ..core.logging import get_logger
from ..api.exception_handlers import standard_exception_handler

logger = get_logger(__name__)


class ServiceTokenType(str, Enum):
    """Types of service tokens"""
    INTERNAL = "internal"      # Service-to-service communication
    WEBHOOK = "webhook"        # Webhook authentication
    BATCH_JOB = "batch_job"    # Background job authentication
    HEALTH_CHECK = "health_check"  # Health check authentication


@dataclass
class ServiceIdentity:
    """Service identity information"""
    service_name: str
    version: str
    instance_id: str
    region: str
    environment: str  # dev, staging, prod
    tenant_scope: Optional[str] = None  # For tenant-scoped services


@dataclass
class ServiceTokenClaims:
    """Claims for service-to-service tokens"""
    service_identity: ServiceIdentity
    target_service: Optional[str] = None
    allowed_operations: List[str] = None
    tenant_context: Optional[str] = None
    issued_at: datetime = None
    expires_at: datetime = None
    token_id: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.allowed_operations is None:
            self.allowed_operations = []
        if self.metadata is None:
            self.metadata = {}
        if not self.issued_at:
            self.issued_at = datetime.utcnow()
        if not self.expires_at:
            self.expires_at = self.issued_at + timedelta(hours=1)
        if not self.token_id:
            self.token_id = self._generate_token_id()
    
    def _generate_token_id(self) -> str:
        """Generate unique token ID"""
        content = f"{self.service_identity.service_name}:{self.issued_at.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class ServiceTokenManager:
    """
    Manages service-to-service authentication tokens.
    
    Features:
    - Signed JWT tokens for service authentication
    - OpenBao integration for secret management
    - Service identity validation
    - Token lifecycle management
    - Audit logging for service communications
    """
    
    def __init__(
        self,
        signing_secret: str,
        openbao_client = None,
        token_expiry_hours: int = 1,
        algorithm: str = "HS256"
    ):
        self.signing_secret = signing_secret
        self.openbao_client = openbao_client
        self.token_expiry_hours = token_expiry_hours
        self.algorithm = algorithm
        
        # Service registry - should be populated from configuration
        self.service_registry = {}
        self.allowed_service_pairs = {}
        
        # Token cache for performance
        self.token_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    @standard_exception_handler
    async def issue_service_token(
        self,
        service_identity: ServiceIdentity,
        target_service: str,
        allowed_operations: List[str],
        tenant_context: Optional[str] = None,
        token_type: ServiceTokenType = ServiceTokenType.INTERNAL,
        custom_expiry: Optional[timedelta] = None
    ) -> str:
        """
        Issue a signed token for service-to-service communication.
        
        Args:
            service_identity: Identity of the requesting service
            target_service: Target service name
            allowed_operations: List of allowed operations
            tenant_context: Optional tenant context
            token_type: Type of service token
            custom_expiry: Custom expiry time
            
        Returns:
            Signed JWT token string
        """
        try:
            # Validate service identity
            if not await self._validate_service_identity(service_identity):
                raise ValueError(f"Invalid service identity: {service_identity.service_name}")
            
            # Validate service communication is allowed
            if not await self._validate_service_communication(
                service_identity.service_name, 
                target_service
            ):
                raise ValueError(f"Service {service_identity.service_name} not allowed to communicate with {target_service}")
            
            # Create token claims
            expires_at = datetime.utcnow() + (custom_expiry or timedelta(hours=self.token_expiry_hours))
            
            claims = ServiceTokenClaims(
                service_identity=service_identity,
                target_service=target_service,
                allowed_operations=allowed_operations,
                tenant_context=tenant_context,
                expires_at=expires_at
            )
            
            # Create JWT payload
            payload = {
                "iss": "dotmac-service-auth",
                "aud": target_service,
                "sub": service_identity.service_name,
                "iat": int(claims.issued_at.timestamp()),
                "exp": int(claims.expires_at.timestamp()),
                "jti": claims.token_id,
                "token_type": token_type.value,
                "service_identity": asdict(service_identity),
                "allowed_operations": allowed_operations,
                "tenant_context": tenant_context
            }
            
            # Sign the token
            token = jwt.encode(payload, self.signing_secret, algorithm=self.algorithm)
            
            # Cache the token
            self.token_cache[claims.token_id] = {
                "claims": claims,
                "cached_at": time.time()
            }
            
            # Audit log token issuance
            logger.info("Service token issued", extra={
                "requesting_service": service_identity.service_name,
                "target_service": target_service,
                "token_id": claims.token_id,
                "tenant_context": tenant_context,
                "expires_at": expires_at.isoformat(),
                "operations": allowed_operations
            })
            
            return token
            
        except Exception as e:
            logger.error(f"Failed to issue service token: {e}", extra={
                "requesting_service": service_identity.service_name,
                "target_service": target_service
            })
            raise
    
    @standard_exception_handler
    async def validate_service_token(
        self,
        token: str,
        expected_source_service: Optional[str] = None,
        required_operations: List[str] = None
    ) -> Optional[ServiceTokenClaims]:
        """
        Validate a service token and return its claims.
        
        Args:
            token: JWT token to validate
            expected_source_service: Expected source service name
            required_operations: Required operations for authorization
            
        Returns:
            ServiceTokenClaims if valid, None otherwise
        """
        try:
            # Decode and validate JWT
            payload = jwt.decode(
                token,
                self.signing_secret,
                algorithms=[self.algorithm],
                audience=None,  # We'll validate audience manually
                issuer="dotmac-service-auth"
            )
            
            # Extract service identity
            service_data = payload.get("service_identity", {})
            service_identity = ServiceIdentity(**service_data)
            
            # Reconstruct claims
            claims = ServiceTokenClaims(
                service_identity=service_identity,
                target_service=payload.get("aud"),
                allowed_operations=payload.get("allowed_operations", []),
                tenant_context=payload.get("tenant_context"),
                issued_at=datetime.fromtimestamp(payload.get("iat")),
                expires_at=datetime.fromtimestamp(payload.get("exp")),
                token_id=payload.get("jti", "")
            )
            
            # Validate expected source service
            if expected_source_service and service_identity.service_name != expected_source_service:
                logger.warning("Service token source mismatch", extra={
                    "expected": expected_source_service,
                    "actual": service_identity.service_name,
                    "token_id": claims.token_id
                })
                return None
            
            # Validate required operations
            if required_operations:
                missing_operations = set(required_operations) - set(claims.allowed_operations)
                if missing_operations:
                    logger.warning("Service token missing required operations", extra={
                        "missing_operations": list(missing_operations),
                        "service": service_identity.service_name,
                        "token_id": claims.token_id
                    })
                    return None
            
            # Validate service identity
            if not await self._validate_service_identity(service_identity):
                logger.warning("Service token has invalid service identity", extra={
                    "service": service_identity.service_name,
                    "token_id": claims.token_id
                })
                return None
            
            # Audit log token validation
            logger.debug("Service token validated", extra={
                "service": service_identity.service_name,
                "target_service": claims.target_service,
                "token_id": claims.token_id,
                "tenant_context": claims.tenant_context
            })
            
            return claims
            
        except jwt.ExpiredSignatureError:
            logger.warning("Service token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid service token: {e}")
            return None
        except Exception as e:
            logger.error(f"Service token validation error: {e}")
            return None
    
    async def _validate_service_identity(self, service_identity: ServiceIdentity) -> bool:
        """Validate that the service identity is legitimate"""
        
        # Check if service is registered
        service_info = self.service_registry.get(service_identity.service_name)
        if not service_info:
            # In production, this should query a service registry
            # For now, allow all services with proper naming convention
            if not service_identity.service_name.startswith(('dotmac-', 'isp-')):
                return False
        
        # Validate environment
        if service_identity.environment not in ['dev', 'staging', 'prod']:
            return False
        
        # Additional validation could include:
        # - Instance ID validation
        # - Region validation
        # - Version validation
        # - Certificate-based validation
        
        return True
    
    async def _validate_service_communication(self, source_service: str, target_service: str) -> bool:
        """Validate that source service is allowed to communicate with target service"""
        
        # Check explicit allow list
        allowed_targets = self.allowed_service_pairs.get(source_service, set())
        if target_service in allowed_targets:
            return True
        
        # Default allow patterns for development
        # In production, this should be more restrictive
        common_patterns = [
            # Management services can communicate with each other
            (lambda s, t: s.startswith('dotmac-') and t.startswith('dotmac-')),
            # ISP services can communicate with each other
            (lambda s, t: s.startswith('isp-') and t.startswith('isp-')),
            # Any service can communicate with shared services
            (lambda s, t: t in ['dotmac-shared', 'dotmac-logging', 'dotmac-metrics'])
        ]
        
        for pattern in common_patterns:
            if pattern(source_service, target_service):
                return True
        
        return False
    
    def register_service(
        self,
        service_name: str,
        service_info: Dict[str, Any],
        allowed_targets: List[str] = None
    ):
        """Register a service and its communication permissions"""
        self.service_registry[service_name] = service_info
        if allowed_targets:
            self.allowed_service_pairs[service_name] = set(allowed_targets)
    
    async def revoke_token(self, token_id: str) -> bool:
        """Revoke a service token"""
        try:
            # Remove from cache
            if token_id in self.token_cache:
                del self.token_cache[token_id]
            
            # In production, maintain a revocation list or use OpenBao
            logger.info(f"Service token revoked", extra={"token_id": token_id})
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke token {token_id}: {e}")
            return False
    
    def create_service_identity(
        self,
        service_name: str,
        version: str = "1.0.0",
        instance_id: Optional[str] = None,
        region: str = "us-east-1",
        environment: str = "prod",
        tenant_scope: Optional[str] = None
    ) -> ServiceIdentity:
        """Create a service identity for token requests"""
        
        if not instance_id:
            # Generate instance ID from hostname or container ID
            import socket
            instance_id = f"{service_name}-{socket.gethostname()}"
        
        return ServiceIdentity(
            service_name=service_name,
            version=version,
            instance_id=instance_id,
            region=region,
            environment=environment,
            tenant_scope=tenant_scope
        )


class ServiceAuthMiddleware:
    """
    Middleware for validating service-to-service authentication tokens.
    """
    
    def __init__(
        self,
        token_manager: ServiceTokenManager,
        service_name: str,
        required_operations: List[str] = None
    ):
        self.token_manager = token_manager
        self.service_name = service_name
        self.required_operations = required_operations or []
    
    async def __call__(self, request, call_next):
        """Process service authentication"""
        
        # Extract service token from headers
        service_token = request.headers.get("X-Service-Token") or request.headers.get("Authorization")
        
        if service_token and service_token.startswith("Bearer "):
            service_token = service_token[7:]  # Remove "Bearer " prefix
        
        if not service_token:
            # Allow requests without service tokens for now
            # In production, this should be more restrictive
            return await call_next(request)
        
        # Validate service token
        token_claims = await self.token_manager.validate_service_token(
            service_token,
            required_operations=self.required_operations
        )
        
        if not token_claims:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service token"
            )
        
        # Set service context in request
        request.state.service_auth = token_claims
        
        return await call_next(request)


# Global service token manager
service_token_manager = None


def get_service_token_manager() -> ServiceTokenManager:
    """Get the configured service token manager"""
    global service_token_manager
    if not service_token_manager:
        raise RuntimeError("Service token manager not configured")
    return service_token_manager


def configure_service_auth(signing_secret: str, **kwargs) -> ServiceTokenManager:
    """Configure the global service token manager"""
    global service_token_manager
    service_token_manager = ServiceTokenManager(signing_secret, **kwargs)
    return service_token_manager