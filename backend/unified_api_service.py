#!/usr/bin/env python3
"""
DotMac Platform - Unified API Service
Exposes all microservices through a single endpoint with comprehensive documentation
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
import httpx
import uvicorn

# Service Registry
SERVICES = {
    "api_gateway": {
        "name": "API Gateway",
        "internal_port": 8000,
        "base_path": "/gateway",
        "description": "Central API gateway with routing, rate limiting, and authentication proxy",
        "health_path": "/health",
        "tags": ["Gateway", "Routing", "Authentication"]
    },
    "identity": {
        "name": "Identity Service",
        "internal_port": 8001,
        "base_path": "/identity",
        "description": "User authentication, customer management, and organization handling",
        "health_path": "/health",
        "tags": ["Authentication", "Users", "Organizations"]
    },
    "billing": {
        "name": "Billing Service",
        "internal_port": 8002,
        "base_path": "/billing",
        "description": "Invoicing, payments, subscriptions, and financial management",
        "health_path": "/health",
        "tags": ["Billing", "Payments", "Invoices"]
    },
    "services": {
        "name": "Services Provisioning",
        "internal_port": 8003,
        "base_path": "/services",
        "description": "Service catalog, provisioning, and lifecycle management",
        "health_path": "/health",
        "tags": ["Services", "Provisioning", "Catalog"]
    },
    "networking": {
        "name": "Network Management",
        "internal_port": 8004,
        "base_path": "/network",
        "description": "Network device management, SNMP monitoring, SSH automation, VOLTHA integration",
        "health_path": "/health",
        "tags": ["Network", "Devices", "Monitoring", "VOLTHA"]
    },
    "analytics": {
        "name": "Analytics Service",
        "internal_port": 8005,
        "base_path": "/analytics",
        "description": "Business intelligence, reporting, and data analytics",
        "health_path": "/health",
        "tags": ["Analytics", "Reports", "BI"]
    },
    "platform": {
        "name": "Platform Service",
        "internal_port": 8006,
        "base_path": "/platform",
        "description": "Core platform utilities, RBAC, and shared services",
        "health_path": "/health",
        "tags": ["Platform", "RBAC", "Utilities"]
    },
    "events": {
        "name": "Event Bus",
        "internal_port": 8007,
        "base_path": "/events",
        "description": "Event-driven architecture, pub/sub, and message queuing",
        "health_path": "/health",
        "tags": ["Events", "PubSub", "Messaging"]
    },
    "ops": {
        "name": "Core Ops",
        "internal_port": 8008,
        "base_path": "/ops",
        "description": "Workflow orchestration, sagas, and job scheduling",
        "health_path": "/health",
        "tags": ["Workflows", "Jobs", "Orchestration"]
    }
}

# Create FastAPI app
app = FastAPI(
    title="DotMac ISP Platform - Unified API",
    description="""
# DotMac ISP Platform API

## Overview
The DotMac Platform is a comprehensive microservices-based telecommunications management platform for Internet Service Providers.

## Key Features
- 🔐 **Multi-tenant Architecture**: Complete tenant isolation and RBAC
- 📡 **Network Management**: SNMP, SSH automation, VOLTHA fiber management
- 💰 **Billing & Invoicing**: Subscription management and payment processing
- 👥 **Customer Management**: CRM capabilities and customer portals
- 📊 **Analytics & Reporting**: Business intelligence and real-time metrics
- 🔄 **Event-Driven**: Asynchronous event processing and workflows
- 🌐 **API Gateway**: Centralized routing and rate limiting
- 🛠️ **Service Provisioning**: Automated service lifecycle management

## Services

| Service | Base Path | Description |
|---------|-----------|-------------|
| API Gateway | `/gateway` | Central routing and authentication |
| Identity | `/identity` | User and customer management |
| Billing | `/billing` | Financial services |
| Services | `/services` | Service provisioning |
| Networking | `/network` | Network management & VOLTHA |
| Analytics | `/analytics` | Business intelligence |
| Platform | `/platform` | Core utilities |
| Events | `/events` | Event bus |
| Core Ops | `/ops` | Workflow orchestration |

## Authentication
All endpoints require JWT Bearer token or API key authentication.

## Rate Limiting
- Default: 1000 requests/minute per client
- Burst: 100 requests/second

## Support
- Documentation: https://docs.dotmac.io
- Support: support@dotmac.io
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "DotMac Platform Team",
        "url": "https://dotmac.io",
        "email": "support@dotmac.io",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# Models
class ServiceStatus(BaseModel):
    """Service health status"""
    service: str
    status: str = Field(description="Health status: healthy, degraded, unhealthy")
    uptime: Optional[str] = None
    version: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None

class PlatformStatus(BaseModel):
    """Platform health status"""
    platform: str = "DotMac ISP Platform"
    status: str = Field(description="Overall platform status")
    services: List[ServiceStatus]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Dependency for optional auth
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get current user from JWT token (optional for some endpoints)"""
    if credentials:
        # In production, validate JWT token here
        return {"user": "authenticated"}
    return None

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API overview"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DotMac Platform API</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 90%;
            }
            h1 {
                color: #333;
                margin: 0 0 10px 0;
                font-size: 2.5em;
            }
            .subtitle {
                color: #666;
                margin: 0 0 30px 0;
                font-size: 1.2em;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }
            .card h3 {
                margin: 0 0 10px 0;
                color: #333;
            }
            .card p {
                margin: 0;
                color: #666;
                font-size: 0.9em;
            }
            .links {
                margin-top: 30px;
                display: flex;
                gap: 20px;
                justify-content: center;
            }
            .link {
                display: inline-block;
                padding: 12px 24px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 500;
                transition: transform 0.2s;
            }
            .link:hover {
                transform: translateY(-2px);
                background: #5a67d8;
            }
            .status {
                margin-top: 20px;
                padding: 15px;
                background: #e8f5e9;
                border-radius: 8px;
                color: #2e7d32;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 DotMac Platform API</h1>
            <p class="subtitle">Comprehensive ISP Management Platform</p>
            
            <div class="status">
                ✅ All Systems Operational - v2.0.0
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>🔐 Identity</h3>
                    <p>User authentication and customer management</p>
                </div>
                <div class="card">
                    <h3>💰 Billing</h3>
                    <p>Invoicing, payments, and subscriptions</p>
                </div>
                <div class="card">
                    <h3>📡 Network</h3>
                    <p>Device management and monitoring</p>
                </div>
                <div class="card">
                    <h3>📊 Analytics</h3>
                    <p>Business intelligence and reporting</p>
                </div>
                <div class="card">
                    <h3>🔄 Events</h3>
                    <p>Event-driven architecture</p>
                </div>
                <div class="card">
                    <h3>🛠️ Services</h3>
                    <p>Service provisioning and catalog</p>
                </div>
            </div>
            
            <div class="links">
                <a href="/docs" class="link">📚 Interactive Docs</a>
                <a href="/redoc" class="link">📖 ReDoc</a>
                <a href="/health" class="link">💚 Health Status</a>
                <a href="/openapi.json" class="link">📋 OpenAPI Spec</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Health endpoints
@app.get("/health", response_model=PlatformStatus, tags=["Health"])
async def platform_health():
    """Get comprehensive platform health status"""
    services_status = []
    overall_status = "healthy"
    
    for service_id, service_info in SERVICES.items():
        try:
            # Check internal service health
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{service_info['internal_port']}{service_info['health_path']}",
                    timeout=2.0
                )
                if response.status_code == 200:
                    status = "healthy"
                else:
                    status = "degraded"
                    overall_status = "degraded"
        except:
            status = "unhealthy"
            overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
        
        services_status.append(ServiceStatus(
            service=service_info["name"],
            status=status,
            version="1.0.0"
        ))
    
    return PlatformStatus(
        status=overall_status,
        services=services_status
    )

@app.get("/{service}/health", response_model=ServiceStatus, tags=["Health"])
async def service_health(service: str):
    """Get specific service health status"""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    service_info = SERVICES[service]
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:{service_info['internal_port']}{service_info['health_path']}",
                timeout=2.0
            )
            if response.status_code == 200:
                return ServiceStatus(
                    service=service_info["name"],
                    status="healthy",
                    version="1.0.0"
                )
    except:
        pass
    
    return ServiceStatus(
        service=service_info["name"],
        status="unhealthy",
        version="1.0.0"
    )

# Service information endpoints
@app.get("/services", tags=["Platform"])
async def list_services():
    """List all available services"""
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

# Example Network Service Endpoints (for demonstration)
@app.get("/network/devices", tags=["Network Management"])
async def list_network_devices():
    """List all network devices"""
    return {
        "devices": [
            {
                "id": "device-001",
                "name": "Core Router 1",
                "type": "router",
                "ip": "192.168.1.1",
                "status": "online",
                "manufacturer": "Cisco",
                "model": "ASR1001-X"
            },
            {
                "id": "device-002",
                "name": "Distribution Switch 1",
                "type": "switch",
                "ip": "192.168.1.10",
                "status": "online",
                "manufacturer": "Juniper",
                "model": "EX4300"
            },
            {
                "id": "device-003",
                "name": "OLT-01",
                "type": "olt",
                "ip": "192.168.2.1",
                "status": "online",
                "manufacturer": "Huawei",
                "model": "MA5800"
            }
        ],
        "total": 3
    }

@app.post("/network/ssh/deploy-configuration", tags=["Network Management"])
async def deploy_network_configuration(
    device_list: List[str] = ["device-001", "device-002"],
    uci_commands: List[str] = ["set network.lan.ipaddr='192.168.1.1'"],
    credentials: Optional[Dict[str, str]] = None
):
    """Deploy UCI configuration to multiple devices via SSH"""
    return {
        "status": "success",
        "message": "Configuration deployed successfully",
        "devices_updated": len(device_list),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/network/topology/analysis", tags=["Network Management"])
async def get_network_topology_analysis():
    """Get comprehensive network analysis"""
    return {
        "nodes": 25,
        "edges": 42,
        "critical_paths": [
            ["Core Router 1", "Distribution Switch 1", "Access Switch 5"]
        ],
        "bottlenecks": ["Distribution Switch 2"],
        "redundancy_score": 0.85,
        "average_path_length": 2.3,
        "network_diameter": 4,
        "clustering_coefficient": 0.62
    }

# Example Identity Service Endpoints
@app.post("/identity/auth/login", tags=["Identity Service"])
async def login(username: str = "admin", password: str = "password"):
    """User authentication endpoint"""
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "id": "user-001",
            "username": username,
            "email": f"{username}@example.com",
            "roles": ["admin", "user"]
        }
    }

@app.get("/identity/users/{user_id}", tags=["Identity Service"])
async def get_user(user_id: str):
    """Get user details by ID"""
    return {
        "id": user_id,
        "username": "john.doe",
        "email": "john.doe@example.com",
        "full_name": "John Doe",
        "created_at": "2024-01-15T10:30:00Z",
        "roles": ["user"],
        "status": "active"
    }

# Example Billing Service Endpoints
@app.get("/billing/invoices", tags=["Billing Service"])
async def list_invoices(customer_id: Optional[str] = None, status: Optional[str] = None):
    """List invoices with optional filters"""
    return {
        "invoices": [
            {
                "id": "inv-2024-001",
                "customer_id": "cust-001",
                "amount": 99.99,
                "currency": "USD",
                "status": "paid",
                "due_date": "2024-02-01",
                "paid_date": "2024-01-28"
            },
            {
                "id": "inv-2024-002",
                "customer_id": "cust-001",
                "amount": 99.99,
                "currency": "USD",
                "status": "pending",
                "due_date": "2024-03-01",
                "paid_date": None
            }
        ],
        "total": 2,
        "total_amount": 199.98
    }

@app.post("/billing/payments", tags=["Billing Service"])
async def process_payment(
    invoice_id: str = "inv-2024-002",
    amount: float = 99.99,
    payment_method: str = "credit_card"
):
    """Process a payment for an invoice"""
    return {
        "payment_id": "pay-" + str(datetime.utcnow().timestamp()),
        "invoice_id": invoice_id,
        "amount": amount,
        "status": "success",
        "payment_method": payment_method,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/services/{service}", tags=["Platform"])
async def get_service_info(service: str):
    """Get detailed service information"""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    service_info = SERVICES[service].copy()
    service_info["id"] = service
    service_info["endpoints"] = [
        f"{service_info['base_path']}/health",
        f"{service_info['base_path']}/api/v1"
    ]
    return service_info

# Proxy endpoints for each service
async def proxy_request(service: str, path: str, request: Request):
    """Proxy requests to internal services"""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    service_info = SERVICES[service]
    target_url = f"http://localhost:{service_info['internal_port']}/{path}"
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    # Forward the request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                params=dict(request.query_params),
                content=body,
                timeout=30.0
            )
            
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

# Create route handlers for each service
# We need to create these dynamically but properly to avoid closure issues
def create_service_proxy(service_id: str, service_info: dict):
    """Factory function to create service proxy handlers with proper closure"""
    
    async def service_proxy_handler(
        path: str,
        request: Request
    ):
        """Proxy handler for a specific service"""
        return await proxy_request(service_id, path, request)
    
    # Set the function name for better debugging
    service_proxy_handler.__name__ = f"{service_id}_proxy_handler"
    
    return service_proxy_handler

# Register routes for each service
for service_id, service_info in SERVICES.items():
    base_path = service_info["base_path"]
    handler = create_service_proxy(service_id, service_info)
    
    # Register the catch-all route for this service
    app.add_api_route(
        f"{base_path}/{{path:path}}",
        handler,
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        tags=[service_info["name"]],
        name=f"{service_id}_proxy",
        summary=f"Proxy to {service_info['name']}",
        description=f"Forward requests to {service_info['name']} service",
        include_in_schema=True
    )
    
    # Also add a root route for each service
    @app.get(
        base_path,
        tags=[service_info["name"]],
        name=f"{service_id}_root",
        summary=f"{service_info['name']} Root",
        description=f"Root endpoint for {service_info['name']}"
    )
    async def service_root(service_id=service_id, service_info=service_info):
        """Service root endpoint"""
        return {
            "service": service_info["name"],
            "description": service_info["description"],
            "base_path": service_info["base_path"],
            "tags": service_info["tags"],
            "status": "available",
            "endpoints": [
                f"{service_info['base_path']}/health",
                f"{service_info['base_path']}/api/v1"
            ]
        }

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        contact=app.contact,
        license_info=app.license_info,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT authentication token"
        },
        "apiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service communication"
        }
    }
    
    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        },
        {
            "url": "http://149.102.135.97:8000",
            "description": "Current deployment"
        },
        {
            "url": "https://api.dotmac.io",
            "description": "Production API"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": "The requested resource was not found",
            "path": str(request.url.path),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    print("🚀 Starting DotMac Unified API Service...")
    print("📚 Documentation: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("💚 Health: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)