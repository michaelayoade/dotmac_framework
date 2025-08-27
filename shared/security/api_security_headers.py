"""
API Security Headers and CORS Policy Management
Provides comprehensive security headers and CORS configuration for API protection

SECURITY: This module implements security headers to prevent XSS, clickjacking,
CSRF, and other web-based attacks on API endpoints
"""

import logging
from typing import Dict, List, Optional, Union, Callable, Any
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import re

logger = logging.getLogger(__name__)

class SecurityHeaders:
    """
    Security headers configuration and management
    """
    
    # Security headers with secure defaults
    DEFAULT_SECURITY_HEADERS = {
        # Prevent XSS attacks
        "X-Content-Type-Options": "nosniff",
        
        # Prevent clickjacking
        "X-Frame-Options": "DENY",
        
        # XSS protection (legacy, but still useful)
        "X-XSS-Protection": "1; mode=block",
        
        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        
        # Content type protection
        "Content-Type": "application/json; charset=utf-8",
        
        # Cache control for sensitive data
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        
        # Remove server information
        "Server": "DotMac-API",
        
        # Permissions policy (formerly feature policy)
        "Permissions-Policy": (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "accelerometer=(), ambient-light-sensor=()"
        ),
        
        # Cross-Origin policies
        "Cross-Origin-Embedder-Policy": "require-corp",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "cross-origin"
    }
    
    @classmethod
    def get_content_security_policy(
        cls,
        strict_mode: bool = True,
        allow_inline_scripts: bool = False,
        allowed_domains: Optional[List[str]] = None
    ) -> str:
        """
        Generate Content Security Policy header
        """
        allowed_domains = allowed_domains or []
        
        if strict_mode:
            # Very restrictive CSP for API endpoints
            csp = (
                "default-src 'none'; "
                "script-src 'none'; "
                "style-src 'none'; "
                "img-src 'none'; "
                "font-src 'none'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'none'; "
                "base-uri 'none';"
            )
        else:
            # More permissive for API documentation and management interfaces
            script_src = "'self'"
            if allow_inline_scripts:
                script_src += " 'unsafe-inline'"
            
            if allowed_domains:
                domain_list = " ".join(allowed_domains)
                script_src += f" {domain_list}"
            
            csp = (
                f"default-src 'self'; "
                f"script-src {script_src}; "
                f"style-src 'self' 'unsafe-inline'; "
                f"img-src 'self' data: https:; "
                f"font-src 'self'; "
                f"connect-src 'self' {' '.join(allowed_domains) if allowed_domains else ''}; "
                f"frame-ancestors 'none'; "
                f"form-action 'self'; "
                f"base-uri 'self';"
            )
        
        return csp
    
    @classmethod
    def get_strict_transport_security(
        cls,
        max_age: int = 31536000,  # 1 year
        include_subdomains: bool = True,
        preload: bool = True
    ) -> str:
        """
        Generate Strict-Transport-Security header
        """
        hsts = f"max-age={max_age}"
        
        if include_subdomains:
            hsts += "; includeSubDomains"
        
        if preload:
            hsts += "; preload"
        
        return hsts

class CORSPolicyManager:
    """
    CORS policy management with environment-specific configurations
    """
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
    
    def get_cors_configuration(
        self,
        api_type: str = "api",  # api, admin, public
        tenant_domains: Optional[List[str]] = None
    ) -> Dict:
        """
        Get CORS configuration based on environment and API type
        """
        tenant_domains = tenant_domains or []
        
        base_config = {
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With", 
                "X-CSRF-Token",
                "X-Tenant-ID",
                "X-User-ID",
                "Accept",
                "Origin",
                "Cache-Control",
                "X-File-Name"
            ],
            "expose_headers": [
                "X-Total-Count",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "Content-Disposition",
                "X-Request-ID"
            ]
        }
        
        if self.environment == "development":
            # Permissive for development
            base_config.update({
                "allow_origins": [
                    "http://localhost:3000",  # Admin frontend
                    "http://localhost:3001",  # Customer frontend
                    "http://localhost:3002",  # Reseller frontend
                    "http://localhost:3003",  # Technician frontend
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:3001",
                    "http://127.0.0.1:3002",
                    "http://127.0.0.1:3003",
                    "http://localhost:8000",  # API docs
                    "http://localhost:8001",
                ] + tenant_domains
            })
            
        elif self.environment == "staging":
            # Controlled staging environment
            staging_origins = [
                "https://staging-admin.dotmac.app",
                "https://staging-api.dotmac.app",
                "https://staging.dotmac.app"
            ]
            
            # Add tenant-specific staging domains
            for domain in tenant_domains:
                if domain.startswith("https://") and "staging" in domain:
                    staging_origins.append(domain)
            
            base_config.update({
                "allow_origins": staging_origins
            })
            
        elif self.environment == "production":
            # Strict production configuration
            if api_type == "public":
                # Public API - more permissive but controlled
                base_config.update({
                    "allow_origins": [
                        "https://app.dotmac.app",
                        "https://admin.dotmac.app",
                        "https://api.dotmac.app"
                    ] + [d for d in tenant_domains if d.startswith("https://")],
                    "allow_methods": ["GET", "POST", "OPTIONS"],  # Restrict methods
                })
            elif api_type == "admin":
                # Admin API - very restrictive
                base_config.update({
                    "allow_origins": [
                        "https://admin.dotmac.app",
                        "https://management.dotmac.app"
                    ],
                    "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
                })
            else:
                # Default API - controlled access
                base_config.update({
                    "allow_origins": [
                        "https://app.dotmac.app",
                        "https://api.dotmac.app"
                    ] + [d for d in tenant_domains if d.startswith("https://")]
                })
        
        return base_config

class APISecurityMiddleware:
    """
    Comprehensive API security middleware
    """
    
    def __init__(
        self,
        app,
        environment: str = "development",
        api_type: str = "api",
        strict_csp: bool = True,
        custom_headers: Optional[Dict[str, str]] = None,
        exempt_paths: Optional[List[str]] = None,
        tenant_domains: Optional[List[str]] = None
    ):
        self.app = app
        self.environment = environment
        self.api_type = api_type
        self.strict_csp = strict_csp
        self.custom_headers = custom_headers or {}
        self.exempt_paths = exempt_paths or []
        self.tenant_domains = tenant_domains or []
        
        # Initialize security components
        self.security_headers = SecurityHeaders()
        self.cors_manager = CORSPolicyManager(environment)
    
    def should_apply_security_headers(self, path: str) -> bool:
        """Check if security headers should be applied to this path"""
        # Apply to all paths except explicitly exempted ones
        return not any(path.startswith(exempt) for exempt in self.exempt_paths)
    
    def get_security_headers(self, request: Request) -> Dict[str, str]:
        """Get security headers for the request"""
        headers = self.security_headers.DEFAULT_SECURITY_HEADERS.copy()
        
        # Add Content Security Policy
        csp = self.security_headers.get_content_security_policy(
            strict_mode=self.strict_csp,
            allow_inline_scripts=self.environment == "development",
            allowed_domains=self.tenant_domains
        )
        headers["Content-Security-Policy"] = csp
        
        # Add HSTS for HTTPS
        if request.url.scheme == "https" or self.environment == "production":
            headers["Strict-Transport-Security"] = self.security_headers.get_strict_transport_security()
        
        # Add custom headers
        headers.update(self.custom_headers)
        
        # Environment-specific adjustments
        if self.environment == "development":
            # More permissive in development
            headers["X-Frame-Options"] = "SAMEORIGIN"
            del headers["Cross-Origin-Embedder-Policy"]  # Can interfere with dev tools
        
        return headers
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Apply security headers
            if self.should_apply_security_headers(request.url.path):
                security_headers = self.get_security_headers(request)
                
                async def send_wrapper(message):
                    if message["type"] == "http.response.start":
                        headers = dict(message.get("headers", []))
                        
                        # Add security headers
                        for key, value in security_headers.items():
                            headers[key.lower().encode()] = value.encode()
                        
                        message["headers"] = list(headers.items())
                    
                    await send(message)
                
                await self.app(scope, receive, send_wrapper)
            else:
                await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)

class APISecurityConfig:
    """
    Centralized API security configuration
    """
    
    @staticmethod
    def configure_cors_middleware(
        app,
        environment: str = "development",
        api_type: str = "api",
        tenant_domains: Optional[List[str]] = None
    ):
        """Configure CORS middleware for FastAPI app"""
        cors_manager = CORSPolicyManager(environment)
        cors_config = cors_manager.get_cors_configuration(api_type, tenant_domains)
        
        app.add_middleware(
            CORSMiddleware,
            **cors_config
        )
        
        logger.info(f"CORS configured for {environment} environment, {api_type} API type")
    
    @staticmethod
    def add_security_headers_middleware(
        app,
        environment: str = "development",
        api_type: str = "api",
        **kwargs
    ):
        """Add security headers middleware to FastAPI app"""
        security_middleware = APISecurityMiddleware(
            app=app,
            environment=environment,
            api_type=api_type,
            **kwargs
        )
        
        app.middleware("http")(security_middleware)
        logger.info(f"Security headers middleware configured for {environment}")
    
    @staticmethod
    def validate_security_configuration(
        app,
        environment: str
    ) -> Dict[str, Any]:
        """Validate security configuration"""
        issues = []
        recommendations = []
        
        # Check if CORS is configured
        cors_configured = any(
            isinstance(middleware, CORSMiddleware) 
            for middleware in getattr(app, 'user_middleware', [])
        )
        
        if not cors_configured:
            issues.append("CORS middleware not configured")
        
        # Environment-specific checks
        if environment == "production":
            if not hasattr(app, 'docs_url') or app.docs_url is not None:
                issues.append("API documentation should be disabled in production")
            
            recommendations.append("Ensure HTTPS is enforced")
            recommendations.append("Consider implementing API key authentication")
        
        return {
            'security_status': 'SECURE' if not issues else 'NEEDS_ATTENTION',
            'issues': issues,
            'recommendations': recommendations,
            'cors_configured': cors_configured
        }

# Factory functions
def create_security_headers_middleware(
    environment: str = "development",
    api_type: str = "api",
    **kwargs
) -> Callable:
    """Factory for creating security headers middleware"""
    def middleware_factory(app):
        return APISecurityMiddleware(
            app=app,
            environment=environment,
            api_type=api_type,
            **kwargs
        )
    return middleware_factory

def setup_api_security(
    app,
    environment: str = "development",
    api_type: str = "api",
    tenant_domains: Optional[List[str]] = None,
    **kwargs
):
    """
    Complete API security setup with CORS and security headers
    """
    # Configure CORS
    APISecurityConfig.configure_cors_middleware(
        app, environment, api_type, tenant_domains
    )
    
    # Add security headers
    APISecurityConfig.add_security_headers_middleware(
        app, environment, api_type, **kwargs
    )
    
    logger.info(f"Complete API security setup configured for {environment}")
    
    return APISecurityConfig.validate_security_configuration(app, environment)