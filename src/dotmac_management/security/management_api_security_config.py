"""
DotMac Management API Security Configuration

Comprehensive security configuration for the DotMac Management API including:
- Rate limiting rules by endpoint sensitivity
- Security headers configuration
- CORS policies for management interface
- Authentication and authorization requirements
- Request validation settings

This configuration leverages dotmac_shared security components for DRY compliance.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from dotmac_shared.security.api_rate_limiter import RateLimit as RateLimitRule
from dotmac_shared.security.api_rate_limiter import RateLimitType
from dotmac_shared.security.api_security_integration import APISecuritySuite


class EndpointSensitivity(Enum):
    """Classification of endpoint sensitivity levels for security policies"""

    PUBLIC = "public"  # Public-facing endpoints (signup, status)
    READ = "read"  # Read-only operations for authenticated users
    WRITE = "write"  # Create/update operations
    FINANCIAL = "financial"  # Financial data operations (commissions, billing)
    ADMIN = "admin"  # Administrative operations
    CRITICAL = "critical"  # Critical system operations (bootstrap removal)


@dataclass
class SecurityPolicy:
    """Security policy definition for endpoint groups"""

    sensitivity: EndpointSensitivity
    max_requests: int
    time_window_seconds: int
    rate_limit_type: RateLimitType
    custom_message: str
    require_auth: bool = True
    require_admin: bool = False
    additional_headers: Optional[dict[str, str]] = None


class ManagementAPISecurityConfig:
    """
    Centralized security configuration for DotMac Management API

    Provides security policies based on endpoint sensitivity and business requirements.
    Integrates with dotmac_shared security components for consistent enforcement.
    """

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self._setup_security_policies()

    def _setup_security_policies(self) -> None:
        """Setup security policies by endpoint sensitivity level"""

        # Base policies - stricter in production
        base_multiplier = 1.0 if self.environment == "production" else 2.0

        self.security_policies = {
            EndpointSensitivity.PUBLIC: SecurityPolicy(
                sensitivity=EndpointSensitivity.PUBLIC,
                max_requests=int(20 * base_multiplier),  # 20 req/min in prod, 40 in dev
                time_window_seconds=60,
                rate_limit_type=RateLimitType.PER_IP,
                custom_message="Too many requests from your IP. Please wait before trying again.",
                require_auth=False,
            ),
            EndpointSensitivity.READ: SecurityPolicy(
                sensitivity=EndpointSensitivity.READ,
                max_requests=int(100 * base_multiplier),  # 100 req/min in prod, 200 in dev
                time_window_seconds=60,
                rate_limit_type=RateLimitType.PER_USER,
                custom_message="You have exceeded your read request quota. Please wait before making more requests.",
                require_auth=True,
            ),
            EndpointSensitivity.WRITE: SecurityPolicy(
                sensitivity=EndpointSensitivity.WRITE,
                max_requests=int(30 * base_multiplier),  # 30 req/min in prod, 60 in dev
                time_window_seconds=60,
                rate_limit_type=RateLimitType.PER_USER,
                custom_message="You have exceeded your write request quota. Please wait before making more requests.",
                require_auth=True,
                additional_headers={
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            ),
            EndpointSensitivity.FINANCIAL: SecurityPolicy(
                sensitivity=EndpointSensitivity.FINANCIAL,
                max_requests=int(10 * base_multiplier),  # 10 req/min in prod, 20 in dev
                time_window_seconds=60,
                rate_limit_type=RateLimitType.PER_USER,
                custom_message="Too many requests to financial endpoints. Please wait before trying again.",
                require_auth=True,
                additional_headers={
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                },
            ),
            EndpointSensitivity.ADMIN: SecurityPolicy(
                sensitivity=EndpointSensitivity.ADMIN,
                max_requests=int(20 * base_multiplier),  # 20 req/min in prod, 40 in dev
                time_window_seconds=60,
                rate_limit_type=RateLimitType.PER_USER,
                custom_message="Too many admin requests. Please wait before trying again.",
                require_auth=True,
                require_admin=True,
                additional_headers={
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
            ),
            EndpointSensitivity.CRITICAL: SecurityPolicy(
                sensitivity=EndpointSensitivity.CRITICAL,
                max_requests=int(5 * base_multiplier),  # 5 req/min in prod, 10 in dev
                time_window_seconds=60,
                rate_limit_type=RateLimitType.PER_IP,  # IP-based for critical operations
                custom_message="Too many requests to critical system endpoints. Please wait before trying again.",
                require_auth=True,
                require_admin=True,
                additional_headers={
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                },
            ),
        }

    def get_rate_limit_rules(self) -> list[RateLimitRule]:
        """Generate rate limiting rules for all endpoint patterns"""

        rules = []

        # Public endpoints (signup, status checks)
        public_policy = self.security_policies[EndpointSensitivity.PUBLIC]
        rules.append(
            RateLimitRule(
                rule_id="public_endpoints",
                limit_type=public_policy.rate_limit_type,
                max_requests=public_policy.max_requests,
                time_window_seconds=public_policy.time_window_seconds,
                endpoints=[
                    "/api/v1/public/signup",
                    "/api/v1/public/verify-email",
                    "/api/v1/public/signup/*/status",
                    "/api/v1/partners/by-domain/*/theme",
                ],
                methods=["GET", "POST"],
            )
        )

        # Financial endpoints (commission config, revenue models)
        financial_policy = self.security_policies[EndpointSensitivity.FINANCIAL]
        rules.append(
            RateLimitRule(
                rule_id="financial_read_endpoints",
                limit_type=financial_policy.rate_limit_type,
                max_requests=financial_policy.max_requests * 10,  # More lenient for reads
                time_window_seconds=financial_policy.time_window_seconds,
                endpoints=[
                    "/api/v1/commission-config",
                    "/api/v1/commission-config/default",
                    "/api/v1/commission-config/*",
                    "/api/v1/commission-config/revenue-models",
                    "/api/v1/commission-config/revenue-models/*",
                ],
                methods=["GET"],
            )
        )

        rules.append(
            RateLimitRule(
                rule_id="financial_write_endpoints",
                limit_type=financial_policy.rate_limit_type,
                max_requests=financial_policy.max_requests,
                time_window_seconds=financial_policy.time_window_seconds,
                endpoints=[
                    "/api/v1/commission-config",
                    "/api/v1/commission-config/*",
                    "/api/v1/commission-config/revenue-models",
                    "/api/v1/commission-config/revenue-models/*",
                ],
                methods=["POST", "PUT", "PATCH", "DELETE"],
            )
        )

        # Partner branding endpoints
        write_policy = self.security_policies[EndpointSensitivity.WRITE]
        rules.append(
            RateLimitRule(
                rule_id="partner_branding_read",
                limit_type=write_policy.rate_limit_type,
                max_requests=write_policy.max_requests * 3,  # More lenient for reads
                time_window_seconds=write_policy.time_window_seconds,
                endpoints=[
                    "/api/v1/partners/*/brand",
                    "/api/v1/partners/*/brand/theme",
                ],
                methods=["GET"],
            )
        )

        rules.append(
            RateLimitRule(
                rule_id="partner_branding_write",
                limit_type=write_policy.rate_limit_type,
                max_requests=write_policy.max_requests,
                time_window_seconds=write_policy.time_window_seconds,
                endpoints=[
                    "/api/v1/partners/*/brand",
                    "/api/v1/partners/*/brand/verify-domain",
                ],
                methods=["POST", "PUT", "PATCH", "DELETE"],
            )
        )

        # Admin endpoints
        admin_policy = self.security_policies[EndpointSensitivity.ADMIN]
        rules.append(
            RateLimitRule(
                rule_id="admin_endpoints",
                limit_type=admin_policy.rate_limit_type,
                max_requests=admin_policy.max_requests,
                time_window_seconds=admin_policy.time_window_seconds,
                endpoints=[
                    "/api/v1/admin/bootstrap-status",
                    "/api/v1/admin/security-checklist",
                ],
                methods=["GET"],
            )
        )

        # Critical admin operations
        critical_policy = self.security_policies[EndpointSensitivity.CRITICAL]
        rules.append(
            RateLimitRule(
                rule_id="critical_admin_endpoints",
                limit_type=critical_policy.rate_limit_type,
                max_requests=critical_policy.max_requests,
                time_window_seconds=critical_policy.time_window_seconds,
                endpoints=["/api/v1/admin/remove-bootstrap-credentials"],
                methods=["POST"],
            )
        )

        return rules

    def get_cors_config(self) -> dict[str, Any]:
        """Get CORS configuration for management API"""

        # Get allowed origins from environment
        cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
        cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

        # Default development origins if none specified and not in production
        if not cors_origins and self.environment != "production":
            cors_origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:8080",
                "https://localhost:3000",
            ]

        return {
            "allow_origins": cors_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "Accept",
                "Origin",
                "Access-Control-Request-Method",
                "Access-Control-Request-Headers",
                "X-CSRF-Token",
                "X-Tenant-ID",
            ],
            "expose_headers": [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "Retry-After",
            ],
        }

    def get_security_headers_config(self) -> dict[str, str]:
        """Get security headers configuration"""

        headers = {
            # Content Security Policy
            "Content-Security-Policy": self._get_csp_policy(),
            # Security headers
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # HSTS (only in production with HTTPS)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
            if self.environment == "production"
            else "",
            # Permissions Policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
            # Custom headers for API identification
            "X-API-Version": "v1",
            "X-Service": "dotmac-management-api",
        }

        # Remove empty headers
        return {k: v for k, v in headers.items() if v}

    def _get_csp_policy(self) -> str:
        """Generate Content Security Policy based on environment"""

        if self.environment == "production":
            # Strict CSP for production
            return (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # More permissive CSP for development
            return (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https: http:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss: http: https:; "
                "frame-ancestors 'none'"
            )

    def get_request_validation_config(self) -> dict[str, Any]:
        """Get request validation configuration"""

        return {
            "max_request_size": 10_000_000 if self.environment != "production" else 5_000_000,
            "max_json_depth": 10,
            "max_query_params": 50,
            "max_headers": 100,
            "allowed_content_types": [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain",
            ],
            "blocked_user_agents": ["curl", "wget", "python-requests"] if self.environment == "production" else [],
        }

    def get_authentication_config(self) -> dict[str, Any]:
        """Get authentication configuration"""

        return {
            "jwt_algorithm": "HS256",
            "token_expiry": 1800 if self.environment == "production" else 3600,  # 30min prod, 1hr dev
            "refresh_token_expiry": 86400,  # 24 hours
            "require_tenant_context": True,
            "verify_email": self.environment == "production",
            "lockout_threshold": 5,
            "lockout_duration": 900,  # 15 minutes
            "password_history": 5 if self.environment == "production" else 3,
            "session_timeout": 3600,  # 1 hour
            "concurrent_sessions": 3 if self.environment == "production" else 5,
        }

    async def setup_api_security(self, app, jwt_secret_key: str, redis_url: str) -> APISecuritySuite:
        """Setup complete API security using dotmac_shared components"""

        from dotmac_shared.security.api_security_integration import (
            setup_complete_api_security,
        )

        # Get tenant domains for CORS
        cors_origins = self.get_cors_config()["allow_origins"]

        security_result = await setup_complete_api_security(
            app=app,
            environment=self.environment,
            jwt_secret_key=jwt_secret_key,
            redis_url=redis_url,
            api_type="management",
            tenant_domains=cors_origins,
            validate_implementation=True,
        )

        if security_result["status"] != "SUCCESS":
            raise RuntimeError(f"Failed to setup API security: {security_result.get('message', 'Unknown error')}")

        return security_result["security_suite"]


# Global instance for easy import
management_security = ManagementAPISecurityConfig(environment=os.getenv("ENVIRONMENT", "production"))


# Export commonly used configurations
def get_rate_limit_rules() -> list[RateLimitRule]:
    """Get rate limiting rules for management API"""
    return management_security.get_rate_limit_rules()


def get_cors_config() -> dict[str, Any]:
    """Get CORS configuration for management API"""
    return management_security.get_cors_config()


def get_security_headers() -> dict[str, str]:
    """Get security headers for management API"""
    return management_security.get_security_headers_config()


def get_authentication_config() -> dict[str, Any]:
    """Get authentication configuration"""
    return management_security.get_authentication_config()


async def setup_management_api_security(app, jwt_secret_key: str, redis_url: str) -> APISecuritySuite:
    """Setup complete security for management API"""
    return await management_security.setup_api_security(app, jwt_secret_key, redis_url)
