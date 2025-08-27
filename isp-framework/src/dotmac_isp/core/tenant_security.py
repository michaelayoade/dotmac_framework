"""
Tenant Security Integration for ISP Framework
Integrates Row Level Security and tenant middleware into the ISP Framework
"""

import os
import logging
from typing import Optional
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

# Import shared security components
import sys
sys.path.append('/home/dotmac_framework/shared')

from security.row_level_security import RLSPolicyManager, setup_complete_rls
from security.tenant_middleware import (
    create_tenant_isolation_middleware,
    create_database_tenant_middleware,
    get_tenant_from_header,
    get_user_from_jwt,
    DatabaseTenantMiddleware
)

logger = logging.getLogger(__name__)

# Global instances
rls_manager: Optional[RLSPolicyManager] = None
db_tenant_middleware: Optional[DatabaseTenantMiddleware] = None

async def init_tenant_security(engine: Engine, session: Session) -> dict:
    """
    Initialize complete tenant security for ISP Framework
    """
    global rls_manager, db_tenant_middleware
    
    try:
        # Initialize RLS manager
        rls_manager = RLSPolicyManager(engine)
        
        # Set up complete Row Level Security
        rls_results = await setup_complete_rls(engine, session)
        
        # Initialize database tenant middleware
        db_tenant_middleware = create_database_tenant_middleware(rls_manager)
        
        logger.info("✅ Tenant security initialization completed")
        return {
            'success': True,
            'rls_manager_created': rls_manager is not None,
            'db_middleware_created': db_tenant_middleware is not None,
            'rls_setup_results': rls_results
        }
        
    except Exception as e:
        logger.error(f"❌ Tenant security initialization failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def get_rls_manager() -> Optional[RLSPolicyManager]:
    """Get the global RLS manager instance"""
    return rls_manager

def get_db_tenant_middleware() -> Optional[DatabaseTenantMiddleware]:
    """Get the global database tenant middleware instance"""
    return db_tenant_middleware

def extract_tenant_from_request(request: Request) -> str:
    """
    Extract tenant ID from request for ISP Framework
    
    Priority order:
    1. Header: x-tenant-id
    2. JWT token (if implemented)
    3. Subdomain (for production)
    """
    # Try header first (for development/testing)
    tenant_id = request.headers.get('x-tenant-id')
    if tenant_id:
        return tenant_id
    
    # Try to extract from JWT token
    try:
        # This would integrate with your JWT implementation
        # For now, use a default tenant for development
        return os.getenv('DEFAULT_TENANT_ID', 'dev-tenant-001')
    except:
        return os.getenv('DEFAULT_TENANT_ID', 'dev-tenant-001')

def extract_user_from_request(request: Request) -> Optional[str]:
    """Extract user ID from request"""
    # Try header first
    user_id = request.headers.get('x-user-id')
    if user_id:
        return user_id
    
    # Try to extract from JWT token
    try:
        # This would integrate with your JWT implementation
        return None
    except:
        return None

def add_tenant_security_middleware(app: FastAPI) -> None:
    """
    Add tenant security middleware to FastAPI application
    """
    # Create tenant isolation middleware
    tenant_middleware = create_tenant_isolation_middleware(
        get_tenant_func=extract_tenant_from_request,
        get_user_func=extract_user_from_request,
        exempt_paths=[
            '/docs',
            '/redoc', 
            '/openapi.json',
            '/health',
            '/api/health',
            '/api/portal/health',
            '/api/technician/health',
            '/api/auth'
        ],
        strict_mode=True  # Enforce tenant context for all requests
    )
    
    # Add middleware to app
    app.middleware("http")(tenant_middleware)
    logger.info("✅ Tenant security middleware added to ISP Framework")

# Dependency for getting tenant-aware database sessions
async def get_tenant_db_session(
    request: Request,
    session: Session = Depends()
) -> Session:
    """
    Get a database session with proper tenant context set
    """
    if not db_tenant_middleware:
        raise RuntimeError("Database tenant middleware not initialized")
    
    tenant_id = extract_tenant_from_request(request)
    user_id = extract_user_from_request(request)
    client_ip = request.client.host if request.client else None
    
    # Use context manager to ensure proper tenant context
    async with db_tenant_middleware.tenant_session(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        client_ip=client_ip
    ) as tenant_session:
        yield tenant_session

# Security validation functions
async def validate_tenant_isolation(
    tenant_1: str = "test-tenant-1",
    tenant_2: str = "test-tenant-2"
) -> dict:
    """
    Validate tenant isolation is working correctly
    """
    if not rls_manager:
        return {'error': 'RLS manager not initialized'}
    
    try:
        from dotmac_isp.core.database import get_session
        
        async with get_session() as session:
            results = await rls_manager.validate_tenant_isolation(
                session, tenant_1, tenant_2
            )
            return results
    except Exception as e:
        return {'error': str(e)}

async def get_rls_status() -> dict:
    """Get current Row Level Security status"""
    if not rls_manager:
        return {'error': 'RLS manager not initialized'}
    
    try:
        from dotmac_isp.core.database import get_session
        
        async with get_session() as session:
            status = await rls_manager.get_rls_status(session)
            return status
    except Exception as e:
        return {'error': str(e)}