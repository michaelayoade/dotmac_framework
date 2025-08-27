"""
CSRF Middleware Integration for ISP Framework
Integrates comprehensive CSRF protection into FastAPI application
"""

import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Import our security modules
import sys
sys.path.append('/home/dotmac_framework/shared')

from security.csrf_protection import CSRFProtection, create_csrf_protection, get_csrf_token_endpoint
from security.input_middleware import create_input_sanitization_middleware

# Global CSRF protection instance
csrf_protection: CSRFProtection = None

def init_csrf_protection(app: FastAPI) -> CSRFProtection:
    """
    Initialize CSRF protection for the ISP framework
    """
    global csrf_protection
    
    # Get secret key from environment
    secret_key = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Create CSRF protection with ISP framework specific config
    csrf_protection = create_csrf_protection(
        secret_key=secret_key,
        token_lifetime=3600,  # 1 hour
        exempt_paths=[
            '/api/auth/csrf',
            '/api/health',
            '/docs',
            '/redoc', 
            '/openapi.json',
            '/api/portal/health',  # Portal health checks
            '/api/technician/health'  # Technician health checks
        ]
    )
    
    return csrf_protection

def get_csrf_protection() -> CSRFProtection:
    """
    Dependency to get CSRF protection instance
    """
    if csrf_protection is None:
        raise RuntimeError("CSRF protection not initialized")
    return csrf_protection

async def csrf_token_endpoint():
    """
    Endpoint to get CSRF token
    GET /api/auth/csrf
    """
    csrf = get_csrf_protection()
    return await get_csrf_token_endpoint(csrf)

# Middleware setup function
async def csrf_middleware(request: Request, call_next):
    """
    CSRF middleware for manual integration
    """
    csrf = get_csrf_protection()
    
    # Skip CSRF for exempt requests
    if csrf.is_exempt(request):
        response = await call_next(request)
        return response
    
    try:
        # Validate CSRF token
        from fastapi import Response
        temp_response = Response()
        await csrf.protect_request(request, temp_response)
        
        # If validation passes, process request
        response = await call_next(request)
        return response
        
    except Exception as e:
        # Return CSRF error
        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF protection failed", "error": str(e)}
        )

# Integration helper for existing FastAPI app
def add_csrf_protection(app: FastAPI) -> None:
    """
    Add CSRF protection to existing FastAPI application
    """
    # Initialize CSRF protection
    init_csrf_protection(app)
    
    # Add input sanitization middleware
    input_sanitizer = create_input_sanitization_middleware(
        strict_mode=True,
        log_suspicious=True,
        exempt_paths=[
            '/api/auth/csrf',
            '/api/health',
            '/docs',
            '/redoc', 
            '/openapi.json',
            '/api/portal/health',
            '/api/technician/health'
        ]
    )
    app.middleware("http")(input_sanitizer)
    
    # Add CSRF token endpoint
    app.add_api_route("/api/auth/csrf", csrf_token_endpoint, methods=["GET"])
    
    # Add CSRF middleware
    app.middleware("http")(csrf_middleware)