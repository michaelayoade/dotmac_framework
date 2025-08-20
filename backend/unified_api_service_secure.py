#!/usr/bin/env python3
"""
DotMac Platform - Secure Unified API Service with Auth and Rate Limiting
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Annotated
from pathlib import Path
from datetime import datetime, timedelta
import logging

from fastapi import FastAPI, HTTPException, Request, Depends, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
import httpx
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from jose import JWTError, jwt
from passlib.context import CryptContext
from circuitbreaker import circuit
import redis
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Security scheme
security = HTTPBearer()

# Redis client for caching and rate limiting
redis_client = redis.Redis.from_url(
    os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True
)

# Prometheus metrics
request_count = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)
request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"]
)

# Circuit breaker for upstream services
@circuit(failure_threshold=5, recovery_timeout=60)
def check_upstream_health(service_url: str):
    """Check if upstream service is healthy."""
    response = httpx.get(f"{service_url}/health", timeout=2.0)
    return response.status_code == 200

# Service Registry (same as before)
SERVICES = {
    "api_gateway": {
        "name": "API Gateway",
        "internal_port": 8000,
        "base_path": "/gateway",
        "description": "Central API gateway with routing, rate limiting, and authentication proxy",
        "health_path": "/health",
        "tags": ["Gateway", "Routing", "Authentication"]
    },
    # ... (other services remain the same)
}

# Create FastAPI app with security enhancements
app = FastAPI(
    title="DotMac ISP Platform - Secure API",
    description="Secure unified API with authentication and rate limiting",
    version="2.0.0",
    docs_url=None,  # Disable in production
    redoc_url=None,  # Disable in production
    openapi_url=None if os.environ.get("ENVIRONMENT") == "production" else "/openapi.json",
)

# Add rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # HSTS in production
    if os.environ.get("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Remove server header
    response.headers.pop("Server", None)
    
    return response

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing."""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response

# Metrics middleware
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    """Track request metrics."""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# CORS middleware with secure configuration
cors_origins = os.environ.get("CORS_ORIGINS", "").split(",")
if cors_origins and cors_origins[0]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # No wildcards
        allow_credentials=False,  # Disabled by default
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        max_age=3600,
    )

# Trusted host middleware
allowed_hosts = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

# Authentication dependencies
def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """Get current user from JWT token."""
    token = credentials.credentials
    
    # Check token blacklist in Redis
    if redis_client.get(f"blacklist:{token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )
    
    user = verify_token(token)
    
    # Verify user still exists and is active
    # (In production, check against database)
    if not user.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user

async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require admin role."""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user

# Token models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class LoginRequest(BaseModel):
    username: str
    password: str

# Authentication endpoints
@app.post("/auth/login", response_model=Token, tags=["Authentication"])
@limiter.limit("5/minute")
async def login(request: Request, login_data: LoginRequest):
    """Authenticate user and return JWT token."""
    # In production, verify against database
    # This is a simplified example
    if login_data.username == "admin" and login_data.password == "secure-password":
        # Create JWT token
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": login_data.username,
            "roles": ["admin", "user"],
            "active": True,
            "exp": expire
        }
        access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        return Token(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )

@app.post("/auth/logout", tags=["Authentication"])
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Logout user by blacklisting token."""
    token = credentials.credentials
    
    # Add token to blacklist with TTL
    ttl = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    redis_client.setex(f"blacklist:{token}", ttl, "1")
    
    return {"message": "Successfully logged out"}

# Health check (public)
@app.get("/health", tags=["Health"])
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Get platform health status."""
    services_status = []
    overall_status = "healthy"
    
    for service_id, service_info in SERVICES.items():
        try:
            # Check with circuit breaker
            if check_upstream_health(f"http://localhost:{service_info['internal_port']}"):
                status = "healthy"
            else:
                status = "unhealthy"
                overall_status = "degraded"
        except:
            status = "unhealthy"
            overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
        
        services_status.append({
            "service": service_info["name"],
            "status": status
        })
    
    return {
        "status": overall_status,
        "services": services_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# Metrics endpoint (requires auth)
@app.get("/metrics", tags=["Monitoring"])
async def get_metrics(current_user: Dict[str, Any] = Depends(require_admin)):
    """Get Prometheus metrics."""
    return Response(content=generate_latest(), media_type="text/plain")

# Protected service endpoints
@app.get("/services", tags=["Platform"])
@limiter.limit("30/minute")
async def list_services(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List all available services."""
    return {
        "services": [
            {
                "id": service_id,
                "name": info["name"],
                "base_path": info["base_path"],
                "description": info["description"],
                "tags": info["tags"]
            }
            for service_id, info in SERVICES.items()
        ]
    }

# Proxy with timeout and circuit breaker
async def proxy_request_secure(
    service: str,
    path: str,
    request: Request,
    current_user: Dict[str, Any]
):
    """Proxy requests to internal services with timeout and auth context."""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    service_info = SERVICES[service]
    target_url = f"http://localhost:{service_info['internal_port']}/{path}"
    
    # Add user context to headers
    headers = dict(request.headers)
    headers["X-User-ID"] = current_user.get("sub", "unknown")
    headers["X-User-Roles"] = ",".join(current_user.get("roles", []))
    headers["X-Request-ID"] = request.state.request_id
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    # Forward request with timeout
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        try:
            # Use circuit breaker
            if not check_upstream_health(f"http://localhost:{service_info['internal_port']}"):
                raise HTTPException(
                    status_code=503,
                    detail=f"Service '{service}' is currently unavailable"
                )
            
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=dict(request.query_params),
                content=body
            )
            
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout calling service {service} at {target_url}")
            raise HTTPException(status_code=504, detail="Service timeout")
        except httpx.RequestError as e:
            logger.error(f"Error calling service {service}: {e}")
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

# Register protected service routes
for service_id, service_info in SERVICES.items():
    base_path = service_info["base_path"]
    
    @app.api_route(
        f"{base_path}/{{path:path}}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        tags=[service_info["name"]],
        name=f"{service_id}_proxy_secure",
        dependencies=[Depends(get_current_user)]
    )
    @limiter.limit("100/minute")
    async def service_proxy_secure(
        path: str,
        request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
        service_id=service_id
    ):
        return await proxy_request_secure(service_id, path, request, current_user)

# Error handlers
@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=401,
        content={
            "error": "unauthorized",
            "message": "Authentication required",
            "request_id": getattr(request.state, "request_id", None)
        },
        headers={"WWW-Authenticate": "Bearer"}
    )

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=403,
        content={
            "error": "forbidden",
            "message": "Insufficient permissions",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal error occurred",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

if __name__ == "__main__":
    # Validate environment
    required_env = ["SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
    missing = [e for e in required_env if not os.environ.get(e)]
    if missing:
        print(f"FATAL: Missing required environment variables: {missing}")
        sys.exit(1)
    
    # Don't run with debug in production
    if os.environ.get("ENVIRONMENT") == "production":
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=False  # Use structured logging instead
        )
    else:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug"
        )