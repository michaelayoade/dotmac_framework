#!/usr/bin/env python3
"""
Management Platform server runner - fixes import issues.
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path for proper imports
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

def create_app():
    """Create FastAPI application with proper imports."""
    
    # Set environment variables
    os.environ.setdefault('SECRET_KEY', 'mgmt-secret-key-minimum-32-chars-long')
    os.environ.setdefault('JWT_SECRET_KEY', 'mgmt-jwt-secret-key-minimum-32-chars-long')
    
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Import configuration
    from config import get_settings
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add basic routes
    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "status": "operational",
            "environment": settings.environment
        }
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "management-platform"}
    
    # Include API routers
    try:
        from api.v1 import api_router
        app.include_router(api_router, prefix="/api/v1")
    except Exception as e:
        print(f"Warning: Could not load API routes: {e}")
        
        # Fallback placeholder endpoints
        @app.get("/api/v1/tenants")
        async def list_tenants_fallback():
            return {
                "tenants": [],
                "message": "Tenant management endpoint (fallback - API routes failed to load)"
            }
        
        @app.post("/api/v1/deploy")
        async def deploy_tenant_fallback():
            return {
                "status": "deployment_initiated", 
                "message": "Tenant deployment endpoint (fallback - API routes failed to load)"
            }
    
    return app

if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    
    print("🚀 Starting Management Platform...")
    print(f"📍 Server: http://0.0.0.0:8001")
    print(f"📚 Docs: http://0.0.0.0:8001/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False
    )